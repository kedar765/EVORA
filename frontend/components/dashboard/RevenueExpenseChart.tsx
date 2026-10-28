"use client";

import React, { useState, useMemo } from "react";
import {
  BarChart3,
  Calendar,
  Layers,
  Info,
} from "lucide-react";
import { FullDatasetData, formatINR } from "./types";

interface RevenueExpenseChartProps {
  fullDataset: FullDatasetData | null;
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
  isLoading = false,
}: RevenueExpenseChartProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  // Derive aggregated chart series strictly from actual records
  const { chartData, groupingMode, maxVal } = useMemo(() => {
    if (!fullDataset || !fullDataset.records || fullDataset.records.length === 0) {
      return { chartData: [], groupingMode: "None", maxVal: 0 };
    }

    const records = fullDataset.records;
    const headers = fullDataset.headers;

    // Detect column names
    const dateCol = headers.find((h) => /^date|timestamp|day|time$/i.test(h.trim()));
    const productCol = headers.find((h) => /^product|category|item|service|segment$/i.test(h.trim()));
    const revCol = headers.find((h) => /^revenue|sales|income$/i.test(h.trim())) || "Revenue";
    const expCol = headers.find((h) => /^expense|cost|expenditure$/i.test(h.trim())) || "Expense";

    // Check if date column has valid dates
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

      // Sort chronological if possible
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

    // 3. Fallback: Record by Record (first 25 records if large)
    const limit = Math.min(records.length, 25);
    for (let i = 0; i < limit; i++) {
      const row = records[i];
      const rev = Number(row[revCol]) || 0;
      const exp = Number(row[expCol]) || 0;
      const profit = rev - exp;
      const margin = rev > 0 ? (profit / rev) * 100 : 0;

      points.push({
        label: `Record ${i + 1}`,
        revenue: rev,
        expense: exp,
        profit,
        margin,
      });
    }

    const max = Math.max(...points.map((p) => Math.max(p.revenue, p.expense)), 100);
    return { chartData: points, groupingMode: "Sequential Record Comparison", maxVal: max };
  }, [fullDataset]);

  const hasChartData = chartData.length > 0;

  // Chart dimensions
  const svgWidth = 800;
  const svgHeight = 280;
  const paddingLeft = 60;
  const paddingRight = 20;
  const paddingTop = 25;
  const paddingBottom = 40;

  const chartInnerWidth = svgWidth - paddingLeft - paddingRight;
  const chartInnerHeight = svgHeight - paddingTop - paddingBottom;

  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((pct) => ({
    val: maxVal * pct,
    y: paddingTop + chartInnerHeight * (1 - pct),
  }));

  const barGroupWidth = chartInnerWidth / Math.max(chartData.length, 1);
  const barWidth = Math.min(28, Math.max(6, (barGroupWidth - 14) / 2));

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 p-5 sm:p-6 shadow-xs space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Primary Financial Visualization
            </span>
            {hasChartData && (
              <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                {groupingMode.includes("Date") ? (
                  <Calendar className="w-3 h-3 text-blue-600" />
                ) : (
                  <Layers className="w-3 h-3 text-slate-500" />
                )}
                <span>{groupingMode}</span>
              </span>
            )}
          </div>
          <h2 className="text-lg font-bold text-slate-900 tracking-tight mt-0.5">
            Revenue vs. Expense Comparison
          </h2>
        </div>

        {/* Legend */}
        {hasChartData && (
          <div className="flex items-center gap-4 text-xs font-medium self-start sm:self-auto">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-sm bg-blue-600 inline-block" />
              <span className="text-slate-700">Revenue</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-sm bg-amber-500 inline-block" />
              <span className="text-slate-700">Expense</span>
            </div>
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="h-64 flex flex-col items-center justify-center space-y-2 text-slate-400">
          <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs font-medium text-slate-500">
            Rendering visualization from ingested records...
          </span>
        </div>
      ) : !hasChartData ? (
        <div className="h-64 flex flex-col items-center justify-center text-center p-6 space-y-2 bg-slate-50/60 rounded-lg border border-dashed border-slate-200">
          <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
            <BarChart3 className="w-5 h-5" />
          </div>
          <h3 className="text-sm font-semibold text-slate-800">
            No Data Available for Visualization
          </h3>
          <p className="text-xs text-slate-400 max-w-md">
            Upload a business CSV with valid Revenue and Expense columns to generate a side-by-side comparison chart.
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
                    y={tick.y + 3}
                    textAnchor="end"
                    fontSize="10"
                    fill="#94a3b8"
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

                const revX = groupCenterX - barWidth - 1.5;
                const expX = groupCenterX + 1.5;

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
                        x={paddingLeft + idx * barGroupWidth}
                        y={paddingTop}
                        width={barGroupWidth}
                        height={chartInnerHeight}
                        fill="#f1f5f9"
                        rx="4"
                        opacity="0.7"
                      />
                    )}

                    {/* Revenue Bar */}
                    <rect
                      x={revX}
                      y={revY}
                      width={barWidth}
                      height={Math.max(revHeight, 2)}
                      fill="#2563eb"
                      rx="2"
                      className="transition-all"
                      opacity={hoveredIndex === null || isHovered ? 1 : 0.6}
                    />

                    {/* Expense Bar */}
                    <rect
                      x={expX}
                      y={expY}
                      width={barWidth}
                      height={Math.max(expHeight, 2)}
                      fill="#f59e0b"
                      rx="2"
                      className="transition-all"
                      opacity={hoveredIndex === null || isHovered ? 1 : 0.6}
                    />

                    {/* X-axis label */}
                    <text
                      x={groupCenterX}
                      y={svgHeight - 12}
                      textAnchor="middle"
                      fontSize="10"
                      fill={isHovered ? "#0f172a" : "#64748b"}
                      fontWeight={isHovered ? "bold" : "normal"}
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
            <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-900">
                  {chartData[hoveredIndex].label}
                </span>
                <span className="text-slate-400">•</span>
                <span className="text-blue-700 font-semibold">
                  Revenue: {formatINR(chartData[hoveredIndex].revenue)}
                </span>
                <span className="text-slate-400">•</span>
                <span className="text-amber-700 font-semibold">
                  Expense: {formatINR(chartData[hoveredIndex].expense)}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-slate-500 font-medium">Net Profit:</span>
                <span
                  className={`font-bold ${
                    chartData[hoveredIndex].profit >= 0
                      ? "text-emerald-700"
                      : "text-rose-700"
                  }`}
                >
                  {formatINR(chartData[hoveredIndex].profit)} (
                  {chartData[hoveredIndex].margin.toFixed(1)}%)
                </span>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
              <span className="flex items-center gap-1">
                <Info className="w-3 h-3 text-slate-400" />
                <span>Hover over any bar to view exact revenue, expenditure, and margin metrics.</span>
              </span>
              <span>Total Periods/Categories: {chartData.length}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
