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

        try:
            raw_response = self.provider.generate(prompt, system=system)
            merged_json = self.json_validator.parse_json(raw_response)
            if isinstance(merged_json, dict):
                return self.post_process_deduplicate(merged_json)
        except Exception as e:
            logger.warning(f"LLM merge pairwise execution failed: {e}. Falling back to Python structural merge.")
            try:
                # Attempt repair with LLM
                repaired = self.json_validator.repair_with_llm(raw_response, self.provider)
                if isinstance(repaired, dict):
                    return self.post_process_deduplicate(repaired)
            except Exception as rep_err:
                logger.warning(f"LLM merge repair failed: {rep_err}. Using deterministic Python merge.")

        # Fallback to deterministic python merging if LLM fails
        return self.python_deterministic_merge(json_a, json_b)

    def merge_all(self, json_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Hierarchically (pairwise) merge a list of partial JSON objects.
        """
        if not json_list:
            return {}
        if len(json_list) == 1:
            return self.post_process_deduplicate(json_list[0])

        logger.info(f"Hierarchically merging {len(json_list)} partial JSON objects...")
        current_level = json_list

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                if i + 1 < len(current_level):
                    logger.debug(f"Merging pair at index {i} and {i+1}")
                    merged = self.merge_two(current_level[i], current_level[i+1])
                    next_level.append(merged)
                else:
                    # Odd element, carry forward to next round
                    next_level.append(current_level[i])
            current_level = next_level

        final_result = current_level[0]
        return self.post_process_deduplicate(final_result)

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
                name = (item.get("publication_name") or "").strip().lower()
                if name and name in seen_pub:
                    for existing in dedup_pub:
                        ex_name = (existing.get("publication_name") or "").strip().lower()
                        if ex_name == name:
                            for k, v in item.items():
                                if v and not existing.get(k):
                                    existing[k] = v
                else:
                    if name:
                        seen_pub.add(name)
                    dedup_pub.append(item)
            data["publications"] = dedup_pub

        # 4. Deduplicate Experience
        exp = data.get("experience", {})
        if isinstance(exp, dict):
            # Academic
            acad_list = exp.get("academic", [])
            if isinstance(acad_list, list):
                dedup_acad = []
                seen_acad = set()
                for item in acad_list:
                    if not isinstance(item, dict):
                        continue
                    inst = (item.get("institution") or "").strip().lower()
                    role = (item.get("role") or "").strip().lower()
                    key = f"{inst}:{role}"
                    if key != ":" and key in seen_acad:
                        for existing in dedup_acad:
                            if f"{(existing.get('institution') or '').strip().lower()}:{(existing.get('role') or '').strip().lower()}" == key:
                                for k, v in item.items():
                                    if v and not existing.get(k):
                                        existing[k] = v
                    else:
                        if key != ":":
                            seen_acad.add(key)
                        dedup_acad.append(item)
                exp["academic"] = dedup_acad

            # Industry
            ind_list = exp.get("industry", [])
            if isinstance(ind_list, list):
                dedup_ind = []
                seen_ind = set()
                for item in ind_list:
                    if not isinstance(item, dict):
                        continue
                    org = (item.get("organization") or "").strip().lower()
                    role = (item.get("role") or "").strip().lower()
                    key = f"{org}:{role}"
                    if key != ":" and key in seen_ind:
                        for existing in dedup_ind:
                            if f"{(existing.get('organization') or '').strip().lower()}:{(existing.get('role') or '').strip().lower()}" == key:
                                for k, v in item.items():
                                    if v and not existing.get(k):
                                        existing[k] = v
                    else:
                        if key != ":":
                            seen_ind.add(key)
                        dedup_ind.append(item)
                exp["industry"] = dedup_ind

        return data

    def python_deterministic_merge(self, a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pure Python fallback for combining two partial candidate dictionaries safely.
        """
        res = {
            "personal_information": {},
            "education": [],
            "publications": [],
            "experience": {
                "academic": [],
                "industry": []
            }
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
        exp_a = a.get("experience", {}) if isinstance(a.get("experience"), dict) else {}
        exp_b = b.get("experience", {}) if isinstance(b.get("experience"), dict) else {}
        
        acad_a = exp_a.get("academic", []) if isinstance(exp_a.get("academic"), list) else []
        acad_b = exp_b.get("academic", []) if isinstance(exp_b.get("academic"), list) else []
        res["experience"]["academic"] = acad_a + acad_b

        ind_a = exp_a.get("industry", []) if isinstance(exp_a.get("industry"), list) else []
        ind_b = exp_b.get("industry", []) if isinstance(exp_b.get("industry"), list) else []
        res["experience"]["industry"] = ind_a + ind_b

        return self.post_process_deduplicate(res)
