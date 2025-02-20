from .notifier import Notifier
from telegram import Bot
from dotenv import load_dotenv
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")


class TelegramNotifier(Notifier):
    def __init__(self):
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        
    async def send_alert(self, message: str):
        try:
            # logger.info(f"TELEGRAM_BOT_TOKEN: {TELEGRAM_BOT_TOKEN}, CHANNEL_ID: {CHANNEL_ID}, Sending Telegram alert: {message}")
            response = await self.bot.send_message(chat_id=CHANNEL_ID, text=message)
            logger.info(f"Telegram alert sent: {response}")
            return response
        except Exception as e:
            logger.error(f"Telegram alert sending failed: {e}")