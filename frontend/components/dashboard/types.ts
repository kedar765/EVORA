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
  dataset_id?: string;
}


export interface AnalyticsData {
  total_revenue: number;
  total_expense: number;
  total_profit: number;
  profit_margin: number;
  insights: string[];
  recommendations?: string[];
  product_performance?: Array<{
    product: string;
    revenue: number;
    expense: number;
    profit: number;
  }>;
  monthly_trends?: Array<{
    month: string;
    revenue: number;
    expense: number;
    profit: number;
  }>;
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
  aggregate_analysis?: {
    current_revenue: number;
    current_expense: number;
    current_profit: number;
    current_margin: number;
    target_revenue: number;
    target_expense: number;
    proposed_profit: number;
    proposed_margin: number;
    profit_delta: number;
    margin_delta: number;
    percentage_profit_improvement: number;
  };
  forecast_comparison?: {
    horizon: string;
    days_in_period: number;
    baseline_daily_profit: number;
    proposed_daily_profit: number;
    daily_profit_delta: number;
  };
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
