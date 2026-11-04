
import pandas as pd


class AnalyticsAgent:

    def analyze(self, df: pd.DataFrame):

        df = df.copy()

        revenue = pd.to_numeric(df["Revenue"], errors="coerce").fillna(0)
        expense = pd.to_numeric(df["Expense"], errors="coerce").fillna(0)

        total_revenue = float(revenue.sum())
        total_expense = float(expense.sum())
        total_profit = total_revenue - total_expense

        profit_margin = (
            total_profit / total_revenue * 100
            if total_revenue != 0 else 0.0
        )

        insights = []
        recommendations = []

        # Profitability Analysis
        if total_profit > 0:
            insights.append("Business is currently profitable.")
        elif total_profit < 0:
            insights.append("Business is operating at a loss.")
            recommendations.append(
                "Review expenses and identify ways to improve profitability."
            )
        else:
            insights.append("Business is currently at break-even.")

        # Profit Margin Analysis
        if profit_margin >= 20:
            insights.append(
                f"Strong profit margin of {profit_margin:.2f}%."
            )
        elif profit_margin > 0:
            insights.append(
                f"Profit margin is {profit_margin:.2f}%, indicating limited profitability."
            )
            recommendations.append(
                "Explore opportunities to improve profit margins."
            )
        else:
            insights.append("Profit margin is zero or negative.")

        # Revenue and Expense Comparison
        if total_revenue > total_expense:
            insights.append("Revenue is higher than total expenses.")
        elif total_revenue < total_expense:
            insights.append("Expenses are higher than revenue.")
        else:
            insights.append("Revenue and expenses are equal.")

        # Product Performance Analysis
        product_performance = []

        if "Product" in df.columns:

            product_df = df.copy()
            product_df["_Revenue"] = revenue
            product_df["_Expense"] = expense

            grouped = product_df.groupby("Product").agg(
                revenue=("_Revenue", "sum"),
                expense=("_Expense", "sum")
            )

            grouped["profit"] = (
                grouped["revenue"] - grouped["expense"]
            )

            if not grouped.empty:

                best_product = grouped["profit"].idxmax()
                worst_product = grouped["profit"].idxmin()

                best_data = grouped.loc[best_product]
                worst_data = grouped.loc[worst_product]

                product_performance = [
                    {
                        "product": str(product),
                        "revenue": round(float(row["revenue"]), 2),
                        "expense": round(float(row["expense"]), 2),
                        "profit": round(float(row["profit"]), 2)
                    }
                    for product, row in grouped.iterrows()
                ]

                insights.append(
                    f"Best-performing product by profit: {best_product}."
                )

                insights.append(
                    f"Lowest-performing product by profit: {worst_product}."
                )

                if worst_data["profit"] < 0:
                    recommendations.append(
                        f"Review pricing and expenses for {worst_product}."
                    )

        # Date-based Trend Analysis
        trends = []

        if "Date" in df.columns:

            date_df = df.copy()
            date_df["Date"] = pd.to_datetime(
                date_df["Date"], errors="coerce"
            )

            date_df["_Revenue"] = revenue
            date_df["_Expense"] = expense

            date_df = date_df.dropna(subset=["Date"])

            if not date_df.empty:

                date_df["Month"] = (
                    date_df["Date"].dt.to_period("M").astype(str)
                )

                monthly = date_df.groupby("Month").agg(
                    revenue=("_Revenue", "sum"),
                    expense=("_Expense", "sum")
                )

                monthly["profit"] = (
                    monthly["revenue"] - monthly["expense"]
                )

                trends = [
                    {
                        "month": str(month),
                        "revenue": round(float(row["revenue"]), 2),
                        "expense": round(float(row["expense"]), 2),
                        "profit": round(float(row["profit"]), 2)
                    }
                    for month, row in monthly.iterrows()
                ]

                if len(monthly) >= 2:

                    previous = float(monthly["revenue"].iloc[-2])
                    current = float(monthly["revenue"].iloc[-1])

                    if current > previous:
                        insights.append(
                            "Revenue increased compared with the previous month."
                        )
                    elif current < previous:
                        insights.append(
                            "Revenue decreased compared with the previous month."
                        )
                        recommendations.append(
                            "Investigate the reasons behind the recent revenue decline."
                        )
                    else:
                        insights.append(
                            "Revenue remained unchanged compared with the previous month."
                        )

        # Final Analysis
        if not recommendations:
            recommendations.append(
                "Continue monitoring revenue, expenses and profitability."
            )

        return {
            "total_revenue": round(total_revenue, 2),
            "total_expense": round(total_expense, 2),
            "total_profit": round(total_profit, 2),
            "profit_margin": round(float(profit_margin), 2),
            "insights": insights,
            "recommendations": recommendations,
            "product_performance": product_performance,
            "monthly_trends": trends
        }
