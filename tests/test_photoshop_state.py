import threading
import unittest

from services import photoshop_state
from backend.services.photoshop_state import PhotoshopExecutionState, cancel_execution, get_execution_state


class TestPhotoshopState(unittest.TestCase):
    def setUp(self):
        with photoshop_state._executions_guard:
            photoshop_state._executions.clear()

    def tearDown(self):
        with photoshop_state._executions_guard:
            photoshop_state._executions.clear()

    def _add_state(self, state: PhotoshopExecutionState):
        with photoshop_state._executions_guard:
            photoshop_state._executions[state.ticket_id] = state

    def test_get_execution_state_returns_copy(self):
        state = PhotoshopExecutionState(
            ticket_id="ticket-1",
            job_id="job-1",
            cancel_event=threading.Event(),
            output_paths=["out.psd"],
        )
        self._add_state(state)

        result = get_execution_state("ticket-1")
        result["output_paths"].append("mutated.psd")

        self.assertEqual(get_execution_state("ticket-1")["output_paths"], ["out.psd"])

    def test_cancel_running_execution_sets_event(self):
        cancel_event = threading.Event()
        self._add_state(PhotoshopExecutionState(ticket_id="ticket-1", job_id="job-1", cancel_event=cancel_event))

        result = cancel_execution("ticket-1")

        self.assertTrue(cancel_event.is_set())
        self.assertEqual(result["message"], "Cancellation requested")

    def test_cancel_missing_execution_raises(self):
        with self.assertRaises(FileNotFoundError):
            cancel_execution("missing")

    def test_cancel_completed_execution_raises(self):
        self._add_state(
            PhotoshopExecutionState(
                ticket_id="ticket-1",
                job_id="job-1",
                cancel_event=threading.Event(),
                status="done",
            )
        )

        with self.assertRaises(RuntimeError):
            cancel_execution("ticket-1")


if __name__ == "__main__":
    unittest.main()
