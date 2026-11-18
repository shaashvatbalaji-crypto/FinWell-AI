import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from mysql_pipeline import reconciliation_case_storage as storage


class ValidationTests(unittest.TestCase):
    def test_positive_id_accepts_valid_integer(self):
        self.assertEqual(storage._positive_id(7, "user_id"), 7)

    def test_positive_id_rejects_boolean(self):
        with self.assertRaises(ValueError):
            storage._positive_id(True, "user_id")

    def test_confidence_rejects_out_of_range_value(self):
        with self.assertRaises(ValueError):
            storage._confidence("1.01")

    def test_money_rejects_more_than_two_decimal_places(self):
        with self.assertRaises(ValueError):
            storage._money("12.345")

    def test_actor_must_match_case_owner(self):
        with self.assertRaises(ValueError):
            storage._verify_actor(3, "user", 2)

    def test_system_actor_must_not_have_user_id(self):
        with self.assertRaises(ValueError):
            storage._verify_actor(3, "system", 3)

    def test_json_value_serializes_data(self):
        result = storage._json_value({"amount": Decimal("10.50")})
        self.assertIn('"amount"', result)
        self.assertIn("10.50", result)


class AllocationValidationTests(unittest.TestCase):
    def setUp(self):
        self.source = {
            "transaction_id": 10,
            "direction": "debit",
            "amount": Decimal("100.00"),
            "account_id": 1,
            "currency": "INR",
        }
        self.target = {
            "transaction_id": 11,
            "direction": "credit",
            "amount": Decimal("100.00"),
            "account_id": 2,
            "currency": "INR",
        }

    @patch.object(storage, "_confirmed_allocation_totals")
    @patch.object(storage, "_transaction_financial_profile")
    def test_opposite_directions_and_matching_currency_pass(
        self, profile_mock, totals_mock
    ):
        profile_mock.side_effect = [self.source, self.target]
        totals_mock.side_effect = [
            (Decimal("0"), Decimal("0")),
            (Decimal("0"), Decimal("0")),
        ]

        source, target = storage._validate_allocation_pair(
            MagicMock(), 3, 10, 11, Decimal("50.00"), "INR", True
        )

        self.assertEqual(source["direction"], "debit")
        self.assertEqual(target["direction"], "credit")

    @patch.object(storage, "_transaction_financial_profile")
    def test_same_direction_is_rejected(self, profile_mock):
        same_direction_target = dict(self.target, direction="debit")
        profile_mock.side_effect = [self.source, same_direction_target]

        with self.assertRaisesRegex(ValueError, "opposite transaction directions"):
            storage._validate_allocation_pair(
                MagicMock(), 3, 10, 11, Decimal("10.00"), "INR", False
            )

    @patch.object(storage, "_confirmed_allocation_totals")
    @patch.object(storage, "_transaction_financial_profile")
    def test_source_over_allocation_is_rejected(self, profile_mock, totals_mock):
        profile_mock.side_effect = [self.source, self.target]
        totals_mock.side_effect = [
            (Decimal("60.00"), Decimal("0")),
            (Decimal("0"), Decimal("0")),
        ]

        with self.assertRaisesRegex(ValueError, "source transaction amount"):
            storage._validate_allocation_pair(
                MagicMock(), 3, 10, 11, Decimal("50.00"), "INR", False
            )

    @patch.object(storage, "_confirmed_allocation_totals")
    @patch.object(storage, "_transaction_financial_profile")
    def test_target_over_allocation_is_rejected(self, profile_mock, totals_mock):
        profile_mock.side_effect = [self.source, self.target]
        totals_mock.side_effect = [
            (Decimal("0"), Decimal("0")),
            (Decimal("0"), Decimal("80.00")),
        ]

        with self.assertRaisesRegex(ValueError, "target transaction amount"):
            storage._validate_allocation_pair(
                MagicMock(), 3, 10, 11, Decimal("30.00"), "INR", False
            )

    @patch.object(storage, "_confirmed_allocation_totals")
    @patch.object(storage, "_transaction_financial_profile")
    def test_unverified_currency_cannot_be_confirmed(
        self, profile_mock, totals_mock
    ):
        target_without_currency = dict(self.target, currency=None)
        profile_mock.side_effect = [self.source, target_without_currency]

        with self.assertRaisesRegex(ValueError, "linked accounts"):
            storage._validate_allocation_pair(
                MagicMock(), 3, 10, 11, Decimal("10.00"), "INR", True
            )

        totals_mock.assert_not_called()


class AtomicCaseCreationTests(unittest.TestCase):
    def setUp(self):
        self.connection = MagicMock()
        self.connection.is_connected.return_value = True
        self.cursor = MagicMock()
        self.cursor.lastrowid = 501
        self.connection.cursor.return_value = self.cursor

    @patch.object(storage, "_insert_audit")
    @patch.object(storage, "_lock_transaction_profiles")
    @patch.object(storage, "get_db_connection")
    def test_case_creation_commits_on_success(
        self, connection_factory, lock_mock, audit_mock
    ):
        connection_factory.return_value = self.connection

        result = storage.create_reconciliation_case(
            user_id=3,
            case_type="duplicate",
            participants=[
                {"transaction_id": 10, "participant_role": "source"},
                {"transaction_id": 11, "participant_role": "target"},
            ],
            case_summary="Unit test case",
        )

        self.assertTrue(result["success"], result["message"])
        self.connection.commit.assert_called_once()
        self.connection.rollback.assert_not_called()
        lock_mock.assert_called_once()
        audit_mock.assert_called_once()
        self.cursor.close.assert_called_once()
        self.connection.close.assert_called_once()

    @patch.object(storage, "_insert_audit", side_effect=ValueError("simulated audit failure"))
    @patch.object(storage, "_lock_transaction_profiles")
    @patch.object(storage, "get_db_connection")
    def test_case_creation_rolls_back_if_audit_fails(
        self, connection_factory, lock_mock, audit_mock
    ):
        connection_factory.return_value = self.connection

        result = storage.create_reconciliation_case(
            user_id=3,
            case_type="duplicate",
            participants=[
                {"transaction_id": 10},
                {"transaction_id": 11},
            ],
        )

        self.assertFalse(result["success"])
        self.assertIsNone(result["case_id"])
        self.connection.rollback.assert_called_once()
        self.connection.commit.assert_not_called()

    @patch.object(storage, "_lock_transaction_profiles")
    @patch.object(storage, "get_db_connection")
    def test_duplicate_transaction_in_case_is_rejected(
        self, connection_factory, lock_mock
    ):
        connection_factory.return_value = self.connection

        result = storage.create_reconciliation_case(
            user_id=3,
            case_type="duplicate",
            participants=[
                {"transaction_id": 10},
                {"transaction_id": 10},
            ],
        )

        self.assertFalse(result["success"])
        self.assertIn("only once", result["message"])
        self.connection.rollback.assert_called_once()
        lock_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
