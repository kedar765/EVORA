from pathlib import Path

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT_DIR / "data" / "anomaly_training_data.csv"

np.random.seed(42)

rows = 500

quantity = np.random.randint(10, 500, rows)
price_per_unit = np.random.uniform(80, 500, rows)

revenue = quantity * price_per_unit

expense_ratio = np.random.uniform(0.45, 0.90, rows)
expense = revenue * expense_ratio

anomaly = np.zeros(rows, dtype=int)

anomaly_indices = np.random.choice(rows, 25, replace=False)
anomaly[anomaly_indices] = 1

revenue[anomaly_indices] *= np.random.uniform(
    2.0, 5.0, len(anomaly_indices)
)

expense[anomaly_indices] *= np.random.uniform(
    1.5, 3.0, len(anomaly_indices)
)

df = pd.DataFrame({
    "Quantity": quantity,
    "Revenue": revenue.round(2),
    "Expense": expense.round(2),
    "Anomaly": anomaly
})

df.to_csv(DATA_PATH, index=False)

print("Anomaly training data generated successfully.")
print(f"Rows: {len(df)}")
print(f"Normal rows: {(df['Anomaly'] == 0).sum()}")
print(f"Anomaly rows: {(df['Anomaly'] == 1).sum()}")
print(f"Saved to: {DATA_PATH}")