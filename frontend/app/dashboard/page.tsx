"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

type UploadResult = {
  success: boolean;
  message: string;
  filename: string;
  rows_processed: number;
  metrics: {
    total_revenue: number;
    total_expense: number;
    total_profit: number;
    total_sales: number;
    average_revenue: number;
    average_expense: number;
    average_profit: number;
    profit_margin: number;
  };
  predicted_profit: number | null;
};

type AnalyticsResult = {
  success: boolean;
  analysis: {
    total_revenue: number;
    total_expense: number;
    total_profit: number;
    profit_margin: number;
    insights: string[];
  };
};

type ProfitPredictionResult = {
  success: boolean;
  predicted_profit: number;
};

type RiskAnalysisResult = {
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
};

type WhatIfResult = {
  success: boolean;
  current_predicted_profit: number;
  new_predicted_profit: number;
  profit_difference: number;
  result: string;
};

export default function DashboardPage() {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const router = useRouter();

  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadError, setUploadError] = useState("");

  const [analyticsResult, setAnalyticsResult] =
    useState<AnalyticsResult | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsError, setAnalyticsError] = useState("");

  const [profitQuantity, setProfitQuantity] = useState("");
  const [profitRevenue, setProfitRevenue] = useState("");
  const [profitExpense, setProfitExpense] = useState("");
  const [profitResult, setProfitResult] =
    useState<ProfitPredictionResult | null>(null);
  const [profitLoading, setProfitLoading] = useState(false);
  const [profitError, setProfitError] = useState("");

  const [riskQuantity, setRiskQuantity] = useState("");
  const [riskRevenue, setRiskRevenue] = useState("");
  const [riskExpense, setRiskExpense] = useState("");
  const [riskResult, setRiskResult] =
    useState<RiskAnalysisResult | null>(null);
  const [riskLoading, setRiskLoading] = useState(false);
  const [riskError, setRiskError] = useState("");

  const [currentQuantity, setCurrentQuantity] = useState("");
  const [currentRevenue, setCurrentRevenue] = useState("");
  const [currentExpense, setCurrentExpense] = useState("");

  const [newQuantity, setNewQuantity] = useState("");
  const [newRevenue, setNewRevenue] = useState("");
  const [newExpense, setNewExpense] = useState("");

  const [result, setResult] = useState<WhatIfResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading || !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <p className="text-sm font-semibold text-slate-500">
          Verifying session...
        </p>
      </div>
    );
  }

  const displayName =
    user?.name || user?.email?.split("@")[0] || "User";

  const handleUpload = async () => {
    setUploadError("");
    setUploadResult(null);
    setAnalyticsResult(null);
    setAnalyticsError("");

    if (!uploadFile) {
      setUploadError("Please select a CSV file.");
      return;
    }

    setUploadLoading(true);
    setAnalyticsLoading(true);

    try {
      const uploadFormData = new FormData();
      uploadFormData.append("file", uploadFile);

      const uploadResponse = await fetch(
        "http://127.0.0.1:8000/upload",
        {
          method: "POST",
          body: uploadFormData,
        }
      );

      const uploadData = await uploadResponse.json();

      if (!uploadResponse.ok) {
        throw new Error(
          typeof uploadData.detail === "string"
            ? uploadData.detail
            : uploadData.detail?.message || "Upload failed."
        );
      }

      setUploadResult(uploadData);

      const analyticsFormData = new FormData();
      analyticsFormData.append("file", uploadFile);

      const analyticsResponse = await fetch(
        "http://127.0.0.1:8000/analytics",
        {
          method: "POST",
          body: analyticsFormData,
        }
      );

      const analyticsData = await analyticsResponse.json();

      if (!analyticsResponse.ok) {
        throw new Error(
          typeof analyticsData.detail === "string"
            ? analyticsData.detail
            : analyticsData.detail?.message ||
                "Analytics analysis failed."
        );
      }

      setAnalyticsResult(analyticsData);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to connect to EVORA backend.";

      if (!uploadResult) {
        setUploadError(message);
      } else {
        setAnalyticsError(message);
      }
    } finally {
      setUploadLoading(false);
      setAnalyticsLoading(false);
    }
  };

  const handleProfitPrediction = async () => {
    setProfitError("");
    setProfitResult(null);

    if (!profitQuantity || !profitRevenue || !profitExpense) {
      setProfitError("Please enter Quantity, Revenue and Expense.");
      return;
    }

    setProfitLoading(true);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/ml/predict-profit",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            Quantity: Number(profitQuantity),
            Revenue: Number(profitRevenue),
            Expense: Number(profitExpense),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : data.detail?.message || "Profit prediction failed."
        );
      }

      setProfitResult(data);
    } catch (err) {
      setProfitError(
        err instanceof Error
          ? err.message
          : "Unable to connect to EVORA backend."
      );
    } finally {
      setProfitLoading(false);
    }
  };

  const handleRiskAnalysis = async () => {
    setRiskError("");
    setRiskResult(null);

    if (!riskQuantity || !riskRevenue || !riskExpense) {
      setRiskError("Please enter Quantity, Revenue and Expense.");
      return;
    }

    setRiskLoading(true);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/analyze-risk",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            Quantity: Number(riskQuantity),
            Revenue: Number(riskRevenue),
            Expense: Number(riskExpense),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : data.detail?.message || "Risk analysis failed."
        );
      }

      setRiskResult(data);
    } catch (err) {
      setRiskError(
        err instanceof Error
          ? err.message
          : "Unable to connect to EVORA backend."
      );
    } finally {
      setRiskLoading(false);
    }
  };

  const handleRiskReset = () => {
    setRiskQuantity("");
    setRiskRevenue("");
    setRiskExpense("");
    setRiskResult(null);
    setRiskError("");
  };

  const handleWhatIf = async () => {
    setError("");
    setResult(null);

    if (
      !currentQuantity ||
      !currentRevenue ||
      !currentExpense ||
      !newQuantity ||
      !newRevenue ||
      !newExpense
    ) {
      setError("Please enter all business values.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/what-if",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            current_quantity: Number(currentQuantity),
            current_revenue: Number(currentRevenue),
            current_expense: Number(currentExpense),
            new_quantity: Number(newQuantity),
            new_revenue: Number(newRevenue),
            new_expense: Number(newExpense),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : data.detail?.message || "Something went wrong."
        );
      }

      setResult(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to connect to EVORA backend."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleWhatIfReset = () => {
    setCurrentQuantity("");
    setCurrentRevenue("");
    setCurrentExpense("");
    setNewQuantity("");
    setNewRevenue("");
    setNewExpense("");
    setResult(null);
    setError("");
  };

  const isIncrease = result && result.profit_difference > 0;
  const isDecrease = result && result.profit_difference < 0;

  const riskLevelStyle =
    riskResult?.risk_level === "HIGH"
      ? "bg-red-100 text-red-700"
      : riskResult?.risk_level === "MEDIUM"
      ? "bg-yellow-100 text-yellow-700"
      : "bg-green-100 text-green-700";

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <p className="text-sm font-bold text-blue-700">
              EVORA Dashboard
            </p>

            <h1 className="text-3xl sm:text-4xl font-black text-slate-900 tracking-tight">
              Welcome, {displayName}
            </h1>

            <p className="text-sm text-slate-500 mt-1">
              Explore business scenarios and understand possible outcomes.
            </p>
          </div>

          <button
            onClick={logout}
            className="self-start sm:self-auto px-5 py-2.5 rounded-xl text-sm font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            Sign Out
          </button>
        </div>

        <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 sm:p-8 mb-6">
          <div className="mb-6">
            <p className="text-sm font-bold text-blue-700">
              Business Data
            </p>

            <h2 className="text-2xl sm:text-3xl font-black text-slate-900 mt-1">
              CSV Upload
            </h2>

            <p className="text-sm text-slate-500 mt-2 max-w-2xl">
              Upload business data to analyze revenue, expense, profit and
              sales.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-4">
            <input
              type="file"
              accept=".csv"
              onChange={(e) => {
                setUploadFile(e.target.files?.[0] || null);
                setUploadResult(null);
                setUploadError("");
                setAnalyticsResult(null);
                setAnalyticsError("");
              }}
              className="flex-1 px-4 py-3 rounded-xl border border-slate-200 bg-white"
            />

            <button
              onClick={handleUpload}
              disabled={uploadLoading}
              className="px-6 py-3 rounded-xl bg-blue-700 text-white font-bold hover:bg-blue-800 disabled:opacity-60 transition-colors cursor-pointer"
            >
              {uploadLoading ? "Analyzing..." : "Upload CSV"}
            </button>
          </div>

          {uploadError && (
            <div className="mt-4 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm font-semibold text-red-700">
              {uploadError}
            </div>
          )}

          {uploadResult && (
            <div className="mt-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="rounded-2xl bg-slate-50 border border-slate-200 p-5">
                  <p className="text-sm text-slate-500">Total Revenue</p>
                  <p className="text-2xl font-black text-slate-900 mt-2">
                    ₹{uploadResult.metrics.total_revenue.toLocaleString()}
                  </p>
                </div>

                <div className="rounded-2xl bg-slate-50 border border-slate-200 p-5">
                  <p className="text-sm text-slate-500">Total Expense</p>
                  <p className="text-2xl font-black text-slate-900 mt-2">
                    ₹{uploadResult.metrics.total_expense.toLocaleString()}
                  </p>
                </div>

                <div className="rounded-2xl bg-slate-50 border border-slate-200 p-5">
                  <p className="text-sm text-slate-500">Total Profit</p>
                  <p className="text-2xl font-black text-slate-900 mt-2">
                    ₹{uploadResult.metrics.total_profit.toLocaleString()}
                  </p>
                </div>

                <div className="rounded-2xl bg-blue-50 border border-blue-100 p-5">
                  <p className="text-sm text-slate-500">
                    Predicted Profit
                  </p>

                  <p className="text-2xl font-black text-blue-700 mt-2">
                    ₹
                    {uploadResult.predicted_profit !== null
                      ? uploadResult.predicted_profit.toLocaleString()
                      : "N/A"}
                  </p>
                </div>
              </div>

              <div className="mt-4 text-sm text-slate-600">
                File:{" "}
                <span className="font-semibold">
                  {uploadResult.filename}
                </span>
                {" • "}
                Rows:{" "}
                <span className="font-semibold">
                  {uploadResult.rows_processed}
                </span>
                {" • "}
                Profit Margin:{" "}
                <span className="font-semibold">
                  {uploadResult.metrics.profit_margin.toFixed(2)}%
                </span>
              </div>
            </div>
          )}

          {analyticsLoading && (
            <div className="mt-6 rounded-2xl bg-blue-50 border border-blue-100 p-5">
              <p className="text-sm font-semibold text-blue-700">
                EVORA Analytics Agent is analyzing your business data...
              </p>
            </div>
          )}

          {analyticsError && (
            <div className="mt-6 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm font-semibold text-red-700">
              {analyticsError}
            </div>
          )}

          {analyticsResult && (
            <div className="mt-8">
              <div className="mb-5">
                <p className="text-sm font-bold text-blue-700">
                  AI Business Intelligence
                </p>

                <h3 className="text-xl sm:text-2xl font-black text-slate-900 mt-1">
                  Analytics Agent Result
                </h3>

                <p className="text-sm text-slate-500 mt-1">
                  EVORA analyzed the uploaded business data.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="rounded-2xl bg-slate-50 border border-slate-200 p-5">
                  <p className="text-sm text-slate-500">
                    Total Revenue
                  </p>

                  <p className="text-2xl font-black text-slate-900 mt-2">
                    ₹
                    {analyticsResult.analysis.total_revenue.toLocaleString()}
                  </p>
                </div>

                <div className="rounded-2xl bg-slate-50 border border-slate-200 p-5">
                  <p className="text-sm text-slate-500">
                    Total Expense
                  </p>

                  <p className="text-2xl font-black text-slate-900 mt-2">
                    ₹
                    {analyticsResult.analysis.total_expense.toLocaleString()}
                  </p>
                </div>

                <div className="rounded-2xl bg-blue-50 border border-blue-100 p-5">
                  <p className="text-sm text-slate-500">
                    Total Profit
                  </p>

                  <p className="text-2xl font-black text-blue-700 mt-2">
                    ₹
                    {analyticsResult.analysis.total_profit.toLocaleString()}
                  </p>
                </div>

                <div className="rounded-2xl bg-green-50 border border-green-100 p-5">
                  <p className="text-sm text-slate-500">
                    Profit Margin
                  </p>

                  <p className="text-2xl font-black text-green-700 mt-2">
                    {analyticsResult.analysis.profit_margin.toFixed(2)}%
                  </p>
                </div>
              </div>

              <div className="mt-6 rounded-2xl bg-blue-50 border border-blue-100 p-5">
                <div className="flex items-center gap-2 mb-4">
                  <span className="text-xl">💡</span>

                  <h4 className="text-lg font-black text-slate-900">
                    Business Insights
                  </h4>
                </div>

                <div className="space-y-3">
                  {analyticsResult.analysis.insights.map(
                    (insight, index) => (
                      <div
                        key={index}
                        className="flex items-start gap-3"
                      >
                        <span className="text-blue-700 font-black mt-0.5">
                          •
                        </span>

                        <p className="text-sm font-semibold text-slate-700">
                          {insight}
                        </p>
                      </div>
                    )
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 sm:p-8 mb-6">
          <div className="mb-6">
            <p className="text-sm font-bold text-blue-700">
              Machine Learning
            </p>

            <h2 className="text-2xl sm:text-3xl font-black text-slate-900 mt-1">
              Profit Prediction
            </h2>

            <p className="text-sm text-slate-500 mt-2 max-w-2xl">
              Enter business values to predict the expected profit.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                Quantity
              </label>

              <input
                type="number"
                value={profitQuantity}
                onChange={(e) => setProfitQuantity(e.target.value)}
                placeholder="e.g. 100"
                className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                Revenue
              </label>

              <input
                type="number"
                value={profitRevenue}
                onChange={(e) => setProfitRevenue(e.target.value)}
                placeholder="e.g. 50000"
                className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                Expense
              </label>

              <input
                type="number"
                value={profitExpense}
                onChange={(e) => setProfitExpense(e.target.value)}
                placeholder="e.g. 30000"
                className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <button
            onClick={handleProfitPrediction}
            disabled={profitLoading}
            className="w-full mt-6 py-3.5 rounded-xl bg-blue-700 text-white font-bold hover:bg-blue-800 disabled:opacity-60 transition-colors cursor-pointer"
          >
            {profitLoading ? "Predicting Profit..." : "Predict Profit"}
          </button>

          {profitError && (
            <div className="mt-5 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm font-semibold text-red-700">
              {profitError}
            </div>
          )}

          {profitResult && (
            <div className="mt-6 rounded-2xl bg-blue-50 border border-blue-100 p-6">
              <p className="text-sm font-semibold text-slate-500">
                Predicted Profit
              </p>

              <p className="text-3xl font-black text-blue-700 mt-2">
                ₹{profitResult.predicted_profit.toLocaleString()}
              </p>
            </div>
          )}
        </div>

        <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 sm:p-8 mb-6">
          <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3 mb-8">
            <div>
              <p className="text-sm font-bold text-blue-700">
                Risk Management
              </p>

              <h2 className="text-2xl sm:text-3xl font-black text-slate-900 mt-1">
                Risk Analysis
              </h2>

              <p className="text-sm text-slate-500 mt-2 max-w-2xl">
                Analyze business values to detect unusual patterns and
                calculate the current risk level.
              </p>
            </div>

            <button
              onClick={handleRiskReset}
              className="px-4 py-2 rounded-xl text-sm font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 transition-colors cursor-pointer"
            >
              Reset
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                Quantity
              </label>

              <input
                type="number"
                value={riskQuantity}
                onChange={(e) => setRiskQuantity(e.target.value)}
                placeholder="e.g. 100"
                className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                Revenue
              </label>

              <input
                type="number"
                value={riskRevenue}
                onChange={(e) => setRiskRevenue(e.target.value)}
                placeholder="e.g. 50000"
                className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                Expense
              </label>

              <input
                type="number"
                value={riskExpense}
                onChange={(e) => setRiskExpense(e.target.value)}
                placeholder="e.g. 30000"
                className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <button
            onClick={handleRiskAnalysis}
            disabled={riskLoading}
            className="w-full mt-6 py-3.5 rounded-xl bg-blue-700 text-white font-bold hover:bg-blue-800 disabled:opacity-60 transition-colors cursor-pointer"
          >
            {riskLoading ? "Analyzing Risk..." : "Analyze Risk"}
          </button>

          {riskError && (
            <div className="mt-5 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm font-semibold text-red-700">
              {riskError}
            </div>
          )}

          {riskResult && (
            <div className="mt-8">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="rounded-2xl bg-slate-50 border border-slate-200 p-5">
                  <p className="text-sm text-slate-500">
                    Predicted Profit
                  </p>

                  <p className="text-2xl font-black text-slate-900 mt-2">
                    ₹{riskResult.predicted_profit.toLocaleString()}
                  </p>
                </div>

                <div className="rounded-2xl bg-slate-50 border border-slate-200 p-5">
                  <p className="text-sm text-slate-500">
                    Anomaly Detection
                  </p>

                  <p
                    className={`text-2xl font-black mt-2 ${
                      riskResult.anomaly_detected
                        ? "text-red-600"
                        : "text-green-600"
                    }`}
                  >
                    {riskResult.anomaly_detected
                      ? "Detected"
                      : "Normal"}
                  </p>
                </div>

                <div className="rounded-2xl bg-blue-50 border border-blue-100 p-5">
                  <p className="text-sm text-slate-500">
                    Risk Score
                  </p>

                  <p className="text-2xl font-black text-blue-700 mt-2">
                    {riskResult.risk_score}/100
                  </p>
                </div>

                <div className="rounded-2xl bg-slate-50 border border-slate-200 p-5">
                  <p className="text-sm text-slate-500">
                    Risk Level
                  </p>

                  <span
                    className={`inline-block mt-2 px-4 py-2 rounded-full text-sm font-black ${riskLevelStyle}`}
                  >
                    {riskResult.risk_level}
                  </span>
                </div>
              </div>

              <div className="mt-6 rounded-2xl border border-slate-200 p-5">
                <div className="flex justify-between text-sm font-semibold text-slate-600 mb-2">
                  <span>Risk Score</span>
                  <span>{riskResult.risk_score}/100</span>
                </div>

                <div className="h-4 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-600 rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.min(
                        100,
                        Math.max(0, riskResult.risk_score)
                      )}%`,
                    }}
                  />
                </div>
              </div>

              <div className="mt-6 rounded-2xl bg-blue-50 border border-blue-100 p-5">
                <div className="flex items-center gap-2 mb-4">
                  <span className="text-xl">🛡️</span>

                  <h4 className="text-lg font-black text-slate-900">
                    Risk Assessment
                  </h4>
                </div>

                <div className="space-y-3">
                  {riskResult.risk_analysis.reasons.map(
                    (reason, index) => (
                      <div
                        key={index}
                        className="flex items-start gap-3"
                      >
                        <span className="text-blue-700 font-black mt-0.5">
                          •
                        </span>

                        <p className="text-sm font-semibold text-slate-700">
                          {reason}
                        </p>
                      </div>
                    )
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 sm:p-8">
          <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3 mb-8">
            <div>
              <p className="text-sm font-bold text-blue-700">
                Decision Support
              </p>

              <h2 className="text-2xl sm:text-3xl font-black text-slate-900 mt-1">
                What-If Analysis
              </h2>

              <p className="text-sm text-slate-500 mt-2 max-w-2xl">
                Modify business values and compare the predicted profit with
                the current scenario.
              </p>
            </div>

            <button
              onClick={handleWhatIfReset}
              className="px-4 py-2 rounded-xl text-sm font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 transition-colors cursor-pointer"
            >
              Reset
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="rounded-2xl bg-slate-50 border border-slate-200 p-5">
              <div className="mb-5">
                <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Scenario 01
                </p>

                <h3 className="text-lg font-bold text-slate-900 mt-1">
                  Current Business
                </h3>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                    Quantity
                  </label>

                  <input
                    type="number"
                    value={currentQuantity}
                    onChange={(e) => setCurrentQuantity(e.target.value)}
                    placeholder="e.g. 100"
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                    Revenue
                  </label>

                  <input
                    type="number"
                    value={currentRevenue}
                    onChange={(e) => setCurrentRevenue(e.target.value)}
                    placeholder="e.g. 50000"
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                    Expense
                  </label>

                  <input
                    type="number"
                    value={currentExpense}
                    onChange={(e) => setCurrentExpense(e.target.value)}
                    placeholder="e.g. 30000"
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>

            <div className="rounded-2xl bg-blue-50 border border-blue-100 p-5">
              <div className="mb-5">
                <p className="text-xs font-bold uppercase tracking-wider text-blue-500">
                  Scenario 02
                </p>

                <h3 className="text-lg font-bold text-slate-900 mt-1">
                  What-If Scenario
                </h3>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                    New Quantity
                  </label>

                  <input
                    type="number"
                    value={newQuantity}
                    onChange={(e) => setNewQuantity(e.target.value)}
                    placeholder="e.g. 120"
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                    New Revenue
                  </label>

                  <input
                    type="number"
                    value={newRevenue}
                    onChange={(e) => setNewRevenue(e.target.value)}
                    placeholder="e.g. 60000"
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                    New Expense
                  </label>

                  <input
                    type="number"
                    value={newExpense}
                    onChange={(e) => setNewExpense(e.target.value)}
                    placeholder="e.g. 32000"
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>
          </div>

          <button
            onClick={handleWhatIf}
            disabled={loading}
            className="w-full mt-6 py-3.5 rounded-xl bg-blue-700 text-white font-bold hover:bg-blue-800 disabled:opacity-60 transition-colors cursor-pointer"
          >
            {loading ? "Analyzing Scenario..." : "Run What-If Analysis"}
          </button>

          {error && (
            <div className="mt-5 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm font-semibold text-red-700">
              {error}
            </div>
          )}

          {result && (
            <div className="mt-8">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-sm font-bold text-blue-700">
                    Analysis Complete
                  </p>

                  <h3 className="text-xl font-black text-slate-900 mt-1">
                    Scenario Comparison
                  </h3>
                </div>

                <div
                  className={`px-4 py-2 rounded-full text-sm font-bold ${
                    isIncrease
                      ? "bg-green-100 text-green-700"
                      : isDecrease
                      ? "bg-red-100 text-red-700"
                      : "bg-slate-100 text-slate-700"
                  }`}
                >
                  {isIncrease
                    ? "↑ Profit Increase"
                    : isDecrease
                    ? "↓ Profit Decrease"
                    : "→ No Change"}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="rounded-2xl bg-slate-50 border border-slate-200 p-5">
                  <p className="text-sm text-slate-500">
                    Current Predicted Profit
                  </p>

                  <p className="text-2xl font-black text-slate-900 mt-2">
                    ₹{result.current_predicted_profit.toLocaleString()}
                  </p>
                </div>

                <div className="rounded-2xl bg-blue-50 border border-blue-100 p-5">
                  <p className="text-sm text-slate-500">
                    New Predicted Profit
                  </p>

                  <p className="text-2xl font-black text-blue-700 mt-2">
                    ₹{result.new_predicted_profit.toLocaleString()}
                  </p>
                </div>

                <div className="rounded-2xl bg-slate-50 border border-slate-200 p-5">
                  <p className="text-sm text-slate-500">
                    Profit Difference
                  </p>

                  <p
                    className={`text-2xl font-black mt-2 ${
                      isIncrease
                        ? "text-green-600"
                        : isDecrease
                        ? "text-red-600"
                        : "text-slate-900"
                    }`}
                  >
                    {result.profit_difference >= 0 ? "+" : ""}
                    ₹{result.profit_difference.toLocaleString()}
                  </p>
                </div>
              </div>

              <div className="mt-6 rounded-2xl border border-slate-200 p-5">
                <div className="flex justify-between text-sm font-semibold text-slate-600 mb-2">
                  <span>Current Profit</span>
                  <span>New Profit</span>
                </div>

                <div className="h-4 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-600 rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.max(
                        5,
                        Math.min(
                          100,
                          (result.current_predicted_profit /
                            Math.max(
                              result.current_predicted_profit,
                              result.new_predicted_profit
                            )) *
                            100
                        )
                      )}%`,
                    }}
                  />
                </div>

                <div className="mt-3 text-center">
                  <span className="text-sm font-semibold text-slate-600">
                    EVORA predicted change:
                  </span>

                  <span
                    className={`ml-2 text-sm font-black ${
                      isIncrease
                        ? "text-green-600"
                        : isDecrease
                        ? "text-red-600"
                        : "text-slate-700"
                    }`}
                  >
                    {result.result}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}