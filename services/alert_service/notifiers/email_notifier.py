import smtplib
from email.mime.text import MIMEText
from .notifier import Notifier

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
    
    def __init__(self, smtp_server, smtp_port, sender_email, sender_password):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password

    def send_alert(self, message: str, recipients: list):
        msg = MIMEText(message)
        msg["Subject"] = "🚨 Alert Notification 🚨"
        msg["From"] = self.sender_email
        msg["To"] = ", ".join(recipients)

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, recipients, msg.as_string())
        except Exception as e:
            print(f"Email sending failed: {e}")
