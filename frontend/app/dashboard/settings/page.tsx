"use client";

import React, { useState, useEffect } from "react";
import {
  User as UserIcon,
  Server,
  Database,
  Shield,
  Trash2,
  CheckCircle2,
  RefreshCw,
  LogOut,
  Info,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useDashboard } from "@/components/dashboard/DashboardContext";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const { uploadResult, clearDataset } = useDashboard();
  const [backendHealth, setBackendHealth] = useState<{ status: string; service?: string } | null>(null);
  const [isCheckingHealth, setIsCheckingHealth] = useState<boolean>(false);
  const [healthError, setHealthError] = useState<string>("");

  const checkHealth = async () => {
    setIsCheckingHealth(true);
    setHealthError("");
    try {
      const res = await fetch(`${API_BASE}/health`, { method: "GET" });
      if (!res.ok) throw new Error(`Health check returned status ${res.status}`);
      const data = await res.json();
      setBackendHealth(data);
    } catch (err: unknown) {
      setHealthError(err instanceof Error ? err.message : "Unable to contact backend service.");
      setBackendHealth(null);
    } finally {
      setIsCheckingHealth(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    const loadInitialHealth = async () => {
      try {
        const res = await fetch(`${API_BASE}/health`, { method: "GET" });
        if (!res.ok) throw new Error(`Status ${res.status}`);
        const data = await res.json();
        if (isMounted) setBackendHealth(data);
      } catch (err: unknown) {
        if (isMounted) {
          setHealthError(err instanceof Error ? err.message : "Unable to contact backend service.");
        }
      }
    };
    loadInitialHealth();
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
          Settings
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Review system configuration, connection diagnostics, and user account parameters.
        </p>
      </div>

      {/* Account Profile Card */}
      <section className="bg-white rounded-xl border border-slate-200/90 shadow-xs p-6 space-y-4">
        <div className="flex items-center gap-2.5 pb-3 border-b border-slate-100">
          <UserIcon className="w-4 h-4 text-slate-500" />
          <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider">
            User Account
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-xs text-slate-400 block">Full Name</span>
            <span className="font-medium text-slate-900 mt-0.5 block">
              {user?.name || "Executive User"}
            </span>
          </div>

          <div>
            <span className="text-xs text-slate-400 block">Email Address</span>
            <span className="font-medium text-slate-900 mt-0.5 block">
              {user?.email || "executive@evora.ai"}
            </span>
          </div>

          <div>
            <span className="text-xs text-slate-400 block">Authentication Mode</span>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700 mt-0.5">
              <Shield className="w-3 h-3 text-slate-500" />
              <span className="capitalize">{user?.provider || "Session"}</span>
            </span>
          </div>
        </div>

        <div className="pt-2">
          <button
            type="button"
            onClick={logout}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200/80 transition-colors cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out</span>
          </button>
        </div>
      </section>

      {/* Backend API Connectivity */}
      <section className="bg-white rounded-xl border border-slate-200/90 shadow-xs p-6 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2.5">
            <Server className="w-4 h-4 text-slate-500" />
            <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider">
              Backend Service Diagnostic
            </h2>
          </div>

          <button
            type="button"
            onClick={checkHealth}
            disabled={isCheckingHealth}
            className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-medium cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`w-3 h-3 ${isCheckingHealth ? "animate-spin" : ""}`} />
            <span>Test Connection</span>
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-xs text-slate-400 block">Service Endpoint</span>
            <span className="font-mono text-xs text-slate-800 mt-0.5 block truncate" title={API_BASE}>
              {API_BASE}
            </span>
          </div>

          <div>
            <span className="text-xs text-slate-400 block">Health Status</span>
            {backendHealth?.status === "healthy" ? (
              <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 mt-0.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                <span>Online & Healthy</span>
              </span>
            ) : healthError ? (
              <span className="text-xs font-semibold text-rose-600 mt-0.5 block truncate">
                {healthError}
              </span>
            ) : (
              <span className="text-xs text-slate-400 mt-0.5 block">Checking...</span>
            )}
          </div>

          <div>
            <span className="text-xs text-slate-400 block">Service Name</span>
            <span className="font-medium text-slate-800 mt-0.5 block">
              {backendHealth?.service || "EVORA Backend API"}
            </span>
          </div>
        </div>
      </section>

      {/* Dataset Session Cache */}
      <section className="bg-white rounded-xl border border-slate-200/90 shadow-xs p-6 space-y-4">
        <div className="flex items-center gap-2.5 pb-3 border-b border-slate-100">
          <Database className="w-4 h-4 text-slate-500" />
          <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider">
            Active Dataset Session
          </h2>
        </div>

        <div className="text-sm">
          {uploadResult ? (
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-3.5 rounded-lg bg-slate-50 border border-slate-200/70">
              <div>
                <span className="font-semibold text-slate-900 block">
                  {uploadResult.filename}
                </span>
                <span className="text-xs text-slate-500 mt-0.5 block">
                  {uploadResult.rows_processed.toLocaleString()} records active in current session storage
                </span>
              </div>

              <button
                type="button"
                onClick={clearDataset}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-rose-700 bg-white hover:bg-rose-50 border border-rose-200 shadow-xs transition-colors cursor-pointer self-start sm:self-auto shrink-0"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear Dataset</span>
              </button>
            </div>
          ) : (
            <p className="text-xs text-slate-500">
              No dataset is currently stored in active session. Upload a CSV from the Dashboard to load data.
            </p>
          )}
        </div>
      </section>

      {/* System Information */}
      <section className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 text-xs text-slate-500 flex items-start gap-2.5">
        <Info className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          EVORA (Enterprise Vision Optimizing Reasoning Assistant) v1.0.0. All analytics and predictions operate under human decision-support mode. No autonomous actions are executed without explicit user verification.
        </p>
      </section>
    </div>
  );
}
