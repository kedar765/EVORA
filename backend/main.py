
import io
import os
import sys

from pathlib import Path
from urllib.parse import urlsplit

import joblib
import pandas as pd

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel


ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from agents.analytics_agent import AnalyticsAgent
from agents.risk_agent import RiskAgent
from backend.auth import get_current_user, router as auth_router
from backend.features import prepare_features


app = FastAPI(
    title="EVORA API",
    description="AI Business Intelligence & Decision Optimization System",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


# ---------------------------------------
# CSRF Origin Protection
# ---------------------------------------

TRUSTED_ORIGINS = {
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "EVORA_TRUSTED_ORIGINS",
        ",".join([
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]),
    ).split(",")
    if origin.strip()
}

SAFE_METHODS = {
    "GET",
    "HEAD",
    "OPTIONS",
}


def get_request_origin(request: Request):
    origin = request.headers.get("origin")

    if origin:
        return origin

    referer = request.headers.get("referer")

    if not referer:
        return None

    try:
        parsed = urlsplit(referer)

        if (
            parsed.scheme not in ("http", "https")
            or not parsed.netloc
        ):
            return None

        return f"{parsed.scheme}://{parsed.netloc}"

    except ValueError:
        return None


@app.middleware("http")
async def csrf_origin_guard(
    request: Request,
    call_next,
):
    if request.method in SAFE_METHODS:
        return await call_next(request)

    origin = get_request_origin(request)

    if origin not in TRUSTED_ORIGINS:
        return JSONResponse(
            status_code=403,
            content={
                "detail": (
                    "CSRF protection: "
                    "untrusted request origin."
                )
            },
        )

    return await call_next(request)


# ---------------------------------------
# Agents and ML Models
# ---------------------------------------

analytics_agent = AnalyticsAgent()
risk_agent = RiskAgent()

MODEL_FEATURES = [
    "Quantity",
    "Revenue",
    "Expense",
    "Profit_Margin",
    "Revenue_per_Unit",
    "Expense_per_Unit",
]


def load_model(filename: str):
    try:
        loaded_model = joblib.load(
            ROOT_DIR / "ml" / filename
        )
        print(f"Model loaded: {filename}")
        return loaded_model

    except Exception as exc:
        print(f"Could not load {filename}: {exc}")
        return None


model = load_model("profit_model.pkl")
anomaly_model = load_model("anomaly_model.pkl")


def require_profit_model():
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="Profit ML model unavailable.",
        )


# ---------------------------------------
# Risk Scoring
# ---------------------------------------

def risk_details(
    predicted_profit: float | None,
    anomaly_detected: bool,
    profit_margin: float,
):
    score = 60 if anomaly_detected else 10

    if profit_margin < 0:
        score += 25
    elif profit_margin < 10:
        score += 15
    elif profit_margin < 20:
        score += 5

    if predicted_profit is not None and predicted_profit < 0:
        score += 15

    score = int(max(0, min(100, score)))

    level = (
        "LOW"
        if score <= 30
        else "MEDIUM"
        if score <= 60
        else "HIGH"
    )

    return score, level


# ---------------------------------------
# Feature Preparation
# ---------------------------------------

def make_feature_frame(
    quantity: float,
    revenue: float,
    expense: float,
):
    return prepare_features(
        pd.DataFrame(
            [
                {
                    "Quantity": quantity,
                    "Revenue": revenue,
                    "Expense": expense,
                }
            ]
        )
    )


# ---------------------------------------
# CSV Validation
# ---------------------------------------

async def read_business_csv(
    file: UploadFile,
    required_columns: list[str],
):
    if (
        not file.filename
        or not file.filename.lower().endswith(".csv")
    ):
        raise HTTPException(
            status_code=400,
            detail="Please select a CSV file.",
        )

    try:
        contents = await file.read()

        dataframe = pd.read_csv(
            io.BytesIO(contents)
        )

    except (
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        UnicodeDecodeError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid or empty CSV file.",
        ) from exc

    if dataframe.empty:
        raise HTTPException(
            status_code=400,
            detail="The uploaded CSV file is empty.",
        )

    dataframe.columns = [
        str(column).strip()
        for column in dataframe.columns
    ]

    missing = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Required columns are missing from CSV.",
                "missing_columns": missing,
                "required_columns": required_columns,
                "available_columns": list(dataframe.columns),
            },
        )

    for column in required_columns:
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

    dataframe = dataframe.dropna(
        subset=required_columns
    )

    if dataframe.empty:
        raise HTTPException(
            status_code=400,
            detail="No valid numeric data found.",
        )

    return dataframe


# ---------------------------------------
# Public Endpoints
# ---------------------------------------

@app.get("/")
def root():
    return {
        "message": "EVORA Backend is running successfully.",
        "status": "online",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "EVORA Backend",
    }


# ---------------------------------------
# CSV Upload and Business Analysis
# ---------------------------------------

@app.post(
    "/upload",
    dependencies=[Depends(get_current_user)],
)
async def upload_csv(
    file: UploadFile = File(...),
):
    df = await read_business_csv(
        file,
        ["Quantity", "Revenue", "Expense"],
    )

    df["Profit"] = (
        df["Revenue"] - df["Expense"]
    )

    total_revenue = float(df["Revenue"].sum())
    total_expense = float(df["Expense"].sum())
    total_profit = float(df["Profit"].sum())

    profit_margin = (
        total_profit / total_revenue * 100
        if total_revenue
        else 0.0
    )

    features = prepare_features(
        df[
            ["Quantity", "Revenue", "Expense"]
        ].copy()
    )

    predicted_profit = (
        float(
            model.predict(
                features[MODEL_FEATURES]
            ).mean()
        )
        if model is not None
        else None
    )

    anomaly_count = 0
    anomaly_indices = []

    if anomaly_model is not None:
        try:
            results = anomaly_model.predict(
                features[MODEL_FEATURES]
            )

            anomaly_indices = [
                int(index)
                for index, value in enumerate(results)
                if value == -1
            ]

            anomaly_count = len(
                anomaly_indices
            )

        except Exception as exc:
            print(
                f"Anomaly detection error: {exc}"
            )

    anomaly_detected = anomaly_count > 0

    score, level = risk_details(
        predicted_profit,
        anomaly_detected,
        profit_margin,
    )

    risk_analysis = risk_agent.analyze(
        predicted_profit=(
            predicted_profit
            if predicted_profit is not None
            else total_profit
        ),
        anomaly_detected=anomaly_detected,
        risk_score=score,
        risk_level=level,
    )

    analytics_result = analytics_agent.analyze(
        df
    )

    if level == "LOW" and total_profit > 0:
        status = "Healthy & Profitable"

    elif level == "MEDIUM":
        status = "Moderate Risk — Review Recommended"

    elif total_profit < 0:
        status = "Critical — Operating at a Loss"

    else:
        status = "High Risk — Anomalies Detected"

    return {
        "success": True,
        "message": "CSV processed and analyzed successfully.",
        "filename": file.filename,
        "rows_processed": int(len(df)),
        "metrics": {
            "total_revenue": total_revenue,
            "total_expense": total_expense,
            "total_profit": total_profit,
            "total_sales": float(
                df["Quantity"].sum()
            ),
            "average_revenue": float(
                df["Revenue"].mean()
            ),
            "average_expense": float(
                df["Expense"].mean()
            ),
            "average_profit": float(
                df["Profit"].mean()
            ),
            "profit_margin": profit_margin,
        },
        "predicted_profit": predicted_profit,
        "anomaly_detected": anomaly_detected,
        "anomaly_count": anomaly_count,
        "anomaly_indices": anomaly_indices,
        "risk_score": score,
        "risk_level": level,
        "risk_analysis": risk_analysis,
        "analytics": analytics_result,
        "business_status": status,
    }


# ---------------------------------------
# ML Profit Prediction
# ---------------------------------------

class ProfitPredictionRequest(BaseModel):
    Quantity: float
    Revenue: float
    Expense: float


@app.post(
    "/ml/predict-profit",
    dependencies=[Depends(get_current_user)],
)
def predict_profit(
    data: ProfitPredictionRequest,
):
    require_profit_model()

    df = make_feature_frame(
        data.Quantity,
        data.Revenue,
        data.Expense,
    )

    prediction = float(
        model.predict(
            df[MODEL_FEATURES]
        )[0]
    )

    return {
        "success": True,
        "predicted_profit": prediction,
    }


# ---------------------------------------
# Risk Intelligence
# ---------------------------------------

class RiskAnalysisRequest(ProfitPredictionRequest):
    pass


@app.post(
    "/analyze-risk",
    dependencies=[Depends(get_current_user)],
)
def analyze_risk(
    data: RiskAnalysisRequest,
):
    require_profit_model()

    if anomaly_model is None:
        raise HTTPException(
            status_code=503,
            detail="Anomaly model unavailable.",
        )

    df = make_feature_frame(
        data.Quantity,
        data.Revenue,
        data.Expense,
    )

    predicted_profit = float(
        model.predict(
            df[MODEL_FEATURES]
        )[0]
    )

    anomaly_detected = bool(
        anomaly_model.predict(
            df[MODEL_FEATURES]
        )[0] == -1
    )

    profit_margin = float(
        df["Profit_Margin"].iloc[0]
    )

    score, level = risk_details(
        predicted_profit,
        anomaly_detected,
        profit_margin,
    )

    risk_analysis = risk_agent.analyze(
        predicted_profit=predicted_profit,
        anomaly_detected=anomaly_detected,
        risk_score=score,
        risk_level=level,
    )

    return {
        "success": True,
        "predicted_profit": predicted_profit,
        "anomaly_detected": anomaly_detected,
        "risk_score": score,
        "risk_level": level,
        "risk_analysis": risk_analysis,
    }


# ---------------------------------------
# What-If Analysis
# ---------------------------------------

class WhatIfRequest(BaseModel):
    current_quantity: float
    current_revenue: float
    current_expense: float

    new_quantity: float
    new_revenue: float
    new_expense: float


@app.post(
    "/what-if",
    dependencies=[Depends(get_current_user)],
)
def what_if_analysis(
    data: WhatIfRequest,
):
    require_profit_model()

    current_df = make_feature_frame(
        data.current_quantity,
        data.current_revenue,
        data.current_expense,
    )

    new_df = make_feature_frame(
        data.new_quantity,
        data.new_revenue,
        data.new_expense,
    )

    current_profit = float(
        model.predict(
            current_df[MODEL_FEATURES]
        )[0]
    )

    new_profit = float(
        model.predict(
            new_df[MODEL_FEATURES]
        )[0]
    )

    difference = new_profit - current_profit

    if difference > 0:
        result = "Profit may increase"

    elif difference < 0:
        result = "Profit may decrease"

    else:
        result = "No significant change"

    return {
        "success": True,
        "current_predicted_profit": round(
            current_profit, 2
        ),
        "new_predicted_profit": round(
            new_profit, 2
        ),
        "profit_difference": round(
            difference, 2
        ),
        "result": result,
    }


# ---------------------------------------
# Business Analytics
# ---------------------------------------

@app.post(
    "/analytics",
    dependencies=[Depends(get_current_user)],
)
async def analytics(
    file: UploadFile = File(...),
):
    df = await read_business_csv(
        file,
        ["Revenue", "Expense"],
    )

    return {
        "success": True,
        "analysis": analytics_agent.analyze(df),
    }
