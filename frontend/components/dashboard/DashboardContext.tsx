
"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { useAuth } from "@/lib/auth";

import type {
  UploadResult,
  DatasetPreviewData,
  FullDatasetData,
  ParsedRecord,
} from "./types";

interface DashboardContextType {
  uploadResult: UploadResult | null;
  fullDataset: FullDatasetData | null;
  datasetPreview: DatasetPreviewData | null;
  isUploading: boolean;
  setIsUploading: (loading: boolean) => void;
  setUploadResult: (result: UploadResult | null) => void;
  handleUploadSuccess: (
    data: UploadResult,
    rawCsvText?: string
  ) => void;
  clearDataset: () => void;
}

interface StoredUserData<T> {
  userId: string;
  data: T;
}

const STORAGE_KEYS = {
  upload: "evora_active_upload",
  preview: "evora_dataset_preview",
  dataset: "evora_full_dataset",
};

const DashboardContext = createContext<
  DashboardContextType | undefined
>(undefined);

function removeStoredData(): void {
  try {
    Object.values(STORAGE_KEYS).forEach((key) => {
      sessionStorage.removeItem(key);
    });
  } catch {
    // Browser storage may be unavailable.
  }
}

function saveStoredData<T>(
  key: string,
  userId: string,
  data: T
): void {
  try {
    const value: StoredUserData<T> = {
      userId,
      data,
    };

    sessionStorage.setItem(
      key,
      JSON.stringify(value)
    );
  } catch (error) {
    console.warn(
      "Unable to save dashboard session data:",
      error
    );
  }
}

function readStoredData<T>(
  key: string,
  userId: string
): T | null {
  try {
    const stored = sessionStorage.getItem(key);

    if (!stored) return null;

    const parsed = JSON.parse(
      stored
    ) as Partial<StoredUserData<T>>;

    if (
      parsed.userId !== userId ||
      parsed.data == null
    ) {
      sessionStorage.removeItem(key);
      return null;
    }

    return parsed.data;
  } catch {
    try {
      sessionStorage.removeItem(key);
    } catch {
      // Ignore storage errors.
    }

    return null;
  }
}

function parseCsvLine(line: string): string[] {
  const values: string[] = [];
  let current = "";
  let insideQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];

    if (char === '"') {
      if (
        insideQuotes &&
        line[i + 1] === '"'
      ) {
        current += '"';
        i++;
      } else {
        insideQuotes = !insideQuotes;
      }
    } else if (
      char === "," &&
      !insideQuotes
    ) {
      values.push(current.trim());
      current = "";
    } else {
      current += char;
    }
  }

  values.push(current.trim());

  return values;
}

export function parseFullCsv(
  csvText: string
): FullDatasetData {
  const lines = csvText
    .replace(/^\uFEFF/, "")
    .split(/\r?\n/)
    .filter((line) => line.trim() !== "");

  if (lines.length === 0) {
    return {
      headers: [],
      records: [],
      totalRows: 0,
      rawCsvText: csvText,
    };
  }

  const headers = parseCsvLine(lines[0]);
  const records: ParsedRecord[] = [];

  for (let i = 1; i < lines.length; i++) {
    const cells = parseCsvLine(lines[i]);
    const record: ParsedRecord = {};

    headers.forEach((header, index) => {
      const value = cells[index] ?? "";
      const numericValue = Number(value);

      record[header] =
        value !== "" &&
        Number.isFinite(numericValue)
          ? numericValue
          : value;
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

export function parseCsvToPreview(
  csvText: string,
  maxRows = 6
): DatasetPreviewData {
  const dataset = parseFullCsv(csvText);

  return {
    headers: dataset.headers,
    rows: dataset.records
      .slice(0, maxRows)
      .map((record) =>
        dataset.headers.map((header) =>
          String(record[header] ?? "")
        )
      ),
    totalRows: dataset.totalRows,
  };
}

export function DashboardProvider({
  children,
}: {
  children: ReactNode;
}) {
  const { user, isAuthenticated } = useAuth();

  const userId =
    isAuthenticated && user?.id
      ? user.id
      : null;

  const [uploadResult, setUploadResultState] =
    useState<UploadResult | null>(null);

  const [datasetPreview, setDatasetPreviewState] =
    useState<DatasetPreviewData | null>(null);

  const [fullDataset, setFullDatasetState] =
    useState<FullDatasetData | null>(null);

  const [isUploading, setIsUploading] =
    useState(false);

  const clearDataset = useCallback(() => {
    setUploadResultState(null);
    setDatasetPreviewState(null);
    setFullDatasetState(null);
    setIsUploading(false);

    removeStoredData();
  }, []);

  // Restore saved data when the authenticated
  // user changes, not after every upload.
  useEffect(() => {
    if (!userId) {
      setUploadResultState(null);
      setDatasetPreviewState(null);
      setFullDatasetState(null);
      removeStoredData();
      return;
    }

    const savedUpload = readStoredData<UploadResult>(
      STORAGE_KEYS.upload,
      userId
    );

    const savedPreview =
      readStoredData<DatasetPreviewData>(
        STORAGE_KEYS.preview,
        userId
      );

    const savedDataset =
      readStoredData<FullDatasetData>(
        STORAGE_KEYS.dataset,
        userId
      );

    const validUpload =
      savedUpload?.success === true &&
      savedUpload.metrics != null;

    setUploadResultState(
      validUpload ? savedUpload : null
    );

    setDatasetPreviewState(
      validUpload ? savedPreview : null
    );

    setFullDatasetState(
      validUpload ? savedDataset : null
    );
  }, [userId]);

  const setUploadResult = useCallback(
    (result: UploadResult | null) => {
      if (!result) {
        clearDataset();
        return;
      }

      if (!userId) {
        throw new Error(
          "Login session is not available."
        );
      }

      setUploadResultState(result);

      saveStoredData(
        STORAGE_KEYS.upload,
        userId,
        result
      );
    },
    [userId, clearDataset]
  );

  const handleUploadSuccess = useCallback(
    (
      data: UploadResult,
      rawCsvText?: string
    ) => {
      if (!userId) {
        throw new Error(
          "Session expired. Please log in again."
        );
      }

      if (
        data?.success !== true ||
        !data.metrics ||
        !Number.isFinite(data.rows_processed)
      ) {
        throw new Error(
          "Invalid CSV analysis result."
        );
      }

      // Parse the new dataset before updating state.
      const dataset =
        rawCsvText !== undefined
          ? parseFullCsv(rawCsvText)
          : null;

      const preview =
        rawCsvText !== undefined
          ? parseCsvToPreview(rawCsvText)
          : null;

      // Update Dashboard immediately.
      setUploadResultState(data);
      setFullDatasetState(dataset);
      setDatasetPreviewState(preview);

      // Save the result for the current user.
      saveStoredData(
        STORAGE_KEYS.upload,
        userId,
        data
      );

      if (dataset && preview) {
        saveStoredData(
          STORAGE_KEYS.dataset,
          userId,
          dataset
        );

        saveStoredData(
          STORAGE_KEYS.preview,
          userId,
          preview
        );
      } else {
        try {
          sessionStorage.removeItem(
            STORAGE_KEYS.dataset
          );

          sessionStorage.removeItem(
            STORAGE_KEYS.preview
          );
        } catch {
          // Ignore storage errors.
        }
      }
    },
    [userId]
  );

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

export function useDashboard(): DashboardContextType {
  const context = useContext(DashboardContext);

  if (!context) {
    throw new Error(
      "useDashboard must be used within DashboardProvider"
    );
  }

  return context;
}
