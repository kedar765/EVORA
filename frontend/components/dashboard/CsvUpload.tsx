
"use client";

import { useState, type ChangeEvent } from "react";
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Sparkles,
  Info,
} from "lucide-react";

import type { UploadResult } from "./types";

interface CsvUploadProps {
  onUploadSuccess: (
    uploadData: UploadResult,
    rawCsvText?: string
  ) => void;
  onUploadStart?: () => void;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  uploadedFilename?: string;
  rowsProcessed?: number;
}

interface ApiErrorResponse {
  detail?: string | { message?: string };
  message?: string;
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

const SAMPLE_CSV = `Date,Product,Quantity,Revenue,Expense,Customer
2026-08-01,Product A,100,20000,12000,Customer 1
2026-08-02,Product B,150,30000,18000,Customer 2
2026-08-03,Product C,200,40000,25000,Customer 3
2026-08-04,Product A,120,24000,15000,Customer 4
2026-08-05,Product B,140,28000,17000,Customer 5`;

function getErrorMessage(
  response: ApiErrorResponse | null
): string {
  if (typeof response?.detail === "string") {
    return response.detail;
  }

  if (
    response?.detail &&
    typeof response.detail.message === "string"
  ) {
    return response.detail.message;
  }

  return (
    response?.message ||
    "CSV processing failed. Please try again."
  );
}

export default function CsvUpload({
  onUploadSuccess,
  onUploadStart,
  isLoading,
  setIsLoading,
  uploadedFilename,
  rowsProcessed,
}: CsvUploadProps) {
  const [selectedFile, setSelectedFile] =
    useState<File | null>(null);

  const [error, setError] = useState("");

  const [internalUploadedName, setInternalUploadedName] =
    useState("");

  const [internalRowCount, setInternalRowCount] =
    useState<number | undefined>(undefined);

  const activeFilename =
    uploadedFilename || internalUploadedName;

  const activeRowCount =
    rowsProcessed ?? internalRowCount;

  const handleFileChange = (
    event: ChangeEvent<HTMLInputElement>
  ) => {
    setError("");

    const file = event.target.files?.[0] ?? null;

    if (
      file &&
      !file.name.toLowerCase().endsWith(".csv")
    ) {
      setSelectedFile(null);
      setError(
        "Invalid file format. Please select a CSV file."
      );
      return;
    }

    setSelectedFile(file);
  };

  const uploadFileToServer = async (
    fileToUpload: File
  ): Promise<void> => {
    if (isLoading) return;

    setError("");
    onUploadStart?.();
    setIsLoading(true);

    try {
      const rawCsvText = await fileToUpload.text();

      const formData = new FormData();
      formData.append("file", fileToUpload);

      const response = await fetch(
        `${API_BASE_URL}/upload`,
        {
          method: "POST",
          credentials: "include",
          body: formData,
          cache: "no-store",
        }
      );

      if (response.status === 401) {
        throw new Error(
          "Your session has expired. Please log in again."
        );
      }

      const result: unknown = await response
        .json()
        .catch(() => null);

      if (!response.ok) {
        throw new Error(
          getErrorMessage(
            result as ApiErrorResponse | null
          )
        );
      }

      const uploadData = result as UploadResult | null;

      if (
        !uploadData ||
        uploadData.success !== true ||
        !uploadData.metrics ||
        typeof uploadData.rows_processed !== "number"
      ) {
        throw new Error(
          "Invalid response received from EVORA backend."
        );
      }

      setInternalUploadedName(fileToUpload.name);
      setInternalRowCount(uploadData.rows_processed);

      onUploadSuccess(uploadData, rawCsvText);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to connect to EVORA backend."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpload = (): void => {
    if (!selectedFile) {
      setError("Please select a CSV file first.");
      return;
    }

    void uploadFileToServer(selectedFile);
  };

  const handleLoadSample = (): void => {
    const demoFile = new File(
      [SAMPLE_CSV],
      "sample_business_data.csv",
      { type: "text/csv" }
    );

    setSelectedFile(demoFile);
    void uploadFileToServer(demoFile);
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
            Upload a CSV file containing Quantity, Revenue,
            and Expense columns to analyze business
            performance, predictions, and risks.
          </p>
        </div>

        <button
          type="button"
          onClick={handleLoadSample}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors border border-slate-200/90 disabled:opacity-50 disabled:cursor-not-allowed"
          title="Load demonstration data"
        >
          <Sparkles className="w-3.5 h-3.5 text-blue-600" />
          Load Demo Data
        </button>
      </div>

      {activeFilename ? (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-xl bg-emerald-50/70 border border-emerald-200/80">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />

            <span className="text-xs font-semibold text-emerald-900">
              Active Dataset:{" "}
              <strong className="font-bold">
                {activeFilename}
              </strong>
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
            No file uploaded yet. Select a CSV file
            containing Quantity, Revenue, and Expense,
            or load demonstration data.
          </span>
        </div>
      )}

      <div className="flex flex-col sm:flex-row gap-3 items-stretch">
        <label className="flex-1 flex items-center gap-3 px-4 py-3 rounded-xl border border-dashed border-slate-300 hover:border-blue-500 bg-slate-50/60 hover:bg-slate-50 cursor-pointer transition-colors group">
          <FileSpreadsheet className="w-5 h-5 text-slate-400 group-hover:text-blue-600 shrink-0" />

          <div className="flex-1 min-w-0">
            <span className="block text-sm font-medium text-slate-700 truncate">
              {selectedFile
                ? selectedFile.name
                : "Choose CSV file from device"}
            </span>

            <span className="block text-[11px] text-slate-400">
              Supported format: .csv (UTF-8)
            </span>
          </div>

          <input
            type="file"
            accept=".csv,text/csv"
            onChange={handleFileChange}
            disabled={isLoading}
            className="hidden"
          />
        </label>

        <button
          type="button"
          onClick={handleUpload}
          disabled={isLoading || !selectedFile}
          className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm shrink-0"
        >
          {isLoading ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              Processing Dataset...
            </>
          ) : (
            <>
              <UploadCloud className="w-4 h-4" />
              Upload & Analyze
            </>
          )}
        </button>
      </div>

      {error && (
        <div
          role="alert"
          className="mt-4 rounded-xl bg-rose-50 border border-rose-200/90 px-4 py-3 text-xs font-semibold text-rose-700 flex items-center gap-2.5"
        >
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
