
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
    const response = await fetch(
      `${API_BASE_URL}${endpoint}`,
      {
        ...options,
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...options.headers,
        },
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

