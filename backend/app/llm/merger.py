import json
import logging
from typing import Dict, Any, List, Optional
from backend.app.llm.base import LLMProvider
from backend.app.llm.json_validator import JSONValidator
from backend.app.llm.prompts import MERGE_SYSTEM_PROMPT, MERGE_USER_PROMPT_TEMPLATE, SCHEMA_STR_TEMPLATE

logger = logging.getLogger("HierarchicalMerger")

class HierarchicalMerger:
    """
    Hierarchical (pairwise binary) merger for combining partial resume JSON outputs.
    Includes both LLM-driven synthesis and deterministic python deduplication.
    """
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.json_validator = JSONValidator()

    def merge_two(self, json_a: Dict[str, Any], json_b: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge two partial candidate JSON objects using LLM merge prompt.
        """
        if not json_a:
            return json_b or {}
        if not json_b:
            return json_a or {}

        prompt = MERGE_USER_PROMPT_TEMPLATE.replace("{schema_str}", SCHEMA_STR_TEMPLATE)\
                                           .replace("{json_a}", json.dumps(json_a, indent=2))\
                                           .replace("{json_b}", json.dumps(json_b, indent=2))
        system = MERGE_SYSTEM_PROMPT

        raw_response = None
        try:
            raw_response = self.provider.generate(prompt, system=system)
            merged_json = self.json_validator.parse_json(raw_response)
            if isinstance(merged_json, dict) and merged_json:
                merged_json = self.preserve_fields(merged_json, json_a, json_b)
                return self.post_process_deduplicate(merged_json)
        except Exception as e:
            logger.warning(f"LLM merge pairwise execution failed: {e}. Falling back to Python structural merge.")
            if raw_response is not None:
                try:
                    # Attempt repair with LLM only if we got a response
                    repaired = self.json_validator.repair_with_llm(raw_response, self.provider)
                    if isinstance(repaired, dict) and repaired:
                        repaired = self.preserve_fields(repaired, json_a, json_b)
                        return self.post_process_deduplicate(repaired)
                except Exception as rep_err:
                    logger.warning(f"LLM merge repair failed: {rep_err}. Using deterministic Python merge.")

        # Fallback to deterministic python merging if LLM fails
        return self.python_deterministic_merge(json_a, json_b)

    def preserve_fields(self, merged: Dict[str, Any], a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
        """
        Safety guard: Prevent loss of extracted records across LLM merges.
        If chunks a or b contained education, publications, or personal information
        that was lost/dropped during the merge, restore them.
        """
        if not isinstance(merged, dict):
            return merged

        # Personal Information
        p_m = merged.get("personal_information")
        if not isinstance(p_m, dict):
            p_m = {}
            merged["personal_information"] = p_m
        p_a = a.get("personal_information", {}) if isinstance(a.get("personal_information"), dict) else {}
        p_b = b.get("personal_information", {}) if isinstance(b.get("personal_information"), dict) else {}

        for k in ["full_name", "current_designation", "email", "phone"]:
            if not p_m.get(k):
                val = p_a.get(k) or p_b.get(k)
                if val:
                    p_m[k] = val

        # Education
        edu_m = merged.get("education") or []
        edu_a = a.get("education") or []
        edu_b = b.get("education") or []
        merged_deg_keys = {
            f"{(e.get('degree') or '').strip().lower()}:{(e.get('university') or '').strip().lower()}"
            for e in edu_m if isinstance(e, dict)
        }
        for src in (edu_a, edu_b):
            if isinstance(src, list):
                for item in src:
                    if isinstance(item, dict):
                        key = f"{(item.get('degree') or '').strip().lower()}:{(item.get('university') or '').strip().lower()}"
                        if key != ":" and key not in merged_deg_keys:
                            edu_m.append(item)
                            merged_deg_keys.add(key)
        merged["education"] = edu_m

        # Publications
        pub_m = merged.get("publications") or []
        pub_a = a.get("publications") or []
        pub_b = b.get("publications") or []
        merged_pub_keys = {
            (p.get("publication_name") or "").strip().lower()
            for p in pub_m if isinstance(p, dict) and p.get("publication_name")
        }
        for src in (pub_a, pub_b):
            if isinstance(src, list):
                for item in src:
                    if isinstance(item, dict):
                        pname = (item.get("publication_name") or "").strip().lower()
                        if pname and pname not in merged_pub_keys:
                            pub_m.append(item)
                            merged_pub_keys.add(pname)
        merged["publications"] = pub_m

        return merged

    def merge_all(self, json_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Hierarchically (pairwise) merge a list of partial JSON objects.
        """
        if not json_list:
            return {}
        if len(json_list) == 1:
            return self.post_process_deduplicate(json_list[0])

        print(f"[HIERARCHICAL-MERGE] Starting hierarchical merge of {len(json_list)} partial chunk outputs...", flush=True)
        logger.info(f"Hierarchically merging {len(json_list)} partial JSON objects...")
        current_level = json_list
        round_num = 0

        while len(current_level) > 1:
            round_num += 1
            next_level = []
            for i in range(0, len(current_level), 2):
                if i + 1 < len(current_level):
                    logger.debug(f"Merging pair at index {i} and {i+1}")
                    merged = self.merge_two(current_level[i], current_level[i+1])
                    next_level.append(merged)
                else:
                    # Odd element, carry forward to next round
                    next_level.append(current_level[i])
            print(f"[HIERARCHICAL-MERGE] Level {round_num}: Merged {len(current_level)} inputs -> {len(next_level)} intermediate outputs", flush=True)
            current_level = next_level

        final_result = current_level[0]
        deduped = self.post_process_deduplicate(final_result)
        print(f"[HIERARCHICAL-MERGE] ✓ Completed merge: Unified into consolidated candidate JSON.", flush=True)
        return deduped

    def post_process_deduplicate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deterministic deduplication & structural hygiene pass over candidate JSON.
        """
        if not isinstance(data, dict):
            return data

        # 1. Clean Personal Information
        p_info = data.get("personal_information", {})
        if not isinstance(p_info, dict):
            p_info = {}

        # 2. Deduplicate Education
        edu_list = data.get("education", [])
        if isinstance(edu_list, list):
            dedup_edu = []
            seen_edu = set()
            for item in edu_list:
                if not isinstance(item, dict):
                    continue
                deg = (item.get("degree") or "").strip().lower()
                uni = (item.get("university") or "").strip().lower()
                key = f"{deg}:{uni}"
                
                if key != ":" and key in seen_edu:
                    # Merge into existing record
                    for existing in dedup_edu:
                        ex_deg = (existing.get("degree") or "").strip().lower()
                        ex_uni = (existing.get("university") or "").strip().lower()
                        if f"{ex_deg}:{ex_uni}" == key:
                            for k, v in item.items():
                                if v and not existing.get(k):
                                    existing[k] = v
                else:
                    if key != ":":
                        seen_edu.add(key)
                    dedup_edu.append(item)
            data["education"] = dedup_edu

        # 3. Deduplicate Publications
        pub_list = data.get("publications", [])
        if isinstance(pub_list, list):
            dedup_pub = []
            seen_pub = set()
            for item in pub_list:
                if not isinstance(item, dict):
                    continue
                raw_name = (item.get("publication_name") or "").strip()
                if not raw_name:
                    continue
                import re
                norm_name = re.sub(r'[\s"\'“”.,:;]+', ' ', raw_name.lower()).strip()
                if norm_name and norm_name in seen_pub:
                    for existing in dedup_pub:
                        ex_norm = re.sub(r'[\s"\'“”.,:;]+', ' ', (existing.get("publication_name") or "").lower()).strip()
                        if ex_norm == norm_name:
                            for k, v in item.items():
                                if v is not None and not existing.get(k):
                                    existing[k] = v
                else:
                    if norm_name:
                        seen_pub.add(norm_name)
                    dedup_pub.append(item)
            data["publications"] = dedup_pub

        # 4. Deduplicate Experience
        exp = data.get("experience")
        from backend.app.llm.experience_calculator import clean_and_calculate_experience_dict
        cleaned_exp_dict, total_exp = clean_and_calculate_experience_dict(exp, raw_total_exp=data.get("total_experience"))
        data["experience"] = cleaned_exp_dict
        data["total_experience"] = total_exp
        return data

    def python_deterministic_merge(self, a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pure Python fallback for combining two partial candidate dictionaries safely.
        """
        res = {
            "personal_information": {},
            "education": [],
            "publications": [],
            "experience": [],
            "total_experience": 0.0
        }

        # Personal Info
        p_a = a.get("personal_information", {}) if isinstance(a.get("personal_information"), dict) else {}
        p_b = b.get("personal_information", {}) if isinstance(b.get("personal_information"), dict) else {}
        for key in ["full_name", "current_designation", "email", "phone"]:
            res["personal_information"][key] = p_a.get(key) or p_b.get(key) or None

        # Education
        ed_a = a.get("education", []) if isinstance(a.get("education"), list) else []
        ed_b = b.get("education", []) if isinstance(b.get("education"), list) else []
        res["education"] = ed_a + ed_b

        # Publications
        pub_a = a.get("publications", []) if isinstance(a.get("publications"), list) else []
        pub_b = b.get("publications", []) if isinstance(b.get("publications"), list) else []
        res["publications"] = pub_a + pub_b

        # Experience
        exp_a = a.get("experience")
        exp_b = b.get("experience")
        if isinstance(exp_a, list) or isinstance(exp_b, list):
            list_a = exp_a if isinstance(exp_a, list) else ((exp_a.get("academic") or []) + (exp_a.get("industry") or []) if isinstance(exp_a, dict) else [])
            list_b = exp_b if isinstance(exp_b, list) else ((exp_b.get("academic") or []) + (exp_b.get("industry") or []) if isinstance(exp_b, dict) else [])
            res["experience"] = list_a + list_b
        elif isinstance(exp_a, dict) or isinstance(exp_b, dict):
            dict_a = exp_a if isinstance(exp_a, dict) else {}
            dict_b = exp_b if isinstance(exp_b, dict) else {}
            res["experience"] = {
                "academic": (dict_a.get("academic") or []) + (dict_b.get("academic") or []),
                "professional": (dict_a.get("professional") or dict_a.get("industry") or []) + (dict_b.get("professional") or dict_b.get("industry") or [])
            }
        else:
            res["experience"] = {"academic": [], "professional": []}

        tot_a = float(a.get("total_experience") or 0.0)
        tot_b = float(b.get("total_experience") or 0.0)
        res["total_experience"] = max(tot_a, tot_b)

        return self.post_process_deduplicate(res)
