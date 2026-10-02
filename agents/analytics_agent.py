import pandas as pd


class AnalyticsAgent:

    def analyze(self, df: pd.DataFrame):

        total_revenue = float(df["Revenue"].sum())
        total_expense = float(df["Expense"].sum())
        total_profit = float(total_revenue - total_expense)

        profit_margin = (
            (total_profit / total_revenue) * 100
            if total_revenue != 0
            else 0.0
        )

        insights = []

        if total_profit > 0:
            insights.append("Business is currently profitable.")
        elif total_profit < 0:
            insights.append("Business is currently operating at a loss.")
        else:
            insights.append("Business is currently at break-even.")

        if profit_margin >= 20:
            insights.append(
                f"Profit margin is {profit_margin:.2f}%, indicating positive profitability."
            )
        elif profit_margin > 0:
            insights.append(
                f"Profit margin is {profit_margin:.2f}%, indicating limited profitability."
            )
        else:
            insights.append("Profit margin is negative.")

        if total_revenue > total_expense:
            insights.append("Revenue is higher than total expense.")
        elif total_revenue < total_expense:
            insights.append("Total expense is higher than revenue.")
        else:
            insights.append("Revenue and expense are equal.")

        return {
            "total_revenue": round(total_revenue, 2),
            "total_expense": round(total_expense, 2),
            "total_profit": round(total_profit, 2),
            "profit_margin": round(float(profit_margin), 2),
            "insights": insights
        }