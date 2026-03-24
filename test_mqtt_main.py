from src.config import AgentConfig
from src.event_listener import EventListener

def dummy_handler(topic: str, payload: str) -> None:
    print(f"Topic: {topic}")
    print(f"Payload: {payload}")

config = AgentConfig()
listener = EventListener(config.mqtt, on_message=dummy_handler)
listener.start()

input("Drücke Enter zum Beenden...\n")
listener.stop()