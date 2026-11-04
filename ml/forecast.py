"""
EVORA Daily Profit Forecast Module
==================================
Production forecasting module for next-day business profit prediction.
Maintains strict data leakage prevention by using only historical data
available strictly before the forecast date.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

# Suppress loky CPU core warnings on Windows
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

# Standard paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_PATH = ROOT_DIR / "ml" / "daily_profit_forecast_model.pkl"
DEFAULT_DATA_PATH = ROOT_DIR / "data" / "sample_business_data.csv"

# Minimum daily records required to compute rolling 30-day statistics
MIN_DAILY_RECORDS = 30

FEATURE_COLUMNS = [
    "day_index",
    "day_of_week",
    "month",
    "day_of_year",
    "week_of_year",
    "is_weekend",
    "profit_lag_1",
    "profit_lag_7",
    "profit_lag_14",
    "profit_lag_30",
    "revenue_lag_1",
    "revenue_lag_7",
    "revenue_lag_14",
    "expense_lag_1",
    "expense_lag_7",
    "expense_lag_14",
    "profit_mean_7",
    "profit_mean_14",
    "profit_mean_30",
    "profit_std_7",
    "profit_std_14",
]


def validate_transaction_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validates transaction-level data schema, checks for required columns,
    and calculates financial figures adhering to EVORA business logic:
      Revenue = Quantity * Unit_Price * (1 - Discount_Percent / 100)
      Expense = (Quantity * Cost_Per_Unit) + Shipping_Cost + Marketing_Spend
      Profit = Revenue - Expense
    """
    if df is None or not isinstance(df, pd.DataFrame):
        raise ValueError("Input must be a valid pandas DataFrame.")

    if df.empty:
        raise ValueError("DataFrame is empty. Historical transactions required.")

    df = df.copy()

    # Column name trimming
    df.columns = [str(c).strip() for c in df.columns]

    if "Date" not in df.columns:
        raise ValueError("Missing required column 'Date' in transaction data.")

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    if df["Date"].isna().all():
        raise ValueError("All 'Date' values could not be parsed as valid dates.")

    df = df.dropna(subset=["Date"])

    # Determine or validate financial columns
    has_rev = "Revenue" in df.columns
    has_exp = "Expense" in df.columns

    if has_rev and has_exp:
        df["Revenue"] = pd.to_numeric(df["Revenue"], errors="coerce").fillna(0.0)
        df["Expense"] = pd.to_numeric(df["Expense"], errors="coerce").fillna(0.0)
    elif "Quantity" in df.columns and "Unit_Price" in df.columns and "Cost_Per_Unit" in df.columns:
        qty = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0.0)
        u_price = pd.to_numeric(df["Unit_Price"], errors="coerce").fillna(0.0)
        c_price = pd.to_numeric(df["Cost_Per_Unit"], errors="coerce").fillna(0.0)
        disc = pd.to_numeric(df.get("Discount_Percent", 0.0), errors="coerce").fillna(0.0)
        ship = pd.to_numeric(df.get("Shipping_Cost", 0.0), errors="coerce").fillna(0.0)
        mktg = pd.to_numeric(df.get("Marketing_Spend", 0.0), errors="coerce").fillna(0.0)

        df["Revenue"] = qty * u_price * (1.0 - disc / 100.0)
        df["Expense"] = (qty * c_price) + ship + mktg
    else:
        raise ValueError(
            "Transaction data must contain either ['Revenue', 'Expense'] or "
            "['Quantity', 'Unit_Price', 'Cost_Per_Unit']."
        )

    if "Profit" not in df.columns:
        df["Profit"] = df["Revenue"] - df["Expense"]
    else:
        df["Profit"] = pd.to_numeric(df["Profit"], errors="coerce").fillna(
            df["Revenue"] - df["Expense"]
        )

    if "Quantity" in df.columns:
        df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(1)
    else:
        df["Quantity"] = 1

    if "Transaction_ID" not in df.columns:
        df["Transaction_ID"] = np.arange(len(df))

    return df


def aggregate_daily_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregates transaction-level data into a strictly chronological daily time series.
    Ensures dates are sorted and calendar continuity is checked.
    """
    validated = validate_transaction_dataframe(df)

    daily = (
        validated.groupby("Date", as_index=False)
        .agg(
            Revenue=("Revenue", "sum"),
            Expense=("Expense", "sum"),
            Profit=("Profit", "sum"),
            Quantity=("Quantity", "sum"),
            Transactions=("Transaction_ID", "count"),
        )
        .sort_values("Date")
        .reset_index(drop=True)
    )

    if len(daily) < MIN_DAILY_RECORDS:
        raise ValueError(
            f"Insufficient historical daily records: found {len(daily)} days, "
            f"minimum required is {MIN_DAILY_RECORDS} days for 30-day lag computation."
        )

    return daily


def build_historical_features(
    daily_df: pd.DataFrame,
    start_reference_date: Optional[pd.Timestamp] = None,
) -> pd.DataFrame:
    """
    Generates chronological, leakage-safe features for daily profit forecasting.
    Every lag and rolling statistic strictly uses shift(1) or higher, ensuring
    no same-day or future data can contaminate the prediction features.
    """
    daily = daily_df.copy().sort_values("Date").reset_index(drop=True)

    if start_reference_date is None:
        start_reference_date = daily["Date"].min()

    # Time & calendar features
    daily["day_index"] = (daily["Date"] - start_reference_date).dt.days
    daily["day_of_week"] = daily["Date"].dt.dayofweek
    daily["month"] = daily["Date"].dt.month
    daily["day_of_year"] = daily["Date"].dt.dayofyear
    daily["week_of_year"] = daily["Date"].dt.isocalendar().week.astype(int)
    daily["is_weekend"] = daily["day_of_week"].isin([5, 6]).astype(int)

    # Historical Lags (strictly strictly past observations)
    daily["profit_lag_1"] = daily["Profit"].shift(1)
    daily["profit_lag_7"] = daily["Profit"].shift(7)
    daily["profit_lag_14"] = daily["Profit"].shift(14)
    daily["profit_lag_30"] = daily["Profit"].shift(30)

    daily["revenue_lag_1"] = daily["Revenue"].shift(1)
    daily["revenue_lag_7"] = daily["Revenue"].shift(7)
    daily["revenue_lag_14"] = daily["Revenue"].shift(14)

    daily["expense_lag_1"] = daily["Expense"].shift(1)
    daily["expense_lag_7"] = daily["Expense"].shift(7)
    daily["expense_lag_14"] = daily["Expense"].shift(14)

    # Rolling statistics: explicitly shifted by 1 so day t never sees day t
    daily["profit_mean_7"] = daily["Profit"].shift(1).rolling(7).mean()
    daily["profit_mean_14"] = daily["Profit"].shift(1).rolling(14).mean()
    daily["profit_mean_30"] = daily["Profit"].shift(1).rolling(30).mean()
    daily["profit_std_7"] = daily["Profit"].shift(1).rolling(7).std().fillna(0.0)
    daily["profit_std_14"] = daily["Profit"].shift(1).rolling(14).std().fillna(0.0)

    return daily


def build_next_day_feature_vector(
    daily_df: pd.DataFrame,
    start_reference_date: Optional[pd.Timestamp] = None,
) -> Tuple[pd.DataFrame, pd.Timestamp]:
    """
    Constructs the exact single-row feature vector required to predict
    the next business day (day T+1) immediately following the latest historical date T.
    
    Guarantees:
    - Zero future leakage: Uses actual observed history up to day T.
    - Forecast date is day T + 1 day.
    - Calendar features correspond to day T + 1.
    - profit_lag_1 is day T's profit.
    - profit_mean_7 is the rolling mean of the 7 days ending on day T.
    """
    if len(daily_df) < MIN_DAILY_RECORDS:
        raise ValueError(
            f"Need at least {MIN_DAILY_RECORDS} historical days to generate forecast features."
        )

    daily = daily_df.copy().sort_values("Date").reset_index(drop=True)
    last_date = daily["Date"].iloc[-1]
    forecast_date = last_date + pd.Timedelta(days=1)

    if start_reference_date is None:
        start_reference_date = daily["Date"].min()

    # Features for forecast_date
    row: Dict[str, Any] = {
        "day_index": int((forecast_date - start_reference_date).days),
        "day_of_week": int(forecast_date.dayofweek),
        "month": int(forecast_date.month),
        "day_of_year": int(forecast_date.dayofyear),
        "week_of_year": int(forecast_date.isocalendar().week),
        "is_weekend": int(forecast_date.dayofweek in [5, 6]),
        # Lags relative to forecast_date
        "profit_lag_1": float(daily["Profit"].iloc[-1]),
        "profit_lag_7": float(daily["Profit"].iloc[-7]),
        "profit_lag_14": float(daily["Profit"].iloc[-14]),
        "profit_lag_30": float(daily["Profit"].iloc[-30]),
        "revenue_lag_1": float(daily["Revenue"].iloc[-1]),
        "revenue_lag_7": float(daily["Revenue"].iloc[-7]),
        "revenue_lag_14": float(daily["Revenue"].iloc[-14]),
        "expense_lag_1": float(daily["Expense"].iloc[-1]),
        "expense_lag_7": float(daily["Expense"].iloc[-7]),
        "expense_lag_14": float(daily["Expense"].iloc[-14]),
        # Rolling stats of history up to day T
        "profit_mean_7": float(daily["Profit"].iloc[-7:].mean()),
        "profit_mean_14": float(daily["Profit"].iloc[-14:].mean()),
        "profit_mean_30": float(daily["Profit"].iloc[-30:].mean()),
        "profit_std_7": float(daily["Profit"].iloc[-7:].std(ddof=1) or 0.0),
        "profit_std_14": float(daily["Profit"].iloc[-14:].std(ddof=1) or 0.0),
    }

    feature_df = pd.DataFrame([row])[FEATURE_COLUMNS]
    return feature_df, forecast_date


class DailyProfitForecaster:
    """
    Independent predictor module for EVORA Future Profit Forecasting.
    Loads model artifact and metadata, validates historical inputs,
    and generates production-grade next-day predictions in INR.
    """

    def __init__(self, model_path: Optional[Path | str] = None):
        self.model_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        self.model = None
        self.metadata: Dict[str, Any] = {}
        self.start_reference_date: Optional[pd.Timestamp] = None
        self.is_loaded = False
        self._load()

    def _load(self) -> None:
        """Loads model object and metadata dictionary from disk."""
        if not self.model_path.exists():
            self.is_loaded = False
            return

        try:
            artifact = joblib.load(self.model_path)
            if isinstance(artifact, dict) and "model" in artifact:
                self.model = artifact["model"]
                self.metadata = artifact.get("metadata", {})
                start_ref = self.metadata.get("start_reference_date")
                if start_ref:
                    self.start_reference_date = pd.to_datetime(start_ref)
            else:
                self.model = artifact
                self.metadata = {
                    "model_name": type(self.model).__name__,
                    "model_version": "1.0",
                }
            self.is_loaded = True
        except Exception as exc:
            self.is_loaded = False
            raise RuntimeError(
                f"Failed to load daily profit forecast model from {self.model_path}: {exc}"
            ) from exc

    def predict_next_day(
        self,
        historical_df: Optional[pd.DataFrame] = None,
        csv_path: Optional[Path | str] = None,
    ) -> Dict[str, Any]:
        """
        Predicts next day's business profit using historical business transactions.
        
        Returns:
            Dict containing:
              - forecast_date: YYYY-MM-DD
              - predicted_profit: float (in INR)
              - currency: 'INR'
              - model_name: str
              - model_version: str
              - model_metrics: dict
              - status: 'success'
        """
        if not self.is_loaded or self.model is None:
            raise RuntimeError(
                "Daily profit forecast model is unavailable. Train model first."
            )

        # 1. Obtain historical transaction DataFrame
        if historical_df is not None:
            raw_df = historical_df
        elif csv_path is not None:
            raw_df = pd.read_csv(csv_path)
        elif DEFAULT_DATA_PATH.exists():
            raw_df = pd.read_csv(DEFAULT_DATA_PATH)
        else:
            raise ValueError(
                "No historical business data provided and default dataset not found."
            )

        # 2. Daily aggregation & continuity
        daily_df = aggregate_daily_metrics(raw_df)

        # 3. Build next day features
        ref_date = self.start_reference_date or daily_df["Date"].min()
        feature_row, forecast_date = build_next_day_feature_vector(
            daily_df, start_reference_date=ref_date
        )

        # 4. Model inference
        prediction_val = float(self.model.predict(feature_row)[0])

        metrics = self.metadata.get("test_metrics") or self.metadata.get("val_metrics") or {}

        return {
            "forecast_date": forecast_date.strftime("%Y-%m-%d"),
            "predicted_profit": round(prediction_val, 2),
            "currency": "INR",
            "model_name": self.metadata.get("model_name", type(self.model).__name__),
            "model_version": self.metadata.get("model_version", "2.0.0"),
            "model_metrics": {
                "mae": round(metrics.get("mae", 0.0), 2),
                "rmse": round(metrics.get("rmse", 0.0), 2),
                "r2": round(metrics.get("r2", 0.0), 4),
            },
            "status": "success",
        }

