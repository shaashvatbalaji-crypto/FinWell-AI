
import unittest
from decimal import Decimal

from reconciliation.balance_reconciler import (
    reconcile_statement_balance,
)


class BalanceReconcilerTests(unittest.TestCase):

    def setUp(self):
        self.transactions = [
            {"debit": 500, "credit": None, "balance": 9500},
            {"debit": None, "credit": 2000, "balance": 11500},
            {"debit": 1500, "credit": None, "balance": 10000},
        ]

    def test_statement_balances_correctly(self):
        result = reconcile_statement_balance(
            self.transactions,
            opening_balance=10000,
            closing_balance=10000,
        )

        self.assertTrue(result["statement_balanced"])
        self.assertEqual(result["total_debits"], Decimal("2000.00"))
        self.assertEqual(result["total_credits"], Decimal("2000.00"))
        self.assertEqual(result["difference"], Decimal("0.00"))

    def test_closing_balance_mismatch(self):
        result = reconcile_statement_balance(
            self.transactions,
            opening_balance=10000,
            closing_balance=10500,
        )

        self.assertFalse(result["statement_balanced"])
        self.assertEqual(result["difference"], Decimal("500.00"))

    def test_running_balance_mismatch(self):
        transactions = [
            {"debit": 500, "credit": None, "balance": 9000},
        ]

        result = reconcile_statement_balance(
            transactions,
            opening_balance=10000,
            closing_balance=9500,
        )

        self.assertTrue(result["statement_balanced"])
        self.assertEqual(len(result["running_balance_mismatches"]), 1)

    def test_invalid_negative_debit(self):
        transactions = [
            {"debit": -500, "credit": None, "balance": 9500},
        ]

        result = reconcile_statement_balance(
            transactions,
            opening_balance=10000,
            closing_balance=9500,
        )

        self.assertFalse(result["statement_balanced"])
        self.assertEqual(result["invalid_transaction_count"], 1)

    def test_both_debit_and_credit_positive(self):
        transactions = [
            {"debit": 500, "credit": 500, "balance": 10000},
        ]

        result = reconcile_statement_balance(
            transactions,
            opening_balance=10000,
            closing_balance=10000,
        )

        self.assertEqual(result["invalid_transaction_count"], 1)

    def test_missing_transaction_balance(self):
        transactions = [
            {"debit": 500, "credit": None},
        ]

        result = reconcile_statement_balance(
            transactions,
            opening_balance=10000,
            closing_balance=9500,
        )

        self.assertTrue(result["statement_balanced"])
        self.assertEqual(len(result["running_balance_mismatches"]), 0)

    def test_rounding_tolerance(self):
        result = reconcile_statement_balance(
            [],
            opening_balance=10000,
            closing_balance=10000.01,
            tolerance=Decimal("0.01"),
        )

        self.assertTrue(result["statement_balanced"])

    def test_invalid_transaction_does_not_pass(self):
        transactions = [
            {"debit": 500, "credit": None},
            {"debit": "invalid", "credit": None},
        ]

        result = reconcile_statement_balance(
            transactions,
            opening_balance=10000,
            closing_balance=9500,
        )

        self.assertFalse(result["statement_balanced"])
        self.assertEqual(result["invalid_transaction_count"], 1)

    def test_empty_statement(self):
        result = reconcile_statement_balance(
            [],
            opening_balance=10000,
            closing_balance=10000,
        )

        self.assertTrue(result["statement_balanced"])
        self.assertEqual(result["valid_transaction_count"], 0)

    def test_invalid_opening_balance(self):
        result = reconcile_statement_balance(
            self.transactions,
            opening_balance="invalid",
            closing_balance=10000,
        )

        self.assertFalse(result["success"])

    def test_no_database_writes(self):
        result = reconcile_statement_balance(
            self.transactions,
            opening_balance=10000,
            closing_balance=10000,
        )

        self.assertFalse(result["writes_performed"])
        self.assertEqual(result["mode"], "dry_run")

    def test_original_transactions_unchanged(self):
        original = [dict(item) for item in self.transactions]

        reconcile_statement_balance(
            self.transactions,
            opening_balance=10000,
            closing_balance=10000,
        )

        self.assertEqual(self.transactions, original)


if __name__ == "__main__":
    unittest.main()
