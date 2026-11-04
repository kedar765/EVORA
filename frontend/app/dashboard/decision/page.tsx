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
} from "lucide-react";

import { useDashboard } from "@/components/dashboard/DashboardContext";
import WhatIfAnalysis from "@/components/dashboard/WhatIfAnalysis";

import {
  api,
  type DecisionRecommendationResponse,
} from "@/lib/api";

import type { WhatIfResult } from "@/components/dashboard/types";

export default function DecisionSupportPage() {
  const { uploadResult } = useDashboard();

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
              current_predicted_profit:
                scenario.current_predicted_profit,
              new_predicted_profit:
                scenario.new_predicted_profit,
              profit_difference:
                scenario.profit_difference,
              result: scenario.result,
            }
          : undefined,
      });

      if (!response.success) {
        throw new Error("Unable to generate recommendations.");
      }

      setDecision(response.decision);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  const priorityStyle = {
    HIGH: "bg-red-50 text-red-700 border-red-200",
    MEDIUM: "bg-amber-50 text-amber-700 border-amber-200",
    LOW: "bg-emerald-50 text-emerald-700 border-emerald-200",
  };

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
            Decision Support
          </h1>

          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Generate evidence-based business recommendations using
            analytics, risk analysis and what-if scenarios.
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
          <p className="font-semibold text-slate-800">
            No Business Dataset Loaded
          </p>

          <p className="text-xs text-slate-500 mt-1">
            Upload a dataset from the Dashboard before generating
            business recommendations.
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

      <section>
        <WhatIfAnalysis
          currentMetrics={currentMetrics}
          onResult={setScenario}
        />
      </section>

      <section className="bg-white border border-slate-200 rounded-xl p-5 sm:p-6 space-y-4">
        <div>
          <div className="flex items-center gap-2">
            <Target className="w-5 h-5 text-indigo-600" />

            <h2 className="text-lg font-bold text-slate-900">
              AI Decision Recommendations
            </h2>
          </div>

          <p className="text-xs text-slate-500 mt-1">
            Analyze business performance and generate an actionable
            decision-support plan.
          </p>
        </div>

        {scenario && (
          <div className="rounded-lg bg-indigo-50 border border-indigo-100 p-3 text-sm">
            <p className="font-semibold text-indigo-900">
              What-if scenario connected
            </p>

            <p className="text-xs text-indigo-700 mt-1">
              Predicted profit difference: ₹
              {scenario.profit_difference.toLocaleString("en-IN")}
            </p>
          </div>
        )}

        <button
          onClick={handleGenerateDecision}
          disabled={!hasData || loading}
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Generating Recommendations...
            </>
          ) : (
            <>
              <Lightbulb className="w-4 h-4" />
              Generate Recommendations
            </>
          )}
        </button>

        {error && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs">
            <AlertCircle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}
      </section>

      {decision && (
        <section className="space-y-5">
          <div className="bg-white border border-slate-200 rounded-xl p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs text-slate-500 font-medium">
                  Decision Priority
                </p>

                <h2 className="text-xl font-bold text-slate-900 mt-1">
                  Business Decision Analysis
                </h2>
              </div>

              <span
                className={`px-3 py-1.5 rounded-full border text-xs font-bold ${
                  priorityStyle[decision.priority]
                }`}
              >
                {decision.priority} PRIORITY
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-5">
              <div className="p-3 rounded-lg bg-slate-50">
                <p className="text-xs text-slate-500">Risk Level</p>
                <p className="font-bold text-slate-900 mt-1">
                  {decision.risk_context.risk_level}
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-50">
                <p className="text-xs text-slate-500">Risk Score</p>
                <p className="font-bold text-slate-900 mt-1">
                  {decision.risk_context.risk_score}
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-50">
                <p className="text-xs text-slate-500">
                  Anomaly Detected
                </p>
                <p className="font-bold text-slate-900 mt-1">
                  {decision.risk_context.anomaly_detected
                    ? "Yes"
                    : "No"}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
            <h3 className="font-bold text-slate-900 flex items-center gap-2">
              <BrainCircuit className="w-4 h-4 text-indigo-600" />
              Evidence
            </h3>

            <ul className="space-y-2">
              {decision.evidence.map((item, index) => (
                <li
                  key={index}
                  className="text-sm text-slate-600 flex gap-2"
                >
                  <span className="text-indigo-500">•</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
            <h3 className="font-bold text-slate-900 flex items-center gap-2">
              <Lightbulb className="w-4 h-4 text-amber-500" />
              Recommendations
            </h3>

            <div className="space-y-3">
              {decision.recommendations.map((item, index) => (
                <div
                  key={index}
                  className="p-3 rounded-lg bg-slate-50 border border-slate-100 text-sm text-slate-700"
                >
                  {item}
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
            <h3 className="font-bold text-slate-900 flex items-center gap-2">
              <ClipboardList className="w-4 h-4 text-indigo-600" />
              Action Plan
            </h3>

            {decision.action_plan.map((item, index) => (
              <div
                key={index}
                className="border border-slate-200 rounded-lg p-4 space-y-2"
              >
                <p className="font-semibold text-sm text-slate-900">
                  {index + 1}. {item.action}
                </p>

                <p className="text-xs text-slate-600">
                  <strong>Reason:</strong> {item.reason}
                </p>

                <p className="text-xs text-emerald-700">
                  <strong>Expected Benefit:</strong>{" "}
                  {item.expected_benefit}
                </p>

                <p className="text-xs text-amber-700">
                  <strong>Potential Risk:</strong> {item.risk}
                </p>
              </div>
            ))}
          </div>

          <div className="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
            <ShieldCheck className="w-5 h-5 text-emerald-700 shrink-0" />

            <p className="text-xs text-emerald-800 leading-relaxed">
              <strong>Human-in-the-Loop Governance:</strong>{" "}
              {decision.decision_disclaimer}
            </p>
          </div>
        </section>
      )}
    </div>
  );
}