import unittest
from unittest.mock import MagicMock, patch

from mysql_pipeline import reconciliation_case_storage as storage


class CaseListingTests(unittest.TestCase):
    @patch.object(storage, "get_db_connection")
    def test_invalid_limit_is_rejected_before_database_access(self, connection_factory):
        result = storage.list_user_cases(user_id=3, limit=0)

        self.assertFalse(result["success"])
        self.assertEqual(result["cases"], [])
        connection_factory.assert_not_called()

    @patch.object(storage, "get_db_connection")
    def test_invalid_status_is_rejected_before_database_access(self, connection_factory):
        result = storage.list_user_cases(user_id=3, case_status="not_a_status")

        self.assertFalse(result["success"])
        self.assertIn("case_status", result["message"])
        connection_factory.assert_not_called()

    @patch.object(storage, "get_db_connection")
    def test_invalid_case_type_is_rejected_before_database_access(self, connection_factory):
        result = storage.list_user_cases(user_id=3, case_type="not_a_type")

        self.assertFalse(result["success"])
        self.assertIn("case_type", result["message"])
        connection_factory.assert_not_called()

    @patch.object(storage, "get_db_connection")
    def test_list_user_cases_applies_user_and_filter_parameters(self, connection_factory):
        connection = MagicMock()
        cursor = MagicMock()
        connection.is_connected.return_value = True
        connection.cursor.return_value = cursor
        cursor.fetchall.return_value = [{"case_id": 12, "user_id": 3}]
        connection_factory.return_value = connection

        result = storage.list_user_cases(
            user_id=3, limit=20, offset=5,
            case_status="needs_review", case_type="duplicate"
        )

        self.assertTrue(result["success"], result["message"])
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["cases"][0]["case_id"], 12)
        query, params = cursor.execute.call_args[0]
        self.assertIn("WHERE user_id = %s", query)
        self.assertIn("case_status = %s", query)
        self.assertIn("case_type = %s", query)
        self.assertEqual(params, (3, "needs_review", "duplicate", 20, 5))
        cursor.close.assert_called_once()
        connection.close.assert_called_once()


class CaseRetrievalTests(unittest.TestCase):
    @patch.object(storage, "get_db_connection")
    def test_case_not_found_returns_no_case(self, connection_factory):
        connection = MagicMock()
        cursor = MagicMock()
        connection.is_connected.return_value = True
        connection.cursor.return_value = cursor
        cursor.fetchone.return_value = None
        connection_factory.return_value = connection

        result = storage.get_case_by_id(user_id=3, case_id=99)

        self.assertFalse(result["success"])
        self.assertIsNone(result["case"])
        cursor.execute.assert_called_once()
        cursor.close.assert_called_once()
        connection.close.assert_called_once()

    @patch.object(storage, "get_db_connection")
    def test_case_retrieval_loads_all_related_records(self, connection_factory):
        connection = MagicMock()
        cursor = MagicMock()
        connection.is_connected.return_value = True
        connection.cursor.return_value = cursor
        cursor.fetchone.return_value = {
            "case_id": 12, "user_id": 3, "case_status": "suggested"
        }
        cursor.fetchall.return_value = []
        connection_factory.return_value = connection

        result = storage.get_case_by_id(user_id=3, case_id=12)

        self.assertTrue(result["success"], result["message"])
        case = result["case"]
        for key in ("participants", "allocations", "evidence", "decisions", "audit_events"):
            self.assertEqual(case[key], [])
        self.assertEqual(cursor.execute.call_count, 6)
        cursor.close.assert_called_once()
        connection.close.assert_called_once()


class AllocationStatusTests(unittest.TestCase):
    def setUp(self):
        self.connection = MagicMock()
        self.cursor = MagicMock()
        self.connection.is_connected.return_value = True
        self.connection.cursor.return_value = self.cursor
        self.connection.cursor.return_value = self.cursor

    @patch.object(storage, "_insert_audit")
    @patch.object(storage, "_case_owner_for_update")
    @patch.object(storage, "get_db_connection")
    def test_proposed_allocation_can_be_rejected(
        self, connection_factory, owner_mock, audit_mock
    ):
        connection_factory.return_value = self.connection
        owner_mock.return_value = (3, "suggested")
        self.cursor.fetchone.return_value = (
            21, 22, "25.00", "INR", "proposed"
        )

        result = storage.update_allocation_status(
            user_id=3, case_id=12, allocation_id=44,
            new_status="rejected", decision_reason="Not the same payment"
        )

        self.assertTrue(result["success"], result["message"])
        self.assertEqual(result["allocation_status"], "rejected")
        self.connection.commit.assert_called_once()
        self.connection.rollback.assert_not_called()
        audit_mock.assert_called_once()
        self.assertEqual(self.cursor.execute.call_count, 3)
        self.cursor.close.assert_called_once()
        self.connection.close.assert_called_once()

    @patch.object(storage, "_case_owner_for_update")
    @patch.object(storage, "get_db_connection")
    def test_allocation_status_rejects_other_users_case(
        self, connection_factory, owner_mock
    ):
        connection_factory.return_value = self.connection
        owner_mock.return_value = (2, "suggested")

        result = storage.update_allocation_status(
            user_id=3, case_id=12, allocation_id=44,
            new_status="rejected"
        )

        self.assertFalse(result["success"])
        self.assertIn("not found", result["message"])
        self.connection.rollback.assert_called_once()
        self.connection.commit.assert_not_called()

    @patch.object(storage, "_case_owner_for_update")
    @patch.object(storage, "get_db_connection")
    def test_only_confirmed_or_rejected_statuses_are_allowed(
        self, connection_factory, owner_mock
    ):
        result = storage.update_allocation_status(
            user_id=3, case_id=12, allocation_id=44,
            new_status="proposed"
        )

        self.assertFalse(result["success"])
        self.assertIn("confirmed or rejected", result["message"])
        connection_factory.assert_not_called()
        owner_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
