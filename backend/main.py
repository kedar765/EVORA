import io
import json
import math
import os
import sys
import time
import uuid

try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit
from typing import Any, Dict, Optional

import joblib
import pandas as pd

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Request,
    UploadFile,
    Query,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel


ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from agents.analytics_agent import AnalyticsAgent
from agents.risk_agent import RiskAgent
from agents.decision_agent import DecisionOptimizationAgent

from backend.auth import (
    database,
    get_current_user,
    router as auth_router,
)
from backend.features import prepare_features
from ml.forecast import DailyProfitForecaster
from schemas.agent_schemas import AgentWorkflowRequest
from workflows.graph import run_evora_workflow


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
decision_agent = DecisionOptimizationAgent()

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
daily_profit_forecaster = DailyProfitForecaster()


def require_profit_model():
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="Profit ML model unavailable.",
        )


def require_forecast_model():
    if not daily_profit_forecaster.is_loaded or daily_profit_forecaster.model is None:
        raise HTTPException(
            status_code=503,
            detail="Daily profit forecast model unavailable.",
        )


# ---------------------------------------
# Risk Scoring
# ---------------------------------------

def risk_details(
    predicted_profit: float | None,
    anomaly_percentage: float,
    profit_margin: float,
):
    score = 5

    if anomaly_percentage > 3:
        score += 25
    elif anomaly_percentage > 1:
        score += 15
    elif anomaly_percentage > 0:
        score += 5

    if profit_margin < 0:
        score += 35
    elif profit_margin < 10:
        score += 20
    elif profit_margin < 20:
        score += 10

    if predicted_profit is not None and predicted_profit < 0:
        score += 20

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
# CSV Validation and Private Storage
# ---------------------------------------

MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024
UPLOAD_STORAGE_DIR = ROOT_DIR / "backend" / "storage" / "uploads"


def make_json_safe(value):
    """Convert common Pandas/NumPy values into JSON-safe values."""
    if isinstance(value, dict):
        return {str(key): make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [make_json_safe(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item") and callable(value.item):
        try:
            value = value.item()
        except (ValueError, TypeError):
            pass
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "isoformat") and callable(value.isoformat):
        return value.isoformat()
    return str(value)


def persist_uploaded_dataset(
    file_contents: bytes,
    original_filename: str,
    dataframe: pd.DataFrame,
    user_id: str,
    analysis_result: dict,
    original_columns: list[str] | None = None,
) -> str:
    """Store a private CSV and its successful upload analysis."""
    dataset_id = str(uuid.uuid4())
    analysis_id = str(uuid.uuid4())
    safe_original_filename = str(original_filename or "uploaded.csv")
    safe_original_filename = safe_original_filename.replace("\\", "/").split("/")[-1][:255]
    if not safe_original_filename:
        safe_original_filename = "uploaded.csv"

    orig_ext = Path(safe_original_filename).suffix.lower()
    if orig_ext not in (".csv", ".xlsx", ".xls"):
        orig_ext = ".csv"
    stored_filename = f"{dataset_id}{orig_ext}"
    UPLOAD_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    final_path = UPLOAD_STORAGE_DIR / stored_filename
    temporary_path = UPLOAD_STORAGE_DIR / f".{stored_filename}.tmp"

    date_start = None
    date_end = None
    if "Date" in dataframe.columns:
        parsed_dates = pd.to_datetime(dataframe["Date"], errors="coerce").dropna()
        if not parsed_dates.empty:
            date_start = parsed_dates.min().date().isoformat()
            date_end = parsed_dates.max().date().isoformat()

    relative_storage_path = str(final_path.relative_to(ROOT_DIR))
    uploaded_at = int(time.time())
    safe_result = dict(analysis_result)
    safe_result["dataset_id"] = dataset_id
    saved_columns = [
        str(column)
        for column in (original_columns or dataframe.columns)
    ]
    input_summary = {
        "original_filename": safe_original_filename,
        "rows_processed": int(len(dataframe)),
        "column_count": len(saved_columns),
        "columns": saved_columns,
    }

    try:
        temporary_path.write_bytes(file_contents)
        temporary_path.replace(final_path)
        with database() as connection:
            connection.execute(
                """
                INSERT INTO datasets (
                    id, user_id, original_filename, stored_filename,
                    storage_path, uploaded_at, row_count, column_count,
                    columns_json, date_start, date_end, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dataset_id,
                    user_id,
                    safe_original_filename,
                    stored_filename,
                    relative_storage_path,
                    uploaded_at,
                    int(len(dataframe)),
                    len(saved_columns),
                    json.dumps(saved_columns),
                    date_start,
                    date_end,
                    "ready",
                ),
            )
            connection.execute(
                """
                INSERT INTO analysis_history (
                    id, user_id, dataset_id, analysis_type, created_at,
                    input_summary_json, result_json, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analysis_id,
                    user_id,
                    dataset_id,
                    "upload_analysis",
                    uploaded_at,
                    json.dumps(make_json_safe(input_summary), allow_nan=False),
                    json.dumps(make_json_safe(safe_result), allow_nan=False),
                    "success",
                ),
            )
    except Exception:
        temporary_path.unlink(missing_ok=True)
        final_path.unlink(missing_ok=True)
        raise

    return dataset_id


def save_analysis_history(
    user_id: str,
    analysis_type: str,
    input_summary: dict,
    result: dict,
    dataset_id: str | None = None,
) -> tuple[str, int]:
    """Persist a successful analysis result for the authenticated user."""
    analysis_id = str(uuid.uuid4())
    created_at = int(time.time())

    with database() as connection:
        if dataset_id is not None:
            owned_dataset = connection.execute(
                "SELECT id FROM datasets WHERE id = ? AND user_id = ?",
                (dataset_id, user_id),
            ).fetchone()
            if owned_dataset is None:
                raise HTTPException(
                    status_code=404,
                    detail="Dataset not found.",
                )

        connection.execute(
            """
            INSERT INTO analysis_history (
                id, user_id, dataset_id, analysis_type, created_at,
                input_summary_json, result_json, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                analysis_id,
                user_id,
                dataset_id,
                analysis_type,
                created_at,
                json.dumps(make_json_safe(input_summary), allow_nan=False),
                json.dumps(make_json_safe(result), allow_nan=False),
                "success",
            ),
        )

    return analysis_id, created_at


async def read_business_csv(
    file: UploadFile,
    required_columns: list[str],
):
    filename_lower = (file.filename or "").lower()
    is_csv = filename_lower.endswith(".csv")
    is_excel = filename_lower.endswith(".xlsx") or filename_lower.endswith(".xls")

    if not file.filename or not (is_csv or is_excel):
        raise HTTPException(
            status_code=400,
            detail="Please select a CSV file (.csv) or Excel (.xlsx) file.",
        )

    try:
        contents = await file.read(MAX_UPLOAD_SIZE_BYTES + 1)
        if len(contents) > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail="File exceeds the 25 MB upload limit.",
            )

        if is_excel:
            dataframe = pd.read_excel(
                io.BytesIO(contents),
                engine="openpyxl" if filename_lower.endswith(".xlsx") else None,
            )
        else:
            dataframe = pd.read_csv(
                io.BytesIO(contents)
            )

    except HTTPException:
        raise
    except (
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        UnicodeDecodeError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid or empty data file.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to read file: {exc}",
        ) from exc

    if dataframe.empty:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    dataframe.columns = [
        str(column).strip()
        for column in dataframe.columns
    ]

    # Map semantic column alternatives if canonical required columns are missing
    if any(column not in dataframe.columns for column in required_columns):
        from tools.dataset_tools import identify_semantic_columns
        semantic_map = identify_semantic_columns(list(dataframe.columns))
        for req in required_columns:
            req_lower = req.lower()
            if req not in dataframe.columns and req_lower in semantic_map:
                dataframe[req] = dataframe[semantic_map[req_lower]]

        # If Expense is missing but Quantity and Unit_Cost are present, calculate total Expense
        if "Expense" not in dataframe.columns and "unit_cost" in semantic_map:
            qty_col = semantic_map.get("quantity") or ("Quantity" if "Quantity" in dataframe.columns else None)
            unit_c_col = semantic_map["unit_cost"]
            if qty_col and qty_col in dataframe.columns:
                q_ser = pd.to_numeric(dataframe[qty_col], errors="coerce").fillna(1.0)
                uc_ser = pd.to_numeric(dataframe[unit_c_col], errors="coerce").fillna(0.0)
                dataframe["Expense"] = q_ser * uc_ser

        # If Revenue is missing but Quantity and Unit_Price are present, calculate total Revenue
        if "Revenue" not in dataframe.columns and "unit_price" in semantic_map:
            qty_col = semantic_map.get("quantity") or ("Quantity" if "Quantity" in dataframe.columns else None)
            unit_p_col = semantic_map["unit_price"]
            if qty_col and qty_col in dataframe.columns:
                q_ser = pd.to_numeric(dataframe[qty_col], errors="coerce").fillna(1.0)
                up_ser = pd.to_numeric(dataframe[unit_p_col], errors="coerce").fillna(0.0)
                dataframe["Revenue"] = q_ser * up_ser

    missing = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Required columns are missing from file.",
                "missing_columns": missing,
                "required_columns": required_columns,
                "available_columns": list(dataframe.columns),
            },
        )

    for column in required_columns:
        if dataframe[column].dtype == object:
            dataframe[column] = (
                dataframe[column].astype(str)
                .str.replace(r"[\$,₹,€,£,\s]", "", regex=True)
                .str.replace(",", "", regex=False)
            )
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )
        dataframe[column] = dataframe[column].replace(
            [float("inf"), float("-inf")],
            pd.NA,
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

@app.post("/upload")
async def upload_csv(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    df = await read_business_csv(
        file,
        ["Quantity", "Revenue", "Expense"],
    )
    original_columns = [str(column) for column in df.columns]

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

    # Unsupervised IsolationForest anomaly detection on the active business dataset
    if len(df) >= 15:
        from sklearn.ensemble import IsolationForest
        try:
            iso = IsolationForest(
                n_estimators=100,
                contamination=0.05,
                random_state=42,
            )
            preds = iso.fit_predict(features[MODEL_FEATURES].astype(float))
            anomaly_indices = [
                int(index)
                for index, value in enumerate(preds)
                if value == -1
            ]
            anomaly_count = len(anomaly_indices)
        except Exception as exc:
            print(f"IsolationForest error: {exc}")
    elif anomaly_model is not None:
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

    anomaly_percentage = (
        anomaly_count / len(df)
    ) * 100

    score, level = risk_details(
        predicted_profit,
        anomaly_percentage,
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

    response_data = {
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

    try:
        await file.seek(0)
        file_contents = await file.read()
        user_id = user.get("id") if isinstance(user, dict) else None
        if user_id:
            dataset_id = persist_uploaded_dataset(
                file_contents=file_contents,
                original_filename=file.filename,
                dataframe=df,
                user_id=user_id,
                analysis_result=response_data,
                original_columns=original_columns,
            )
            response_data["dataset_id"] = dataset_id
    except HTTPException:
        raise
    except Exception as exc:
        print(f"Dataset persistence error: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Analysis completed, but the dataset could not be saved.",
        ) from exc

    return response_data


# ---------------------------------------
# Dataset and Analysis History Read APIs
# ---------------------------------------

def _parse_stored_json(value, default):
    if value is None:
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Stored dataset or analysis metadata is invalid.",
        ) from exc


def _get_owned_dataset(connection, dataset_id: str, user_id: str):
    row = connection.execute(
        """
        SELECT *
        FROM datasets
        WHERE id = ? AND user_id = ?
        """,
        (dataset_id, user_id),
    ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found.",
        )

    return row


def _dataset_response(row):
    return {
        "dataset_id": row["id"],
        "filename": row["original_filename"],
        "uploaded_at": row["uploaded_at"],
        "rows": row["row_count"],
        "columns_count": row["column_count"],
        "columns": _parse_stored_json(row["columns_json"], []),
        "date_start": row["date_start"],
        "date_end": row["date_end"],
        "status": row["status"],
    }


def _history_list_response(row):
    return {
        "analysis_id": row["id"],
        "dataset_id": row["dataset_id"],
        "analysis_type": row["analysis_type"],
        "created_at": row["created_at"],
        "input_summary": _parse_stored_json(
            row["input_summary_json"], {}
        ),
        "status": row["status"],
    }


def _date_timestamp(value: str, end_of_day: bool = False) -> float:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Dates must use YYYY-MM-DD format.",
        ) from exc

    if end_of_day:
        parsed += timedelta(days=1)

    return parsed.timestamp()


@app.get("/datasets")
def list_datasets(
    user: dict = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    with database() as connection:
        total = connection.execute(
            "SELECT COUNT(*) FROM datasets WHERE user_id = ?",
            (user["id"],),
        ).fetchone()[0]

        rows = connection.execute(
            """
            SELECT *
            FROM datasets
            WHERE user_id = ?
            ORDER BY uploaded_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (user["id"], limit, offset),
        ).fetchall()

    return {
        "success": True,
        "total": total,
        "limit": limit,
        "offset": offset,
        "datasets": [_dataset_response(row) for row in rows],
    }


@app.get("/datasets/{dataset_id}")
def get_dataset(
    dataset_id: str,
    user: dict = Depends(get_current_user),
):
    with database() as connection:
        row = _get_owned_dataset(
            connection,
            dataset_id,
            user["id"],
        )

    return {
        "success": True,
        "dataset": _dataset_response(row),
    }


@app.get("/datasets/{dataset_id}/preview")
def preview_dataset(
    dataset_id: str,
    user: dict = Depends(get_current_user),
    rows: int = Query(10, ge=1, le=50),
):
    with database() as connection:
        dataset = _get_owned_dataset(
            connection,
            dataset_id,
            user["id"],
        )

    stored_path = Path(dataset["storage_path"])
    if stored_path.is_absolute():
        raise HTTPException(
            status_code=500,
            detail="Stored dataset path is invalid.",
        )

    upload_root = UPLOAD_STORAGE_DIR.resolve()
    csv_path = (ROOT_DIR / stored_path).resolve()

    try:
        csv_path.relative_to(upload_root)
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail="Stored dataset path is outside private storage.",
        ) from exc

    if not csv_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Stored dataset file is unavailable.",
        )

    try:
        orig_ext = Path(dataset["original_filename"] or "").suffix.lower()
        if csv_path.suffix.lower() in (".xlsx", ".xls") or orig_ext in (".xlsx", ".xls"):
            preview_df = pd.read_excel(
                csv_path,
                nrows=rows,
                engine="openpyxl" if (csv_path.suffix.lower() == ".xlsx" or orig_ext == ".xlsx") else None,
            )
        else:
            preview_df = pd.read_csv(csv_path, nrows=rows)
        records = make_json_safe(preview_df.to_dict(orient="records"))
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not read the stored dataset.",
        ) from exc

    return {
        "success": True,
        "dataset_id": dataset_id,
        "filename": dataset["original_filename"],
        "columns": list(preview_df.columns),
        "preview_rows": len(records),
        "data": records,
    }


@app.get("/datasets/{dataset_id}/history")
def list_dataset_history(
    dataset_id: str,
    user: dict = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    with database() as connection:
        _get_owned_dataset(connection, dataset_id, user["id"])

        total = connection.execute(
            """
            SELECT COUNT(*)
            FROM analysis_history
            WHERE user_id = ? AND dataset_id = ?
            """,
            (user["id"], dataset_id),
        ).fetchone()[0]

        rows = connection.execute(
            """
            SELECT *
            FROM analysis_history
            WHERE user_id = ? AND dataset_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (user["id"], dataset_id, limit, offset),
        ).fetchall()

    return {
        "success": True,
        "total": total,
        "limit": limit,
        "offset": offset,
        "history": [_history_list_response(row) for row in rows],
    }


@app.get("/analysis-history")
def list_analysis_history(
    user: dict = Depends(get_current_user),
    analysis_type: str | None = Query(None, max_length=80),
    dataset_id: str | None = Query(None, max_length=80),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    conditions = ["user_id = ?"]
    parameters = [user["id"]]

    if analysis_type:
        conditions.append("analysis_type = ?")
        parameters.append(analysis_type)

    if dataset_id:
        conditions.append("dataset_id = ?")
        parameters.append(dataset_id)

    if start_date:
        conditions.append("created_at >= ?")
        parameters.append(_date_timestamp(start_date))

    if end_date:
        conditions.append("created_at < ?")
        parameters.append(_date_timestamp(end_date, end_of_day=True))

    if start_date and end_date:
        if _date_timestamp(start_date) >= _date_timestamp(end_date, end_of_day=True):
            raise HTTPException(
                status_code=400,
                detail="start_date must be on or before end_date.",
            )

    where_clause = " AND ".join(conditions)

    with database() as connection:
        total = connection.execute(
            f"SELECT COUNT(*) FROM analysis_history WHERE {where_clause}",
            parameters,
        ).fetchone()[0]

        rows = connection.execute(
            f"""
            SELECT *
            FROM analysis_history
            WHERE {where_clause}
            ORDER BY created_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            [*parameters, limit, offset],
        ).fetchall()

    return {
        "success": True,
        "total": total,
        "limit": limit,
        "offset": offset,
        "history": [_history_list_response(row) for row in rows],
    }


@app.get("/analysis-history/{analysis_id}")
def get_analysis_history_item(
    analysis_id: str,
    user: dict = Depends(get_current_user),
):
    with database() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM analysis_history
            WHERE id = ? AND user_id = ?
            """,
            (analysis_id, user["id"]),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Analysis history item not found.",
        )

    return {
        "success": True,
        "analysis": {
            **_history_list_response(row),
            "result": _parse_stored_json(row["result_json"], {}),
        },
    }


# ---------------------------------------
# ML Profit Prediction
# ---------------------------------------

class ProfitPredictionRequest(BaseModel):
    Quantity: float
    Revenue: float
    Expense: float


@app.post("/ml/predict-profit")
def predict_profit(
    data: ProfitPredictionRequest,
    user: dict = Depends(get_current_user),
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

    response = {
        "success": True,
        "predicted_profit": prediction,
    }

    user_id = user.get("id") if isinstance(user, dict) else None
    if user_id:
        analysis_id, created_at = save_analysis_history(
            user_id=user_id,
            analysis_type="profit_prediction",
            input_summary={
                "quantity": data.Quantity,
                "revenue": data.Revenue,
                "expense": data.Expense,
            },
            result=response,
        )
        response["analysis_id"] = analysis_id
        response["created_at"] = created_at
    return response


# ---------------------------------------
# Risk Intelligence
# ---------------------------------------

class RiskAnalysisRequest(ProfitPredictionRequest):
    pass


@app.post("/analyze-risk")
def analyze_risk(
    data: RiskAnalysisRequest,
    user: dict = Depends(get_current_user),
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

    anomaly_percentage = (
    100.0 if anomaly_detected else 0.0
)

    score, level = risk_details(
        predicted_profit,
        anomaly_percentage,
        profit_margin,
    )

    risk_analysis = risk_agent.analyze(
        predicted_profit=predicted_profit,
        anomaly_detected=anomaly_detected,
        risk_score=score,
        risk_level=level,
    )

    response = {
        "success": True,
        "predicted_profit": predicted_profit,
        "anomaly_detected": anomaly_detected,
        "risk_score": score,
        "risk_level": level,
        "risk_analysis": risk_analysis,
    }

    user_id = user.get("id") if isinstance(user, dict) else None
    if user_id:
        analysis_id, created_at = save_analysis_history(
            user_id=user_id,
            analysis_type="risk_analysis",
            input_summary={
                "quantity": data.Quantity,
                "revenue": data.Revenue,
                "expense": data.Expense,
            },
            result=response,
        )
        response["analysis_id"] = analysis_id
        response["created_at"] = created_at
    return response


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
    dataset_id: Optional[str] = None


@app.post("/what-if")
def what_if_analysis(
    data: WhatIfRequest,
    user: Optional[dict] = Depends(get_current_user),
):
    require_profit_model()

    # 1. Deterministic Aggregate Financial Calculations (Ground Truth Accounting)
    current_profit = float(data.current_revenue - data.current_expense)
    new_profit = float(data.new_revenue - data.new_expense)
    profit_difference = float(new_profit - current_profit)

    current_margin = float(
        (current_profit / data.current_revenue * 100.0)
        if data.current_revenue > 0
        else 0.0
    )
    new_margin = float(
        (new_profit / data.new_revenue * 100.0)
        if data.new_revenue > 0
        else 0.0
    )
    margin_difference = float(new_margin - current_margin)
    percentage_profit_improvement = float(
        (profit_difference / abs(current_profit) * 100.0)
        if current_profit != 0
        else 0.0
    )

    # 2. Dataset Context & Horizon Estimation
    user_id = user.get("id") if isinstance(user, dict) else None
    dataset_path = None
    days_count = 1

    if data.dataset_id and user_id:
        with database() as conn:
            row = conn.execute(
                "SELECT storage_path FROM datasets WHERE id = ? AND user_id = ?",
                (data.dataset_id, user_id),
            ).fetchone()
            if row:
                dataset_path = row["storage_path"]
    elif user_id:
        with database() as conn:
            row = conn.execute(
                "SELECT storage_path FROM datasets WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 1",
                (user_id,),
            ).fetchone()
            if row:
                dataset_path = row["storage_path"]

    dataset_df = None
    if dataset_path and Path(dataset_path).exists():
        try:
            p = str(dataset_path).lower()
            if p.endswith((".xlsx", ".xls")):
                dataset_df = pd.read_excel(dataset_path)
            else:
                dataset_df = pd.read_csv(dataset_path)
            if "Date" in dataset_df.columns:
                days_count = len(dataset_df["Date"].dropna().unique())
        except Exception:
            dataset_df = None

    if days_count <= 1:
        if data.current_revenue > 5_000_000:
            days_count = 184
        elif data.current_revenue > 500_000:
            days_count = 90
        elif data.current_revenue > 50_000:
            days_count = 30
        else:
            days_count = 1

    days_count = max(1, days_count)

    # 3. Next-Day ML Forecasting Horizon Comparison
    forecast_horizon = "1-day (Next Business Day)"
    baseline_daily_profit = 0.0
    daily_profit_delta = 0.0

    if dataset_df is not None and daily_profit_forecaster.is_loaded and len(dataset_df) >= 30:
        try:
            fc_res = daily_profit_forecaster.predict_next_day(historical_df=dataset_df)
            baseline_daily_profit = float(fc_res.get("predicted_profit", 0.0))
        except Exception:
            baseline_daily_profit = round(current_profit / days_count, 2)
    else:
        baseline_daily_profit = round(current_profit / days_count, 2)

    daily_profit_delta = round(profit_difference / days_count, 2)
    proposed_daily_profit = round(baseline_daily_profit + daily_profit_delta, 2)

    # 4. Format Human-Readable Result Summary
    if profit_difference > 0:
        result = f"Profit may increase by ₹{profit_difference:,.2f} ({'+' if percentage_profit_improvement >= 0 else ''}{percentage_profit_improvement:.2f}%)"
    elif profit_difference < 0:
        result = f"Profit may decrease by ₹{abs(profit_difference):,.2f} ({percentage_profit_improvement:.2f}%)"
    else:
        result = "No significant change"

    response = {
        "success": True,
        "current_predicted_profit": round(current_profit, 2),
        "new_predicted_profit": round(new_profit, 2),
        "profit_difference": round(profit_difference, 2),
        "result": result,
        "aggregate_analysis": {
            "current_revenue": round(data.current_revenue, 2),
            "current_expense": round(data.current_expense, 2),
            "current_profit": round(current_profit, 2),
            "current_margin": round(current_margin, 2),
            "target_revenue": round(data.new_revenue, 2),
            "target_expense": round(data.new_expense, 2),
            "proposed_profit": round(new_profit, 2),
            "proposed_margin": round(new_margin, 2),
            "profit_delta": round(profit_difference, 2),
            "margin_delta": round(margin_difference, 2),
            "percentage_profit_improvement": round(percentage_profit_improvement, 2),
        },
        "forecast_comparison": {
            "horizon": forecast_horizon,
            "days_in_period": days_count,
            "baseline_daily_profit": round(baseline_daily_profit, 2),
            "proposed_daily_profit": round(proposed_daily_profit, 2),
            "daily_profit_delta": round(daily_profit_delta, 2),
        },
    }

    if user_id:
        analysis_id, created_at = save_analysis_history(
            user_id=user_id,
            analysis_type="what_if_analysis",
            dataset_id=data.dataset_id,
            input_summary={
                "current_quantity": data.current_quantity,
                "current_revenue": data.current_revenue,
                "current_expense": data.current_expense,
                "new_quantity": data.new_quantity,
                "new_revenue": data.new_revenue,
                "new_expense": data.new_expense,
                "dataset_id": data.dataset_id,
            },
            result=response,
        )
        response["analysis_id"] = analysis_id
        response["created_at"] = created_at
    return response


# ---------------------------------------
# Decision Optimization
# ---------------------------------------

class DecisionRecommendationRequest(BaseModel):
    analytics: Optional[Dict[str, Any]] = None
    risk: Optional[Dict[str, Any]] = None
    scenario: Optional[Dict[str, Any]] = None


@app.post("/decision/recommend")
def get_decision_recommendations(
    data: DecisionRecommendationRequest,
    user: dict = Depends(get_current_user),
):
    decision_result = decision_agent.recommend(
        analytics=data.analytics,
        risk=data.risk,
        scenario=data.scenario,
    )

    response = {
        "success": True,
        "decision": make_json_safe(decision_result),
    }

    risk_level = None

    if data.risk:
        risk_level = data.risk.get("risk_level")

        if risk_level is None:
            risk_analysis = data.risk.get("risk_analysis")

            if isinstance(risk_analysis, dict):
                risk_level = risk_analysis.get("risk_level")

    user_id = user.get("id") if isinstance(user, dict) else None
    if user_id:
        analysis_id, created_at = save_analysis_history(
            user_id=user_id,
            analysis_type="decision_recommendation",
            input_summary={
                "risk_level": risk_level,
                "has_analytics": data.analytics is not None,
                "has_risk": data.risk is not None,
                "has_scenario": data.scenario is not None,
            },
            result=response,
        )
        response["analysis_id"] = analysis_id
        response["created_at"] = created_at

    return response


# ---------------------------------------
# Business Analytics
# ---------------------------------------

@app.post("/analytics")
async def analytics(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    df = await read_business_csv(
        file,
        ["Revenue", "Expense"],
    )

    analysis_result = analytics_agent.analyze(df)
    response = {
        "success": True,
        "analysis": make_json_safe(analysis_result),
    }

    original_filename = (
        str(file.filename or "uploaded.csv")
        .replace("\\", "/")
        .split("/")[-1][:255]
    )
    input_summary = {
        "original_filename": original_filename,
        "rows_processed": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": [str(column) for column in df.columns],
    }

    user_id = user.get("id") if isinstance(user, dict) else None
    if user_id:
        analysis_id, created_at = save_analysis_history(
            user_id=user_id,
            analysis_type="business_analytics",
            input_summary=input_summary,
            result=response,
        )
        response["analysis_id"] = analysis_id
        response["created_at"] = created_at
    return response


# ---------------------------------------
# Future Profit Forecasting
# ---------------------------------------

@app.get("/forecast/next-day")
def get_next_day_forecast(
    dataset_id: Optional[str] = Query(None, description="Optional dataset ID belonging to the authenticated user"),
    user: dict = Depends(get_current_user),
):
    require_forecast_model()

    # Normalize parameters for both FastAPI HTTP routing and direct Python calls
    actual_dataset_id = dataset_id if isinstance(dataset_id, str) else None
    actual_user = user if isinstance(user, dict) else {}
    user_id = actual_user.get("id")

    historical_df = None
    dataset_meta = None

    if actual_dataset_id is not None:
        clean_dataset_id = actual_dataset_id.strip()
        if not clean_dataset_id:
            raise HTTPException(status_code=400, detail="dataset_id cannot be empty.")
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required.")

        from tools.dataset_tools import load_user_dataset, DatasetAccessError

        try:
            historical_df, dataset_meta = load_user_dataset(
                dataset_id=clean_dataset_id,
                user_id=user_id,
            )
        except DatasetAccessError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Failed to load dataset: {str(exc)}")

        # Validate time-series columns
        if not dataset_meta.get("has_date") or "Date" not in historical_df.columns or historical_df["Date"].dropna().empty:
            raise HTTPException(
                status_code=400,
                detail="Dataset must contain a valid 'Date' column with parseable timestamps for forecasting.",
            )

        orig_cols_lower = [str(c).lower().strip() for c in dataset_meta.get("original_columns", [])]
        semantic_map = dataset_meta.get("semantic_mapping", {})
        has_rev = "revenue" in semantic_map or any(c in orig_cols_lower for c in ["revenue", "sales", "turnover", "income"])
        has_exp = "expense" in semantic_map or any(c in orig_cols_lower for c in ["expense", "expenses", "cost", "spending", "cogs", "expenditure"])
        has_unit_financials = any(c in orig_cols_lower for c in ["quantity", "qty"]) and \
                              any(c in orig_cols_lower for c in ["unit_price", "price"]) and \
                              any(c in orig_cols_lower for c in ["cost_per_unit", "unit_cost"])

        if not ((has_rev and has_exp) or has_unit_financials):
            raise HTTPException(
                status_code=400,
                detail="Dataset must contain either ['Revenue', 'Expense'] or ['Quantity', 'Unit_Price', 'Cost_Per_Unit'] columns.",
            )

    try:
        if historical_df is not None:
            forecast_result = daily_profit_forecaster.predict_next_day(historical_df=historical_df)
        else:
            forecast_result = daily_profit_forecaster.predict_next_day()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Forecasting error: {str(exc)}",
        ) from exc

    response = make_json_safe(forecast_result)
    if not isinstance(response, dict):
        response = {"prediction": response, "success": True}

    if dataset_meta:
        response["dataset_id"] = dataset_meta.get("dataset_id")
        response["filename"] = dataset_meta.get("filename")

    if user_id:
        input_summary = {
            "source": "user_dataset" if dataset_meta else "stored_forecast_history",
        }
        if dataset_meta:
            input_summary["dataset_id"] = dataset_meta.get("dataset_id")
            input_summary["filename"] = dataset_meta.get("filename")
            input_summary["row_count"] = dataset_meta.get("row_count")
            input_summary["date_range"] = f"{dataset_meta.get('date_start')} to {dataset_meta.get('date_end')}"

        analysis_id, created_at = save_analysis_history(
            user_id=user_id,
            analysis_type="future_profit_forecast",
            input_summary=input_summary,
            result=response,
            dataset_id=dataset_meta.get("dataset_id") if dataset_meta else None,
        )
        response["analysis_id"] = analysis_id
        response["created_at"] = created_at

    return response


@app.post("/forecast/next-day")
async def post_next_day_forecast(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    require_forecast_model()
    df = await read_business_csv(
        file,
        ["Revenue", "Expense"],
    )
    try:
        forecast_result = daily_profit_forecaster.predict_next_day(historical_df=df)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Forecasting error: {str(exc)}",
        ) from exc

    response = make_json_safe(forecast_result)
    user_id = user.get("id") if isinstance(user, dict) else None
    if user_id:
        input_summary = {
            "original_filename": (file.filename or "uploaded.csv").replace("\\", "/").split("/")[-1][:255],
            "rows_processed": int(len(df)),
            "columns": [str(column) for column in df.columns],
        }
        analysis_id, created_at = save_analysis_history(
            user_id=user_id,
            analysis_type="future_profit_forecast",
            input_summary=input_summary,
            result=response if isinstance(response, dict) else {"prediction": response},
        )

        if isinstance(response, dict):
            response["analysis_id"] = analysis_id
            response["created_at"] = created_at
            return response

        return {
            "success": True,
            "prediction": response,
            "analysis_id": analysis_id,
            "created_at": created_at,
        }

    return response if isinstance(response, dict) else {
        "success": True,
        "prediction": response,
    }


# ---------------------------------------
# Multi-Agent Workflow Orchestration
# ---------------------------------------

@app.post("/agents/run")
def run_agents_workflow(
    data: AgentWorkflowRequest,
    user: dict = Depends(get_current_user),
):
    """
    Executes the complete EVORA LangGraph Multi-Agent Workflow:
    Dataset Validation -> Analytics Agent -> Risk Agent -> Decision Optimization Agent -> Final Report.
    """
    user_id = user["id"]
    dataset_id = str(data.dataset_id).strip()

    if not dataset_id:
        raise HTTPException(
            status_code=400,
            detail="dataset_id is required.",
        )

    # Verify dataset exists and is owned by the user
    with database() as connection:
        owned_dataset = connection.execute(
            "SELECT id, original_filename FROM datasets WHERE id = ? AND user_id = ?",
            (dataset_id, user_id),
        ).fetchone()

        if owned_dataset is None:
            raise HTTPException(
                status_code=404,
                detail=f"Dataset '{dataset_id}' not found or access unauthorized.",
            )

    import concurrent.futures

    workflow_timeout = float(os.getenv("EVORA_WORKFLOW_TIMEOUT", "120.0"))
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                run_evora_workflow,
                dataset_id=dataset_id,
                user_id=user_id,
                user_query=data.user_query or "",
            )
            workflow_output = future.result(timeout=workflow_timeout)
    except concurrent.futures.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Multi-agent workflow execution timed out.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Workflow execution failed: {str(exc)}",
        ) from exc

    status = workflow_output.get("execution_status", "completed")
    errors = workflow_output.get("errors", [])

    response_payload = {
        "success": status in {"completed", "partial"},
        "dataset_id": dataset_id,
        "user_query": data.user_query or "",
        "status": status,
        "errors": errors,
        "step_durations": workflow_output.get("step_durations", {}),
        "agent_statuses": workflow_output.get("agent_statuses", {}),
        "models_used": workflow_output.get("models_used", {}),
        "execution_modes": workflow_output.get("execution_modes", {}),
        "analytics": make_json_safe(workflow_output.get("analytics_results")),
        "risk": make_json_safe(workflow_output.get("risk_results")),
        "decision": make_json_safe(workflow_output.get("decision_results")),
        "final_report": make_json_safe(workflow_output.get("final_report")),
    }

    # Persist in analysis history
    analysis_id, created_at = save_analysis_history(
        user_id=user_id,
        dataset_id=dataset_id,
        analysis_type="multi_agent_workflow",
        input_summary={
            "dataset_id": dataset_id,
            "filename": owned_dataset["original_filename"],
            "user_query": data.user_query or "",
        },
        result=response_payload,
    )
    response_payload["analysis_id"] = analysis_id
    response_payload["created_at"] = created_at

    return response_payload