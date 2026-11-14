"use client";

import React, { useState, useMemo } from "react";
import {
  BarChart3,
  Calendar,
  Layers,
  Info,
  TrendingUp,
  ArrowUpRight,
} from "lucide-react";
import { FullDatasetData, UploadResult, formatINR } from "./types";

interface RevenueExpenseChartProps {
  fullDataset: FullDatasetData | null;
  uploadResult?: UploadResult | null;
  isLoading?: boolean;
}

interface ChartDataPoint {
  label: string;
  revenue: number;
  expense: number;
  profit: number;
  margin: number;
}

export default function RevenueExpenseChart({
  fullDataset,
  uploadResult,
  isLoading = false,
}: RevenueExpenseChartProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  // Derive aggregated chart series strictly from actual records or backend analytics
  const { chartData, groupingMode, maxVal } = useMemo(() => {
    if (!fullDataset || !fullDataset.records || fullDataset.records.length === 0) {
      // Fallback 1: Backend monthly trends if available
      const trends = uploadResult?.analytics?.monthly_trends;
      if (trends && trends.length > 0) {
        const points: ChartDataPoint[] = trends.map((t) => {
          const rev = Number(t.revenue) || 0;
          const exp = Number(t.expense) || 0;
          const prof = Number(t.profit) ?? (rev - exp);
          const margin = rev > 0 ? (prof / rev) * 100 : 0;
          return { label: t.month, revenue: rev, expense: exp, profit: prof, margin };
        });
        const max = Math.max(...points.map((p) => Math.max(p.revenue, p.expense)), 100);
        return { chartData: points, groupingMode: "Monthly Trend Analysis", maxVal: max };
      }

      // Fallback 2: Backend product performance if available
      const products = uploadResult?.analytics?.product_performance;
      if (products && products.length > 0) {
        const points: ChartDataPoint[] = products.map((p) => {
          const rev = Number(p.revenue) || 0;
          const exp = Number(p.expense) || 0;
          const prof = Number(p.profit) ?? (rev - exp);
          const margin = rev > 0 ? (prof / rev) * 100 : 0;
          return { label: p.product, revenue: rev, expense: exp, profit: prof, margin };
        });
        const max = Math.max(...points.map((p) => Math.max(p.revenue, p.expense)), 100);
        return { chartData: points, groupingMode: "Product Performance Breakdown", maxVal: max };
      }

      // Fallback 3: Single overall aggregate if metrics exist
      if (uploadResult?.metrics) {
        const rev = uploadResult.metrics.total_revenue || 0;
        const exp = uploadResult.metrics.total_expense || 0;
        const prof = uploadResult.metrics.total_profit || 0;
        const margin = uploadResult.metrics.profit_margin || 0;
        const points: ChartDataPoint[] = [
          { label: "Active Dataset Total", revenue: rev, expense: exp, profit: prof, margin }
        ];
        const max = Math.max(rev, exp, 100);
        return { chartData: points, groupingMode: "Aggregate Financial Overview", maxVal: max };
      }

      return { chartData: [], groupingMode: "None", maxVal: 0 };
    }

    const records = fullDataset.records;
    const headers = fullDataset.headers;

    // Detect column names with prioritized canonical matches (never confuse Unit_Cost with Expense)
    const dateCol = headers.find((h) => /^(date|timestamp|day|time)$/i.test(h.trim()));
    const productCol = headers.find((h) => /^(product|category|item|service|segment)$/i.test(h.trim()));
    const revCol =
      headers.find((h) => /^(total[_\s]?)?revenue$/i.test(h.trim())) ||
      headers.find((h) => /^(total[_\s]?)?sales$/i.test(h.trim())) ||
      headers.find((h) => /^(amount|income|turnover)$/i.test(h.trim())) ||
      "Revenue";
    const expCol =
      headers.find((h) => /^(total[_\s]?)?expense(s)?$/i.test(h.trim())) ||
      headers.find((h) => /^(total[_\s]?)?cost(s)?$/i.test(h.trim()) && !/unit|per|rate/i.test(h.trim())) ||
      headers.find((h) => /^(expenditure|cogs)$/i.test(h.trim())) ||
      "Expense";

    const hasValidDates =
      dateCol &&
      records.some((r) => {
        const val = String(r[dateCol] || "");
        return val && !isNaN(Date.parse(val));
      });

    const points: ChartDataPoint[] = [];

    if (hasValidDates && dateCol) {
      // 1. Time-series aggregation by Date
      const dateMap = new Map<string, { revenue: number; expense: number }>();

      const sorted = [...records].sort((a, b) => {
        const da = new Date(String(a[dateCol])).getTime();
        const db = new Date(String(b[dateCol])).getTime();
        return da - db;
      });

      for (const row of sorted) {
        const rawDate = String(row[dateCol] || "Unknown");
        const rev = Number(row[revCol]) || 0;
        const exp = Number(row[expCol]) || 0;

        const current = dateMap.get(rawDate) || { revenue: 0, expense: 0 };
        current.revenue += rev;
        current.expense += exp;
        dateMap.set(rawDate, current);
      }

      dateMap.forEach((vals, d) => {
        const profit = vals.revenue - vals.expense;
        const margin = vals.revenue > 0 ? (profit / vals.revenue) * 100 : 0;
        points.push({
          label: d,
          revenue: vals.revenue,
          expense: vals.expense,
          profit,
          margin,
        });
      });

      const max = Math.max(...points.map((p) => Math.max(p.revenue, p.expense)), 100);
      return { chartData: points, groupingMode: "Chronological Date Trend", maxVal: max };
    }

    if (productCol) {
      // 2. Category / Product aggregation
      const catMap = new Map<string, { revenue: number; expense: number }>();

      for (const row of records) {
        const cat = String(row[productCol] || "Uncategorized");
        const rev = Number(row[revCol]) || 0;
        const exp = Number(row[expCol]) || 0;

        const current = catMap.get(cat) || { revenue: 0, expense: 0 };
        current.revenue += rev;
        current.expense += exp;
        catMap.set(cat, current);
      }

      catMap.forEach((vals, c) => {
        const profit = vals.revenue - vals.expense;
        const margin = vals.revenue > 0 ? (profit / vals.revenue) * 100 : 0;
        points.push({
          label: c,
          revenue: vals.revenue,
          expense: vals.expense,
          profit,
          margin,
        });
      });

      const max = Math.max(...points.map((p) => Math.max(p.revenue, p.expense)), 100);
      return { chartData: points, groupingMode: `Category Breakdown (${productCol})`, maxVal: max };
    }

    // 3. Fallback: Sequential records (first 25)
    const limit = Math.min(records.length, 25);
    for (let i = 0; i < limit; i++) {
      const row = records[i];
      const rev = Number(row[revCol]) || 0;
      const exp = Number(row[expCol]) || 0;
      const profit = rev - exp;
      const margin = rev > 0 ? (profit / rev) * 100 : 0;

      points.push({
        label: `Row ${i + 1}`,
        revenue: rev,
        expense: exp,
        profit,
        margin,
      });
    }

    const max = Math.max(...points.map((p) => Math.max(p.revenue, p.expense)), 100);
    return { chartData: points, groupingMode: "Sequential Record Comparison", maxVal: max };
  }, [fullDataset, uploadResult]);

  const hasChartData = chartData.length > 0;

  // Chart dimensions
  const svgWidth = 840;
  const svgHeight = 290;
  const paddingLeft = 65;
  const paddingRight = 25;
  const paddingTop = 30;
  const paddingBottom = 42;

  const chartInnerWidth = svgWidth - paddingLeft - paddingRight;
  const chartInnerHeight = svgHeight - paddingTop - paddingBottom;

  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((pct) => ({
    val: maxVal * pct,
    y: paddingTop + chartInnerHeight * (1 - pct),
  }));

  const barGroupWidth = chartInnerWidth / Math.max(chartData.length, 1);
  const barWidth = Math.min(26, Math.max(8, (barGroupWidth - 16) / 2));

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 p-5 sm:p-6 shadow-xs space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-4 rounded-full bg-blue-600" />
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Comparative Analysis
            </span>
            {hasChartData && (
              <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
                {groupingMode.includes("Date") ? (
                  <Calendar className="w-3 h-3 text-blue-600" />
                ) : (
                  <Layers className="w-3 h-3 text-slate-500" />
                )}
                <span>{groupingMode}</span>
              </span>
            )}
          </div>
          <h2 className="text-lg font-bold text-slate-900 tracking-tight mt-1">
            Revenue vs. Expense Comparison
          </h2>
        </div>

        {/* Legend */}
        {hasChartData && (
          <div className="flex items-center gap-4 text-xs font-semibold self-start sm:self-auto bg-slate-50 px-3 py-1.5 rounded-xl border border-slate-200/70">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-blue-600 inline-block shadow-2xs" />
              <span className="text-slate-800">Revenue</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-amber-500 inline-block shadow-2xs" />
              <span className="text-slate-800">Expense</span>
            </div>
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="h-64 flex flex-col items-center justify-center space-y-2 text-slate-400">
          <div className="w-7 h-7 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs font-medium text-slate-500">
            Synthesizing comparative telemetry...
          </span>
        </div>
      ) : !hasChartData ? (
        <div className="h-64 flex flex-col items-center justify-center text-center p-6 space-y-2.5 bg-slate-50/60 rounded-xl border border-dashed border-slate-200">
          <div className="w-11 h-11 rounded-2xl bg-white border border-slate-200 flex items-center justify-center text-slate-400 shadow-2xs">
            <BarChart3 className="w-5 h-5 text-blue-600" />
          </div>
          <h3 className="text-sm font-bold text-slate-800">
            Awaiting Dataset for Comparative Visualization
          </h3>
          <p className="text-xs text-slate-500 max-w-sm">
            Ingest a business CSV or Excel file containing Revenue and Expense columns to generate side-by-side performance bars.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Responsive SVG Chart */}
          <div className="relative w-full overflow-x-auto custom-scrollbar">
            <svg
              viewBox={`0 0 ${svgWidth} ${svgHeight}`}
              className="w-full h-auto min-w-[580px] select-none"
              aria-label="Revenue versus expense comparison chart"
            >
              <defs>
                <linearGradient id="blueRevGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#2563eb" />
                  <stop offset="100%" stopColor="#1d4ed8" />
                </linearGradient>
                <linearGradient id="amberExpGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#f59e0b" />
                  <stop offset="100%" stopColor="#d97706" />
                </linearGradient>
              </defs>

              {/* Horizontal grid lines & Y-axis labels */}
              {yTicks.map((tick, idx) => (
                <g key={idx}>
                  <line
                    x1={paddingLeft}
                    y1={tick.y}
                    x2={svgWidth - paddingRight}
                    y2={tick.y}
                    stroke="#e2e8f0"
                    strokeDasharray={idx === 0 ? "none" : "3 3"}
                    strokeWidth="1"
                  />
                  <text
                    x={paddingLeft - 8}
                    y={tick.y + 3.5}
                    textAnchor="end"
                    fontSize="10"
                    fill="#94a3b8"
                    fontWeight="500"
                    fontFamily="inherit"
                  >
                    {tick.val >= 100000
                      ? `₹${(tick.val / 100000).toFixed(1)}L`
                      : tick.val >= 1000
                      ? `₹${(tick.val / 1000).toFixed(0)}k`
                      : `₹${tick.val.toFixed(0)}`}
                  </text>
                </g>
              ))}

              {/* Data Bars */}
              {chartData.map((d, idx) => {
                const groupCenterX =
                  paddingLeft + idx * barGroupWidth + barGroupWidth / 2;
                const revHeight = (d.revenue / maxVal) * chartInnerHeight;
                const expHeight = (d.expense / maxVal) * chartInnerHeight;

                const revX = groupCenterX - barWidth - 2;
                const expX = groupCenterX + 2;

                const revY = paddingTop + chartInnerHeight - revHeight;
                const expY = paddingTop + chartInnerHeight - expHeight;

                const isHovered = hoveredIndex === idx;

                return (
                  <g
                    key={idx}
                    onMouseEnter={() => setHoveredIndex(idx)}
                    onMouseLeave={() => setHoveredIndex(null)}
                    className="cursor-pointer transition-opacity"
                  >
                    {/* Hover highlight background */}
                    {isHovered && (
                      <rect
                        x={paddingLeft + idx * barGroupWidth + 2}
                        y={paddingTop}
                        width={barGroupWidth - 4}
                        height={chartInnerHeight}
                        fill="#f8fafc"
                        stroke="#cbd5e1"
                        strokeWidth="1"
                        rx="8"
                        opacity="0.9"
                      />
                    )}

                    {/* Revenue Bar */}
                    <rect
                      x={revX}
                      y={revY}
                      width={barWidth}
                      height={Math.max(revHeight, 3)}
                      fill="url(#blueRevGradient)"
                      rx="3"
                      className="transition-all duration-150"
                      opacity={hoveredIndex === null || isHovered ? 1 : 0.6}
                    />

                    {/* Expense Bar */}
                    <rect
                      x={expX}
                      y={expY}
                      width={barWidth}
                      height={Math.max(expHeight, 3)}
                      fill="url(#amberExpGradient)"
                      rx="3"
                      className="transition-all duration-150"
                      opacity={hoveredIndex === null || isHovered ? 1 : 0.6}
                    />

                    {/* X-axis label */}
                    <text
                      x={groupCenterX}
                      y={svgHeight - 12}
                      textAnchor="middle"
                      fontSize="10"
                      fill={isHovered ? "#0f172a" : "#64748b"}
                      fontWeight={isHovered ? "700" : "500"}
                      fontFamily="inherit"
                    >
                      {d.label.length > 10 ? `${d.label.slice(0, 9)}…` : d.label}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          {/* Active Hover / Detail Card */}
          {hoveredIndex !== null && chartData[hoveredIndex] ? (
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/90 flex flex-wrap items-center justify-between gap-3 text-xs shadow-2xs">
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-900 bg-white px-2.5 py-1 rounded-lg border border-slate-200">
                  {chartData[hoveredIndex].label}
                </span>
                <span className="text-blue-700 font-semibold">
                  Revenue: {formatINR(chartData[hoveredIndex].revenue)}
                </span>
                <span className="text-slate-300">•</span>
                <span className="text-amber-700 font-semibold">
                  Expense: {formatINR(chartData[hoveredIndex].expense)}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-slate-500 font-medium">Net Profit:</span>
                <span
                  className={`font-bold px-2 py-0.5 rounded-md ${
                    chartData[hoveredIndex].profit >= 0
                      ? "text-emerald-700 bg-emerald-50 border border-emerald-200/60"
                      : "text-rose-700 bg-rose-50 border border-rose-200/60"
                  }`}
                >
                  {formatINR(chartData[hoveredIndex].profit)} ({chartData[hoveredIndex].margin.toFixed(1)}%)
                </span>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
              <span className="flex items-center gap-1.5">
                <Info className="w-3.5 h-3.5 text-slate-400" />
                <span>Hover over any group to inspect itemized revenue, expenditure, and margin.</span>
              </span>
              <span className="font-medium text-slate-500">
                Series Count: {chartData.length}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
