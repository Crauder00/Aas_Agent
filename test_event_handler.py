import unittest
from unittest.mock import MagicMock, patch
from src.event_handler import EventHandler


class TestEventHandler(unittest.TestCase):

    def setUp(self):
        # AasOperationService wird gemockt — wir testen nur den Handler
        self.mock_service = MagicMock()
        self.handler = EventHandler(self.mock_service)

    # ── Bekannte Topics → Operation wird ausgelöst ────────

    def test_emissionfactor_löst_operation_aus(self):
        topic = (
            "sm-repository/sm-repo/submodels/"
            "aHR0cHM6Ly9leGFtcGxlLmNvbS9pZHMvc20vNTY1MF85MTM0XzQ5MzhfNDM0MA"
            "/submodelElements/emissionfactor/updated"
        )
        payload = '{"value": "0.059", "idShort": "emissionfactor"}'

        self.handler.handle(topic, payload)

        # Warten bis der Thread-Pool die Aufgabe ausgeführt hat
        self.handler._executor.shutdown(wait=True)
        self.mock_service.set_emission_factor.assert_called_once()

    def test_scope3proxy_löst_operation_aus(self):
        topic = self._make_topic("scope3proxy")
        self.handler.handle(topic, "{}")
        self.handler._executor.shutdown(wait=True)
        self.mock_service.set_scope3_proxy.assert_called_once()

    def test_triggeraggregation_löst_operation_aus(self):
        topic = self._make_topic("triggeraggregation")
        self.handler.handle(topic, "{}")
        self.handler._executor.shutdown(wait=True)
        self.mock_service.trigger_aggregation.assert_called_once()

    # ── Unbekannte Topics → werden ignoriert ──────────────

    def test_unbekanntes_element_wird_ignoriert(self):
        topic = self._make_topic("temperature")
        self.handler.handle(topic, "{}")
        self.handler._executor.shutdown(wait=True)
        # Kein Methode des Service darf aufgerufen worden sein
        self.mock_service.assert_not_called()

    def test_anderes_submodel_wird_ignoriert(self):
        topic = self._make_topic("pressure")
        self.handler.handle(topic, "{}")
        self.handler._executor.shutdown(wait=True)
        self.mock_service.assert_not_called()

    # ── Fehlerhafte Topics → kein Crash ──────────────────

    def test_kaputtes_topic_wirft_keinen_fehler(self):
        self.handler.handle("kaputtes/topic", "{}")
        self.handler._executor.shutdown(wait=True)
        self.mock_service.assert_not_called()

    def test_leeres_topic_wirft_keinen_fehler(self):
        self.handler.handle("", "{}")
        self.handler._executor.shutdown(wait=True)
        self.mock_service.assert_not_called()

    # ── Gross/Kleinschreibung ─────────────────────────────

    def test_grossschreibung_im_topic_wird_erkannt(self):
        # BaSyx könnte idShort gross schreiben: "EmissionFactor"
        topic = self._make_topic("EmissionFactor")
        self.handler.handle(topic, "{}")
        self.handler._executor.shutdown(wait=True)
        self.mock_service.set_emission_factor.assert_called_once()

    # ── Hilfsmethode ─────────────────────────────────────

    def _make_topic(self, id_short: str) -> str:
        """Baut ein gültiges Topic mit beliebigem idShort zusammen."""
        return (
            f"sm-repository/sm-repo/submodels/"
            f"aHR0cHM6Ly9leGFtcGxlLmNvbS9pZHMvc20vNTY1MF85MTM0XzQ5MzhfNDM0MA"
            f"/submodelElements/{id_short}/updated"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)