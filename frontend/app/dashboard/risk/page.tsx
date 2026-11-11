"use client";

import React from "react";
import Link from "next/link";
import {
  ArrowRight,
  Activity,
  Search,
  BarChart3,
  Target,
} from "lucide-react";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import RiskDetailsCard from "@/components/dashboard/RiskDetailsCard";
import RiskAgent from "@/components/dashboard/RiskAgent";

export default function RiskIntelligencePage() {
  const { uploadResult, fullDataset, isUploading } = useDashboard();
  const hasData = !!uploadResult;

  const riskScore = uploadResult?.risk_score ?? 0;
  const riskLevel = uploadResult?.risk_level?.toUpperCase() || "LOW";
  const anomalyCount = uploadResult?.anomaly_count ?? 0;
  const rowsProcessed = uploadResult?.rows_processed ?? 0;
  const anomalyPct = rowsProcessed > 0 ? ((anomalyCount / rowsProcessed) * 100).toFixed(1) : "0.0";

  const isHigh = riskLevel === "HIGH";
  const isMedium = riskLevel === "MEDIUM";

  const riskResultData = uploadResult?.risk_analysis
    ? {
        success: true,
        predicted_profit: uploadResult.predicted_profit ?? 0,
        anomaly_detected: uploadResult.anomaly_detected ?? false,
        risk_score: uploadResult.risk_score ?? 0,
        risk_level: uploadResult.risk_level ?? "LOW",
        risk_analysis: uploadResult.risk_analysis,
      }
    : null;

  // Concrete operational risk recommendations based on actual findings
  const getRiskRecommendations = (): string[] => {
    if (isHigh) {
      return [
        "Conduct an immediate cost audit on the outlier transactions flagged by Isolation Forest.",
        "Implement mandatory manager sign-off for purchase orders exceeding baseline cost parameters.",
        "Review pricing tiers on loss-making product categories to restore gross operating headroom.",
        "Freeze discretionary expenditures until multi-variable transaction distribution normalizes.",
      ];
    }
    if (isMedium) {
      return [
        "Monitor flagged transaction deviations weekly to prevent margin erosion.",
        "Review supplier contracts and procurement discounts for categories exhibiting cost variance.",
        "Adjust volume discount thresholds to ensure consistent contribution margins.",
        "Perform bi-weekly reconciliation between recorded sales and operational expenses.",
      ];
    }
    return [
      "Maintain existing operational agreements and vendor procurement schedules.",
      "Preserve existing pricing buffers while exploring volume discounting to accelerate revenue.",
      "Continue periodic Isolation Forest monitoring to ensure early detection of margin drift.",
      "Reinvest surplus retained profit into high-margin product lines.",
    ];
  };

  const recommendations = getRiskRecommendations();

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold uppercase tracking-widest text-amber-600 bg-amber-50 px-2 py-0.5 rounded border border-amber-200/80">
              Section 4 • Core Intelligence
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
            Risk Intelligence
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Isolation Forest statistical anomaly detection, multi-factor risk scoring, loss exposure diagnostics, and actionable mitigation guidance.
          </p>
        </div>

        <Link
          href="/dashboard/analytics"
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold border border-slate-200/80 transition-colors self-start sm:self-auto cursor-pointer"
        >
          <BarChart3 className="w-3.5 h-3.5 text-blue-600" />
          <span>View Business Analytics</span>
        </Link>
      </div>

      {!hasData && (
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200/90 text-sm">
          <div>
            <span className="font-semibold text-slate-800 block">
              Risk Diagnostics on Standby
            </span>
            <span className="text-xs text-slate-500">
              Upload a business CSV from the Dashboard to evaluate risk scores and scan for statistical outliers.
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

      {/* Top Risk Intelligence KPI Highlights */}
      {hasData && (
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-slate-200/90 p-4 shadow-xs space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
              Risk Score
            </span>
            <div className="flex items-baseline gap-1.5">
              <span className="text-2xl font-bold text-slate-900">{riskScore}</span>
              <span className="text-xs text-slate-400">/ 100</span>
            </div>
            <span className="text-[11px] text-slate-500 block">
              Composite diagnostic index
            </span>
          </div>

          <div className="bg-white rounded-xl border border-slate-200/90 p-4 shadow-xs space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
              Advisory Level
            </span>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span
                className={`inline-block px-2.5 py-0.5 rounded text-xs font-bold border ${
                  isHigh
                    ? "bg-rose-50 text-rose-800 border-rose-200"
                    : isMedium
                    ? "bg-amber-50 text-amber-800 border-amber-200"
                    : "bg-emerald-50 text-emerald-800 border-emerald-200"
                }`}
              >
                {riskLevel} RISK
              </span>
            </div>
            <span className="text-[11px] text-slate-500 block">
              Operational triage rating
            </span>
          </div>

          <div className="bg-white rounded-xl border border-slate-200/90 p-4 shadow-xs space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
              Statistical Outliers
            </span>
            <div className="flex items-baseline gap-1.5">
              <span className="text-2xl font-bold text-slate-900">{anomalyCount.toLocaleString()}</span>
              <span className="text-xs text-slate-400">({anomalyPct}%)</span>
            </div>
            <span className="text-[11px] text-slate-500 block">
              Isolation Forest flags
            </span>
          </div>

          <div className="bg-white rounded-xl border border-slate-200/90 p-4 shadow-xs space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
              Evaluated Scope
            </span>
            <div className="text-2xl font-bold text-slate-900">
              {rowsProcessed.toLocaleString()}
            </div>
            <span className="text-[11px] text-slate-500 block">
              Active transaction rows
            </span>
          </div>
        </div>
      )}

      {/* Risk Mitigation Recommendations Section */}
      {hasData && (
        <section aria-labelledby="risk-recommendations-heading" className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
              <Target className="w-4 h-4 text-amber-600" />
              <span>Risk Recommendations & Action Plan</span>
            </h2>
            <span className="text-[11px] text-slate-400 font-medium">
              Targeted for {riskLevel} Risk Profile
            </span>
          </div>

          <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {recommendations.map((rec, i) => (
                <div
                  key={i}
                  className="p-3.5 rounded-lg bg-amber-50/40 border border-amber-100 hover:bg-amber-50/70 transition-colors flex items-start gap-2.5"
                >
                  <div className="p-1 rounded bg-amber-100 text-amber-800 shrink-0 mt-0.5">
                    <Target className="w-3.5 h-3.5" />
                  </div>
                  <p className="text-xs text-slate-800 leading-relaxed font-medium">
                    {rec}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Main Risk Details & Flagged Records Component */}
      <section aria-labelledby="risk-details-heading">
        <RiskDetailsCard
          uploadResult={uploadResult}
          fullDataset={fullDataset}
          showLinkToRiskPage={false}
        />
      </section>

      {/* Interactive Custom Evaluation Simulator */}
      <section aria-labelledby="interactive-risk-heading">
        <RiskAgent
          automaticRiskResult={riskResultData}
          isLoading={isUploading}
        />
      </section>

      {/* Methodology & Theoretical Grounding */}
      <section aria-labelledby="methodology-heading" className="space-y-3">
        <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider">
          Evaluation Methodology
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs space-y-2.5">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-800">
              <Search className="w-4 h-4 text-blue-600" />
              <span>Statistical Anomaly Detection</span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              Powered by an unsupervised <strong>Isolation Forest</strong> algorithm (<code className="font-mono text-[11px] bg-slate-100 px-1 py-0.5 rounded">backend/ml/anomaly_model.pkl</code>). It isolates records through recursive feature space partitioning. Outlier observations require few partitions, while standard transactions require many. An anomaly flag denotes unusual transaction proportions requiring human verification, not confirmed fraud.
            </p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs space-y-2.5">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-800">
              <Activity className="w-4 h-4 text-amber-600" />
              <span>Composite Risk Score (0–100)</span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              Calculated using verified backend risk rules: Isolation Forest anomaly presence (+60 or +10 pts), profit margin tier (+0 to +25 pts), and projected loss (+15 pts). Scores are classified into <strong>LOW</strong> (0–30), <strong>MEDIUM</strong> (31–60), and <strong>HIGH</strong> (61–100) operational advisory levels.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
