"""registration_service_config.py - Configuration dataclass for the Registration Service."""

from dataclasses import dataclass


@dataclass
class RegisterConfig:
    """Configuration for the Registration Service.

    Attributes:
        mainserver_url: The URL of the main server. Defaults to a standard URL.
        base_url: The base URL for the registration service. Defaults to "http://localhost:8081".
    """
    mainserver_url:  str = "http://<MainServerURL>:8081"
    base_url: str = "http://localhost:8081"
