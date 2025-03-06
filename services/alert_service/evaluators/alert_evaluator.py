import logging
from typing import List, Callable, Dict
from models import AlertRuleSchema

logger = logging.getLogger(__name__)


class AlertEvaluator:
    """Evaluates metric values against alert rules to determine if an alert should be triggered."""

    COMPARISON_OPERATORS: Dict[str, Callable[[float, float], bool]] = {
        ">": lambda v, t: v > t,
        "<": lambda v, t: v < t,
        "==": lambda v, t: v == t,
        ">=": lambda v, t: v >= t,
        "<=": lambda v, t: v <= t,
        "!=": lambda v, t: v != t,
    }

    @staticmethod
    def evaluate(comparison: str, threshold: float, metric_values: List[float]) -> bool:
        """Determines if an alert should be triggered based on metric values and the alert condition."""
        if comparison not in AlertEvaluator.COMPARISON_OPERATORS:
            logger.error(f"Unknown comparison operator: {comparison}. No alert triggered.")
            return False

        if not metric_values:
            logger.info("No metric values available. No alert triggered.")
            return False

        metric_values = [float(v) for v in metric_values if isinstance(v, (int, float))]
        if not metric_values:
            logger.warning("All metric values were invalid. No alert triggered.")
            return False

        comparator = AlertEvaluator.COMPARISON_OPERATORS[comparison]
        result = all(comparator(value, threshold) for value in metric_values)

        logger.info(
            f"Evaluating condition: `{comparison}` against threshold {threshold} | "
            f"Values: {metric_values} | Result: {'Triggered' if result else 'Not Triggered'}"
        )

        return result

    @staticmethod
    def from_alert_rule(alert_rule: AlertRuleSchema, metric_values: List[float]) -> bool:
        """Extracts condition and threshold from `AlertRuleSchema` and evaluates the alert."""
        return AlertEvaluator.evaluate(
            comparison=alert_rule.comparison,
            threshold=alert_rule.threshold,
            metric_values=metric_values,
        )
