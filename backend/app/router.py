import json
import os
import re
from typing import Optional

_rules: list[dict] = []

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

_CONDITION_RE = re.compile(
    r"^\s*(\w+)\s*(>=|<=|>|<|=)\s*(.+?)\s*$"
)


def load_routing_rules():
    global _rules
    path = os.path.join(DATA_DIR, "routing_rules.json")
    with open(path) as f:
        _rules = json.load(f)
    print(f"[Router] Loaded {len(_rules)} routing rules")


def _evaluate_condition(conditions: str, entities: dict) -> bool:
    """
    Evaluate a routing rule condition string against extracted entities.

    Supported formats:
      "any"                          → always True
      "billing_amount > 500"         → numeric comparison
      "billing_amount <= 500"        → numeric comparison
      "elevated_privileges = true"   → boolean/string equality
      "transfer_from = ICU"          → string equality
      "is_life_critical = true"      → boolean check
      "waiver_percentage > 25"       → numeric comparison

    If the field is not present in entities, the condition does NOT match.
    """
    cond = conditions.strip().lower()
    if cond == "any":
        return True

    m = _CONDITION_RE.match(conditions)
    if not m:
        return False

    field, operator, raw_value = m.group(1), m.group(2), m.group(3).strip()

    # Use "amount" as alias for any billing_amount-style field
    entity_value = entities.get(field) or entities.get("amount") if "amount" in field else entities.get(field)
    if entity_value is None:
        return False

    raw_value_lower = raw_value.lower()

    # Boolean check
    if raw_value_lower in ("true", "false"):
        if operator != "=":
            return False
        expected = raw_value_lower == "true"
        actual = str(entity_value).lower() in ("true", "1", "yes")
        return actual == expected

    # Numeric comparison
    try:
        threshold = float(raw_value)
        actual_num = float(entity_value)
        if operator == ">":
            return actual_num > threshold
        if operator == ">=":
            return actual_num >= threshold
        if operator == "<":
            return actual_num < threshold
        if operator == "<=":
            return actual_num <= threshold
        if operator == "=":
            return actual_num == threshold
    except (TypeError, ValueError):
        pass

    # String equality
    if operator == "=":
        return str(entity_value).strip().lower() == raw_value_lower

    return False


def find_route(issue_type: str, entities: dict) -> Optional[dict]:
    if not _rules:
        return None

    for rule in _rules:
        rule_issue = rule.get("issue_type", "")
        if rule_issue != issue_type and rule_issue != "general_operational":
            continue
        conditions = rule.get("conditions", "any")
        if _evaluate_condition(conditions, entities):
            return rule

    # Fallback: first general_operational rule with "any" condition
    for rule in _rules:
        if rule.get("issue_type") == "general_operational":
            if rule.get("conditions", "any").lower() == "any":
                return rule

    return None
