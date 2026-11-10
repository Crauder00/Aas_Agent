"""Deterministic scheduling checks and threaded lifecycle integration tests."""

from concurrent.futures import Future
import threading
import unittest
from unittest.mock import Mock, patch

from aas_agent import AasAgent, AgentConfig, BaseOperationService, GuardResult
from aas_agent.core.operation_scheduler import OperationScheduler


class DeferredExecutor:
    """Hold a submitted invocation until the test explicitly runs it."""

    def __init__(self):
        self.calls = []

    def submit(self, method, *args):
        future = Future()
        self.calls.append((future, method, args))
        return future

    def run_next(self):
        future, method, args = self.calls.pop(0)
        if future.set_running_or_notify_cancel():
            future.set_result(method(*args))

    def shutdown(self, **kwargs):
        for future, _, _ in self.calls:
            future.cancel()


class OperationSchedulerTests(unittest.TestCase):
    def setUp(self):
        self.now = 0.0
        self.service = BaseOperationService()
        self.method = Mock(__name__="read_batteries")

    def scheduler(self, **options):
        self.service.register_periodic(self.method, 300, **options)
        scheduler = OperationScheduler([self.service], clock=lambda: self.now)
        self.addCleanup(scheduler.stop)
        job = scheduler._jobs[0]
        job.next_due = 300
        job.executor = DeferredExecutor()
        return scheduler, job

    def tick(self, scheduler, now):
        self.now = now
        scheduler._dispatch_due(now)

    def test_first_call_after_full_interval_and_no_runtime_drift(self):
        scheduler, job = self.scheduler()
        self.tick(scheduler, 299)
        self.assertFalse(job.executor.calls)
        self.tick(scheduler, 300)
        self.now = 340  # Simulate a worker which takes time to start.
        job.executor.run_next()
        self.method.assert_called_once_with()
        self.assertEqual(job.next_due, 600)
        self.tick(scheduler, 600)
        job.executor.run_next()
        self.assertEqual(self.method.call_count, 2)
        self.assertEqual(job.next_due, 900)

    def test_soft_missed_intervals_coalesce_without_catchup_burst(self):
        scheduler, job = self.scheduler()
        with self.assertLogs("aas_agent.core.operation_scheduler", "WARNING"):
            self.tick(scheduler, 1000)
        self.assertEqual(len(job.executor.calls), 1)
        job.executor.run_next()
        self.method.assert_called_once()
        self.assertEqual(job.next_due, 1200)

    def test_pending_or_running_invocations_never_overlap(self):
        scheduler, job = self.scheduler()
        self.tick(scheduler, 300)
        with self.assertLogs("aas_agent.core.operation_scheduler", "WARNING"):
            self.tick(scheduler, 600)
        self.assertEqual(len(job.executor.calls), 1)
        job.executor.run_next()
        self.tick(scheduler, 900)
        job.executor.run_next()
        self.assertEqual(self.method.call_count, 2)

    def test_hard_late_call_is_skipped_at_actual_worker_start(self):
        scheduler, job = self.scheduler(timing="hard", max_lateness_seconds=2)
        self.tick(scheduler, 300)
        self.now = 303
        with self.assertLogs("aas_agent.core.operation_scheduler", "ERROR"):
            job.executor.run_next()
        self.method.assert_not_called()
        self.tick(scheduler, 600)
        job.executor.run_next()
        self.method.assert_called_once()

    def test_hard_late_policy_run_logs_and_executes(self):
        scheduler, job = self.scheduler(
            timing="hard", max_lateness_seconds=2, late_policy="run"
        )
        self.tick(scheduler, 305)
        with self.assertLogs("aas_agent.core.operation_scheduler", "ERROR"):
            job.executor.run_next()
        self.method.assert_called_once()

    def test_soft_late_call_warns_but_still_runs(self):
        scheduler, job = self.scheduler(max_lateness_seconds=2)
        self.tick(scheduler, 305)
        with self.assertLogs("aas_agent.core.operation_scheduler", "WARNING"):
            job.executor.run_next()
        self.method.assert_called_once()

    def test_hard_busy_and_missed_intervals_are_errors(self):
        scheduler, job = self.scheduler(timing="hard", max_lateness_seconds=2)
        self.tick(scheduler, 300)
        with self.assertLogs("aas_agent.core.operation_scheduler", "ERROR") as logs:
            self.tick(scheduler, 1200)
        self.assertEqual(len(logs.output), 2)
        self.assertEqual(len(job.executor.calls), 1)

    def test_guard_blocks_then_allows_next_interval(self):
        guard = Mock(return_value=GuardResult(False, "not ready"))
        scheduler, job = self.scheduler(guard=guard)
        self.tick(scheduler, 300)
        job.executor.run_next()
        self.method.assert_not_called()
        guard.return_value = GuardResult(True)
        self.tick(scheduler, 600)
        job.executor.run_next()
        self.method.assert_called_once()

    def test_guard_time_is_part_of_start_lateness(self):
        def guard():
            self.now += 5
            return GuardResult(True)

        scheduler, job = self.scheduler(
            timing="hard", max_lateness_seconds=2, guard=guard
        )
        self.tick(scheduler, 300)
        with self.assertLogs("aas_agent.core.operation_scheduler", "ERROR"):
            job.executor.run_next()
        self.method.assert_not_called()

    def test_method_and_guard_exceptions_do_not_disable_next_interval(self):
        for source in ("method", "guard"):
            with self.subTest(source=source):
                self.service = BaseOperationService()
                self.method = Mock(__name__="read_batteries")
                guard = Mock(return_value=GuardResult(True))
                failing = self.method if source == "method" else guard
                failing.side_effect = RuntimeError("temporary failure")
                scheduler, job = self.scheduler(guard=guard)
                self.tick(scheduler, 300)
                with self.assertLogs("aas_agent.core.operation_scheduler", "ERROR"):
                    job.executor.run_next()
                failing.side_effect = None
                self.tick(scheduler, 600)
                job.executor.run_next()
                self.assertEqual(self.method.call_count, 2 if source == "method" else 1)

    def test_stop_cancels_pending_calls_and_prevents_new_dispatch(self):
        scheduler, job = self.scheduler()
        self.tick(scheduler, 300)
        scheduler.stop()
        job.executor.run_next()
        self.tick(scheduler, 600)
        self.method.assert_not_called()
        self.assertFalse(job.executor.calls)

    def test_validation_rejects_invalid_configurations(self):
        options = [
            {"interval_seconds": value} for value in (0, -1, float("nan"), float("inf"))
        ] + [
            {"timing": "invalid"},
            {"timing": "hard"},
            {"max_lateness_seconds": -1},
            {"max_lateness_seconds": float("nan")},
            {"max_lateness_seconds": float("inf")},
            {"overlap": "allow"},
            {"late_policy": "invalid"},
        ]
        for option in options:
            with self.subTest(option=option), self.assertRaises(ValueError):
                self.service.register_periodic(
                    self.method, **({"interval_seconds": 300} | option)
                )
        self.assertEqual(self.service.get_periodic_operations(), ())

    def test_rejects_required_arguments_async_and_duplicate_methods(self):
        async def asynchronous():
            pass

        def needs_payload(payload):
            pass

        for method in (asynchronous, needs_payload, 42, None):
            with self.subTest(method=method), self.assertRaises(ValueError):
                self.service.register_periodic(method, 300)
        self.service.register_periodic(self.method, 300)
        with self.assertRaisesRegex(ValueError, "already registered"):
            self.service.register_periodic(self.method, 600)

    def test_event_and_periodic_registries_are_independent(self):
        self.service.register(self.method, "battery")
        self.service.register_periodic(self.method, 300)
        self.assertEqual(len(self.service.get_registry()), 1)
        self.assertEqual(len(self.service.get_periodic_operations()), 1)

    def test_stop_requested_during_guard_prevents_method_call(self):
        def guard():
            scheduler.request_stop()
            return GuardResult(True)

        scheduler, job = self.scheduler(guard=guard)
        self.tick(scheduler, 300)
        job.executor.run_next()
        self.method.assert_not_called()

    def test_exact_hard_deadline_is_still_allowed(self):
        scheduler, job = self.scheduler(timing="hard", max_lateness_seconds=2)
        self.tick(scheduler, 302)
        job.executor.run_next()
        self.method.assert_called_once()

    def test_start_anchors_each_service_instance_at_current_monotonic_time(self):
        class BatteryService(BaseOperationService):
            def __init__(self):
                super().__init__()
                self.calls = 0
                self.register_periodic(self.read_batteries, 300)

            def read_batteries(self):
                self.calls += 1

        first, second = BatteryService(), BatteryService()
        self.now = 125
        scheduler = OperationScheduler([first, second], clock=lambda: self.now)
        self.addCleanup(scheduler.stop)
        with patch("aas_agent.core.operation_scheduler.threading.Thread"):
            scheduler.start()
        self.assertEqual([job.next_due for job in scheduler._jobs], [425, 425])
        self.assertNotEqual(scheduler._jobs[0].name, scheduler._jobs[1].name)
        self.tick(scheduler, 425)
        for job in scheduler._jobs:
            job.future.result(timeout=2)
        self.assertEqual((first.calls, second.calls), (1, 1))


class SchedulerLifecycleTests(unittest.TestCase):
    def test_timer_only_agent_runs_without_event_infrastructure(self):
        called = threading.Event()
        service = BaseOperationService()
        service.register_periodic(called.set, 0.01)
        with (
            patch("aas_agent.aas_agent.EventListener") as listener,
            patch("aas_agent.aas_agent.EventHandler") as handler,
        ):
            agent = AasAgent(AgentConfig(event_mode="disabled"), [service])
            self.addCleanup(agent.stop)
            agent.start()
            timer = agent._scheduler._thread
            agent.start()
            self.assertIs(agent._scheduler._thread, timer)
            self.assertTrue(called.wait(2))
            agent.stop()
            agent.stop()
            listener.assert_not_called()
            handler.assert_not_called()
            self.assertFalse(timer.is_alive())
            with self.assertRaises(RuntimeError):
                agent.start()

    def test_blocked_job_does_not_block_other_jobs_and_stop_waits(self):
        entered = threading.Event()
        release = threading.Event()
        other_called = threading.Event()
        stopped = threading.Event()

        def blocking():
            entered.set()
            release.wait(3)

        service = BaseOperationService()
        service.register_periodic(blocking, 0.01)
        service.register_periodic(
            other_called.set, 0.01, timing="hard", max_lateness_seconds=1
        )
        scheduler = OperationScheduler([service])
        self.addCleanup(scheduler.stop)
        self.addCleanup(release.set)
        scheduler.start()
        self.assertTrue(entered.wait(2))
        self.assertTrue(other_called.wait(2))

        def stop():
            scheduler.stop()
            stopped.set()

        stopper = threading.Thread(target=stop)
        stopper.start()
        try:
            self.assertTrue(scheduler._stop.wait(2))
            self.assertFalse(stopped.is_set())
        finally:
            release.set()
            stopper.join(3)
        self.assertTrue(stopped.is_set())

    def test_default_agent_still_starts_and_stops_event_listener(self):
        with patch("aas_agent.aas_agent.EventListener") as listener:
            agent = AasAgent(AgentConfig(), [])
            self.addCleanup(agent._handler.close)
            self.addCleanup(agent.stop)
            agent.start()
            listener.return_value.start.assert_called_once()
            agent.stop()
            listener.return_value.stop.assert_called_once()

    def test_start_failure_closes_scheduler_and_event_source(self):
        with patch("aas_agent.aas_agent.EventListener") as listener:
            agent = AasAgent(AgentConfig(), [])
            self.addCleanup(agent._handler.close)
            listener.return_value.start.side_effect = RuntimeError("broker unavailable")
            with self.assertRaisesRegex(RuntimeError, "broker unavailable"):
                agent.start()
            self.assertTrue(agent._scheduler._closed)
            listener.return_value.stop.assert_called_once()

    def test_invalid_event_mode_fails_early(self):
        with self.assertRaisesRegex(ValueError, "event_mode"):
            AgentConfig(event_mode="invalid")


if __name__ == "__main__":
    unittest.main()
