"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  LayoutDashboard,
  BarChart3,
  BrainCircuit,
  ShieldAlert,
  Target,
  FileText,
  Settings,
  LogOut,
  X,
  CheckCircle2,
  AlertCircle,
  Database,
  Sparkles,
  ChevronRight,
} from "lucide-react";

import { useAuth } from "@/lib/auth";
import { useDashboard } from "./DashboardContext";

interface SidebarProps {
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}

const navItems = [
  {
    name: "Overview",
    href: "/dashboard",
    icon: LayoutDashboard,
    badge: null,
  },
  {
    name: "Data Management",
    href: "/dashboard/data",
    icon: Database,
    badge: null,
  },
  {
    name: "Analytics",
    href: "/dashboard/analytics",
    icon: BarChart3,
    badge: null,
  },
  {
    name: "Predictions",
    href: "/dashboard/predictions",
    icon: BrainCircuit,
    badge: "ML",
  },
  {
    name: "Risk Intelligence",
    href: "/dashboard/risk",
    icon: ShieldAlert,
    badge: null,
  },
  {
    name: "Decision Support",
    href: "/dashboard/decision",
    icon: Target,
    badge: "AI",
  },
  {
    name: "Reports",
    href: "/dashboard/reports",
    icon: FileText,
    badge: null,
  },
  {
    name: "Settings",
    href: "/dashboard/settings",
    icon: Settings,
    badge: null,
  },
];

export default function Sidebar({
  mobileOpen = false,
  onCloseMobile,
}: SidebarProps) {
  const pathname = usePathname();

  const {
    user,
    isAuthenticated,
    isLoading,
    logout,
  } = useAuth();

  const { uploadResult } = useDashboard();

  const displayName =
    user?.name?.trim() ||
    user?.email?.split("@")[0] ||
    "Enterprise User";

  const displayEmail = user?.email || "";

  const userInitial =
    displayName.charAt(0).toUpperCase();

  const hasDataset =
    uploadResult?.success === true;

  const isItemActive = (href: string) => {
    if (href === "/dashboard") {
      return pathname === href;
    }

    return (
      pathname === href ||
      pathname.startsWith(`${href}/`)
    );
  };

  const handleLogout = () => {
    if (!isAuthenticated || isLoading) {
      return;
    }

    onCloseMobile?.();
    logout();
  };

  const sidebarContent = (
    <div className="flex flex-col h-full bg-white border-r border-slate-200/90 shadow-xs select-none">
      {/* Brand Header */}
      <div className="h-16 px-5 flex items-center justify-between border-b border-slate-100 bg-white">
        <Link
          href="/dashboard"
          onClick={onCloseMobile}
          className="flex items-center gap-2.5 group"
        >
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-600 via-indigo-600 to-blue-800 flex items-center justify-center text-white shadow-sm shadow-blue-500/20 group-hover:scale-105 transition-transform">
            <Sparkles className="w-5 h-5 text-cyan-200" />
          </div>

          <div className="flex flex-col">
            <div className="flex items-center gap-1.5">
              <span className="text-base font-extrabold tracking-tight text-slate-900 group-hover:text-blue-600 transition-colors">
                EVORA
              </span>
              <span className="text-[9px] font-bold px-1.5 py-0.2 rounded-full bg-blue-50 text-blue-700 border border-blue-200/60 uppercase">
                BI
              </span>
            </div>

            <span className="text-[10px] font-semibold text-slate-400 tracking-wider uppercase">
              Decision Optimization
            </span>
          </div>
        </Link>

        {onCloseMobile && (
          <button
            type="button"
            onClick={onCloseMobile}
            className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
            aria-label="Close sidebar"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Active Dataset Telemetry Card */}
      <div className="p-3.5 border-b border-slate-100 bg-slate-50/60">
        <div className="p-3 rounded-xl bg-white border border-slate-200/80 shadow-2xs">
          <div className="flex items-center justify-between gap-2 mb-1.5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Active Dataset
            </span>

            {hasDataset ? (
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                Live
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-400">
                <AlertCircle className="w-3 h-3 text-slate-400" />
                No Data
              </span>
            )}
          </div>

          <p
            className="text-xs font-semibold text-slate-900 truncate"
            title={hasDataset ? uploadResult.filename : "No dataset loaded"}
          >
            {hasDataset ? uploadResult.filename : "Awaiting CSV / Excel"}
          </p>

          <div className="flex items-center justify-between text-[11px] text-slate-500 mt-1 pt-1.5 border-t border-slate-100">
            <span>
              {hasDataset
                ? `${uploadResult.rows_processed.toLocaleString("en-IN")} rows`
                : "No rows ingested"}
            </span>

            <Link
              href="/dashboard/data"
              onClick={onCloseMobile}
              className="text-blue-600 hover:text-blue-700 font-semibold inline-flex items-center gap-0.5 text-[10px]"
            >
              Manage
              <ChevronRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav
        aria-label="Dashboard navigation"
        className="flex-1 px-3 py-3 space-y-1 overflow-y-auto custom-scrollbar"
      >
        <div className="px-2 pb-1.5">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Navigation
          </span>
        </div>

        {navItems.map((item) => {
          const active = isItemActive(item.href);
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onCloseMobile}
              aria-current={active ? "page" : undefined}
              className={`flex items-center justify-between px-3 py-2.5 rounded-xl text-sm transition-all duration-150 group ${
                active
                  ? "bg-blue-600 text-white font-semibold shadow-xs shadow-blue-500/25"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50 font-medium"
              }`}
            >
              <div className="flex items-center gap-3 min-w-0">
                <Icon
                  className={`w-4 h-4 shrink-0 transition-colors ${
                    active
                      ? "text-white"
                      : "text-slate-400 group-hover:text-blue-600"
                  }`}
                />
                <span className="truncate">{item.name}</span>
              </div>

              {item.badge && (
                <span
                  className={`text-[9px] font-bold px-1.5 py-0.5 rounded-md uppercase tracking-wider ${
                    active
                      ? "bg-white/20 text-white"
                      : "bg-blue-50 text-blue-700 border border-blue-200/60"
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* User Profile & Sign Out */}
      <div className="p-3 border-t border-slate-100 bg-white">
        <div className="flex items-center justify-between gap-2 p-2 rounded-xl bg-slate-50/80 border border-slate-200/80">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-2xs">
              {userInitial}
            </div>

            <div className="min-w-0">
              <p className="text-xs font-semibold text-slate-900 truncate">
                {displayName}
              </p>

              {displayEmail && (
                <p className="text-[10px] text-slate-500 truncate">
                  {displayEmail}
                </p>
              )}
            </div>
          </div>

          <button
            type="button"
            onClick={handleLogout}
            disabled={!isAuthenticated || isLoading}
            className="p-2 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
            title="Sign out of EVORA"
            aria-label="Sign out of EVORA"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Sidebar */}
      <aside className="hidden lg:block w-64 shrink-0 h-screen sticky top-0 z-30">
        {sidebarContent}
      </aside>

      {/* Mobile Backdrop */}
      {mobileOpen && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-slate-900/40 backdrop-blur-xs lg:hidden cursor-default transition-opacity"
          onClick={onCloseMobile}
          aria-label="Close mobile navigation"
        />
      )}

      {/* Mobile Sidebar */}
      <div
        aria-label="Mobile navigation"
        className={`fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-200 ease-in-out lg:hidden shadow-2xl ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {sidebarContent}
      </div>
    </>
  );
}
