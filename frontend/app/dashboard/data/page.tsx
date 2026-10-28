"use client";

import React from "react";
import {
  FileSpreadsheet,
  Table as TableIcon,
  Trash2,
  CheckCircle2,
  HelpCircle,
} from "lucide-react";

import { useDashboard } from "@/components/dashboard/DashboardContext";
import CsvUpload from "@/components/dashboard/CsvUpload";

export default function DataManagementPage() {
  const {
    uploadResult,
    isUploading,
    setIsUploading,
    datasetPreview,
    handleUploadSuccess,
    clearDataset,
  } = useDashboard();

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <span className="text-xs font-bold uppercase tracking-wider text-blue-700">
          Dataset Ingestion & Storage
        </span>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight mt-0.5">
          Data Management
        </h1>
        <p className="text-sm text-slate-500 mt-1 max-w-3xl">
          Upload and manage transaction datasets. EVORA automatically parses records, generates statistical summaries, and runs predictive analytics.
        </p>
      </div>

      {/* CSV Ingestion Component */}
      <section aria-labelledby="upload-section-heading">
        <CsvUpload
          onUploadSuccess={handleUploadSuccess}
          onUploadStart={clearDataset}
          isLoading={isUploading}
          setIsLoading={setIsUploading}
          uploadedFilename={uploadResult?.filename}
          rowsProcessed={uploadResult?.rows_processed}
        />

      </section>

      {/* Active Dataset Overview & Preview */}
      <section aria-labelledby="preview-section-heading" className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Dataset Inspection
            </span>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">
              Active Dataset Preview
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Live inspection of ingested tabular records and column headers.
            </p>
          </div>

          {uploadResult && (
            <button
              type="button"
              onClick={clearDataset}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200/80 transition-colors cursor-pointer self-start sm:self-auto"
              title="Clear active dataset from session"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Clear Dataset</span>
            </button>
          )}
        </div>

        {uploadResult && datasetPreview && datasetPreview.headers.length > 0 ? (
          <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-5 sm:p-6 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100 text-xs">
              <div className="flex items-center gap-2">
                <FileSpreadsheet className="w-4 h-4 text-blue-600" />
                <span className="font-bold text-slate-900">{uploadResult.filename}</span>
                <span className="text-slate-400">•</span>
                <span className="text-slate-500 font-medium">
                  {uploadResult.rows_processed} Total Records
                </span>
              </div>
              <span className="text-slate-400">
                Displaying first {datasetPreview.rows.length} sample rows
              </span>
            </div>

            <div className="overflow-x-auto custom-scrollbar border border-slate-200/80 rounded-xl">
              <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
                <thead className="bg-slate-50 font-bold text-slate-700">
                  <tr>
                    <th scope="col" className="px-3.5 py-2.5 w-12 text-slate-400 font-semibold">
                      #
                    </th>
                    {datasetPreview.headers.map((header, idx) => (
                      <th key={idx} scope="col" className="px-3.5 py-2.5 tracking-wider">
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white font-medium text-slate-800">
                  {datasetPreview.rows.map((row, rIdx) => (
                    <tr key={rIdx} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-3.5 py-2 text-slate-400 font-mono text-[11px]">
                        {rIdx + 1}
                      </td>
                      {row.map((cell, cIdx) => (
                        <td key={cIdx} className="px-3.5 py-2 whitespace-nowrap">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex items-center gap-2 text-xs text-slate-500 pt-1">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>
                Required features (Quantity, Revenue, Expense) verified and normalized for ML model consumption.
              </span>
            </div>
          </div>
        ) : uploadResult ? (
          <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-6 text-center space-y-2">
            <div className="w-10 h-10 mx-auto rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold text-slate-900">
              Dataset {uploadResult.filename} Active
            </h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Processed {uploadResult.rows_processed} records. Detailed row preview is generated during file selection or when loading the demonstration dataset.
            </p>
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-8 text-center space-y-3">
            <div className="w-12 h-12 mx-auto rounded-full bg-slate-100 text-slate-400 flex items-center justify-center">
              <TableIcon className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-800">
                No Active Dataset to Preview
              </h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto mt-1">
                Upload a CSV file above or click <strong>Load Demo Data</strong> to preview tabular records and feed business intelligence agents.
              </p>
            </div>
          </div>
        )}
      </section>

      {/* CSV Schema Guidelines */}
      <section className="bg-slate-50 rounded-2xl border border-slate-200/80 p-5 sm:p-6 space-y-3">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-700">
          <HelpCircle className="w-4 h-4 text-blue-600" />
          <span>Expected CSV Schema Requirements</span>
        </div>
        <p className="text-xs text-slate-600 leading-relaxed max-w-3xl">
          EVORA requires three mandatory numeric columns: <code className="bg-white px-1.5 py-0.5 rounded border border-slate-200 font-bold text-slate-800">Quantity</code> (units sold), <code className="bg-white px-1.5 py-0.5 rounded border border-slate-200 font-bold text-slate-800">Revenue</code> (total receipts in ₹), and <code className="bg-white px-1.5 py-0.5 rounded border border-slate-200 font-bold text-slate-800">Expense</code> (operational costs in ₹). Optional contextual attributes such as <code className="bg-white px-1.5 py-0.5 rounded border border-slate-200 text-slate-700">Date</code>, <code className="bg-white px-1.5 py-0.5 rounded border border-slate-200 text-slate-700">Product</code>, and <code className="bg-white px-1.5 py-0.5 rounded border border-slate-200 text-slate-700">Customer</code> are preserved during analysis.
        </p>
      </section>
    </div>
  );
}
