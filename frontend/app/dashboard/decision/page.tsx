"use client";

import React from "react";
import Link from "next/link";
import {
  BrainCircuit,
  ArrowRight,
  ShieldCheck,
  Clock,
} from "lucide-react";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import WhatIfAnalysis from "@/components/dashboard/WhatIfAnalysis";

export default function DecisionSupportPage() {
  const { uploadResult } = useDashboard();
  const currentMetrics = uploadResult?.metrics || null;
  const hasData = !!uploadResult;

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
            What-If Scenario Simulation
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Simulate and contrast prospective sales volumes, pricing targets, and operational expense shifts against current baseline performance.
          </p>
        </div>

        <Link
          href="/dashboard/predictions"
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold border border-indigo-200/80 transition-colors self-start sm:self-auto cursor-pointer"
        >
          <BrainCircuit className="w-3.5 h-3.5" />
          <span>View ML Predictions</span>
        </Link>
      </div>

      {!hasData && (
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200/90 text-sm">
          <div>
            <span className="font-semibold text-slate-800 block">
              No Current Baseline Loaded
            </span>
            <span className="text-xs text-slate-500">
              Upload a transaction dataset on the Dashboard to populate baseline metrics automatically, or enter manual figures below.
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

      {/* Main What-If Scenario Simulation Component */}
      <section aria-labelledby="what-if-heading">
        <WhatIfAnalysis currentMetrics={currentMetrics} />
      </section>

      {/* Governance & Future Optimization Roadmap */}
      <section aria-labelledby="roadmap-heading" className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider">
            Prescriptive Optimization Roadmap
          </h2>
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200/80">
            <Clock className="w-3 h-3 text-amber-600" />
            <span>Coming Soon</span>
          </span>
        </div>

        <div className="bg-white rounded-xl border border-slate-200/90 p-5 sm:p-6 shadow-xs space-y-4">
          <p className="text-xs text-slate-500 max-w-2xl leading-relaxed">
            While interactive What-If scenario comparison is fully active above, future EVORA versions will incorporate mathematical constraint optimization to recommend target price-volume points automatically.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200/70 space-y-1">
              <span className="font-bold text-slate-800 block">Pareto Frontier Analysis</span>
              <p className="text-slate-500 text-[11px] leading-tight">
                Algorithmic discovery of optimal trade-offs between volume growth and operational expenditure.
              </p>
            </div>

            <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200/70 space-y-1">
              <span className="font-bold text-slate-800 block">Automated Price Elasticity</span>
              <p className="text-slate-500 text-[11px] leading-tight">
                Sensitivity simulations testing demand retention across progressive price increment steps.
              </p>
            </div>

            <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200/70 space-y-1">
              <span className="font-bold text-slate-800 block">Executive Approval Gates</span>
              <p className="text-slate-500 text-[11px] leading-tight">
                Mandatory human review requirements ensuring no business decisions execute without user sign-off.
              </p>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-100 flex items-start gap-2 text-xs text-slate-500">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            <p className="leading-relaxed">
              <strong>Human-in-the-Loop Governance:</strong> EVORA provides decision-support evidence and scenario estimates. Final operational and pricing execution remains under human control.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
