"use client";

import React, { useEffect, useState } from "react";
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
  ArrowUpRight,
  ArrowDownRight,
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

  const getRiskBadge = () => {
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
      {/* Group 1: Financial Performance KPI Cards */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-4 rounded-full bg-blue-600" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Financial Performance
            </h2>
          </div>
          <span className="text-[11px] text-slate-400 font-medium">
            {hasData ? "Aggregated from active dataset" : "Awaiting dataset ingestion"}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* 1. Total Revenue */}
          <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-xs hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 group">
            <div className="flex items-center justify-between text-slate-500 mb-3">
              <span className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
                Total Revenue
              </span>
              <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center group-hover:scale-110 transition-transform">
                <IndianRupee className="w-4 h-4" />
              </div>
            </div>

            <div className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
              {hasData ? formatINR(totalRevenue) : "—"}
            </div>

            <div className="flex items-center gap-1.5 mt-2.5 text-[11px] text-slate-500">
              {hasData ? (
                <>
                  <span className="inline-flex items-center text-emerald-600 font-semibold">
                    <ArrowUpRight className="w-3.5 h-3.5" />
                    Gross
                  </span>
                  <span>Recorded transaction volume</span>
                </>
              ) : (
                <span>Upload CSV or load demo data</span>
              )}
            </div>
          </div>

          {/* 2. Total Expenses */}
          <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-xs hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 group">
            <div className="flex items-center justify-between text-slate-500 mb-3">
              <span className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
                Total Expenses
              </span>
              <div className="w-9 h-9 rounded-xl bg-slate-100 text-slate-700 flex items-center justify-center group-hover:scale-110 transition-transform">
                <CreditCard className="w-4 h-4" />
              </div>
            </div>

            <div className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
              {hasData ? formatINR(totalExpense) : "—"}
            </div>

            <div className="flex items-center gap-1.5 mt-2.5 text-[11px] text-slate-500">
              {hasData ? (
                <>
                  <span className="inline-flex items-center text-slate-600 font-semibold">
                    Cost
                  </span>
                  <span>Operating and unit expenditures</span>
                </>
              ) : (
                <span>Pending dataset upload</span>
              )}
            </div>
          </div>

          {/* 3. Net Profit */}
          <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-xs hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 group">
            <div className="flex items-center justify-between text-slate-500 mb-3">
              <span className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
                Net Profit
              </span>
              <div
                className={`w-9 h-9 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform ${
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
              className={`text-2xl sm:text-3xl font-extrabold tracking-tight ${
                hasData
                  ? isProfitable
                    ? "text-emerald-700"
                    : "text-rose-700"
                  : "text-slate-900"
              }`}
            >
              {hasData ? formatINR(totalProfit) : "—"}
            </div>

            <div className="flex items-center gap-1.5 mt-2.5 text-[11px] text-slate-500">
              {hasData ? (
                isProfitable ? (
                  <span className="text-emerald-700 font-medium">
                    Positive Net Gain (Headroom)
                  </span>
                ) : (
                  <span className="text-rose-700 font-medium">
                    Net Operating Loss
                  </span>
                )
              ) : (
                <span>Revenue minus Expenses</span>
              )}
            </div>
          </div>

          {/* 4. Profit Margin */}
          <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-xs hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 group">
            <div className="flex items-center justify-between text-slate-500 mb-3">
              <span className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
                Profit Margin
              </span>
              <div className="w-9 h-9 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center group-hover:scale-110 transition-transform">
                <Percent className="w-4 h-4" />
              </div>
            </div>

            <div
              className={`text-2xl sm:text-3xl font-extrabold tracking-tight ${
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

            <div className="flex items-center gap-1.5 mt-2.5 text-[11px]">
              {hasData ? (
                (profitMargin ?? 0) >= 20 ? (
                  <span className="text-emerald-700 font-semibold">
                    Healthy Ratio (≥ 20%)
                  </span>
                ) : (profitMargin ?? 0) > 0 ? (
                  <span className="text-amber-700 font-semibold">
                    Moderate Margin Headroom
                  </span>
                ) : (
                  <span className="text-rose-700 font-semibold">
                    Margin Under Pressure
                  </span>
                )
              ) : (
                <span className="text-slate-500">Net Profit / Revenue × 100</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Group 2: Prediction, Risk & Operations Cards */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-4 rounded-full bg-indigo-600" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Predictions, Risk & Operations
            </h2>
          </div>
          <span className="text-[11px] text-slate-400 font-medium">
            {hasData ? "Trained ML models & operational records" : "Standby"}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* 5. Predicted Profit */}
          <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-xs hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 group">
            <div className="flex items-center justify-between text-slate-500 mb-3">
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
                  Predicted Profit
                </span>
                <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-blue-50 text-blue-700 border border-blue-200/60 uppercase">
                  ML
                </span>
              </div>
              <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center group-hover:scale-110 transition-transform">
                <BrainCircuit className="w-4 h-4" />
              </div>
            </div>

            <div className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
              {hasData && predictedProfit !== null && predictedProfit !== undefined
                ? formatINR(predictedProfit)
                : "—"}
            </div>

            <p className="text-[11px] text-slate-500 mt-2.5">
              Random Forest model regression estimate
            </p>
          </div>

          {/* 6. Risk Score */}
          <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-xs hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 group">
            <div className="flex items-center justify-between text-slate-500 mb-3">
              <span className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
                Risk Score
              </span>
              <div className="flex items-center gap-1.5">
                {hasData && getRiskBadge()}
                <div className="w-9 h-9 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center group-hover:scale-110 transition-transform">
                  <ShieldAlert className="w-4 h-4" />
                </div>
              </div>
            </div>

            <div className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
              {hasData && riskScore !== undefined ? `${riskScore} / 100` : "—"}
            </div>

            <p className="text-[11px] text-slate-500 mt-2.5">
              Multi-factor composite risk evaluation
            </p>
          </div>

          {/* 7. Anomalies Detected */}
          <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-xs hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 group">
            <div className="flex items-center justify-between text-slate-500 mb-3">
              <span className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
                Anomalies Detected
              </span>
              <div className="w-9 h-9 rounded-xl bg-slate-100 text-slate-700 flex items-center justify-center group-hover:scale-110 transition-transform">
                <Search className="w-4 h-4" />
              </div>
            </div>

            <div
              className={`text-2xl sm:text-3xl font-extrabold tracking-tight ${
                hasData && (anomalyCount ?? 0) > 0 ? "text-amber-700" : "text-slate-900"
              }`}
            >
              {hasData && anomalyCount !== undefined
                ? `${anomalyCount} ${anomalyCount === 1 ? "Record" : "Records"}`
                : "—"}
            </div>

            <p className="text-[11px] text-slate-500 mt-2.5">
              Flagged by Isolation Forest model
            </p>
          </div>

          {/* 8. Total Units Sold */}
          <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-xs hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 group">
            <div className="flex items-center justify-between text-slate-500 mb-3">
              <span className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
                Total Units Sold
              </span>
              <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center group-hover:scale-110 transition-transform">
                <Package className="w-4 h-4" />
              </div>
            </div>

            <div className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
              {hasData && totalUnits !== undefined
                ? `${totalUnits.toLocaleString("en-IN")} Units`
                : "—"}
            </div>

            <p className="text-[11px] text-slate-500 mt-2.5">
              Aggregated across all transaction rows
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
