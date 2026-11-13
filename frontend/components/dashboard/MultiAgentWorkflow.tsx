"use client";

import React, { useState } from "react";
import {
  Play,
  CheckCircle2,
  AlertTriangle,
  BrainCircuit,
  FileText,
  Loader2,
  Sparkles,
  ChevronRight,
  ShieldAlert,
  BarChart3,
  Target,
  ArrowRight,
  TrendingUp,
} from "lucide-react";
import { api, type AgentWorkflowResponse } from "@/lib/api";
import { formatINR } from "./types";

interface MultiAgentWorkflowProps {
  datasetId?: string;
  filename?: string;
  hasData: boolean;
}

export default function MultiAgentWorkflow({
  datasetId,
  filename,
  hasData,
}: MultiAgentWorkflowProps) {
  const [query, setQuery] = useState(
    "Analyze business profitability, evaluate operational risks, and generate strategic optimization decisions."
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AgentWorkflowResponse | null>(null);
  const [activeTab, setActiveTab] = useState<"report" | "analytics" | "risk" | "decision">("report");

  const handleRunWorkflow = async () => {
    if (!datasetId) {
      setError("Please upload or select an active dataset first.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.runAgentWorkflow({
        dataset_id: datasetId,
        user_query: query,
      });

      if (!response.success && response.errors?.length) {
        setError(response.errors.join(", "));
      }

      setResult(response);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to run multi-agent workflow.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-xs p-5 sm:p-7 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="w-1.5 h-4 rounded-full bg-indigo-600" />
            <span className="text-xs font-bold uppercase tracking-wider text-indigo-700">
              Autonomous Multi-Agent System
            </span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200/60 uppercase">
              LangGraph
            </span>
          </div>

          <h2 className="text-xl font-bold text-slate-900 tracking-tight">
            Decision Optimization & Reasoning Workflow
          </h2>

          <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-2xl leading-relaxed">
            Coordinated execution of 3 specialized LangChain agents using dedicated Gemini models to profile data, detect operational risks, and simulate decision action plans.
          </p>
        </div>

        {hasData && (
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200/80 text-xs font-medium text-slate-700 self-start sm:self-auto">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>Target: <strong className="text-slate-900">{filename || "Active Dataset"}</strong></span>
          </div>
        )}
      </div>

      {/* 3 Specialized Agents Model Architecture Bar */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 p-3.5 rounded-xl bg-slate-50/80 border border-slate-200/70 text-xs">
        {/* Agent 1 */}
        <div className="flex items-start gap-2.5 p-2 rounded-lg bg-white border border-slate-200/60">
          <div className="w-7 h-7 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
            <BarChart3 className="w-3.5 h-3.5" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center justify-between gap-1">
              <span className="font-bold text-slate-900">Analytics Agent</span>
              <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-blue-50 text-blue-700">
                7 Tools
              </span>
            </div>
            <p className="text-[10px] text-slate-500 font-mono mt-0.5 truncate">
              gemini-3.1-flash-lite
            </p>
          </div>
        </div>

        {/* Agent 2 */}
        <div className="flex items-start gap-2.5 p-2 rounded-lg bg-white border border-slate-200/60">
          <div className="w-7 h-7 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center shrink-0">
            <ShieldAlert className="w-3.5 h-3.5" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center justify-between gap-1">
              <span className="font-bold text-slate-900">Risk Agent</span>
              <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-amber-50 text-amber-700">
                7 Tools
              </span>
            </div>
            <p className="text-[10px] text-slate-500 font-mono mt-0.5 truncate">
              gemini-3.5-flash
            </p>
          </div>
        </div>

        {/* Agent 3 */}
        <div className="flex items-start gap-2.5 p-2 rounded-lg bg-white border border-slate-200/60">
          <div className="w-7 h-7 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0">
            <Target className="w-3.5 h-3.5" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center justify-between gap-1">
              <span className="font-bold text-slate-900">Decision Agent</span>
              <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-indigo-50 text-indigo-700">
                6 Tools
              </span>
            </div>
            <p className="text-[10px] text-slate-500 font-mono mt-0.5 truncate">
              gemini-3.6-flash
            </p>
          </div>
        </div>
      </div>

      {/* Query Input Section */}
      <div className="space-y-2.5">
        <label htmlFor="agent-query" className="text-xs font-semibold text-slate-700 uppercase tracking-wider block">
          Strategic Focus / Business Objective
        </label>
        <div className="flex flex-col sm:flex-row gap-2.5">
          <input
            id="agent-query"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. Which products are eroding margin? What actions should we take?"
            disabled={loading || !hasData}
            className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 disabled:opacity-50 transition-colors"
          />
          <button
            type="button"
            onClick={handleRunWorkflow}
            disabled={loading || !hasData || !datasetId}
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold transition-all shadow-xs hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Executing Workflow...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-white" />
                <span>Execute Multi-Agent Workflow</span>
              </>
            )}
          </button>
        </div>

        {!hasData && (
          <p className="text-xs text-amber-600 font-medium flex items-center gap-1.5 mt-1">
            <AlertTriangle className="w-3.5 h-3.5" />
            Please upload a business CSV dataset from the ingestion tray above to run the multi-agent system.
          </p>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-700 flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <div>
            <strong className="font-semibold block">Execution Notice</strong>
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Results View */}
      {result && (
        <div className="space-y-5 pt-4 border-t border-slate-100">
          {/* Status & Navigation Tabs */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-xl text-xs font-semibold">
              <button
                type="button"
                onClick={() => setActiveTab("report")}
                className={`px-3 py-1.5 rounded-lg transition-all ${
                  activeTab === "report" ? "bg-white text-slate-900 shadow-xs" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Executive Report
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("analytics")}
                className={`px-3 py-1.5 rounded-lg transition-all ${
                  activeTab === "analytics" ? "bg-white text-slate-900 shadow-xs" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Analytics Agent
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("risk")}
                className={`px-3 py-1.5 rounded-lg transition-all ${
                  activeTab === "risk" ? "bg-white text-slate-900 shadow-xs" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Risk Agent
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("decision")}
                className={`px-3 py-1.5 rounded-lg transition-all ${
                  activeTab === "decision" ? "bg-white text-slate-900 shadow-xs" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Decision Agent
              </button>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-slate-500">Pipeline Status:</span>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/80">
                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                {result.status.toUpperCase()}
              </span>
            </div>
          </div>

          {/* TAB 1: Executive Report */}
          {activeTab === "report" && result.final_report && (
            <div className="space-y-4">
              <div className="p-5 rounded-xl bg-gradient-to-r from-blue-50/80 via-indigo-50/80 to-purple-50/80 border border-blue-200/70 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-blue-800">
                    Business Health Assessment
                  </span>
                  <span className="px-2.5 py-0.5 rounded-md text-xs font-bold bg-white text-blue-900 border border-blue-200">
                    {result.final_report.business_health_status}
                  </span>
                </div>
                <p className="text-sm font-medium text-slate-800 leading-relaxed">
                  {result.final_report.executive_summary}
                </p>
              </div>

              {/* Immediate Strategic Actions */}
              {result.final_report.immediate_actions && result.final_report.immediate_actions.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                    Immediate Recommended Interventions
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {result.final_report.immediate_actions.map((act, i) => (
                      <div key={i} className="p-4 rounded-xl border border-slate-200/80 bg-white space-y-1.5 shadow-2xs">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-slate-900">{act.action}</span>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            act.priority === "critical" || act.priority === "high"
                              ? "bg-rose-100 text-rose-800"
                              : "bg-blue-100 text-blue-800"
                          }`}>
                            {act.priority}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500">{act.reason}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <p className="text-[11px] text-slate-400 italic">
                {result.final_report.governance_disclaimer}
              </p>
            </div>
          )}

          {/* TAB 2: Analytics Agent */}
          {activeTab === "analytics" && result.analytics && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80">
                  <span className="text-[11px] font-medium text-slate-500 block">Total Revenue</span>
                  <span className="text-base font-bold text-slate-900">
                    {formatINR(result.analytics.total_revenue)}
                  </span>
                </div>
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80">
                  <span className="text-[11px] font-medium text-slate-500 block">Total Expenses</span>
                  <span className="text-base font-bold text-slate-900">
                    {formatINR(result.analytics.total_expenses)}
                  </span>
                </div>
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80">
                  <span className="text-[11px] font-medium text-slate-500 block">Net Profit</span>
                  <span className={`text-base font-bold ${
                    (result.analytics.total_profit ?? 0) >= 0 ? "text-emerald-600" : "text-rose-600"
                  }`}>
                    {formatINR(result.analytics.total_profit)}
                  </span>
                </div>
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80">
                  <span className="text-[11px] font-medium text-slate-500 block">Profit Margin</span>
                  <span className="text-base font-bold text-slate-900">
                    {result.analytics.profit_margin?.toFixed(2)}%
                  </span>
                </div>
              </div>

              {/* Key Findings */}
              {result.analytics.key_findings && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                    Agent Observations & Findings
                  </h4>
                  <ul className="space-y-1.5">
                    {result.analytics.key_findings.map((f, i) => (
                      <li key={i} className="text-xs text-slate-700 flex items-start gap-2 bg-slate-50/60 p-2.5 rounded-lg border border-slate-100">
                        <TrendingUp className="w-3.5 h-3.5 text-blue-600 shrink-0 mt-0.5" />
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: Risk Agent */}
          {activeTab === "risk" && result.risk && (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200/80">
                <div>
                  <span className="text-xs text-slate-500 block">Evaluated Risk Score</span>
                  <span className="text-2xl font-bold text-slate-900">
                    {result.risk.risk_score.toFixed(1)} <span className="text-xs font-normal text-slate-500">/ 100</span>
                  </span>
                </div>

                <div className="border-l border-slate-200 pl-4">
                  <span className="text-xs text-slate-500 block">Risk Tier</span>
                  <span className={`inline-block px-2.5 py-0.5 rounded text-xs font-bold uppercase ${
                    result.risk.risk_level === "critical" || result.risk.risk_level === "high"
                      ? "bg-rose-100 text-rose-800"
                      : result.risk.risk_level === "medium"
                      ? "bg-amber-100 text-amber-800"
                      : "bg-emerald-100 text-emerald-800"
                  }`}>
                    {result.risk.risk_level} Risk
                  </span>
                </div>

                <div className="border-l border-slate-200 pl-4">
                  <span className="text-xs text-slate-500 block">ML Anomalies Detected</span>
                  <span className="text-sm font-bold text-slate-800">
                    {result.risk.anomaly_detected ? `${result.risk.anomaly_count || 1} flagged` : "None"}
                  </span>
                </div>
              </div>

              {result.risk.findings && result.risk.findings.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                    Specific Identified Risks
                  </h4>
                  <div className="space-y-2">
                    {result.risk.findings.map((finding, i) => (
                      <div key={i} className="p-3.5 rounded-xl border border-slate-200/80 bg-white flex items-start gap-3">
                        <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                        <div>
                          <strong className="text-xs font-bold text-slate-900 block">{finding.risk_type}</strong>
                          <p className="text-xs text-slate-600 mt-0.5">{finding.description}</p>
                          {finding.recommended_action && (
                            <p className="text-xs text-blue-700 font-medium mt-1">
                              Action: {finding.recommended_action}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 4: Decision Optimization */}
          {activeTab === "decision" && result.decision && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-indigo-50/60 border border-indigo-200/70">
                <span className="text-xs font-bold uppercase tracking-wider text-indigo-700 block">
                  Recommended Core Strategy
                </span>
                <span className="text-base font-bold text-slate-900 mt-1 block">
                  {result.decision.recommended_strategy}
                </span>
                <p className="text-xs text-slate-600 mt-1">
                  {result.decision.summary}
                </p>
              </div>

              {/* Scenarios */}
              {result.decision.scenarios && result.decision.scenarios.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                    What-If Strategic Scenarios
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {result.decision.scenarios.map((scen, i) => (
                      <div key={i} className="p-3.5 rounded-xl border border-slate-200/80 bg-slate-50/50 space-y-1">
                        <span className="text-xs font-bold text-slate-900 block">{scen.scenario_name}</span>
                        <div className="flex justify-between text-xs text-slate-500">
                          <span>Projected Profit:</span>
                          <span className="font-bold text-slate-800">{formatINR(scen.projected_profit)}</span>
                        </div>
                        <div className="flex justify-between text-xs text-slate-500">
                          <span>Net Profit Delta:</span>
                          <span className={`font-bold ${scen.profit_delta >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                            {scen.profit_delta >= 0 ? `+${formatINR(scen.profit_delta)}` : formatINR(scen.profit_delta)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
