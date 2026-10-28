"use client";

import React from "react";
import Link from "next/link";
import {
  ShieldAlert,
  ArrowRight,
  PieChart,
} from "lucide-react";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import RevenueExpenseChart from "@/components/dashboard/RevenueExpenseChart";
import AIInsights from "@/components/dashboard/AIInsights";
import { formatINR } from "@/components/dashboard/types";

export default function BusinessAnalyticsPage() {
  const { uploadResult, fullDataset, isUploading } = useDashboard();
  const metrics = uploadResult?.metrics || null;
  const hasData = !!uploadResult && !!metrics;

  const totalRev = metrics?.total_revenue || 0;
  const totalExp = metrics?.total_expense || 0;
  const totalProf = metrics?.total_profit || 0;

  const expensePct = totalRev > 0 ? Math.min(100, Math.max(0, (totalExp / totalRev) * 100)) : 0;
  const profitPct = totalRev > 0 ? Math.min(100, Math.max(0, (totalProf / totalRev) * 100)) : 0;

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
            Analytics
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Financial allocations, revenue-to-expense distribution, unit economics, and evidence-based AI insights derived from uploaded transaction records.
          </p>
        </div>

        {/* Access to Risk Intelligence subpage */}
        <Link
          href="/dashboard/risk"
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-800 text-xs font-semibold border border-amber-200/80 transition-colors self-start sm:self-auto cursor-pointer"
        >
          <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
          <span>Inspect Risk Intelligence</span>
        </Link>
      </div>

      {!hasData && (
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200/90 text-sm">
          <div>
            <span className="font-semibold text-slate-800 block">
              Awaiting Dataset Ingestion
            </span>
            <span className="text-xs text-slate-500">
              Upload a business CSV from the Dashboard to evaluate financial distributions, chart trends, and synthesize AI insights.
            </span>
          </div>

          <Link
            href="/dashboard"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition-colors shrink-0"
          >
            <span>Go to Dashboard</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}

      {/* Primary Revenue vs Expense Chart */}
      <section aria-labelledby="chart-heading">
        <RevenueExpenseChart
          fullDataset={fullDataset}
          isLoading={isUploading}
        />
      </section>

      {/* Financial Ratio Breakdown */}
      {metrics && (
        <section aria-labelledby="ratios-heading" className="space-y-3">
          <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider">
            Financial Allocation & Unit Economics
          </h2>

          <div className="bg-white rounded-xl border border-slate-200/90 p-5 sm:p-6 shadow-xs space-y-5">
            <div>
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-semibold text-slate-700 mb-2">
                <span className="flex items-center gap-1.5">
                  <PieChart className="w-4 h-4 text-blue-600" />
                  <span>Revenue Allocation: Expenditure vs Net Margin</span>
                </span>
                <span className="text-slate-500">
                  Gross Base: {formatINR(totalRev)}
                </span>
              </div>

              <div className="w-full h-3.5 bg-slate-100 rounded-full overflow-hidden flex">
                <div
                  className="bg-amber-500 h-full transition-all duration-500"
                  style={{ width: `${expensePct}%` }}
                  title={`Expense: ${expensePct.toFixed(1)}%`}
                />
                <div
                  className="bg-emerald-600 h-full transition-all duration-500"
                  style={{ width: `${profitPct}%` }}
                  title={`Profit: ${profitPct.toFixed(1)}%`}
                />
              </div>

              <div className="flex flex-wrap items-center justify-between gap-4 text-xs font-medium mt-2.5">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-sm bg-amber-500" />
                  <span className="text-slate-600">
                    Expenditure: {formatINR(totalExp)} ({expensePct.toFixed(1)}%)
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-sm bg-emerald-600" />
                  <span className="text-slate-600">
                    Net Profit: {formatINR(totalProf)} ({profitPct.toFixed(1)}%)
                  </span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4 border-t border-slate-100">
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200/80">
                <span className="text-[10px] font-medium text-slate-400 block uppercase">
                  Avg Revenue / Record
                </span>
                <span className="text-sm font-bold text-slate-900 mt-0.5 block">
                  {formatINR(metrics.average_revenue)}
                </span>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200/80">
                <span className="text-[10px] font-medium text-slate-400 block uppercase">
                  Avg Expense / Record
                </span>
                <span className="text-sm font-bold text-slate-900 mt-0.5 block">
                  {formatINR(metrics.average_expense)}
                </span>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200/80">
                <span className="text-[10px] font-medium text-slate-400 block uppercase">
                  Avg Profit / Record
                </span>
                <span
                  className={`text-sm font-bold mt-0.5 block ${
                    totalProf >= 0 ? "text-emerald-700" : "text-rose-700"
                  }`}
                >
                  {formatINR(metrics.average_profit)}
                </span>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200/80">
                <span className="text-[10px] font-medium text-slate-400 block uppercase">
                  Total Volume Sold
                </span>
                <span className="text-sm font-bold text-slate-900 mt-0.5 block">
                  {metrics.total_sales.toLocaleString()} Units
                </span>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* AI Insights Section */}
      <section aria-labelledby="ai-insights-heading">
        <AIInsights
          uploadResult={uploadResult}
          fullDataset={fullDataset}
          isLoading={isUploading}
        />
      </section>
    </div>
  );
}
