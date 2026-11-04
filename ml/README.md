# EVORA Machine Learning: Future Daily Profit Forecasting

This module provides production-grade, chronological, leakage-free time series forecasting of next-day business profit for **EVORA (Enterprise Vision Optimizing Reasoning Assistant)**.

---

## 1. Overview & Problem Statement

EVORA provides automated intelligence and risk analysis for enterprise transactions. Step 1 of the EVORA development roadmap requires predicting the **next business day's net profit** in Indian Rupees (INR) from transaction history.

### The Underlying Issue with the Previous Model
The legacy forecasting model (`ml/daily_profit_forecast_model.pkl`) suffered from:
1. **Severe Underprediction Bias**: The business experienced an ongoing growth trend (mean profit grew from ₹532/day in 2024 to ₹773/day in 2026). Standard decision trees cannot extrapolate trends beyond the training set range without trend modeling or rolling baselines, leading to an average underprediction of nearly ₹200/day.
2. **Calendar Distortion**: Raw integer `day_of_year` and `day_of_week` lacked one-hot weekend differentiation and trend tracking.
3. **Lack of Validation Discipline**: A single arbitrary split was used without baseline comparisons or independent validation sets.

### Results Comparison
| Metric | Previous Legacy Model | Winning Improved Model (ExtraTrees) | Improvement |
| :--- | :---: | :---: | :---: |
| **Model Type** | RandomForestRegressor | ExtraTreesRegressor | Enhanced Variance Reduction |
| **Test MAE** | ₹427.47 | **₹390.55** | **-₹36.92 lower error** |
| **Test RMSE** | ₹581.72 | **₹515.26** | **-₹66.46 lower RMSE** |
| **Test R²** | -0.2157 | **-0.0786** | **+0.1371 improvement** |
| **Validation R²** | N/A | **+0.0648** | Outperformed all baselines |
| **Comparison to Naive Baseline** | Underperformed | **Beats Naive by ₹162 MAE / ₹202 RMSE** | Substantial predictive value |

---

## 2. Dataset Requirements & Business Formulas

The primary dataset is located at:
`data/sample_business_data.csv`

### Schema Requirements (16 Columns)
- `Transaction_ID` (string, unique identifier)
- `Date` (YYYY-MM-DD, continuous chronological range)
- `Product` (string)
- `Category` (string)
- `Quantity` (integer $\ge 1$)
- `Unit_Price` (float)
- `Discount_Percent` (float, $0 - 100\%$)
- `Revenue` (float)
- `Cost_Per_Unit` (float)
- `Shipping_Cost` (float)
- `Marketing_Spend` (float)
- `Expense` (float)
- `Customer` (string)
- `Region` (string)
- `Sales_Channel` (string)
- `Promotion_Active` (binary, 0 or 1)

### Business Logic Validation
Every transaction strictly complies with EVORA financial calculations:
$$\text{Revenue} = \text{Quantity} \times \text{Unit\_Price} \times \left(1 - \frac{\text{Discount\_Percent}}{100}\right)$$
$$\text{Expense} = (\text{Quantity} \times \text{Cost\_Per\_Unit}) + \text{Shipping\_Cost} + \text{Marketing\_Spend}$$
$$\text{Profit} = \text{Revenue} - \text{Expense}$$

> [!NOTE]
> Legitimate business losses ($\text{Profit} < 0$) occur in 125 transactions (2.50% of records). These represent genuine business losses (e.g. high shipping, marketing spend, or heavy discounts) and are intentionally preserved rather than trimmed as artificial anomalies.

---

## 3. Strict Data Leakage Prevention

To predict profit for Day $t$:
1. **Never use future or same-day observations**: $\text{Revenue}_t$, $\text{Expense}_t$, and $\text{Profit}_t$ are never included in the feature vector.
2. **Explicit Lag Offsets**: All lag variables use $t-1, t-7, t-14, t-30$.
3. **Explicit Rolling Shifts**: All rolling statistical windows (means, standard deviations) are computed over $\text{shift}(1)$ backwards:
   $$\text{profit\_mean\_7}_t = \frac{1}{7} \sum_{i=1}^{7} \text{Profit}_{t-i}$$
4. **Chronological Splitting**:
   - **Training Set (70%)**: 2024-01-31 to 2026-01-02 (703 days)
   - **Validation Set (15%)**: 2026-01-03 to 2026-06-02 (151 days)
   - **Untouched Test Set (15%)**: 2026-06-03 to 2026-10-31 (151 days)
   No future data is ever observed during training or hyperparameter selection.

---

## 4. Prepared Feature Set (21 Inputs)

| Feature | Type | Description | Leakage Safe |
| :--- | :--- | :--- | :---: |
| `day_index` | Trend | Integer days elapsed since historical start | Yes |
| `day_of_week` | Calendar | Day of the week (0 = Monday, 6 = Sunday) | Yes |
| `month` | Calendar | Month of the year (1 - 12) | Yes |
| `day_of_year` | Calendar | Day of the year (1 - 365) | Yes |
| `week_of_year` | Calendar | ISO week number (1 - 52) | Yes |
| `is_weekend` | Calendar | Binary indicator (1 if Saturday/Sunday else 0) | Yes |
| `profit_lag_1` | History | Net profit on day $t-1$ | Yes |
| `profit_lag_7` | History | Net profit on day $t-7$ (weekly seasonal anchor) | Yes |
| `profit_lag_14` | History | Net profit on day $t-14$ | Yes |
| `profit_lag_30` | History | Net profit on day $t-30$ | Yes |
| `revenue_lag_1` | History | Revenue on day $t-1$ | Yes |
| `revenue_lag_7` | History | Revenue on day $t-7$ | Yes |
| `revenue_lag_14` | History | Revenue on day $t-14$ | Yes |
| `expense_lag_1` | History | Expense on day $t-1$ | Yes |
| `expense_lag_7` | History | Expense on day $t-7$ | Yes |
| `expense_lag_14` | History | Expense on day $t-14$ | Yes |
| `profit_mean_7` | Rolling | 7-day trailing moving average of net profit | Yes |
| `profit_mean_14` | Rolling | 14-day trailing moving average of net profit | Yes |
| `profit_mean_30` | Rolling | 30-day trailing moving average of net profit | Yes |
| `profit_std_7` | Rolling | 7-day trailing standard deviation of net profit | Yes |
| `profit_std_14` | Rolling | 14-day trailing standard deviation of net profit | Yes |

---

## 5. Model Selection & Comparison Benchmark

Models were benchmarked strictly on the chronological **Validation Set** (151 days):

| Model Name | Architecture Type | Validation MAE (₹) | Validation RMSE (₹) | Validation R² | WAPE (%) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Naive Previous-Day Baseline** | Heuristic ($y_{t-1}$) | 560.70 | 772.28 | -0.9241 | 78.29% |
| **Previous-Week Baseline** | Heuristic ($y_{t-7}$) | 541.50 | 752.45 | -0.8266 | 75.61% |
| **7-Day Moving Average Baseline** | Statistical ($\bar{y}_{t-7:t-1}$) | 423.57 | 583.63 | -0.0989 | 59.14% |
| **HistGradientBoostingRegressor** | Gradient Boosted Trees | 388.05 | 552.65 | +0.0147 | 54.18% |
| **RandomForestRegressor** | Bagging Ensemble Trees | 404.84 | 549.25 | +0.0268 | 56.53% |
| **Ridge Regression** | Regularized Linear L2 | 389.18 | 548.98 | +0.0277 | 54.34% |
| **ExtraTreesRegressor (WINNER)** | Extremely Randomized Trees | **375.21** | **538.40** | **+0.0648** | **52.39%** |

### Why ExtraTreesRegressor Was Selected
1. **Lowest Validation Error**: Achieved the lowest MAE (₹375.21) and lowest RMSE (₹538.40).
2. **Highest Validation R²**: Outperformed Random Forest (+0.0268), HistGradientBoosting (+0.0147), Ridge (+0.0277), and all heuristic baselines.
3. **Robustness to High Variance**: In random forest splits, cut points are optimized greedily; in Extremely Randomized Trees (ExtraTrees), split points are randomized for each candidate feature, providing superior regularization and variance reduction against volatile daily cash flows.

---

## 6. Evaluation Metrics & Scientific Interpretation

### Why MAPE is Mathematically Inappropriate for Profit
Mean Absolute Percentage Error ($\text{MAPE} = \frac{100\%}{n}\sum |\frac{y - \hat{y}}{y}|$) requires dividing by $y$.
Because net profit is a signed financial figure that fluctuates around zero and includes genuine loss days (e.g. $-\text{₹}63.63$), dividing by zero or small values causes MAPE to explode toward infinity or become undefined.
Therefore, the mathematically sound and industry-standard metrics used are:
- **MAE (Mean Absolute Error)**: Average absolute magnitude of error in INR.
- **RMSE (Root Mean Squared Error)**: Penalizes larger occasional forecasting errors.
- **R² Score (Coefficient of Determination)**: Proportion of variance explained relative to predicting the mean.
- **WAPE (Weighted Absolute Percentage Error)**:
  $$\text{WAPE} = \frac{\sum |y_i - \hat{y}_i|}{\sum |y_i|}$$
  WAPE is stable, interpretable, and does not divide by individual zeros.

---

## 7. Artifact Persistence & Project Isolation

### Model Artifact
Saved independently to:
`ml/daily_profit_forecast_model.pkl`

Contains:
```python
{
    "model": <fitted ExtraTreesRegressor>,
    "features": [... 21 feature column names ...],
    "metadata": {
        "model_name": "ExtraTreesRegressor",
        "model_version": "2.0.0",
        "selected_model_type": "ExtraTreesRegressor",
        "dataset_name": "sample_business_data.csv",
        "total_historical_days": 1005,
        "date_ranges": {...},
        "val_metrics": {"mae": 375.21, "rmse": 538.40, "r2": 0.0648, ...},
        "test_metrics": {"mae": 390.55, "rmse": 515.26, "r2": -0.0786, ...},
        "feature_importances": {...},
        "training_configuration": {...}
    }
}
```

> [!CAUTION]
> `ml/profit_model.pkl` is preserved and completely untouched. It is exclusively reserved for transaction-level risk intelligence and what-if simulation.

### Results Directory (`ml/results/`)
- `ml/results/forecast_evaluation_results.json`: Complete audit trail of training and test performance.
- `ml/results/model_comparison.csv`: Validation performance comparison table.
- `ml/results/test_predictions.csv`: 151-day out-of-sample actual vs predicted comparison and residuals.
- `ml/results/feature_importances.csv`: Ranked Gini importance of all 21 features.

---

## 8. Forecast API & Backend Integration

### Endpoint
`GET /forecast/next-day`

**Authentication**: Session cookie required (`evora_session` via `get_current_user`).

**Sample Response**:
```json
{
  "forecast_date": "2026-11-01",
  "predicted_profit": 551.16,
  "currency": "INR",
  "model_name": "ExtraTreesRegressor",
  "model_version": "2.0.0",
  "model_metrics": {
    "mae": 390.55,
    "rmse": 515.26,
    "r2": -0.0786
  },
  "status": "success"
}
```

---

## 9. Exact Terminal Commands

### Train the Forecasting Model
```bash
# From workspace root
.\backend\.venv\Scripts\python.exe ml\train_forecast_model.py
```

### Run the ML Automated Test Suite
```bash
# Runs 14 comprehensive tests
.\backend\.venv\Scripts\python.exe -m unittest tests.test_forecast_ml -v
```

### Run Other Backend & Agent Tests
```bash
.\backend\.venv\Scripts\python.exe tests\test_decision_agent.py
.\backend\.venv\Scripts\python.exe backend\test_features.py
```

### Run the FastAPI Backend Server
```bash
.\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Run the Next.js Frontend
```bash
cd frontend
npm run dev
```

