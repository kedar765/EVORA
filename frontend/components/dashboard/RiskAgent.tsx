
"use client";

import { useEffect, useState } from "react";
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

import {
  type RiskAnalysisResult,
  formatINR,
} from "./types";

interface RiskAgentProps {
  automaticRiskResult: RiskAnalysisResult | null;
  isLoading?: boolean;
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

export default function RiskAgent({
  automaticRiskResult,
  isLoading = false,
}: RiskAgentProps) {
  const [quantity, setQuantity] = useState("");
  const [revenue, setRevenue] = useState("");
  const [expense, setExpense] = useState("");

  const [customResult, setCustomResult] =
    useState<RiskAnalysisResult | null>(null);

  const [customLoading, setCustomLoading] =
    useState(false);

  const [error, setError] = useState("");
  const [showCustomForm, setShowCustomForm] =
    useState(false);

  useEffect(() => {
    setCustomResult(null);
    setError("");
  }, [automaticRiskResult]);

  const displayResult =
    customResult ?? automaticRiskResult;

  const handleCustomAnalyze = async () => {
    if (customLoading || isLoading) return;

    setError("");
    setCustomResult(null);

    if (
      quantity.trim() === "" ||
      revenue.trim() === "" ||
      expense.trim() === ""
    ) {
      setError("Please fill in all fields.");
      return;
    }

    const values = [
      Number(quantity),
      Number(revenue),
      Number(expense),
    ];

    if (
      values.some((value) => !Number.isFinite(value))
    ) {
      setError("Please enter valid numeric values.");
      return;
    }

    const [q, r, e] = values;

    if (q <= 0) {
      setError(
        "Quantity must be greater than zero."
      );
      return;
    }

    if (r < 0 || e < 0) {
      setError(
        "Revenue and Expense cannot be negative."
      );
      return;
    }

    setCustomLoading(true);

    try {
      const response = await fetch(
        `${API_BASE_URL}/analyze-risk`,
        {
          method: "POST",
          credentials: "include",
          cache: "no-store",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            Quantity: q,
            Revenue: r,
            Expense: e,
          }),
        }
      );

      if (response.status === 401) {
        throw new Error(
          "Your session has expired. Please log in again."
        );
      }

      const data: unknown = await response
        .json()
        .catch(() => null);

      if (!response.ok) {
        const errorData = data as {
          detail?: string | { message?: string };
        } | null;

        const detail = errorData?.detail;

        throw new Error(
          typeof detail === "string"
            ? detail
            : typeof detail?.message === "string"
            ? detail.message
            : "Risk analysis failed."
        );
      }

      const result = data as RiskAnalysisResult | null;

      if (
        !result ||
        result.success !== true ||
        typeof result.risk_score !== "number" ||
        !Number.isFinite(result.risk_score) ||
        typeof result.risk_level !== "string" ||
        typeof result.anomaly_detected !== "boolean" ||
        typeof result.predicted_profit !== "number" ||
        !Number.isFinite(result.predicted_profit)
      ) {
        throw new Error(
          "Invalid risk analysis response from backend."
        );
      }

      setCustomResult(result);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to connect to EVORA backend."
      );
    } finally {
      setCustomLoading(false);
    }
  };

  const handleReset = () => {
    if (customLoading) return;

    setQuantity("");
    setRevenue("");
    setExpense("");

    setCustomResult(null);
    setError("");
    setShowCustomForm(false);
  };

  const riskLevel =
    displayResult?.risk_level?.toUpperCase();

  const isHigh = riskLevel === "HIGH";
  const isMedium = riskLevel === "MEDIUM";

  const badgeColor = isHigh
    ? "bg-rose-50 text-rose-800 border-rose-200"
    : isMedium
    ? "bg-amber-50 text-amber-800 border-amber-200"
    : "bg-emerald-50 text-emerald-800 border-emerald-200";

  const progressColor = isHigh
    ? "bg-rose-600"
    : isMedium
    ? "bg-amber-500"
    : "bg-emerald-600";

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-7">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6 pb-4 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-amber-50 text-amber-700">
            <ShieldAlert className="w-5 h-5" />
          </div>

          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-amber-700">
              Risk Intelligence
            </span>

            <h3 className="text-lg font-bold text-slate-900 mt-0.5">
              Risk Agent
            </h3>

            <p className="text-xs text-slate-500">
              What is wrong?
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {displayResult && (
            <span
              className={`px-3 py-1 rounded-full text-xs font-bold border ${badgeColor}`}
            >
              {riskLevel} RISK
            </span>
          )}

          <button
            type="button"
            onClick={() =>
              setShowCustomForm((current) => !current)
            }
            disabled={customLoading}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-xl border border-slate-200 disabled:opacity-50"
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            {showCustomForm
              ? "Close Form"
              : "Custom Evaluation"}
          </button>
        </div>
      </div>

      {showCustomForm && (
        <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 mb-5 space-y-4">
          <div className="flex items-center justify-between gap-2">
            <h4 className="text-xs font-bold text-slate-700">
              Manual Risk Evaluation
            </h4>

            {customResult && (
              <button
                type="button"
                onClick={handleReset}
                className="text-xs font-semibold text-blue-600 hover:text-blue-800"
              >
                Return to Automatic Results
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label
                htmlFor="risk-quantity"
                className="block text-xs font-semibold text-slate-600 mb-1"
              >
                Quantity
              </label>

              <input
                id="risk-quantity"
                type="number"
                min="0"
                step="any"
                placeholder="e.g. 100"
                value={quantity}
                onChange={(event) => {
                  setQuantity(event.target.value);
                  setCustomResult(null);
                }}
                disabled={customLoading}
                className="w-full px-3 py-2 text-sm bg-white rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label
                htmlFor="risk-revenue"
                className="block text-xs font-semibold text-slate-600 mb-1"
              >
                Revenue (₹)
              </label>

              <input
                id="risk-revenue"
                type="number"
                min="0"
                step="any"
                placeholder="e.g. 50000"
                value={revenue}
                onChange={(event) => {
                  setRevenue(event.target.value);
                  setCustomResult(null);
                }}
                disabled={customLoading}
                className="w-full px-3 py-2 text-sm bg-white rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label
                htmlFor="risk-expense"
                className="block text-xs font-semibold text-slate-600 mb-1"
              >
                Expense (₹)
              </label>

              <input
                id="risk-expense"
                type="number"
                min="0"
                step="any"
                placeholder="e.g. 30000"
                value={expense}
                onChange={(event) => {
                  setExpense(event.target.value);
                  setCustomResult(null);
                }}
                disabled={customLoading}
                className="w-full px-3 py-2 text-sm bg-white rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <button
            type="button"
            onClick={handleCustomAnalyze}
            disabled={
              customLoading ||
              isLoading ||
              !quantity.trim() ||
              !revenue.trim() ||
              !expense.trim()
            }
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs disabled:opacity-50"
          >
            {customLoading && (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            )}

            {customLoading
              ? "Evaluating..."
              : "Evaluate Risk"}
          </button>

          {error && (
            <div
              role="alert"
              className="rounded-lg bg-rose-50 border border-rose-200 p-3 text-xs font-semibold text-rose-700"
            >
              {error}
            </div>
          )}
        </div>
      )}

      {isLoading ? (
        <div className="py-12 text-center space-y-3">
          <RefreshCw className="w-7 h-7 mx-auto animate-spin text-amber-600" />

          <p className="text-sm font-medium text-slate-700">
            Evaluating business risk...
          </p>
        </div>
      ) : displayResult ? (
        <div className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="rounded-xl bg-slate-50 border border-slate-200 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-500">
                  Overall Risk Score
                </span>

                <Activity className="w-4 h-4 text-slate-400" />
              </div>

              <div className="text-2xl font-bold text-slate-900 mt-2">
                {displayResult.risk_score}
                <span className="text-xs text-slate-500">
                  {" "}/ 100
                </span>
              </div>

              <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden mt-3">
                <div
                  className={`h-full rounded-full ${progressColor}`}
                  style={{
                    width: `${Math.min(
                      100,
                      Math.max(
                        0,
                        displayResult.risk_score
                      )
                    )}%`,
                  }}
                />
              </div>
            </div>

            <div className="rounded-xl bg-slate-50 border border-slate-200 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-500">
                  Anomaly Detection
                </span>

                <Search className="w-4 h-4 text-slate-400" />
              </div>

              <div className="flex items-center gap-2 mt-3">
                {displayResult.anomaly_detected ? (
                  <>
                    <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />

                    <span className="text-sm font-bold text-rose-700">
                      Outlier Detected
                    </span>
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />

                    <span className="text-sm font-bold text-emerald-700">
                      Normal Patterns
                    </span>
                  </>
                )}
              </div>

              <p className="text-xs text-slate-500 mt-2">
                Isolation Forest Model
              </p>
            </div>

            <div className="rounded-xl bg-slate-50 border border-slate-200 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-500">
                  Predicted Profit
                </span>

                <Layers className="w-4 h-4 text-slate-400" />
              </div>

              <div className="text-xl font-bold text-slate-900 mt-3">
                {formatINR(
                  displayResult.predicted_profit
                )}
              </div>

              <p className="text-xs text-slate-500 mt-2">
                Random Forest Estimate
              </p>
            </div>
          </div>

          <div className="rounded-xl bg-slate-50 border border-slate-200 p-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3">
              Risk Findings
            </h4>

            {displayResult.risk_analysis?.reasons?.length ? (
              <div className="space-y-3">
                {displayResult.risk_analysis.reasons.map(
                  (reason, index) => (
                    <div
                      key={index}
                      className="flex items-start gap-2.5 text-xs text-slate-700"
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0" />

                      <span className="leading-relaxed">
                        {reason}
                      </span>
                    </div>
                  )
                )}
              </div>
            ) : (
              <p className="text-xs text-slate-500">
                No detailed risk findings available.
              </p>
            )}
          </div>

          <p className="text-xs text-slate-500 leading-relaxed">
            Risk scores are rule-based indicators.
            Anomalies represent unusual patterns, not
            confirmed business losses or fraud.
            Final decisions require human review.
          </p>
        </div>
      ) : (
        <div className="py-12 text-center space-y-3">
          <ShieldAlert className="w-9 h-9 text-slate-300 mx-auto" />

          <p className="text-sm font-semibold text-slate-700">
            No Risk Analysis Available
          </p>

          <p className="text-xs text-slate-500">
            Upload business data or run a custom evaluation.
          </p>
        </div>
      )}

      <div className="pt-4 mt-5 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
        <span>Isolation Forest</span>
        <span>Rule-Based Risk Scoring</span>
      </div>
    </div>
  );
}
