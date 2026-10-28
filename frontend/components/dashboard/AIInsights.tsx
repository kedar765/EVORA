"use client";

import React, { useMemo } from "react";
import {
  Lightbulb,
  ArrowUpRight,
  Info,
} from "lucide-react";
import { UploadResult, FullDatasetData, formatINR } from "./types";

interface AIInsightsProps {
  uploadResult: UploadResult | null;
  fullDataset: FullDatasetData | null;
  isLoading?: boolean;
}

interface ActionableInsight {
  category: "Revenue" | "Expense" | "Profitability" | "Risk" | "Portfolio";
  finding: string;
  evidence: string;
  whyItMatters: string;
  suggestedAction?: string;
  sentiment: "positive" | "warning" | "neutral";
}

export default function AIInsights({
  uploadResult,
  fullDataset,
  isLoading = false,
}: AIInsightsProps) {
  const insights = useMemo<ActionableInsight[]>(() => {
    if (!uploadResult || !uploadResult.metrics) return [];

    const metrics = uploadResult.metrics;
    const records = fullDataset?.records || [];
    const headers = fullDataset?.headers || [];
    const list: ActionableInsight[] = [];

    const totalRev = metrics.total_revenue;
    const totalExp = metrics.total_expense;
    const totalProfit = metrics.total_profit;
    const profitMargin = metrics.profit_margin;
    const anomalyCount = uploadResult.anomaly_count ?? 0;

    // Detect column names
    const productCol = headers.find((h) => /^product|category|item|service|segment$/i.test(h.trim()));
    const revCol = headers.find((h) => /^revenue|sales|income$/i.test(h.trim())) || "Revenue";
    const expCol = headers.find((h) => /^expense|cost|expenditure$/i.test(h.trim())) || "Expense";

    // 1. Highest revenue category or product
    if (productCol && records.length > 0) {
      const productRevMap = new Map<string, { revenue: number; count: number }>();
      for (const row of records) {
        const prod = String(row[productCol] || "Uncategorized");
        const rev = Number(row[revCol]) || 0;
        const cur = productRevMap.get(prod) || { revenue: 0, count: 0 };
        cur.revenue += rev;
        cur.count += 1;
        productRevMap.set(prod, cur);
      }

      let topProd = "";
      let topRev = -1;
      let topCount = 0;
      productRevMap.forEach((val, prod) => {
        if (val.revenue > topRev) {
          topRev = val.revenue;
          topProd = prod;
          topCount = val.count;
        }
      });

      if (topProd && topRev > 0 && totalRev > 0) {
        const sharePct = ((topRev / totalRev) * 100).toFixed(1);
        list.push({
          category: "Revenue",
          finding: `${topProd} is your primary revenue generator.`,
          evidence: `Generated ${formatINR(topRev)} (${sharePct}% of total revenue across ${topCount} ${topCount === 1 ? "record" : "records"}).`,
          whyItMatters: "Heavy reliance on a single category represents core strength but also operational concentration risk.",
          suggestedAction: "Ensure supply chain resilience for this category while scaling secondary product lines.",
          sentiment: "positive",
        });
      }
    } else if (totalRev > 0) {
      list.push({
        category: "Revenue",
        finding: `Total gross receipts reached ${formatINR(totalRev)}.`,
        evidence: `Aggregated across ${uploadResult.rows_processed} transaction records with an average of ${formatINR(metrics.average_revenue)} per record.`,
        whyItMatters: "Establishes baseline commercial scale for assessing operating overhead and volume trends.",
        suggestedAction: "Monitor average revenue per transaction to evaluate potential basket size increases.",
        sentiment: "neutral",
      });
    }

    // 2. Expense concentration
    if (totalRev > 0) {
      const costRatio = (totalExp / totalRev) * 100;
      if (costRatio > 70) {
        list.push({
          category: "Expense",
          finding: `Operating expense concentration is high at ${costRatio.toFixed(1)}% of revenue.`,
          evidence: `Total expenditure of ${formatINR(totalExp)} against ${formatINR(totalRev)} in receipts.`,
          whyItMatters: "High cost-to-revenue ratios leave minimal buffer against demand dips or supplier price increases.",
          suggestedAction: "Conduct an expense audit on unit procurement costs and identify renegotiation targets.",
          sentiment: "warning",
        });
      } else {
        list.push({
          category: "Expense",
          finding: `Controlled cost structure with operating expense at ${costRatio.toFixed(1)}% of revenue.`,
          evidence: `Total expenditure is ${formatINR(totalExp)}, leaving ${(100 - costRatio).toFixed(1)}% gross operating headroom.`,
          whyItMatters: "Low overhead-to-revenue ratio protects cash flow and enables strategic reinvestment.",
          suggestedAction: "Maintain existing procurement agreements and evaluate volume discounting.",
          sentiment: "positive",
        });
      }
    }

    // 3. Profit margin & bottom-line health
    if (profitMargin < 0) {
      list.push({
        category: "Profitability",
        finding: "Business is operating at a net loss.",
        evidence: `Net deficit of ${formatINR(totalProfit)} with a profit margin of ${profitMargin.toFixed(1)}%.`,
        whyItMatters: "Operational costs exceed gross income, eroding working capital over time.",
        suggestedAction: "Immediately pause discretionary expenditure and adjust pricing tiers on loss-making transactions.",
        sentiment: "warning",
      });
    } else if (profitMargin >= 20) {
      list.push({
        category: "Profitability",
        finding: `Strong net profitability with a ${profitMargin.toFixed(1)}% operating margin.`,
        evidence: `Net retained profit of ${formatINR(totalProfit)} on ${formatINR(totalRev)} revenue.`,
        whyItMatters: "Profit margin significantly exceeds SaaS and commercial baseline benchmarks of 15-20%.",
        suggestedAction: "Evaluate reinvesting surplus earnings into expansion or customer acquisition.",
        sentiment: "positive",
      });
    } else {
      list.push({
        category: "Profitability",
        finding: `Moderate net profitability at ${profitMargin.toFixed(1)}% margin.`,
        evidence: `Net profit is ${formatINR(totalProfit)} against ${formatINR(totalRev)} in receipts.`,
        whyItMatters: "Operations are profitable but margins are vulnerable to minor cost escalations.",
        suggestedAction: "Target a 3-5% margin improvement through selective price increases on top-selling items.",
        sentiment: "neutral",
      });
    }

    // 4. Products or categories with low or negative profitability
    if (productCol && records.length > 0) {
      const lossProducts: { name: string; loss: number }[] = [];
      const productMap = new Map<string, { rev: number; exp: number }>();

      for (const row of records) {
        const prod = String(row[productCol] || "Uncategorized");
        const rev = Number(row[revCol]) || 0;
        const exp = Number(row[expCol]) || 0;
        const cur = productMap.get(prod) || { rev: 0, exp: 0 };
        cur.rev += rev;
        cur.exp += exp;
        productMap.set(prod, cur);
      }

      productMap.forEach((vals, prod) => {
        const diff = vals.rev - vals.exp;
        if (diff < 0) {
          lossProducts.push({ name: prod, loss: Math.abs(diff) });
        }
      });

      if (lossProducts.length > 0) {
        const topLoss = lossProducts[0];
        list.push({
          category: "Portfolio",
          finding: `${topLoss.name} is operating at negative net profitability.`,
          evidence: `Net loss of ${formatINR(-topLoss.loss)} recorded for this category.`,
          whyItMatters: "Unprofitable products dilute gains generated by profitable product lines.",
          suggestedAction: "Re-evaluate unit pricing or assess if high delivery/production costs can be reduced.",
          sentiment: "warning",
        });
      }
    }

    // 5. Statistical anomalies from Isolation Forest
    if (anomalyCount > 0) {
      list.push({
        category: "Risk",
        finding: `${anomalyCount} statistical ${anomalyCount === 1 ? "anomaly was" : "anomalies were"} detected by Isolation Forest.`,
        evidence: `Flagged outlier records based on multi-variable quantity and cost relationships.`,
        whyItMatters: "Anomalous records represent statistical deviations requiring human verification; they do not automatically denote fraud.",
        suggestedAction: "Review flagged entries in the Risk Intelligence audit log below to confirm entry accuracy.",
        sentiment: "warning",
      });
    } else {
      list.push({
        category: "Risk",
        finding: "No operational anomalies identified in transaction records.",
        evidence: `All ${uploadResult.rows_processed} records fall within standard statistical distribution bands.`,
        whyItMatters: "Operational consistency reduces pricing volatility and transaction uncertainty.",
        suggestedAction: "Continue standard periodic reconciliation schedules.",
        sentiment: "positive",
      });
    }

    return list.slice(0, 5); // Return up to 5 highest-value insights
  }, [uploadResult, fullDataset]);

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 p-5 sm:p-6 shadow-xs space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-blue-50 text-blue-600">
            <Lightbulb className="w-4 h-4" />
          </div>
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Evidence-Based Intelligence
            </span>
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">
              AI Insights
            </h2>
          </div>
        </div>

        <span className="text-[11px] font-medium text-slate-400">
          Derived strictly from verified dataset calculations
        </span>
      </div>

      {isLoading ? (
        <div className="py-10 text-center space-y-2 text-slate-400">
          <div className="w-6 h-6 mx-auto border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs font-medium text-slate-500">
            Synthesizing findings from uploaded financial records...
          </p>
        </div>
      ) : insights.length === 0 ? (
        <div className="py-10 text-center space-y-2 bg-slate-50/60 rounded-lg border border-dashed border-slate-200 p-6">
          <div className="w-10 h-10 mx-auto rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
            <Lightbulb className="w-5 h-5" />
          </div>
          <h3 className="text-sm font-semibold text-slate-800">
            No Insights Generated
          </h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Upload transaction records above to generate actionable business findings with supporting metrics and suggested actions.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {insights.map((item, idx) => (
            <div
              key={idx}
              className="p-4 rounded-lg bg-slate-50/70 border border-slate-200/80 hover:bg-slate-50 transition-colors space-y-2.5"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      item.sentiment === "positive"
                        ? "bg-emerald-500"
                        : item.sentiment === "warning"
                        ? "bg-amber-500"
                        : "bg-blue-500"
                    }`}
                  />
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    {item.category}
                  </span>
                </div>

                <span className="text-[11px] font-medium text-slate-600 bg-white px-2 py-0.5 rounded border border-slate-200/70 shadow-2xs">
                  {item.evidence}
                </span>
              </div>

              <div>
                <h4 className="text-sm font-bold text-slate-900 leading-snug">
                  {item.finding}
                </h4>
                <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                  <strong className="font-semibold text-slate-700">Why it matters:</strong> {item.whyItMatters}
                </p>
              </div>

              {item.suggestedAction && (
                <div className="pt-2 border-t border-slate-200/60 flex items-start gap-1.5 text-xs text-slate-700">
                  <ArrowUpRight className="w-3.5 h-3.5 text-blue-600 shrink-0 mt-0.5" />
                  <span>
                    <strong className="font-semibold text-blue-700">Suggested Action:</strong> {item.suggestedAction}
                  </span>
                </div>
              )}
            </div>
          ))}

          <div className="pt-2 flex items-center justify-between text-[11px] text-slate-400">
            <span className="flex items-center gap-1">
              <Info className="w-3 h-3 text-slate-400" />
              <span>Rule-based diagnostic reasoning • No generative AI hallucinations</span>
            </span>
            <span>Total Insights: {insights.length}</span>
          </div>
        </div>
      )}
    </div>
  );
}
