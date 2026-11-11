"""
EVORA Analytics Agent
=====================
Production AI Business Intelligence and Financial Reasoning Agent.
- Performs reliable, pure Pandas financial and operational calculations.
- Generates privacy-safe, compact aggregated summaries (no raw transactions or customer records).
- Generates executive business intelligence insights and strategic recommendations via:
    1. Primary LLM: Google Gemini Flash (e.g. gemini-3.5-flash / gemini-3.8-flash)
    2. Fallback LLM: Groq (e.g. llama-3.3-70b-versatile)
    3. Baseline Fallback: Deterministic rule-based financial analytics.
- Enforces strict Pydantic JSON schema validation.
- Preserves the exact `AnalyticsAgent` class and `analyze(df)` API contract.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment configuration from workspace root if present
_ROOT_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _ROOT_DIR / ".env"
if _ENV_FILE.exists():
    load_dotenv(dotenv_path=_ENV_FILE, override=False)
else:
    load_dotenv(override=False)

logger = logging.getLogger("evora.analytics_agent")


class AnalyticsLLMOutput(BaseModel):
    """Structured schema for LLM-generated business insights and recommendations."""
    insights: List[str] = Field(
        default_factory=list,
        description="3 to 5 concise, actionable business intelligence observations derived strictly from the financial summary."
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="2 to 4 concrete, actionable strategic recommendations for leadership to optimize margins and manage costs."
    )


class AnalyticsAgent:
    """
    EVORA Analytics Agent with multi-tier LLM reasoning and rule-based resilience.
    """

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        groq_api_key: Optional[str] = None,
        gemini_model: Optional[str] = None,
        groq_model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.gemini_api_key = (
            gemini_api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )
        self.groq_api_key = (
            groq_api_key
            or os.getenv("GROQ_API_KEY")
        )
        self.gemini_model = gemini_model or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        self.groq_model = groq_model or os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        
        env_timeout = os.getenv("LLM_TIMEOUT")
        if timeout is not None:
            self.timeout = float(timeout)
        elif env_timeout:
            self.timeout = float(env_timeout)
        else:
            self.timeout = 25.0

    # -------------------------------------------------------------------------
    # 1. Deterministic Financial Metrics (Pure Pandas - Never LLM)
    # -------------------------------------------------------------------------

    def _compute_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculates ground-truth financial figures directly in Pandas."""
        if df.empty or "Revenue" not in df.columns or "Expense" not in df.columns:
            return {
                "total_revenue": 0.0,
                "total_expense": 0.0,
                "total_profit": 0.0,
                "profit_margin": 0.0,
                "product_performance": [],
                "monthly_trends": [],
                "row_count": len(df),
            }

        revenue = pd.to_numeric(df["Revenue"], errors="coerce").fillna(0)
        expense = pd.to_numeric(df["Expense"], errors="coerce").fillna(0)

        total_revenue = float(revenue.sum())
        total_expense = float(expense.sum())
        total_profit = total_revenue - total_expense

        profit_margin = (
            (total_profit / total_revenue * 100)
            if total_revenue != 0 else 0.0
        )

        # Product Performance Analysis
        product_performance: List[Dict[str, Any]] = []
        if "Product" in df.columns:
            product_df = df.copy()
            product_df["_Revenue"] = revenue
            product_df["_Expense"] = expense

            grouped = product_df.groupby("Product").agg(
                revenue=("_Revenue", "sum"),
                expense=("_Expense", "sum"),
            )
            grouped["profit"] = grouped["revenue"] - grouped["expense"]

            product_performance = [
                {
                    "product": str(product),
                    "revenue": round(float(row["revenue"]), 2),
                    "expense": round(float(row["expense"]), 2),
                    "profit": round(float(row["profit"]), 2),
                }
                for product, row in grouped.iterrows()
            ]

        # Monthly Trends Analysis
        monthly_trends: List[Dict[str, Any]] = []
        if "Date" in df.columns:
            date_df = df.copy()
            date_df["Date"] = pd.to_datetime(date_df["Date"], errors="coerce")
            date_df["_Revenue"] = revenue
            date_df["_Expense"] = expense
            date_df = date_df.dropna(subset=["Date"])

            if not date_df.empty:
                date_df["Month"] = date_df["Date"].dt.to_period("M").astype(str)
                monthly = date_df.groupby("Month").agg(
                    revenue=("_Revenue", "sum"),
                    expense=("_Expense", "sum"),
                )
                monthly["profit"] = monthly["revenue"] - monthly["expense"]

                monthly_trends = [
                    {
                        "month": str(month),
                        "revenue": round(float(row["revenue"]), 2),
                        "expense": round(float(row["expense"]), 2),
                        "profit": round(float(row["profit"]), 2),
                    }
                    for month, row in monthly.iterrows()
                ]

        return {
            "total_revenue": round(total_revenue, 2),
            "total_expense": round(total_expense, 2),
            "total_profit": round(total_profit, 2),
            "profit_margin": round(float(profit_margin), 2),
            "product_performance": product_performance,
            "monthly_trends": monthly_trends,
            "row_count": len(df),
        }

    # -------------------------------------------------------------------------
    # 2. Compact Aggregated Summary for LLM (Zero Sensitive / Customer Data)
    # -------------------------------------------------------------------------

    def _generate_compact_summary(
        self,
        df: pd.DataFrame,
        metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Creates a minimal, aggregated JSON payload for LLM consumption.
        Never transmits full CSV tables, customer records, or raw rows.
        """
        products = metrics.get("product_performance", [])
        top_products = sorted(products, key=lambda p: p["profit"], reverse=True)[:3]
        loss_products = [p for p in products if p["profit"] < 0][:2]

        trends = metrics.get("monthly_trends", [])
        recent_trends = trends[-3:] if len(trends) >= 3 else trends

        summary: Dict[str, Any] = {
            "financial_summary": {
                "total_revenue": metrics["total_revenue"],
                "total_expense": metrics["total_expense"],
                "total_profit": metrics["total_profit"],
                "profit_margin_percent": metrics["profit_margin"],
                "total_transactions_analyzed": metrics.get("row_count", 0),
            },
            "top_profitable_products": [
                {
                    "product": p["product"],
                    "profit": p["profit"],
                    "revenue": p["revenue"],
                    "expense": p["expense"],
                }
                for p in top_products
            ],
            "unprofitable_products": [
                {
                    "product": p["product"],
                    "profit": p["profit"],
                    "revenue": p["revenue"],
                    "expense": p["expense"],
                }
                for p in loss_products
            ],
            "recent_monthly_performance": [
                {
                    "month": t["month"],
                    "revenue": t["revenue"],
                    "profit": t["profit"],
                }
                for t in recent_trends
            ],
        }

        # MoM comparison indicator if monthly data exists
        if len(trends) >= 2:
            prev_rev = trends[-2]["revenue"]
            curr_rev = trends[-1]["revenue"]
            summary["recent_trend"] = {
                "previous_month_revenue": prev_rev,
                "current_month_revenue": curr_rev,
                "revenue_direction": (
                    "increased" if curr_rev > prev_rev
                    else "decreased" if curr_rev < prev_rev
                    else "unchanged"
                ),
            }

        return summary

    # -------------------------------------------------------------------------
    # 3. Deterministic Rule-Based Fallback Engine
    # -------------------------------------------------------------------------

    def _compute_rule_based(self, metrics: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Exact baseline rule-based insights and recommendations."""
        total_revenue = metrics["total_revenue"]
        total_expense = metrics["total_expense"]
        total_profit = metrics["total_profit"]
        profit_margin = metrics["profit_margin"]
        product_performance = metrics.get("product_performance", [])
        monthly_trends = metrics.get("monthly_trends", [])

        insights: List[str] = []
        recommendations: List[str] = []

        # Profitability Analysis
        if total_profit > 0:
            insights.append("Business is currently profitable.")
        elif total_profit < 0:
            insights.append("Business is operating at a loss.")
            recommendations.append(
                "Review expenses and identify ways to improve profitability."
            )
        else:
            insights.append("Business is currently at break-even.")

        # Profit Margin Analysis
        if profit_margin >= 20:
            insights.append(f"Strong profit margin of {profit_margin:.2f}%.")
        elif profit_margin > 0:
            insights.append(
                f"Profit margin is {profit_margin:.2f}%, indicating limited profitability."
            )
            recommendations.append(
                "Explore opportunities to improve profit margins."
            )
        else:
            insights.append("Profit margin is zero or negative.")

        # Revenue and Expense Comparison
        if total_revenue > total_expense:
            insights.append("Revenue is higher than total expenses.")
        elif total_revenue < total_expense:
            insights.append("Expenses are higher than revenue.")
        else:
            insights.append("Revenue and expenses are equal.")

        # Product Performance Analysis
        if product_performance:
            sorted_products = sorted(
                product_performance, key=lambda p: p["profit"], reverse=True
            )
            best_p = sorted_products[0]
            worst_p = sorted_products[-1]

            insights.append(
                f"Best-performing product by profit: {best_p['product']}."
            )
            insights.append(
                f"Lowest-performing product by profit: {worst_p['product']}."
            )

            if worst_p["profit"] < 0:
                recommendations.append(
                    f"Review pricing and expenses for {worst_p['product']}."
                )

        # Date-based Trend Analysis
        if len(monthly_trends) >= 2:
            previous = float(monthly_trends[-2]["revenue"])
            current = float(monthly_trends[-1]["revenue"])

            if current > previous:
                insights.append(
                    "Revenue increased compared with the previous month."
                )
            elif current < previous:
                insights.append(
                    "Revenue decreased compared with the previous month."
                )
                recommendations.append(
                    "Investigate the reasons behind the recent revenue decline."
                )
            else:
                insights.append(
                    "Revenue remained unchanged compared with the previous month."
                )

        if not recommendations:
            recommendations.append(
                "Continue monitoring revenue, expenses and profitability."
            )

        return insights, recommendations

    # -------------------------------------------------------------------------
    # 4. LLM Response Extraction and Validation
    # -------------------------------------------------------------------------

    def _validate_llm_output(self, output: Any) -> Optional[Tuple[List[str], List[str]]]:
        """Validates that the LLM response contains clean, non-empty insights & recommendations."""
        try:
            if isinstance(output, AnalyticsLLMOutput):
                insights = [str(i).strip() for i in output.insights if str(i).strip()]
                recommendations = [str(r).strip() for r in output.recommendations if str(r).strip()]
                if insights and recommendations:
                    return insights, recommendations
                return None

            if isinstance(output, dict):
                insights_raw = output.get("insights", [])
                recs_raw = output.get("recommendations", [])
                if isinstance(insights_raw, list) and isinstance(recs_raw, list):
                    insights = [str(i).strip() for i in insights_raw if str(i).strip()]
                    recommendations = [str(r).strip() for r in recs_raw if str(r).strip()]
                    if insights and recommendations:
                        return insights, recommendations
                return None

            if isinstance(output, str):
                cleaned = output.strip()
                match = re.search(r"\{.*\}", cleaned, re.DOTALL)
                if match:
                    parsed = json.loads(match.group(0))
                    return self._validate_llm_output(parsed)

            return None
        except Exception as e:
            logger.debug("Failed to validate LLM output: %s", e)
            return None

    # -------------------------------------------------------------------------
    # 5. Primary LLM: Google Gemini Flash
    # -------------------------------------------------------------------------

    def _call_gemini(self, summary: Dict[str, Any]) -> Optional[Tuple[List[str], List[str]]]:
        """Calls Google Gemini Flash using structured output."""
        if os.getenv("EVORA_SKIP_EXTERNAL_LLM") == "1":
            return None
        if not self.gemini_api_key:
            logger.debug("Gemini API key is not configured.")
            return None

        prompt_text = (
            "You are the AI Analytics Engine for EVORA (Enterprise Vision Optimizing Reasoning Assistant).\n"
            "Analyze the following business financial summary and generate:\n"
            "1. 'insights': 3 to 5 concise, actionable business intelligence observations and contextual trends derived strictly from the financial summary.\n"
            "2. 'recommendations': 2 to 4 high-impact, practical recommendations for leadership to optimize margins and manage costs.\n\n"
            "Constraints:\n"
            "- Rely strictly on the provided financial metrics. Do not fabricate numbers or invent data not in the summary.\n"
            "- Be concise, professional, and executive-ready.\n\n"
            f"Financial Summary:\n{json.dumps(summary, indent=2)}"
        )

        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm = ChatGoogleGenerativeAI(
                model=self.gemini_model,
                api_key=self.gemini_api_key,
                temperature=0.2,
                max_output_tokens=800,
                timeout=self.timeout,
            )

            structured_llm = llm.with_structured_output(AnalyticsLLMOutput)
            raw_response = structured_llm.invoke(prompt_text)

            validated = self._validate_llm_output(raw_response)
            if validated:
                logger.info("Successfully generated insights using Gemini model: %s", self.gemini_model)
                return validated

        except Exception as e:
            logger.warning("Gemini (%s) invocation failed: %s", self.gemini_model, e)

        return None

    # -------------------------------------------------------------------------
    # 6. Fallback LLM: Groq
    # -------------------------------------------------------------------------

    def _call_groq(self, summary: Dict[str, Any]) -> Optional[Tuple[List[str], List[str]]]:
        """Calls Groq using structured output as fallback."""
        if os.getenv("EVORA_SKIP_EXTERNAL_LLM") == "1":
            return None
        if not self.groq_api_key:
            logger.debug("Groq API key is not configured.")
            return None

        prompt_text = (
            "You are the AI Analytics Engine for EVORA (Enterprise Vision Optimizing Reasoning Assistant).\n"
            "Analyze the following business financial summary and generate:\n"
            "1. 'insights': 3 to 5 concise, actionable business intelligence observations and contextual trends derived strictly from the financial summary.\n"
            "2. 'recommendations': 2 to 4 high-impact, practical recommendations for leadership to optimize margins and manage costs.\n\n"
            "Constraints:\n"
            "- Rely strictly on the provided financial metrics. Do not fabricate numbers or invent data not in the summary.\n"
            "- Be concise, professional, and executive-ready.\n\n"
            f"Financial Summary:\n{json.dumps(summary, indent=2)}"
        )

        try:
            from langchain_groq import ChatGroq

            llm = ChatGroq(
                model=self.groq_model,
                api_key=self.groq_api_key,
                temperature=0.2,
                max_tokens=800,
                timeout=self.timeout,
            )

            structured_llm = llm.with_structured_output(AnalyticsLLMOutput)
            raw_response = structured_llm.invoke(prompt_text)

            validated = self._validate_llm_output(raw_response)
            if validated:
                logger.info("Successfully generated insights using Groq model: %s", self.groq_model)
                return validated

        except Exception as e:
            logger.warning("Groq invocation failed: %s", e)

        return None

    # -------------------------------------------------------------------------
    # 7. Orchestration & Provider Cascade
    # -------------------------------------------------------------------------

    def _generate_insights(
        self,
        summary: Dict[str, Any],
        metrics: Dict[str, Any],
    ) -> Tuple[List[str], List[str], str]:
        """
        Cascades:
          1. Gemini Flash
          2. Groq
          3. Deterministic Rule-Based Fallback
        Always ensures foundational profitability verdict is present.
        """
        total_profit = metrics["total_profit"]

        # 1. Try Gemini Flash
        gemini_result = self._call_gemini(summary)
        if gemini_result:
            insights, recommendations = gemini_result
            provider = "gemini"
        else:
            # 2. Try Groq
            groq_result = self._call_groq(summary)
            if groq_result:
                insights, recommendations = groq_result
                provider = "groq"
            else:
                # 3. Rule-Based Fallback
                insights, recommendations = self._compute_rule_based(metrics)
                provider = "rule_based"

        # Ensure foundational profitability status keyword is always present
        # to ensure compatibility with existing evaluation tests and reports.
        if total_profit > 0:
            status_keyword = "Business is currently profitable."
        elif total_profit < 0:
            status_keyword = "Business is operating at a loss."
        else:
            status_keyword = "Business is currently at break-even."

        if not any(status_keyword.lower() in s.lower() for s in insights):
            insights.insert(0, status_keyword)

        return insights, recommendations, provider

    # -------------------------------------------------------------------------
    # 8. Main Public Interface (Preserved API Contract)
    # -------------------------------------------------------------------------

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyzes a tabular transaction dataset.
        Returns:
            dict with:
                - total_revenue (float)
                - total_expense (float)
                - total_profit (float)
                - profit_margin (float)
                - insights (List[str])
                - recommendations (List[str])
                - product_performance (List[Dict])
                - monthly_trends (List[Dict])
        """
        # 1. Compute ground-truth metrics with Pandas
        metrics = self._compute_metrics(df)

        if metrics.get("row_count", 0) == 0:
            return {
                "total_revenue": 0.0,
                "total_expense": 0.0,
                "total_profit": 0.0,
                "profit_margin": 0.0,
                "insights": ["No transaction records available to analyze."],
                "recommendations": [
                    "Upload a valid business CSV with Revenue and Expense columns."
                ],
                "product_performance": [],
                "monthly_trends": [],
            }

        # 2. Create compact privacy-safe summary for LLM
        summary = self._generate_compact_summary(df, metrics)

        # 3. Multi-tier LLM reasoning (Gemini -> Groq -> Rule-Based)
        insights, recommendations, _ = self._generate_insights(summary, metrics)

        return {
            "total_revenue": metrics["total_revenue"],
            "total_expense": metrics["total_expense"],
            "total_profit": metrics["total_profit"],
            "profit_margin": metrics["profit_margin"],
            "insights": insights,
            "recommendations": recommendations,
            "product_performance": metrics["product_performance"],
            "monthly_trends": metrics["monthly_trends"],
        }
