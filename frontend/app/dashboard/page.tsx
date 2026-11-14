"use client";

import { useState } from "react";
import {
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  Trash2,
  ChevronDown,
  ChevronUp,
  FileSpreadsheet,
  ArrowRight,
  ShieldAlert,
  BrainCircuit,
} from "lucide-react";
import Link from "next/link";

import { useDashboard } from "@/components/dashboard/DashboardContext";
import OverviewCards from "@/components/dashboard/OverviewCards";
import RevenueExpenseChart from "@/components/dashboard/RevenueExpenseChart";
import AIInsights from "@/components/dashboard/AIInsights";
import RiskDetailsCard from "@/components/dashboard/RiskDetailsCard";
import WhatIfAnalysis from "@/components/dashboard/WhatIfAnalysis";
import CsvUpload from "@/components/dashboard/CsvUpload";
import MultiAgentWorkflow from "@/components/dashboard/MultiAgentWorkflow";

export default function DashboardPage() {
  const {
    uploadResult,
    fullDataset,
    isUploading,
    setIsUploading,
    handleUploadSuccess,
    clearDataset,
  } = useDashboard();

  const [showUploadTray, setShowUploadTray] = useState(false);

  const hasData =
    uploadResult?.success === true &&
    uploadResult.metrics != null;

  const handleSuccessfulUpload = (
    data: Parameters<typeof handleUploadSuccess>[0],
    rawCsvText?: string
  ) => {
    if (
      data.success !== true ||
      !data.metrics ||
      !Number.isFinite(data.rows_processed)
    ) {
      throw new Error("CSV analysis response is incomplete.");
    }

    handleUploadSuccess(data, rawCsvText);
    setShowUploadTray(false);
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      {/* Overview Top Section */}
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="w-1.5 h-4 rounded-full bg-blue-600" />
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Enterprise BI & Decision Optimization
              </span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              Enterprise Dashboard
            </h1>

            <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-3xl leading-relaxed">
              Real-time Business Intelligence evaluating financial performance, scanning for operational risks, predicting profit, and simulating autonomous multi-agent business decisions.
            </p>
          </div>

          <div className="flex items-center gap-2.5 self-start sm:self-auto">
            <button
              type="button"
              onClick={() => setShowUploadTray((value) => !value)}
              disabled={isUploading}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition-all shadow-xs hover:shadow-md disabled:opacity-50"
            >
              <UploadCloud className="w-4 h-4" />
              <span>{showUploadTray ? "Hide Ingestion Tray" : "Ingest Dataset"}</span>
              {showUploadTray ? (
                <ChevronUp className="w-3.5 h-3.5 text-blue-200" />
              ) : (
                <ChevronDown className="w-3.5 h-3.5 text-blue-200" />
              )}
            </button>
          </div>
        </div>

        {/* Active Dataset Telemetry Banner */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3.5 p-4 rounded-2xl bg-white border border-slate-200/90 shadow-xs">
          <div className="flex items-center gap-3.5 min-w-0">
            <div
              className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                hasData
                  ? "bg-emerald-50 text-emerald-600"
                  : "bg-slate-100 text-slate-400"
              }`}
            >
              {hasData ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              ) : (
                <FileSpreadsheet className="w-5 h-5 text-slate-400" />
              )}
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <p className="text-sm font-bold text-slate-900 truncate">
                  {hasData ? uploadResult.filename : "No Business Dataset Active"}
                </p>
                {hasData && (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200/60 uppercase">
                    Active Telemetry
                  </span>
                )}
              </div>

              <p className="text-xs text-slate-500 mt-0.5">
                {hasData
                  ? `${uploadResult.rows_processed.toLocaleString(
                      "en-IN"
                    )} records ingested and verified by EVORA pipeline.`
                  : "Upload a CSV or Excel file with Quantity, Revenue, and Expense columns."}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto shrink-0">
            {hasData ? (
              <button
                type="button"
                onClick={clearDataset}
                disabled={isUploading}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200/70 transition-colors disabled:opacity-50"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Clear Dataset
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setShowUploadTray(true)}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200/70 transition-colors"
              >
                <UploadCloud className="w-3.5 h-3.5 text-blue-600" />
                Upload Business Dataset
              </button>
            )}
          </div>
        </div>

        {/* Ingestion Drawer */}
        {showUploadTray && (
          <div className="pt-2 animate-fade-in">
            <CsvUpload
              onUploadSuccess={handleSuccessfulUpload}
              isLoading={isUploading}
              setIsLoading={setIsUploading}
              uploadedFilename={uploadResult?.filename}
              rowsProcessed={uploadResult?.rows_processed}
            />
          </div>
        )}
      </section>

      {/* Financial & Operations KPI Cards */}
      <section aria-label="Financial and operational performance">
        <OverviewCards uploadResult={uploadResult} />
      </section>

      {/* Autonomous Multi-Agent AI Decision Optimization */}
      <section aria-label="Multi-Agent AI Decision System">
        <MultiAgentWorkflow
          datasetId={uploadResult?.dataset_id}
          filename={uploadResult?.filename}
          hasData={hasData}
        />
      </section>

      {/* Revenue vs Expense Comparison Chart */}
      <section aria-label="Revenue and expense chart">
        <RevenueExpenseChart
          fullDataset={fullDataset}
          uploadResult={uploadResult}
          isLoading={isUploading}
        />
      </section>

      {/* Strategic AI Insights & Recommendations */}
      <section aria-label="Strategic AI Insights">
        <AIInsights
          uploadResult={uploadResult}
          fullDataset={fullDataset}
          isLoading={isUploading}
        />
      </section>

      {/* Risk Intelligence & Anomaly Review */}
      <section aria-label="Risk intelligence">
        <RiskDetailsCard
          uploadResult={uploadResult}
          fullDataset={fullDataset}
        />
      </section>

      {/* Decision Support: What-If Scenario Simulation */}
      <section aria-label="What-if analysis">
        <WhatIfAnalysis
          currentMetrics={uploadResult?.metrics || null}
        />
      </section>
    </div>
  );
}
