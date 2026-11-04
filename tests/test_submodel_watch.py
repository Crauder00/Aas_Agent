"""Regression tests for operation paths split across submodel watches."""

import unittest
from unittest.mock import Mock, patch

from aas_agent.config.listener_config import SubmodelWatch
from aas_agent.core.base_operation_service import BaseOperationService
from aas_agent.core.event_handler import EventHandler


class SubmodelWatchTests(unittest.TestCase):
    def setUp(self):
        self.handler = EventHandler()
        self.addCleanup(self.handler.close)
        self.service = BaseOperationService()
        self.operations = {}
        for path in ("Red_parts", "min_number_red_parts", "min_battery_allowed"):
            operation = Mock(__name__=path)
            self.service.register(operation, topic=path)
            self.operations[path] = operation
        self.handler.register_service(self.service)
        self.repository = patch(
            "aas_agent.core.event_handler.SubmodelRepository"
        ).start()
        self.addCleanup(patch.stopall)

    def watch(self, submodel="storage", topics=None, service=None):
        return SubmodelWatch(
            base_url="http://localhost:8082",
            submodel_id=submodel,
            services=[service if service is not None else self.service],
            operation_topics=topics,
        )

    def test_one_service_reads_and_dispatches_only_selected_submodel_paths(self):
        storage = Mock()
        agv = Mock()
        storage.get_value.return_value = "9"
        agv.get_value.return_value = "20"
        self.repository.side_effect = [storage, agv]
        self.handler.configure_watches(
            [
                self.watch(topics=["Red_parts", "min_number_red_parts"]),
                self.watch("agv", ["min_battery_allowed"]),
            ]
        )

        self.handler.initialize_watches()
        for operation in self.operations.values():
            operation.assert_not_called()

        storage.get_value.return_value = "10"
        agv.get_value.return_value = "21"
        self.handler.request_refresh()
        self.handler.close()

        self.assertEqual(
            [call.args[0] for call in storage.get_value.call_args_list],
            ["Red_parts", "min_number_red_parts"] * 2,
        )
        self.assertEqual(
            [call.args[0] for call in agv.get_value.call_args_list],
            ["min_battery_allowed"] * 2,
        )
        self.operations["Red_parts"].assert_called_once_with('{"value": "10"}')
        self.operations["min_number_red_parts"].assert_called_once_with(
            '{"value": "10"}'
        )
        self.operations["min_battery_allowed"].assert_called_once_with(
            '{"value": "21"}'
        )

    def test_omitted_filter_keeps_all_registered_paths(self):
        self.handler.configure_watches([self.watch()])
        self.handler.initialize_watches()
        self.assertEqual(
            [
                call.args[0]
                for call in self.repository.return_value.get_value.call_args_list
            ],
            list(self.operations),
        )

    def test_unknown_or_wrong_case_paths_fail_before_creating_repository(self):
        for topics in (["missing"], ["red_parts"]):
            with (
                self.subTest(topics=topics),
                self.assertRaisesRegex(ValueError, "not registered"),
            ):
                self.handler.configure_watches([self.watch(topics=topics)])
        self.repository.assert_not_called()

    def test_empty_filter_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "requires registered operation paths"):
            self.handler.configure_watches([self.watch(topics=[])])
        self.repository.assert_not_called()

    def test_filter_cannot_select_paths_from_other_services(self):
        other_service = BaseOperationService()
        other_service.register(Mock(__name__="other"), topic="Other")
        self.handler.register_service(other_service)
        with self.assertRaisesRegex(ValueError, "not registered"):
            self.handler.configure_watches([self.watch(topics=["Other"])])

    def test_unregistered_service_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "must be registered"):
            self.handler.configure_watches([self.watch(service=BaseOperationService())])

    def test_duplicate_repository_submodel_is_rejected(self):
        self.handler.configure_watches([self.watch(topics=["Red_parts"])])
        with self.assertRaisesRegex(ValueError, "one SubmodelWatch"):
            self.handler.configure_watches(
                [self.watch(topics=["min_number_red_parts"])]
            )


if __name__ == "__main__":
    unittest.main()
