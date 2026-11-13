
export interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export interface SignupCredentials {
  fullName: string;
  email: string;
  password: string;
}

export interface AuthResponse {
  success: boolean;
  message?: string;
  user?: {
    id: string;
    email: string;
    fullName?: string;
  };
}

export interface ForecastNextDayResponse {
  forecast_date: string;
  predicted_profit: number;
  currency: string;
  model_name: string;
  model_version: string;
  model_metrics: {
    mae: number;
    rmse: number;
    r2: number;
  };
  status: string;
}

export interface DecisionRecommendationRequest {
  analytics?: {
    total_revenue?: number;
    total_expense?: number;
    total_profit?: number;
    profit_margin?: number;
  };
  risk?: {
    risk_level?: string;
    risk_score?: number;
    anomaly_detected?: boolean;
  };
  scenario?: {
    current_predicted_profit?: number;
    new_predicted_profit?: number;
    profit_difference?: number;
    result?: string;
  };
}

export interface DecisionAction {
  action: string;
  reason: string;
  expected_benefit: string;
  risk: string;
}

export interface DecisionRecommendationResponse {
  success: boolean;
  decision: {
    question_addressed: string;
    priority: "HIGH" | "MEDIUM" | "LOW";
    risk_context: {
      risk_level: string;
      risk_score: number;
      anomaly_detected: boolean;
    };
    evidence: string[];
    recommendations: string[];
    action_plan: DecisionAction[];
    decision_disclaimer: string;
  };
  analysis_id: string;
  created_at: number;
}

export interface DatasetItem {
  dataset_id: string;
  filename: string;
  uploaded_at: number;
  rows: number;
  columns_count: number;
  columns: string[];
  date_start?: string | null;
  date_end?: string | null;
  status: string;
}

export interface DatasetListResponse {
  success: boolean;
  total: number;
  limit: number;
  offset: number;
  datasets: DatasetItem[];
}

export interface DatasetDetailResponse {
  success: boolean;
  dataset: DatasetItem;
}

export interface DatasetPreviewResponse {
  success: boolean;
  dataset_id: string;
  filename: string;
  columns: string[];
  preview_rows: number;
  data: Record<string, unknown>[];
}

export interface AnalysisHistoryItem {
  analysis_id: string;
  dataset_id: string | null;
  analysis_type: string;
  created_at: number;
  input_summary: Record<string, unknown>;
  status: string;
}

export interface AnalysisHistoryListResponse {
  success: boolean;
  total: number;
  limit: number;
  offset: number;
  history: AnalysisHistoryItem[];
}

export interface WhatIfRequest {
  current_quantity: number;
  current_revenue: number;
  current_expense: number;
  new_quantity: number;
  new_revenue: number;
  new_expense: number;
}

export interface WhatIfResponse {
  success: boolean;
  current_predicted_profit: number;
  new_predicted_profit: number;
  profit_difference: number;
  result: string;
  analysis_id?: string;
  created_at?: number;
}

export interface ProfitPredictionRequest {
  Quantity: number;
  Revenue: number;
  Expense: number;
}

export interface ProfitPredictionResponse {
  success: boolean;
  predicted_profit: number;
  analysis_id?: string;
  created_at?: number;
}

export interface RiskAnalysisRequest {
  Quantity: number;
  Revenue: number;
  Expense: number;
}

export interface RiskAnalysisBackendResponse {
  success: boolean;
  predicted_profit: number;
  anomaly_detected: boolean;
  risk_score: number;
  risk_level: string;
  risk_analysis: {
    risk_level: string;
    risk_score: number;
    predicted_profit: number;
    anomaly_detected: boolean;
    reasons: string[];
  };
  analysis_id?: string;
  created_at?: number;
}

export interface HealthResponse {
  status: string;
  service?: string;
  timestamp?: number;
  models_loaded?: {
    profit_model?: boolean;
    anomaly_model?: boolean;
    daily_profit_forecaster?: boolean;
  };
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  try {
    const isFormData = options.body instanceof FormData;
    const headers: Record<string, string> = {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...((options.headers as Record<string, string>) || {}),
    };

    const response = await fetch(
      `${API_BASE_URL}${endpoint}`,
      {
        ...options,
        credentials: "include",
        headers,
      }
    );

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      const detail = data?.detail || data?.message;

      throw new ApiError(
        response.status,
        typeof detail === "string"
          ? detail
          : "Request failed. Please try again."
      );
    }

    return data as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    throw new ApiError(
      0,
      "Unable to connect to EVORA backend."
    );
  }
}

function validateAuthResponse(
  response: AuthResponse
): AuthResponse {
  if (
    !response?.success ||
    !response.user?.id ||
    !response.user?.email
  ) {
    throw new ApiError(
      401,
      response?.message || "Authentication failed."
    );
  }

  return response;
}

export const api = {
  getHealth: async (): Promise<HealthResponse> => {
    return request<HealthResponse>("/health", {
      method: "GET",
    });
  },

  login: async (
    credentials: LoginCredentials
  ): Promise<AuthResponse> => {
    const response = await request<AuthResponse>(
      "/api/auth/login",
      {
        method: "POST",
        body: JSON.stringify(credentials),
      }
    );

    return validateAuthResponse(response);
  },

  signup: async (
    credentials: SignupCredentials
  ): Promise<AuthResponse> => {
    const response = await request<AuthResponse>(
      "/api/auth/signup",
      {
        method: "POST",
        body: JSON.stringify(credentials),
      }
    );

    return validateAuthResponse(response);
  },

  listDatasets: async (
    limit = 20,
    offset = 0
  ): Promise<DatasetListResponse> => {
    return request<DatasetListResponse>(
      `/datasets?limit=${limit}&offset=${offset}`,
      {
        method: "GET",
      }
    );
  },

  getDataset: async (
    datasetId: string
  ): Promise<DatasetDetailResponse> => {
    return request<DatasetDetailResponse>(
      `/datasets/${encodeURIComponent(datasetId)}`,
      {
        method: "GET",
      }
    );
  },

  getDatasetPreview: async (
    datasetId: string,
    rows = 10
  ): Promise<DatasetPreviewResponse> => {
    return request<DatasetPreviewResponse>(
      `/datasets/${encodeURIComponent(datasetId)}/preview?rows=${rows}`,
      {
        method: "GET",
      }
    );
  },

  listDatasetHistory: async (
    datasetId: string,
    limit = 20,
    offset = 0
  ): Promise<AnalysisHistoryListResponse> => {
    return request<AnalysisHistoryListResponse>(
      `/datasets/${encodeURIComponent(datasetId)}/history?limit=${limit}&offset=${offset}`,
      {
        method: "GET",
      }
    );
  },

  listAnalysisHistory: async (
    limit = 20,
    offset = 0
  ): Promise<AnalysisHistoryListResponse> => {
    return request<AnalysisHistoryListResponse>(
      `/analysis-history?limit=${limit}&offset=${offset}`,
      {
        method: "GET",
      }
    );
  },

  predictProfit: async (
    data: ProfitPredictionRequest
  ): Promise<ProfitPredictionResponse> => {
    return request<ProfitPredictionResponse>(
      "/ml/predict-profit",
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    );
  },

  analyzeRisk: async (
    data: RiskAnalysisRequest
  ): Promise<RiskAnalysisBackendResponse> => {
    return request<RiskAnalysisBackendResponse>(
      "/analyze-risk",
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    );
  },

  runWhatIf: async (
    data: WhatIfRequest
  ): Promise<WhatIfResponse> => {
    return request<WhatIfResponse>(
      "/what-if",
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    );
  },

  getDecisionRecommendations: async (
    data: DecisionRecommendationRequest
  ): Promise<DecisionRecommendationResponse> => {
    return request<DecisionRecommendationResponse>(
      "/decision/recommend",
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    );
  },

  getForecastNextDay: async (): Promise<ForecastNextDayResponse> => {
    return request<ForecastNextDayResponse>("/forecast/next-day", {
      method: "GET",
    });
  },

  runAgentWorkflow: async (
    data: { dataset_id: string; user_query?: string }
  ): Promise<AgentWorkflowResponse> => {
    return request<AgentWorkflowResponse>("/agents/run", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
};

export interface AgentWorkflowResponse {
  success: boolean;
  dataset_id: string;
  user_query: string;
  status: "completed" | "partial" | "failed";
  errors: string[];
  analytics?: {
    total_revenue?: number;
    total_expenses?: number;
    total_profit?: number;
    profit_margin?: number;
    key_findings?: string[];
    recommendations?: string[];
    product_performance?: Array<{
      product: string;
      revenue: number;
      expense: number;
      profit: number;
      profit_margin_pct?: number;
    }>;
    monthly_trends?: Array<{
      period?: string;
      month?: string;
      revenue: number;
      expense: number;
      profit: number;
    }>;
    summary?: string;
  };
  risk?: {
    risk_score: number;
    risk_level: "low" | "medium" | "high" | "critical";
    anomaly_detected: boolean;
    anomaly_count?: number;
    predicted_profit?: number;
    key_risks?: string[];
    findings?: Array<{
      risk_type: string;
      severity: string;
      description: string;
      recommended_action?: string;
    }>;
    summary?: string;
  };
  decision?: {
    overall_priority: "low" | "medium" | "high" | "critical";
    recommended_strategy: string;
    alternative_strategies?: string[];
    actions?: Array<{
      action: string;
      priority: string;
      expected_impact?: string;
      reason: string;
      risk?: string;
    }>;
    scenarios?: Array<{
      scenario_name: string;
      projected_revenue: number;
      projected_expenses: number;
      projected_profit: number;
      profit_delta: number;
    }>;
    human_approval_required: boolean;
    summary?: string;
  };
  final_report?: {
    executive_summary: string;
    business_health_status: string;
    overall_risk_level: string;
    risk_score: number;
    financial_highlights?: Record<string, number>;
    key_insights?: string[];
    immediate_actions?: Array<{
      action: string;
      priority: string;
      reason: string;
    }>;
    governance_disclaimer: string;
  };
  analysis_id?: string;
  created_at?: number;
}

