from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from database import create_alert_rule
from notifiers.telegram_notifier import TelegramNotifier

app = FastAPI()

class AlertRuleCreate(BaseModel):
    metric_name: str
    threshold: float
    duration: int
    comparison: str
    notification_channels: list
    recipients: dict

@app.get("/")
async def root():
    return {"message": "Alert Service Running"}

# @app.post("/alerts/")
# def create_alert(rule: AlertRuleCreate):
#     rule_id = create_alert_rule(**rule.dict())
#     return {"message": "Alert rule created", "rule_id": str(rule_id)}

@app.get("/bot-test/")
async def send_bot_message():
    notifier = TelegramNotifier()
    response = await notifier.send_alert("Hello, this is a test message")
    return {"message": "Test message sent"}

# @app.get("/alerts/")
# def get_alerts():
#     return list(alert_rules.find({}, {"_id": 0}))

# @app.delete("/alerts/{rule_id}")
# def delete_alert(rule_id: str):
#     result = alert_rules.delete_one({"_id": rule_id})
#     if result.deleted_count == 0:
#         raise HTTPException(status_code=404, detail="Alert rule not found")
#     return {"message": "Alert rule deleted"}
