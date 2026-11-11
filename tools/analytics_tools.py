"""
EVORA Analytics Tools
=====================
Production LangChain tools for business analytics and financial reasoning.
Calculates deterministic ground-truth metrics, trends, segment comparisons,
and product performance from real user datasets.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from langchain_core.tools import tool

from tools.dataset_tools import DatasetAccessError, load_user_dataset


@tool
def get_dataset_profile(dataset_id: str, user_id: str) -> str:
    """
    Returns an overview profile of the dataset including row count, columns,
    identified semantic roles (revenue, expense, date, product, etc.), and date range.
    """
    try:
        df, meta = load_user_dataset(dataset_id, user_id)
        numeric_cols = [str(c) for c in df.select_dtypes(include=[np.number]).columns]
        categorical_cols = [str(c) for c in df.select_dtypes(include=["string", "object", "category"]).columns]

        profile = {
            "dataset_id": dataset_id,
            "filename": str(meta.get("filename", "unknown.csv")),
            "row_count": int(len(df)),
            "column_count": int(len(df.columns)),
            "columns": [str(c) for c in df.columns],
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "semantic_mapping": meta.get("semantic_mapping", {}),
            "date_range": {
                "start": meta.get("date_start"),
                "end": meta.get("date_end"),
            },
            "has_date": bool(meta.get("has_date", False)),
            "has_product": bool(meta.get("has_product", False)),
            "has_category": bool(meta.get("has_category", False)),
        }
        return json.dumps(profile)

    except DatasetAccessError as e:
        return json.dumps({"error": e.message, "status_code": e.status_code})
    except Exception as e:
        return json.dumps({"error": f"Failed to profile dataset: {str(e)}"})


@tool
def calculate_business_metrics(dataset_id: str, user_id: str) -> str:
    """
    Calculates primary financial and business metrics from the dataset:
    Total Revenue, Total Expenses, Total Profit, Profit Margin (%), Average Order Value,
    Total Orders/Units, and basic growth indicators.
    """
    try:
        df, _ = load_user_dataset(dataset_id, user_id)

        revenue_series = pd.to_numeric(df["Revenue"], errors="coerce").fillna(0.0)
        expense_series = pd.to_numeric(df["Expense"], errors="coerce").fillna(0.0)
        profit_series = pd.to_numeric(df["Profit"], errors="coerce").fillna(revenue_series - expense_series)

        total_revenue = float(revenue_series.sum())
        total_expense = float(expense_series.sum())
        total_profit = float(profit_series.sum())
        profit_margin = (total_profit / total_revenue * 100) if total_revenue != 0 else 0.0

        quantity_series = pd.to_numeric(df.get("Quantity", pd.Series(1.0, index=df.index)), errors="coerce").fillna(1.0)
        total_quantity = float(quantity_series.sum())
        avg_order_value = (total_revenue / len(df)) if len(df) > 0 else 0.0
        avg_unit_revenue = (total_revenue / total_quantity) if total_quantity > 0 else 0.0
        avg_unit_cost = (total_expense / total_quantity) if total_quantity > 0 else 0.0

        metrics = {
            "total_revenue": round(total_revenue, 2),
            "total_expenses": round(total_expense, 2),
            "total_profit": round(total_profit, 2),
            "profit_margin_pct": round(profit_margin, 2),
            "total_orders": len(df),
            "total_quantity": round(total_quantity, 2),
            "average_order_value": round(avg_order_value, 2),
            "average_unit_revenue": round(avg_unit_revenue, 2),
            "average_unit_cost": round(avg_unit_cost, 2),
            "is_profitable": total_profit > 0,
        }
        return json.dumps(metrics)
    except DatasetAccessError as e:
        return json.dumps({"error": e.message})
    except Exception as e:
        return json.dumps({"error": f"Failed to compute business metrics: {str(e)}"})


@tool
def analyze_time_trends(dataset_id: str, user_id: str, period: str = "monthly") -> str:
    """
    Analyzes periodic financial trends over time (e.g. monthly revenue, expense, profit trends,
    growth rates, and consecutive decline patterns).
    """
    try:
        df, meta = load_user_dataset(dataset_id, user_id)
        if "Date" not in df.columns or df["Date"].isna().all():
            return json.dumps({
                "available": False,
                "message": "Dataset does not contain a recognizable Date column for trend analysis."
            })

        date_df = df.copy()
        date_df["Date"] = pd.to_datetime(date_df["Date"], errors="coerce")
        date_df = date_df.dropna(subset=["Date"]).sort_values("Date")

        if date_df.empty:
            return json.dumps({"available": False, "message": "No valid timestamped rows found."})

        # Group by Year-Month
        date_df["Period"] = date_df["Date"].dt.to_period("M").astype(str)
        grouped = date_df.groupby("Period").agg(
            revenue=("Revenue", "sum"),
            expense=("Expense", "sum"),
            profit=("Profit", "sum"),
            orders=("Revenue", "count"),
        ).reset_index()

        grouped["profit_margin"] = np.where(
            grouped["revenue"] > 0,
            (grouped["profit"] / grouped["revenue"]) * 100,
            0.0
        )

        # Calculate period-over-period growth
        grouped["revenue_growth_pct"] = grouped["revenue"].pct_change().fillna(0.0) * 100
        grouped["profit_growth_pct"] = grouped["profit"].pct_change().fillna(0.0) * 100

        trends_list = [
            {
                "period": str(row["Period"]),
                "month": str(row["Period"]),
                "revenue": round(float(row["revenue"]), 2),
                "expense": round(float(row["expense"]), 2),
                "profit": round(float(row["profit"]), 2),
                "profit_margin_pct": round(float(row["profit_margin"]), 2),
                "orders": int(row["orders"]),
                "revenue_growth_pct": round(float(row["revenue_growth_pct"]), 2),
                "profit_growth_pct": round(float(row["profit_growth_pct"]), 2),
            }
            for _, row in grouped.iterrows()
        ]


        # Key trend signals
        best_month = max(trends_list, key=lambda x: x["profit"]) if trends_list else None
        worst_month = min(trends_list, key=lambda x: x["profit"]) if trends_list else None

        result = {
            "available": True,
            "period_count": len(trends_list),
            "trends": trends_list,
            "best_period": best_month,
            "worst_period": worst_month,
        }
        return json.dumps(result)
    except DatasetAccessError as e:
        return json.dumps({"error": e.message})
    except Exception as e:
        return json.dumps({"error": f"Failed to analyze time trends: {str(e)}"})


@tool
def compare_business_segments(dataset_id: str, user_id: str, segment_column: str = "auto") -> str:
    """
    Compares financial performance across segments such as Category, Region, or Product.
    Identifies top performing and underperforming business units.
    """
    try:
        df, _ = load_user_dataset(dataset_id, user_id)

        target_col: Optional[str] = None
        if segment_column != "auto" and segment_column in df.columns:
            target_col = segment_column
        elif "Category" in df.columns and df["Category"].nunique() > 1:
            target_col = "Category"
        elif "Region" in df.columns and df["Region"].nunique() > 1:
            target_col = "Region"
        elif "Product" in df.columns and df["Product"].nunique() > 1:
            target_col = "Product"

        if target_col is None:
            return json.dumps({
                "available": False,
                "message": "No multi-category segmentation column (Category/Region/Product) detected."
            })

        grouped = df.groupby(target_col).agg(
            revenue=("Revenue", "sum"),
            expense=("Expense", "sum"),
            profit=("Profit", "sum"),
            transactions=("Revenue", "count"),
        ).reset_index()

        grouped["profit_margin_pct"] = np.where(
            grouped["revenue"] > 0,
            (grouped["profit"] / grouped["revenue"]) * 100,
            0.0
        )

        segments = [
            {
                "segment": str(row[target_col]),
                "revenue": round(float(row["revenue"]), 2),
                "expense": round(float(row["expense"]), 2),
                "profit": round(float(row["profit"]), 2),
                "profit_margin_pct": round(float(row["profit_margin_pct"]), 2),
                "transactions": int(row["transactions"]),
            }
            for _, row in grouped.iterrows()
        ]

        segments.sort(key=lambda s: s["profit"], reverse=True)

        return json.dumps({
            "available": True,
            "segment_dimension": target_col,
            "segment_count": len(segments),
            "top_segment": segments[0] if segments else None,
            "lowest_segment": segments[-1] if segments else None,
            "segments": segments[:10],
        })
    except DatasetAccessError as e:
        return json.dumps({"error": e.message})
    except Exception as e:
        return json.dumps({"error": f"Failed to compare business segments: {str(e)}"})


@tool
def analyze_product_performance(dataset_id: str, user_id: str, top_n: int = 5) -> str:
    """
    Analyzes product-level profitability, unit revenue, unit cost, and margin distribution.
    Identifies top profit drivers and loss-making products.
    """
    try:
        df, _ = load_user_dataset(dataset_id, user_id)
        if "Product" not in df.columns or df["Product"].nunique() <= 1 and df["Product"].iloc[0] == "All Products":
            return json.dumps({
                "available": False,
                "message": "Product breakdown is not available in this dataset."
            })

        grouped = df.groupby("Product").agg(
            revenue=("Revenue", "sum"),
            expense=("Expense", "sum"),
            profit=("Profit", "sum"),
            quantity=("Quantity", "sum"),
            orders=("Revenue", "count"),
        ).reset_index()

        grouped["profit_margin_pct"] = np.where(
            grouped["revenue"] > 0,
            (grouped["profit"] / grouped["revenue"]) * 100,
            0.0
        )

        products = [
            {
                "product": str(row["Product"]),
                "revenue": round(float(row["revenue"]), 2),
                "expense": round(float(row["expense"]), 2),
                "profit": round(float(row["profit"]), 2),
                "profit_margin_pct": round(float(row["profit_margin_pct"]), 2),
                "total_units": round(float(row["quantity"]), 1),
                "orders": int(row["orders"]),
            }
            for _, row in grouped.iterrows()
        ]

        sorted_by_profit = sorted(products, key=lambda p: p["profit"], reverse=True)
        loss_products = [p for p in sorted_by_profit if p["profit"] < 0]

        return json.dumps({
            "available": True,
            "total_unique_products": len(products),
            "top_profitable_products": sorted_by_profit[:top_n],
            "loss_making_products": loss_products[:top_n],
            "loss_product_count": len(loss_products),
        })
    except DatasetAccessError as e:
        return json.dumps({"error": e.message})
    except Exception as e:
        return json.dumps({"error": f"Failed to analyze product performance: {str(e)}"})


@tool
def query_business_data(
    dataset_id: str,
    user_id: str,
    query_type: str = "summary",
    product_filter: Optional[str] = None,
    min_profit: Optional[float] = None,
    max_margin: Optional[float] = None,
) -> str:
    """
    Queries business records with structured filters (e.g. loss records, high margin records,
    or specific product records) without exposing raw customer or transaction identifiers.
    """
    try:
        df, _ = load_user_dataset(dataset_id, user_id)
        filtered = df.copy()

        if product_filter and "Product" in filtered.columns:
            filtered = filtered[filtered["Product"].str.contains(product_filter, case=False, na=False)]

        if min_profit is not None:
            filtered = filtered[filtered["Profit"] >= min_profit]

        if max_margin is not None and "Revenue" in filtered.columns:
            margins = np.where(filtered["Revenue"] > 0, (filtered["Profit"] / filtered["Revenue"]) * 100, 0.0)
            filtered = filtered[margins <= max_margin]

        total_rev = float(filtered["Revenue"].sum())
        total_exp = float(filtered["Expense"].sum())
        total_prof = float(filtered["Profit"].sum())

        return json.dumps({
            "matched_records": len(filtered),
            "total_revenue": round(total_rev, 2),
            "total_expense": round(total_exp, 2),
            "total_profit": round(total_prof, 2),
            "profit_margin_pct": round((total_prof / total_rev * 100), 2) if total_rev > 0 else 0.0,
        })
    except DatasetAccessError as e:
        return json.dumps({"error": e.message})
    except Exception as e:
        return json.dumps({"error": f"Query failed: {str(e)}"})


@tool
def analyze_relationships(dataset_id: str, user_id: str) -> str:
    """
    Computes statistical relationships and correlations between revenue, expenses, profit,
    and quantity to evaluate cost structure linearity and pricing sensitivity.
    """
    try:
        df, _ = load_user_dataset(dataset_id, user_id)
        numeric_df = df[["Revenue", "Expense", "Profit", "Quantity"]].apply(pd.to_numeric, errors="coerce").fillna(0.0)

        corr_matrix = numeric_df.corr().round(2).to_dict()

        total_rev = float(numeric_df["Revenue"].sum())
        total_exp = float(numeric_df["Expense"].sum())
        expense_ratio = (total_exp / total_rev * 100) if total_rev > 0 else 0.0

        return json.dumps({
            "correlation_matrix": corr_matrix,
            "expense_to_revenue_ratio_pct": round(expense_ratio, 2),
            "profit_volatility_std": round(float(numeric_df["Profit"].std()), 2),
        })
    except DatasetAccessError as e:
        return json.dumps({"error": e.message})
    except Exception as e:
        return json.dumps({"error": f"Failed to compute relationships: {str(e)}"})


ANALYTICS_TOOLS = [
    get_dataset_profile,
    calculate_business_metrics,
    analyze_time_trends,
    compare_business_segments,
    analyze_product_performance,
    query_business_data,
    analyze_relationships,
]
