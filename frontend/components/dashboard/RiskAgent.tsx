"use client";

import React, { useState } from "react";
import {
  ShieldAlert,
  AlertTriangle,
  CheckCircle,
  SlidersHorizontal,
  RefreshCw,
  Search,
  Activity,
  Layers,
} from "lucide-react";
import { RiskAnalysisResult, formatINR } from "./types";

interface RiskAgentProps {
  automaticRiskResult: RiskAnalysisResult | null;
  isLoading?: boolean;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function RiskAgent({
  automaticRiskResult,
  isLoading = false,
}: RiskAgentProps) {
  const [customQuantity, setCustomQuantity] = useState<string>("");
  const [customRevenue, setCustomRevenue] = useState<string>("");
  const [customExpense, setCustomExpense] = useState<string>("");
  const [customResult, setCustomResult] = useState<RiskAnalysisResult | null>(null);
  const [customLoading, setCustomLoading] = useState<boolean>(false);
  const [customError, setCustomError] = useState<string>("");
  const [showCustomForm, setShowCustomForm] = useState<boolean>(false);

  const displayResult = customResult || automaticRiskResult;

  const handleCustomAnalyze = async () => {
    setCustomError("");
    const q = Number(customQuantity);
    const r = Number(customRevenue);
    const e = Number(customExpense);

    if (isNaN(q) || isNaN(r) || isNaN(e) || !q || !r) {
      setCustomError("Please enter valid numbers for Quantity, Revenue, and Expense.");
      return;
    }

    setCustomLoading(true);

    try {
      const res = await fetch(`${API_BASE}/analyze-risk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          Quantity: q,
          Revenue: r,
          Expense: e,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : data.detail?.message || "Risk evaluation failed."
        );
      }

      setCustomResult(data);
    } catch (err: unknown) {
      setCustomError(err instanceof Error ? err.message : "Failed to run risk analysis.");
    } finally {
      setCustomLoading(false);
    }
  };

  const handleResetCustom = () => {
    setCustomQuantity("");
    setCustomRevenue("");
    setCustomExpense("");
    setCustomResult(null);
    setCustomError("");
    setShowCustomForm(false);
  };

  const riskLevel = displayResult?.risk_level?.toUpperCase();
  const isHigh = riskLevel === "HIGH";
  const isMedium = riskLevel === "MEDIUM";

  const badgeColor = isHigh
    ? "bg-rose-50 text-rose-800 border-rose-200/90"
    : isMedium
    ? "bg-amber-50 text-amber-800 border-amber-200/90"
    : "bg-emerald-50 text-emerald-800 border-emerald-200/90";

  const progressColor = isHigh
    ? "bg-rose-600"
    : isMedium
    ? "bg-amber-500"
    : "bg-emerald-600";

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-6 sm:p-7 flex flex-col justify-between transition-all">
      <div>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6 pb-4 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-amber-50 text-amber-700 border border-amber-100">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-amber-700">
                  AI Diagnostic Agent
                </span>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                  Answers: What is wrong?
                </span>
              </div>
              <h3 className="text-lg font-bold text-slate-900 mt-0.5">
                Risk Agent
              </h3>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {displayResult && (
              <span className={`px-3 py-1 rounded-full text-xs font-extrabold border ${badgeColor}`}>
                {riskLevel} RISK
              </span>
            )}
            <button
              type="button"
              onClick={() => setShowCustomForm(!showCustomForm)}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-xl transition-colors cursor-pointer border border-slate-200/80"
              title="Test custom parameters with Risk Agent"
            >
              <SlidersHorizontal className="w-3.5 h-3.5 text-slate-500" />
              <span>{showCustomForm ? "Close Form" : "Custom Evaluation"}</span>
            </button>
          </div>
        </div>

        {showCustomForm && (
          <div className="bg-slate-50/90 rounded-xl p-4 border border-slate-200 mb-5 space-y-3">
            <div className="flex items-center justify-between text-xs font-bold text-slate-700">
              <span>Manual Risk Parameter Evaluation</span>
              {customResult && (
                <button
                  type="button"
                  onClick={handleResetCustom}
                  className="text-xs font-semibold text-blue-600 hover:text-blue-800 cursor-pointer"
                >
                  Return to Automatic Results
                </button>
              )}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                  Quantity
                </label>
                <input
                  type="number"
                  placeholder="e.g. 100"
                  value={customQuantity}
                  onChange={(e) => setCustomQuantity(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-white rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                  Revenue (₹)
                </label>
                <input
                  type="number"
                  placeholder="e.g. 50000"
                  value={customRevenue}
                  onChange={(e) => setCustomRevenue(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-white rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                  Expense (₹)
                </label>
                <input
                  type="number"
                  placeholder="e.g. 30000"
                  value={customExpense}
                  onChange={(e) => setCustomExpense(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-white rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div className="flex items-center gap-3 pt-1">
              <button
                type="button"
                onClick={handleCustomAnalyze}
                disabled={customLoading || !customQuantity || !customRevenue}
                className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs transition-colors flex items-center gap-1.5 disabled:opacity-50 cursor-pointer shadow-xs"
              >
                {customLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : null}
                <span>Evaluate Custom Parameters</span>
              </button>
            </div>
            {customError && (
              <p className="text-xs text-rose-600 font-semibold mt-1">{customError}</p>
            )}
          </div>
        )}

        {isLoading ? (
          <div className="py-12 text-center space-y-3">
            <div className="w-8 h-8 mx-auto border-3 border-amber-600 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm font-semibold text-slate-700">
              Evaluating risk scores and anomaly indicators...
            </p>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Scanning for volume-cost deviations, Isolation Forest anomalies, and loss exposure.
            </p>
          </div>
        ) : displayResult ? (
          <div className="space-y-5">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {/* Factor 1: Composite Risk Score */}
              <div className="rounded-xl bg-slate-50 border border-slate-200/80 p-3.5">
                <div className="flex items-center justify-between text-[11px] font-semibold text-slate-500">
                  <span>Overall Risk Score</span>
                  <Activity className="w-3.5 h-3.5 text-slate-400" />
                </div>
                <div className="text-2xl font-black text-slate-900 mt-1">
                  {displayResult.risk_score} <span className="text-xs font-semibold text-slate-400">/ 100</span>
                </div>
                <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden mt-2.5">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${progressColor}`}
                    style={{ width: `${Math.min(100, Math.max(0, displayResult.risk_score))}%` }}
                  />
                </div>
                <span className="text-[10px] text-slate-500 block mt-1.5 font-medium">
                  Overall Composite Risk
                </span>
              </div>

              {/* Factor 2: Statistical Anomaly Detection (Distinct from Overall Risk) */}
              <div className="rounded-xl bg-slate-50 border border-slate-200/80 p-3.5">
                <div className="flex items-center justify-between text-[11px] font-semibold text-slate-500">
                  <span>Anomaly Detection</span>
                  <Search className="w-3.5 h-3.5 text-slate-400" />
                </div>
                <div className="flex items-center gap-1.5 mt-1.5">
                  {displayResult.anomaly_detected ? (
                    <>
                      <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
                      <span className="text-base font-bold text-rose-700">Outlier Detected</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
                      <span className="text-base font-bold text-emerald-700">Normal Patterns</span>
                    </>
                  )}
                </div>
                <span className="text-[10px] text-slate-500 block mt-2 font-medium">
                  Model: Isolation Forest (Statistical)
                </span>
              </div>

              {/* Factor 3: Predicted Profit */}
              <div className="rounded-xl bg-slate-50 border border-slate-200/80 p-3.5">
                <div className="flex items-center justify-between text-[11px] font-semibold text-slate-500">
                  <span>Predicted Profit</span>
                  <Layers className="w-3.5 h-3.5 text-slate-400" />
                </div>
                <div className="text-xl font-black text-slate-900 mt-1">
                  {formatINR(displayResult.predicted_profit)}
                </div>
                <span className="text-[10px] text-slate-500 block mt-2 font-medium">
                  Random Forest Baseline
                </span>
              </div>
            </div>

            {/* Diagnostic Reasons */}
            <div className="rounded-xl bg-slate-50/80 border border-slate-200/80 p-4">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2.5">
                Risk Agent Findings & Analysis
              </h4>
              <div className="space-y-2">
                {displayResult.risk_analysis?.reasons && displayResult.risk_analysis.reasons.length > 0 ? (
                  displayResult.risk_analysis.reasons.map((reason, idx) => (
                    <div key={idx} className="flex items-start gap-2.5 text-xs text-slate-700 font-medium">
                      <div className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0" />
                      <span className="leading-relaxed">{reason}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400 italic">No critical risk conditions detected.</p>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="py-12 text-center space-y-2">
            <div className="w-10 h-10 mx-auto rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <p className="text-sm font-semibold text-slate-600">
              No risk diagnostics generated
            </p>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Upload business data above to execute multi-factor risk scoring, anomaly detection, and diagnostic reasoning.
            </p>
          </div>
        )}
      </div>

      <div className="pt-4 mt-5 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
        <span>Anomaly Engine: Isolation Forest</span>
        <span>Risk Scoring: Multi-factor Rules</span>
      </div>
    </div>
  );
}
