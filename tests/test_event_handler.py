import logging
from src.config import AgentConfig
from src.aas_operation_service import AasOperationService
from src.event_listener import EventListener
from src.event_handler import EventHandler

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
# testet die EventHandler-Logik und einfachen AAS-Operationen mit realen Mqtt-Nachrichten

config = AgentConfig()
service = AasOperationService(config.aas)
handler = EventHandler(service)
listener = EventListener(config.mqtt, on_message=handler.handle)
listener.start()

print("Warte auf MQTT-Nachrichten...")
# print("Bekannte idShorts:", list(AgentConfig.topic_operation_map.keys()))
print()

input("Drücke Enter zum Beenden...\n")
listener.stop()

