
import unittest

from reconciliation.internal_transfer_matcher import (
    reconcile_internal_transfers,
)


class InternalTransferMatcherV2Tests(unittest.TestCase):

    def setUp(self):
        self.accounts = {
            101: {"account_id": 101, "user_id": 1, "verified": True},
            202: {"account_id": 202, "user_id": 1, "verified": True},
            303: {"account_id": 303, "user_id": 1, "verified": False},
        }

    def transaction(
        self,
        tx_id,
        account_id,
        date,
        description,
        debit=None,
        credit=None,
        currency="INR",
    ):
        return {
            "transaction_id": tx_id,
            "user_id": 1,
            "account_id": account_id,
            "date": date,
            "description": description,
            "debit": debit,
            "credit": credit,
            "currency": currency,
        }

    def test_missing_currency_goes_to_diagnostics(self):
        transactions = [
            self.transaction(
                1, 101, "2026-11-06",
                "TRANSFER TO OWN AC REF TRF501",
                debit=5000, currency=None,
            ),
            self.transaction(
                2, 202, "2026-11-06",
                "TRANSFER FROM OWN AC REF TRF501",
                credit=5000, currency=None,
            ),
        ]

        result = reconcile_internal_transfers(
            transactions, self.accounts
        )

        self.assertEqual(result["candidate_count"], 0)
        self.assertTrue(
            any(
                "currency_unknown" in item["reasons"]
                for item in result["comparison_diagnostics"]
            )
        )

    def test_unverified_account_is_sent_for_review(self):
        transactions = [
            self.transaction(
                1, 303, "2026-11-06",
                "TRANSFER TO OWN AC REF TRF501",
                debit=5000,
            ),
        ]

        result = reconcile_internal_transfers(
            transactions, self.accounts
        )

        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["review_required_count"], 1)
        self.assertEqual(
            result["review_required"][0]["reason"],
            "account_ownership_not_verified",
        )

    def test_ambiguous_matches_are_sent_for_review(self):
        transactions = [
            self.transaction(
                1, 101, "2026-11-06",
                "TRANSFER TO OWN AC REF TRF501",
                debit=5000,
            ),
            self.transaction(
                2, 202, "2026-11-06",
                "TRANSFER FROM OWN AC REF TRF501",
                credit=5000,
            ),
            self.transaction(
                3, 202, "2026-11-06",
                "TRANSFER FROM OWN AC REF TRF501",
                credit=5000,
            ),
        ]

        result = reconcile_internal_transfers(
            transactions, self.accounts
        )

        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["review_required_count"], 3)
        self.assertTrue(
            all(
                item["reason"] == "multiple_possible_matches"
                for item in result["review_required"]
            )
        )

    def test_unique_match_has_high_confidence_label(self):
        transactions = [
            self.transaction(
                1, 101, "2026-11-06",
                "TRANSFER TO OWN AC REF TRF501",
                debit=5000,
            ),
            self.transaction(
                2, 202, "2026-11-06",
                "TRANSFER FROM OWN AC REF TRF501",
                credit=5000,
            ),
        ]

        result = reconcile_internal_transfers(
            transactions, self.accounts
        )

        self.assertEqual(result["candidate_count"], 1)
        candidate = result["candidates"][0]

        self.assertEqual(candidate["confidence_label"], "high")
        self.assertFalse(candidate["auto_confirmed"])
        self.assertEqual(candidate["decision"], "proposed_only")

    def test_no_database_writes(self):
        transactions = [
            self.transaction(
                1, 101, "2026-11-06",
                "TRANSFER TO OWN AC REF TRF501",
                debit=5000,
            ),
            self.transaction(
                2, 202, "2026-11-06",
                "TRANSFER FROM OWN AC REF TRF501",
                credit=5000,
            ),
        ]

        result = reconcile_internal_transfers(
            transactions, self.accounts
        )

        self.assertFalse(result["writes_performed"])
        self.assertEqual(result["mode"], "dry_run")


if __name__ == "__main__":
    unittest.main()
