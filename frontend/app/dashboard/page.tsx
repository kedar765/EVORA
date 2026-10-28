"use client";

import React, { useState } from "react";
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

  const [showUploadTray, setShowUploadTray] = useState<boolean>(false);
  const hasData = !!uploadResult;

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* 1. Page Title & Dataset Status */}
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
              Dashboard
            </h1>
            <p className="text-sm text-slate-500 mt-1 max-w-3xl">
              EVORA (Enterprise Vision Optimizing Reasoning Assistant) provides decision support by evaluating financial performance, scanning for operational risks, predicting profit, and simulating business scenarios.
            </p>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto shrink-0">
            <button
              type="button"
              onClick={() => setShowUploadTray(!showUploadTray)}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition-colors cursor-pointer shadow-xs"
            >
              <UploadCloud className="w-3.5 h-3.5" />
              <span>{showUploadTray ? "Hide Ingestion Tray" : "Ingest Business CSV"}</span>
              {showUploadTray ? (
                <ChevronUp className="w-3.5 h-3.5 ml-0.5" />
              ) : (
                <ChevronDown className="w-3.5 h-3.5 ml-0.5" />
              )}
            </button>
          </div>
        </div>

        {/* Dataset Status Banner */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-3.5 sm:p-4 rounded-xl bg-white border border-slate-200/90 shadow-xs">
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
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-900 truncate">
                  {hasData ? uploadResult.filename : "No Business Dataset Active"}
                </span>
                {hasData && (
                  <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200/80">
                    {uploadResult.rows_processed.toLocaleString()} records evaluated
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5 truncate">
                {hasData
                  ? "All metrics, chart trends, AI insights, and predictions below are computed from this dataset."
                  : "Upload a transaction CSV (Quantity, Revenue, Expense) or load demonstration data to activate analysis."}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto shrink-0">
            {hasData ? (
              <button
                type="button"
                onClick={clearDataset}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200/80 transition-colors cursor-pointer"
                title="Clear current dataset from session"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear Dataset</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setShowUploadTray(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200/80 transition-colors cursor-pointer"
              >
                <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                <span>Upload or Load Demo Data</span>
              </button>
            )}
          </div>
        </div>

        {/* Collapsible CSV Ingestion Component */}
        {showUploadTray && (
          <div className="pt-2">
            <CsvUpload
              onUploadSuccess={(data, rawText) => {
                handleUploadSuccess(data, rawText);
                setShowUploadTray(false);
              }}
              onUploadStart={clearDataset}
              isLoading={isUploading}
              setIsLoading={setIsUploading}
              uploadedFilename={uploadResult?.filename}
              rowsProcessed={uploadResult?.rows_processed}
            />
          </div>
        )}
      </section>

      {/* 2 & 3. Business Analytics KPI Cards (Financial Performance & Prediction/Risk/Operations) */}
      <section aria-labelledby="kpi-cards-heading">
        <OverviewCards uploadResult={uploadResult} />
      </section>

      {/* 4. Primary Visualization: Revenue vs. Expense Comparison */}
      <section aria-labelledby="revenue-expense-heading">
        <RevenueExpenseChart
          fullDataset={fullDataset}
          isLoading={isUploading}
        />
      </section>

      {/* 5. AI Insights */}
      <section aria-labelledby="ai-insights-heading">
        <AIInsights
          uploadResult={uploadResult}
          fullDataset={fullDataset}
          isLoading={isUploading}
        />
      </section>

      {/* 6. Risk Details and Flagged Records */}
      <section aria-labelledby="risk-details-heading">
        <RiskDetailsCard
          uploadResult={uploadResult}
          fullDataset={fullDataset}
        />
      </section>

      {/* 7. What-If Analysis Entry Point & Interactive Simulator */}
      <section aria-labelledby="what-if-heading">
        <WhatIfAnalysis currentMetrics={uploadResult?.metrics || null} />
      </section>
    </div>
  );
}