from abc import ABC, abstractmethod

class Notifier(ABC):
    @abstractmethod
    def send_alert(self, message: str, recipients: list):
        pass
