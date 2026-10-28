
"use client";

import { useState } from "react";
import {
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  Trash2,
  Sparkles,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

import { useDashboard } from "@/components/dashboard/DashboardContext";
import OverviewCards from "@/components/dashboard/OverviewCards";
import RevenueExpenseChart from "@/components/dashboard/RevenueExpenseChart";
import AIInsights from "@/components/dashboard/AIInsights";
import RiskDetailsCard from "@/components/dashboard/RiskDetailsCard";
import WhatIfAnalysis from "@/components/dashboard/WhatIfAnalysis";
import CsvUpload from "@/components/dashboard/CsvUpload";

export default function DashboardPage() {
  const {
    uploadResult,
    fullDataset,
    isUploading,
    setIsUploading,
    handleUploadSuccess,
    clearDataset,
  } = useDashboard();

  const [showUploadTray, setShowUploadTray] =
    useState(false);

  const hasData =
    uploadResult?.success === true &&
    uploadResult.metrics != null;

  const handleSuccessfulUpload = (
    data: Parameters<
      typeof handleUploadSuccess
    >[0],
    rawCsvText?: string
  ) => {
    if (
      data.success !== true ||
      !data.metrics ||
      !Number.isFinite(data.rows_processed)
    ) {
      throw new Error(
        "CSV analysis response is incomplete."
      );
    }

    handleUploadSuccess(data, rawCsvText);

    // Close only after successful dashboard update.
    setShowUploadTray(false);
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
              Dashboard
            </h1>

            <p className="text-sm text-slate-500 mt-1 max-w-3xl">
              EVORA (Enterprise Vision Optimizing Reasoning
              Assistant) provides decision support by
              evaluating financial performance, scanning
              for operational risks, predicting profit,
              and simulating business scenarios.
            </p>
          </div>

          <button
            type="button"
            onClick={() =>
              setShowUploadTray((value) => !value)
            }
            disabled={isUploading}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition-colors shadow-xs disabled:opacity-50"
          >
            <UploadCloud className="w-3.5 h-3.5" />

            <span>
              {showUploadTray
                ? "Hide Ingestion Tray"
                : "Ingest Business CSV"}
            </span>

            {showUploadTray ? (
              <ChevronUp className="w-3.5 h-3.5" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5" />
            )}
          </button>
        </div>

        {/* Active Dataset Status */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
          <div className="flex items-center gap-3 min-w-0">
            <div
              className={`p-2 rounded-lg shrink-0 ${
                hasData
                  ? "bg-emerald-50 text-emerald-600"
                  : "bg-slate-100 text-slate-400"
              }`}
            >
              {hasData ? (
                <CheckCircle2 className="w-4 h-4" />
              ) : (
                <AlertCircle className="w-4 h-4" />
              )}
            </div>

            <div className="min-w-0">
              <p className="text-xs font-bold text-slate-900 truncate">
                {hasData
                  ? uploadResult.filename
                  : "No Business Dataset Active"}
              </p>

              <p className="text-[11px] text-slate-500 mt-1">
                {hasData
                  ? `${uploadResult.rows_processed.toLocaleString(
                      "en-IN"
                    )} records analyzed successfully.`
                  : "Upload a CSV file with Quantity, Revenue, and Expense columns."}
              </p>
            </div>
          </div>

          {hasData ? (
            <button
              type="button"
              onClick={() => {
                clearDataset();
                setShowUploadTray(true);
              }}
              disabled={isUploading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 disabled:opacity-50"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Clear Dataset
            </button>
          ) : (
            <button
              type="button"
              onClick={() => setShowUploadTray(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200"
            >
              <Sparkles className="w-3.5 h-3.5" />
              Upload or Load Demo Data
            </button>
          )}
        </div>

        {/* CSV Ingestion */}
        {showUploadTray && (
          <div className="pt-2">
            <CsvUpload
              onUploadSuccess={handleSuccessfulUpload}
              isLoading={isUploading}
              setIsLoading={setIsUploading}
              uploadedFilename={
                uploadResult?.filename
              }
              rowsProcessed={
                uploadResult?.rows_processed
              }
            />
          </div>
        )}
      </section>

      {/* Business Metrics */}
      <section aria-label="Financial performance">
        <OverviewCards uploadResult={uploadResult} />
      </section>

      {/* Revenue vs Expense */}
      <section aria-label="Revenue and expense chart">
        <RevenueExpenseChart
          fullDataset={fullDataset}
          isLoading={isUploading}
        />
      </section>

      {/* AI Insights */}
      <section aria-label="Business insights">
        <AIInsights
          uploadResult={uploadResult}
          fullDataset={fullDataset}
          isLoading={isUploading}
        />
      </section>

      {/* Risk Intelligence */}
      <section aria-label="Risk intelligence">
        <RiskDetailsCard
          uploadResult={uploadResult}
          fullDataset={fullDataset}
        />
      </section>

      {/* Decision Support */}
      <section aria-label="What-if analysis">
        <WhatIfAnalysis
          currentMetrics={
            uploadResult?.metrics || null
          }
        />
      </section>
    </div>
  );
}
