"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  BrainCircuit,
  ArrowRight,
  ShieldCheck,
  Loader2,
  AlertCircle,
  Lightbulb,
  Target,
  ClipboardList,
  CheckCircle2,
  TrendingUp,
  AlertTriangle,
  Sparkles,
  Info,
} from "lucide-react";

import { useDashboard } from "@/components/dashboard/DashboardContext";
import WhatIfAnalysis from "@/components/dashboard/WhatIfAnalysis";

import {
  api,
  type DecisionRecommendationResponse,
  type DecisionRecommendationItem,
} from "@/lib/api";

import type { WhatIfResult } from "@/components/dashboard/types";

export default function DecisionSupportPage() {
  const { uploadResult, setDecisionResult } = useDashboard();

  const currentMetrics = uploadResult?.metrics || null;
  const hasData = !!uploadResult;

  const [scenario, setScenario] = useState<WhatIfResult | null>(null);
  const [decision, setDecision] =
    useState<DecisionRecommendationResponse["decision"] | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleGenerateDecision = async () => {
    if (!uploadResult) {
      setError("Please upload a business dataset first.");
      return;
    }

    setLoading(true);
    setError("");
    setDecision(null);

    try {
      const response = await api.getDecisionRecommendations({
        analytics: {
          total_revenue: currentMetrics?.total_revenue,
          total_expense: currentMetrics?.total_expense,
          total_profit: currentMetrics?.total_profit,
          profit_margin: currentMetrics?.profit_margin,
        },

        risk: {
          risk_level:
            uploadResult.risk_analysis?.risk_level ||
            uploadResult.risk_level ||
            "LOW",

          risk_score:
            uploadResult.risk_analysis?.risk_score ??
            uploadResult.risk_score ??
            0,

          anomaly_detected:
            uploadResult.risk_analysis?.anomaly_detected ??
            uploadResult.anomaly_detected ??
            false,
        },

        scenario: scenario
          ? {
              current_predicted_profit: scenario.current_predicted_profit,
              new_predicted_profit: scenario.new_predicted_profit,
              profit_difference: scenario.profit_difference,
              result: scenario.result,
            }
          : undefined,
      });

      if (!response.success || !response.decision) {
        throw new Error("Unable to generate recommendations.");
      }

      setDecision(response.decision);
      setDecisionResult(response.decision);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong. Please check your connection or AI provider status."
      );
    } finally {
      setLoading(false);
    }
  };

  const priorityStyle: Record<string, string> = {
    CRITICAL: "bg-red-50 text-red-700 border-red-200",
    critical: "bg-red-50 text-red-700 border-red-200",
    HIGH: "bg-orange-50 text-orange-700 border-orange-200",
    high: "bg-orange-50 text-orange-700 border-orange-200",
    MEDIUM: "bg-amber-50 text-amber-700 border-amber-200",
    medium: "bg-amber-50 text-amber-700 border-amber-200",
    LOW: "bg-emerald-50 text-emerald-700 border-emerald-200",
    low: "bg-emerald-50 text-emerald-700 border-emerald-200",
  };

  const priorityBadgeText = (p: string) => {
    const norm = (p || "MEDIUM").toUpperCase();
    return norm;
  };

  const normalizePriority = (
    p?: string
  ): DecisionRecommendationItem["priority"] => {
    const norm = (p || "MEDIUM").toUpperCase();
    if (norm === "CRITICAL" || norm === "HIGH" || norm === "LOW") {
      return norm;
    }
    return "MEDIUM";
  };

  // Normalize recommendations into rich individual cards
  const recommendationCards: DecisionRecommendationItem[] = React.useMemo(() => {
    if (!decision) return [];
    if (decision.structured_recommendations && decision.structured_recommendations.length > 0) {
      return decision.structured_recommendations;
    }
    // Fallback normalization from action_plan and recommendations
    if (decision.action_plan && decision.action_plan.length > 0) {
      return decision.action_plan.map((act, idx) => ({
        recommendation_id: `REC-${String(idx + 1).padStart(2, "0")}`,
        title: act.action.length > 60 ? `${act.action.slice(0, 57)}...` : act.action,
        recommendation: act.action,
        reasoning: act.reason || "Reasoned by EVORA decision agent from current operational context.",
        priority: normalizePriority(act.priority || decision.priority),
        category: "Strategic Execution",
        expected_impact: act.expected_benefit,
        estimated_financial_impact: act.estimated_financial_impact ?? null,
        implementation_steps: [act.action],
        associated_risk: act.risk || "Review implementation trade-offs prior to authorization.",
        supporting_evidence: decision.evidence?.map((e) => ({ description: e })) || [],
      }));
    }
    if (decision.recommendations && decision.recommendations.length > 0) {
      return decision.recommendations.map((rec, idx) => ({
        recommendation_id: `REC-${String(idx + 1).padStart(2, "0")}`,
        title: rec.length > 60 ? `${rec.slice(0, 57)}...` : rec,
        recommendation: rec,
        reasoning: "Generated by EVORA multi-agent decision reasoning engine.",
        priority: normalizePriority(decision.priority),
        category: "Operational Improvement",
        implementation_steps: [rec],
        associated_risk: "Ensure human executive authorization before deploying changes.",
        supporting_evidence: decision.evidence?.map((e) => ({ description: e })) || [],
      }));
    }
    return [];
  }, [decision]);

  return (
    <div className="space-y-6 max-w-5xl pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
            Decision Support & Optimization
          </h1>

          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Synthesizes business analytics, ML risk analysis, and what-if simulation to generate
            evidence-backed strategic recommendations powered by enterprise LLM reasoning.
          </p>
        </div>

        <Link
          href="/dashboard/predictions"
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold border border-indigo-200 transition-colors"
        >
          <BrainCircuit className="w-3.5 h-3.5" />
          View ML Predictions
        </Link>
      </div>

      {!hasData && (
        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-sm">
          <p className="font-semibold text-slate-800">No Business Dataset Loaded</p>

          <p className="text-xs text-slate-500 mt-1">
            Upload a dataset from the Dashboard before generating business recommendations.
          </p>

          <Link
            href="/dashboard"
            className="inline-flex items-center gap-1 mt-3 text-blue-600 text-xs font-semibold"
          >
            Go to Dashboard
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}

      {/* What-If Scenario Section */}
      <section>
        <WhatIfAnalysis currentMetrics={currentMetrics} onResult={setScenario} />
      </section>

      {/* Generator Action Section */}
      <section className="bg-white border border-slate-200 rounded-xl p-5 sm:p-6 space-y-4 shadow-sm">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <div className="flex items-center gap-2">
              <Target className="w-5 h-5 text-indigo-600" />
              <h2 className="text-lg font-bold text-slate-900">AI Strategic Decision Generator</h2>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Runs deep LLM reasoning over analytics facts, anomaly signals, and scenario projections.
            </p>
          </div>

          <button
            onClick={handleGenerateDecision}
            disabled={!hasData || loading}
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Reasoning Recommendations...
              </>
            ) : (
              <>
                <Lightbulb className="w-4 h-4" />
                Generate Strategic Recommendations
              </>
            )}
          </button>
        </div>

        {scenario && (
          <div className="rounded-lg bg-indigo-50 border border-indigo-100 p-3 text-sm flex items-center justify-between flex-wrap gap-2">
            <div>
              <p className="font-semibold text-indigo-900">What-If Simulation Connected</p>
              <p className="text-xs text-indigo-700 mt-0.5">
                Target scenario delta: ₹{scenario.profit_difference.toLocaleString("en-IN")} (
                {scenario.profit_difference >= 0 ? "+Profit" : "-Profit"})
              </p>
            </div>
            <span className="text-xs px-2.5 py-1 rounded-full bg-indigo-100 text-indigo-800 font-semibold">
              Live Scenario
            </span>
          </div>
        )}

        {error && (
          <div className="flex items-start gap-2.5 p-3.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Generation Notice</p>
              <p className="mt-0.5">{error}</p>
            </div>
          </div>
        )}
      </section>

      {/* Decision Results Presentation */}
      {decision && (
        <section className="space-y-6">
          {/* Executive Strategy Overview Card */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 sm:p-6 shadow-sm space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-indigo-600" />
                  <span className="text-xs font-semibold uppercase tracking-wider text-indigo-600">
                    LLM Synthesis & Strategy
                  </span>
                </div>
                <h2 className="text-xl font-bold text-slate-900 mt-1">
                  {decision.recommended_strategy || "Business Decision Strategy"}
                </h2>
              </div>

              <span
                className={`px-3 py-1 rounded-full border text-xs font-bold ${
                  priorityStyle[decision.priority] || priorityStyle.MEDIUM
                }`}
              >
                {priorityBadgeText(decision.priority)} PRIORITY
              </span>
            </div>

            {decision.expected_outcome && (
              <p className="text-sm text-slate-700 bg-slate-50 border border-slate-100 rounded-lg p-3 leading-relaxed">
                <strong>Projected Executive Outcome:</strong> {decision.expected_outcome}
              </p>
            )}

            {/* Context Indicators */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
              <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-100">
                <p className="text-xs text-slate-500 font-medium">Risk Posture</p>
                <p className="font-bold text-slate-900 mt-1 uppercase text-sm">
                  {decision.risk_context.risk_level} Risk
                </p>
              </div>

              <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-100">
                <p className="text-xs text-slate-500 font-medium">Risk Score</p>
                <p className="font-bold text-slate-900 mt-1 text-sm">
                  {decision.risk_context.risk_score} / 100
                </p>
              </div>

              <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-100">
                <p className="text-xs text-slate-500 font-medium">Anomalies Detected</p>
                <p className="font-bold text-slate-900 mt-1 text-sm">
                  {decision.risk_context.anomaly_detected ? "Yes (Flagged)" : "None Detected"}
                </p>
              </div>
            </div>

            {/* Alternative Strategies */}
            {decision.alternative_strategies && decision.alternative_strategies.length > 0 && (
              <div className="pt-2">
                <p className="text-xs text-slate-500 font-semibold mb-2">Alternative Pathways Considered:</p>
                <div className="flex flex-wrap gap-2">
                  {decision.alternative_strategies.map((alt, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 text-xs font-medium border border-slate-200"
                    >
                      {alt}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Individual Recommendations Cards */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ClipboardList className="w-5 h-5 text-indigo-600" />
                <h3 className="text-lg font-bold text-slate-900">
                  Strategic Recommendations ({recommendationCards.length})
                </h3>
              </div>
              <span className="text-xs text-slate-500">
                Evidence-verified by EVORA Decision Engine
              </span>
            </div>

            {recommendationCards.length === 0 ? (
              <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-500 text-sm">
                No specific recommendations generated for this context.
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-5">
                {recommendationCards.map((rec, index) => {
                  const cardPriority = (rec.priority || "medium").toUpperCase();
                  const badgeStyle = priorityStyle[cardPriority] || priorityStyle.MEDIUM;

                  return (
                    <div
                      key={rec.recommendation_id || index}
                      className="bg-white border border-slate-200 rounded-xl p-5 sm:p-6 shadow-sm space-y-4 hover:border-slate-300 transition-all"
                    >
                      {/* Card Header */}
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded">
                              {rec.recommendation_id || `REC-${index + 1}`}
                            </span>
                            {rec.category && (
                              <span className="text-xs font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
                                {rec.category}
                              </span>
                            )}
                          </div>
                          <h4 className="text-base font-bold text-slate-900 mt-1">
                            {rec.title}
                          </h4>
                        </div>

                        <span className={`px-2.5 py-1 rounded-full border text-xs font-bold ${badgeStyle}`}>
                          {cardPriority} PRIORITY
                        </span>
                      </div>

                      {/* Main Recommendation Statement */}
                      <div className="p-3.5 rounded-lg bg-slate-50 border-l-4 border-indigo-500 text-sm text-slate-800 font-medium">
                        {rec.recommendation}
                      </div>

                      {/* Strategic Reasoning */}
                      <div className="space-y-1.5">
                        <p className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                          <Lightbulb className="w-3.5 h-3.5 text-amber-500" />
                          Strategic Reasoning & Context
                        </p>
                        <p className="text-xs sm:text-sm text-slate-600 leading-relaxed pl-5">
                          {rec.reasoning}
                        </p>
                      </div>

                      {/* Supporting Evidence */}
                      {rec.supporting_evidence && rec.supporting_evidence.length > 0 && (
                        <div className="space-y-1.5">
                          <p className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                            <BrainCircuit className="w-3.5 h-3.5 text-indigo-500" />
                            Supporting Evidence
                          </p>
                          <ul className="space-y-1 pl-5">
                            {rec.supporting_evidence.map((ev, evIdx) => (
                              <li key={evIdx} className="text-xs text-slate-600 flex items-start gap-1.5">
                                <span className="text-indigo-500 font-bold">•</span>
                                <span>
                                  {ev.description}
                                  {ev.metric && (
                                    <span className="ml-1 text-slate-400 font-mono text-[11px]">
                                      ({ev.metric}: {ev.value !== undefined ? String(ev.value) : "referenced"})
                                    </span>
                                  )}
                                </span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Financial Impact & Expected Benefit */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                        <div className="p-3 rounded-lg bg-emerald-50/70 border border-emerald-100 space-y-1">
                          <p className="text-xs font-semibold text-emerald-900 flex items-center gap-1.5">
                            <TrendingUp className="w-3.5 h-3.5 text-emerald-600" />
                            Expected Impact
                          </p>
                          <p className="text-xs text-emerald-800">
                            {rec.expected_impact || "Improves operational and financial margins."}
                          </p>
                          {rec.estimated_financial_impact !== null &&
                            rec.estimated_financial_impact !== undefined && (
                              <div className="mt-1.5 pt-1.5 border-t border-emerald-200 flex items-center justify-between text-xs">
                                <span className="text-emerald-700 font-medium">Validated Financial Impact:</span>
                                <span className="font-bold text-emerald-900">
                                  ₹{Number(rec.estimated_financial_impact).toLocaleString("en-IN", {
                                    maximumFractionDigits: 2,
                                  })}
                                </span>
                              </div>
                            )}
                        </div>

                        {/* Associated Risk */}
                        <div className="p-3 rounded-lg bg-amber-50/70 border border-amber-100 space-y-1">
                          <p className="text-xs font-semibold text-amber-900 flex items-center gap-1.5">
                            <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                            Associated Risk & Considerations
                          </p>
                          <p className="text-xs text-amber-800">
                            {rec.associated_risk ||
                              rec.risks_and_tradeoffs ||
                              "Review operational side effects prior to resource deployment."}
                          </p>
                        </div>
                      </div>

                      {/* Implementation Steps */}
                      {rec.implementation_steps && rec.implementation_steps.length > 0 && (
                        <div className="pt-2 border-t border-slate-100 space-y-2">
                          <p className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                            <CheckCircle2 className="w-3.5 h-3.5 text-blue-600" />
                            Implementation Steps
                          </p>
                          <div className="space-y-1.5 pl-2">
                            {rec.implementation_steps.map((step, sIdx) => (
                              <div key={sIdx} className="flex items-start gap-2 text-xs text-slate-600">
                                <span className="font-bold text-slate-400 min-w-[1.2rem]">
                                  {sIdx + 1}.
                                </span>
                                <span>{step}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Assumptions (if present) */}
                      {rec.assumptions && rec.assumptions.length > 0 && (
                        <div className="pt-1 flex items-center gap-1.5 text-[11px] text-slate-400">
                          <Info className="w-3 h-3 text-slate-400 shrink-0" />
                          <span>
                            <strong>Assumptions:</strong> {rec.assumptions.join("; ")}
                          </span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Governance & Human-in-the-Loop Safeguard */}
          <div className="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
            <ShieldCheck className="w-5 h-5 text-emerald-700 shrink-0 mt-0.5" />
            <div>
              <p className="text-xs font-bold text-emerald-900">
                Human-in-the-Loop Decision Governance
              </p>
              <p className="text-xs text-emerald-800 leading-relaxed mt-0.5">
                {decision.decision_disclaimer ||
                  "EVORA provides decision-support evidence. The final business decision, financial commitment, and execution remain exclusively under human executive authority."}
              </p>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
