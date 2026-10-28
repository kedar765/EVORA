"use client";

import React from "react";
import Link from "next/link";
import {
  ArrowRight,
  Activity,
  Search,
  BarChart3,
} from "lucide-react";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import RiskDetailsCard from "@/components/dashboard/RiskDetailsCard";
import RiskAgent from "@/components/dashboard/RiskAgent";

export default function RiskIntelligencePage() {
  const { uploadResult, fullDataset, isUploading } = useDashboard();
  const hasData = !!uploadResult;

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

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
            Risk Intelligence
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Isolation Forest statistical anomaly detection, loss exposure indicators, and multi-factor risk scoring for operational decision support.
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

      {/* Main Risk Details & Flagged Records Component */}
      <section aria-labelledby="risk-details-heading">
        <RiskDetailsCard
          uploadResult={uploadResult}
          fullDataset={fullDataset}
        />
      </section>

      {/* Interactive Custom Evaluation Simulator */}
      <section aria-labelledby="interactive-risk-heading">
        <RiskAgent
          automaticRiskResult={riskResultData}
          isLoading={isUploading}
        />
      </section>

      {/* Methodology & Distinction */}
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
              Calculated using verified backend risk rules: Isolation Forest anomaly (+60 or +10 pts), profit margin tier (+0 to +25 pts), and projected loss (+15 pts). Scores are classified into <strong>LOW</strong> (0–30), <strong>MEDIUM</strong> (31–60), and <strong>HIGH</strong> (61–100) operational advisory levels.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
