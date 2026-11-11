"""
EVORA Dataset Pipeline Test Suite
=================================
Validates:
1. CSV upload and parsing.
2. Missing values handling (ensuring no literal 'nan' string conversions).
3. Alternative column names ('Sales', 'Total Sales', 'Amount', 'Qty', 'Cost', 'Product Name').
4. Numeric conversion with currency symbol stripping ($, ₹, €, £, commas).
5. Date conversion and handling of invalid dates.
6. Excel (.xlsx) file loading and parsing.
7. Path traversal prevention and ownership enforcement.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from backend.auth import database, initialize_database
from tools.dataset_tools import (
    DatasetAccessError,
    identify_semantic_columns,
    load_user_dataset,
    resolve_safe_dataset_path,
    sanitize_dataframe,
)


class TestDatasetPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="evora_dataset_test_")
        cls.db_path = Path(cls.test_dir) / "evora_test.db"
        cls.upload_dir = Path(cls.test_dir) / "uploads"
        cls.upload_dir.mkdir(parents=True, exist_ok=True)

        os.environ["EVORA_DB_PATH"] = str(cls.db_path)
        os.environ["EVORA_UPLOAD_DIR"] = str(cls.upload_dir)

        import backend.auth as auth_mod
        auth_mod.DB_PATH = cls.db_path
        initialize_database()

        cls.user_id = "dataset_test_user_01"
        with database() as conn:
            conn.execute(
                "INSERT INTO users (id, full_name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (cls.user_id, "Data Tester", "data_tester@evora.ai", "dummy_hash", 1700000000),
            )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_alternative_column_detection(self):
        """Verifies semantic identification of alternative column names."""
        columns = ["Sales", "Cost", "Qty", "Product Name", "Date"]
        mapping = identify_semantic_columns(columns)

        self.assertEqual(mapping.get("revenue"), "Sales")
        self.assertEqual(mapping.get("expense"), "Cost")
        self.assertEqual(mapping.get("quantity"), "Qty")
        self.assertEqual(mapping.get("product"), "Product Name")
        self.assertEqual(mapping.get("date"), "Date")

    def test_total_sales_and_amount_candidates(self):
        """Verifies 'Total Sales' and 'Amount' match revenue, and 'Total Cost' matches expense."""
        cols = ["Total Sales", "Total Cost", "Volume", "Item"]
        mapping = identify_semantic_columns(cols)

        self.assertEqual(mapping.get("revenue"), "Total Sales")
        self.assertEqual(mapping.get("expense"), "Total Cost")
        self.assertEqual(mapping.get("quantity"), "Volume")
        self.assertEqual(mapping.get("product"), "Item")

    def test_missing_values_and_no_literal_nan_string(self):
        """Verifies that missing values are handled safely and NEVER converted into literal 'nan' strings."""
        raw_df = pd.DataFrame([
            {"Product": None, "Category": None, "Region": None, "Revenue": "5000", "Expense": "3000"},
            {"Product": float("nan"), "Category": float("nan"), "Region": float("nan"), "Revenue": None, "Expense": None},
        ])

        mapping = identify_semantic_columns(list(raw_df.columns))
        clean_df = sanitize_dataframe(raw_df, mapping)

        for prod in clean_df["Product"]:
            self.assertNotEqual(str(prod).lower(), "nan", "Missing product must NOT become literal 'nan' string.")
            self.assertEqual(prod, "Unknown")

        for cat in clean_df["Category"]:
            self.assertNotEqual(str(cat).lower(), "nan", "Missing category must NOT become literal 'nan' string.")
            self.assertEqual(cat, "General")

        for reg in clean_df["Region"]:
            self.assertNotEqual(str(reg).lower(), "nan", "Missing region must NOT become literal 'nan' string.")
            self.assertEqual(reg, "All Regions")

        # Verify numeric columns filled cleanly
        self.assertEqual(clean_df["Revenue"].iloc[1], 0.0)
        self.assertEqual(clean_df["Expense"].iloc[1], 0.0)

    def test_currency_symbol_and_formatting_cleanup(self):
        """Verifies cleaning of currency symbols ($, ₹, €, £) and commas in numerical strings."""
        raw_df = pd.DataFrame([
            {"Revenue": "₹50,000.50", "Expense": "$25,000", "Quantity": "100"},
            {"Revenue": "€12,500.00", "Expense": "£8,200.75", "Quantity": " 50 "},
        ])

        mapping = identify_semantic_columns(list(raw_df.columns))
        clean_df = sanitize_dataframe(raw_df, mapping)

        self.assertAlmostEqual(clean_df["Revenue"].iloc[0], 50000.50)
        self.assertAlmostEqual(clean_df["Expense"].iloc[0], 25000.0)
        self.assertAlmostEqual(clean_df["Quantity"].iloc[0], 100.0)

        self.assertAlmostEqual(clean_df["Revenue"].iloc[1], 12500.00)
        self.assertAlmostEqual(clean_df["Expense"].iloc[1], 8200.75)
        self.assertAlmostEqual(clean_df["Quantity"].iloc[1], 50.0)

    def test_date_conversion_and_invalid_dates(self):
        """Verifies date normalization and graceful handling of invalid date formats."""
        raw_df = pd.DataFrame([
            {"Date": "2025-01-15", "Revenue": 1000, "Expense": 500},
            {"Date": "invalid-date-string", "Revenue": 2000, "Expense": 1000},
            {"Date": None, "Revenue": 3000, "Expense": 1500},
        ])

        mapping = identify_semantic_columns(list(raw_df.columns))
        clean_df = sanitize_dataframe(raw_df, mapping)

        self.assertFalse(pd.isna(clean_df["Date"].iloc[0]))
        self.assertTrue(pd.isna(clean_df["Date"].iloc[1]))
        self.assertTrue(pd.isna(clean_df["Date"].iloc[2]))

    def test_excel_file_loading(self):
        """Verifies reading an Excel (.xlsx) dataset file via load_user_dataset."""
        excel_path = self.upload_dir / "test_spreadsheet.xlsx"
        df_to_save = pd.DataFrame([
            {"Product": "Excel Item A", "Revenue": 15000, "Expense": 9000, "Quantity": 30},
            {"Product": "Excel Item B", "Revenue": 22000, "Expense": 14000, "Quantity": 45},
        ])
        df_to_save.to_excel(excel_path, index=False, engine="openpyxl")

        dataset_id = "ds_excel_001"
        with database() as conn:
            conn.execute(
                """
                INSERT INTO datasets (
                    id, user_id, original_filename, stored_filename, storage_path,
                    uploaded_at, row_count, column_count, columns_json, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dataset_id,
                    self.user_id,
                    "test_spreadsheet.xlsx",
                    "test_spreadsheet.xlsx",
                    str(excel_path),
                    1700000000,
                    2,
                    4,
                    '["Product", "Revenue", "Expense", "Quantity"]',
                    "ready",
                ),
            )

        loaded_df, meta = load_user_dataset(dataset_id, self.user_id)
        self.assertEqual(len(loaded_df), 2)
        self.assertEqual(loaded_df["Revenue"].sum(), 37000.0)
        self.assertEqual(meta["filename"], "test_spreadsheet.xlsx")

    def test_path_traversal_prevention(self):
        """Verifies that paths outside authorized upload storage are strictly rejected."""
        traversal_path = "../../etc/passwd"
        with self.assertRaises(DatasetAccessError):
            resolve_safe_dataset_path(traversal_path)

    def test_unauthorized_dataset_access_rejected(self):
        """Verifies that accessing a dataset owned by another user raises 404."""
        with self.assertRaises(DatasetAccessError) as ctx:
            load_user_dataset("ds_excel_001", "unauthorized_intruder")
        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
