from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_create_alert_success():
    """Successful Alert Rule Creation"""
    payload = {
        "metric_name": "cpu_usage",
        "tags": {"host": "server1"},
        "field_name": "usage",
        "threshold": 80.0,
        "duration_value": 5,
        "duration_unit": "minutes",
        "comparison": ">",
        "use_recovery_alert": True,
        "recovery_time_value": 10,
        "recovery_time_unit": "minutes",
    }
    response = client.post("/alerts/", json=payload)
    assert response.status_code == 200
    assert "rule_id" in response.json()


def test_create_alert_no_tag():
    """Invalid Alert Rule (No Tags)"""
    payload = {
        "metric_name": "cpu_usage",
        "threshold": 80.0,
        "duration_value": 5,
        "duration_unit": "minutes",
        "comparison": ">",
        "use_recovery_alert": True,
        "recovery_time_value": 10,
        "recovery_time_unit": "minutes",
    }
    response = client.post("/alerts/", json=payload)
    assert response.status_code == 422


def test_create_alert_invalid_comparison():
    """Invalid Comparison Operator"""
    payload = {
        "metric_name": "cpu_usage",
        "tags": {"host": "server1"},
        "threshold": 80.0,
        "duration_value": 5,
        "duration_unit": "minutes",
        "comparison": "INVALID",  # Not allowed
        "use_recovery_alert": False,
    }
    response = client.post("/alerts/", json=payload)
    assert response.status_code == 422  # FastAPI should return validation error


def test_create_alert_invalid_duration():
    """Invalid Duration (Negative)"""
    payload = {
        "metric_name": "cpu_usage",
        "tags": {"host": "server1"},
        "threshold": 80.0,
        "duration_value": -5,  # Cannot be negative
        "duration_unit": "minutes",
        "comparison": ">",
        "use_recovery_alert": False,
    }
    response = client.post("/alerts/", json=payload)
    assert response.status_code == 422  # FastAPI validation error


def test_create_alert_invalid_recovery_time():
    """Invalid Recovery Time (Negative)"""
    payload = {
        "metric_name": "cpu_usage",
        "tags": {"host": "server1"},
        "field_name": "usage",
        "threshold": 80.0,
        "duration_value": 5,
        "duration_unit": "minutes",
        "comparison": ">",
        "use_recovery_alert": True,
        "recovery_time_value": -10,
        "recovery_time_unit": "minutes",
    }
    response = client.post("/alerts/", json=payload)
    assert response.status_code == 422


def test_create_alert_invalid_no_field_name():
    """Invalid no field_name"""
    payload = {
        "metric_name": "cpu_usage",
        "tags": {"host": "server1"},
        "threshold": 80.0,
        "duration_value": 5,
        "duration_unit": "minutes",
        "comparison": ">",
        "use_recovery_alert": True,
        "recovery_time_value": -10,
        "recovery_time_unit": "minutes",
    }
    response = client.post("/alerts/", json=payload)
    assert response.status_code == 422


def test_create_alert_default_values():
    """Default Values for Notification Channels & Recipients"""
    payload = {
        "metric_name": "memory_usage",
        "tags": {"host": "server1"},
        "field_name": "usage",
        "threshold": 75.0,
        "duration_value": 3,
        "duration_unit": "minutes",
        "comparison": "<",
        "use_recovery_alert": False,
    }
    response = client.post("/alerts/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "rule_id" in data

    # Retrieve the created alert rule to check default values
    rule_id = data["rule_id"]
    get_response = client.get("/alerts/")
    assert get_response.status_code == 200
    print(get_response.json())
    rules = get_response.json()["alert_rules"]
    rule = next((r for r in rules if str(r.get("_id", "")) == rule_id), None)
    assert rule is not None
    assert rule["notification_channels"] == ["telegram"]
    assert rule["recipients"] == {}  # Default


def test_get_alert_by_id():
    """Retrieve a single alert rule by its ID"""
    payload = {
        "metric_name": "cpu_usage",
        "field_name": "usage",
        "tags": {"host": "server1"},
        "threshold": 80.0,
        "duration_value": 5,
        "duration_unit": "minutes",
        "comparison": ">",
        "use_recovery_alert": True,
        "recovery_time_value": 10,
        "recovery_time_unit": "minutes",
    }
    create_response = client.post("/alerts/", json=payload)
    assert create_response.status_code == 200
    data = create_response.json()
    assert "rule_id" in data

    rule_id = data["rule_id"]

    # Retrieve the created alert rule
    get_response = client.get(f"/alerts/{rule_id}")
    assert get_response.status_code == 200
    rule_data = get_response.json()

    # Check that the response contains correct data
    assert rule_data["metric_name"] == payload["metric_name"]
    assert rule_data["tags"] == payload["tags"]
    assert rule_data["field_name"] == payload["field_name"]
    assert rule_data["threshold"] == payload["threshold"]
    assert rule_data["comparison"] == payload["comparison"]
    assert rule_data["use_recovery_alert"] == payload["use_recovery_alert"]
    assert rule_data["notification_channels"] == ["telegram"]  # Default
    assert rule_data["recipients"] == {}  # Default

    # non-existing alert rule
    invalid_response = client.get("/alerts/invalid_rule_id")
    assert invalid_response.status_code == 404
    assert invalid_response.json()["detail"] == "Alert rule not found"


def test_delete_alert_by_id():
    """Delete single alert rule by its ID"""
    payload = {
        "metric_name": "cpu_usage",
        "tags": {"host": "server1"},
        "field_name": "usage",
        "threshold": 80.0,
        "duration_value": 5,
        "duration_unit": "minutes",
        "comparison": ">",
        "use_recovery_alert": True,
        "recovery_time_value": 10,
        "recovery_time_unit": "minutes",
    }
    create_response = client.post("/alerts/", json=payload)
    assert create_response.status_code == 200
    data = create_response.json()
    assert "rule_id" in data

    rule_id = data["rule_id"]

    # Retrieve the created alert rule
    get_response = client.delete(f"/alerts/{rule_id}")
    assert get_response.status_code == 200

    # Check that the rule was deleted
    get_response = client.get(f"/alerts/{rule_id}")
    assert get_response.status_code == 404
    assert get_response.json()["detail"] == "Alert rule not found"
