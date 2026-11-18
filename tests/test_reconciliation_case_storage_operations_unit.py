import unittest
from unittest.mock import MagicMock, patch

from mysql_pipeline import reconciliation_case_storage as storage


class ParticipantTests(unittest.TestCase):
    def setUp(self):
        self.connection = MagicMock()
        self.cursor = MagicMock()
        self.connection.is_connected.return_value = True
        self.connection.cursor.return_value = self.cursor
        self.cursor.lastrowid = 71

    @patch.object(storage, "_insert_audit")
    @patch.object(storage, "_lock_transaction_profiles")
    @patch.object(storage, "_case_owner_for_update")
    @patch.object(storage, "get_db_connection")
    def test_add_participant_to_open_owned_case(
        self, connection_factory, owner_mock, lock_mock, audit_mock
    ):
        connection_factory.return_value = self.connection
        owner_mock.return_value = (3, "suggested")

        result = storage.add_case_participant(
            user_id=3, case_id=12, transaction_id=88,
            participant_role="member", participant_status="proposed"
        )

        self.assertTrue(result["success"], result["message"])
        self.assertEqual(result["participant_id"], 71)
        lock_mock.assert_called_once_with(self.cursor, [88], 3)
        audit_mock.assert_called_once()
        self.connection.commit.assert_called_once()
        self.connection.rollback.assert_not_called()

    @patch.object(storage, "_case_owner_for_update")
    @patch.object(storage, "get_db_connection")
    def test_add_participant_rejects_another_users_case(
        self, connection_factory, owner_mock
    ):
        connection_factory.return_value = self.connection
        owner_mock.return_value = (2, "suggested")

        result = storage.add_case_participant(3, 12, 88)

        self.assertFalse(result["success"])
        self.assertIn("not found", result["message"])
        self.connection.rollback.assert_called_once()
        self.connection.commit.assert_not_called()

    @patch.object(storage, "_case_owner_for_update")
    @patch.object(storage, "get_db_connection")
    def test_add_participant_rejects_closed_case(
        self, connection_factory, owner_mock
    ):
        connection_factory.return_value = self.connection
        owner_mock.return_value = (3, "confirmed")

        result = storage.add_case_participant(3, 12, 88)

        self.assertFalse(result["success"])
        self.assertIn("closed case", result["message"])
        self.connection.rollback.assert_called_once()


class EvidenceAndAuditTests(unittest.TestCase):
    def setUp(self):
        self.connection = MagicMock()
        self.cursor = MagicMock()
        self.connection.is_connected.return_value = True
        self.connection.cursor.return_value = self.cursor
        self.cursor.lastrowid = 81

    @patch.object(storage, "_insert_audit")
    @patch.object(storage, "_case_owner_for_update")
    @patch.object(storage, "get_db_connection")
    def test_add_evidence_checks_document_ownership(
        self, connection_factory, owner_mock, audit_mock
    ):
        connection_factory.return_value = self.connection
        owner_mock.return_value = (3, "suggested")
        self.cursor.fetchone.return_value = (13,)

        result = storage.add_case_evidence(
            user_id=3, case_id=12, evidence_type="document_reference",
            evidence_description="Statement source",
            evidence_data={"source": "statement"}, document_id=13
        )

        self.assertTrue(result["success"], result["message"])
        self.assertEqual(result["evidence_id"], 81)
        first_query, first_params = self.cursor.execute.call_args_list[0][0]
        self.assertIn("document_id = %s AND user_id = %s", first_query)
        self.assertEqual(first_params, (13, 3))
        audit_mock.assert_called_once()
        self.connection.commit.assert_called_once()

    @patch.object(storage, "_case_owner_for_update")
    @patch.object(storage, "get_db_connection")
    def test_evidence_rejects_document_owned_by_another_user(
        self, connection_factory, owner_mock
    ):
        connection_factory.return_value = self.connection
        owner_mock.return_value = (3, "suggested")
        self.cursor.fetchone.return_value = None

        result = storage.add_case_evidence(
            user_id=3, case_id=12, evidence_type="document_reference",
            document_id=13
        )

        self.assertFalse(result["success"])
        self.assertIn("document not found", result["message"])
        self.connection.rollback.assert_called_once()
        self.connection.commit.assert_not_called()

    @patch.object(storage, "_insert_audit", return_value=91)
    @patch.object(storage, "_case_owner_for_update")
    @patch.object(storage, "get_db_connection")
    def test_record_audit_event_commits_for_case_owner(
        self, connection_factory, owner_mock, audit_mock
    ):
        connection_factory.return_value = self.connection
        owner_mock.return_value = (3, "suggested")

        result = storage.record_audit_event(
            user_id=3, case_id=12, event_type="manual_review",
            event_description="Reviewed evidence",
            event_data={"reviewed": True}
        )

        self.assertTrue(result["success"], result["message"])
        self.assertEqual(result["event_id"], 91)
        audit_mock.assert_called_once()
        self.connection.commit.assert_called_once()

    @patch.object(storage, "get_db_connection")
    def test_record_audit_event_rejects_invalid_event_type(self, connection_factory):
        result = storage.record_audit_event(
            user_id=3, case_id=12, event_type=" " * 2
        )

        self.assertFalse(result["success"])
        connection_factory.assert_not_called()


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.connection = MagicMock()
        self.cursor = MagicMock()
        self.connection.is_connected.return_value = True
        self.connection.cursor.return_value = self.cursor

    @patch.object(storage, "_insert_audit")
    @patch.object(storage, "_case_owner_for_update")
    @patch.object(storage, "get_db_connection")
    def test_user_confirmation_updates_case_and_records_history(
        self, connection_factory, owner_mock, audit_mock
    ):
        connection_factory.return_value = self.connection
        owner_mock.return_value = (3, "suggested")

        result = storage.record_case_decision(
            user_id=3, case_id=12, decision_type="user_confirmed",
            decision_reason="Evidence agrees", confidence_score="0.99"
        )

        self.assertTrue(result["success"], result["message"])
        self.assertEqual(result["case_status"], "confirmed")
        self.assertEqual(self.cursor.execute.call_count, 2)
        decision_sql, decision_params = self.cursor.execute.call_args_list[0][0]
        self.assertIn("INSERT INTO reconciliation_decisions", decision_sql)
        self.assertEqual(decision_params, (12, "user_confirmed", "Evidence agrees", decision_params[3], 3))
        status_sql, status_params = self.cursor.execute.call_args_list[1][0]
        self.assertIn("UPDATE reconciliation_cases", status_sql)
        self.assertEqual(status_params, ("confirmed", 12, 3))
        audit_mock.assert_called_once()
        self.connection.commit.assert_called_once()

    @patch.object(storage, "_case_owner_for_update")
    @patch.object(storage, "get_db_connection")
    def test_decision_rejects_another_users_case(
        self, connection_factory, owner_mock
    ):
        connection_factory.return_value = self.connection
        owner_mock.return_value = (2, "suggested")

        result = storage.record_case_decision(3, 12, "rejected")

        self.assertFalse(result["success"])
        self.assertIn("not found", result["message"])
        self.connection.rollback.assert_called_once()

    @patch.object(storage, "_case_owner_for_update")
    @patch.object(storage, "get_db_connection")
    def test_closed_case_must_be_reopened_before_new_decision(
        self, connection_factory, owner_mock
    ):
        connection_factory.return_value = self.connection
        owner_mock.return_value = (3, "confirmed")

        result = storage.record_case_decision(3, 12, "rejected")

        self.assertFalse(result["success"])
        self.assertIn("closed", result["message"])
        self.connection.rollback.assert_called_once()

    @patch.object(storage, "_insert_audit")
    @patch.object(storage, "_case_owner_for_update")
    @patch.object(storage, "get_db_connection")
    def test_rejected_case_can_be_reopened(
        self, connection_factory, owner_mock, audit_mock
    ):
        connection_factory.return_value = self.connection
        owner_mock.return_value = (3, "rejected")

        result = storage.record_case_decision(
            3, 12, "reopened", decision_reason="New evidence received"
        )

        self.assertTrue(result["success"], result["message"])
        self.assertEqual(result["case_status"], "reopened")
        self.connection.commit.assert_called_once()
        audit_mock.assert_called_once()


class AllocationCreationTests(unittest.TestCase):
    @patch.object(storage, "get_db_connection")
    def test_allocation_rejects_same_participant_before_connecting(self, connection_factory):
        result = storage.add_reconciliation_allocation(
            user_id=3, case_id=12, from_participant_id=20,
            to_participant_id=20, allocated_amount="10.00"
        )

        self.assertFalse(result["success"])
        self.assertIn("itself", result["message"])
        connection_factory.assert_not_called()

    @patch.object(storage, "get_db_connection")
    def test_allocation_rejects_nonpositive_amount_before_connecting(self, connection_factory):
        result = storage.add_reconciliation_allocation(
            user_id=3, case_id=12, from_participant_id=20,
            to_participant_id=21, allocated_amount="0.00"
        )

        self.assertFalse(result["success"])
        connection_factory.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
