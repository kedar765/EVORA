"use client";

import React, { createContext, useContext, useState, ReactNode } from "react";
import { UploadResult, DatasetPreviewData, FullDatasetData, ParsedRecord } from "./types";

interface DashboardContextType {
  uploadResult: UploadResult | null;
  fullDataset: FullDatasetData | null;
  datasetPreview: DatasetPreviewData | null;
  isUploading: boolean;
  setIsUploading: (loading: boolean) => void;
  setUploadResult: (result: UploadResult | null) => void;
  handleUploadSuccess: (data: UploadResult, rawCsvText?: string) => void;
  clearDataset: () => void;
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

const UPLOAD_STORAGE_KEY = "evora_active_upload";
const PREVIEW_STORAGE_KEY = "evora_dataset_preview";
const DATASET_STORAGE_KEY = "evora_full_dataset";

function parseCsvLine(line: string): string[] {
  const result: string[] = [];
  let current = "";
  let insideQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      insideQuotes = !insideQuotes;
    } else if (char === "," && !insideQuotes) {
      result.push(current.trim());
      current = "";
    } else {
      current += char;
    }
  }
  result.push(current.trim());
  return result;
}

export function parseFullCsv(csvText: string): FullDatasetData {
  const lines = csvText
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);

  if (lines.length === 0) {
    return { headers: [], records: [], totalRows: 0, rawCsvText: csvText };
  }

  const headers = parseCsvLine(lines[0]);
  const records: ParsedRecord[] = [];

  for (let i = 1; i < lines.length; i++) {
    const cells = parseCsvLine(lines[i]);
    const record: ParsedRecord = {};
    headers.forEach((header, colIdx) => {
      const val = cells[colIdx] ?? "";
      const numVal = Number(val);
      record[header] = !isNaN(numVal) && val !== "" ? numVal : val;
    });
    records.push(record);
  }

  return {
    headers,
    records,
    totalRows: records.length,
    rawCsvText: csvText,
  };
}

export function parseCsvToPreview(csvText: string, maxRows = 6): DatasetPreviewData {
  const lines = csvText
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);

  if (lines.length === 0) {
    return { headers: [], rows: [], totalRows: 0 };
  }

  const headers = parseCsvLine(lines[0]);
  const rows = lines.slice(1, maxRows + 1).map((line) => parseCsvLine(line));

  return {
    headers,
    rows,
    totalRows: lines.length - 1,
  };
}

function getInitialUpload(): UploadResult | null {
  if (typeof window === "undefined") return null;
  try {
    const stored = sessionStorage.getItem(UPLOAD_STORAGE_KEY);
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
}

function getInitialPreview(): DatasetPreviewData | null {
  if (typeof window === "undefined") return null;
  try {
    const stored = sessionStorage.getItem(PREVIEW_STORAGE_KEY);
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
}

function getInitialFullDataset(): FullDatasetData | null {
  if (typeof window === "undefined") return null;
  try {
    const stored = sessionStorage.getItem(DATASET_STORAGE_KEY);
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
}

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [uploadResult, setUploadResultState] = useState<UploadResult | null>(getInitialUpload);
  const [datasetPreview, setDatasetPreviewState] = useState<DatasetPreviewData | null>(getInitialPreview);
  const [fullDataset, setFullDatasetState] = useState<FullDatasetData | null>(getInitialFullDataset);
  const [isUploading, setIsUploading] = useState<boolean>(false);

  const setUploadResult = (result: UploadResult | null) => {
    setUploadResultState(result);
    try {
      if (result) {
        sessionStorage.setItem(UPLOAD_STORAGE_KEY, JSON.stringify(result));
      } else {
        sessionStorage.removeItem(UPLOAD_STORAGE_KEY);
      }
    } catch {
      // Ignore write errors
    }
  };

  const handleUploadSuccess = (data: UploadResult, rawCsvText?: string) => {
    setUploadResult(data);

    if (rawCsvText) {
      const preview = parseCsvToPreview(rawCsvText);
      const parsedFull = parseFullCsv(rawCsvText);
      setDatasetPreviewState(preview);
      setFullDatasetState(parsedFull);
      try {
        sessionStorage.setItem(PREVIEW_STORAGE_KEY, JSON.stringify(preview));
        sessionStorage.setItem(DATASET_STORAGE_KEY, JSON.stringify(parsedFull));
      } catch {
        // Ignore write errors
      }
    }
  };

  const clearDataset = () => {
    setUploadResult(null);
    setDatasetPreviewState(null);
    setFullDatasetState(null);
    try {
      sessionStorage.removeItem(UPLOAD_STORAGE_KEY);
      sessionStorage.removeItem(PREVIEW_STORAGE_KEY);
      sessionStorage.removeItem(DATASET_STORAGE_KEY);
    } catch {
      // Ignore
    }
  };

  return (
    <DashboardContext.Provider
      value={{
        uploadResult,
        fullDataset,
        datasetPreview,
        isUploading,
        setIsUploading,
        setUploadResult,
        handleUploadSuccess,
        clearDataset,
      }}
    >
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboard() {
  const context = useContext(DashboardContext);
  if (!context) {
    throw new Error("useDashboard must be used within a DashboardProvider");
  }
  return context;
}
