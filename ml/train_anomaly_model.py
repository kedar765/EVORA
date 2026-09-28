import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
DATA_PATH = ROOT_DIR / "data" / "anomaly_training_data.csv"
MODEL_PATH = ROOT_DIR / "ml" / "anomaly_model.pkl"

sys.path.append(str(BACKEND_DIR))
from features import prepare_features

df = pd.read_csv(DATA_PATH)

normal_df = df[df["Anomaly"] == 0].copy()
normal_df = normal_df.drop(columns=["Anomaly"])

normal_df = prepare_features(normal_df)

features = [
    "Quantity",
    "Revenue",
    "Expense",
    "Profit_Margin",
    "Revenue_per_Unit",
    "Expense_per_Unit"
]

X = normal_df[features].astype(float)

model = IsolationForest(
    n_estimators=200,
    contamination="auto",
    random_state=42
)

model.fit(X)

joblib.dump(model, MODEL_PATH)

print("Anomaly model trained successfully.")
print(f"Model saved to: {MODEL_PATH}")
print(f"Training rows: {len(X)}")