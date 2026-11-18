import unittest
from reconciliation.internal_transfer_matcher import reconcile_internal_transfers, extract_reference


class InternalTransferMatcherTests(unittest.TestCase):
    def setUp(self):
        self.accounts = {
            4821: {"account_id": 4821, "user_id": 7, "verified": True},
            7392: {"account_id": 7392, "user_id": 7, "verified": True},
            8888: {"account_id": 8888, "user_id": 8, "verified": True},
        }
        self.debit = {
            "transaction_id": 101, "user_id": 7, "account_id": 4821,
            "date": "2026-11-06", "description": "UPI TRANSFER TO OWN AC 7392 REF TRF501",
            "debit": 5000.0, "credit": None, "balance": 81550.0, "currency": "INR",
        }
        self.credit = {
            "transaction_id": 201, "user_id": 7, "account_id": 7392,
            "date": "2026-11-06", "description": "UPI RECEIVED FROM OWN AC 4821 REF TRF501",
            "debit": None, "credit": 5000.0, "balance": 25000.0, "currency": "INR",
        }

    def run_match(self, transactions=None, accounts=None, **kwargs):
        return reconcile_internal_transfers(
            transactions if transactions is not None else [self.debit, self.credit],
            accounts if accounts is not None else self.accounts,
            **kwargs,
        )

    def test_expected_pdf_pair_is_proposed_not_confirmed(self):
        result = self.run_match()
        self.assertEqual(result["candidate_count"], 1)
        pair = result["candidates"][0]
        self.assertEqual(pair["debit_transaction_id"], 101)
        self.assertEqual(pair["credit_transaction_id"], 201)
        self.assertEqual(pair["amount"], "5000.00")
        self.assertEqual(pair["reference"], "TRF501")
        self.assertFalse(pair["auto_confirmed"])
        self.assertEqual(pair["decision"], "proposed_only")
        self.assertFalse(result["writes_performed"])

    def test_reference_extraction(self):
        self.assertEqual(extract_reference("UPI TRANSFER REF TRF501"), "TRF501")
        self.assertEqual(extract_reference("IMPS UTR: ABCD123456"), "ABCD123456")

    def test_amount_mismatch_is_not_matched(self):
        other = dict(self.credit, credit=4999.99)
        result = self.run_match([self.debit, other])
        self.assertEqual(result["candidate_count"], 0)

    def test_reference_mismatch_is_not_matched(self):
        other = dict(self.credit, description="UPI RECEIVED FROM OWN AC 4821 REF TRF777")
        result = self.run_match([self.debit, other])
        self.assertEqual(result["candidate_count"], 0)

    def test_missing_reference_is_not_matched(self):
        other = dict(self.credit, description="UPI RECEIVED FROM OWN AC 4821")
        result = self.run_match([self.debit, other])
        self.assertEqual(result["candidate_count"], 0)

    def test_same_direction_is_not_matched(self):
        other = dict(self.credit, debit=5000.0, credit=None)
        result = self.run_match([self.debit, other])
        self.assertEqual(result["candidate_count"], 0)

    def test_same_account_is_not_matched(self):
        other = dict(self.credit, account_id=4821)
        result = self.run_match([self.debit, other])
        self.assertEqual(result["candidate_count"], 0)

    def test_different_users_are_not_matched(self):
        other = dict(self.credit, user_id=8, account_id=8888)
        result = self.run_match([self.debit, other])
        self.assertEqual(result["candidate_count"], 0)

    def test_unverified_account_is_excluded(self):
        accounts = dict(self.accounts)
        accounts[7392] = dict(accounts[7392], verified=False)
        result = self.run_match(accounts=accounts)
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["unmatched_count"], 1)

    def test_date_outside_window_is_not_matched(self):
        other = dict(self.credit, date="2026-11-09")
        result = self.run_match([self.debit, other], max_date_gap_days=1)
        self.assertEqual(result["candidate_count"], 0)

    def test_currency_mismatch_is_not_matched(self):
        other = dict(self.credit, currency="USD")
        result = self.run_match([self.debit, other])
        self.assertEqual(result["candidate_count"], 0)

    def test_non_transfer_narration_is_ignored(self):
        other = dict(self.credit, description="SALARY CREDIT REF TRF501")
        result = self.run_match([self.debit, other])
        self.assertEqual(result["candidate_count"], 0)

    def test_invalid_transaction_is_reported(self):
        invalid = dict(self.debit, transaction_id=303, debit=0, credit=0)
        result = self.run_match([invalid, self.credit])
        self.assertIn(303, result["invalid_transaction_ids"])

    def test_invalid_window_rejected(self):
        with self.assertRaises(ValueError):
            self.run_match(max_date_gap_days=-1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
