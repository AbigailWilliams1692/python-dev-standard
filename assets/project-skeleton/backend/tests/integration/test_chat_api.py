################################################################################
# @Project: ai-assistant
# @File Path: backend/tests/integration/test_chat_api.py
# @Description: Integration tests exercising the chat endpoints over HTTP
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

# Third-Party Libraries
from fastapi.testclient import TestClient

# Local Modules
from app.core.config import AppEnvironment, LlmProvider, Settings
from app.main import create_app

################################################################################
# Module Constants
################################################################################
SESSION_PATH: str = "/api/v1/chat/sessions"
OTHER_OWNER_ID: str = "user-b"


################################################################################
# Module Functions
################################################################################
def _create_session(client: TestClient) -> str:
    """
    Create one session and return its identifier.

    :param client: Client bound to the application under test.
    :return: Identifier of the created session.
    """
    response = client.post(SESSION_PATH, json={"title": "First chat"})
    assert response.status_code == 201
    session_id: str = response.json()["data"]["session_id"]
    return session_id


def test_health_reports_ok(client: TestClient) -> None:
    """
    The liveness probe must stay dependency free.

    :param client: Client bound to the application under test.
    :return: ``None``, the assertion raises on failure.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_session_returns_envelope(client: TestClient) -> None:
    """
    A created session comes back inside the shared envelope.

    :param client: Client bound to the application under test.
    :return: ``None``, the assertions raise on failure.
    """
    response = client.post(SESSION_PATH, json={"title": "  First chat  "})
    body = response.json()

    assert response.status_code == 201
    assert body["code"] == 0
    assert body["data"]["title"] == "First chat"
    assert body["data"]["messages"] == []
    assert body["trace_id"]


def test_send_message_returns_two_turns(client: TestClient) -> None:
    """
    One send returns the stored user turn and the generated reply.

    :param client: Client bound to the application under test.
    :return: ``None``, the assertions raise on failure.
    """
    session_id = _create_session(client)
    response = client.post(
        f"{SESSION_PATH}/{session_id}/messages",
        json={"content": "hello world"},
    )
    messages = response.json()["data"]["messages"]

    assert response.status_code == 200
    assert [item["role"] for item in messages] == ["user", "assistant"]
    assert messages[1]["content"] == "Echo: hello world"


def test_foreign_session_is_hidden(client: TestClient) -> None:
    """
    Another caller must receive the same answer as for a missing session.

    :param client: Client bound to the application under test.
    :return: ``None``, the assertions raise on failure.
    """
    session_id = _create_session(client)
    response = client.get(
        f"{SESSION_PATH}/{session_id}",
        headers={"X-User-Id": OTHER_OWNER_ID},
    )

    assert response.status_code == 404
    assert response.json()["code"] == 40401


def test_blank_title_is_rejected(client: TestClient) -> None:
    """
    Validation failures are reported with a located message.

    :param client: Client bound to the application under test.
    :return: ``None``, the assertions raise on failure.
    """
    response = client.post(SESSION_PATH, json={"title": "   "})

    assert response.status_code == 400
    assert "title" in response.json()["message"]


def test_missing_identity_is_rejected(settings: Settings) -> None:
    """
    Outside development a request without identity must not pass.

    :param settings: Isolated configuration for the app under test.
    :return: ``None``, the assertion raises on failure.
    """
    with TestClient(create_app(settings)) as anonymous:
        response = anonymous.get(SESSION_PATH)

    assert response.status_code == 401
    assert response.json()["code"] == 40101


def test_turn_limit_returns_conflict() -> None:
    """
    The configured turn limit surfaces as a conflict, not a server error.

    :return: ``None``, the assertions raise on failure.
    """
    limited = Settings(
        app_env=AppEnvironment.TEST,
        llm_provider=LlmProvider.FAKE,
        log_json=False,
        chat_max_turns=1,
    )
    with TestClient(create_app(limited), headers={"X-User-Id": "user-a"}) as client:
        session_id = _create_session(client)
        first = client.post(
            f"{SESSION_PATH}/{session_id}/messages",
            json={"content": "hello"},
        )
        second = client.post(
            f"{SESSION_PATH}/{session_id}/messages",
            json={"content": "again"},
        )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["code"] == 40901
