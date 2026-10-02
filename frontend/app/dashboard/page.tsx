"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

type WhatIfResult = {
  success: boolean;
  current_predicted_profit: number;
  new_predicted_profit: number;
  profit_difference: number;
  result: string;
};

export default function DashboardPage() {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const router = useRouter();

  const [currentQuantity, setCurrentQuantity] = useState("");
  const [currentRevenue, setCurrentRevenue] = useState("");
  const [currentExpense, setCurrentExpense] = useState("");

  const [newQuantity, setNewQuantity] = useState("");
  const [newRevenue, setNewRevenue] = useState("");
  const [newExpense, setNewExpense] = useState("");

  const [result, setResult] = useState<WhatIfResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading || !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <p className="text-sm font-semibold text-slate-500">
          Verifying session...
        </p>
      </div>
    );
  }

  const displayName =
    user?.name || user?.email?.split("@")[0] || "User";

  const handleWhatIf = async () => {
    setError("");
    setResult(null);

    if (
      !currentQuantity ||
      !currentRevenue ||
      !currentExpense ||
      !newQuantity ||
      !newRevenue ||
      !newExpense
    ) {
      setError("Please enter all business values.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/what-if", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          current_quantity: Number(currentQuantity),
          current_revenue: Number(currentRevenue),
          current_expense: Number(currentExpense),
          new_quantity: Number(newQuantity),
          new_revenue: Number(newRevenue),
          new_expense: Number(newExpense),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Something went wrong.");
      }

      setResult(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to connect to EVORA backend."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setCurrentQuantity("");
    setCurrentRevenue("");
    setCurrentExpense("");
    setNewQuantity("");
    setNewRevenue("");
    setNewExpense("");
    setResult(null);
    setError("");
  };

  const isIncrease = result && result.profit_difference > 0;
  const isDecrease = result && result.profit_difference < 0;

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto">

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <p className="text-sm font-bold text-blue-700">
              EVORA Dashboard
            </p>

            <h1 className="text-3xl sm:text-4xl font-black text-slate-900 tracking-tight">
              Welcome, {displayName}
            </h1>

            <p className="text-sm text-slate-500 mt-1">
              Explore business scenarios and understand possible outcomes.
            </p>
          </div>

          <button
            onClick={logout}
            className="self-start sm:self-auto px-5 py-2.5 rounded-xl text-sm font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            Sign Out
          </button>
        </div>

        <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 sm:p-8">

          <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3 mb-8">
            <div>
              <p className="text-sm font-bold text-blue-700">
                Decision Support
              </p>

              <h2 className="text-2xl sm:text-3xl font-black text-slate-900 mt-1">
                What-If Analysis
              </h2>

              <p className="text-sm text-slate-500 mt-2 max-w-2xl">
                Modify business values and compare the predicted profit with
                the current scenario.
              </p>
            </div>

            <button
              onClick={handleReset}
              className="px-4 py-2 rounded-xl text-sm font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 transition-colors cursor-pointer"
            >
              Reset
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

            <div className="rounded-2xl bg-slate-50 border border-slate-200 p-5">
              <div className="mb-5">
                <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Scenario 01
                </p>

                <h3 className="text-lg font-bold text-slate-900 mt-1">
                  Current Business
                </h3>
              </div>

              <div className="space-y-4">

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                    Quantity
                  </label>

                  <input
                    type="number"
                    value={currentQuantity}
                    onChange={(e) => setCurrentQuantity(e.target.value)}
                    placeholder="e.g. 100"
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                    Revenue
                  </label>

                  <input
                    type="number"
                    value={currentRevenue}
                    onChange={(e) => setCurrentRevenue(e.target.value)}
                    placeholder="e.g. 50000"
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                    Expense
                  </label>

                  <input
                    type="number"
                    value={currentExpense}
                    onChange={(e) => setCurrentExpense(e.target.value)}
                    placeholder="e.g. 30000"
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

              </div>
            </div>

            <div className="rounded-2xl bg-blue-50 border border-blue-100 p-5">
              <div className="mb-5">
                <p className="text-xs font-bold uppercase tracking-wider text-blue-500">
                  Scenario 02
                </p>

                <h3 className="text-lg font-bold text-slate-900 mt-1">
                  What-If Scenario
                </h3>
              </div>

              <div className="space-y-4">

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                    New Quantity
                  </label>

                  <input
                    type="number"
                    value={newQuantity}
                    onChange={(e) => setNewQuantity(e.target.value)}
                    placeholder="e.g. 120"
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                    New Revenue
                  </label>

                  <input
                    type="number"
                    value={newRevenue}
                    onChange={(e) => setNewRevenue(e.target.value)}
                    placeholder="e.g. 60000"
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                    New Expense
                  </label>

                  <input
                    type="number"
                    value={newExpense}
                    onChange={(e) => setNewExpense(e.target.value)}
                    placeholder="e.g. 32000"
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

              </div>
            </div>

          </div>

          <button
            onClick={handleWhatIf}
            disabled={loading}
            className="w-full mt-6 py-3.5 rounded-xl bg-blue-700 text-white font-bold hover:bg-blue-800 disabled:opacity-60 transition-colors cursor-pointer"
          >
            {loading ? "Analyzing Scenario..." : "Run What-If Analysis"}
          </button>

          {error && (
            <div className="mt-5 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm font-semibold text-red-700">
              {error}
            </div>
          )}

          {result && (
            <div className="mt-8">

              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-sm font-bold text-blue-700">
                    Analysis Complete
                  </p>

                  <h3 className="text-xl font-black text-slate-900 mt-1">
                    Scenario Comparison
                  </h3>
                </div>

                <div
                  className={`px-4 py-2 rounded-full text-sm font-bold ${
                    isIncrease
                      ? "bg-green-100 text-green-700"
                      : isDecrease
                      ? "bg-red-100 text-red-700"
                      : "bg-slate-100 text-slate-700"
                  }`}
                >
                  {isIncrease
                    ? "↑ Profit Increase"
                    : isDecrease
                    ? "↓ Profit Decrease"
                    : "→ No Change"}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">

                <div className="rounded-2xl bg-slate-50 border border-slate-200 p-5">
                  <p className="text-sm text-slate-500">
                    Current Predicted Profit
                  </p>

                  <p className="text-2xl font-black text-slate-900 mt-2">
                    ₹{result.current_predicted_profit.toLocaleString()}
                  </p>
                </div>

                <div className="rounded-2xl bg-blue-50 border border-blue-100 p-5">
                  <p className="text-sm text-slate-500">
                    New Predicted Profit
                  </p>

                  <p className="text-2xl font-black text-blue-700 mt-2">
                    ₹{result.new_predicted_profit.toLocaleString()}
                  </p>
                </div>

                <div className="rounded-2xl bg-slate-50 border border-slate-200 p-5">
                  <p className="text-sm text-slate-500">
                    Profit Difference
                  </p>

                  <p
                    className={`text-2xl font-black mt-2 ${
                      isIncrease
                        ? "text-green-600"
                        : isDecrease
                        ? "text-red-600"
                        : "text-slate-900"
                    }`}
                  >
                    {result.profit_difference >= 0 ? "+" : ""}
                    ₹{result.profit_difference.toLocaleString()}
                  </p>
                </div>

              </div>

              <div className="mt-6 rounded-2xl border border-slate-200 p-5">

                <div className="flex justify-between text-sm font-semibold text-slate-600 mb-2">
                  <span>Current Profit</span>
                  <span>New Profit</span>
                </div>

                <div className="h-4 bg-slate-100 rounded-full overflow-hidden">

                  <div
                    className="h-full bg-blue-600 rounded-full transition-all duration-500"
                    style={{
                      width: `${
                        Math.max(
                          5,
                          Math.min(
                            100,
                            (result.current_predicted_profit /
                              Math.max(
                                result.current_predicted_profit,
                                result.new_predicted_profit
                              )) *
                              100
                          )
                        )
                      }%`,
                    }}
                  />

                </div>

                <div className="mt-3 text-center">
                  <span className="text-sm font-semibold text-slate-600">
                    EVORA predicted change:
                  </span>

                  <span
                    className={`ml-2 text-sm font-black ${
                      isIncrease
                        ? "text-green-600"
                        : isDecrease
                        ? "text-red-600"
                        : "text-slate-700"
                    }`}
                  >
                    {result.result}
                  </span>
                </div>

              </div>

            </div>
          )}

        </div>
      </div>
    </div>
  );
}