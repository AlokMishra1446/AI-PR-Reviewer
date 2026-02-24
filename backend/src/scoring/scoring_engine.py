from typing import Any, Dict, List


def clamp_score(value: float, minimum: float = 0.0, maximum: float = 10.0) -> float:
    return max(minimum, min(maximum, value))


def compute_rule_compliance(rule_result: Dict[str, Any]) -> float:
    violations = rule_result.get("rule_violations", [])
    if not violations:
        return 10.0
    critical_count = sum(1 for v in violations if v.get("severity") == "Critical")
    major_count = sum(1 for v in violations if v.get("severity") == "Major")
    minor_count = sum(1 for v in violations if v.get("severity") == "Minor")
    base = 10.0
    penalty = critical_count * 2.5 + major_count * 1.5 + minor_count * 0.5
    return clamp_score(base - penalty)


def compute_overall_scores(rule_result: Dict[str, Any], expert_result: Dict[str, Any]) -> Dict[str, float]:
    scores = expert_result.get("scores", {})
    performance = float(scores.get("performance", 5.0))
    scalability = float(scores.get("scalability", 5.0))
    security = float(scores.get("security", 5.0))
    maintainability = float(scores.get("maintainability", 5.0))
    readability = float(scores.get("readability", 5.0))
    bug_risk = float(scores.get("bug_risk", 5.0))
    rule_compliance = compute_rule_compliance(rule_result)
    performance = clamp_score(performance)
    scalability = clamp_score(scalability)
    security = clamp_score(security)
    maintainability = clamp_score(maintainability)
    readability = clamp_score(readability)
    bug_risk = clamp_score(bug_risk)
    weights = {
        "performance": 1.0,
        "scalability": 1.0,
        "security": 1.5,
        "maintainability": 1.2,
        "readability": 0.8,
        "bug_risk": 1.5,
        "rule_compliance": 1.0,
    }
    weighted_sum = (
        performance * weights["performance"]
        + scalability * weights["scalability"]
        + security * weights["security"]
        + maintainability * weights["maintainability"]
        + readability * weights["readability"]
        + (10 - bug_risk) * weights["bug_risk"]
        + rule_compliance * weights["rule_compliance"]
    )
    total_weight = sum(weights.values())
    overall_score = clamp_score(weighted_sum / total_weight)
    return {
        "performance": performance,
        "scalability": scalability,
        "security": security,
        "maintainability": maintainability,
        "readability": readability,
        "bug_risk": bug_risk,
        "rule_compliance": rule_compliance,
        "overall_score": overall_score,
    }

