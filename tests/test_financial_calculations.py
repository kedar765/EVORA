"""
Unit tests validating EVORA ground-truth financial calculations and data sanitization:
1. Profit = Revenue - Expense
2. Profit Margin (%) = (Profit / Revenue) * 100
3. Revenue = Quantity * Unit_Price (when direct Revenue is missing)
4. Expense = Quantity * Unit_Cost (when direct Expense is missing)
5. Zero revenue edge case: Margin = 0.0 without ZeroDivisionError
6. Currency and delimiter stripping ($, ₹, €, £, commas)
7. Non-finite, NaN, and null values handled safely without 'nan' string pollution.
"""

import json
import unittest
import pandas as pd
import numpy as np

from tools.dataset_tools import (
    identify_semantic_columns,
    sanitize_dataframe,
    _clean_numeric_series,
)
from tools.analytics_tools import calculate_business_metrics


class TestFinancialCalculations(unittest.TestCase):
    """Verifies strict financial calculation formulas and edge case handling."""

    def test_profit_and_margin_ground_truth(self):
        """Validates Profit = Revenue - Expense and Profit Margin (%) = (Profit / Revenue) * 100."""
        df = pd.DataFrame({
            "Revenue": [1000.0, 500.0, 200.0],
            "Expense": [600.0, 400.0, 250.0],
        })
        mapping = identify_semantic_columns(list(df.columns))
        clean_df = sanitize_dataframe(df, mapping)

        # Row 1: 1000 - 600 = 400 -> 40%
        # Row 2: 500 - 400 = 100 -> 20%
        # Row 3: 200 - 250 = -50 -> -25%
        self.assertAlmostEqual(clean_df["Profit"].iloc[0], 400.0)
        self.assertAlmostEqual(clean_df["Profit_Margin"].iloc[0], 40.0)

        self.assertAlmostEqual(clean_df["Profit"].iloc[1], 100.0)
        self.assertAlmostEqual(clean_df["Profit_Margin"].iloc[1], 20.0)

        self.assertAlmostEqual(clean_df["Profit"].iloc[2], -50.0)
        self.assertAlmostEqual(clean_df["Profit_Margin"].iloc[2], -25.0)

        # Aggregate consistency
        tot_rev = clean_df["Revenue"].sum()
        tot_exp = clean_df["Expense"].sum()
        tot_prof = clean_df["Profit"].sum()
        self.assertAlmostEqual(tot_prof, tot_rev - tot_exp)
        agg_margin = (tot_prof / tot_rev) * 100.0
        self.assertAlmostEqual(agg_margin, (450.0 / 1700.0) * 100.0)

    def test_zero_and_negative_revenue_safe_margin(self):
        """Validates that zero revenue safely evaluates to 0.0 margin with no division by zero."""
        df = pd.DataFrame({
            "Revenue": [0.0, 0.0, 100.0],
            "Expense": [50.0, 0.0, 80.0],
        })
        mapping = identify_semantic_columns(list(df.columns))
        clean_df = sanitize_dataframe(df, mapping)

        # Zero revenue must not divide by zero
        self.assertEqual(clean_df["Profit_Margin"].iloc[0], 0.0)
        self.assertEqual(clean_df["Profit_Margin"].iloc[1], 0.0)
        self.assertAlmostEqual(clean_df["Profit_Margin"].iloc[2], 20.0)

    def test_derived_revenue_and_expense_from_rates(self):
        """Validates Revenue = Quantity * Unit_Price and Expense = Quantity * Unit_Cost."""
        df = pd.DataFrame({
            "units_sold": [10, 5, 20],
            "unit_price": [100.0, 50.0, 25.0],
            "unit_cost": [60.0, 30.0, 15.0],
        })
        mapping = identify_semantic_columns(list(df.columns))
        clean_df = sanitize_dataframe(df, mapping)

        # Row 0: Rev = 10 * 100 = 1000, Exp = 10 * 60 = 600, Profit = 400
        self.assertAlmostEqual(clean_df["Revenue"].iloc[0], 1000.0)
        self.assertAlmostEqual(clean_df["Expense"].iloc[0], 600.0)
        self.assertAlmostEqual(clean_df["Profit"].iloc[0], 400.0)
        self.assertAlmostEqual(clean_df["Profit_Margin"].iloc[0], 40.0)

        # Row 1: Rev = 5 * 50 = 250, Exp = 5 * 30 = 150, Profit = 100
        self.assertAlmostEqual(clean_df["Revenue"].iloc[1], 250.0)
        self.assertAlmostEqual(clean_df["Expense"].iloc[1], 150.0)
        self.assertAlmostEqual(clean_df["Profit"].iloc[1], 100.0)
        self.assertAlmostEqual(clean_df["Profit_Margin"].iloc[1], 40.0)

    def test_currency_and_delimiter_cleaning(self):
        """Validates that strings with $, ₹, €, £, commas, and whitespace parse accurately."""
        series = pd.Series(["$1,250.50", "₹ 50,000", "€100.00", "£500", "  2,000.25  ", None, "invalid"])
        cleaned = _clean_numeric_series(series, default=0.0)

        self.assertAlmostEqual(cleaned.iloc[0], 1250.50)
        self.assertAlmostEqual(cleaned.iloc[1], 50000.0)
        self.assertAlmostEqual(cleaned.iloc[2], 100.00)
        self.assertAlmostEqual(cleaned.iloc[3], 500.0)
        self.assertAlmostEqual(cleaned.iloc[4], 2000.25)
        self.assertAlmostEqual(cleaned.iloc[5], 0.0)
        self.assertAlmostEqual(cleaned.iloc[6], 0.0)

    def test_nan_pollution_prevention(self):
        """Validates that NaN/missing string fields are replaced with clean categorical defaults."""
        df = pd.DataFrame({
            "sales": [100.0, 200.0, 300.0],
            "costs": [50.0, 100.0, 150.0],
            "product_name": ["Widget A", np.nan, None],
            "category": [np.nan, "Electronics", "  "],
            "region": [None, np.nan, "North"],
        })
        mapping = identify_semantic_columns(list(df.columns))
        clean_df = sanitize_dataframe(df, mapping)

        self.assertEqual(clean_df["Product"].iloc[0], "Widget A")
        self.assertEqual(clean_df["Product"].iloc[1], "Unknown")
        self.assertEqual(clean_df["Product"].iloc[2], "Unknown")

        self.assertEqual(clean_df["Category"].iloc[0], "General")
        self.assertEqual(clean_df["Category"].iloc[1], "Electronics")
        self.assertEqual(clean_df["Category"].iloc[2], "General")

        self.assertEqual(clean_df["Region"].iloc[0], "All Regions")
        self.assertEqual(clean_df["Region"].iloc[1], "All Regions")
        self.assertEqual(clean_df["Region"].iloc[2], "North")


    def test_verified_first_record_financial_mapping(self):
        """
        Tests the exact verified first dataset record from user audit:
        Date: 2025-11-14, Quantity: 24, Revenue: 29217.12, Unit_Cost: 706.01,
        Expense: 17927.67, Profit: 11289.45.
        Verifies Unit_Cost is never mapped to Expense, total Expense is preserved,
        and Profit = Revenue - Expense is strictly 11289.45 (NEVER 28511.11).
        """
        df = pd.DataFrame([{
            "Date": "2025-11-14",
            "Order_ID": "EV-20251114",
            "Product": "Laptop Stand",
            "Category": "Accessories",
            "Region": "Pune",
            "Quantity": 24,
            "Unit_Price": 1217.38,
            "Revenue": 29217.12,
            "Unit_Cost": 706.01,
            "Expense": 17927.67,
            "Profit": 11289.45,
        }])
        mapping = identify_semantic_columns(list(df.columns))
        self.assertEqual(mapping.get("revenue"), "Revenue")
        self.assertEqual(mapping.get("expense"), "Expense")
        self.assertEqual(mapping.get("unit_cost"), "Unit_Cost")
        self.assertNotEqual(mapping.get("expense"), "Unit_Cost")

        clean_df = sanitize_dataframe(df, mapping)
        self.assertAlmostEqual(clean_df["Revenue"].iloc[0], 29217.12)
        self.assertAlmostEqual(clean_df["Expense"].iloc[0], 17927.67)
        self.assertNotEqual(clean_df["Expense"].iloc[0], 706.01)
        self.assertAlmostEqual(clean_df["Profit"].iloc[0], 11289.45)
        self.assertNotEqual(clean_df["Profit"].iloc[0], 28511.11)
        expected_margin = (11289.45 / 29217.12) * 100.0
        self.assertAlmostEqual(clean_df["Profit_Margin"].iloc[0], expected_margin)

    def test_derived_expense_when_only_unit_cost_present(self):
        """Verifies missing Expense is derived as Quantity * Unit_Cost without overwriting existing Expense."""
        df = pd.DataFrame([{
            "Quantity": 10,
            "Revenue": 5000.0,
            "Unit_Cost": 250.0,
        }])
        mapping = identify_semantic_columns(list(df.columns))
        self.assertEqual(mapping.get("unit_cost"), "Unit_Cost")
        self.assertNotIn("expense", mapping)

        clean_df = sanitize_dataframe(df, mapping)
        # Expected: Expense = 10 * 250.0 = 2500.0, Profit = 5000.0 - 2500.0 = 2500.0
        self.assertAlmostEqual(clean_df["Expense"].iloc[0], 2500.0)
        self.assertAlmostEqual(clean_df["Profit"].iloc[0], 2500.0)
        self.assertAlmostEqual(clean_df["Profit_Margin"].iloc[0], 50.0)


if __name__ == "__main__":
    unittest.main()
