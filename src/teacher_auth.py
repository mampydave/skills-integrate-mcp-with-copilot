import base64
import hashlib
import hmac
import json
import os
import secrets
import tempfile
import time
from pathlib import Path


DEFAULT_TEACHERS_FILE = Path(__file__).with_name("teachers.json")
PASSWORD_ITERATIONS = 600_000
SESSION_MAX_AGE = 60 * 60


def normalize_username(username: str) -> str:
    return username.strip().lower()


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Teacher passwords must be at least 12 characters")

    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return "$".join(
        (
            "pbkdf2_sha256",
            str(PASSWORD_ITERATIONS),
            base64.urlsafe_b64encode(salt).decode("ascii").rstrip("="),
            base64.urlsafe_b64encode(digest).decode("ascii").rstrip("="),
        )
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        scheme, iterations_text, salt_text, digest_text = encoded_hash.split("$", 3)
        iterations = int(iterations_text)
        if scheme != "pbkdf2_sha256" or not 100_000 <= iterations <= 2_000_000:
            return False
        salt = _decode_base64(salt_text)
        expected = _decode_base64(digest_text)
    except (AttributeError, TypeError, ValueError):
        return False

    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def create_session_token(username: str, secret: str, now: int | None = None) -> str:
    issued_at = int(time.time()) if now is None else now
    payload = base64.urlsafe_b64encode(
        json.dumps([normalize_username(username), issued_at]).encode("utf-8")
    ).decode("ascii").rstrip("=")
    signature = hmac.new(secret.encode("utf-8"), payload.encode("ascii"), hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return f"{payload}.{encoded_signature}"


def verify_session_token(token: str | None, secret: str, now: int | None = None) -> str | None:
    if not token:
        return None
    try:
        payload, encoded_signature = token.split(".", 1)
        signature = _decode_base64(encoded_signature)
        expected = hmac.new(secret.encode("utf-8"), payload.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            return None
        session_data = json.loads(_decode_base64(payload))
        username, issued_at = session_data
        current_time = int(time.time()) if now is None else now
        if not isinstance(username, str) or not username or not isinstance(issued_at, int):
            return None
        if issued_at > current_time or current_time - issued_at > SESSION_MAX_AGE:
            return None
        return username
    except (AttributeError, TypeError, ValueError, json.JSONDecodeError):
        return None


def load_teachers(path: Path = DEFAULT_TEACHERS_FILE) -> dict[str, str]:
    try:
        with path.open(encoding="utf-8") as teachers_file:
            data = json.load(teachers_file)
    except FileNotFoundError:
        return {}

    if not isinstance(data, dict) or not isinstance(data.get("teachers"), list):
        raise ValueError("Teacher file must contain a teachers list")

    teachers: dict[str, str] = {}
    for record in data["teachers"]:
        if not isinstance(record, dict):
            raise ValueError("Teacher records must be objects")
        username = record.get("username")
        password_hash = record.get("password_hash")
        if not isinstance(username, str) or not isinstance(password_hash, str):
            raise ValueError("Teacher records need a username and password_hash")
        teachers[normalize_username(username)] = password_hash
    return teachers


def save_teacher(username: str, password: str, path: Path = DEFAULT_TEACHERS_FILE) -> None:
    normalized = normalize_username(username)
    if not normalized:
        raise ValueError("Username cannot be empty")

    teachers = load_teachers(path)
    teachers[normalized] = hash_password(password)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "teachers": [
            {"username": teacher, "password_hash": password_hash}
            for teacher, password_hash in sorted(teachers.items())
        ]
    }

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as temp_file:
            temp_path = Path(temp_file.name)
            json.dump(payload, temp_file, indent=2)
            temp_file.write("\n")
        temp_path.chmod(0o600)
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def _decode_base64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))