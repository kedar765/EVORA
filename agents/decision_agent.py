"""EVORA LLM-driven Decision Optimization Agent.

Design contract:
- Gemini/Groq generate the business reasoning and final recommendations.
- The six Decision tools return dataset evidence and perform calculations only.
- Python validates structure, evidence presence and numerical claims; it does not
  select a strategy or create rule-based recommendations.
- If both LLM providers fail, this agent raises an explicit error. It never
  substitutes a deterministic/rule-based decision.
- The legacy recommend() response keys are preserved.
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from dotenv import load_dotenv

from agents.config import (
    ModelQuotaManager,
    create_gemini_chat_model,
    create_groq_chat_model,
    get_decision_model,
    get_groq_model,
    resolve_active_gemini_model,
)
from schemas.agent_schemas import (
    DecisionAction,
    DecisionAgentOutput,
    DecisionLLMOutput,
    DecisionRecommendation,
    EvidenceItem,
    ScenarioSimulationResult,
)
from tools.decision_tools import DECISION_TOOLS, generate_action_plan

_ROOT_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _ROOT_DIR / ".env"
if _ENV_FILE.exists():
    load_dotenv(dotenv_path=_ENV_FILE, override=False)
else:
    load_dotenv(override=False)

logger = logging.getLogger("evora.decision_agent")


class DecisionLLMUnavailableError(RuntimeError):
    """Raised when no configured LLM provider can produce a decision."""


class DecisionOptimizationAgent:
    """Generate dynamic, evidence-backed decisions using Gemini or Groq."""

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        groq_api_key: Optional[str] = None,
        gemini_model: Optional[str] = None,
        groq_model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.gemini_api_key = (
            gemini_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        )
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.gemini_model = gemini_model or get_decision_model()
        self.groq_model = groq_model or get_groq_model()
        raw_timeout = timeout if timeout is not None else os.getenv("LLM_TIMEOUT", "15.0")
        try:
            self.timeout = float(raw_timeout)
        except (TypeError, ValueError):
            self.timeout = 15.0
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            self.timeout = 15.0

    # ------------------------------------------------------------------
    # Input normalization and safe parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _unwrap_context(value: Optional[Dict[str, Any]], keys: Tuple[str, ...]) -> Dict[str, Any]:
        if value is None:
            return {}
        if hasattr(value, "model_dump"):
            value = value.model_dump(mode="json")
        if not isinstance(value, dict):
            return {}
        for key in keys:
            nested = value.get(key)
            if isinstance(nested, dict):
                return nested
        return value

    @staticmethod
    def _as_bool(value: Any, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value != 0
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "y", "detected"}:
                return True
            if normalized in {"false", "0", "no", "n", "not detected", "none", ""}:
                return False
        return default

    @staticmethod
    def _json_safe(value: Any) -> Any:
        """Convert nested Pydantic/dataframe-like values into JSON-safe primitives."""
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if isinstance(value, dict):
            return {str(k): DecisionOptimizationAgent._json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [DecisionOptimizationAgent._json_safe(v) for v in value]
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        return str(value)

    @staticmethod
    def _parse_tool_payload(value: Any) -> Dict[str, Any]:
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, dict) else {"raw_result": parsed}
            except (json.JSONDecodeError, TypeError):
                return {"raw_result": value}
        return {}

    @staticmethod
    def _message_content(message: Any) -> str:
        content = getattr(message, "content", message)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            return "\n".join(parts)
        return str(content)

    @staticmethod
    def _extract_json_object(text: str) -> Dict[str, Any]:
        cleaned = (text or "").strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        start = cleaned.find("{")
        if start < 0:
            raise ValueError("LLM response did not contain a JSON object.")
        decoder = json.JSONDecoder()
        parsed, _ = decoder.raw_decode(cleaned[start:])
        if not isinstance(parsed, dict):
            raise ValueError("LLM response JSON must be an object.")
        return parsed

    # ------------------------------------------------------------------
    # Provider management: Gemini -> Groq. There is intentionally no
    # deterministic recommendation fallback.
    # ------------------------------------------------------------------

    def _llm_candidates(self) -> Tuple[List[Tuple[Any, str, str]], List[str]]:
        if os.getenv("EVORA_SKIP_EXTERNAL_LLM", "0") == "1":
            return [], ["External LLM execution is disabled by EVORA_SKIP_EXTERNAL_LLM=1."]

        candidates: List[Tuple[Any, str, str]] = []
        errors: List[str] = []
        active_gemini = resolve_active_gemini_model(self.gemini_model)
        exhausted, reason = ModelQuotaManager.is_exhausted(active_gemini)

        if self.gemini_api_key and not exhausted:
            try:
                gemini = create_gemini_chat_model(
                    model_name=active_gemini,
                    api_key=self.gemini_api_key,
                    timeout=self.timeout,
                )
                candidates.append((gemini, "llm", active_gemini))
            except Exception as exc:
                errors.append(f"Gemini initialization failed: {exc}")
                logger.warning("Could not initialize Gemini Decision model: %s", exc)
                if ModelQuotaManager.is_quota_error(exc):
                    ModelQuotaManager.mark_exhausted(active_gemini, str(exc))
        elif exhausted:
            errors.append(reason or f"Gemini model {active_gemini} is quota-exhausted.")
        else:
            errors.append("Gemini API key is not configured.")

        if self.groq_api_key:
            try:
                groq = create_groq_chat_model(
                    model_name=self.groq_model,
                    api_key=self.groq_api_key,
                    temperature=0.1,
                    timeout=self.timeout,
                )
                candidates.append((groq, "groq_fallback", self.groq_model))
            except Exception as exc:
                errors.append(f"Groq initialization failed: {exc}")
                logger.warning("Could not initialize Groq Decision model: %s", exc)
        else:
            errors.append("Groq API key is not configured.")
        return candidates, errors

    def _resolve_llm_with_metadata(self) -> Tuple[Any, str, str, Optional[str]]:
        """Compatibility wrapper for existing callers; never returns a rules model."""
        candidates, errors = self._llm_candidates()
        if candidates:
            model, mode, model_name = candidates[0]
            return model, mode, model_name, "; ".join(errors) or None
        return None, "unavailable", "unavailable", "; ".join(errors)

    def get_llm(self) -> Any:
        model, _, _, error = self._resolve_llm_with_metadata()
        if model is None:
            raise DecisionLLMUnavailableError(error or "No Decision LLM provider is available.")
        return model

    # ------------------------------------------------------------------
    # LangChain tool-use phase. Tools only gather data/calculate values;
    # the final strategic recommendations are generated in a separate LLM call.
    # ------------------------------------------------------------------

    def build_langchain_agent(self, llm: Optional[Any] = None) -> Any:
        from langchain.agents import create_agent

        system_prompt = (
            "You are EVORA's Decision Evidence Analyst. You do NOT author the final "
            "recommendations in this phase. Use the six available Decision tools to "
            "retrieve dataset-grounded facts and calculate LLM-proposed scenarios. "
            "Call the legacy generate_action_plan tool only as an evidence-profile tool: "
            "it returns observations, not a plan. Propose strategy/options dynamically "
            "from the supplied Analytics and Risk context when calling compare_business_strategies "
            "or evaluate_decision_options; do not reuse a fixed template. Use estimate_financial_impact "
            "only when its required percentage/assumptions are supported by the context. "
            "Do not invent numbers, ROI scores, risk scores, feasibility scores, or cost ratios. "
            "Explain missing data through tool results. Final business decisions belong to a human."
        )
        model = llm or self.get_llm()
        return create_agent(model=model, tools=DECISION_TOOLS, system_prompt=system_prompt)

    def _tool_results_from_agent(self, result: Any) -> Dict[str, Any]:
        from langchain_core.messages import ToolMessage

        messages = result.get("messages", []) if isinstance(result, dict) else []
        tool_results: Dict[str, Any] = {}
        for message in messages:
            if isinstance(message, ToolMessage):
                name = getattr(message, "name", None) or "unknown"
                payload = self._parse_tool_payload(self._message_content(message))
                if name in tool_results:
                    existing = tool_results[name]
                    if not isinstance(existing, list):
                        existing = [existing]
                    existing.append(payload)
                    tool_results[name] = existing
                else:
                    tool_results[name] = payload
        return tool_results

    def _ensure_dataset_evidence(
        self,
        tool_results: Dict[str, Any],
        dataset_id: str,
        user_id: str,
        risk_level: str,
    ) -> Dict[str, Any]:
        """Ensure a base facts profile exists; this is data collection, not decision logic."""
        existing = tool_results.get("generate_action_plan")
        if isinstance(existing, dict) and not existing.get("error"):
            return tool_results
        try:
            raw = generate_action_plan.invoke({
                "dataset_id": dataset_id,
                "user_id": user_id,
                "risk_level": risk_level,
                "priority_focus": "LLM determines focus from evidence",
            })
            tool_results["generate_action_plan"] = self._parse_tool_payload(raw)
        except Exception as exc:
            logger.warning("Could not collect base Decision evidence: %s", exc)
            tool_results["generate_action_plan"] = {"error": str(exc)}
        return tool_results

    # ------------------------------------------------------------------
    # Structured LLM synthesis
    # ------------------------------------------------------------------

    def _invoke_decision_llm(self, llm: Any, messages: Sequence[Any]) -> DecisionLLMOutput:
        """Get a validated structured response from the actual LLM."""
        structured_error: Optional[Exception] = None
        if hasattr(llm, "with_structured_output"):
            try:
                structured = llm.with_structured_output(DecisionLLMOutput)
                result = structured.invoke(list(messages))
                if isinstance(result, DecisionLLMOutput):
                    return result
                if isinstance(result, dict):
                    return DecisionLLMOutput.model_validate(result)
                if hasattr(result, "model_dump"):
                    return DecisionLLMOutput.model_validate(result.model_dump())
                structured_error = TypeError("Structured LLM response had an unsupported type.")
            except Exception as exc:
                structured_error = exc
                logger.warning("Structured Decision output failed; retrying JSON mode: %s", exc)

        # Still an LLM response, not a deterministic fallback.
        try:
            from langchain_core.messages import SystemMessage
            json_messages = [
                SystemMessage(content=(
                    "Return only one valid JSON object matching the DecisionLLMOutput schema. "
                    "Do not add markdown fences or prose outside the JSON."
                )),
                *list(messages),
            ]
            raw = llm.invoke(json_messages)
            parsed = self._extract_json_object(self._message_content(raw))
            return DecisionLLMOutput.model_validate(parsed)
        except Exception as raw_exc:
            if structured_error:
                raise RuntimeError(
                    f"Structured response failed ({structured_error}); JSON response failed ({raw_exc})."
                ) from raw_exc
            raise

    @staticmethod
    def _numeric_values(value: Any) -> List[float]:
        found: List[float] = []
        if isinstance(value, dict):
            for item in value.values():
                found.extend(DecisionOptimizationAgent._numeric_values(item))
        elif isinstance(value, (list, tuple)):
            for item in value:
                found.extend(DecisionOptimizationAgent._numeric_values(item))
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            number = float(value)
            if math.isfinite(number):
                found.append(number)
        return found

    @staticmethod
    def _deduplicate_recommendations(
        recommendations: List[DecisionRecommendation],
        verified_numbers: List[float],
    ) -> List[DecisionRecommendation]:
        """Reject duplicates and remove unsupported quantified impact amounts."""
        unique: List[DecisionRecommendation] = []
        fingerprints: List[str] = []
        for item in recommendations:
            fingerprint = re.sub(r"\W+", " ", f"{item.title} {item.recommendation}".lower()).strip()
            if not fingerprint or not item.title.strip() or not item.recommendation.strip():
                continue
            if not item.reasoning.strip():
                continue
            evidence_items = [
                evidence for evidence in item.supporting_evidence
                if isinstance(evidence.description, str) and evidence.description.strip()
            ]
            if not evidence_items:
                # No evidence attached means this is not an acceptable EVORA recommendation.
                continue
            if any(SequenceMatcher(None, fingerprint, old).ratio() >= 0.88 for old in fingerprints):
                continue

            rec_id = item.recommendation_id or f"REC-{len(unique) + 1:02d}"
            risk_desc = item.associated_risk or item.risks_and_tradeoffs
            update_fields: Dict[str, Any] = {
                "recommendation_id": rec_id,
                "supporting_evidence": evidence_items,
                "associated_risk": risk_desc,
                "risks_and_tradeoffs": risk_desc,
            }

            # An estimated financial amount is only retained if it matches a value
            # returned in the supplied context/tool evidence (within rounding tolerance).
            impact = item.estimated_financial_impact
            if impact is not None:
                has_match = bool(verified_numbers) and any(
                    abs(abs(impact) - abs(value)) <= max(1.0, abs(value) * 0.005)
                    for value in verified_numbers
                )
                if not has_match:
                    update_fields["estimated_financial_impact"] = None
                    update_fields["expected_impact"] = (
                        (item.expected_impact + " ") if item.expected_impact else ""
                    ) + "A quantified financial impact was omitted because it could not be matched to a tool-verified value."

            item = item.model_copy(update=update_fields)
            unique.append(item)
            fingerprints.append(fingerprint)
            if len(unique) >= 8:
                break
        return unique

    def _synthesis_messages(
        self,
        analytics_context: Dict[str, Any],
        risk_context: Dict[str, Any],
        user_query: str,
        tool_results: Dict[str, Any],
    ) -> List[Any]:
        from langchain_core.messages import HumanMessage, SystemMessage

        evidence_bundle = {
            "analytics": self._json_safe(analytics_context),
            "risk": self._json_safe(risk_context),
            "decision_tool_results": self._json_safe(tool_results),
        }
        system = SystemMessage(content=(
            "You are EVORA's senior business decision strategist. You must independently reason "
            "over the supplied Analytics, Risk and Decision-tool evidence and generate the final "
            "business recommendations yourself. Do not copy a fixed action-plan template, do not "
            "repeat the same generic advice across datasets, and do not let Python rules choose "
            "the strategy or priorities.\n\n"
            "Generate 3 to 5 distinct, useful recommendations when the evidence supports them. "
            "Return fewer only when the evidence genuinely supports fewer; never invent extra items "
            "just to reach a count. Every recommendation must contain:\n"
            "- recommendation_id: Unique string identifier (e.g. 'REC-01')\n"
            "- title: Clear executive headline\n"
            "- recommendation: Specific, actionable business decision\n"
            "- reasoning: Strategic explanation derived from Analytics and Risk metrics\n"
            "- supporting_evidence: List of EvidenceItem objects linking to metrics or tool evidence\n"
            "- priority: Critical, high, medium, or low\n"
            "- category: Strategic category (e.g. Cost Optimization, Revenue Expansion, Risk Mitigation)\n"
            "- expected_impact: Qualitative business benefit\n"
            "- estimated_financial_impact: Validated float amount ONLY if verified by context/tools, else null\n"
            "- implementation_steps: Array of concrete operational steps\n"
            "- associated_risk: Key risks, trade-offs, and governance caveats\n"
            "- assumptions: Explicit operational assumptions\n\n"
            "Use only facts in the provided evidence. Never fabricate figures, ROI, risk scores, "
            "feasibility scores, or financial savings. Set estimated_financial_impact to null unless "
            "the exact amount is explicitly supported by Analytics or a Decision tool. Distinguish "
            "historical facts from scenario projections and assumptions. Do not claim that a "
            "simulation is guaranteed. If evidence is insufficient, return analysis_status="
            "'insufficient_evidence', an empty recommendations list, and explain what is missing.\n\n"
            "Decide overall_priority and recommended_strategy through your own reasoning from the "
            "evidence; do not apply a hard-coded risk-level-to-priority mapping. The user query may "
            "change the focus. Keep recommendations meaningfully different rather than restating "
            "one action in several ways. Human executive approval is mandatory before execution."
        ))
        human = HumanMessage(content=(
            f"User request: {user_query or 'Analyze the business and propose the most valuable decisions.'}\n\n"
            "Evidence bundle (treat this as the source of truth; do not invent missing fields):\n"
            + json.dumps(evidence_bundle, ensure_ascii=False, default=str)
            + "\n\nReturn the structured DecisionLLMOutput now."
        ))
        return [system, human]

    # ------------------------------------------------------------------
    # Legacy API: same response keys, but recommendation content is LLM-authored.
    # ------------------------------------------------------------------

    def recommend(
        self,
        analytics: Optional[Dict[str, Any]] = None,
        risk: Optional[Dict[str, Any]] = None,
        scenario: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        analytics_data = self._unwrap_context(analytics, ("analysis", "analytics", "data"))
        risk_data = self._unwrap_context(risk, ("risk_analysis", "risk", "data"))
        scenario_data = self._unwrap_context(scenario, ("scenario", "what_if", "result"))
        context = {
            "analytics": self._json_safe(analytics_data),
            "risk": self._json_safe(risk_data),
            "scenario": self._json_safe(scenario_data),
        }
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=(
                "You are EVORA's business Decision LLM. Generate several distinct, dataset-specific "
                "recommendations only from the provided evidence. Do not use fixed templates or "
                "rule-based mappings. Provide 3-5 when evidence supports them, fewer when it does not. "
                "Every recommendation needs reasoning and supporting evidence. Do not invent financial "
                "amounts. If evidence is insufficient, return no recommendations and explain why. "
                "Return a structured DecisionLLMOutput."
            )),
            HumanMessage(content=json.dumps(context, ensure_ascii=False, default=str)),
        ]
        candidates, init_errors = self._llm_candidates()
        if not candidates:
            raise DecisionLLMUnavailableError("; ".join(init_errors) or "No LLM provider is available.")

        errors = list(init_errors)
        decision: Optional[DecisionLLMOutput] = None
        used_mode = "llm"
        used_model = ""
        for llm, mode, model_name in candidates:
            try:
                decision = self._invoke_decision_llm(llm, messages)
                used_mode, used_model = mode, model_name
                break
            except Exception as exc:
                errors.append(f"{model_name} decision generation failed: {exc}")
                logger.warning("Decision generation failed with %s: %s", model_name, exc)
                if mode == "llm" and ModelQuotaManager.is_quota_error(exc):
                    ModelQuotaManager.mark_exhausted(model_name, str(exc))
        if decision is None:
            raise DecisionLLMUnavailableError("No LLM generated a valid decision: " + "; ".join(errors))

        recommendations = self._deduplicate_recommendations(
            decision.recommendations,
            self._numeric_values(context),
        )
        action_plan = [
            {
                "action": item.recommendation,
                "reason": item.reasoning,
                "expected_benefit": item.expected_impact or "Not quantified from the supplied evidence.",
                "risk": item.associated_risk or item.risks_and_tradeoffs or "Review implementation risks before execution.",
                "priority": item.priority,
            }
            for item in recommendations
        ]
        evidence = [
            evidence_item.description
            for recommendation in recommendations
            for evidence_item in recommendation.supporting_evidence
            if evidence_item.description.strip()
        ]
        raw_risk_level = str(risk_data.get("risk_level", "unknown")).strip().upper()
        risk_score = risk_data.get("risk_score")
        return {
            "question_addressed": "What should we do?",
            "priority": decision.overall_priority.upper(),
            "recommended_strategy": decision.recommended_strategy or "No strategy selected by the LLM",
            "alternative_strategies": decision.alternative_strategies or [],
            "risk_context": {
                "risk_level": raw_risk_level,
                "risk_score": risk_score,
                "anomaly_detected": self._as_bool(risk_data.get("anomaly_detected"), False),
            },
            "evidence": list(dict.fromkeys(evidence)),
            "recommendations": [item.recommendation for item in recommendations],
            "structured_recommendations": [item.model_dump(mode="json") for item in recommendations],
            "action_plan": action_plan,
            "assumptions": decision.assumptions or [],
            "expected_outcome": decision.expected_outcome or "",
            "decision_disclaimer": (
                "EVORA provides LLM-generated decision-support options. "
                "The final decision and execution remain with the human user."
            ),
        }

    # ------------------------------------------------------------------
    # Main multi-agent interface
    # ------------------------------------------------------------------

    def run_agent(
        self,
        dataset_id: str,
        user_id: str,
        analytics_context: Optional[Dict[str, Any]] = None,
        risk_context: Optional[Dict[str, Any]] = None,
        user_query: str = "",
    ) -> DecisionAgentOutput:
        analytics_ctx = self._unwrap_context(analytics_context, ("analysis", "analytics", "data"))
        risk_ctx = self._unwrap_context(risk_context, ("risk_analysis", "risk", "data"))
        risk_level = str(risk_ctx.get("risk_level", "unknown")).strip().lower()

        # Only compact aggregated context is sent to external LLM providers.
        decision_context = {
            "total_revenue": analytics_ctx.get("total_revenue"),
            "total_expense": analytics_ctx.get("total_expense", analytics_ctx.get("total_expenses")),
            "total_profit": analytics_ctx.get("total_profit"),
            "profit_margin": analytics_ctx.get("profit_margin"),
            "analytics_key_findings": analytics_ctx.get("key_findings", []),
            "analytics_evidence": analytics_ctx.get("evidence", []),
            "risk_level": risk_level,
            "risk_score": risk_ctx.get("risk_score"),
            "anomaly_detected": self._as_bool(risk_ctx.get("anomaly_detected"), False),
            "risk_findings": risk_ctx.get("findings", []),
            "risk_key_risks": risk_ctx.get("key_risks", []),
            "risk_evidence": risk_ctx.get("evidence", []),
        }
        planner_prompt = (
            f"Dataset ID: {dataset_id}\nUser ID: {user_id}\n"
            f"Aggregated context: {json.dumps(self._json_safe(decision_context), ensure_ascii=False, default=str)}\n"
            f"User question: {user_query or 'Analyze the dataset and gather evidence for strategic decisions.'}\n\n"
            "Gather factual evidence with the available Decision tools. Call the evidence-profile tool. "
            "When useful, propose scenario options dynamically from the supplied findings and have the "
            "tools calculate them. Do not use fixed option templates or make the final decision in this phase."
        )
        from langchain_core.messages import HumanMessage

        candidates, init_errors = self._llm_candidates()
        if not candidates:
            raise DecisionLLMUnavailableError(
                "; ".join(init_errors) or "No Decision LLM provider is configured."
            )

        errors = list(init_errors)
        last_error: Optional[Exception] = None
        for llm, execution_mode, model_used in candidates:
            try:
                # Phase 1: LLM chooses which evidence/calculation tools to call.
                agent = self.build_langchain_agent(llm=llm)
                tool_agent_result = agent.invoke({"messages": [HumanMessage(content=planner_prompt)]})
                tool_results = self._tool_results_from_agent(tool_agent_result)
                tool_results = self._ensure_dataset_evidence(
                    tool_results, dataset_id, user_id, risk_level
                )

                # Phase 2: the same provider authors the final structured recommendations.
                synthesis_messages = self._synthesis_messages(
                    analytics_ctx, risk_ctx, user_query, tool_results
                )
                decision = self._invoke_decision_llm(llm, synthesis_messages)

                verified_numbers = self._numeric_values({
                    "analytics": decision_context,
                    "tools": tool_results,
                })
                recommendations = self._deduplicate_recommendations(
                    decision.recommendations, verified_numbers
                )

                scenarios: List[ScenarioSimulationResult] = []
                for tool_name in ("compare_business_strategies", "evaluate_decision_options"):
                    payloads = tool_results.get(tool_name, [])
                    if isinstance(payloads, dict):
                        payloads = [payloads]
                    for payload in payloads if isinstance(payloads, list) else []:
                        if not isinstance(payload, dict) or payload.get("error"):
                            continue
                        strategy_items = payload.get("strategies") or payload.get("evaluated_options") or []
                        for item in strategy_items if isinstance(strategy_items, list) else []:
                            if not isinstance(item, dict):
                                continue
                            name = str(item.get("strategy_name") or item.get("name") or "").strip()
                            values = [
                                item.get("projected_revenue"),
                                item.get("projected_expenses"),
                                item.get("projected_profit"),
                                item.get("profit_delta"),
                            ]
                            try:
                                converted = [float(value) for value in values]
                                if not name or not all(math.isfinite(value) for value in converted):
                                    continue
                                scenarios.append(ScenarioSimulationResult(
                                    scenario_name=name,
                                    projected_revenue=converted[0],
                                    projected_expenses=converted[1],
                                    projected_profit=converted[2],
                                    profit_delta=converted[3],
                                    notes=json.dumps(item.get("assumptions_and_limitations", []), ensure_ascii=False),
                                ))
                            except (TypeError, ValueError, OverflowError):
                                continue

                # `actions` is a compatibility projection of LLM recommendations.
                # No Python rule creates or prioritizes an action.
                actions = [
                    DecisionAction(
                        action=item.recommendation,
                        priority=item.priority,
                        expected_impact=item.expected_impact,
                        estimated_financial_impact=item.estimated_financial_impact,
                        reason=item.reasoning,
                        risk=item.associated_risk or item.risks_and_tradeoffs,
                    )
                    for item in recommendations
                ]
                assumptions = list(decision.assumptions)
                for tool_name, payload in tool_results.items():
                    payload_list = payload if isinstance(payload, list) else [payload]
                    for result in payload_list:
                        if not isinstance(result, dict):
                            continue
                        limitations = result.get("limitations") or result.get("assumptions_and_limitations") or []
                        if isinstance(limitations, str):
                            limitations = [limitations]
                        if isinstance(limitations, list):
                            for limitation in limitations:
                                if isinstance(limitation, str) and limitation.strip():
                                    note = f"{tool_name}: {limitation.strip()}"
                                    if note not in assumptions:
                                        assumptions.append(note)

                status = decision.analysis_status
                if status == "completed" and not recommendations:
                    status = "insufficient_evidence"
                summary = decision.summary.strip() or (
                    "The Decision LLM did not find enough validated evidence to provide recommendations."
                    if status == "insufficient_evidence"
                    else f"The Decision LLM generated {len(recommendations)} evidence-backed recommendations."
                )
                return DecisionAgentOutput(
                    analysis_status=status,
                    overall_priority=decision.overall_priority,
                    recommended_strategy=decision.recommended_strategy or "No strategy selected by the LLM",
                    alternative_strategies=decision.alternative_strategies,
                    recommendations=recommendations,
                    actions=actions,
                    scenarios=scenarios,
                    expected_outcome=decision.expected_outcome,
                    assumptions=assumptions,
                    human_approval_required=True,
                    summary=summary,
                    model_used=model_used,
                    execution_mode=execution_mode,
                    model_error="; ".join(errors) or None,
                    insufficient_evidence_reason=decision.insufficient_evidence_reason,
                )
            except Exception as exc:
                last_error = exc
                errors.append(f"{model_used} Decision workflow failed: {exc}")
                logger.exception("Decision workflow failed using %s", model_used)
                if execution_mode == "llm" and ModelQuotaManager.is_quota_error(exc):
                    ModelQuotaManager.mark_exhausted(model_used, str(exc))
                # Continue to Groq if it was initialized. Never switch to rules.

        raise DecisionLLMUnavailableError(
            "No LLM provider completed the Decision workflow. " + "; ".join(errors)
        ) from last_error


def create_decision_agent(
    gemini_api_key: Optional[str] = None,
    groq_api_key: Optional[str] = None,
) -> DecisionOptimizationAgent:
    """Factory for the EVORA LLM-driven Decision Optimization Agent."""
    return DecisionOptimizationAgent(
        gemini_api_key=gemini_api_key,
        groq_api_key=groq_api_key,
    )
