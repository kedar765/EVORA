"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  FileText,
  Download,
  Clock,
  FileSpreadsheet,
  CheckCircle2,
  Info,
} from "lucide-react";
import { useDashboard } from "@/components/dashboard/DashboardContext";

export default function ReportsPage() {
  const { uploadResult, fullDataset } = useDashboard();
  const [downloadNotice, setDownloadNotice] = useState<string>("");

  const hasData = !!uploadResult;

  const downloadRawCsv = () => {
    if (!fullDataset?.rawCsvText) return;
    const blob = new Blob([fullDataset.rawCsvText], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", uploadResult?.filename || "evora_business_data.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    setDownloadNotice("CSV dataset exported successfully.");
    setTimeout(() => setDownloadNotice(""), 3500);
  };

  const downloadJsonSummary = () => {
    if (!uploadResult) return;
    const summary = {
      system: "EVORA Business Intelligence",
      export_timestamp: new Date().toISOString(),
      dataset: {
        filename: uploadResult.filename,
        rows_processed: uploadResult.rows_processed,
      },
      metrics: uploadResult.metrics,
      predicted_profit: uploadResult.predicted_profit,
      risk_intelligence: {
        risk_score: uploadResult.risk_score,
        risk_level: uploadResult.risk_level,
        anomaly_count: uploadResult.anomaly_count,
        reasons: uploadResult.risk_analysis?.reasons || [],
      },
      analytics: uploadResult.analytics,
      governance: "Human decision support mode; estimates do not guarantee commercial outcomes.",
    };

    const blob = new Blob([JSON.stringify(summary, null, 2)], {
      type: "application/json;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute(
      "download",
      `evora_summary_${new Date().toISOString().slice(0, 10)}.json`
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    setDownloadNotice("Executive intelligence JSON audit file exported successfully.");
    setTimeout(() => setDownloadNotice(""), 3500);
  };

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
          Reports & Exports
        </h1>
        <p className="text-sm text-slate-500 mt-1 max-w-2xl">
          Export verified dataset records and machine learning audit summaries for executive review and external compliance.
        </p>
      </div>

      {downloadNotice && (
        <div className="p-3.5 rounded-lg bg-emerald-50 border border-emerald-200 text-xs font-semibold text-emerald-800 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{downloadNotice}</span>
        </div>
      )}

      {/* Available Working Exports */}
      <section aria-labelledby="active-exports-heading" className="space-y-3">
        <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider">
          Available Data Exports
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Export 1: Ingested CSV */}
          <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs flex flex-col justify-between space-y-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-700">
                <FileSpreadsheet className="w-4 h-4 text-blue-600" />
                <span>Active CSV Ingestion File</span>
              </div>
              <h3 className="text-base font-bold text-slate-900">
                Download Raw Transaction Data
              </h3>
              <p className="text-xs text-slate-500 leading-relaxed">
                Export the currently active CSV dataset in its original UTF-8 tabular format for audit or spreadsheet analysis.
              </p>
            </div>

            <div className="pt-2">
              <button
                type="button"
                onClick={downloadRawCsv}
                disabled={!hasData || !fullDataset?.rawCsvText}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-colors cursor-pointer shadow-xs"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export Dataset (.csv)</span>
              </button>
            </div>
          </div>

          {/* Export 2: Executive Summary JSON */}
          <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs flex flex-col justify-between space-y-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-700">
                <FileText className="w-4 h-4 text-indigo-600" />
                <span>Business Intelligence Audit Summary</span>
              </div>
              <h3 className="text-base font-bold text-slate-900">
                Export Verified Intelligence JSON
              </h3>
              <p className="text-xs text-slate-500 leading-relaxed">
                Generates a structured JSON file containing computed metrics, Isolation Forest findings, risk scores, and model predictions.
              </p>
            </div>

            <div className="pt-2">
              <button
                type="button"
                onClick={downloadJsonSummary}
                disabled={!hasData}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-colors cursor-pointer shadow-xs"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export Audit Summary (.json)</span>
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Planned Reports - Clearly Marked as Coming Soon */}
      <section aria-labelledby="roadmap-heading" className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider">
            Automated Reporting Suite
          </h2>
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200/80">
            <Clock className="w-3 h-3 text-amber-600" />
            <span>Coming Soon</span>
          </span>
        </div>

        <div className="bg-white rounded-xl border border-slate-200/90 p-5 sm:p-6 shadow-xs space-y-4">
          <p className="text-xs text-slate-500 max-w-2xl leading-relaxed">
            The automated document generation pipeline is currently in development. In accordance with EVORA&apos;s data integrity rules, unbuilt features are clearly designated and not simulated with fake outputs.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200/70 space-y-1">
              <span className="font-bold text-slate-800 block">Boardroom PDF Brief</span>
              <p className="text-slate-500 text-[11px] leading-tight">
                Formatted single-page executive PDF summarizing quarterly performance, anomaly alerts, and margin trends.
              </p>
            </div>

            <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200/70 space-y-1">
              <span className="font-bold text-slate-800 block">Scheduled Email Digest</span>
              <p className="text-slate-500 text-[11px] leading-tight">
                Automated weekly or monthly dispatch of business KPIs and risk score alerts to leadership teams.
              </p>
            </div>

            <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200/70 space-y-1">
              <span className="font-bold text-slate-800 block">Multi-Period Comparison</span>
              <p className="text-slate-500 text-[11px] leading-tight">
                Cross-quarter audit comparisons contrasting baseline figures with simulated target outcomes.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer Info */}
      <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 flex items-start gap-2.5 text-xs text-slate-600">
        <Info className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          Need to ingest or clear business transaction records? Visit the{" "}
          <Link href="/dashboard" className="text-blue-600 font-semibold hover:underline">
            Dashboard
          </Link>{" "}
          to load new data or review active records.
        </p>
      </div>
    </div>
  );
}
