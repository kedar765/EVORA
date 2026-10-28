export interface BusinessMetrics {
  total_revenue: number;
  total_expense: number;
  total_profit: number;
  total_sales: number;
  average_revenue?: number;
  average_expense?: number;
  average_profit?: number;
  profit_margin: number;
}

export interface UploadResult {
  success: boolean;
  message: string;
  filename: string;
  rows_processed: number;
  metrics: BusinessMetrics;
  predicted_profit: number | null;
  anomaly_detected?: boolean;
  anomaly_count?: number;
  anomaly_indices?: number[];
  risk_score?: number;
  risk_level?: string;
  risk_analysis?: RiskAnalysisData;
  analytics?: AnalyticsData;
  business_status?: string;
}

export interface AnalyticsData {
  total_revenue: number;
  total_expense: number;
  total_profit: number;
  profit_margin: number;
  insights: string[];
}

export interface AnalyticsResult {
  success: boolean;
  analysis: AnalyticsData;
}

export interface ProfitPredictionResult {
  success: boolean;
  predicted_profit: number;
}

export interface RiskAnalysisData {
  risk_level: string;
  risk_score: number;
  predicted_profit: number;
  anomaly_detected: boolean;
  reasons: string[];
}

export interface RiskAnalysisResult {
  success: boolean;
  predicted_profit: number;
  anomaly_detected: boolean;
  risk_score: number;
  risk_level: string;
  risk_analysis: RiskAnalysisData;
}

export interface WhatIfResult {
  success: boolean;
  current_predicted_profit: number;
  new_predicted_profit: number;
  profit_difference: number;
  result: string;
}

export function formatINR(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return "—";
  const isNegative = val < 0;
  const absVal = Math.abs(val);
  const formatted = absVal.toLocaleString("en-IN", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  });
  return isNegative ? `-₹${formatted}` : `₹${formatted}`;
}

export function formatNumber(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return "—";
  return val.toLocaleString("en-IN");
}

export function formatPercent(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return "—";
  return `${val.toFixed(2)}%`;
}

export interface DatasetPreviewData {
  headers: string[];
  rows: string[][];
  totalRows: number;
}

export interface ParsedRecord {
  [key: string]: string | number;
}

export interface FullDatasetData {
  headers: string[];
  records: ParsedRecord[];
  totalRows: number;
  rawCsvText: string;
}
