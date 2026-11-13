"use client";

import {
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  Menu,
  RefreshCw,
  ShieldAlert,
  Activity,
  Sparkles,
} from "lucide-react";

import { useAuth } from "@/lib/auth";
import { DashboardProvider, useDashboard } from "@/components/dashboard/DashboardContext";
import Sidebar from "@/components/dashboard/Sidebar";

interface DashboardLayoutProps {
  children: ReactNode;
}

type SessionStatus =
  | "checking"
  | "verified"
  | "unauthorized"
  | "error";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

function TopHeaderBar({ onOpenMobile }: { onOpenMobile: () => void }) {
  const pathname = usePathname();
  const { user } = useAuth();
  const { uploadResult } = useDashboard();

  const getPageTitle = (path: string) => {
    if (path === "/dashboard") return "Overview";
    if (path.startsWith("/dashboard/data")) return "Data Management";
    if (path.startsWith("/dashboard/analytics")) return "Analytics";
    if (path.startsWith("/dashboard/predictions")) return "Predictions";
    if (path.startsWith("/dashboard/risk")) return "Risk Intelligence";
    if (path.startsWith("/dashboard/decision")) return "Decision Support";
    if (path.startsWith("/dashboard/reports")) return "Reports & History";
    if (path.startsWith("/dashboard/settings")) return "Settings & System Health";
    return "Dashboard";
  };

  const title = getPageTitle(pathname);
  const hasData = uploadResult?.success === true;

  return (
    <header className="h-16 bg-white border-b border-slate-200/90 px-4 sm:px-6 lg:px-8 flex items-center justify-between sticky top-0 z-20 shadow-2xs">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onOpenMobile}
          className="lg:hidden p-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          aria-label="Open sidebar"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-400 hidden sm:inline">
              EVORA BI
            </span>
            <span className="text-xs text-slate-300 hidden sm:inline">/</span>
            <h1 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight">
              {title}
            </h1>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Active Dataset Chip */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-50 border border-slate-200/80 text-xs">
          <span
            className={`w-2 h-2 rounded-full ${
              hasData ? "bg-emerald-500 animate-pulse" : "bg-slate-300"
            }`}
          />
          <span className="font-medium text-slate-600 truncate max-w-[180px]">
            {hasData ? uploadResult.filename : "No dataset loaded"}
          </span>
          {hasData && (
            <span className="text-[10px] font-semibold text-slate-400 border-l border-slate-200 pl-2">
              {uploadResult.rows_processed.toLocaleString("en-IN")} rows
            </span>
          )}
        </div>

        {/* Live System Indicator */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200/70 text-[11px] font-semibold">
          <Activity className="w-3 h-3 text-emerald-600" />
          <span className="hidden sm:inline">Online</span>
        </div>

        {/* User Avatar */}
        <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 text-white flex items-center justify-center font-bold text-xs shadow-2xs">
          {(user?.name || user?.email || "U").charAt(0).toUpperCase()}
        </div>
      </div>
    </header>
  );
}

export default function DashboardLayout({
  children,
}: DashboardLayoutProps) {
  const router = useRouter();

  const {
    user,
    isAuthenticated,
    isLoading,
  } = useAuth();

  const [mobileOpen, setMobileOpen] =
    useState(false);

  const [sessionStatus, setSessionStatus] =
    useState<SessionStatus>("checking");

  useEffect(() => {
    if (isLoading) return;

    if (!isAuthenticated || !user?.id) {
      router.replace("/login");
      return;
    }

    let active = true;
    let controller: AbortController | null = null;

    async function verifySession() {
      controller?.abort();

      const currentController =
        new AbortController();

      controller = currentController;

      try {
        const response = await fetch(
          `${API_BASE_URL}/api/auth/me`,
          {
            method: "GET",
            credentials: "include",
            cache: "no-store",
            signal: currentController.signal,
          }
        );

        if (
          !active ||
          currentController.signal.aborted
        ) {
          return;
        }

        if (response.status === 401) {
          setSessionStatus("unauthorized");
          router.replace("/login");
          return;
        }

        if (!response.ok) {
          throw new Error(
            "Session verification failed."
          );
        }

        const data = await response.json();

        if (
          !data?.user?.id ||
          data.user.id !== user?.id
        ) {
          setSessionStatus("unauthorized");
          router.replace("/login");
          return;
        }

        setSessionStatus("verified");
      } catch (error) {
        if (
          !active ||
          currentController.signal.aborted
        ) {
          return;
        }

        console.error(
          "EVORA session verification error:",
          error
        );

        setSessionStatus("error");
      }
    }

    void verifySession();

    function handleFocus() {
      void verifySession();
    }

    function handleVisibilityChange() {
      if (document.visibilityState === "visible") {
        void verifySession();
      }
    }

    window.addEventListener(
      "focus",
      handleFocus
    );

    document.addEventListener(
      "visibilitychange",
      handleVisibilityChange
    );

    return () => {
      active = false;
      controller?.abort();

      window.removeEventListener(
        "focus",
        handleFocus
      );

      document.removeEventListener(
        "visibilitychange",
        handleVisibilityChange
      );
    };
  }, [
    isLoading,
    isAuthenticated,
    user?.id,
    router,
  ]);

  if (
    isLoading ||
    (isAuthenticated && !!user?.id && sessionStatus === "checking")
  ) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div
          role="status"
          className="flex flex-col items-center gap-3"
        >
          <div className="w-10 h-10 rounded-2xl bg-blue-600 text-white flex items-center justify-center shadow-md shadow-blue-500/30 animate-pulse">
            <Sparkles className="w-5 h-5 text-cyan-200" />
          </div>

          <p className="text-sm font-semibold text-slate-700">
            Verifying your EVORA session...
          </p>
          <p className="text-xs text-slate-400">
            Establishing secure connection
          </p>
        </div>
      </div>
    );
  }

  if (
    !isAuthenticated ||
    sessionStatus === "unauthorized"
  ) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <p className="text-sm font-medium text-slate-600">
          Redirecting to login...
        </p>
      </div>
    );
  }

  if (sessionStatus === "error") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
        <div className="max-w-sm w-full rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-sm">
          <ShieldAlert className="w-10 h-10 text-amber-600 mx-auto mb-3" />

          <h2 className="text-lg font-bold text-slate-900">
            Session Verification Failed
          </h2>

          <p className="text-sm text-slate-500 mt-2">
            EVORA could not verify your session.
            Check the backend connection and retry.
          </p>

          <button
            type="button"
            onClick={() =>
              window.location.reload()
            }
            className="mt-5 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 transition-colors shadow-xs"
          >
            Retry Verification
          </button>
        </div>
      </div>
    );
  }

  return (
    <DashboardProvider>
      <div className="min-h-screen bg-[#f8fafc] text-slate-900 flex overflow-x-hidden antialiased">
        <Sidebar
          mobileOpen={mobileOpen}
          onCloseMobile={() =>
            setMobileOpen(false)
          }
        />

        <div className="flex-1 flex flex-col min-w-0 min-h-screen">
          <TopHeaderBar onOpenMobile={() => setMobileOpen(true)} />

          <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-[1440px] w-full mx-auto">
            {children}
          </main>
        </div>
      </div>
    </DashboardProvider>
  );
}
