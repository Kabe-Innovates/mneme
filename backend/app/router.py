import json
import os
from typing import Optional

_rules: list[dict] = []

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def load_routing_rules():
    global _rules
    path = os.path.join(DATA_DIR, "routing_rules.json")
    with open(path) as f:
        _rules = json.load(f)
    print(f"[Router] Loaded {len(_rules)} routing rules")


def find_route(issue_type: str, entities: dict) -> Optional[dict]:
    if not _rules:
        return None

    amount = entities.get("amount") or 0

    # Find best matching rule
    for rule in _rules:
        rule_issue = rule.get("issue_type", "")
        if rule_issue == issue_type or rule_issue == "general_operational":
            conditions = rule.get("conditions", "any").lower()

            # Evaluate simple conditions
            if conditions == "any":
                return rule
            if ">" in conditions and "amount" in conditions:
                try:
                    threshold = float(conditions.split(">")[1].strip())
                    if float(amount) > threshold:
                        return rule
                except (ValueError, IndexError):
                    return rule
            if "<=" in conditions and "amount" in conditions:
                try:
                    threshold = float(conditions.split("<=")[1].strip())
                    if float(amount) <= threshold:
                        return rule
                except (ValueError, IndexError):
                    pass
            else:
                return rule

    # Fallback: return general_operational rule
    for rule in _rules:
        if rule.get("issue_type") == "general_operational":
            return rule

    return None
