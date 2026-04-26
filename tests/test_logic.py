from __future__ import annotations

import pytest
from pytest_mock import MockerFixture

from podinfo.logic import PodInfo, safe_css_background

from tests.conftest import mock_getenv


@pytest.fixture
def pod() -> PodInfo:
    return PodInfo()


def test_safe_css_background_named_and_hex() -> None:
    assert safe_css_background("teal") == "teal"
    assert safe_css_background("#aabbcc") == "#aabbcc"


def test_safe_css_invalid_uses_theme_env(
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "podinfo.logic.os.getenv",
        side_effect=mock_getenv({"THEME_COLOR": "navy"}),
    )
    assert safe_css_background("not a color") == "navy"


def test_safe_css_invalid_defaults_to_blue(
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "podinfo.logic.os.getenv",
        side_effect=mock_getenv(env_is_empty=True),
    )
    assert safe_css_background("not a color") == "blue"


def test_safe_css_invalid_theme_falls_back_to_blue(
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "podinfo.logic.os.getenv",
        side_effect=mock_getenv({"THEME_COLOR": "not a color"}),
    )
    assert safe_css_background("still not a color") == "blue"


def test_get_version(
    mocker: MockerFixture, pod: PodInfo
) -> None:
    mocker.patch(
        "podinfo.logic.os.getenv",
        side_effect=mock_getenv(
            {"APP_VERSION": "9.9.9", "GIT_SHA": "a1b2c3d4"},
        ),
    )
    assert pod.get_version() == {
        "version": "9.9.9",
        "git_sha": "a1b2c3d4",
    }


def test_get_info(mocker: MockerFixture, pod: PodInfo) -> None:
    mocker.patch(
        "podinfo.logic.os.getenv",
        side_effect=mock_getenv(
            {"APP_ENV": "staging", "THEME_COLOR": "green"},
        ),
    )
    mocker.patch(
        "podinfo.logic.socket.gethostname",
        return_value="test-host",
    )
    mocker.patch(
        "podinfo.logic.platform.platform",
        return_value="TestOS-1.0",
    )
    assert pod.get_info() == {
        "hostname": "test-host",
        "platform": "TestOS-1.0",
        "environment": "staging",
        "theme_color": "green",
    }


def test_get_dashboard_html_keys(
    mocker: MockerFixture, pod: PodInfo
) -> None:
    mocker.patch(
        "podinfo.logic.os.getenv",
        side_effect=mock_getenv(env_is_empty=True),
    )
    mocker.patch(
        "podinfo.logic.socket.gethostname", return_value="h1"
    )
    ctx = pod.get_dashboard_html()
    assert set(ctx.keys()) == {
        "hostname",
        "version",
        "git_sha",
        "environment",
        "theme_color",
    }
    assert ctx["hostname"] == "h1"
    assert ctx["environment"] == "dev"
    assert ctx["theme_color"] == "blue"


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (
            "ping",
            {
                "message": "ping",
                "timestamp": "2026-01-01T10:11:12Z",
            },
        ),
        (
            "",
            {
                "message": "",
                "timestamp": "2026-01-01T10:11:12Z",
            },
        ),
    ],
    ids=["non_empty_message", "empty_message"],
)
def test_echo_message(
    mocker: MockerFixture,
    pod: PodInfo,
    message: str,
    expected: dict[str, str],
) -> None:
    mock_now = mocker.Mock()
    mock_now.isoformat.return_value = "2026-01-01T10:11:12+00:00"
    mock_datetime = mocker.patch("podinfo.logic.datetime")
    mock_datetime.now.return_value = mock_now

    out = pod.echo_message(message)
    assert out == expected
