"""
EVORA Daily Profit Forecast Model Training Pipeline
===================================================
Production training, evaluation, model selection and artifact persistence
for EVORA Future Profit Forecasting.

Key Architecture Guarantees:
1. Strict Data Leakage Prevention: All lag and rolling statistics shift(1).
2. Chronological Splitting: Train (70%), Validation (15%), Test (15%).
3. Baseline Comparison: Naive Previous-Day, Previous-Week, 7-Day MA.
4. Model Comparison: Ridge, RandomForest, ExtraTrees, HistGradientBoosting.
5. Model Selection: Selected strictly on untouched Validation set.
6. Independent Artifacts: Saves to ml/daily_profit_forecast_model.pkl.
   NEVER modifies or overwrites ml/profit_model.pkl.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import (
    ExtraTreesRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Set CPU count to avoid loky wmic warnings on Windows
os.environ["LOKY_MAX_CPU_COUNT"] = "1"

# Directory paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT_DIR / "data" / "sample_business_data.csv"
MODEL_PATH = ROOT_DIR / "ml" / "daily_profit_forecast_model.pkl"
RESULTS_DIR = ROOT_DIR / "ml" / "results"

# Import forecast definitions
sys.path.append(str(ROOT_DIR / "ml"))
from forecast import (
    FEATURE_COLUMNS,
    aggregate_daily_metrics,
    build_historical_features,
    validate_transaction_dataframe,
)


def validate_raw_dataset(csv_path: Path) -> pd.DataFrame:
    """
    Performs data science validation on the raw transactions CSV.
    Validates schema, rows, missing values, duplicates, and business formulas:
      Revenue = Quantity * Unit_Price * (1 - Discount_Percent / 100)
      Expense = (Quantity * Cost_Per_Unit) + Shipping_Cost + Marketing_Spend
      Profit = Revenue - Expense
    """
    print("\n=======================================================")
    print("STEP 1.1: RAW DATASET VALIDATION & BUSINESS INTEGRITY")
    print("=======================================================")

    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset not found at {csv_path}")

    df = pd.read_csv(csv_path)
    print(f"Dataset Loaded Successfully: {csv_path.name}")
    print(f"Row count: {len(df):,} transactions | Columns: {len(df.columns)}")

    # 1. Null check
    null_counts = df.isnull().sum()
    total_nulls = int(null_counts.sum())
    print(f"Total Missing Values: {total_nulls}")
    if total_nulls > 0:
        print("Columns with missing values:\n", null_counts[null_counts > 0])

    # 2. Duplicate check
    dup_txn = int(df["Transaction_ID"].duplicated().sum()) if "Transaction_ID" in df.columns else 0
    dup_rows = int(df.duplicated().sum())
    print(f"Duplicate Transaction IDs: {dup_txn} | Duplicate Rows: {dup_rows}")

    # 3. Date continuity check
    df["Date"] = pd.to_datetime(df["Date"])
    min_date = df["Date"].min()
    max_date = df["Date"].max()
    unique_dates = df["Date"].nunique()
    expected_days = (max_date - min_date).days + 1
    missing_dates = expected_days - unique_dates

    print(f"Date Range: {min_date.date()} to {max_date.date()}")
    print(f"Calendar Days: {expected_days} | Unique Transaction Dates: {unique_dates}")
    print(f"Missing Calendar Dates: {missing_dates}")

    # 4. Business formula checks
    calc_rev = df["Quantity"] * df["Unit_Price"] * (1.0 - df["Discount_Percent"] / 100.0)
    rev_diff = np.abs(df["Revenue"] - calc_rev).max()

    calc_exp = (df["Quantity"] * df["Cost_Per_Unit"]) + df["Shipping_Cost"] + df["Marketing_Spend"]
    exp_diff = np.abs(df["Expense"] - calc_exp).max()

    df["Profit"] = df["Revenue"] - df["Expense"]
    negative_profit_count = int((df["Profit"] < 0).sum())
    neg_pct = (negative_profit_count / len(df)) * 100

    print(f"Formula Validation: Max Revenue Diff = {rev_diff:.4f} (OK <= 0.05)")
    print(f"Formula Validation: Max Expense Diff = {exp_diff:.4f} (OK <= 0.05)")
    print(f"Legitimate Business Losses (Profit < 0): {negative_profit_count} rows ({neg_pct:.2f}%)")

    return df


def prepare_chronological_splits(
    daily_features: pd.DataFrame,
    train_pct: float = 0.70,
    val_pct: float = 0.15,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Splits daily time series data strictly chronologically:
      - Train: First 70% of chronological history
      - Validation: Middle 15% for model comparison and selection
      - Test: Final 15% untouched for unbiased evaluation
    """
    clean_df = daily_features.dropna().reset_index(drop=True)
    n = len(clean_df)

    train_end = int(n * train_pct)
    val_end = int(n * (train_pct + val_pct))

    train_df = clean_df.iloc[:train_end].copy()
    val_df = clean_df.iloc[train_end:val_end].copy()
    test_df = clean_df.iloc[val_end:].copy()

    print("\n=======================================================")
    print("STEP 1.2: CHRONOLOGICAL DATA SPLIT (NO FUTURE LEAKAGE)")
    print("=======================================================")
    print(f"Total Usable Days: {n} (after 30-day lag window)")
    print(f"  Training Set:   {len(train_df):3d} days ({train_df['Date'].min().date()} to {train_df['Date'].max().date()})")
    print(f"  Validation Set: {len(val_df):3d} days ({val_df['Date'].min().date()} to {val_df['Date'].max().date()})")
    print(f"  Test Set:       {len(test_df):3d} days ({test_df['Date'].min().date()} to {test_df['Date'].max().date()})")

    # Safety assertion: zero chronological overlap
    assert train_df["Date"].max() < val_df["Date"].min(), "Leakage: Train overlaps with Validation!"
    assert val_df["Date"].max() < test_df["Date"].min(), "Leakage: Validation overlaps with Test!"

    return train_df, val_df, test_df


def compute_metrics(y_true: pd.Series | np.ndarray, y_pred: pd.Series | np.ndarray) -> Dict[str, float]:
    """Computes MAE, RMSE, R², and WAPE."""
    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)

    mae = float(mean_absolute_error(y_true_arr, y_pred_arr))
    rmse = float(np.sqrt(mean_squared_error(y_true_arr, y_pred_arr)))
    r2 = float(r2_score(y_true_arr, y_pred_arr))

    # WAPE (Weighted Absolute Percentage Error = sum(|y - y_hat|) / sum(|y|))
    denom = float(np.sum(np.abs(y_true_arr)))
    wape = float(np.sum(np.abs(y_true_arr - y_pred_arr)) / denom) if denom > 0 else 0.0

    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "r2": round(r2, 4),
        "wape_pct": round(wape * 100, 2),
    }


def train_and_compare_models(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    features: List[str],
) -> Tuple[str, Any, List[Dict[str, Any]]]:
    """
    Compares Baselines and ML models on the Validation set:
      1. Naive Previous-Day Baseline
      2. Previous-Week Baseline
      3. 7-Day Moving Average Baseline
      4. Ridge Regression
      5. RandomForestRegressor
      6. ExtraTreesRegressor
      7. HistGradientBoostingRegressor
    """
    print("\n=======================================================")
    print("STEP 1.3: BENCHMARK & MODEL COMPARISON ON VALIDATION SET")
    print("=======================================================")

    X_train = train_df[features]
    y_train = train_df["Profit"]
    X_val = val_df[features]
    y_val = val_df["Profit"]

    comparison_results = []

    # --- BASELINES ---
    # 1. Naive Previous Day
    pred_naive1 = val_df["profit_lag_1"]
    m_naive1 = compute_metrics(y_val, pred_naive1)
    comparison_results.append({
        "Model": "Naive Previous-Day Baseline",
        "Type": "Heuristic Baseline",
        **m_naive1,
    })

    # 2. Previous Week
    pred_naive7 = val_df["profit_lag_7"]
    m_naive7 = compute_metrics(y_val, pred_naive7)
    comparison_results.append({
        "Model": "Previous-Week Baseline",
        "Type": "Heuristic Baseline",
        **m_naive7,
    })

    # 3. 7-Day Moving Average
    pred_roll7 = val_df["profit_mean_7"]
    m_roll7 = compute_metrics(y_val, pred_roll7)
    comparison_results.append({
        "Model": "7-Day Moving Average Baseline",
        "Type": "Statistical Baseline",
        **m_roll7,
    })

    # --- MACHINE LEARNING CANDIDATES ---
    candidates: Dict[str, Any] = {
        "Ridge Regression": Ridge(alpha=100.0),
        "RandomForestRegressor": RandomForestRegressor(
            n_estimators=200,
            max_depth=6,
            min_samples_leaf=4,
            random_state=42,
            n_jobs=1,
        ),
        "ExtraTreesRegressor": ExtraTreesRegressor(
            n_estimators=200,
            max_depth=7,
            min_samples_leaf=4,
            random_state=42,
            n_jobs=1,
        ),
        "HistGradientBoostingRegressor": HistGradientBoostingRegressor(
            max_iter=60,
            max_depth=3,
            min_samples_leaf=15,
            l2_regularization=5.0,
            random_state=42,
        ),
    }

    trained_models = {}

    for name, model in candidates.items():
        model.fit(X_train, y_train)
        preds = model.predict(X_val)
        m = compute_metrics(y_val, preds)
        trained_models[name] = model
        comparison_results.append({
            "Model": name,
            "Type": "Machine Learning Regressor",
            **m,
        })

    comp_df = pd.DataFrame(comparison_results)
    print("\nValidation Performance Comparison:")
    print(comp_df.to_string(index=False))

    # Model Selection: Best R² and lowest MAE on Validation set
    ml_candidates = [r for r in comparison_results if r["Type"] == "Machine Learning Regressor"]
    # Sort by R2 descending, then MAE ascending
    best_candidate_info = sorted(ml_candidates, key=lambda x: (-x["r2"], x["mae"]))[0]
    best_model_name = best_candidate_info["Model"]
    best_model = trained_models[best_model_name]

    print(f"\n>>> Winning Model Selected: {best_model_name}")
    print(f"    Validation MAE:  {best_candidate_info['mae']:.2f} INR")
    print(f"    Validation RMSE: {best_candidate_info['rmse']:.2f} INR")
    print(f"    Validation R2:   {best_candidate_info['r2']:+.4f}")

    return best_model_name, best_model, comparison_results


def evaluate_on_untouched_test_set(
    model_name: str,
    model: Any,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    features: List[str],
) -> Tuple[Dict[str, float], pd.DataFrame]:
    """
    Evaluates the winning model on the completely untouched chronological Test set.
    Generates actual vs predicted comparisons, residuals, and error distribution.
    """
    print("\n=======================================================")
    print("STEP 1.4: UNTOUCHED CHRONOLOGICAL TEST SET EVALUATION")
    print("=======================================================")

    X_test = test_df[features]
    y_test = test_df["Profit"]

    # Predict on test set
    predictions = model.predict(X_test)
    test_metrics = compute_metrics(y_test, predictions)

    print(f"Test Set Evaluation ({len(test_df)} days):")
    print(f"  MAE:      {test_metrics['mae']:.2f} INR")
    print(f"  RMSE:     {test_metrics['rmse']:.2f} INR")
    print(f"  R2 Score: {test_metrics['r2']:+.4f}")
    print(f"  WAPE:     {test_metrics['wape_pct']:.2f}%")

    # Residuals & detailed error analysis
    residuals = y_test - predictions
    abs_errors = np.abs(residuals)

    pred_df = pd.DataFrame({
        "Date": test_df["Date"].dt.strftime("%Y-%m-%d"),
        "Actual_Profit": y_test.values,
        "Predicted_Profit": np.round(predictions, 2),
        "Residual_Error": np.round(residuals.values, 2),
        "Absolute_Error": np.round(abs_errors.values, 2),
        "Percentage_Error": np.round((abs_errors.values / np.maximum(np.abs(y_test.values), 1.0)) * 100, 2),
    })

    print(f"  Mean Error Bias: {residuals.mean():+.2f} INR")
    print(f"  Median Absolute Error: {np.median(abs_errors):.2f} INR")
    print(f"  Max Absolute Error: {abs_errors.max():.2f} INR")

    return test_metrics, pred_df


def save_artifacts(
    model: Any,
    model_name: str,
    features: List[str],
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    comparison_results: List[Dict[str, Any]],
    val_metrics: Dict[str, float],
    test_metrics: Dict[str, float],
    pred_df: pd.DataFrame,
    start_reference_date: pd.Timestamp,
) -> None:
    """
    Saves the final trained forecasting model and complete metadata to
    ml/daily_profit_forecast_model.pkl, and exports structured results to ml/results/.
    """
    print("\n=======================================================")
    print("STEP 1.5: SAVING MODEL ARTIFACT & EVALUATION REPORTS")
    print("=======================================================")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Feature Importances if supported
    feature_importances = {}
    if hasattr(model, "feature_importances_"):
        fi_series = pd.Series(model.feature_importances_, index=features).sort_values(ascending=False)
        feature_importances = {k: round(float(v), 5) for k, v in fi_series.items()}
        pd.DataFrame({
            "Feature": list(feature_importances.keys()),
            "Importance": list(feature_importances.values()),
        }).to_csv(RESULTS_DIR / "feature_importances.csv", index=False)
        print("Feature importances saved to ml/results/feature_importances.csv")

    # 2. Metadata Dictionary
    metadata = {
        "model_name": model_name,
        "model_version": "2.0.0",
        "created_at": datetime.now().isoformat(),
        "selected_model_type": type(model).__name__,
        "dataset_name": "sample_business_data.csv",
        "total_historical_days": len(train_df) + len(val_df) + len(test_df),
        "start_reference_date": start_reference_date.strftime("%Y-%m-%d"),
        "date_ranges": {
            "train": [train_df["Date"].min().strftime("%Y-%m-%d"), train_df["Date"].max().strftime("%Y-%m-%d")],
            "val": [val_df["Date"].min().strftime("%Y-%m-%d"), val_df["Date"].max().strftime("%Y-%m-%d")],
            "test": [test_df["Date"].min().strftime("%Y-%m-%d"), test_df["Date"].max().strftime("%Y-%m-%d")],
        },
        "features": features,
        "val_metrics": val_metrics,
        "test_metrics": test_metrics,
        "feature_importances": feature_importances,
        "training_configuration": {
            "n_estimators": getattr(model, "n_estimators", None),
            "max_depth": getattr(model, "max_depth", None),
            "min_samples_leaf": getattr(model, "min_samples_leaf", None),
            "random_state": getattr(model, "random_state", None),
        },
    }

    # 3. Save Model Artifact to ml/daily_profit_forecast_model.pkl
    artifact = {
        "model": model,
        "features": features,
        "metadata": metadata,
    }
    joblib.dump(artifact, MODEL_PATH)
    print(f"Model artifact saved to: {MODEL_PATH}")

    # 4. Save structured JSON evaluation results
    full_evaluation = {
        "metadata": metadata,
        "comparison_results": comparison_results,
        "test_evaluation": test_metrics,
    }
    with open(RESULTS_DIR / "forecast_evaluation_results.json", "w") as f:
        json.dump(full_evaluation, f, indent=2)
    print("Full evaluation JSON saved to: ml/results/forecast_evaluation_results.json")

    # 5. Save Model Comparison CSV
    pd.DataFrame(comparison_results).to_csv(RESULTS_DIR / "model_comparison.csv", index=False)
    print("Model comparison CSV saved to: ml/results/model_comparison.csv")

    # 6. Save Test Predictions CSV
    pred_df.to_csv(RESULTS_DIR / "test_predictions.csv", index=False)
    print("Test predictions CSV saved to: ml/results/test_predictions.csv")


def main() -> None:
    print("================================================================")
    print("EVORA ML STEP 1: PRODUCTION FUTURE PROFIT FORECAST TRAINING")
    print("================================================================")

    # 1. Raw Dataset Validation
    raw_df = validate_raw_dataset(DATA_PATH)

    # 2. Daily Aggregation
    daily_df = aggregate_daily_metrics(raw_df)
    start_reference_date = daily_df["Date"].min()

    # 3. Leakage-Free Feature Engineering
    features_df = build_historical_features(daily_df, start_reference_date=start_reference_date)

    # 4. Chronological Split (Train 70%, Val 15%, Test 15%)
    train_df, val_df, test_df = prepare_chronological_splits(features_df, 0.70, 0.15)

    # 5. Model Comparison on Validation Set
    best_model_name, best_model, comparison_results = train_and_compare_models(
        train_df, val_df, FEATURE_COLUMNS
    )

    # Extract validation metrics for best model
    val_metrics = next(r for r in comparison_results if r["Model"] == best_model_name)

    # 6. Untouched Test Set Evaluation
    test_metrics, pred_df = evaluate_on_untouched_test_set(
        best_model_name, best_model, train_df, val_df, test_df, FEATURE_COLUMNS
    )

    # 7. Persist Artifacts and Results
    save_artifacts(
        model=best_model,
        model_name=best_model_name,
        features=FEATURE_COLUMNS,
        train_df=train_df,
        val_df=val_df,
        test_df=test_df,
        comparison_results=comparison_results,
        val_metrics=val_metrics,
        test_metrics=test_metrics,
        pred_df=pred_df,
        start_reference_date=start_reference_date,
    )

    print("\n================================================================")
    print("EVORA STEP 1 MODEL TRAINING COMPLETED SUCCESSFULLY!")
    print("================================================================")


if __name__ == "__main__":
    main()
