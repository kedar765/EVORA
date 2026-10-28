"use client";

import React from "react";
import {
  BrainCircuit,
  Sliders,
  Shield,
} from "lucide-react";
import { BusinessMetrics, formatINR } from "./types";

interface MlPredictionProps {
  predictedProfit: number | null | undefined;
  actualMetrics?: BusinessMetrics | null;
  isLoading: boolean;
}

export default function MlPrediction({
  predictedProfit,
  actualMetrics,
  isLoading,
}: MlPredictionProps) {
  const hasPrediction = predictedProfit !== null && predictedProfit !== undefined;
  const actualProfit = actualMetrics?.total_profit;
  const hasActual = actualProfit !== undefined && actualProfit !== null;

  const profitVariance =
    hasPrediction && hasActual ? predictedProfit - actualProfit : null;

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 p-5 sm:p-6 shadow-xs space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-indigo-50 text-indigo-600">
            <BrainCircuit className="w-4 h-4" />
          </div>
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Predictive Intelligence
            </span>
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">
              Machine Learning Profit Prediction
            </h2>
          </div>
        </div>

        <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-slate-100 text-slate-600 border border-slate-200/80">
          Random Forest Regressor
        </span>
      </div>

      {isLoading ? (
        <div className="py-10 text-center space-y-2 text-slate-400">
          <div className="w-6 h-6 mx-auto border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs font-medium text-slate-500">
            Executing Random Forest regression on engineered features...
          </p>
        </div>
      ) : (
        <div className="space-y-5">
          {/* Main Comparison: Actual vs Predicted */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Predicted Profit Card */}
            <div className="p-4 rounded-lg bg-indigo-50/50 border border-indigo-200/80 space-y-1.5">
              <div className="flex items-center justify-between text-xs font-semibold text-indigo-700">
                <span>Predicted Profit</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-800">
                  ML ESTIMATE
                </span>
              </div>
              <div className="text-2xl font-bold text-indigo-950">
                {hasPrediction ? formatINR(predictedProfit) : "—"}
              </div>
              <p className="text-[11px] text-indigo-600">
                Output of Random Forest regressor on feature inputs
              </p>
            </div>

            {/* Actual Recorded Profit Card */}
            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200/80 space-y-1.5">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-600">
                <span>Actual Net Profit</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-200 text-slate-700">
                  VERIFIED DATA
                </span>
              </div>
              <div
                className={`text-2xl font-bold ${
                  hasActual
                    ? actualProfit >= 0
                      ? "text-emerald-700"
                      : "text-rose-700"
                    : "text-slate-900"
                }`}
              >
                {hasActual ? formatINR(actualProfit) : "—"}
              </div>
              <p className="text-[11px] text-slate-400">
                Sum of Revenue minus Expense from uploaded CSV
              </p>
            </div>

            {/* Model Variance */}
            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200/80 space-y-1.5">
              <span className="text-xs font-semibold text-slate-600 block">
                Model Variance (Predicted − Actual)
              </span>
              <div
                className={`text-2xl font-bold ${
                  profitVariance !== null
                    ? profitVariance >= 0
                      ? "text-blue-700"
                      : "text-amber-700"
                    : "text-slate-900"
                }`}
              >
                {profitVariance !== null
                  ? `${profitVariance >= 0 ? "+" : ""}${formatINR(profitVariance)}`
                  : "—"}
              </div>
              <p className="text-[11px] text-slate-400">
                Difference between ML regression projection and historical sum
              </p>
            </div>
          </div>

          {/* Model Inputs Transparency */}
          <div className="p-4 rounded-lg bg-slate-50 border border-slate-200/70 space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-700">
              <Sliders className="w-3.5 h-3.5 text-blue-600" />
              <span>Prepared Model Input Features (6 Normalized Dimensions)</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 text-xs">
              <div className="p-2.5 rounded bg-white border border-slate-200/80">
                <span className="text-[10px] text-slate-400 block font-medium">Quantity</span>
                <span className="font-semibold text-slate-800 mt-0.5 block">
                  {actualMetrics?.total_sales !== undefined ? actualMetrics.total_sales.toLocaleString() : "—"}
                </span>
              </div>

              <div className="p-2.5 rounded bg-white border border-slate-200/80">
                <span className="text-[10px] text-slate-400 block font-medium">Revenue</span>
                <span className="font-semibold text-slate-800 mt-0.5 block">
                  {actualMetrics?.total_revenue ? formatINR(actualMetrics.total_revenue) : "—"}
                </span>
              </div>

              <div className="p-2.5 rounded bg-white border border-slate-200/80">
                <span className="text-[10px] text-slate-400 block font-medium">Expense</span>
                <span className="font-semibold text-slate-800 mt-0.5 block">
                  {actualMetrics?.total_expense ? formatINR(actualMetrics.total_expense) : "—"}
                </span>
              </div>

              <div className="p-2.5 rounded bg-white border border-slate-200/80">
                <span className="text-[10px] text-slate-400 block font-medium">Profit Margin</span>
                <span className="font-semibold text-slate-800 mt-0.5 block">
                  {actualMetrics?.profit_margin !== undefined ? `${actualMetrics.profit_margin.toFixed(1)}%` : "—"}
                </span>
              </div>

              <div className="p-2.5 rounded bg-white border border-slate-200/80">
                <span className="text-[10px] text-slate-400 block font-medium">Rev / Unit</span>
                <span className="font-semibold text-slate-800 mt-0.5 block">
                  {actualMetrics?.total_sales && actualMetrics.total_revenue
                    ? formatINR(actualMetrics.total_revenue / actualMetrics.total_sales)
                    : "—"}
                </span>
              </div>

              <div className="p-2.5 rounded bg-white border border-slate-200/80">
                <span className="text-[10px] text-slate-400 block font-medium">Exp / Unit</span>
                <span className="font-semibold text-slate-800 mt-0.5 block">
                  {actualMetrics?.total_sales && actualMetrics.total_expense
                    ? formatINR(actualMetrics.total_expense / actualMetrics.total_sales)
                    : "—"}
                </span>
              </div>
            </div>
          </div>

          {/* Model Limitation Note */}
          <div className="p-3.5 rounded-lg bg-blue-50/50 border border-blue-200/70 flex items-start gap-2.5 text-xs text-slate-600">
            <Shield className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
            <p className="leading-relaxed">
              <strong>Model Limitation Notice:</strong> Predicted profit is an algorithmic regression output based on historical training patterns and the six prepared unit features above. Business outcomes are subject to operational conditions, market volatility, and unmodeled external factors; predictions do not constitute guaranteed earnings.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
