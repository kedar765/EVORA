"""
EVORA Centralized Dataset Access & Validation Layer
===================================================
Provides secure, validated, and normalized dataset access for:
- Analytics Agent
- Risk Agent
- Decision Optimization Agent

Security & Validation Rules:
1. Verifies dataset ownership against SQLite `datasets` table.
2. Prevents directory traversal attacks by validating stored paths relative to `backend/storage/uploads`.
3. Sanitizes numerical fields (rejects or replaces infinite/NaN values with safe representations).
4. Conservative semantic column mapping (e.g. Sales -> revenue, Cost -> expense).
5. Exposes normalized metrics and clean DataFrames without leaking filesystem paths.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Workspace root configuration
ROOT_DIR = Path(__file__).resolve().parent.parent
UPLOAD_STORAGE_DIR = (ROOT_DIR / "backend" / "storage" / "uploads").resolve()

# Semantic column candidate patterns (lowercase, stripped)
COLUMN_CANDIDATES = {
    "revenue": [
        "revenue", "sales", "total sales", "net sales", "total revenue",
        "gross revenue", "gross sales", "turnover", "income", "amount"
    ],
    "expense": [
        "expense", "expenses", "cost", "costs", "total cost", "total expense",
        "expenditure", "spending"
    ],
    "profit": [
        "profit", "net profit", "operating profit", "gross profit", "earnings",
        "margin"
    ],
    "quantity": [
        "quantity", "qty", "volume", "units", "units sold", "orders",
        "order count", "count"
    ],
    "date": [
        "date", "order date", "transaction date", "timestamp", "time",
        "created_at", "invoice date"
    ],
    "product": [
        "product", "product name", "item", "item name", "sku", "service"
    ],
    "category": [
        "category", "segment", "product category", "department", "type", "sector"
    ],
    "region": [
        "region", "area", "location", "country", "state", "city", "territory", "market"
    ],
    "customer": [
        "customer", "customer name", "client", "client name", "account", "buyer"
    ],
}


class DatasetAccessError(Exception):
    """Base exception for dataset loading and security errors."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _get_database_connection():
    """Lazily import and connect to EVORA SQLite database."""
    from backend.auth import database
    return database()


def get_upload_storage_dir() -> Path:
    """Returns the configured upload storage root directory."""
    env_dir = os.getenv("EVORA_UPLOAD_DIR")
    if env_dir:
        return Path(env_dir).resolve()
    try:
        from backend.main import UPLOAD_STORAGE_DIR as backend_dir
        return Path(backend_dir).resolve()
    except Exception:
        return UPLOAD_STORAGE_DIR


def resolve_safe_dataset_path(storage_path_str: str) -> Path:
    """
    Validates that a dataset's storage path is strictly within the private uploads directory.
    Prevents path traversal vulnerabilities.
    """
    upload_root = get_upload_storage_dir()
    stored_path = Path(storage_path_str)
    if stored_path.is_absolute():
        resolved_path = stored_path.resolve()
    else:
        resolved_path = (ROOT_DIR / stored_path).resolve()

    try:
        resolved_path.relative_to(upload_root)
    except ValueError as exc:
        raise DatasetAccessError(
            "Access denied: Dataset path points outside authorized storage directory.",
            status_code=403,
        ) from exc

    if not resolved_path.is_file():
        raise DatasetAccessError(
            "Dataset storage file could not be found.",
            status_code=404,
        )

    return resolved_path


def identify_semantic_columns(columns: List[str]) -> Dict[str, str]:
    """
    Conservatively maps dataset columns to standardized semantic business roles.
    Returns mapping: {standard_name: actual_dataset_column}
    """
    mapping: Dict[str, str] = {}
    normalized_cols = {col: col.strip().lower() for col in columns}

    for standard_name, candidates in COLUMN_CANDIDATES.items():
        matched_actual: Optional[str] = None

        # 1. Exact match check
        for actual, norm in normalized_cols.items():
            if norm in candidates:
                matched_actual = actual
                break

        # 2. Substring match check if not matched yet
        if matched_actual is None:
            for actual, norm in normalized_cols.items():
                if any(cand == norm or f" {cand}" in norm or f"{cand} " in norm for cand in candidates):
                    matched_actual = actual
                    break

        if matched_actual is not None:
            mapping[standard_name] = matched_actual

    return mapping


def _clean_numeric_series(series: pd.Series, default: float = 0.0) -> pd.Series:
    """Cleans numeric series, stripping currency symbols, commas, and whitespace."""
    if not pd.api.types.is_numeric_dtype(series):
        s_clean = (
            series.astype(str)
            .str.replace(r"[\$,₹,€,£,\s]", "", regex=True)
            .str.replace(",", "", regex=False)
        )
        return pd.to_numeric(s_clean, errors="coerce").fillna(default)
    return pd.to_numeric(series, errors="coerce").fillna(default)


def sanitize_dataframe(df: pd.DataFrame, semantic_mapping: Dict[str, str]) -> pd.DataFrame:
    """
    Sanitizes values, standardizes types, handles missing data, and creates canonical columns.
    Avoids converting missing values into literal 'nan' strings.
    """
    clean_df = df.copy()

    # Deduplicate column names if any
    clean_df.columns = [str(c).strip() for c in clean_df.columns]
    if len(clean_df.columns) != len(set(clean_df.columns)):
        clean_df = clean_df.loc[:, ~clean_df.columns.duplicated(keep="first")]

    # Normalize canonical columns based on semantic mapping
    if "revenue" in semantic_mapping:
        clean_df["Revenue"] = _clean_numeric_series(
            clean_df[semantic_mapping["revenue"]], 0.0
        )
    elif "Revenue" not in clean_df.columns:
        clean_df["Revenue"] = 0.0

    if "expense" in semantic_mapping:
        clean_df["Expense"] = _clean_numeric_series(
            clean_df[semantic_mapping["expense"]], 0.0
        )
    elif "Expense" not in clean_df.columns:
        clean_df["Expense"] = 0.0

    # Ensure Profit exists and is consistent
    if "profit" in semantic_mapping and semantic_mapping["profit"] in clean_df.columns:
        clean_df["Profit"] = _clean_numeric_series(
            clean_df[semantic_mapping["profit"]], 0.0
        )
    else:
        clean_df["Profit"] = clean_df["Revenue"] - clean_df["Expense"]

    # Normalize Quantity
    if "quantity" in semantic_mapping:
        clean_df["Quantity"] = _clean_numeric_series(
            clean_df[semantic_mapping["quantity"]], 1.0
        )
    elif "Quantity" not in clean_df.columns:
        clean_df["Quantity"] = 1.0

    # Normalize Date
    if "date" in semantic_mapping:
        clean_df["Date"] = pd.to_datetime(
            clean_df[semantic_mapping["date"]], errors="coerce"
        )
    elif "Date" in clean_df.columns:
        clean_df["Date"] = pd.to_datetime(clean_df["Date"], errors="coerce")

    # Normalize Product (avoid literal 'nan' strings)
    if "product" in semantic_mapping:
        raw_prod = clean_df[semantic_mapping["product"]].fillna("Unknown").astype(str)
        clean_df["Product"] = raw_prod.replace(
            {"nan": "Unknown", "None": "Unknown", "null": "Unknown", "": "Unknown"}
        )
    elif "Product" not in clean_df.columns:
        clean_df["Product"] = "All Products"

    # Normalize Category (avoid literal 'nan' strings)
    if "category" in semantic_mapping:
        raw_cat = clean_df[semantic_mapping["category"]].fillna("General").astype(str)
        clean_df["Category"] = raw_cat.replace(
            {"nan": "General", "None": "General", "null": "General", "": "General"}
        )

    # Normalize Region (avoid literal 'nan' strings)
    if "region" in semantic_mapping:
        raw_reg = clean_df[semantic_mapping["region"]].fillna("All Regions").astype(str)
        clean_df["Region"] = raw_reg.replace(
            {"nan": "All Regions", "None": "All Regions", "null": "All Regions", "": "All Regions"}
        )

    # Clean non-finite numbers in numeric columns
    numeric_cols = clean_df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        clean_df[col] = clean_df[col].replace([np.inf, -np.inf], np.nan).fillna(0.0)

    return clean_df


def load_user_dataset(
    dataset_id: str,
    user_id: str,
    max_rows: Optional[int] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Securely loads and validates an uploaded dataset belonging to the authenticated user.
    Supports CSV and Excel (.xlsx, .xls) formats.

    Returns:
        (sanitized_df, metadata_dict)
    """
    if not dataset_id or not str(dataset_id).strip():
        raise DatasetAccessError("Dataset ID is required.", status_code=400)
    if not user_id or not str(user_id).strip():
        raise DatasetAccessError("User ID is required.", status_code=401)

    with _get_database_connection() as conn:
        row = conn.execute(
            """
            SELECT id, user_id, original_filename, stored_filename,
                   storage_path, uploaded_at, row_count, column_count,
                   columns_json, date_start, date_end, status
            FROM datasets
            WHERE id = ? AND user_id = ?
            """,
            (dataset_id, user_id),
        ).fetchone()

    if row is None:
        raise DatasetAccessError(
            f"Dataset '{dataset_id}' not found or access unauthorized for this user.",
            status_code=404,
        )

    file_path = resolve_safe_dataset_path(row["storage_path"])
    suffix = file_path.suffix.lower()

    try:
        if suffix in [".xlsx", ".xls"]:
            raw_df = pd.read_excel(file_path, nrows=max_rows, engine="openpyxl" if suffix == ".xlsx" else None)
        else:
            raw_df = pd.read_csv(file_path, nrows=max_rows)
    except Exception as exc:
        raise DatasetAccessError(
            f"Failed to read dataset file: {exc}",
            status_code=400,
        ) from exc

    if raw_df.empty:
        raise DatasetAccessError(
            "Dataset is empty and contains no transaction records.",
            status_code=400,
        )

    semantic_mapping = identify_semantic_columns(list(raw_df.columns))
    clean_df = sanitize_dataframe(raw_df, semantic_mapping)

    # Calculate date range if date column present
    date_start = row["date_start"]
    date_end = row["date_end"]
    if "Date" in clean_df.columns:
        valid_dates = clean_df["Date"].dropna()
        if not valid_dates.empty:
            date_start = valid_dates.min().strftime("%Y-%m-%d")
            date_end = valid_dates.max().strftime("%Y-%m-%d")

    metadata = {
        "dataset_id": dataset_id,
        "filename": row["original_filename"],
        "row_count": len(clean_df),
        "column_count": len(clean_df.columns),
        "original_columns": list(raw_df.columns),
        "semantic_mapping": semantic_mapping,
        "has_date": bool("Date" in clean_df.columns and clean_df["Date"].notna().any()),
        "has_product": bool("Product" in clean_df.columns),
        "has_category": bool("Category" in clean_df.columns),
        "has_region": bool("Region" in clean_df.columns),
        "date_start": date_start,
        "date_end": date_end,
    }


    return clean_df, metadata
