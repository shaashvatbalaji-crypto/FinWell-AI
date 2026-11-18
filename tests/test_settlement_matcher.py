
import unittest
from decimal import Decimal

from reconciliation.settlement_matcher import reconcile_settlements


class SettlementMatcherTests(unittest.TestCase):

    def setUp(self):
        self.gateway = [{
            "transaction_id": 101,
            "user_id": 1,
            "date": "2026-11-10",
            "description": "GATEWAY PAYMENT",
            "gross_amount": 5000,
            "processing_fee": 100,
            "currency": "INR",
            "settlement_reference": "SETTLE501",
        }]

        self.bank = [{
            "transaction_id": 201,
            "user_id": 1,
            "date": "2026-11-11",
            "description": "GATEWAY SETTLEMENT REF SETTLE501",
            "credit": 4900,
            "currency": "INR",
            "reference": "SETTLE501",
        }]

    def test_exact_settlement_match(self):
        result = reconcile_settlements(
            self.gateway,
            self.bank
        )

        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(
            result["matched_candidates"][0]["expected_net"],
            Decimal("4900.00")
        )
        self.assertEqual(
            result["matched_candidates"][0]["status"],
            "proposed"
        )

    def test_fee_mismatch_not_matched(self):
        bank = [dict(self.bank[0], credit=4800)]

        result = reconcile_settlements(self.gateway, bank)

        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(len(result["unmatched_gateway"]), 1)

    def test_different_users_not_matched(self):
        bank = [dict(self.bank[0], user_id=2)]

        result = reconcile_settlements(self.gateway, bank)

        self.assertEqual(result["candidate_count"], 0)

    def test_currency_mismatch_not_matched(self):
        bank = [dict(self.bank[0], currency="USD")]

        result = reconcile_settlements(self.gateway, bank)

        self.assertEqual(result["candidate_count"], 0)

    def test_reference_mismatch_not_matched(self):
        bank = [dict(self.bank[0], reference="OTHER501")]

        result = reconcile_settlements(self.gateway, bank)

        self.assertEqual(result["candidate_count"], 0)

    def test_date_outside_window_not_matched(self):
        bank = [dict(self.bank[0], date="2026-11-20")]

        result = reconcile_settlements(self.gateway, bank)

        self.assertEqual(result["candidate_count"], 0)

    def test_multiple_gateway_payments(self):
        gateway = [
            dict(
                self.gateway[0],
                transaction_id=101,
                gross_amount=3000,
                processing_fee=60,
            ),
            dict(
                self.gateway[0],
                transaction_id=102,
                gross_amount=2000,
                processing_fee=40,
            ),
        ]

        result = reconcile_settlements(
            gateway,
            self.bank
        )

        self.assertEqual(result["candidate_count"], 1)

        candidate = result["matched_candidates"][0]

        self.assertEqual(len(candidate["gateway_transaction_ids"]), 2)
        self.assertEqual(candidate["gross_amount"], Decimal("5000.00"))
        self.assertEqual(candidate["processing_fee"], Decimal("100.00"))
        self.assertEqual(candidate["expected_net"], Decimal("4900.00"))

    def test_missing_reference_can_match_exact_amount(self):
        gateway = [
            dict(self.gateway[0], settlement_reference=None)
        ]

        bank = [
            dict(self.bank[0], reference=None, description="BANK CREDIT")
        ]

        result = reconcile_settlements(gateway, bank)

        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(
            result["matched_candidates"][0]["confidence_label"],
            "medium"
        )

    def test_ambiguous_bank_matches_sent_for_review(self):
        bank = [
            self.bank[0],
            dict(self.bank[0], transaction_id=202),
        ]

        result = reconcile_settlements(
            self.gateway,
            bank
        )

        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(len(result["review_required"]), 1)

    def test_missing_currency_is_invalid(self):
        gateway = [
            dict(self.gateway[0], currency=None)
        ]

        result = reconcile_settlements(gateway, self.bank)

        self.assertEqual(len(result["invalid_transactions"]), 1)
        self.assertEqual(result["candidate_count"], 0)

    def test_invalid_date_window(self):
        result = reconcile_settlements(
            self.gateway,
            self.bank,
            max_date_gap_days=-1
        )

        self.assertFalse(result["success"])

    def test_original_transactions_are_unchanged(self):
        gateway = [dict(self.gateway[0])]
        bank = [dict(self.bank[0])]

        gateway_before = dict(gateway[0])
        bank_before = dict(bank[0])

        reconcile_settlements(gateway, bank)

        self.assertEqual(gateway[0], gateway_before)
        self.assertEqual(bank[0], bank_before)

    def test_no_database_writes(self):
        result = reconcile_settlements(
            self.gateway,
            self.bank
        )

        self.assertFalse(result["writes_performed"])
        self.assertEqual(result["mode"], "dry_run")


if __name__ == "__main__":
    unittest.main()
