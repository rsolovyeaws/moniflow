import pytest
from evaluators.alert_evaluator import AlertEvaluator
from models import AlertRuleSchema


@pytest.mark.parametrize(
    "metric_values, comparison, threshold, expected_result",
    [
        # ✅ Basic Threshold Checks
        ([90.0, 92.5, 95.1], ">", 85.0, True),  # All values above threshold
        ([80.0, 85.0, 90.0], ">", 85.0, False),  # Not all values exceed threshold
        ([70.0, 60.0, 50.0], "<", 75.0, True),  # All values below threshold
        ([75.0, 80.0, 85.0], "<", 75.0, False),  # Some values exceed threshold
        ([50.0, 50.0, 50.0], "==", 50.0, True),  # All values match threshold
        ([50.0, 60.0, 50.0], "==", 50.0, False),  # One value does not match
        # ✅ Edge Cases
        ([85.0, 85.0, 90.0], ">=", 85.0, True),  # Values meet/exceed threshold
        ([80.0, 85.0, 90.0], ">=", 85.0, False),  # Some values below threshold
        ([80.0, 82.0, 90.0], "!=", 85.0, True),  # No value matches threshold
        ([80.0, 85.0, 90.0], "!=", 85.0, False),  # One value matches threshold
        ([85.0, 85.0, 85.0], "!=", 85.0, False),  # All values match threshold
        # ✅ Single Value Checks
        ([85.0], ">", 80.0, True),
        ([75.0], "<", 80.0, True),
        ([85.0], "==", 85.0, True),
        ([85.0], "==", 80.0, False),
        # ✅ Float Precision
        ([85.0001, 85.0002, 85.0003], ">", 85.0, True),
        ([85.0001, 84.9999], "==", 85.0, False),
        # ✅ Empty or Invalid Lists
        ([], ">", 85.0, False),  # No data → No alert
        ([None, "invalid", 90.0], ">", 85.0, True),  # Only 90.0 should be considered
        ([None, "high", "error"], ">", 85.0, False),  # No valid floats → No alert
    ],
)
def test_evaluate_alert(metric_values, comparison, threshold, expected_result):
    """Test `evaluate` with different conditions."""
    result = AlertEvaluator.evaluate(comparison, threshold, metric_values)
    assert result == expected_result


def test_evaluate_alert_no_metrics():
    """Test evaluation when no metric values are available."""
    assert AlertEvaluator.evaluate(">", 85.0, []) is False


def test_evaluate_alert_invalid_comparison():
    """Test evaluation with an invalid comparison operator."""
    assert AlertEvaluator.evaluate("INVALID", 85.0, [90.0, 95.0, 100.0]) is False


def test_evaluate_alert_mixed_types():
    """Ensure non-numeric values are ignored and valid floats are considered."""
    assert AlertEvaluator.evaluate(">", 85.0, ["90", None, 95.5]) is True  # 95.5 is valid
    assert AlertEvaluator.evaluate(">", 85.0, ["high", None, "error"]) is False  # No valid floats


def test_evaluate_alert_from_alert_rule():
    """Test `from_alert_rule()` with valid alert rules."""
    alert_rule = AlertRuleSchema(
        metric_name="cpu_usage",
        tags={"host": "server-1"},
        field_name="usage",
        threshold=85.0,
        duration=300,  # ✅ 5 minutes in seconds
        comparison=">",
        use_recovery_alert=True,
        recovery_time=600,  # ✅ 10 minutes in seconds
        notification_channels=["telegram"],
        recipients={"telegram": ["@user1"]},
    )

    metric_values = [90.0, 92.5, 95.1]
    assert AlertEvaluator.from_alert_rule(alert_rule, metric_values) is True

    metric_values = [80.0, 85.0, 90.0]
    assert AlertEvaluator.from_alert_rule(alert_rule, metric_values) is False


def test_evaluate_alert_from_alert_rule_invalid():
    """Test `from_alert_rule()` with invalid data."""
    alert_rule = AlertRuleSchema(
        metric_name="cpu_usage",
        tags={"host": "server-1"},
        field_name="usage",
        threshold=85.0,
        duration=300,  # ✅ 5 minutes in seconds
        comparison=">",
        use_recovery_alert=True,
        recovery_time=600,  # ✅ 10 minutes in seconds
        notification_channels=["telegram"],
        recipients={"telegram": ["@user1"]},
    )

    assert AlertEvaluator.from_alert_rule(alert_rule, []) is False  # No metric values
    assert AlertEvaluator.from_alert_rule(alert_rule, ["invalid", None]) is False  # No valid floats
