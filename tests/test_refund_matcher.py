
import unittest

from reconciliation.refund_matcher import reconcile_refunds


class RefundMatcherTests(unittest.TestCase):

    def setUp(self):
        self.purchase = {
            "transaction_id": 101,
            "user_id": 1,
            "account_id": 10,
            "date": "2026-11-05",
            "description": "AMAZON PURCHASE REF A501",
            "debit": 3000.00,
            "credit": 0,
            "currency": "INR",
        }

        self.refund1 = {
            "transaction_id": 102,
            "user_id": 1,
            "account_id": 10,
            "date": "2026-11-10",
            "description": "AMAZON REFUND REF A501",
            "debit": 0,
            "credit": 1000.00,
            "currency": "INR",
        }

        self.refund2 = {
            "transaction_id": 103,
            "user_id": 1,
            "account_id": 10,
            "date": "2026-11-14",
            "description": "AMAZON REFUND REF A501",
            "debit": 0,
            "credit": 500.00,
            "currency": "INR",
        }

    def test_two_partial_refunds_match_one_purchase(self):
        result = reconcile_refunds([
            self.purchase,
            self.refund1,
            self.refund2,
        ])

        self.assertTrue(result["success"])
        self.assertEqual(result["allocation_count"], 2)
        self.assertEqual(result["total_refunded"], "1500.00")
        self.assertEqual(
            result["total_remaining_expense"],
            "1500.00",
        )

        self.assertEqual(result["review_required_count"], 0)
        self.assertEqual(result["over_refund_count"], 0)

    def test_full_refund(self):
        refund = dict(self.refund1)
        refund["credit"] = 3000.00

        result = reconcile_refunds([
            self.purchase,
            refund,
        ])

        self.assertEqual(result["allocation_count"], 1)
        self.assertEqual(result["total_refunded"], "3000.00")
        self.assertEqual(
            result["total_remaining_expense"],
            "0.00",
        )

        summary = result["purchase_summaries"][0]

        self.assertEqual(
            summary["refund_status"],
            "fully_refunded",
        )

    def test_reference_conflict_is_not_matched(self):
        refund = dict(self.refund1)
        refund["description"] = "AMAZON REFUND REF DIFFERENT99"

        result = reconcile_refunds([
            self.purchase,
            refund,
        ])

        self.assertEqual(result["allocation_count"], 0)
        self.assertEqual(result["unmatched_refund_count"], 1)

    def test_different_accounts_are_not_matched(self):
        refund = dict(self.refund1)
        refund["account_id"] = 20

        result = reconcile_refunds([
            self.purchase,
            refund,
        ])

        self.assertEqual(result["allocation_count"], 0)
        self.assertEqual(result["unmatched_refund_count"], 1)

    def test_ambiguous_purchase_is_sent_for_review(self):
        purchase2 = dict(self.purchase)
        purchase2["transaction_id"] = 104
        purchase2["date"] = "2026-11-06"

        refund = dict(self.refund1)

        result = reconcile_refunds([
            self.purchase,
            purchase2,
            refund,
        ])

        self.assertEqual(result["allocation_count"], 0)
        self.assertEqual(result["review_required_count"], 1)

        review = result["review_required"][0]

        self.assertEqual(
            review["reason"],
            "multiple_possible_purchases",
        )

        self.assertEqual(
            review["status"],
            "needs_review",
        )

    def test_missing_reference_requires_manual_review(self):
        purchase = dict(self.purchase)
        purchase["description"] = "AMAZON PURCHASE"

        refund = dict(self.refund1)
        refund["description"] = "AMAZON REFUND"

        result = reconcile_refunds([
            purchase,
            refund,
        ])

        self.assertEqual(result["allocation_count"], 0)
        self.assertEqual(result["review_required_count"], 1)

        review = result["review_required"][0]

        self.assertEqual(
            review["reason"],
            "reference_missing_weak_match",
        )

        self.assertEqual(
            review["status"],
            "needs_review",
        )

        self.assertEqual(
            review["purchase_transaction_id"],
            purchase["transaction_id"],
        )

        self.assertEqual(
            review["refund_transaction_id"],
            refund["transaction_id"],
        )

        self.assertEqual(result["total_refunded"], "0.00")

    def test_over_refund_is_flagged(self):
        refund = dict(self.refund1)
        refund["credit"] = 3500.00

        result = reconcile_refunds([
            self.purchase,
            refund,
        ])

        self.assertEqual(result["allocation_count"], 0)
        self.assertEqual(result["over_refund_count"], 1)

        self.assertEqual(
            result["over_refunds"][0]["status"],
            "needs_review",
        )

    def test_invalid_date_window_is_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_refunds(
                [self.purchase, self.refund1],
                max_date_gap_days=-1,
            )

        with self.assertRaises(ValueError):
            reconcile_refunds(
                [self.purchase, self.refund1],
                max_date_gap_days=1.5,
            )

    def test_database_writes_are_disabled(self):
        result = reconcile_refunds([
            self.purchase,
            self.refund1,
        ])

        self.assertEqual(result["mode"], "dry_run")
        self.assertFalse(result["writes_performed"])


if __name__ == "__main__":
    unittest.main()
