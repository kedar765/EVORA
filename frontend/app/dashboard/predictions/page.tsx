"use client";

import React from "react";
import Link from "next/link";
import {
  ArrowRight,
  GitCompare,
  Sliders,
  Cpu,
} from "lucide-react";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import MlPrediction from "@/components/dashboard/MlPrediction";

export default function PredictionsPage() {
  const { uploadResult, isUploading } = useDashboard();
  const hasData = !!uploadResult;

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
