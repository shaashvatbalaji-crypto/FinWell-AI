"""
Regression tests for FinWell AI inter-account reconciliation.

Run from the FinWell_AI project root:
    python -m unittest test_inter_account_reconciler -v

These tests cover the reference-extraction bug where "UPI TRANSFER" and
"UPI RECEIVED" were incorrectly interpreted as reference values.
"""

import unittest

from reconciliation.inter_account_reconciler import (
    match_inter_account_transfers,
)
from reconciliation.multi_account_reconciler import (
    reconcile_multiple_accounts,
)


def tx(account_id, day, description, debit=None, credit=None, balance=None):
    return {
        "account_id": account_id,
        "date": f"2026-12-{day:02d}",
        "description": description,
        "debit": debit,
        "credit": credit,
        "balance": balance,
        "currency": "INR",
    }


class InterAccountReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.transactions = [
            # TRF601: 4821 -> 7392
            tx("4821", 2, "UPI TRANSFER TO OWN AC 7392 REF TRF601 MC2602DEC482104",
               debit=10000.00),
            tx("7392", 2, "UPI RECEIVED FROM OWN AC 4821 REF TRF601 MC2602DEC739201",
               credit=10000.00),

            # Same reference as TRF601, but a bank fee. Must not be matched.
            tx("4821", 2, "IMPS FEE REF TRF601 MC2602DEC482105", debit=5.90),

            # TRF602: 7392 -> 4821
            tx("4821", 16, "UPI RECEIVED FROM OWN AC 7392 REF TRF602",
               credit=4000.00),
            tx("7392", 16, "UPI TRANSFER TO OWN AC 4821 REF TRF602",
               debit=4000.00),

            # TRF603: 4821 -> 7392
            tx("4821", 23, "UPI TRANSFER TO OWN AC 7392 REF TRF603",
               debit=6000.00),
            tx("7392", 23, "UPI RECEIVED FROM OWN AC 4821 REF TRF603",
               credit=6000.00),

            # TRF604: 4821 -> 7392
            tx("4821", 23, "UPI TRANSFER TO OWN AC 7392 REF TRF604",
               debit=6000.00),
            tx("7392", 23, "UPI RECEIVED FROM OWN AC 4821 REF TRF604",
               credit=6000.00),
        ]

    def test_upi_narration_is_not_used_as_reference(self):
        result = match_inter_account_transfers(self.transactions)
        self.assertTrue(result["success"])
        self.assertEqual(len(result["matches"]), 4)
        self.assertEqual(
            {match["reference"] for match in result["matches"]},
            {"TRF601", "TRF602", "TRF603", "TRF604"},
        )

    def test_bank_fee_is_not_matched_as_transfer(self):
        result = match_inter_account_transfers(self.transactions)
        fee_rows = [
            item for item in result["unmatched_transactions"]
            if item["description"].startswith("IMPS FEE")
        ]
        self.assertEqual(len(fee_rows), 1)
        self.assertEqual(fee_rows[0]["debit"], 5.90)

    def test_internal_transfer_amount(self):
        result = match_inter_account_transfers(self.transactions)
        self.assertEqual(result["summary"]["internal_transfer_amount"], 26000.00)

    def test_multi_account_reconciler_excludes_internal_transfers(self):
        result = reconcile_multiple_accounts(self.transactions)
        self.assertTrue(result["success"])
        self.assertEqual(result["summary"]["matched_internal_transfer_pairs"], 4)

        consolidated = result["consolidated_report"]["INR"]
        self.assertEqual(consolidated["internal_transfer_debits"], 26000.00)
        self.assertEqual(consolidated["internal_transfer_credits"], 26000.00)

        # The fee remains an external expense; transfer principal is excluded.
        account_4821 = next(
            row for row in result["account_reports"]
            if row["account_id"] == "4821"
        )
        self.assertEqual(account_4821["internal_transfer_debits"], 22000.00)
        self.assertEqual(account_4821["internal_transfer_credits"], 4000.00)


if __name__ == "__main__":
    unittest.main(verbosity=2)
