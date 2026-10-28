
"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  LayoutDashboard,
  BarChart3,
  BrainCircuit,
  FileText,
  Settings,
  LogOut,
  X,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";

import { useAuth } from "@/lib/auth";
import { useDashboard } from "./DashboardContext";

interface SidebarProps {
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}

const navItems = [
  {
    name: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    name: "Analytics",
    href: "/dashboard/analytics",
    icon: BarChart3,
  },
  {
    name: "Predictions",
    href: "/dashboard/predictions",
    icon: BrainCircuit,
  },
  {
    name: "Reports",
    href: "/dashboard/reports",
    icon: FileText,
  },
  {
    name: "Settings",
    href: "/dashboard/settings",
    icon: Settings,
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
    "User";

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

    // AuthProvider handles backend session revocation.
    logout();
  };

  const sidebarContent = (
    <div className="flex flex-col h-full bg-white border-r border-slate-200">

      {/* Brand Header */}
      <div className="h-16 px-5 flex items-center justify-between border-b border-slate-100">
        <Link
          href="/dashboard"
          onClick={onCloseMobile}
          className="flex items-center gap-2.5"
        >
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white">
            <LayoutDashboard className="w-4 h-4" />
          </div>

          <div>
            <span className="text-base font-bold tracking-tight text-slate-900 block">
              EVORA
            </span>

            <span className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">
              Business Intelligence
            </span>
          </div>
        </Link>

        {onCloseMobile && (
          <button
            type="button"
            onClick={onCloseMobile}
            className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100"
            aria-label="Close sidebar"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Dataset Status */}
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/70">
        <div className="flex items-center justify-between gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
            Active Dataset
          </span>

          {hasDataset ? (
            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700">
              <CheckCircle2 className="w-3 h-3" />
              Loaded
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-500">
              <AlertCircle className="w-3 h-3" />
              No Data
            </span>
          )}
        </div>

        <p
          className="text-xs font-semibold text-slate-800 mt-1 truncate"
          title={
            hasDataset
              ? uploadResult.filename
              : "No dataset active"
          }
        >
          {hasDataset
            ? uploadResult.filename
            : "No dataset active"}
        </p>

        {hasDataset && (
          <p className="text-[10px] text-slate-500 mt-0.5">
            {uploadResult.rows_processed.toLocaleString(
              "en-IN"
            )}{" "}
            records processed
          </p>
        )}
      </div>

      {/* Navigation */}
      <nav
        aria-label="Dashboard navigation"
        className="flex-1 px-3 py-3 space-y-1 overflow-y-auto"
      >
        {navItems.map((item) => {
          const active = isItemActive(item.href);
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onCloseMobile}
              aria-current={
                active ? "page" : undefined
              }
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                active
                  ? "bg-blue-50 text-blue-700 font-semibold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50 font-medium"
              }`}
            >
              <Icon
                className={`w-4 h-4 shrink-0 ${
                  active
                    ? "text-blue-600"
                    : "text-slate-400"
                }`}
              />

              <span className="truncate">
                {item.name}
              </span>
            </Link>
          );
        })}
      </nav>

      {/* User Profile */}
      <div className="p-3 border-t border-slate-100">
        <div className="flex items-center justify-between gap-2 p-2 rounded-lg bg-slate-50 border border-slate-200/70">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-xs shrink-0">
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

          {/* Logout */}
          <button
            type="button"
            onClick={handleLogout}
            disabled={
              !isAuthenticated || isLoading
            }
            className="p-2 rounded-md text-slate-500 hover:text-rose-600 hover:bg-rose-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
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
      <aside className="hidden lg:block w-60 shrink-0 h-screen sticky top-0 z-30">
        {sidebarContent}
      </aside>

      {/* Mobile Backdrop */}
      {mobileOpen && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-slate-900/40 backdrop-blur-xs lg:hidden cursor-default"
          onClick={onCloseMobile}
          aria-label="Close mobile navigation"
        />
      )}

      {/* Mobile Sidebar */}
      <div
        aria-label="Mobile navigation"
        className={`fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-200 ease-in-out lg:hidden shadow-xl ${
          mobileOpen
            ? "translate-x-0"
            : "-translate-x-full"
        }`}
      >
        {sidebarContent}
      </div>
    </>
  );
}
