
"use client";

import {
  BrainCircuit,
  TrendingUp,
  TrendingDown,
  SlidersHorizontal,
  ShieldCheck,
} from "lucide-react";

import {
  type BusinessMetrics,
  formatINR,
  formatNumber,
} from "./types";

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
  const hasPrediction =
    predictedProfit !== null &&
    predictedProfit !== undefined &&
    Number.isFinite(predictedProfit);

  const actualAverageProfit =
    actualMetrics?.average_profit;

  const hasActual =
    actualAverageProfit !== null &&
    actualAverageProfit !== undefined &&
    Number.isFinite(actualAverageProfit);

  const profitDifference =
    hasPrediction && hasActual
      ? predictedProfit - actualAverageProfit
      : null;

  const isPositiveDifference =
    profitDifference !== null &&
    profitDifference > 0;

  const isNegativeDifference =
    profitDifference !== null &&
    profitDifference < 0;

  const totalQuantity =
    actualMetrics?.total_sales ?? null;

  const totalRevenue =
    actualMetrics?.total_revenue ?? null;

  const totalExpense =
    actualMetrics?.total_expense ?? null;

  const revenuePerUnit =
    totalQuantity !== null &&
    totalQuantity !== 0 &&
    totalRevenue !== null
      ? totalRevenue / totalQuantity
      : null;

  const expensePerUnit =
    totalQuantity !== null &&
    totalQuantity !== 0 &&
    totalExpense !== null
      ? totalExpense / totalQuantity
      : null;

  const features = [
    {
      label: "Total Quantity",
      value:
        totalQuantity !== null
          ? formatNumber(totalQuantity)
          : "—",
    },
    {
      label: "Total Revenue",
      value: formatINR(totalRevenue),
    },
    {
      label: "Total Expense",
      value: formatINR(totalExpense),
    },
    {
      label: "Overall Profit Margin",
      value:
        actualMetrics?.profit_margin !== undefined
          ? `${actualMetrics.profit_margin.toFixed(2)}%`
          : "—",
    },
    {
      label: "Revenue / Unit",
      value: formatINR(revenuePerUnit),
    },
    {
      label: "Expense / Unit",
      value: formatINR(expensePerUnit),
    },
  ];

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-100 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-indigo-50 text-indigo-600">
            <BrainCircuit className="w-5 h-5" />
          </div>

          <div>
            <h2 className="text-lg font-bold text-slate-900">
              ML Profit Prediction
            </h2>

            <p className="text-xs text-slate-500 mt-1">
              Machine learning based business profit estimation
            </p>
          </div>
        </div>

        <span className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-100 text-slate-700 border border-slate-200">
          Random Forest Regressor
        </span>
      </div>

      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-12 gap-3">
          <div className="w-7 h-7 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />

          <p className="text-sm text-slate-500">
            Processing ML prediction...
          </p>
        </div>
      ) : !hasPrediction && !actualMetrics ? (
        <div className="text-center py-12 space-y-3">
          <BrainCircuit className="w-9 h-9 text-slate-300 mx-auto" />

          <h3 className="text-sm font-semibold text-slate-800">
            No Prediction Available
          </h3>

          <p className="text-xs text-slate-500">
            Upload a business CSV file to view ML predictions.
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-4">
              <p className="text-xs font-semibold text-indigo-700">
                Average Predicted Profit
              </p>

              <h3 className="text-2xl font-bold text-indigo-950 mt-2">
                {hasPrediction
                  ? formatINR(predictedProfit)
                  : "—"}
              </h3>

              <p className="text-xs text-indigo-600 mt-2">
                ML estimate per CSV record
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs font-semibold text-slate-600">
                Average Actual Profit
              </p>

              <h3 className="text-2xl font-bold text-slate-900 mt-2">
                {hasActual
                  ? formatINR(actualAverageProfit)
                  : "—"}
              </h3>

              <p className="text-xs text-slate-500 mt-2">
                Recorded profit per CSV record
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs font-semibold text-slate-600">
                Prediction Difference
              </p>

              <div className="flex items-center gap-2 mt-2">
                {isPositiveDifference ? (
                  <TrendingUp className="w-5 h-5 text-emerald-600" />
                ) : isNegativeDifference ? (
                  <TrendingDown className="w-5 h-5 text-rose-600" />
                ) : null}

                <h3
                  className={`text-2xl font-bold ${
                    isPositiveDifference
                      ? "text-emerald-700"
                      : isNegativeDifference
                      ? "text-rose-700"
                      : "text-slate-900"
                  }`}
                >
                  {profitDifference !== null
                    ? `${profitDifference > 0 ? "+" : ""}${formatINR(
                        profitDifference
                      )}`
                    : "—"}
                </h3>
              </div>

              <p className="text-xs text-slate-500 mt-2">
                Predicted minus actual average
              </p>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-5">
            <div className="flex items-center gap-2 mb-4">
              <SlidersHorizontal className="w-4 h-4 text-blue-600" />

              <h3 className="text-sm font-bold text-slate-800">
                Dataset Feature Summary
              </h3>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {features.map((feature) => (
                <div
                  key={feature.label}
                  className="rounded-lg bg-white border border-slate-200 p-3"
                >
                  <p className="text-xs text-slate-500">
                    {feature.label}
                  </p>

                  <p className="text-sm font-bold text-slate-900 mt-1 break-words">
                    {feature.value}
                  </p>
                </div>
              ))}
            </div>

            <p className="text-xs text-slate-500 mt-3">
              These values summarize the uploaded dataset.
              The model receives features calculated for
              each individual record.
            </p>
          </div>

          <div className="flex items-start gap-3 bg-blue-50/60 border border-blue-200 rounded-xl p-4">
            <ShieldCheck className="w-5 h-5 text-blue-600 shrink-0" />

            <p className="text-xs leading-relaxed text-slate-600">
              <strong>Model Limitation:</strong> Predictions
              are generated using a Random Forest model.
              They are estimates, not guaranteed outcomes.
              Model accuracy must be evaluated on sufficient,
              representative data before using predictions
              for real business decisions.
            </p>
          </div>
        </>
      )}
    </div>
  );
}
