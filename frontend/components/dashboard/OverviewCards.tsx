"use client";

import React from "react";
import {
  IndianRupee,
  CreditCard,
  TrendingUp,
  TrendingDown,
  Percent,
  BrainCircuit,
  ShieldAlert,
  Search,
  Package,
} from "lucide-react";
import { UploadResult, formatINR } from "./types";

interface OverviewCardsProps {
  uploadResult: UploadResult | null;
}

export default function OverviewCards({ uploadResult }: OverviewCardsProps) {
  const metrics = uploadResult?.metrics || null;
  const hasData = !!uploadResult && !!metrics;

  const totalRevenue = metrics?.total_revenue;
  const totalExpense = metrics?.total_expense;
  const totalProfit = metrics?.total_profit;
  const profitMargin = metrics?.profit_margin;
  const predictedProfit = uploadResult?.predicted_profit;
  const riskScore = uploadResult?.risk_score;
  const riskLevel = uploadResult?.risk_level?.toUpperCase();
  const anomalyCount = uploadResult?.anomaly_count;
  const totalUnits = metrics?.total_sales;

  const isProfitable = totalProfit !== undefined ? totalProfit >= 0 : true;

  const riskBadge = () => {
    if (riskScore === undefined || !riskLevel) return null;
    if (riskLevel === "HIGH") {
      return (
        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200">
          HIGH RISK
        </span>
      );
    }
    if (riskLevel === "MEDIUM") {
      return (
        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
          MEDIUM RISK
        </span>
      );
    }
    return (
      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
        LOW RISK
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Group 1: Financial Performance */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">
            Financial Performance
          </h2>
          <span className="text-[11px] text-slate-400">
            {hasData ? "Aggregated from active CSV records" : "No dataset loaded"}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* 1. Total Revenue */}
          <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs transition-all hover:border-slate-300">
            <div className="flex items-center justify-between text-slate-500 mb-2.5">
              <span className="text-xs font-semibold text-slate-600">
                Total Revenue
              </span>
              <div className="p-2 rounded-lg bg-blue-50 text-blue-600">
                <IndianRupee className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-bold tracking-tight text-slate-900">
              {hasData ? formatINR(totalRevenue) : "—"}
            </div>
            <p className="text-[11px] text-slate-400 mt-1.5">
              {hasData ? "Sum of all recorded transaction revenue" : "Awaiting CSV ingestion"}
            </p>
          </div>

          {/* 2. Total Expenses */}
          <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs transition-all hover:border-slate-300">
            <div className="flex items-center justify-between text-slate-500 mb-2.5">
              <span className="text-xs font-semibold text-slate-600">
                Total Expenses
              </span>
              <div className="p-2 rounded-lg bg-slate-100 text-slate-600">
                <CreditCard className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-bold tracking-tight text-slate-900">
              {hasData ? formatINR(totalExpense) : "—"}
            </div>
            <p className="text-[11px] text-slate-400 mt-1.5">
              {hasData ? "Sum of operational and cost line items" : "Awaiting CSV ingestion"}
            </p>
          </div>

          {/* 3. Net Profit */}
          <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs transition-all hover:border-slate-300">
            <div className="flex items-center justify-between text-slate-500 mb-2.5">
              <span className="text-xs font-semibold text-slate-600">
                Net Profit
              </span>
              <div
                className={`p-2 rounded-lg ${
                  hasData
                    ? isProfitable
                      ? "bg-emerald-50 text-emerald-600"
                      : "bg-rose-50 text-rose-600"
                    : "bg-slate-100 text-slate-400"
                }`}
              >
                {isProfitable ? (
                  <TrendingUp className="w-4 h-4" />
                ) : (
                  <TrendingDown className="w-4 h-4" />
                )}
              </div>
            </div>
            <div
              className={`text-2xl font-bold tracking-tight ${
                hasData
                  ? isProfitable
                    ? "text-emerald-700"
                    : "text-rose-700"
                  : "text-slate-900"
              }`}
            >
              {hasData ? formatINR(totalProfit) : "—"}
            </div>
            <p className="text-[11px] text-slate-400 mt-1.5">
              {hasData
                ? isProfitable
                  ? "Revenue minus Expense (Net Gain)"
                  : "Revenue minus Expense (Operating Loss)"
                : "Awaiting CSV ingestion"}
            </p>
          </div>

          {/* 4. Profit Margin */}
          <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs transition-all hover:border-slate-300">
            <div className="flex items-center justify-between text-slate-500 mb-2.5">
              <span className="text-xs font-semibold text-slate-600">
                Profit Margin
              </span>
              <div className="p-2 rounded-lg bg-indigo-50 text-indigo-600">
                <Percent className="w-4 h-4" />
              </div>
            </div>
            <div
              className={`text-2xl font-bold tracking-tight ${
                hasData
                  ? (profitMargin ?? 0) >= 0
                    ? "text-slate-900"
                    : "text-rose-700"
                  : "text-slate-900"
              }`}
            >
              {hasData
                ? totalRevenue && totalRevenue > 0
                  ? `${profitMargin?.toFixed(2)}%`
                  : "0.00%"
                : "—"}
            </div>
            <p className="text-[11px] text-slate-400 mt-1.5">
              {hasData
                ? (profitMargin ?? 0) >= 20
                  ? "Healthy margin ratio (>= 20%)"
                  : (profitMargin ?? 0) > 0
                  ? "Moderate operating margin"
                  : "Negative margin warning"
                : "Net Profit / Total Revenue × 100"}
            </p>
          </div>
        </div>
      </div>

      {/* Group 2: Prediction, Risk & Operations */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">
            Prediction, Risk & Operations
          </h2>
          <span className="text-[11px] text-slate-400">
            {hasData ? "Backend ML models & operational records" : "Standby"}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* 5. Predicted Profit */}
          <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs transition-all hover:border-slate-300">
            <div className="flex items-center justify-between text-slate-500 mb-2.5">
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-semibold text-slate-600">
                  Predicted Profit
                </span>
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 uppercase">
                  ML
                </span>
              </div>
              <div className="p-2 rounded-lg bg-blue-50 text-blue-600">
                <BrainCircuit className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-bold tracking-tight text-slate-900">
              {hasData && predictedProfit !== null && predictedProfit !== undefined
                ? formatINR(predictedProfit)
                : "—"}
            </div>
            <p className="text-[11px] text-slate-400 mt-1.5">
              Random Forest regression estimate based on unit features
            </p>
          </div>

          {/* 6. Risk Score */}
          <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs transition-all hover:border-slate-300">
            <div className="flex items-center justify-between text-slate-500 mb-2.5">
              <span className="text-xs font-semibold text-slate-600">
                Risk Score
              </span>
              <div className="flex items-center gap-1.5">
                {hasData && riskBadge()}
                <div className="p-2 rounded-lg bg-amber-50 text-amber-600">
                  <ShieldAlert className="w-4 h-4" />
                </div>
              </div>
            </div>
            <div className="text-2xl font-bold tracking-tight text-slate-900">
              {hasData && riskScore !== undefined ? `${riskScore} / 100` : "—"}
            </div>
            <p className="text-[11px] text-slate-400 mt-1.5">
              {hasData
                ? `Scored from anomalies, profit margin tiers, and profit projections`
                : "Multi-factor composite (0–100)"}
            </p>
          </div>

          {/* 7. Anomalies Detected */}
          <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs transition-all hover:border-slate-300">
            <div className="flex items-center justify-between text-slate-500 mb-2.5">
              <span className="text-xs font-semibold text-slate-600">
                Anomalies Detected
              </span>
              <div className="p-2 rounded-lg bg-slate-100 text-slate-600">
                <Search className="w-4 h-4" />
              </div>
            </div>
            <div
              className={`text-2xl font-bold tracking-tight ${
                hasData && (anomalyCount ?? 0) > 0 ? "text-amber-700" : "text-slate-900"
              }`}
            >
              {hasData && anomalyCount !== undefined
                ? `${anomalyCount} ${anomalyCount === 1 ? "Record" : "Records"}`
                : "—"}
            </div>
            <p className="text-[11px] text-slate-400 mt-1.5">
              Flagged by Isolation Forest for review; not confirmed fraud or loss
            </p>
          </div>

          {/* 8. Total Units Sold */}
          <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs transition-all hover:border-slate-300">
            <div className="flex items-center justify-between text-slate-500 mb-2.5">
              <span className="text-xs font-semibold text-slate-600">
                Total Units Sold
              </span>
              <div className="p-2 rounded-lg bg-emerald-50 text-emerald-600">
                <Package className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-bold tracking-tight text-slate-900">
              {hasData && totalUnits !== undefined
                ? `${totalUnits.toLocaleString()} Units`
                : "—"}
            </div>
            <p className="text-[11px] text-slate-400 mt-1.5">
              {hasData && totalUnits !== undefined
                ? "Sum of Quantity across processed rows"
                : "Quantity column required"}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}