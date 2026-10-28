"use client";

import React from "react";
import Link from "next/link";
import {
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Info,
  SlidersHorizontal,
} from "lucide-react";
import { UploadResult, FullDatasetData, formatINR } from "./types";

interface RiskDetailsCardProps {
  uploadResult: UploadResult | null;
  fullDataset?: FullDatasetData | null;
}

export default function RiskDetailsCard({
  uploadResult,
  fullDataset,
}: RiskDetailsCardProps) {
  const hasData = !!uploadResult;
  const riskScore = uploadResult?.risk_score ?? 0;
  const riskLevel = uploadResult?.risk_level?.toUpperCase() || "LOW";
  const anomalyCount = uploadResult?.anomaly_count ?? 0;
  const reasons = uploadResult?.risk_analysis?.reasons || [];
  const anomalyIndices = uploadResult?.anomaly_indices || [];

  const isHigh = riskLevel === "HIGH";
  const isMedium = riskLevel === "MEDIUM";

  const badgeClass = isHigh
    ? "bg-rose-50 text-rose-800 border-rose-200"
    : isMedium
    ? "bg-amber-50 text-amber-800 border-amber-200"
    : "bg-emerald-50 text-emerald-800 border-emerald-200";

  const progressBarColor = isHigh
    ? "bg-rose-600"
    : isMedium
    ? "bg-amber-500"
    : "bg-emerald-600";

  // Identify flagged records from the actual dataset
  const records = fullDataset?.records || [];
  const headers = fullDataset?.headers || [];
  const dateCol = headers.find((h) => /^date|timestamp|day$/i.test(h.trim()));
  const productCol = headers.find((h) => /^product|category|item$/i.test(h.trim()));
  const revCol = headers.find((h) => /^revenue|sales$/i.test(h.trim())) || "Revenue";
  const expCol = headers.find((h) => /^expense|cost$/i.test(h.trim())) || "Expense";
  const qtyCol = headers.find((h) => /^quantity|units$/i.test(h.trim())) || "Quantity";

  const flaggedRows = records
    .map((row, idx) => {
      const isAnomaly = anomalyIndices.includes(idx);
      const rev = Number(row[revCol]) || 0;
      const exp = Number(row[expCol]) || 0;
      const isLoss = rev < exp;

      if (isAnomaly || isLoss) {
        return {
          rowNum: idx + 1,
          label: (dateCol && row[dateCol]) || (productCol && row[productCol]) || `Record ${idx + 1}`,
          quantity: row[qtyCol] ?? "—",
          revenue: rev,
          expense: exp,
          profit: rev - exp,
          reason: isAnomaly && isLoss
            ? "Isolation Forest Outlier & Operating Loss"
            : isAnomaly
            ? "Statistical Isolation Forest Outlier"
            : "Negative Margin (Expense > Revenue)",
        };
      }
      return null;
    })
    .filter(Boolean);

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 p-5 sm:p-6 shadow-xs space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-amber-50 text-amber-600">
            <ShieldAlert className="w-4 h-4" />
          </div>
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Risk Diagnostics
            </span>
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">
              Risk Intelligence & Flagged Records
            </h2>
          </div>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-auto">
          {hasData && (
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${badgeClass}`}>
              {riskLevel} RISK
            </span>
          )}
          <Link
            href="/dashboard/risk"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-200/80 transition-colors"
          >
            <SlidersHorizontal className="w-3.5 h-3.5 text-slate-500" />
            <span>Full Risk Diagnostics</span>
          </Link>
        </div>
      </div>

      {!hasData ? (
        <div className="py-8 text-center space-y-2 bg-slate-50/60 rounded-lg border border-dashed border-slate-200 p-6">
          <div className="w-10 h-10 mx-auto rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <h3 className="text-sm font-semibold text-slate-800">
            No Risk Assessment Generated
          </h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Upload transaction records to evaluate composite risk scores (0–100) and scan for statistical outliers.
          </p>
        </div>
      ) : (
        <div className="space-y-5">
          {/* Top Score Matrix */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Risk Score */}
            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200/80 space-y-2">
              <span className="text-xs text-slate-500 font-medium block">
                Composite Risk Score
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold text-slate-900">
                  {riskScore}
                </span>
                <span className="text-xs text-slate-400 font-medium">/ 100</span>
              </div>
              <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${progressBarColor}`}
                  style={{ width: `${Math.min(100, Math.max(0, riskScore))}%` }}
                />
              </div>
              <p className="text-[11px] text-slate-500 leading-tight pt-1">
                Based on anomaly presence (+60 or +10), profit margin brackets, and forecasted yields.
              </p>
            </div>

            {/* Anomaly Detection Status */}
            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200/80 space-y-2">
              <span className="text-xs text-slate-500 font-medium block">
                Statistical Anomaly Scan
              </span>
              <div className="flex items-center gap-2">
                {anomalyCount > 0 ? (
                  <>
                    <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
                    <span className="text-lg font-bold text-slate-900">
                      {anomalyCount} {anomalyCount === 1 ? "Record Flagged" : "Records Flagged"}
                    </span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                    <span className="text-lg font-bold text-slate-900">
                      Normal Distribution
                    </span>
                  </>
                )}
              </div>
              <p className="text-[11px] text-slate-500 leading-tight">
                Model: Isolation Forest. Outliers represent atypical feature proportions and require operational review.
              </p>
            </div>

            {/* Backend Risk Reasons */}
            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200/80 space-y-2">
              <span className="text-xs text-slate-500 font-medium block">
                Evaluated Risk Triggers
              </span>
              <div className="space-y-1.5 text-xs text-slate-700">
                {reasons.length > 0 ? (
                  reasons.map((r, i) => (
                    <div key={i} className="flex items-start gap-1.5">
                      <div className="w-1.5 h-1.5 rounded-full bg-slate-400 mt-1.5 shrink-0" />
                      <span className="leading-tight">{r}</span>
                    </div>
                  ))
                ) : (
                  <span className="text-slate-400 italic">No specific risk triggers tripped.</span>
                )}
              </div>
            </div>
          </div>

          {/* Flagged Records Table */}
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Flagged Records for Operational Review
              </h3>
              <span className="text-[11px] text-slate-500">
                {flaggedRows.length} {flaggedRows.length === 1 ? "record requires inspection" : "records require inspection"}
              </span>
            </div>

            {flaggedRows.length > 0 ? (
              <div className="overflow-x-auto custom-scrollbar border border-slate-200 rounded-lg">
                <table className="min-w-full divide-y divide-slate-200 text-xs text-left">
                  <thead className="bg-slate-50 font-semibold text-slate-700">
                    <tr>
                      <th className="px-3.5 py-2.5 w-12 text-slate-400">#</th>
                      <th className="px-3.5 py-2.5">Identifier</th>
                      <th className="px-3.5 py-2.5">Quantity</th>
                      <th className="px-3.5 py-2.5">Revenue</th>
                      <th className="px-3.5 py-2.5">Expense</th>
                      <th className="px-3.5 py-2.5">Net Profit</th>
                      <th className="px-3.5 py-2.5">Diagnostic Flag</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 bg-white">
                    {flaggedRows.map((r, i) => (
                      <tr key={i} className="hover:bg-slate-50/70">
                        <td className="px-3.5 py-2 text-slate-400 font-mono text-[11px]">
                          {r?.rowNum}
                        </td>
                        <td className="px-3.5 py-2 font-medium text-slate-900">
                          {String(r?.label)}
                        </td>
                        <td className="px-3.5 py-2 text-slate-700">
                          {String(r?.quantity)}
                        </td>
                        <td className="px-3.5 py-2 text-slate-700">
                          {formatINR(r?.revenue)}
                        </td>
                        <td className="px-3.5 py-2 text-slate-700">
                          {formatINR(r?.expense)}
                        </td>
                        <td className="px-3.5 py-2">
                          <span
                            className={`font-semibold ${
                              (r?.profit ?? 0) >= 0 ? "text-emerald-700" : "text-rose-700"
                            }`}
                          >
                            {formatINR(r?.profit)}
                          </span>
                        </td>
                        <td className="px-3.5 py-2">
                          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-800 bg-amber-50 px-2 py-0.5 rounded border border-amber-200/70">
                            {r?.reason}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-4 rounded-lg bg-emerald-50/60 border border-emerald-200/70 flex items-center gap-2.5 text-xs text-emerald-800">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>
                  No flagged outlier transactions or loss-making records identified in the active dataset.
                </span>
              </div>
            )}
          </div>

          {/* Educational Governance Disclaimer */}
          <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200/80 flex items-start gap-2.5 text-xs text-slate-600">
            <Info className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
            <p className="leading-relaxed">
              <strong>Risk Intelligence Notice:</strong> Statistical anomalies indicate records whose feature proportions deviate from the dataset distribution. Unusual records warrant human verification (e.g., verifying custom bulk orders or special discounts) and are not automatically proof of fraud or commercial loss.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
