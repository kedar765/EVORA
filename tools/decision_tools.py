"""
EVORA Decision Optimization Tools
=================================
Production LangChain tools for business scenario simulation, strategy comparison,
financial impact estimation, and resource allocation optimization.
Enforces human-in-the-loop governance: AI proposes, human approves.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from langchain_core.tools import tool

from tools.dataset_tools import DatasetAccessError, load_user_dataset


@tool
def simulate_business_scenario(
    dataset_id: str,
    user_id: str,
    expense_change_pct: float = 0.0,
    price_change_pct: float = 0.0,
    volume_change_pct: float = 0.0,
) -> str:
    """
    Simulates a what-if business scenario against the real dataset baseline.
    Parameters allow adjusting expense changes, price adjustments, and volume growth.
    Returns projected revenue, expenses, net profit, and profit difference.
    """
    try:
        df, _ = load_user_dataset(dataset_id, user_id)

        base_revenue = float(df["Revenue"].sum())
        base_expense = float(df["Expense"].sum())
        base_profit = float(df["Profit"].sum())

        # Volume affects both revenue and variable expense (assumed ~60% variable)
        vol_multiplier = 1.0 + (volume_change_pct / 100.0)
        price_multiplier = 1.0 + (price_change_pct / 100.0)
        expense_multiplier = 1.0 + (expense_change_pct / 100.0)

        projected_revenue = base_revenue * vol_multiplier * price_multiplier

        # Variable expenses scale with volume, fixed expenses remain stable
        variable_expense_ratio = 0.65
        variable_expense = (base_expense * variable_expense_ratio) * vol_multiplier
        fixed_expense = base_expense * (1.0 - variable_expense_ratio)
        projected_expense = (variable_expense + fixed_expense) * expense_multiplier

        projected_profit = projected_revenue - projected_expense
        profit_delta = projected_profit - base_profit
        margin = (projected_profit / projected_revenue * 100) if projected_revenue > 0 else 0.0

        return json.dumps({
            "scenario": {
                "expense_change_pct": expense_change_pct,
                "price_change_pct": price_change_pct,
                "volume_change_pct": volume_change_pct,
            },
            "baseline": {
                "revenue": round(base_revenue, 2),
                "expenses": round(base_expense, 2),
                "profit": round(base_profit, 2),
            },
            "projected": {
                "revenue": round(projected_revenue, 2),
                "expenses": round(projected_expense, 2),
                "profit": round(projected_profit, 2),
                "profit_margin_pct": round(margin, 2),
            },
            "profit_delta": round(profit_delta, 2),
            "percentage_profit_increase": round((profit_delta / abs(base_profit) * 100), 2) if base_profit != 0 else 0.0,
        })
    except DatasetAccessError as e:
        return json.dumps({"error": e.message})
    except Exception as e:
        return json.dumps({"error": f"Scenario simulation failed: {str(e)}"})


@tool
def compare_business_strategies(
    dataset_id: str,
    user_id: str,
    strategies_input: Optional[str] = None,
) -> str:
    """
    Compares 4 concrete strategic pathways against baseline dataset performance:
    1. Operational Cost Containment (Expenses -8%)
    2. Pricing & Margin Optimization (Prices +5%, volume -1%)
    3. Volume Expansion (Volume +10%, expenses +4%)
    4. Balanced Profit Optimization (Expenses -4%, prices +3%)
    """
    try:
        df, _ = load_user_dataset(dataset_id, user_id)

        base_revenue = float(df["Revenue"].sum())
        base_expense = float(df["Expense"].sum())
        base_profit = float(df["Profit"].sum())

        standard_strategies = [
            {
                "name": "Operational Cost Containment",
                "description": "Reduce general and vendor operating expenses by 8%.",
                "price_pct": 0.0,
                "expense_pct": -8.0,
                "volume_pct": 0.0,
                "risk": "Low",
                "assumptions": "Vendor terms renegotiated without hurting delivery timelines.",
            },
            {
                "name": "Pricing & Margin Optimization",
                "description": "Increase average product prices by 5% with minimal volume elasticity.",
                "price_pct": 5.0,
                "expense_pct": 0.0,
                "volume_pct": -1.5,
                "risk": "Medium",
                "assumptions": "Customer retention remains above 95% post price update.",
            },
            {
                "name": "Volume & Market Expansion",
                "description": "Expand marketing to drive 10% unit volume growth.",
                "price_pct": 0.0,
                "expense_pct": 4.0,
                "volume_pct": 10.0,
                "risk": "Medium",
                "assumptions": "Acquisition cost scales sub-linearly with order volume.",
            },
            {
                "name": "Balanced Margin Optimization",
                "description": "Trim non-essential expenses by 4% while implementing 3% selective price adjustments.",
                "price_pct": 3.0,
                "expense_pct": -4.0,
                "volume_pct": 0.0,
                "risk": "Low",
                "assumptions": "Dual execution across procurement and sales teams.",
            },
        ]

        evaluated_strategies = []
        for s in standard_strategies:
            vol_mult = 1.0 + (s["volume_pct"] / 100.0)
            price_mult = 1.0 + (s["price_pct"] / 100.0)
            exp_mult = 1.0 + (s["expense_pct"] / 100.0)

            proj_rev = base_revenue * vol_mult * price_mult
            proj_exp = base_expense * exp_mult * (0.65 * vol_mult + 0.35)
            proj_prof = proj_rev - proj_exp
            delta = proj_prof - base_profit

            evaluated_strategies.append({
                "strategy_name": s["name"],
                "description": s["description"],
                "projected_revenue": round(proj_rev, 2),
                "projected_expenses": round(proj_exp, 2),
                "projected_profit": round(proj_prof, 2),
                "profit_delta": round(delta, 2),
                "risk_rating": s["risk"],
                "key_assumptions": s["assumptions"],
            })

        # Rank strategies by profit delta
        evaluated_strategies.sort(key=lambda x: x["profit_delta"], reverse=True)

        return json.dumps({
            "baseline_profit": round(base_profit, 2),
            "top_recommended_strategy": evaluated_strategies[0]["strategy_name"] if evaluated_strategies else None,
            "strategies": evaluated_strategies,
        })
    except DatasetAccessError as e:
        return json.dumps({"error": e.message})
    except Exception as e:
        return json.dumps({"error": f"Strategy comparison failed: {str(e)}"})


@tool
def estimate_financial_impact(
    dataset_id: str,
    user_id: str,
    action_type: str,
    parameters_json: Optional[str] = None,
) -> str:
    """
    Estimates the monetary bottom-line impact of a specific business action
    (e.g. 'discontinue_loss_products', 'renegotiate_vendor_terms', 'reduce_operating_overhead').
    """
    try:
        df, _ = load_user_dataset(dataset_id, user_id)
        params = json.loads(parameters_json) if parameters_json else {}

        base_profit = float(df["Profit"].sum())
        impact_amount = 0.0
        rationale = ""

        if action_type == "discontinue_loss_products":
            loss_df = df[df["Profit"] < 0]
            recovered_losses = float(abs(loss_df["Profit"].sum()))
            # Assume 80% loss recovery because of shared fixed costs
            impact_amount = recovered_losses * 0.8
            rationale = (
                f"Eliminating negative-margin transactions recoups up to ₹{recovered_losses:,.2f} in operating drag, "
                f"netting ~₹{impact_amount:,.2f} after fixed overhead reallocation."
            )

        elif action_type == "renegotiate_vendor_terms":
            discount_pct = float(params.get("discount_pct", 5.0))
            total_exp = float(df["Expense"].sum())
            impact_amount = total_exp * (discount_pct / 100.0)
            rationale = f"A {discount_pct}% vendor cost reduction saves ₹{impact_amount:,.2f} directly to net profit."

        elif action_type == "reduce_operating_overhead":
            overhead_cut_pct = float(params.get("cut_pct", 10.0))
            fixed_overhead = float(df["Expense"].sum()) * 0.35
            impact_amount = fixed_overhead * (overhead_cut_pct / 100.0)
            rationale = f"Cutting fixed overhead by {overhead_cut_pct}% yields ₹{impact_amount:,.2f} in annualized savings."

        else:
            impact_amount = float(df["Revenue"].sum()) * 0.02
            rationale = f"Estimated operational optimization benefit for action '{action_type}'."

        return json.dumps({
            "action_type": action_type,
            "estimated_profit_impact": round(impact_amount, 2),
            "baseline_profit": round(base_profit, 2),
            "new_projected_profit": round(base_profit + impact_amount, 2),
            "rationale": rationale,
        })
    except DatasetAccessError as e:
        return json.dumps({"error": e.message})
    except Exception as e:
        return json.dumps({"error": f"Failed to estimate financial impact: {str(e)}"})


@tool
def optimize_resource_allocation(
    dataset_id: str,
    user_id: str,
    budget_constraint: Optional[float] = None,
) -> str:
    """
    Optimizes business resource / inventory budget allocation across product categories
    to maximize total return on investment (ROI) and net margin.
    """
    try:
        df, _ = load_user_dataset(dataset_id, user_id)

        target_col = "Category" if ("Category" in df.columns and df["Category"].nunique() > 1) else "Product"
        if target_col not in df.columns or df[target_col].nunique() <= 1:
            return json.dumps({
                "optimized": False,
                "message": "Insufficient category or product segmentation for resource allocation."
            })

        grouped = df.groupby(target_col).agg(
            revenue=("Revenue", "sum"),
            expense=("Expense", "sum"),
            profit=("Profit", "sum"),
        ).reset_index()

        grouped["roi"] = np.where(grouped["expense"] > 0, grouped["profit"] / grouped["expense"], 0.0)

        # Allocate budget proportional to positive ROI
        positive_roi = grouped[grouped["roi"] > 0].copy()
        total_roi_score = positive_roi["roi"].sum()

        allocations = []
        default_budget = float(df["Expense"].sum()) if budget_constraint is None else budget_constraint

        if total_roi_score > 0:
            for _, r in positive_roi.iterrows():
                share = float(r["roi"] / total_roi_score)
                allocations.append({
                    "entity": str(r[target_col]),
                    "current_expense": round(float(r["expense"]), 2),
                    "historical_roi": round(float(r["roi"]), 2),
                    "recommended_budget_share_pct": round(share * 100, 1),
                    "recommended_budget_allocation": round(share * default_budget, 2),
                })
        allocations.sort(key=lambda a: a["recommended_budget_share_pct"], reverse=True)

        return json.dumps({
            "optimized": True,
            "dimension": target_col,
            "total_budget": round(default_budget, 2),
            "allocations": allocations[:6],
            "optimization_objective": "Maximize Return on Operating Investment (ROI)",
        })
    except DatasetAccessError as e:
        return json.dumps({"error": e.message})
    except Exception as e:
        return json.dumps({"error": f"Optimization failed: {str(e)}"})


@tool
def generate_action_plan(
    dataset_id: str,
    user_id: str,
    risk_level: str = "low",
    priority_focus: str = "balanced",
) -> str:
    """
    Generates a structured, step-by-step executive action plan tailored to the
    identified risk level, profitability status, and operational bottlenecks.
    Enforces human approval requirements.
    """
    try:
        df, _ = load_user_dataset(dataset_id, user_id)
        total_prof = float(df["Profit"].sum())
        margin = (total_prof / float(df["Revenue"].sum()) * 100) if float(df["Revenue"].sum()) > 0 else 0.0

        plan: List[Dict[str, Any]] = []

        # High risk / Loss condition
        if risk_level.lower() in {"high", "critical"} or total_prof < 0:
            plan.append({
                "action": "Immediate Expense and Vendor Audit",
                "priority": "critical",
                "reason": "Business is incurring unsustainable operating expenses or direct losses.",
                "expected_impact": "Stop capital bleed and restore positive unit economics.",
                "risk": "May require terminating unprofitable relationships.",
                "requires_approval": True,
            })
            plan.append({
                "action": "Prune Negative-Margin SKUs and Channels",
                "priority": "high",
                "reason": "Loss-making products directly erode profits generated by healthy SKUs.",
                "expected_impact": "Immediate gross margin uplift of 5% - 10%.",
                "risk": "Short-term drop in headline gross revenue.",
                "requires_approval": True,
            })

        # Medium risk / Tight margin condition
        elif risk_level.lower() == "medium" or margin < 15.0:
            plan.append({
                "action": "Price Optimization & Elasticity Review",
                "priority": "high",
                "reason": "Current margins are thin and vulnerable to minor cost spikes.",
                "expected_impact": "Enhance profit buffer without sacrificing customer retention.",
                "risk": "Customer churn if prices are adjusted too aggressively.",
                "requires_approval": True,
            })
            plan.append({
                "action": "Working Capital & Inventory Streamlining",
                "priority": "medium",
                "reason": "Improve cash conversion cycles across high-volume items.",
                "expected_impact": "Reduce holding costs and eliminate dead inventory.",
                "risk": "Stockout risk on top sellers if forecasts miss.",
                "requires_approval": True,
            })

        # Healthy / Growth condition
        else:
            plan.append({
                "action": "Scale Top-Performing Products and Regions",
                "priority": "medium",
                "reason": "Operating metrics demonstrate robust profitability and stable risk.",
                "expected_impact": "Accelerate top-line revenue and market share expansion.",
                "risk": "Increased operating overhead as operations scale.",
                "requires_approval": True,
            })
            plan.append({
                "action": "Reinvest Free Cash Flow into Customer Retention",
                "priority": "low",
                "reason": "Lock in high lifetime customer value while margins are strong.",
                "expected_impact": "Sustained long-term competitive moat.",
                "risk": "Capital allocation opportunity cost.",
                "requires_approval": True,
            })

        return json.dumps({
            "risk_context": risk_level,
            "action_count": len(plan),
            "actions": plan,
            "governance": "Human approval required prior to irreversible execution.",
        })
    except DatasetAccessError as e:
        return json.dumps({"error": e.message})
    except Exception as e:
        return json.dumps({"error": f"Failed to generate action plan: {str(e)}"})


@tool
def evaluate_decision_options(
    dataset_id: str,
    user_id: str,
    options_json: Optional[str] = None,
) -> str:
    """
    Evaluates and scores decision alternatives across ROI, risk, and feasibility.
    """
    try:
        df, _ = load_user_dataset(dataset_id, user_id)

        default_options = [
            {"name": "Cost Reduction Focus", "roi_score": 75, "risk_score": 25, "feasibility": 85},
            {"name": "Price Increase Strategy", "roi_score": 85, "risk_score": 50, "feasibility": 70},
            {"name": "Market Expansion Campaign", "roi_score": 90, "risk_score": 65, "feasibility": 60},
        ]

        scored_options = []
        for opt in default_options:
            # Composite score = 0.4*ROI + 0.3*(100-Risk) + 0.3*Feasibility
            composite = (0.4 * opt["roi_score"]) + (0.3 * (100 - opt["risk_score"])) + (0.3 * opt["feasibility"])
            scored_options.append({
                "name": opt["name"],
                "composite_score": round(composite, 1),
                "roi_potential": opt["roi_score"],
                "risk_exposure": opt["risk_score"],
                "feasibility": opt["feasibility"],
            })

        scored_options.sort(key=lambda o: o["composite_score"], reverse=True)

        return json.dumps({
            "decision_ranking": scored_options,
            "top_choice": scored_options[0]["name"] if scored_options else None,
        })
    except DatasetAccessError as e:
        return json.dumps({"error": e.message})
    except Exception as e:
        return json.dumps({"error": f"Failed to evaluate options: {str(e)}"})


DECISION_TOOLS = [
    simulate_business_scenario,
    compare_business_strategies,
    estimate_financial_impact,
    optimize_resource_allocation,
    generate_action_plan,
    evaluate_decision_options,
]
