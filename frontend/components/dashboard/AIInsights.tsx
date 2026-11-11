"use client";

import React from "react";
import {
  Lightbulb,
  CheckCircle2,
  AlertTriangle,
  Info,
  Target,
  Sparkles,
  TrendingUp,
  Package,
} from "lucide-react";
import { UploadResult, FullDatasetData, formatINR } from "./types";

interface AIInsightsProps {
  uploadResult: UploadResult | null;
  fullDataset?: FullDatasetData | null;
  isLoading?: boolean;
}

export default function AIInsights({
  uploadResult,
  isLoading = false,
}: AIInsightsProps) {
  const analytics = uploadResult?.analytics;
  const metrics = uploadResult?.metrics;

  const backendInsights: string[] = analytics?.insights || [];
  const backendRecommendations: string[] = analytics?.recommendations || [];
  const productPerformance = analytics?.product_performance || [];

  const hasInsights = backendInsights.length > 0;
  const hasRecommendations = backendRecommendations.length > 0;
  const hasContent = hasInsights || hasRecommendations || (metrics !== undefined && metrics !== null);

  const businessStatus =
    uploadResult?.business_status ||
    (metrics
      ? metrics.total_profit >= 0
        ? "Healthy & Profitable"
        : "Operating at a Loss"
      : "");

  const isProfitable = metrics ? metrics.total_profit >= 0 : true;

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 p-5 sm:p-6 shadow-xs space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-blue-50 text-blue-600">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
              AI Analytics Agent
            </span>
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">
              Business Intelligence & Strategic Insights
            </h2>
          </div>
        </div>

        {uploadResult && businessStatus && (
          <div className="flex items-center gap-2 self-start sm:self-auto">
            <span
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${
                isProfitable
                  ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                  : "bg-rose-50 text-rose-800 border-rose-200"
              }`}
            >
              {isProfitable ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              ) : (
                <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
              )}
              <span>{businessStatus}</span>
            </span>
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="py-10 text-center space-y-2 text-slate-400">
          <div className="w-6 h-6 mx-auto border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs font-medium text-slate-500">
            Analyzing financial records with AI Analytics Agent...
          </p>
        </div>
      ) : !hasContent ? (
        <div className="py-10 text-center space-y-2 bg-slate-50/60 rounded-lg border border-dashed border-slate-200 p-6">
          <div className="w-10 h-10 mx-auto rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
            <Lightbulb className="w-5 h-5" />
          </div>
          <h3 className="text-sm font-semibold text-slate-800">
            Awaiting Ingested Financial Data
          </h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Upload transaction records above to generate verified business insights and strategic AI recommendations.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Section 1: Backend Insights */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1.5">
                <Lightbulb className="w-3.5 h-3.5 text-blue-600" />
                <span>Executive Business Insights</span>
              </h3>
              <span className="text-[11px] text-slate-400 font-medium">
                {backendInsights.length} Observations Generated
              </span>
            </div>

            {hasInsights ? (
              <div className="grid grid-cols-1 gap-2.5">
                {backendInsights.map((insight, idx) => {
                  const lower = insight.toLowerCase();
                  const isWarning =
                    lower.includes("loss") ||
                    lower.includes("deficit") ||
                    lower.includes("decreased") ||
                    lower.includes("unprofitable") ||
                    lower.includes("risk");
                  const isPositive =
                    lower.includes("profitable") ||
                    lower.includes("increased") ||
                    lower.includes("strong") ||
                    lower.includes("top performing");

                  return (
                    <div
                      key={idx}
                      className={`p-3.5 rounded-lg border transition-colors flex items-start gap-3 ${
                        isWarning
                          ? "bg-amber-50/50 border-amber-200/80 hover:bg-amber-50/80"
                          : isPositive
                          ? "bg-emerald-50/40 border-emerald-200/70 hover:bg-emerald-50/70"
                          : "bg-slate-50/80 border-slate-200 hover:bg-slate-50"
                      }`}
                    >
                      <div className="mt-0.5 shrink-0">
                        {isWarning ? (
                          <AlertTriangle className="w-4 h-4 text-amber-600" />
                        ) : isPositive ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                        ) : (
                          <TrendingUp className="w-4 h-4 text-blue-600" />
                        )}
                      </div>
                      <div className="flex-1 text-xs text-slate-800 leading-relaxed font-medium">
                        {insight}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600">
                {metrics && metrics.total_profit >= 0
                  ? `Operations are profitable with net income of ${formatINR(metrics.total_profit)} and an operating margin of ${metrics.profit_margin.toFixed(1)}%.`
                  : metrics
                  ? `Business is operating at a net deficit of ${formatINR(metrics?.total_profit ?? 0)}.`
                  : "No insights generated for this dataset."}
              </div>
            )}
          </div>

          {/* Section 2: Strategic Recommendations */}
          <div className="space-y-3 pt-2 border-t border-slate-100">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1.5">
                <Target className="w-3.5 h-3.5 text-indigo-600" />
                <span>Strategic Leadership Recommendations</span>
              </h3>
              <span className="text-[11px] text-slate-400 font-medium">
                {backendRecommendations.length} Action Items
              </span>
            </div>

            {hasRecommendations ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {backendRecommendations.map((rec, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-lg bg-indigo-50/40 border border-indigo-100 hover:bg-indigo-50/70 transition-colors flex items-start gap-2.5"
                  >
                    <div className="p-1 rounded bg-indigo-100 text-indigo-700 shrink-0 mt-0.5">
                      <Target className="w-3.5 h-3.5" />
                    </div>
                    <p className="text-xs text-slate-800 leading-relaxed font-medium">
                      {rec}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-500">
                Review operating cost ratios and product margin distribution to identify margin expansion opportunities.
              </div>
            )}
          </div>

          {/* Section 3: Product Profitability Breakdown (if available) */}
          {productPerformance.length > 0 && (
            <div className="space-y-3 pt-2 border-t border-slate-100">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1.5">
                  <Package className="w-3.5 h-3.5 text-slate-700" />
                  <span>Product Profitability Performance</span>
                </h3>
                <span className="text-[11px] text-slate-400 font-medium">
                  {productPerformance.length} Categories Analyzed
                </span>
              </div>

              <div className="overflow-x-auto rounded-lg border border-slate-200">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                    <tr>
                      <th className="py-2.5 px-3">Product / Category</th>
                      <th className="py-2.5 px-3 text-right">Revenue</th>
                      <th className="py-2.5 px-3 text-right">Expense</th>
                      <th className="py-2.5 px-3 text-right">Net Profit</th>
                      <th className="py-2.5 px-3 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {productPerformance.map((prod, idx) => {
                      const isProfit = prod.profit >= 0;
                      return (
                        <tr key={idx} className="hover:bg-slate-50/70 transition-colors">
                          <td className="py-2.5 px-3 font-medium text-slate-900">
                            {prod.product}
                          </td>
                          <td className="py-2.5 px-3 text-right text-slate-700">
                            {formatINR(prod.revenue)}
                          </td>
                          <td className="py-2.5 px-3 text-right text-slate-700">
                            {formatINR(prod.expense)}
                          </td>
                          <td
                            className={`py-2.5 px-3 text-right font-semibold ${
                              isProfit ? "text-emerald-700" : "text-rose-700"
                            }`}
                          >
                            {formatINR(prod.profit)}
                          </td>
                          <td className="py-2.5 px-3 text-center">
                            <span
                              className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                                isProfit
                                  ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                  : "bg-rose-50 text-rose-700 border border-rose-200"
                              }`}
                            >
                              {isProfit ? "Profitable" : "Deficit"}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Footer Metadata */}
          <div className="pt-2 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-[11px] text-slate-400 border-t border-slate-100">
            <span className="flex items-center gap-1">
              <Info className="w-3 h-3 text-slate-400" />
              <span>Multi-tier LLM reasoning (Gemini / Groq / Rules) • Ground-truth Pandas financial metrics</span>
            </span>
            <span>Privacy-preserving • Zero raw row transmission</span>
          </div>
        </div>
      )}
    </div>
  );
}
