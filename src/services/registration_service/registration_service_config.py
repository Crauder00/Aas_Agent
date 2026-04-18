from dataclasses import dataclass

@dataclass
class RegisterConfig:
    """Referenz zwischen lokalem und Hauptserver für eine Anmeldung in der Shell Description"""
    mainserver_url:  str = "http://<MainServerURL>:8081"
    base_url: str = "http://localhost:8081"
    