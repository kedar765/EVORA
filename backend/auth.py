
import hashlib
import hmac
import os
import secrets
import sqlite3
import time
import uuid

from contextlib import contextmanager
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Request,
    Response,
)
from pydantic import BaseModel, Field


# Configuration

DB_PATH = Path(
    os.getenv(
        "EVORA_DB_PATH",
        str(Path(__file__).resolve().parent / "evora.db"),
    )
)

COOKIE_NAME = "evora_session"

COOKIE_SECURE = (
    os.getenv("EVORA_COOKIE_SECURE", "false").lower()
    == "true"
)

HASH_ITERATIONS = 600_000

SESSION_SECONDS = 12 * 60 * 60
REMEMBER_SECONDS = 30 * 24 * 60 * 60

# Login rate limiting
LOGIN_WINDOW_SECONDS = 15 * 60
MAX_EMAIL_IP_ATTEMPTS = 5
MAX_IP_ATTEMPTS = 30

# Signup rate limiting
SIGNUP_WINDOW_SECONDS = 15 * 60
MAX_SIGNUP_IP_ATTEMPTS = 5

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


# Database

@contextmanager
def database():
    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        DB_PATH,
        timeout=10,
    )
    connection.row_factory = sqlite3.Row

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database():
    with database() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                FOREIGN KEY (user_id)
                    REFERENCES users(id)
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS login_attempts (
                attempt_key TEXT PRIMARY KEY,
                attempt_count INTEGER NOT NULL,
                window_started_at INTEGER NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS signup_attempts (
                attempt_key TEXT PRIMARY KEY,
                attempt_count INTEGER NOT NULL,
                window_started_at INTEGER NOT NULL
            )
        """)


# Password Security

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        HASH_ITERATIONS,
    )

    return (
        f"pbkdf2_sha256${HASH_ITERATIONS}"
        f"${salt.hex()}${digest.hex()}"
    )


def verify_password(
    password: str,
    stored_hash: str,
) -> bool:
    try:
        algorithm, iterations, salt, digest = (
            stored_hash.split("$")
        )

        if algorithm != "pbkdf2_sha256":
            return False

        calculated = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt),
            int(iterations),
        )

        return hmac.compare_digest(
            calculated,
            bytes.fromhex(digest),
        )

    except (ValueError, TypeError):
        return False


# User Helpers

def public_user(user):
    return {
        "id": user["id"],
        "email": user["email"],
        "fullName": user["full_name"],
    }


def normalize_email(email: str) -> str:
    email = email.strip().lower()

    if (
        "@" not in email
        or "." not in email.rsplit("@", 1)[-1]
        or " " in email
    ):
        raise HTTPException(
            status_code=422,
            detail="Enter a valid email address.",
        )

    return email


# Request Models

class SignupRequest(BaseModel):
    fullName: str = Field(
        min_length=2,
        max_length=100,
    )
    email: str = Field(
        min_length=3,
        max_length=254,
    )
    password: str = Field(
        min_length=8,
        max_length=128,
    )


class LoginRequest(BaseModel):
    email: str
    password: str
    rememberMe: bool = False


# Login Rate Limiting

def rate_limit_keys(
    email: str,
    client_ip: str,
) -> tuple[str, str]:

    email_ip_key = hashlib.sha256(
        f"email-ip:{email}:{client_ip}".encode(
            "utf-8"
        )
    ).hexdigest()

    ip_key = hashlib.sha256(
        f"ip:{client_ip}".encode("utf-8")
    ).hexdigest()

    return email_ip_key, ip_key


def check_and_record_login_attempt(
    email: str,
    client_ip: str,
) -> None:
    now = int(time.time())

    pair_key, ip_key = rate_limit_keys(
        email,
        client_ip,
    )

    limits = (
        (pair_key, MAX_EMAIL_IP_ATTEMPTS),
        (ip_key, MAX_IP_ATTEMPTS),
    )

    with database() as connection:
        connection.execute("BEGIN IMMEDIATE")

        connection.execute(
            """
            DELETE FROM login_attempts
            WHERE window_started_at <= ?
            """,
            (now - LOGIN_WINDOW_SECONDS,),
        )

        for key, limit in limits:
            row = connection.execute(
                """
                SELECT attempt_count, window_started_at
                FROM login_attempts
                WHERE attempt_key = ?
                """,
                (key,),
            ).fetchone()

            if (
                row is not None
                and row["attempt_count"] >= limit
            ):
                retry_after = max(
                    1,
                    row["window_started_at"]
                    + LOGIN_WINDOW_SECONDS
                    - now,
                )

                raise HTTPException(
                    status_code=429,
                    detail=(
                        "Too many login attempts. "
                        "Please try again later."
                    ),
                    headers={
                        "Retry-After": str(retry_after)
                    },
                )

        for key, _ in limits:
            connection.execute(
                """
                INSERT INTO login_attempts (
                    attempt_key,
                    attempt_count,
                    window_started_at
                )
                VALUES (?, 1, ?)
                ON CONFLICT(attempt_key)
                DO UPDATE SET
                    attempt_count =
                        attempt_count + 1
                """,
                (key, now),
            )


def clear_successful_login_attempts(
    email: str,
    client_ip: str,
) -> None:
    pair_key, _ = rate_limit_keys(
        email,
        client_ip,
    )

    with database() as connection:
        connection.execute(
            """
            DELETE FROM login_attempts
            WHERE attempt_key = ?
            """,
            (pair_key,),
        )


# Signup Rate Limiting

def check_and_record_signup_attempt(
    client_ip: str,
) -> None:
    now = int(time.time())

    attempt_key = hashlib.sha256(
        f"signup-ip:{client_ip}".encode("utf-8")
    ).hexdigest()

    with database() as connection:
        # Prevent concurrent requests from
        # bypassing the signup counter.
        connection.execute("BEGIN IMMEDIATE")

        # Delete expired signup counters.
        connection.execute(
            """
            DELETE FROM signup_attempts
            WHERE window_started_at <= ?
            """,
            (now - SIGNUP_WINDOW_SECONDS,),
        )

        row = connection.execute(
            """
            SELECT attempt_count, window_started_at
            FROM signup_attempts
            WHERE attempt_key = ?
            """,
            (attempt_key,),
        ).fetchone()

        if (
            row is not None
            and row["attempt_count"]
            >= MAX_SIGNUP_IP_ATTEMPTS
        ):
            retry_after = max(
                1,
                row["window_started_at"]
                + SIGNUP_WINDOW_SECONDS
                - now,
            )

            raise HTTPException(
                status_code=429,
                detail=(
                    "Too many signup attempts. "
                    "Please try again later."
                ),
                headers={
                    "Retry-After": str(retry_after)
                },
            )

        connection.execute(
            """
            INSERT INTO signup_attempts (
                attempt_key,
                attempt_count,
                window_started_at
            )
            VALUES (?, 1, ?)
            ON CONFLICT(attempt_key)
            DO UPDATE SET
                attempt_count =
                    attempt_count + 1
            """,
            (attempt_key, now),
        )


# Session Management

def create_session(
    response: Response,
    user_id: str,
    remember_me: bool = False,
):
    token = secrets.token_urlsafe(32)

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    max_age = (
        REMEMBER_SECONDS
        if remember_me
        else SESSION_SECONDS
    )

    with database() as connection:
        connection.execute(
            """
            DELETE FROM sessions
            WHERE expires_at <= ?
            """,
            (int(time.time()),),
        )

        connection.execute(
            """
            INSERT INTO sessions (
                token_hash,
                user_id,
                expires_at
            )
            VALUES (?, ?, ?)
            """,
            (
                token_hash,
                user_id,
                int(time.time()) + max_age,
            ),
        )

    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=max_age,
        path="/",
    )


# Signup

@router.post(
    "/signup",
    status_code=201,
)
def signup(
    data: SignupRequest,
    response: Response,
    request: Request,
):
    email = normalize_email(data.email)
    full_name = data.fullName.strip()

    if len(full_name) < 2:
        raise HTTPException(
            status_code=422,
            detail=(
                "Name must contain "
                "at least 2 characters."
            ),
        )

    # Check signup rate limit before
    # creating a new user account.
    client_ip = (
        request.client.host
        if request.client
        else "unknown"
    )

    check_and_record_signup_attempt(client_ip)

    user_id = str(uuid.uuid4())

    try:
        with database() as connection:
            connection.execute(
                """
                INSERT INTO users (
                    id,
                    full_name,
                    email,
                    password_hash,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    full_name,
                    email,
                    hash_password(data.password),
                    int(time.time()),
                ),
            )

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail=(
                "Account already exists "
                "for this email."
            ),
        ) from None

    create_session(response, user_id)

    return {
        "success": True,
        "user": {
            "id": user_id,
            "email": email,
            "fullName": full_name,
        },
    }


# Login

@router.post("/login")
def login(
    data: LoginRequest,
    response: Response,
    request: Request,
):
    email = normalize_email(data.email)

    # Only use the connection IP.
    # Do not trust arbitrary X-Forwarded-For headers.
    client_ip = (
        request.client.host
        if request.client
        else "unknown"
    )

    check_and_record_login_attempt(
        email,
        client_ip,
    )

    with database() as connection:
        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

    if (
        user is None
        or not verify_password(
            data.password,
            user["password_hash"],
        )
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    clear_successful_login_attempts(
        email,
        client_ip,
    )

    create_session(
        response,
        user["id"],
        data.rememberMe,
    )

    return {
        "success": True,
        "user": public_user(user),
    }


# Current User Verification

def get_current_user(
    token: Annotated[
        str | None,
        Cookie(alias=COOKIE_NAME),
    ] = None,
):
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Login required.",
        )

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    with database() as connection:
        user = connection.execute(
            """
            SELECT
                users.id,
                users.email,
                users.full_name
            FROM sessions
            JOIN users
                ON users.id = sessions.user_id
            WHERE sessions.token_hash = ?
              AND sessions.expires_at > ?
            """,
            (
                token_hash,
                int(time.time()),
            ),
        ).fetchone()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Session expired or invalid.",
        )

    return public_user(user)


@router.get("/me")
def me(
    user: Annotated[
        dict,
        Depends(get_current_user),
    ],
):
    return {"user": user}


# Logout

@router.post("/logout")
def logout(
    response: Response,
    token: Annotated[
        str | None,
        Cookie(alias=COOKIE_NAME),
    ] = None,
):
    if token:
        token_hash = hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

        with database() as connection:
            connection.execute(
                """
                DELETE FROM sessions
                WHERE token_hash = ?
                """,
                (token_hash,),
            )

    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        samesite="lax",
        secure=COOKIE_SECURE,
        httponly=True,
    )

    return {"success": True}


initialize_database()
