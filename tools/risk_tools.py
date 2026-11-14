"""
EVORA Risk Tools
================
Production LangChain tools for financial risk assessment, anomaly detection,
loss pattern analysis, and forecast-driven risk mitigation.
Integrates existing IsolationForest and profit forecasting ML models.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
from langchain_core.tools import tool

from tools.dataset_tools import DatasetAccessError, load_user_dataset

ROOT_DIR = Path(__file__).resolve().parent.parent
ML_DIR = ROOT_DIR / "ml"
MODEL_FEATURES = [
    "Quantity",
    "Revenue",
    "Expense",
    "Profit_Margin",
    "Revenue_per_Unit",
    "Expense_per_Unit",
]

_anomaly_model = None
_profit_model = None


def _load_ml_model(filename: str):
    path = ML_DIR / filename
    if path.exists():
        try:
            return joblib.load(path)
        except Exception:
            return None
    return None


def compute_dataset_anomalies(df: pd.DataFrame, contamination: float = 0.05) -> Tuple[List[int], str]:
    """
    Computes statistical and ML anomalies on an active business dataset.
    Uses unsupervised IsolationForest for datasets with >= 15 records,
    and robust statistical IQR as fallback for small datasets.
    """
    from backend.features import prepare_features
    from sklearn.ensemble import IsolationForest

    features_df = prepare_features(df[["Quantity", "Revenue", "Expense"]].copy())

    if len(df) >= 15:
        try:
            iso = IsolationForest(
                n_estimators=100,
                contamination=contamination,
                random_state=42,
            )
            preds = iso.fit_predict(features_df[MODEL_FEATURES].astype(float))
            anomaly_indices = [int(i) for i, p in enumerate(preds) if p == -1]
            return anomaly_indices, "IsolationForest"
        except Exception:
            pass

    # Statistical fallback: IQR on Expense
    q1 = df["Expense"].quantile(0.25)
    q3 = df["Expense"].quantile(0.75)
    iqr = q3 - q1
    upper = q3 + (2.5 * iqr)
    anomaly_indices = [int(i) for i in df[df["Expense"] > upper].index]
    return anomaly_indices, "Statistical IQR"


@tool
def detect_anomalies(dataset_id: str, user_id: str) -> str:
    """
    Detects unusual, suspicious, or abnormal business transactions using the
    unsupervised IsolationForest machine learning model and statistical validation.
    """
    try:
        df, _ = load_user_dataset(dataset_id, user_id)
        anomaly_indices, method = compute_dataset_anomalies(df)
        anomaly_count = len(anomaly_indices)
        anomaly_pct = (anomaly_count / len(df) * 100) if len(df) > 0 else 0.0

        return json.dumps({
            "anomaly_detected": anomaly_count > 0,
            "anomaly_count": anomaly_count,
            "anomaly_percentage": round(anomaly_pct, 2),
            "sample_anomaly_indices": anomaly_indices[:10],
            "total_records_evaluated": len(df),
            "detection_method": method,
        })
    except DatasetAccessError as e:
        return json.dumps({"error": e.message})
    except Exception as e:
        return json.dumps({"error": f"Anomaly detection failed: {str(e)}"})


@tool
def analyze_revenue_drops(dataset_id: str, user_id: str) -> str:
    """
    Analyzes historical revenue declines, identifying consecutive drop periods,
    steepest drops, and revenue instability across periods.
    """
    try:
        df, meta = load_user_dataset(dataset_id, user_id)
        if "Date" not in df.columns or df["Date"].isna().all():
            return json.dumps({
                "available": False,
                "message": "Date column not available for revenue drop analysis."
            })

        date_df = df.copy()
        date_df["Date"] = pd.to_datetime(date_df["Date"], errors="coerce")
        date_df = date_df.dropna(subset=["Date"]).sort_values("Date")

        date_df["Period"] = date_df["Date"].dt.to_period("M").astype(str)
        monthly = date_df.groupby("Period")["Revenue"].sum().reset_index()

        if len(monthly) < 2:
            return json.dumps({
                "available": False,
                "message": "At least 2 distinct periods are required to detect revenue drops."
            })

        monthly["pct_change"] = monthly["Revenue"].pct_change() * 100
        drops = monthly[monthly["pct_change"] < 0].copy()

        severe_drops = drops[drops["pct_change"] < -15.0]

        return json.dumps({
            "available": True,
            "total_periods": len(monthly),
            "drop_periods_count": len(drops),
            "severe_drops_count": len(severe_drops),
            "steepest_drop_pct": round(float(drops["pct_change"].min()), 2) if not drops.empty else 0.0,
            "drops": [
                {
                    "period": str(row["Period"]),
                    "revenue": round(float(row["Revenue"]), 2),
                    "drop_pct": round(float(row["pct_change"]), 2),
                }
                for _, row in drops.iterrows()
            ],
        })
    except DatasetAccessError as e:
        return json.dumps({"error": e.message})
    except Exception as e:
        return json.dumps({"error": f"Failed to analyze revenue drops: {str(e)}"})


@tool
def analyze_expense_growth(dataset_id: str, user_id: str) -> str:
    """
    Identifies cost inflation patterns, expense spikes, and periods where
    expense growth exceeded revenue growth.
    """
    try:
        df, _ = load_user_dataset(dataset_id, user_id)

        total_rev = float(df["Revenue"].sum())
        total_exp = float(df["Expense"].sum())
        overall_expense_ratio = (total_exp / total_rev * 100) if total_rev > 0 else 100.0

        # Individual high-expense transactions (Expense > Revenue)
        loss_transactions = df[df["Expense"] > df["Revenue"]]
        unprofitable_tx_count = len(loss_transactions)
        unprofitable_tx_pct = (unprofitable_tx_count / len(df) * 100) if len(df) > 0 else 0.0

        high_expense_records = df[df["Expense"] > (df["Revenue"] * 0.9)]

        return json.dumps({
            "overall_expense_ratio_pct": round(overall_expense_ratio, 2),
            "unprofitable_transaction_count": unprofitable_tx_count,
            "unprofitable_transaction_pct": round(unprofitable_tx_pct, 2),
            "high_cost_records_count": len(high_expense_records),
            "cost_control_risk": "critical" if overall_expense_ratio > 100 else (
                "high" if overall_expense_ratio > 85 else (
                    "medium" if overall_expense_ratio > 70 else "low"
                )
            ),
        })
    except DatasetAccessError as e:
        return json.dumps({"error": e.message})
    except Exception as e:
        return json.dumps({"error": f"Failed to analyze expense growth: {str(e)}"})


@tool
def identify_loss_patterns(dataset_id: str, user_id: str) -> str:
    """
    Identifies systemic loss patterns, including products, categories, or regions
    that consistently generate negative net profit.
    """
    try:
        df, _ = load_user_dataset(dataset_id, user_id)

        loss_df = df[df["Profit"] < 0].copy()
        total_losses = float(loss_df["Profit"].sum())

        loss_by_product: List[Dict[str, Any]] = []
        if "Product" in df.columns:
            prod_summary = df.groupby("Product").agg(
                total_profit=("Profit", "sum"),
                total_revenue=("Revenue", "sum"),
                total_expense=("Expense", "sum"),
                loss_count=("Profit", lambda p: int((p < 0).sum())),
            ).reset_index()

            losing_prods = prod_summary[prod_summary["total_profit"] < 0]
            for _, r in losing_prods.iterrows():
                loss_by_product.append({
                    "product": str(r["Product"]),
                    "net_loss": round(float(r["total_profit"]), 2),
                    "loss_transactions": int(r["loss_count"]),
                })

        return json.dumps({
            "loss_generating_records_count": len(loss_df),
            "total_negative_profit": round(total_losses, 2),
            "unprofitable_products": loss_by_product[:5],
            "unprofitable_product_count": len(loss_by_product),
        })
    except DatasetAccessError as e:
        return json.dumps({"error": e.message})
    except Exception as e:
        return json.dumps({"error": f"Failed to identify loss patterns: {str(e)}"})


@tool
def calculate_risk_score(dataset_id: str, user_id: str) -> str:
    """
    Synthesizes a standardized financial risk score between 0 and 100,
    along with severity level, key findings, and action triggers.
    """
    try:
        df, _ = load_user_dataset(dataset_id, user_id)
        from backend.features import prepare_features

        features_df = prepare_features(df[["Quantity", "Revenue", "Expense"]].copy())

        # 1. Base Score
        score = 5.0
        findings: List[Dict[str, Any]] = []

        total_rev = float(df["Revenue"].sum())
        total_exp = float(df["Expense"].sum())
        total_prof = float(df["Profit"].sum())
        margin = (total_prof / total_rev * 100) if total_rev > 0 else 0.0

        # 2. Profit Margin Risk Factor
        if total_prof < 0 or margin < 0:
            score += 35
            findings.append({
                "risk_type": "Operating Loss",
                "severity": "critical",
                "description": f"The business operates at a net loss of ₹{abs(total_prof):,.2f} ({margin:.2f}% margin).",
            })
        elif margin < 10:
            score += 20
            findings.append({
                "risk_type": "Compressed Margin",
                "severity": "high",
                "description": f"Low operating margin of {margin:.2f}%, leaving thin cushion for volatility.",
            })
        elif margin < 20:
            score += 10
            findings.append({
                "risk_type": "Moderate Margin",
                "severity": "medium",
                "description": f"Operating margin is {margin:.2f}%.",
            })

        # 3. Anomaly Risk Factor
        anomaly_indices, _ = compute_dataset_anomalies(df)
        anom_count = len(anomaly_indices)
        anomaly_pct = (anom_count / len(df) * 100) if len(df) > 0 else 0.0
        anomaly_detected = anom_count > 0

        if anomaly_pct > 8.0:
            score += 25
            findings.append({
                "risk_type": "Elevated Operational Anomalies",
                "severity": "high",
                "description": f"{anomaly_pct:.1f}% of transactions deviate significantly from regular patterns ({anom_count} outlier records).",
            })
        elif anomaly_pct > 2.0:
            score += 15
            findings.append({
                "risk_type": "Moderate Operational Anomalies",
                "severity": "medium",
                "description": f"{anomaly_pct:.1f}% of transactions flagged as pattern anomalies ({anom_count} outlier records).",
            })
        elif anomaly_detected:
            score += 5

        # 4. Expense Ratio Risk Factor
        expense_ratio = (total_exp / total_rev * 100) if total_rev > 0 else 100.0
        if expense_ratio > 90 and total_prof >= 0:
            score += 15
            findings.append({
                "risk_type": "High Cost Structure",
                "severity": "high",
                "description": f"Expenses absorb {expense_ratio:.1f}% of gross revenue.",
            })

        # 5. ML Predicted Profit Factor
        global _profit_model
        if _profit_model is None:
            _profit_model = _load_ml_model("profit_model.pkl")

        predicted_profit: Optional[float] = None
        if _profit_model is not None and all(f in features_df.columns for f in MODEL_FEATURES):
            predicted_profit = float(_profit_model.predict(features_df[MODEL_FEATURES]).mean())
            if predicted_profit < 0:
                score += 20
                findings.append({
                    "risk_type": "Negative Forecast",
                    "severity": "high",
                    "description": f"RandomForest ML model projects negative expected profit of ₹{predicted_profit:,.2f}.",
                })

        final_score = float(max(0.0, min(100.0, score)))
        if final_score > 75:
            level = "critical"
        elif final_score > 55:
            level = "high"
        elif final_score > 30:
            level = "medium"
        else:
            level = "low"

        return json.dumps({
            "risk_score": round(final_score, 1),
            "risk_level": level,
            "anomaly_detected": anomaly_detected,
            "anomaly_percentage": round(anomaly_pct, 2),
            "predicted_profit": round(predicted_profit, 2) if predicted_profit is not None else None,
            "findings": findings,
        })
    except DatasetAccessError as e:
        return json.dumps({"error": e.message})
    except Exception as e:
        return json.dumps({"error": f"Failed to compute risk score: {str(e)}"})


@tool
def forecast_business_risks(dataset_id: str, user_id: str) -> str:
    """
    Evaluates forward-looking business risks using the DailyProfitForecaster
    or trained RandomForest model to estimate expected profitability under baseline conditions.
    """
    try:
        df, _ = load_user_dataset(dataset_id, user_id)
        from backend.features import prepare_features

        features_df = prepare_features(df[["Quantity", "Revenue", "Expense"]].copy())

        global _profit_model
        if _profit_model is None:
            _profit_model = _load_ml_model("profit_model.pkl")

        predicted_profit: Optional[float] = None
        if _profit_model is not None and all(f in features_df.columns for f in MODEL_FEATURES):
            predicted_profit = float(_profit_model.predict(features_df[MODEL_FEATURES]).mean())

        from ml.forecast import DailyProfitForecaster
        forecaster = DailyProfitForecaster()
        forecast_result = None
        if forecaster.is_loaded and forecaster.model is not None:
            try:
                forecast_result = forecaster.forecast_next_day(DATA_PATH=None)
            except Exception:
                pass

        risk_assessment = "stable"
        if predicted_profit is not None and predicted_profit < 0:
            risk_assessment = "negative_profit_warning"

        return json.dumps({
            "predicted_mean_profit": round(predicted_profit, 2) if predicted_profit is not None else None,
            "risk_assessment": risk_assessment,
            "daily_forecast": forecast_result,
            "model_used": "RandomForestRegressor / ExtraTrees Daily Profit Forecaster",
        })
    except DatasetAccessError as e:
        return json.dumps({"error": e.message})
    except Exception as e:
        return json.dumps({"error": f"Failed to forecast business risks: {str(e)}"})


@tool
def explain_risk_records(dataset_id: str, user_id: str, top_n: int = 5) -> str:
    """
    Identifies and explains the specific transaction records contributing most
    heavily to business risk (e.g. largest losses, abnormal cost ratios).
    """
    try:
        df, _ = load_user_dataset(dataset_id, user_id)

        # Rank records by negative profit and high expense ratio
        df_copy = df.copy()
        df_copy["loss_amount"] = np.where(df_copy["Profit"] < 0, -df_copy["Profit"], 0.0)
        df_copy["expense_ratio"] = np.where(df_copy["Revenue"] > 0, df_copy["Expense"] / df_copy["Revenue"], 999.0)

        high_risk_rows = df_copy.sort_values(by=["loss_amount", "expense_ratio"], ascending=[False, False]).head(top_n)

        records = []
        for idx, row in high_risk_rows.iterrows():
            reason = "Operating at a direct loss" if row["Profit"] < 0 else "Disproportionately high expense ratio"
            records.append({
                "record_index": int(idx),
                "revenue": round(float(row["Revenue"]), 2),
                "expense": round(float(row["Expense"]), 2),
                "profit": round(float(row["Profit"]), 2),
                "product": str(row.get("Product", "N/A")),
                "date": str(row.get("Date", "N/A")) if pd.notna(row.get("Date")) else "N/A",
                "risk_reason": reason,
            })

        return json.dumps({
            "high_risk_records": records,
            "total_analyzed": len(df),
        })
    except DatasetAccessError as e:
        return json.dumps({"error": e.message})
    except Exception as e:
        return json.dumps({"error": f"Failed to explain risk records: {str(e)}"})


RISK_TOOLS = [
    detect_anomalies,
    analyze_revenue_drops,
    analyze_expense_growth,
    identify_loss_patterns,
    calculate_risk_score,
    forecast_business_risks,
    explain_risk_records,
]
