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

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from agents.config import (
    ModelQuotaManager,
    create_gemini_chat_model,
    create_groq_chat_model,
    get_analytics_model,
    get_groq_model,
)

# Load environment configuration from workspace root if present (override=False preserves deployment precedence)
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
        self.gemini_model = gemini_model or get_analytics_model()
        self.groq_model = groq_model or get_groq_model()
        
        env_timeout = os.getenv("LLM_TIMEOUT")
        if timeout is not None:
            self.timeout = float(timeout)
        elif env_timeout:
            self.timeout = float(env_timeout)
        else:
            self.timeout = 15.0

    # -------------------------------------------------------------------------
    # 1. Deterministic Financial Metrics (Pure Pandas - Never LLM)
    # -------------------------------------------------------------------------

    def _compute_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate ground-truth financial metrics from valid numeric rows only.

        Rows with missing, non-numeric, or infinite Revenue/Expense values are
        excluded from both sides of the calculation so revenue and expense
        totals always use the same transaction population.
        """
        if not isinstance(df, pd.DataFrame):
            raise TypeError("AnalyticsAgent expects a pandas DataFrame.")

        if df.empty:
            return {
                "total_revenue": 0.0,
                "total_expense": 0.0,
                "total_profit": 0.0,
                "profit_margin": 0.0,
                "product_performance": [],
                "monthly_trends": [],
                "row_count": 0,
                "data_quality": {
                    "valid_financial_rows": 0,
                    "excluded_financial_rows": 0,
                    "invalid_revenue_values": 0,
                    "invalid_expense_values": 0,
                    "profit_margin_available": False,
                },
            }

        required_columns = ("Revenue", "Expense")
        missing_columns = [column for column in required_columns if column not in df.columns]
        if missing_columns:
            raise ValueError(
                "Analytics requires the following financial columns: "
                + ", ".join(missing_columns)
            )

        revenue_values = pd.to_numeric(df["Revenue"], errors="coerce").to_numpy(dtype="float64")
        expense_values = pd.to_numeric(df["Expense"], errors="coerce").to_numpy(dtype="float64")
        valid_revenue = np.isfinite(revenue_values)
        valid_expense = np.isfinite(expense_values)
        valid_mask = valid_revenue & valid_expense

        valid_count = int(valid_mask.sum())
        if valid_count == 0:
            raise ValueError(
                "No rows contain both valid numeric Revenue and Expense values. "
                "Check the uploaded dataset before running analytics."
            )

        # Use the same valid rows for revenue, expenses, profit and breakdowns.
        valid_revenue_values = revenue_values[valid_mask]
        valid_expense_values = expense_values[valid_mask]
        total_revenue = float(valid_revenue_values.sum())
        total_expense = float(valid_expense_values.sum())
        total_profit = total_revenue - total_expense
        profit_margin_available = total_revenue > 0
        profit_margin = (total_profit / total_revenue * 100) if profit_margin_available else 0.0

        data_quality = {
            "valid_financial_rows": valid_count,
            "excluded_financial_rows": int((~valid_mask).sum()),
            "invalid_revenue_values": int((~valid_revenue).sum()),
            "invalid_expense_values": int((~valid_expense).sum()),
            "profit_margin_available": profit_margin_available,
        }

        # Product Performance Analysis
        product_performance: List[Dict[str, Any]] = []
        if "Product" in df.columns:
            product_df = pd.DataFrame({
                "Product": df.loc[valid_mask, "Product"].to_numpy(),
                "_Revenue": valid_revenue_values,
                "_Expense": valid_expense_values,
            })
            grouped = product_df.groupby("Product", dropna=True).agg(
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
            date_df = pd.DataFrame({
                "Date": pd.to_datetime(df.loc[valid_mask, "Date"], errors="coerce").to_numpy(),
                "_Revenue": valid_revenue_values,
                "_Expense": valid_expense_values,
            }).dropna(subset=["Date"])

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
            "data_quality": data_quality,
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
                "total_transactions_analyzed": metrics.get("data_quality", {}).get(
                    "valid_financial_rows", metrics.get("row_count", 0)
                ),
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
                    "month": t.get("month") or t.get("period", "unknown"),
                    "revenue": t.get("revenue", 0.0),
                    "profit": t.get("profit", 0.0),
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

    @staticmethod
    def _numeric_values_in_source(value: Any) -> set:
        """Collect finite numeric values explicitly present in the supplied summary."""
        values = set()
        numeric_pattern = re.compile(r"(?<![A-Za-z])(-?\d[\d,]*(?:\.\d+)?)(?![A-Za-z])")

        def visit(item: Any) -> None:
            if isinstance(item, bool) or item is None:
                return
            if isinstance(item, (int, float, np.number)):
                number = float(item)
                if np.isfinite(number):
                    values.add(number)
                return
            if isinstance(item, dict):
                for nested in item.values():
                    visit(nested)
                return
            if isinstance(item, (list, tuple)):
                for nested in item:
                    visit(nested)
                return
            if isinstance(item, str):
                for match in numeric_pattern.finditer(item):
                    try:
                        number = float(match.group(1).replace(",", ""))
                        if np.isfinite(number):
                            values.add(number)
                    except (TypeError, ValueError):
                        continue

        visit(value)
        return values

    def _has_only_grounded_numeric_claims(
        self,
        texts: List[str],
        summary: Optional[Dict[str, Any]],
    ) -> bool:
        """Reject LLM output containing numeric claims absent from source metrics."""
        if summary is None:
            return True

        allowed_values = self._numeric_values_in_source(summary)
        claim_pattern = re.compile(
            r"(?<![A-Za-z])(?:₹\s*)?(-?\d[\d,]*(?:\.\d+)?)\s*(?:%|percent)?(?![A-Za-z])",
            re.IGNORECASE,
        )
        for text_value in texts:
            for match in claim_pattern.finditer(text_value):
                try:
                    claimed = float(match.group(1).replace(",", ""))
                except (TypeError, ValueError):
                    return False
                if not any(
                    abs(claimed - allowed) <= max(1e-6, abs(allowed) * 1e-6)
                    for allowed in allowed_values
                ):
                    logger.warning(
                        "Rejected LLM output containing an unsupported numeric claim: %s",
                        match.group(0).strip(),
                    )
                    return False
        return True

    def _validate_llm_output(
        self,
        output: Any,
        summary: Optional[Dict[str, Any]] = None,
    ) -> Optional[Tuple[List[str], List[str]]]:
        """Validate schema, text quality and numeric claims against source metrics."""
        try:
            if isinstance(output, AnalyticsLLMOutput):
                insights_raw = output.insights
                recs_raw = output.recommendations
            elif isinstance(output, dict):
                insights_raw = output.get("insights", [])
                recs_raw = output.get("recommendations", [])
            elif isinstance(output, str):
                match = re.search(r"\{.*\}", output.strip(), re.DOTALL)
                if not match:
                    return None
                return self._validate_llm_output(json.loads(match.group(0)), summary)
            else:
                return None

            if not isinstance(insights_raw, list) or not isinstance(recs_raw, list):
                return None

            def clean(items: List[Any]) -> List[str]:
                cleaned: List[str] = []
                seen = set()
                for item in items:
                    if not isinstance(item, str):
                        continue
                    value = item.strip()
                    if not value or len(value) > 600:
                        continue
                    normalized = value.casefold()
                    if normalized not in seen:
                        seen.add(normalized)
                        cleaned.append(value)
                return cleaned

            insights = clean(insights_raw)
            recommendations = clean(recs_raw)
            if not insights or not recommendations:
                return None

            if not self._has_only_grounded_numeric_claims(insights + recommendations, summary):
                return None
            return insights[:5], recommendations[:4]
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
        exhausted, reason = ModelQuotaManager.is_exhausted(self.gemini_model)
        if exhausted:
            logger.info("Skipping quota-exhausted Gemini model %s: %s", self.gemini_model, reason)
            return None

        prompt_text = (
            "You are the AI Analytics Engine for EVORA (Enterprise Vision Optimizing Reasoning Assistant).\n"
            "Analyze the following business financial summary and generate:\n"
            "1. 'insights': 3 to 5 concise, actionable business intelligence observations and contextual trends derived strictly from the financial summary.\n"
            "2. 'recommendations': 2 to 4 high-impact, practical recommendations for leadership to optimize margins and manage costs.\n\n"
            "Constraints:\n"
            "- Rely strictly on the provided financial metrics. Do not fabricate numbers or invent data not in the summary.\n"
            "- Do not include any numerical value unless that exact value is supported by the summary.\n"
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

            validated = self._validate_llm_output(raw_response, summary)
            if validated:
                logger.info("Successfully generated insights using Gemini model: %s", self.gemini_model)
                return validated

        except Exception as e:
            logger.warning("Gemini (%s) invocation failed: %s", self.gemini_model, e)
            if ModelQuotaManager.is_quota_error(e):
                ModelQuotaManager.mark_exhausted(self.gemini_model, str(e))

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
            "- Do not include any numerical value unless that exact value is supported by the summary.\n"
            "- Be concise, professional, and executive-ready.\n\n"
            f"Financial Summary:\n{json.dumps(summary, indent=2)}"
        )

        try:
            llm = create_groq_chat_model(
                model_name=self.groq_model,
                api_key=self.groq_api_key,
                temperature=0.2,
                timeout=self.timeout,
            )

            structured_llm = llm.with_structured_output(AnalyticsLLMOutput)
            raw_response = structured_llm.invoke(prompt_text)

            validated = self._validate_llm_output(raw_response, summary)
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

        logger.info("Analytics insights generated using provider: %s", provider)
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
                "data_quality": metrics.get("data_quality", {}),
            }

        # 2. Create compact privacy-safe summary for LLM
        summary = self._generate_compact_summary(df, metrics)

        # 3. Multi-tier LLM reasoning (Gemini -> Groq -> Rule-Based)
        insights, recommendations, _ = self._generate_insights(summary, metrics)
        quality = metrics.get("data_quality", {})
        excluded_rows = int(quality.get("excluded_financial_rows", 0))
        if excluded_rows:
            insights.append(
                f"Financial totals use {quality.get('valid_financial_rows', 0)} valid rows; "
                f"{excluded_rows} rows with invalid Revenue or Expense values were excluded."
            )
        if not quality.get("profit_margin_available", True):
            insights.append("Profit margin is unavailable because total revenue is not positive.")

        return {
            "total_revenue": metrics["total_revenue"],
            "total_expense": metrics["total_expense"],
            "total_profit": metrics["total_profit"],
            "profit_margin": metrics["profit_margin"],
            "insights": insights,
            "recommendations": recommendations,
            "product_performance": metrics["product_performance"],
            "monthly_trends": metrics["monthly_trends"],
            "data_quality": quality,
        }

    # -------------------------------------------------------------------------
    # 9. Multi-Agent Workflow Interface (LangChain Tool-Calling Agent)
    # -------------------------------------------------------------------------

    def _resolve_llm(self) -> Tuple[Any, str, Optional[str]]:
        """Resolve the first available provider and report which one was selected."""
        if os.getenv("EVORA_SKIP_EXTERNAL_LLM", "0") == "1":
            return (
                AnalyticsToolCallingModel(agent_instance=self),
                "deterministic_fallback",
                "External LLM calls are disabled by EVORA_SKIP_EXTERNAL_LLM=1",
            )

        init_errors: List[str] = []
        is_exhausted, exhaust_reason = ModelQuotaManager.is_exhausted(self.gemini_model)
        if self.gemini_api_key and not is_exhausted:
            try:
                llm = create_gemini_chat_model(
                    model_name=self.gemini_model,
                    api_key=self.gemini_api_key,
                    timeout=self.timeout,
                )
                return llm, "gemini", None
            except Exception as e:
                logger.warning("Failed to initialize Gemini for AnalyticsAgent: %s", e)
                init_errors.append(f"Gemini initialization failed: {e}")
                if ModelQuotaManager.is_quota_error(e):
                    ModelQuotaManager.mark_exhausted(self.gemini_model, str(e))
        elif is_exhausted:
            init_errors.append(f"Gemini quota exhausted: {exhaust_reason}")

        if self.groq_api_key:
            try:
                llm = create_groq_chat_model(
                    model_name=self.groq_model,
                    api_key=self.groq_api_key,
                    temperature=0.1,
                    timeout=self.timeout,
                )
                return llm, "groq", "; ".join(init_errors) or None
            except Exception as e:
                logger.warning("Failed to initialize Groq for AnalyticsAgent: %s", e)
                init_errors.append(f"Groq initialization failed: {e}")

        fallback_reason = "; ".join(init_errors) or "No external LLM provider is configured"
        return AnalyticsToolCallingModel(agent_instance=self), "deterministic_fallback", fallback_reason

    def get_llm(self) -> Any:
        """Backward-compatible LLM resolver; returns the selected model only."""
        return self._resolve_llm()[0]

    def build_langchain_agent(self, llm: Optional[Any] = None) -> Any:
        """Constructs a real LangChain tool-calling agent using create_agent."""
        from langchain.agents import create_agent
        from tools.analytics_tools import (
            get_dataset_profile,
            calculate_business_metrics,
            analyze_time_trends,
            compare_business_segments,
            analyze_product_performance,
            query_business_data,
            analyze_relationships,
        )

        tools = [
            get_dataset_profile,
            calculate_business_metrics,
            analyze_time_trends,
            compare_business_segments,
            analyze_product_performance,
            query_business_data,
            analyze_relationships,
        ]

        system_prompt = (
            "You are the EVORA Analytics Agent, an advanced business intelligence AI.\n"
            "You have access to 7 specialized tools to analyze business financial data.\n"
            "Select and execute the appropriate tools using dataset_id and user_id.\n"
            "Always inspect ground truth data via tools. Never guess numbers.\n"
            "Synthesize your findings into clear, concise executive insights."
        )

        model = llm or self.get_llm()
        return create_agent(model=model, tools=tools, system_prompt=system_prompt)

    @staticmethod
    def _decode_tool_payload(payload: Any) -> Any:
        """Decode JSON tool content while accepting already-decoded dictionaries."""
        if isinstance(payload, (dict, list)):
            return payload
        if isinstance(payload, str):
            try:
                return json.loads(payload)
            except (TypeError, ValueError):
                return payload
        return payload

    @staticmethod
    def _finite_metric(metrics: Dict[str, Any], key: str) -> float:
        """Read a required numeric metric without silently substituting zero."""
        if key not in metrics or metrics[key] is None:
            raise ValueError(f"Analytics tool output is missing required metric '{key}'.")
        try:
            value = float(metrics[key])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Analytics tool returned a non-numeric '{key}' value.") from exc
        if not np.isfinite(value):
            raise ValueError(f"Analytics tool returned a non-finite '{key}' value.")
        return value

    def run_agent(
        self,
        dataset_id: str,
        user_id: str,
        user_query: str = "",
    ) -> "AnalyticsAgentOutput":
        """
        Executes genuine LangChain tool-backed analytics for the multi-agent workflow.
        Returns validated AnalyticsAgentOutput schema.
        """
        from langchain_core.messages import HumanMessage, ToolMessage
        from schemas.agent_schemas import AnalyticsAgentOutput, EvidenceItem
        from tools.dataset_tools import load_user_dataset

        df, meta = load_user_dataset(dataset_id, user_id)

        prompt = (
            f"Dataset ID: {dataset_id}\n"
            f"User ID: {user_id}\n"
            f"User Question: {user_query or 'Provide a comprehensive financial and operational analytics report.'}"
        )

        # 1. Resolve and execute the actual LangChain agent.
        llm, selected_provider, init_error = self._resolve_llm()
        model_error: Optional[str] = init_error
        if selected_provider == "gemini":
            model_used = self.gemini_model
            execution_mode = "llm"
        elif selected_provider == "groq":
            model_used = self.groq_model
            execution_mode = "groq_fallback"
        else:
            model_used = f"deterministic_fallback (requested: {self.gemini_model})"
            execution_mode = "deterministic_fallback"

        try:
            agent = self.build_langchain_agent(llm=llm)
            res = agent.invoke({"messages": [HumanMessage(content=prompt)]})
        except Exception as primary_error:
            if selected_provider == "deterministic_fallback":
                raise

            model_error = str(primary_error)
            logger.warning(
                "Analytics %s agent invocation failed: %s",
                selected_provider,
                primary_error,
            )
            if selected_provider == "gemini" and ModelQuotaManager.is_quota_error(primary_error):
                ModelQuotaManager.mark_exhausted(self.gemini_model, str(primary_error))

            groq_succeeded = False
            if selected_provider != "groq" and self.groq_api_key:
                try:
                    groq_llm = create_groq_chat_model(
                        model_name=self.groq_model,
                        api_key=self.groq_api_key,
                        temperature=0.1,
                        timeout=self.timeout,
                    )
                    groq_agent = self.build_langchain_agent(llm=groq_llm)
                    res = groq_agent.invoke({"messages": [HumanMessage(content=prompt)]})
                    execution_mode = "groq_fallback"
                    model_used = self.groq_model
                    groq_succeeded = True
                except Exception as groq_error:
                    logger.warning("Analytics Groq fallback failed: %s", groq_error)
                    model_error = f"{primary_error}; Groq fallback failed: {groq_error}"

            if not groq_succeeded:
                fallback_model = AnalyticsToolCallingModel(agent_instance=self)
                fallback_agent = self.build_langchain_agent(llm=fallback_model)
                res = fallback_agent.invoke({"messages": [HumanMessage(content=prompt)]})
                execution_mode = "deterministic_fallback"
                model_used = f"deterministic_fallback (requested: {self.gemini_model})"

        # 2. Extract tool messages and findings from the agent conversation
        messages = res.get("messages", [])
        tool_results: Dict[str, Any] = {}
        for m in messages:
            if isinstance(m, ToolMessage):
                tool_name = getattr(m, "name", None) or "unknown"
                tool_results[tool_name] = self._decode_tool_payload(m.content)

        # 3. Ensure core metrics are present from tool output
        metrics = tool_results.get("calculate_business_metrics")
        if not metrics or not isinstance(metrics, dict):
            from tools.analytics_tools import calculate_business_metrics
            metrics_raw = calculate_business_metrics.invoke({"dataset_id": dataset_id, "user_id": user_id})
            metrics = self._decode_tool_payload(metrics_raw)

        if not isinstance(metrics, dict):
            raise ValueError("Analytics metrics tool returned an invalid response.")
        total_revenue = self._finite_metric(metrics, "total_revenue")
        total_expenses = self._finite_metric(metrics, "total_expenses")
        total_profit = self._finite_metric(metrics, "total_profit")
        profit_margin = self._finite_metric(metrics, "profit_margin_pct")

        # 4. Extract product performance and trends if called
        products_res = self._decode_tool_payload(tool_results.get("analyze_product_performance")) or {}
        trends_res = self._decode_tool_payload(tool_results.get("analyze_time_trends")) or {}
        segments_res = self._decode_tool_payload(tool_results.get("compare_business_segments")) or {}
        if not isinstance(products_res, dict):
            products_res = {}
        if not isinstance(trends_res, dict):
            trends_res = {}
        if not isinstance(segments_res, dict):
            segments_res = {}

        # 5. Assemble evidence items
        evidence: List[EvidenceItem] = [
            EvidenceItem(
                description=f"Total gross revenue calculated from {len(df)} records.",
                metric="total_revenue",
                value=total_revenue,
                source="calculate_business_metrics",
            ),
            EvidenceItem(
                description="Total operational and product expenses.",
                metric="total_expenses",
                value=total_expenses,
                source="calculate_business_metrics",
            ),
            EvidenceItem(
                description="Net total business profit.",
                metric="total_profit",
                value=total_profit,
                source="calculate_business_metrics",
            ),
            EvidenceItem(
                description="Operating profit margin percentage.",
                metric="profit_margin",
                value=f"{profit_margin:.2f}%",
                source="calculate_business_metrics",
            ),
        ]

        if segments_res.get("available") and segments_res.get("top_segment"):
            top_seg = segments_res["top_segment"]
            evidence.append(
                EvidenceItem(
                    description=f"Top segment by profit: {top_seg.get('segment')}",
                    metric="top_segment_profit",
                    value=top_seg.get("profit"),
                    source="compare_business_segments",
                )
            )

        # 6. Generate natural language insights and recommendations
        summary_payload = self._generate_compact_summary(df, {
            "total_revenue": total_revenue,
            "total_expense": total_expenses,
            "total_profit": total_profit,
            "profit_margin": profit_margin,
            "row_count": len(df),
            "product_performance": products_res.get("top_profitable_products", []),
            "monthly_trends": trends_res.get("trends", []),
        })
        if user_query:
            summary_payload["user_question"] = user_query

        insights, recommendations, _ = self._generate_insights(summary_payload, {
            "total_revenue": total_revenue,
            "total_expense": total_expenses,
            "total_profit": total_profit,
            "profit_margin": profit_margin,
            "product_performance": products_res.get("top_profitable_products", []),
            "monthly_trends": trends_res.get("trends", []),
        })

        summary_text = (
            f"Business recorded ₹{total_revenue:,.2f} in revenue and ₹{total_expenses:,.2f} in expenses, "
            f"yielding a net profit of ₹{total_profit:,.2f} (profit margin: {profit_margin:.2f}%)."
        )

        return AnalyticsAgentOutput(
            total_revenue=total_revenue,
            total_expenses=total_expenses,
            total_profit=total_profit,
            profit_margin=profit_margin,
            key_findings=insights,
            recommendations=recommendations,
            evidence=evidence,
            product_performance=products_res.get("top_profitable_products", []),
            monthly_trends=trends_res.get("trends", []),
            row_count=len(df),
            summary=summary_text,
            model_used=model_used,
            execution_mode=execution_mode,
            model_error=model_error,
        )


class AnalyticsToolCallingModel:
    """
    Deterministic tool-calling chat model for the Analytics Agent.
    Implements bind_tools to integrate seamlessly with LangChain's create_agent() runner.
    Autonomously selects appropriate tools based on user question and business query.
    """
    def __init__(self, agent_instance: Any = None):
        self.agent_instance = agent_instance
        self.bound_tools: List[Any] = []

    @property
    def _llm_type(self) -> str:
        return "evora_analytics_tool_calling_model"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "AnalyticsToolCallingModel":
        self.bound_tools = list(tools)
        return self

    def _generate(
        self,
        messages: List[Any],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> Any:
        from langchain_core.messages import AIMessage, ToolMessage
        from langchain_core.outputs import ChatGeneration, ChatResult

        tool_messages = [m for m in messages if isinstance(m, ToolMessage)]

        # Turn 1: LLM tool selection turn
        if not tool_messages:
            human_text = ""
            for m in reversed(messages):
                if getattr(m, "type", None) == "human" or m.__class__.__name__ == "HumanMessage":
                    human_text = str(m.content)
                    break

            dataset_id = ""
            user_id = ""
            for line in human_text.splitlines():
                if line.startswith("Dataset ID:"):
                    dataset_id = line.split(":", 1)[1].strip()
                elif line.startswith("User ID:"):
                    user_id = line.split(":", 1)[1].strip()

            q_lower = human_text.lower()
            tool_calls = []
            call_id = 1

            # 1. Core financial metrics
            tool_calls.append({
                "name": "calculate_business_metrics",
                "args": {"dataset_id": dataset_id, "user_id": user_id},
                "id": f"call_{call_id}",
                "type": "tool_call",
            })
            call_id += 1

            # 2. Product performance
            tool_calls.append({
                "name": "analyze_product_performance",
                "args": {"dataset_id": dataset_id, "user_id": user_id, "top_n": 5},
                "id": f"call_{call_id}",
                "type": "tool_call",
            })
            call_id += 1

            # 3. Monthly trends
            tool_calls.append({
                "name": "analyze_time_trends",
                "args": {"dataset_id": dataset_id, "user_id": user_id, "period": "monthly"},
                "id": f"call_{call_id}",
                "type": "tool_call",
            })
            call_id += 1

            # 4. Segment comparisons
            tool_calls.append({
                "name": "compare_business_segments",
                "args": {"dataset_id": dataset_id, "user_id": user_id, "segment_column": "auto"},
                "id": f"call_{call_id}",
                "type": "tool_call",
            })
            call_id += 1

            # 5. Relationship correlation (if indicated or general)
            if any(k in q_lower for k in ["relation", "correlation", "driver", "impact"]):
                tool_calls.append({
                    "name": "analyze_relationships",
                    "args": {"dataset_id": dataset_id, "user_id": user_id},
                    "id": f"call_{call_id}",
                    "type": "tool_call",
                })
                call_id += 1

            # 6. Profile if requested
            if any(k in q_lower for k in ["profile", "schema", "column", "count", "record", "overview"]):
                tool_calls.append({
                    "name": "get_dataset_profile",
                    "args": {"dataset_id": dataset_id, "user_id": user_id},
                    "id": f"call_{call_id}",
                    "type": "tool_call",
                })
                call_id += 1

            return ChatResult(generations=[ChatGeneration(message=AIMessage(content="", tool_calls=tool_calls))])

        # Turn 2: Synthesize findings from real tool execution results
        tool_results_map: Dict[str, Any] = {}
        for tm in tool_messages:
            tool_name = getattr(tm, "name", None) or "unknown"
            try:
                tool_results_map[tool_name] = json.loads(tm.content) if isinstance(tm.content, str) else tm.content
            except (TypeError, ValueError):
                tool_results_map[tool_name] = tm.content

        metrics = tool_results_map.get("calculate_business_metrics", {})
        if not isinstance(metrics, dict):
            metrics = {}
        rev = metrics.get("total_revenue", 0.0)
        exp = metrics.get("total_expenses", 0.0)
        prof = metrics.get("total_profit", 0.0)
        margin = metrics.get("profit_margin_pct", 0.0)

        synthesis = (
            f"Business recorded ₹{rev:,.2f} in total revenue and ₹{exp:,.2f} in expenses, "
            f"generating a net profit of ₹{prof:,.2f} ({margin:.2f}% operating margin)."
        )
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=synthesis))])

    def invoke(self, input: Any, config: Optional[Any] = None, **kwargs: Any) -> Any:
        messages = input if isinstance(input, list) else input.get("messages", [])
        return self._generate(messages).generations[0].message


def create_analytics_agent(
    gemini_api_key: Optional[str] = None,
    groq_api_key: Optional[str] = None,
) -> AnalyticsAgent:
    """Factory creating an AnalyticsAgent instance."""
    return AnalyticsAgent(gemini_api_key=gemini_api_key, groq_api_key=groq_api_key)