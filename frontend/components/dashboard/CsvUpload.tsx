"use client";

import React, { useState } from "react";
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Sparkles,
  Info,
} from "lucide-react";
import { UploadResult } from "./types";

interface CsvUploadProps {
  onUploadSuccess: (uploadData: UploadResult, rawCsvText?: string) => void;
  onUploadStart?: () => void;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  uploadedFilename?: string;
  rowsProcessed?: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

const SAMPLE_CSV = `Date,Product,Quantity,Revenue,Expense,Customer
2026-08-01,Product A,100,20000,12000,Customer 1
2026-08-02,Product B,150,30000,18000,Customer 2
2026-08-03,Product C,200,40000,25000,Customer 3
2026-08-04,Product A,120,24000,15000,Customer 4
2026-08-05,Product B,140,28000,17000,Customer 5`;

export default function CsvUpload({
  onUploadSuccess,
  onUploadStart,
  isLoading,
  setIsLoading,
  uploadedFilename,
  rowsProcessed,
}: CsvUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string>("");
  const [internalUploadedName, setInternalUploadedName] = useState<string>("");
  const [internalRowCount, setInternalRowCount] = useState<number | undefined>(undefined);

  const activeFilename = uploadedFilename || internalUploadedName;
  const activeRowCount = rowsProcessed ?? internalRowCount;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError("");
    const file = e.target.files?.[0] || null;
    if (file && !file.name.toLowerCase().endsWith(".csv")) {
      setError("Invalid file format. Please select a file with .csv extension.");
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file);
  };

  const uploadFileToServer = async (fileToUpload: File) => {
    setError("");
    setInternalUploadedName("");
    setInternalRowCount(undefined);
    onUploadStart?.();
    setIsLoading(true);


    try {
      const rawText = await fileToUpload.text();
      const uploadFormData = new FormData();
      uploadFormData.append("file", fileToUpload);

      const uploadRes = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        body: uploadFormData,
      });

      const uploadData: UploadResult = await uploadRes.json();
      if (!uploadRes.ok) {
        throw new Error(
          typeof (uploadData as unknown as { detail?: string | { message?: string } }).detail === "string"
            ? (uploadData as unknown as { detail: string }).detail
            : (uploadData as unknown as { detail?: { message?: string } }).detail?.message || "CSV processing failed."
        );
      }

      setInternalUploadedName(fileToUpload.name);
      setInternalRowCount(uploadData.rows_processed);
      onUploadSuccess(uploadData, rawText);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unable to connect to EVORA backend.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpload = () => {
    if (!selectedFile) {
      setError("Please select a CSV file first.");
      return;
    }
    uploadFileToServer(selectedFile);
  };

  const handleLoadSample = () => {
    const file = new File([SAMPLE_CSV], "sample_business_data.csv", { type: "text/csv" });
    setSelectedFile(file);
    uploadFileToServer(file);
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-6 sm:p-7 transition-all">
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center justify-center w-6 h-6 rounded-md bg-blue-50 text-blue-700">
              <UploadCloud className="w-3.5 h-3.5" />
            </span>
            <span className="text-xs font-bold uppercase tracking-wider text-blue-700">
              CSV Ingestion
            </span>
          </div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">
            Upload Business Records
          </h2>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Upload your transaction CSV with Quantity, Revenue, and Expense columns for automated metrics, machine learning predictions, and agent diagnostics.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto shrink-0">
          <button
            type="button"
            onClick={handleLoadSample}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors cursor-pointer border border-slate-200/90 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Load built-in demonstration dataset"
          >
            <Sparkles className="w-3.5 h-3.5 text-blue-600" />
            <span>Load Demo Data</span>
          </button>
        </div>
      </div>

      {activeFilename ? (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-xl bg-emerald-50/70 border border-emerald-200/80">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="text-xs font-semibold text-emerald-900">
              Active Dataset: <strong className="font-bold">{activeFilename}</strong>
            </span>
            {activeRowCount !== undefined && (
              <span className="text-xs text-emerald-700 bg-emerald-100/70 px-2 py-0.5 rounded-md font-medium">
                {activeRowCount} rows processed
              </span>
            )}
          </div>
          <span className="text-[11px] font-medium text-emerald-700">
            Pipeline Ready
          </span>
        </div>
      ) : (
        <div className="mb-4 flex items-center gap-2.5 p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 text-xs text-slate-600">
          <Info className="w-4 h-4 text-slate-400 shrink-0" />
          <span>
            No file uploaded yet. Select a CSV file with required columns (Quantity, Revenue, Expense) or click <strong>Load Demo Data</strong> to begin analysis.
          </span>
        </div>
      )}

      <div className="flex flex-col sm:flex-row gap-3 items-stretch">
        <label className="flex-1 flex items-center gap-3 px-4 py-3 rounded-xl border border-dashed border-slate-300 hover:border-blue-500 bg-slate-50/60 hover:bg-slate-50 cursor-pointer transition-colors group">
          <FileSpreadsheet className="w-5 h-5 text-slate-400 group-hover:text-blue-600 transition-colors shrink-0" />
          <div className="flex-1 min-w-0">
            <span className="block text-sm font-medium text-slate-700 truncate">
              {selectedFile ? selectedFile.name : "Choose CSV file from device or drag here"}
            </span>
            <span className="block text-[11px] text-slate-400">
              Supported format: .csv (UTF-8)
            </span>
          </div>
          <input
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            className="hidden"
          />
        </label>

        <button
          type="button"
          onClick={handleUpload}
          disabled={isLoading || !selectedFile}
          className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm cursor-pointer shrink-0"
        >
          {isLoading ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span>Processing Dataset...</span>
            </>
          ) : (
            <>
              <UploadCloud className="w-4 h-4" />
              <span>Upload & Analyze</span>
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="mt-4 rounded-xl bg-rose-50 border border-rose-200/90 px-4 py-3 text-xs font-semibold text-rose-700 flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
