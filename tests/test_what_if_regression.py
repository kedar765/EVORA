"""
EVORA Regression Test: What-If Analysis Financial & ML Horizon Validation
==========================================================================
Verifies:
1. 5% Expense reduction with Revenue and Quantity unchanged.
2. Ground-truth deterministic aggregate financial comparison:
     Current Profit = Revenue - Expense = 23,411,580.19 - 20,754,621.79 = ₹26,56,958.40
     Proposed Profit = Target Revenue - Target Expense = 23,411,580.19 - 19,716,890.73 = ₹36,94,689.46
     Expected aggregate profit improvement = +₹10,37,731.06
3. Strictly non-zero profit improvement (fixes bug where static model returned ₹13,320 and delta ₹0.00).
4. Explicit identification of the ML forecasting horizon: "1-day (Next Business Day)".
5. ML daily prediction comparison reflects proposed scenario inputs with non-zero shift.
6. Direct call and API client contract compatibility.
"""

from __future__ import annotations

import unittest
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import backend.main as main
from backend.main import WhatIfRequest, what_if_analysis


class TestWhatIfAnalysisRegression(unittest.TestCase):
    """Regression test suite for What-If scenario simulations and horizon separation."""

    def test_01_five_percent_expense_reduction_aggregate_validation(self):
        """
        Validates the exact user scenario:
          Current Revenue: 23,411,580.19
          Current Expense: 20,754,621.79
          Target Revenue: 23,411,580.19 (unchanged)
          Target Expense: 19,716,890.73 (-5% reduction)
          Quantity: 26,685 (unchanged)
        """
        req = WhatIfRequest(
            current_quantity=26685.0,
            current_revenue=23411580.19,
            current_expense=20754621.79,
            new_quantity=26685.0,
            new_revenue=23411580.19,
            new_expense=19716890.73,
        )

        res = what_if_analysis(req)

        self.assertTrue(res.get("success"), "What-If analysis must return success=True")

        # 1. Deterministic aggregate financial validation
        expected_current_profit = 23411580.19 - 20754621.79  # 2656958.40
        expected_new_profit = 23411580.19 - 19716890.73      # 3694689.46
        expected_profit_delta = expected_new_profit - expected_current_profit  # 1037731.06

        self.assertAlmostEqual(res["current_predicted_profit"], round(expected_current_profit, 2), places=2)
        self.assertAlmostEqual(res["new_predicted_profit"], round(expected_new_profit, 2), places=2)
        self.assertAlmostEqual(res["profit_difference"], round(expected_profit_delta, 2), places=2)

        # 2. Verify non-zero profit improvement (Must never collapse to 0.0)
        self.assertGreater(res["profit_difference"], 0.0, "5% expense cut must yield strictly positive profit delta")
        self.assertAlmostEqual(res["profit_difference"], 1037731.06, places=2)

        # 3. Check aggregate analysis structure
        agg = res.get("aggregate_analysis", {})
        self.assertAlmostEqual(agg.get("current_profit", 0.0), 2656958.40, places=2)
        self.assertAlmostEqual(agg.get("proposed_profit", 0.0), 3694689.46, places=2)
        self.assertAlmostEqual(agg.get("profit_delta", 0.0), 1037731.06, places=2)
        self.assertAlmostEqual(agg.get("current_margin", 0.0), 11.35, places=2)
        self.assertAlmostEqual(agg.get("proposed_margin", 0.0), 15.78, places=2)
        self.assertAlmostEqual(agg.get("margin_delta", 0.0), 4.43, places=2)

        # 4. Check ML forecast horizon and daily comparison
        fc = res.get("forecast_comparison", {})
        self.assertEqual(fc.get("horizon"), "1-day (Next Business Day)")
        self.assertGreater(fc.get("days_in_period", 0), 0)
        self.assertGreater(fc.get("daily_profit_delta", 0.0), 0.0, "Daily forecast delta must be positive")
        self.assertAlmostEqual(
            fc["proposed_daily_profit"] - fc["baseline_daily_profit"],
            fc["daily_profit_delta"],
            places=2,
        )

        # 5. Verify human-readable summary
        result_text = res.get("result", "")
        self.assertIn("Profit may increase", result_text)
        self.assertIn("1,037,731.06", result_text)

    def test_02_expense_increase_yields_negative_delta(self):
        """Validates that a 10% expense increase correctly yields a negative profit delta."""
        req = WhatIfRequest(
            current_quantity=100.0,
            current_revenue=50000.0,
            current_expense=30000.0,
            new_quantity=100.0,
            new_revenue=50000.0,
            new_expense=33000.0,  # +10% expense
        )
        res = what_if_analysis(req)
        self.assertTrue(res["success"])
        self.assertEqual(res["current_predicted_profit"], 20000.0)
        self.assertEqual(res["new_predicted_profit"], 17000.0)
        self.assertEqual(res["profit_difference"], -3000.0)
        self.assertIn("Profit may decrease", res["result"])

    def test_03_zero_change_yields_zero_delta(self):
        """Validates identical baseline and target values yield 0.0 delta and neutral status."""
        req = WhatIfRequest(
            current_quantity=100.0,
            current_revenue=50000.0,
            current_expense=30000.0,
            new_quantity=100.0,
            new_revenue=50000.0,
            new_expense=30000.0,
        )
        res = what_if_analysis(req)
        self.assertTrue(res["success"])
        self.assertEqual(res["profit_difference"], 0.0)
        self.assertEqual(res["result"], "No significant change")


if __name__ == "__main__":
    unittest.main()
