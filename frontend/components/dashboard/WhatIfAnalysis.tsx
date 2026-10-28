
"use client";

import { useState } from "react";
import {
  GitCompare,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  Zap,
  ShieldCheck,
  RotateCcw,
} from "lucide-react";

import {
  type WhatIfResult,
  type BusinessMetrics,
  formatINR,
} from "./types";

interface WhatIfAnalysisProps {
  currentMetrics: BusinessMetrics | null;
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

export default function WhatIfAnalysis({
  currentMetrics,
}: WhatIfAnalysisProps) {
  const [currentQuantity, setCurrentQuantity] = useState("");
  const [currentRevenue, setCurrentRevenue] = useState("");
  const [currentExpense, setCurrentExpense] = useState("");

  const [newQuantity, setNewQuantity] = useState("");
  const [newRevenue, setNewRevenue] = useState("");
  const [newExpense, setNewExpense] = useState("");

  const [result, setResult] = useState<WhatIfResult | null>(
    null
  );

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handlePopulateFromCurrent = () => {
    if (!currentMetrics || isLoading) return;

    const quantity = String(
      currentMetrics.total_sales
    );
    const revenue = String(
      currentMetrics.total_revenue
    );
    const expense = String(
      currentMetrics.total_expense
    );

    setCurrentQuantity(quantity);
    setCurrentRevenue(revenue);
    setCurrentExpense(expense);

    setNewQuantity(quantity);
    setNewRevenue(revenue);
    setNewExpense(expense);

    setResult(null);
    setError("");
  };

  const handleRunSimulation = async () => {
    if (isLoading) return;

    setError("");
    setResult(null);

    const inputs = [
      currentQuantity,
      currentRevenue,
      currentExpense,
      newQuantity,
      newRevenue,
      newExpense,
    ];

    if (inputs.some((value) => value.trim() === "")) {
      setError("Please fill in all scenario fields.");
      return;
    }

    const [
      cq,
      cr,
      ce,
      nq,
      nr,
      ne,
    ] = inputs.map(Number);

    if (
      [cq, cr, ce, nq, nr, ne].some(
        (value) => !Number.isFinite(value)
      )
    ) {
      setError("Please enter valid numeric values.");
      return;
    }

    if (cq <= 0 || nq <= 0) {
      setError(
        "Current and proposed quantities must be greater than zero."
      );
      return;
    }

    if (
      cr < 0 ||
      ce < 0 ||
      nr < 0 ||
      ne < 0
    ) {
      setError(
        "Revenue and expense values cannot be negative."
      );
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch(
        `${API_BASE_URL}/what-if`,
        {
          method: "POST",
          credentials: "include",
          cache: "no-store",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            current_quantity: cq,
            current_revenue: cr,
            current_expense: ce,
            new_quantity: nq,
            new_revenue: nr,
            new_expense: ne,
          }),
        }
      );

      if (response.status === 401) {
        throw new Error(
          "Your session has expired. Please log in again."
        );
      }

      const data = await response
        .json()
        .catch(() => null);

      if (!response.ok) {
        const detail = data?.detail;

        throw new Error(
          typeof detail === "string"
            ? detail
            : typeof detail?.message === "string"
            ? detail.message
            : "Scenario simulation failed."
        );
      }

      if (
        data?.success !== true ||
        typeof data.current_predicted_profit !== "number" ||
        typeof data.new_predicted_profit !== "number" ||
        typeof data.profit_difference !== "number" ||
        typeof data.result !== "string" ||
        !Number.isFinite(data.current_predicted_profit) ||
        !Number.isFinite(data.new_predicted_profit) ||
        !Number.isFinite(data.profit_difference)
      ) {
        throw new Error(
          "Invalid simulation response received from backend."
        );
      }

      setResult(data as WhatIfResult);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to connect to EVORA backend."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    if (isLoading) return;

    setCurrentQuantity("");
    setCurrentRevenue("");
    setCurrentExpense("");

    setNewQuantity("");
    setNewRevenue("");
    setNewExpense("");

    setResult(null);
    setError("");
  };

  const isIncrease =
    result !== null && result.profit_difference > 0;

  const isDecrease =
    result !== null && result.profit_difference < 0;

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-6 sm:p-7 transition-all">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6 pb-4 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center justify-center w-6 h-6 rounded-md bg-blue-50 text-blue-700">
              <GitCompare className="w-3.5 h-3.5" />
            </span>

            <span className="text-xs font-bold uppercase tracking-wider text-blue-700">
              Decision Support
            </span>
          </div>

          <h2 className="text-xl font-bold text-slate-900 tracking-tight">
            What-If Analysis
          </h2>

          <p className="text-sm text-slate-500 mt-0.5">
            Compare a proposed business scenario with
            current performance.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          {currentMetrics && (
            <button
              type="button"
              onClick={handlePopulateFromCurrent}
              disabled={isLoading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200/80 transition-colors disabled:opacity-50"
            >
              <Zap className="w-3.5 h-3.5" />
              <span>Use Current Data</span>
            </button>
          )}

          {(currentQuantity || newQuantity || result) && (
            <button
              type="button"
              onClick={handleReset}
              disabled={isLoading}
              className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-slate-800 px-2.5 py-1.5 rounded-lg hover:bg-slate-100 transition-colors disabled:opacity-50"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Reset</span>
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-5">
        <div className="rounded-xl bg-slate-50 border border-slate-200/90 p-4 sm:p-5">
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-200/70">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
              Scenario A • Current Baseline
            </span>

            <span className="text-[10px] font-semibold text-slate-500 bg-white px-2 py-0.5 rounded border border-slate-200">
              Current Values
            </span>
          </div>

          <div className="space-y-3.5">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Quantity (Units)
              </label>
              <input
                type="number"
                min="0"
                step="any"
                placeholder="Enter quantity"
                value={currentQuantity}
                onChange={(event) =>
                  setCurrentQuantity(event.target.value)
                }
                disabled={isLoading}
                className="w-full px-3 py-2 text-sm bg-white rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Revenue (₹)
              </label>
              <input
                type="number"
                min="0"
                step="any"
                placeholder="Enter revenue"
                value={currentRevenue}
                onChange={(event) =>
                  setCurrentRevenue(event.target.value)
                }
                disabled={isLoading}
                className="w-full px-3 py-2 text-sm bg-white rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Expense (₹)
              </label>
              <input
                type="number"
                min="0"
                step="any"
                placeholder="Enter expense"
                value={currentExpense}
                onChange={(event) =>
                  setCurrentExpense(event.target.value)
                }
                disabled={isLoading}
                className="w-full px-3 py-2 text-sm bg-white rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        <div className="rounded-xl bg-blue-50/40 border border-blue-200/80 p-4 sm:p-5">
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-blue-200/70">
            <span className="text-xs font-bold uppercase tracking-wider text-blue-800">
              Scenario B • Proposed Scenario
            </span>

            <span className="text-[10px] font-semibold text-blue-700 bg-white px-2 py-0.5 rounded border border-blue-200">
              Proposed Values
            </span>
          </div>

          <div className="space-y-3.5">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Target Quantity (Units)
              </label>
              <input
                type="number"
                min="0"
                step="any"
                placeholder="Enter target quantity"
                value={newQuantity}
                onChange={(event) =>
                  setNewQuantity(event.target.value)
                }
                disabled={isLoading}
                className="w-full px-3 py-2 text-sm bg-white rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Target Revenue (₹)
              </label>
              <input
                type="number"
                min="0"
                step="any"
                placeholder="Enter target revenue"
                value={newRevenue}
                onChange={(event) =>
                  setNewRevenue(event.target.value)
                }
                disabled={isLoading}
                className="w-full px-3 py-2 text-sm bg-white rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Target Expense (₹)
              </label>
              <input
                type="number"
                min="0"
                step="any"
                placeholder="Enter target expense"
                value={newExpense}
                onChange={(event) =>
                  setNewExpense(event.target.value)
                }
                disabled={isLoading}
                className="w-full px-3 py-2 text-sm bg-white rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3 mb-5">
        <button
          type="button"
          onClick={handleRunSimulation}
          disabled={
            isLoading ||
            !currentQuantity ||
            !newQuantity
          }
          className="inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs sm:text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
        >
          {isLoading ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span>Simulating...</span>
            </>
          ) : (
            <>
              <GitCompare className="w-4 h-4" />
              <span>Run What-If Comparison</span>
            </>
          )}
        </button>
      </div>

      {error && (
        <div
          role="alert"
          className="rounded-xl bg-rose-50 border border-rose-200/90 p-4 text-xs font-semibold text-rose-700 mb-5"
        >
          {error}
        </div>
      )}

      {result && (
        <div className="rounded-xl bg-slate-50 border border-slate-200/90 p-5 sm:p-6 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-3 border-b border-slate-200/70">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Simulation Outcome
              </span>

              <h4 className="text-base font-bold text-slate-900">
                Scenario Comparison Summary
              </h4>
            </div>

            <div
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${
                isIncrease
                  ? "bg-emerald-50 text-emerald-800 border-emerald-200/80"
                  : isDecrease
                  ? "bg-rose-50 text-rose-800 border-rose-200/80"
                  : "bg-slate-100 text-slate-700 border-slate-200"
              }`}
            >
              {isIncrease ? (
                <TrendingUp className="w-3.5 h-3.5" />
              ) : isDecrease ? (
                <TrendingDown className="w-3.5 h-3.5" />
              ) : null}

              <span>{result.result}</span>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
            <div className="rounded-xl bg-white p-4 border border-slate-200 shadow-xs">
              <span className="text-xs font-semibold text-slate-500 block">
                Current Predicted Profit
              </span>

              <span className="text-xl font-black text-slate-900 mt-1 block tracking-tight">
                {formatINR(
                  result.current_predicted_profit
                )}
              </span>

              <span className="text-[10px] text-slate-400 mt-1 block">
                Scenario A Baseline
              </span>
            </div>

            <div className="rounded-xl bg-white p-4 border border-blue-200 shadow-xs">
              <span className="text-xs font-semibold text-blue-700 block">
                Proposed Predicted Profit
              </span>

              <span className="text-xl font-black text-blue-900 mt-1 block tracking-tight">
                {formatINR(
                  result.new_predicted_profit
                )}
              </span>

              <span className="text-[10px] text-blue-500 mt-1 block">
                Scenario B Target
              </span>
            </div>

            <div className="rounded-xl bg-white p-4 border border-slate-200 shadow-xs">
              <span className="text-xs font-semibold text-slate-500 block">
                Projected Profit Delta
              </span>

              <span
                className={`text-xl font-black mt-1 block tracking-tight ${
                  isIncrease
                    ? "text-emerald-700"
                    : isDecrease
                    ? "text-rose-700"
                    : "text-slate-900"
                }`}
              >
                {result.profit_difference >= 0
                  ? "+"
                  : ""}
                {formatINR(
                  result.profit_difference
                )}
              </span>

              <span className="text-[10px] text-slate-400 mt-1 block">
                Estimated difference
              </span>
            </div>
          </div>

          <div className="flex items-start gap-2.5 pt-3 text-xs text-slate-600 border-t border-slate-200/70">
            <ShieldCheck className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />

            <p className="leading-relaxed">
              <strong>
                Decision Support:
              </strong>{" "}
              These predictions are estimates generated by
              the ML model, not guaranteed business outcomes.
              EVORA does not execute decisions automatically.
              Final decisions remain with the user.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
