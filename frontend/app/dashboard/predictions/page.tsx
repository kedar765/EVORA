"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  GitCompare,
  Sliders,
  Cpu,
  Calendar,
  TrendingUp,
  Activity,
  CheckCircle2,
  RefreshCw,
} from "lucide-react";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import MlPrediction from "@/components/dashboard/MlPrediction";
import { formatINR } from "@/components/dashboard/types";
import { api, type ForecastNextDayResponse } from "@/lib/api";

export default function PredictionsPage() {
  const { uploadResult, isUploading } = useDashboard();
  const hasData = !!uploadResult;

  const [forecast, setForecast] = useState<ForecastNextDayResponse | null>(null);
  const [forecastLoading, setForecastLoading] = useState(true);
  const [forecastError, setForecastError] = useState<string | null>(null);

  const fetchForecast = useCallback(async () => {
    try {
      const data = await api.getForecastNextDay();
      setForecast(data);
      setForecastError(null);
    } catch (err: unknown) {
      setForecastError(
        err instanceof Error
          ? err.message
          : "Failed to load next-day profit forecast."
      );
    } finally {
      setForecastLoading(false);
    }
  }, []);

  const handleRefreshForecast = () => {
    setForecastLoading(true);
    setForecastError(null);
    void fetchForecast();
  };

  useEffect(() => {
  let isActive = true;

  api.getForecastNextDay()
    .then((data) => {
      if (!isActive) return;

      setForecast(data);
      setForecastError(null);
    })
    .catch((err: unknown) => {
      if (!isActive) return;

      setForecastError(
        err instanceof Error
          ? err.message
          : "Failed to load next-day profit forecast."
      );
    })
    .finally(() => {
      if (isActive) {
        setForecastLoading(false);
      }
    });

  return () => {
    isActive = false;
  };
}, []);

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
            Predictions
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Supervised Random Forest regression estimating net business profitability from transaction volume and cost features.
          </p>
        </div>

        <Link
          href="/dashboard/decision"
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-semibold border border-blue-200/80 transition-colors self-start sm:self-auto cursor-pointer"
        >
          <GitCompare className="w-3.5 h-3.5" />
          <span>Launch What-If Simulation</span>
        </Link>
      </div>

      {!hasData && (
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200/90 text-sm">
          <div>
            <span className="font-semibold text-slate-800 block">
              Random Forest Model on Standby
            </span>
            <span className="text-xs text-slate-500">
              Upload a transaction CSV with Quantity, Revenue, and Expense to execute feature engineering and calculate profit projections.
            </span>
          </div>

          <Link
            href="/dashboard"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition-colors shrink-0"
          >
            <span>Go to Dashboard</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}

      {/* Next-Day Future Profit Forecasting Card */}
      <section aria-labelledby="forecast-heading" className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-100 pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-50 text-emerald-600">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 id="forecast-heading" className="text-lg font-bold text-slate-900">
                  Next-Day Profit Forecast
                </h2>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-100 text-emerald-800">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>Production Live</span>
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Leakage-safe chronological time series regression predicting the next business day&apos;s net profit.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-medium px-2.5 py-1 rounded bg-slate-100 text-slate-700 border border-slate-200">
              {forecast?.model_name || "ExtraTreesRegressor"} v{forecast?.model_version || "2.0.0"}
            </span>
            <button
              onClick={handleRefreshForecast}
              disabled={forecastLoading}
              className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:text-slate-800 hover:bg-slate-50 transition-colors disabled:opacity-50 cursor-pointer"
              title="Refresh Forecast"
            >
              <RefreshCw className={`w-4 h-4 ${forecastLoading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {forecastLoading ? (
          <div className="py-8 flex flex-col items-center justify-center gap-2">
            <div className="w-6 h-6 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin" />
            <p className="text-xs text-slate-500">Generating next-day profit forecast...</p>
          </div>
        ) : forecastError ? (
          <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-800 flex items-center justify-between">
            <span>{forecastError}</span>
            <button
              onClick={handleRefreshForecast}
              className="px-2.5 py-1 rounded bg-amber-200 text-amber-900 font-semibold hover:bg-amber-300 transition-colors"
            >
              Retry
            </button>
          </div>
        ) : forecast ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
                <span className="text-xs font-medium text-slate-500 flex items-center gap-1.5 mb-1">
                  <Calendar className="w-3.5 h-3.5 text-slate-400" />
                  <span>Forecast Date</span>
                </span>
                <span className="text-xl font-bold text-slate-900 tracking-tight font-mono">
                  {forecast.forecast_date}
                </span>
                <span className="block text-[11px] text-slate-500 mt-1">
                  Next Business Day
                </span>
              </div>

              <div className="p-4 rounded-xl bg-emerald-50/60 border border-emerald-200/70 sm:col-span-2">
                <span className="text-xs font-semibold text-emerald-800 flex items-center gap-1.5 mb-1">
                  <Activity className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Predicted Next-Day Profit</span>
                </span>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl sm:text-3xl font-extrabold text-emerald-900 tracking-tight font-mono">
                    {formatINR(forecast.predicted_profit)}
                  </span>
                  <span className="text-xs font-semibold text-emerald-700 uppercase">
                    {forecast.currency}
                  </span>
                </div>
                <span className="block text-[11px] text-emerald-700/90 mt-1">
                  Computed from strictly historical lags (shift 1+) & rolling statistics
                </span>
              </div>
            </div>

            {/* Model Evaluation Metrics */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                  Untouched Test Set Evaluation Metrics
                </span>
                <span className="text-[11px] text-slate-500">
                  Evaluated on 151 Chronological Out-of-Sample Days
                </span>
              </div>
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="p-2.5 rounded-lg bg-white border border-slate-200/70 shadow-2xs">
                  <span className="text-[11px] text-slate-500 block">Mean Absolute Error (MAE)</span>
                  <strong className="text-sm sm:text-base font-bold text-slate-800 font-mono">
                    ₹{forecast.model_metrics.mae.toFixed(2)}
                  </strong>
                </div>
                <div className="p-2.5 rounded-lg bg-white border border-slate-200/70 shadow-2xs">
                  <span className="text-[11px] text-slate-500 block">Root Mean Squared Error (RMSE)</span>
                  <strong className="text-sm sm:text-base font-bold text-slate-800 font-mono">
                    ₹{forecast.model_metrics.rmse.toFixed(2)}
                  </strong>
                </div>
                <div className="p-2.5 rounded-lg bg-white border border-slate-200/70 shadow-2xs">
                  <span className="text-[11px] text-slate-500 block">R² Score</span>
                  <strong className="text-sm sm:text-base font-bold text-slate-800 font-mono">
                    {forecast.model_metrics.r2.toFixed(4)}
                  </strong>
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </section>

      {/* Main ML Prediction Component */}
      <section aria-labelledby="ml-inference-heading">
        <MlPrediction
          predictedProfit={uploadResult?.predicted_profit}
          actualMetrics={uploadResult?.metrics}
          isLoading={isUploading}
        />
      </section>

      {/* Architecture Transparency */}
      <section aria-labelledby="architecture-heading" className="space-y-3">
        <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider">
          Model Specifications & Feature Engineering
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-800">
              <Sliders className="w-4 h-4 text-blue-600" />
              <span>Prepared Feature Vector (6 Inputs)</span>
            </div>

            <div className="space-y-2 text-xs">
              <div className="p-2 rounded bg-slate-50 border border-slate-200/70 flex justify-between">
                <span className="font-semibold text-slate-700">Quantity</span>
                <span className="text-slate-500">Units sold per transaction record</span>
              </div>
              <div className="p-2 rounded bg-slate-50 border border-slate-200/70 flex justify-between">
                <span className="font-semibold text-slate-700">Revenue</span>
                <span className="text-slate-500">Monetary receipts generated (₹)</span>
              </div>
              <div className="p-2 rounded bg-slate-50 border border-slate-200/70 flex justify-between">
                <span className="font-semibold text-slate-700">Expense</span>
                <span className="text-slate-500">Operational costs incurred (₹)</span>
              </div>
              <div className="p-2 rounded bg-slate-50 border border-slate-200/70 flex justify-between">
                <span className="font-semibold text-slate-700">Profit Margin</span>
                <span className="text-slate-500">(Revenue − Expense) / Revenue</span>
              </div>
              <div className="p-2 rounded bg-slate-50 border border-slate-200/70 flex justify-between">
                <span className="font-semibold text-slate-700">Revenue per Unit</span>
                <span className="text-slate-500">Normalized Revenue / Quantity</span>
              </div>
              <div className="p-2 rounded bg-slate-50 border border-slate-200/70 flex justify-between">
                <span className="font-semibold text-slate-700">Expense per Unit</span>
                <span className="text-slate-500">Normalized Expense / Quantity</span>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-xs flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-800">
                <Cpu className="w-4 h-4 text-blue-600" />
                <span>Model Architecture</span>
              </div>

              <div className="space-y-2 text-xs text-slate-600">
                <div className="flex justify-between py-1.5 border-b border-slate-100">
                  <span className="text-slate-500">Algorithm</span>
                  <strong className="font-semibold text-slate-800">Scikit-learn RandomForestRegressor</strong>
                </div>
                <div className="flex justify-between py-1.5 border-b border-slate-100">
                  <span className="text-slate-500">Target Feature</span>
                  <strong className="font-semibold text-slate-800">Net Profit (₹)</strong>
                </div>
                <div className="flex justify-between py-1.5 border-b border-slate-100">
                  <span className="text-slate-500">Ensemble Type</span>
                  <strong className="font-semibold text-slate-800">Bootstrap Bagging & Averaging</strong>
                </div>
                <div className="flex justify-between py-1.5">
                  <span className="text-slate-500">Artifact Source</span>
                  <strong className="font-semibold text-slate-800 font-mono text-[11px]">backend/ml/profit_model.pkl</strong>
                </div>
              </div>
            </div>

            <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200/80 text-xs text-slate-600 leading-relaxed">
              <strong className="font-semibold text-slate-800">Human Governance:</strong> Model estimates assist human analysis. EVORA does not execute business decisions automatically.
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
