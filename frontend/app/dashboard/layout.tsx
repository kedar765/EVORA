
"use client";

import {
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { useRouter } from "next/navigation";
import {
  Menu,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";

import { useAuth } from "@/lib/auth";
import { DashboardProvider } from "@/components/dashboard/DashboardContext";
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
      setSessionStatus("unauthorized");
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

    // Initial authentication verification.
    void verifySession();

    // Recheck the session without resetting
    // or unmounting the active dashboard.
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
    sessionStatus === "checking"
  ) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div
          role="status"
          className="flex flex-col items-center gap-3"
        >
          <RefreshCw className="w-7 h-7 text-blue-600 animate-spin" />

          <p className="text-sm font-medium text-slate-600">
            Verifying your EVORA session...
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
        <p className="text-sm text-slate-600">
          Redirecting to login...
        </p>
      </div>
    );
  }

  if (sessionStatus === "error") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
        <div className="max-w-sm w-full rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-sm">
          <ShieldAlert className="w-9 h-9 text-amber-600 mx-auto mb-3" />

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
            className="mt-5 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
          >
            Retry Verification
          </button>
        </div>
      </div>
    );
  }

  return (
    <DashboardProvider>
      <div className="min-h-screen bg-slate-50/70 text-slate-900 flex overflow-x-hidden antialiased">
        <Sidebar
          mobileOpen={mobileOpen}
          onCloseMobile={() =>
            setMobileOpen(false)
          }
        />

        <div className="flex-1 flex flex-col min-w-0 min-h-screen">
          <header className="lg:hidden h-16 bg-white border-b border-slate-200 px-4 flex items-center justify-between sticky top-0 z-20 shadow-sm">
            <button
              type="button"
              onClick={() =>
                setMobileOpen(true)
              }
              className="p-2 rounded-xl text-slate-600 hover:bg-slate-100"
              aria-label="Open sidebar"
            >
              <Menu className="w-5 h-5" />
            </button>

            <span className="text-sm font-bold text-slate-900">
              EVORA BI
            </span>

            <div className="w-8" />
          </header>

          <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-[1440px] w-full mx-auto">
            {children}
          </main>
        </div>
      </div>
    </DashboardProvider>
  );
}
