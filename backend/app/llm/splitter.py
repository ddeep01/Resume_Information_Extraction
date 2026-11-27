import os
import sys
import re
import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Union, Dict, Any
from pathlib import Path

from backend.app.llm.token_counter import TokenCounter
from backend.app.config import settings, BASE_DIR

logger = logging.getLogger("TextSplitter")

# ANSI color codes for rich terminal display
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

@dataclass
class Chunk:
    chunk_id: str
    text: str
    token_count: int
    start_char: int
    end_char: int
    overlap_tokens: int = 0
    overlap_chars: int = 0
    split_level: int = 0

SECTION_HEADER_PATTERN = re.compile(
    r'\n\s*(?:[A-Z\s]{3,30}|EDUCATION|WORK\s+EXPERIENCE|ACADEMIC\s+EXPERIENCE|INDUSTRY\s+EXPERIENCE|EXPERIENCE|EMPLOYMENT|PUBLICATIONS|PROJECTS|RESEARCH(?:\s+AREAS|\s+EXPERIENCE|\s+INTERESTS)?|PATENTS|CERTIFICATIONS|SKILLS|TECHNICAL\s+SKILLS|AWARDS|HONORS|SUMMARY|PROFILE)\s*(?::|\n)',
    re.IGNORECASE
)
BULLET_PATTERN = re.compile(r'\n\s*(?:[-*•]|\d+\.)\s+')
SENTENCE_PATTERN = re.compile(r'(?<=[.!?])\s+')


class RecursiveTextSplitter:
    """
    Adaptive, boundary-aware, recursive text splitter with token overlap control
    and rich terminal visualization of the recursive splitting process.
    """
    def __init__(self, token_counter: Optional[TokenCounter] = None, verbose: bool = True):
        self.token_counter = token_counter or TokenCounter()
        self.verbose = verbose

    def find_best_split_point(
        self,
        text: str,
        target_char_idx: int,
        window_chars: int = 4000,
        return_details: bool = False
    ) -> Union[int, Tuple[int, str, str]]:
        """
        Find natural semantic split boundary near target_char_idx within +/- window_chars.
        Priority order:
        1. Section boundary
        2. Paragraph boundary (\n\n)
        3. Bullet item boundary
        4. Sentence boundary
        5. Line boundary (\n)
        6. Target char fallback
        """
        text_len = len(text)
        search_start = max(0, target_char_idx - window_chars)
        search_end = min(text_len, target_char_idx + window_chars)
        search_region = text[search_start:search_end]

        boundary_type = "MIDPOINT_FALLBACK"
        boundary_detail = "Exact midpoint character"
        split_idx = target_char_idx

        # 1. Section boundary
        section_matches = list(SECTION_HEADER_PATTERN.finditer(search_region))
        if section_matches:
            best_match = min(section_matches, key=lambda m: abs((search_start + m.start()) - target_char_idx))
            split_idx = search_start + best_match.start()
            boundary_type = "SECTION_HEADER"
            boundary_detail = best_match.group(0).strip().replace("\n", " ")
        else:
            # 2. Paragraph boundary (\n\n)
            para_indices = [search_start + m.start() for m in re.finditer(r'\n\s*\n', search_region)]
            if para_indices:
                split_idx = min(para_indices, key=lambda idx: abs(idx - target_char_idx))
                boundary_type = "PARAGRAPH_BREAK"
                boundary_detail = "Double newline paragraph separator (\\n\\n)"
            else:
                # 3. Bullet boundary
                bullet_matches = list(BULLET_PATTERN.finditer(search_region))
                if bullet_matches:
                    best_bullet = min(bullet_matches, key=lambda m: abs((search_start + m.start()) - target_char_idx))
                    split_idx = search_start + best_bullet.start()
                    boundary_type = "BULLET_POINT"
                    boundary_detail = f"Bullet list marker '{best_bullet.group(0).strip()}'"
                else:
                    # 4. Sentence boundary
                    sentence_indices = [search_start + m.start() for m in SENTENCE_PATTERN.finditer(search_region)]
                    if sentence_indices:
                        split_idx = min(sentence_indices, key=lambda idx: abs(idx - target_char_idx))
                        boundary_type = "SENTENCE_BOUNDARY"
                        boundary_detail = "Sentence terminating punctuation (. / ! / ?)"
                    else:
                        # 5. Line boundary (\n)
                        line_indices = [search_start + m.start() for m in re.finditer(r'\n', search_region)]
                        if line_indices:
                            split_idx = min(line_indices, key=lambda idx: abs(idx - target_char_idx))
                            boundary_type = "LINE_BREAK"
                            boundary_detail = "Newline boundary (\\n)"

        if return_details:
            return split_idx, boundary_type, boundary_detail
        return split_idx

    def _split_into_two(
        self,
        text: str,
        safe_limit: int,
        overlap_tokens: int,
        start_offset: int = 0,
        chunk_prefix: str = "chunk",
        level: int = 1,
        verbose: bool = True
    ) -> Tuple[Tuple[str, int, int], Tuple[str, int, int]]:
        """
        Split text into left and right sub-texts with overlap near the midpoint.
        Outputs detailed boundary and overlap reasoning to terminal.
        """
        total_tokens = self.token_counter.count_tokens(text)
        total_chars = len(text)

        # Estimate midpoint in characters
        mid_ratio = 0.5
        target_char_idx = int(total_chars * mid_ratio)
        
        split_idx, split_type, split_detail = self.find_best_split_point(
            text, target_char_idx, return_details=True
        )
        
        # Ensure split_idx is valid and not at exact boundaries 0 or total_chars
        if split_idx <= 100 or split_idx >= total_chars - 100:
            split_idx = total_chars // 2
            split_type = "MIDPOINT_FALLBACK"
            split_detail = "Boundary was too close to ends (<100 chars); using exact midpoint"

        # Left piece: 0 to split_idx
        left_text = text[:split_idx]

        # Right piece with overlap: start back from split_idx by overlap_tokens equivalent
        overlap_chars = self.token_counter.estimate_chars_for_tokens(overlap_tokens)
        right_start_raw = max(0, split_idx - overlap_chars)
        
        # Refine right_start to a clean boundary near right_start_raw
        right_start, right_type, right_detail = self.find_best_split_point(
            text, right_start_raw, window_chars=500, return_details=True
        )
        if right_start >= split_idx:
            right_start = max(0, split_idx - overlap_chars)
            right_type = "DIRECT_OFFSET"
            right_detail = f"Raw offset -{overlap_chars} chars"

        right_text = text[right_start:]

        left_range = (left_text, start_offset, start_offset + split_idx)
        right_range = (right_text, start_offset + right_start, start_offset + total_chars)

        overlap_segment_chars = max(0, split_idx - right_start)
        overlap_segment_tokens = self.token_counter.count_tokens(text[right_start:split_idx]) if overlap_segment_chars > 0 else 0
        left_tokens = self.token_counter.count_tokens(left_text)
        right_tokens = self.token_counter.count_tokens(right_text)

        if verbose:
            indent = "  " * (level - 1)
            print(f"{CYAN}[TOKEN-SPLIT]{RESET} {indent}├── {BOLD}Split Level {level} for '{chunk_prefix}':{RESET}", flush=True)
            print(f"{CYAN}[TOKEN-SPLIT]{RESET} {indent}│   ├─ Current Node: {total_chars:,} chars (~{total_tokens:,} tokens) > Limit {safe_limit:,}", flush=True)
            print(f"{CYAN}[TOKEN-SPLIT]{RESET} {indent}│   ├─ Target Midpoint: char {target_char_idx:,} (~50% of node)", flush=True)
            print(f"{CYAN}[TOKEN-SPLIT]{RESET} {indent}│   ├─ {MAGENTA}Boundary Found [{split_type}]:{RESET} local char {split_idx:,} (doc pos: {start_offset + split_idx:,})", flush=True)
            if split_detail:
                print(f"{CYAN}[TOKEN-SPLIT]{RESET} {indent}│   │  Detail: \"{split_detail[:70]}\"", flush=True)
            print(f"{CYAN}[TOKEN-SPLIT]{RESET} {indent}│   ├─ {YELLOW}Overlap Configuration:{RESET} {overlap_tokens} tokens target (~{overlap_chars} chars)", flush=True)
            print(f"{CYAN}[TOKEN-SPLIT]{RESET} {indent}│   │  Right branch start: [{right_type}] at local char {right_start:,} (doc pos: {start_offset + right_start:,})", flush=True)
            print(f"{CYAN}[TOKEN-SPLIT]{RESET} {indent}│   │  Actual shared overlap: {overlap_segment_chars:,} chars (~{overlap_segment_tokens} tokens)", flush=True)
            print(f"{CYAN}[TOKEN-SPLIT]{RESET} {indent}│   ├─ {GREEN}Child L [{chunk_prefix}_L]:{RESET} doc chars [{start_offset:,} .. {start_offset + split_idx:,}] ({len(left_text):,} chars, ~{left_tokens:,} tokens)", flush=True)
            print(f"{CYAN}[TOKEN-SPLIT]{RESET} {indent}│   └─ {GREEN}Child R [{chunk_prefix}_R]:{RESET} doc chars [{start_offset + right_start:,} .. {start_offset + total_chars:,}] ({len(right_text):,} chars, ~{right_tokens:,} tokens)", flush=True)

        return left_range, right_range

    def split_text(
        self,
        text: str,
        safe_limit: Optional[int] = None,
        overlap_tokens: Optional[int] = None,
        chunk_prefix: str = "chunk",
        start_offset: int = 0,
        level: int = 0,
        verbose: Optional[bool] = None,
        is_root: bool = True
    ) -> List[Chunk]:
        """
        Recursively split text into overlapping chunks until every chunk <= safe_limit.
        Prints real-time breakdown, boundary detection details, tree view, and summary table to terminal.
        """
        safe_limit = safe_limit or settings.SAFE_INPUT_TOKENS
        overlap_tokens = overlap_tokens or settings.OVERLAP_TOKENS
        is_verbose = self.verbose if verbose is None else verbose

        token_count = self.token_counter.count_tokens(text)

        # Print banner on root call
        if is_root and is_verbose:
            print(f"\n{CYAN}{'=' * 80}{RESET}", flush=True)
            print(f"{CYAN}{BOLD}[TOKEN-SPLIT] BOUNDARY-AWARE RECURSIVE TOKEN SPLITTER{RESET}", flush=True)
            print(f"{CYAN}[TOKEN-SPLIT]{RESET} Document ID     : {BOLD}{chunk_prefix}{RESET}", flush=True)
            print(f"{CYAN}[TOKEN-SPLIT]{RESET} Document Size   : {len(text):,} chars | {BOLD}{token_count:,} tokens{RESET}", flush=True)
            print(f"{CYAN}[TOKEN-SPLIT]{RESET} Safe Input Limit: {BOLD}{safe_limit:,} tokens{RESET} (Max per LLM call)", flush=True)
            print(f"{CYAN}[TOKEN-SPLIT]{RESET} Overlap Target  : {BOLD}{overlap_tokens:,} tokens{RESET} (~{self.token_counter.estimate_chars_for_tokens(overlap_tokens):,} chars)", flush=True)
            print(f"{CYAN}{'-' * 80}{RESET}", flush=True)

        # Base case: text fits within safe limit
        if token_count <= safe_limit:
            if is_root and is_verbose:
                print(f"{GREEN}[TOKEN-SPLIT] ✓ Document fits safely ({token_count:,} tokens <= {safe_limit:,} limit). No splitting required.{RESET}", flush=True)
                print(f"{CYAN}{'=' * 80}{RESET}\n", flush=True)
            return [
                Chunk(
                    chunk_id=chunk_prefix,
                    text=text,
                    token_count=token_count,
                    start_char=start_offset,
                    end_char=start_offset + len(text),
                    overlap_tokens=0,
                    overlap_chars=0,
                    split_level=level
                )
            ]

        if is_root and is_verbose:
            print(f"{YELLOW}[TOKEN-SPLIT] ⚠ Document exceeds safe limit ({token_count:,} > {safe_limit:,} tokens).{RESET}", flush=True)
            print(f"{YELLOW}[TOKEN-SPLIT] ➔ Initiating Recursive Semantic Splitting Pipeline...{RESET}\n", flush=True)

        # Recursive case: split into left and right
        left_item, right_item = self._split_into_two(
            text,
            safe_limit,
            overlap_tokens,
            start_offset=start_offset,
            chunk_prefix=chunk_prefix,
            level=level + 1,
            verbose=is_verbose
        )
        
        left_text, left_start, left_end = left_item
        right_text, right_start, right_end = right_item

        # Guard against infinite recursion if split produced identical sizes
        if len(left_text) >= len(text) or len(right_text) >= len(text):
            mid = len(text) // 2
            left_text = text[:mid]
            right_text = text[max(0, mid - 500):]
            left_start, left_end = start_offset, start_offset + len(left_text)
            right_start, right_end = start_offset + max(0, mid - 500), start_offset + len(text)

        left_chunks = self.split_text(
            left_text,
            safe_limit=safe_limit,
            overlap_tokens=overlap_tokens,
            chunk_prefix=f"{chunk_prefix}_L",
            start_offset=left_start,
            level=level + 1,
            verbose=is_verbose,
            is_root=False
        )
        right_chunks = self.split_text(
            right_text,
            safe_limit=safe_limit,
            overlap_tokens=overlap_tokens,
            chunk_prefix=f"{chunk_prefix}_R",
            start_offset=right_start,
            level=level + 1,
            verbose=is_verbose,
            is_root=False
        )

        all_chunks = left_chunks + right_chunks

        # When root completes, display summary table and tree visualization
        if is_root and is_verbose:
            self._print_summary_table(all_chunks, chunk_prefix, safe_limit, overlap_tokens)

        return all_chunks

    def _render_tree_lines(self, chunks: List[Chunk], prefix: str) -> List[str]:
        """
        Build an ASCII hierarchical tree diagram of the recursive split structure.
        """
        tree: Dict[str, Any] = {}
        for chk in chunks:
            suffix = chk.chunk_id[len(prefix):].lstrip('_')
            parts = suffix.split('_') if suffix else []
            curr = tree
            for p in parts:
                if p not in curr:
                    curr[p] = {}
                curr = curr[p]
            curr['__chunk__'] = chk

        lines = []
        def _walk(node: Dict[str, Any], path_prefix: str, is_last: bool, name: str):
            connector = "└── " if is_last else "├── "
            chk_data: Optional[Chunk] = node.get('__chunk__')
            if name == prefix:
                lines.append(f"└── {BOLD}{name}{RESET} (Root Document)")
                next_p = "    "
            else:
                if chk_data:
                    lines.append(
                        f"{path_prefix}{connector}{GREEN}{BOLD}{name}{RESET} "
                        f"[Leaf: {chk_data.token_count:,} tokens, chars {chk_data.start_char:,}..{chk_data.end_char:,}]"
                    )
                else:
                    lines.append(f"{path_prefix}{connector}{CYAN}{name}{RESET} (Branch node)")
                next_p = path_prefix + ("    " if is_last else "│   ")

            children = [k for k in node.keys() if k != '__chunk__']
            for i, c in enumerate(children):
                _walk(node[c], next_p, i == len(children) - 1, c)

        _walk(tree, "", True, prefix)
        return lines

    def _print_summary_table(
        self,
        chunks: List[Chunk],
        prefix: str,
        safe_limit: int,
        overlap_tokens: int
    ):
        """
        Print formatted table and hierarchy breakdown of final chunks to terminal.
        """
        print(f"\n{CYAN}{'=' * 80}{RESET}", flush=True)
        print(f"{GREEN}{BOLD}[TOKEN-SPLIT] SPLITTING COMPLETE: Generated {len(chunks)} Leaf Chunks for '{prefix}'{RESET}", flush=True)
        print(f"{CYAN}{'-' * 80}{RESET}", flush=True)

        # Print Tree Hierarchy
        print(f"\n{BOLD}[TOKEN-SPLIT TREE HIERARCHY]{RESET}", flush=True)
        for line in self._render_tree_lines(chunks, prefix):
            print(f"  {line}", flush=True)
        print("", flush=True)
        
        # Table Header
        print(f"{BOLD}[TOKEN-SPLIT CHUNK BREAKDOWN TABLE]{RESET}", flush=True)
        header = f" {'#':<3} | {'Chunk ID':<26} | {'Tokens':<8} | {'Doc Span (Chars)':<20} | {'Overlap':<11} | {'Preview (First line / text)':<35}"
        print(f"{BOLD}{header}{RESET}", flush=True)
        print(f"{DIM}{'-' * 115}{RESET}", flush=True)

        for idx, chk in enumerate(chunks, 1):
            span_str = f"{chk.start_char:,} -> {chk.end_char:,} ({chk.end_char - chk.start_char:,}c)"
            
            # Calculate overlap with previous chunk if any
            if idx > 1:
                prev_chk = chunks[idx - 2]
                overlap_c = max(0, prev_chk.end_char - chk.start_char)
                overlap_t = self.token_counter.count_tokens(prev_chk.text[-(overlap_c):]) if overlap_c > 0 else 0
                overlap_str = f"{overlap_c:,}c (~{overlap_t}t)"
            else:
                overlap_str = "0 (Initial)"

            # First non-empty line preview
            preview = ""
            for line in chk.text.splitlines():
                clean_l = line.strip()
                if clean_l and len(clean_l) > 3:
                    preview = clean_l[:40] + ("..." if len(clean_l) > 40 else "")
                    break
            if not preview:
                preview = chk.text[:40].replace("\n", " ") + "..."

            # Color code tokens based on limit
            token_color = GREEN if chk.token_count <= safe_limit else YELLOW
            row = f" {idx:<3} | {chk.chunk_id:<26} | {token_color}{chk.token_count:>6,}{RESET}  | {span_str:<20} | {overlap_str:<11} | {preview:<35}"
            print(row, flush=True)

        print(f"{DIM}{'-' * 115}{RESET}", flush=True)
        all_passed = all(chk.token_count <= safe_limit for chk in chunks)
        if all_passed:
            print(f"{GREEN}[TOKEN-SPLIT] ✓ Verification Passed: All {len(chunks)} leaf chunks strictly comply with SAFE_INPUT_TOKENS ({safe_limit:,} tokens).{RESET}", flush=True)
        else:
            print(f"{YELLOW}[TOKEN-SPLIT] ⚠ Note: Some chunks exceed {safe_limit:,} tokens.{RESET}", flush=True)
        print(f"{CYAN}{'=' * 80}{RESET}\n", flush=True)


def parse_and_split_cli():
    """
    CLI runner to demonstrate and test token splitting directly in the terminal.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Antigravity Boundary-Aware Recursive Token Splitter Terminal Visualizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run live demonstration on default session resume (CAND-0001):
  python -m backend.app.llm.splitter

  # Run on a specific text, PDF or DOCX file:
  python -m backend.app.llm.splitter data/sessions/SES-2026-0001/cleaned_text/CAND-0001.txt

  # Custom safe limits and overlap:
  python -m backend.app.llm.splitter resume.pdf --safe-limit 1000 --overlap 100

  # Synthetic high-token resume demo:
  python -m backend.app.llm.splitter --demo --tokens 6000
        """
    )
    parser.add_argument("path", nargs="?", default=None, help="Path to resume file (txt, pdf, docx) or text string")
    parser.add_argument("--safe-limit", type=int, default=settings.SAFE_INPUT_TOKENS, help=f"Safe token limit per chunk (default: {settings.SAFE_INPUT_TOKENS})")
    parser.add_argument("--overlap", type=int, default=settings.OVERLAP_TOKENS, help=f"Overlap token target (default: {settings.OVERLAP_TOKENS})")
    parser.add_argument("--prefix", type=str, default="RESUME_DEMO", help="Prefix for chunk IDs (default: RESUME_DEMO)")
    parser.add_argument("--demo", action="store_true", help="Generate synthetic multi-section resume for demonstration")
    parser.add_argument("--tokens", type=int, default=5000, help="Target token count for synthetic resume demo (default: 5000)")
    parser.add_argument("--show-chunks", action="store_true", help="Print full text content of each generated chunk")

    args = parser.parse_args()

    splitter = RecursiveTextSplitter(verbose=True)

    text_to_split = None
    input_source = ""

    if args.demo:
        print(f"\n{BLUE}[CLI] Generating synthetic {args.tokens:,}-token academic CV for splitting demo...{RESET}")
        text_to_split = _generate_synthetic_cv(args.tokens)
        input_source = f"Synthetic Demo ({args.tokens:,} tokens)"
    elif args.path:
        file_path = Path(args.path)
        if file_path.exists():
            input_source = str(file_path)
            if file_path.suffix.lower() == ".pdf":
                from backend.app.pipeline.pdf_extractor import PDFExtractor
                extractor = PDFExtractor()
                text_to_split, _, _ = extractor.extract(file_path)
            elif file_path.suffix.lower() == ".docx":
                from backend.app.pipeline.docx_extractor import DocxExtractor
                extractor = DocxExtractor()
                text_to_split, _, _ = extractor.extract(file_path)
            else:
                text_to_split = file_path.read_text(encoding="utf-8")
        else:
            # Treated as raw string
            text_to_split = args.path
            input_source = "Direct string input"
    else:
        # Check if default session resume exists
        default_resume = BASE_DIR / "data" / "sessions" / "SES-2026-0001" / "cleaned_text" / "CAND-0001.txt"
        if default_resume.exists():
            input_source = f"Default Session Resume ({default_resume.name})"
            text_to_split = default_resume.read_text(encoding="utf-8")
        else:
            # Generate demo CV
            print(f"\n{BLUE}[CLI] No file specified. Running demonstration with synthetic 5,000-token resume...{RESET}")
            text_to_split = _generate_synthetic_cv(5000)
            input_source = "Synthetic Academic Resume (5,000 tokens)"

    print(f"\n{BOLD}Loaded Input Source:{RESET} {input_source}")

    chunks = splitter.split_text(
        text_to_split,
        safe_limit=args.safe_limit,
        overlap_tokens=args.overlap,
        chunk_prefix=args.prefix
    )

    if args.show_chunks:
        print(f"\n{CYAN}{'=' * 80}{RESET}")
        print(f"{BOLD}[CLI] FULL CHUNK CONTENTS INSPECTOR:{RESET}")
        print(f"{CYAN}{'=' * 80}{RESET}")
        for i, chk in enumerate(chunks, 1):
            print(f"\n{GREEN}{BOLD}--- CHUNK {i}/{len(chunks)}: {chk.chunk_id} ({chk.token_count} tokens | chars {chk.start_char}-{chk.end_char}) ---{RESET}")
            print(chk.text[:600] + ("\n... [truncated] ..." if len(chk.text) > 600 else ""))
            print(f"{DIM}{'-' * 80}{RESET}")


def _generate_synthetic_cv(approx_tokens: int) -> str:
    """Generate realistic academic resume text with headers and sections."""
    sections = [
        """CURRICULUM VITAE
DR. VIKRAMADITYA SEN, Ph.D.
Professor & Head of Department | Computer Science & Engineering
Indian Institute of Technology Delhi, Hauz Khas, New Delhi 110016
Email: vikram.sen@cse.iitd.ac.in | Phone: +91 11 2659 1000

EDUCATION
2010 - 2014: Doctor of Philosophy (Ph.D.) in Computer Science
Massachusetts Institute of Technology (MIT), Cambridge, USA
Thesis: High-Performance Distributed Systems for Massive-Scale Graph Processing
Advisor: Prof. Arvind Krishnamurthy

2008 - 2010: Master of Technology (M.Tech) in Computer Science
Indian Institute of Technology Bombay, Mumbai, India
CPI: 9.85 / 10.0 (Institute Gold Medal)

2004 - 2008: Bachelor of Technology (B.Tech) in Computer Engineering
Delhi Technological University (DTU), New Delhi, India
First Class with Distinction (88.4%)

WORK EXPERIENCE
July 2019 - Present: Full Professor
Department of Computer Science & Engineering, IIT Delhi
- Leading the Distributed Systems & Network Architecture Research Laboratory.
- Supervised 14 PhD theses and 32 Master's theses.
- Principal Investigator on $3.8M funded research projects from DST, MeitY, and Intel.

Jan 2015 - June 2019: Associate Professor
Department of Computer Science & Engineering, IIT Delhi
- Developed foundational courses in Cloud Computing, Operating Systems, and Distributed Algorithms.
- Authored 28 top-tier conference and journal papers in IEEE TPDS, ACM TOCS, and OSDI.

June 2014 - Dec 2014: Postdoctoral Research Fellow
Computer Science and Artificial Intelligence Laboratory (CSAIL), MIT
- Researched RDMA-accelerated disaggregated memory architectures.
"""
    ]

    pub_template = """
PUBLICATIONS & RESEARCH PAPERS
[Paper {i}] "{title}"
Authors: Vikramaditya Sen, {coauthors}
Venue: {venue} ({year})
Abstract: This paper presents novel algorithmic paradigms for low-latency consensus protocols in heterogeneous distributed clusters. Extensive empirical evaluations across 2,048 compute nodes show up to 3.8x improvement in transaction throughput under high contention.
"""
    venues = [
        "IEEE Transactions on Parallel and Distributed Systems (TPDS)",
        "ACM Symposium on Operating Systems Principles (SOSP)",
        "USENIX Symposium on Operating Systems Design and Implementation (OSDI)",
        "IEEE International Conference on Distributed Computing Systems (ICDCS)",
        "ACM Transactions on Computer Systems (TOCS)",
        "IEEE Transactions on Cloud Computing"
    ]

    i = 1
    while True:
        p_text = pub_template.format(
            i=i,
            title=f"Scalable Fault-Tolerant Consensus Protocol for Cloud Systems Part {i}",
            coauthors=f"Co-author A{i}, Co-author B{i}, Co-author C{i}",
            venue=venues[i % len(venues)],
            year=2015 + (i % 10)
        )
        sections.append(p_text)
        current = "\n".join(sections)
        if len(current) / 3.8 >= approx_tokens:
            break
        i += 1

    return "\n".join(sections)


if __name__ == "__main__":
    parse_and_split_cli()
