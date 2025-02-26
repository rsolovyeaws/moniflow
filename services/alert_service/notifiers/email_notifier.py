from .notifier import Notifier
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailNotifier(Notifier):
    """
    A notifier class to send alert notifications via email.
    Attributes:
        smtp_server (str): The SMTP server address.
        smtp_port (int): The SMTP server port.
        sender_email (str): The sender's email address.
        sender_password (str): The sender's email password.
    Methods:
        send_alert(message: str, recipients: list):
            Sends an alert message to the specified recipients via email.
            Args:
                message (str): The alert message to be sent.
                recipients (list): A list of recipient email addresses.
    """
    
    def __init__(self):
        pass

    def send_alert(self, message: str, recipients: list):
        pass
