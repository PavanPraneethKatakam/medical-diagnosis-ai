import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials
from starlette.requests import Request

from api.models import ChatRequest, PredictRequest, RefineRequest, UploadDocRequest
from api.security import (
    _rate_limit_storage,
    check_rate_limit,
    get_current_username,
    validate_file_upload,
)
from database.db_utils import (
    execute_many,
    execute_query,
    execute_write,
    get_db_connection,
    transaction,
)


@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, qty INTEGER)")
    conn.commit()
    conn.close()
    return str(db_path)


class TestApiModels:
    def test_predict_request_strips_empty_comment(self):
        request = PredictRequest(patient_id=1, clinician_comment="   ")
        assert request.clinician_comment is None

    def test_refine_request_rejects_missing_feedback_keys(self):
        with pytest.raises(ValueError):
            RefineRequest(
                patient_id=1,
                feedback={"action": "add_edge", "from": "I10", "to": "I50.9"},
            )

    def test_refine_request_rejects_invalid_action(self):
        with pytest.raises(ValueError):
            RefineRequest(
                patient_id=1,
                feedback={
                    "action": "unknown",
                    "from": "I10",
                    "to": "I50.9",
                    "reason": "invalid",
                },
            )

    def test_chat_request_trims_message(self):
        request = ChatRequest(patient_id=1, message="  monitor edema  ")
        assert request.message == "monitor edema"

    def test_chat_request_rejects_blank_message(self):
        with pytest.raises(ValueError):
            ChatRequest(patient_id=1, message="   ")

    def test_upload_doc_request_normalizes_disease_code(self):
        request = UploadDocRequest(disease_code=" n18.4 ")
        assert request.disease_code == "N18.4"

    def test_upload_doc_request_blank_disease_code_to_none(self):
        request = UploadDocRequest(disease_code="   ")
        assert request.disease_code is None


class TestSecurityUtils:
    def setup_method(self):
        _rate_limit_storage.clear()

    def test_get_current_username_success(self, monkeypatch):
        monkeypatch.setenv("AUTH_USERNAME", "doctor")
        monkeypatch.setenv("AUTH_PASSWORD", "secret")

        credentials = HTTPBasicCredentials(username="doctor", password="secret")
        assert get_current_username(credentials) == "doctor"

    def test_get_current_username_unauthorized(self, monkeypatch):
        monkeypatch.setenv("AUTH_USERNAME", "doctor")
        monkeypatch.setenv("AUTH_PASSWORD", "secret")

        credentials = HTTPBasicCredentials(username="doctor", password="wrong")
        with pytest.raises(HTTPException) as exc:
            get_current_username(credentials)
        assert exc.value.status_code == 401

    def _request_for_ip(self, ip="127.0.0.1"):
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/agents/predict",
            "headers": [],
            "client": (ip, 12345),
        }
        return Request(scope)

    def test_check_rate_limit_allows_within_limit(self):
        request = self._request_for_ip()
        check_rate_limit(request, max_requests=2, window_seconds=60)
        check_rate_limit(request, max_requests=2, window_seconds=60)
        assert len(_rate_limit_storage["127.0.0.1"]) == 2

    def test_check_rate_limit_blocks_excess(self):
        request = self._request_for_ip()
        check_rate_limit(request, max_requests=1, window_seconds=60)
        with pytest.raises(HTTPException) as exc:
            check_rate_limit(request, max_requests=1, window_seconds=60)
        assert exc.value.status_code == 429

    def test_check_rate_limit_cleans_old_entries(self):
        request = self._request_for_ip("10.0.0.2")
        _rate_limit_storage["10.0.0.2"] = [datetime.now() - timedelta(seconds=120)]
        check_rate_limit(request, max_requests=1, window_seconds=60)
        assert len(_rate_limit_storage["10.0.0.2"]) == 1

    def test_validate_file_upload_accepts_and_sanitizes(self):
        filename = validate_file_upload("../unsafe report?.txt", file_size=1024)
        assert filename == "__unsafe_report_.txt"

    def test_validate_file_upload_rejects_large_file(self):
        with pytest.raises(HTTPException) as exc:
            validate_file_upload("x.txt", file_size=6 * 1024 * 1024, max_size_mb=5)
        assert exc.value.status_code == 413

    def test_validate_file_upload_rejects_invalid_extension(self):
        with pytest.raises(HTTPException) as exc:
            validate_file_upload("report.exe", file_size=100)
        assert exc.value.status_code == 400

    def test_validate_file_upload_generates_safe_name_for_hidden(self):
        filename = validate_file_upload(".txt", file_size=100)
        assert filename.startswith("upload_")
        assert filename.endswith(".txt")


class TestDbUtils:
    def test_get_db_connection_closes_connection(self, temp_db):
        with get_db_connection(temp_db) as conn:
            conn.execute("SELECT 1")
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

    def test_transaction_commits_on_success(self, temp_db):
        with get_db_connection(temp_db) as conn:
            with transaction(conn) as cursor:
                cursor.execute("INSERT INTO items (name, qty) VALUES (?, ?)", ("a", 1))

        row = execute_query(temp_db, "SELECT name, qty FROM items", fetch_one=True)
        assert row == ("a", 1)

    def test_transaction_rolls_back_on_error(self, temp_db):
        with get_db_connection(temp_db) as conn:
            with pytest.raises(sqlite3.OperationalError):
                with transaction(conn) as cursor:
                    cursor.execute("INSERT INTO items (name, qty) VALUES (?, ?)", ("a", 1))
                    cursor.execute("INSERT INTO unknown_table VALUES (1)")

        count = execute_query(temp_db, "SELECT COUNT(*) FROM items", fetch_one=True)[0]
        assert count == 0

    def test_execute_write_insert_and_update(self, temp_db):
        row_id = execute_write(temp_db, "INSERT INTO items (name, qty) VALUES (?, ?)", ("item", 2))
        assert isinstance(row_id, int)

        changed = execute_write(temp_db, "UPDATE items SET qty = ? WHERE id = ?", (3, row_id))
        assert changed == 1

    def test_execute_query_fetch_modes(self, temp_db):
        execute_many(
            temp_db,
            "INSERT INTO items (name, qty) VALUES (?, ?)",
            [("a", 1), ("b", 2)],
        )

        one = execute_query(temp_db, "SELECT name FROM items ORDER BY id", fetch_one=True)
        all_rows = execute_query(temp_db, "SELECT name FROM items ORDER BY id", fetch_all=True)
        none_result = execute_query(temp_db, "SELECT name FROM items", fetch_all=False)

        assert one == ("a",)
        assert all_rows == [("a",), ("b",)]
        assert none_result is None

    def test_execute_many_returns_rowcount(self, temp_db):
        count = execute_many(
            temp_db,
            "INSERT INTO items (name, qty) VALUES (?, ?)",
            [("x", 1), ("y", 2), ("z", 3)],
        )
        assert count == 3
