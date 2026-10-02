import pandas as pd
from analytics_agent import AnalyticsAgent

df = pd.DataFrame({
    "Revenue": [50000, 60000, 40000],
    "Expense": [30000, 35000, 25000]
})

agent = AnalyticsAgent()
result = agent.analyze(df)

print(result)