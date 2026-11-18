################################################################################
# @Project: ai-assistant
# @File Path: backend/tests/conftest.py
# @Description: Shared fixtures for the unit and integration test suites
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
################################################################################

################################################################################
# Import Libraries
################################################################################
# Standard Libraries
from __future__ import annotations

from collections.abc import Iterator
from typing import Final

# Third-Party Libraries
import pytest
from fastapi.testclient import TestClient

# Local Modules
from app.core.config import AppEnvironment, LlmProvider, Settings
from app.main import create_app

################################################################################
# Module Constants
################################################################################
TEST_OWNER_ID: Final[str] = "user-a"


################################################################################
# Module Functions
################################################################################
@pytest.fixture
def settings() -> Settings:
    """
    Build an isolated configuration for the application under test.

    The fake provider keeps the suite offline, and a small turn limit keeps
    the limit test short.

    :return: Settings pinned to the fake provider and plain text logs.
    """
    return Settings(
        app_env=AppEnvironment.TEST,
        llm_provider=LlmProvider.FAKE,
        log_json=False,
        chat_max_turns=3,
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    """
    Provide a client bound to a freshly assembled application.

    :param settings: Isolated configuration for the app under test.
    :return: Context managed client disposed after the test.
    """
    application = create_app(settings)
    with TestClient(
        application,
        headers={"X-User-Id": TEST_OWNER_ID},
    ) as test_client:
        yield test_client
