"""Shared pytest fixtures and import setup for the offline test suite.

These tests never touch the network. They import the single-file ``lol_monitor``
module and drive it with test doubles that stand in for the Riot API.
"""

import os
import sys
import time

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
elif sys.path.index(_PROJECT_ROOT) != 0:
    sys.path.remove(_PROJECT_ROOT)
    sys.path.insert(0, _PROJECT_ROOT)

import pytest

import lol_monitor as lm


# Fails fast when pytest imports an installed module instead of the working tree
def _assert_in_repo_module():
    resolved = os.path.abspath(lm.__file__)
    expected = os.path.join(_PROJECT_ROOT, "lol_monitor.py")
    assert resolved == expected, f"Tests imported the wrong lol_monitor module\n  imported: {resolved}\n  expected: {expected}"


_assert_in_repo_module()


# Raised by the test doubles to break out of the tool's endless monitoring loop
class LoopFinished(BaseException):
    pass


# Marks a queue of scripted responses, so an endpoint that legitimately returns a list is not mistaken for one
class Replies(list):
    pass


# Advances only when the code under test sleeps, so a monitoring run is deterministic and instant
class FakeClock:
    def __init__(self, start=1767226800):
        self.now = float(start)
        self.slept = []

    # Returns the current fake wall clock value
    def time(self):
        return self.now

    # Records a sleep and moves the fake clock forward by the same amount
    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += float(seconds)

    # Moves the fake clock forward without recording a sleep
    def advance(self, seconds):
        self.now += float(seconds)


# Replays scripted Riot API responses and records how each endpoint was called
class FakeRiotAPIClient:
    responses: dict = {}
    calls: list = []

    def __init__(self, default_headers=None):
        self.default_headers = default_headers or {}
        FakeRiotAPIClient.calls.append({"endpoint": "__init__", "headers": self.default_headers})

    # Enters the async context the tool wraps every request in
    async def __aenter__(self):
        return self

    # Leaves the async context without swallowing anything
    async def __aexit__(self, exc_type, exc, traceback):
        return False

    # Returns a coroutine function that replays whatever was scripted for the requested endpoint
    def __getattr__(self, endpoint):
        if endpoint.startswith("_"):
            raise AttributeError(endpoint)

        # Records one request and returns or raises the scripted response
        async def call(**kwargs):
            FakeRiotAPIClient.calls.append({"endpoint": endpoint, **kwargs})
            if endpoint not in FakeRiotAPIClient.responses:
                raise LoopFinished
            scripted = FakeRiotAPIClient.responses[endpoint]
            if isinstance(scripted, Replies):
                if not scripted:
                    raise LoopFinished
                scripted = scripted.pop(0)
            if isinstance(scripted, BaseException):
                raise scripted
            if callable(scripted):
                return scripted(**kwargs)
            return scripted

        return call


# Scripts the Riot API responses and exposes the requests the tool made
class RiotApiDouble:
    def __init__(self):
        FakeRiotAPIClient.responses = {}
        FakeRiotAPIClient.calls = []
        self.responses = FakeRiotAPIClient.responses
        self.calls = FakeRiotAPIClient.calls
        self.client_class = FakeRiotAPIClient

    # Scripts one endpoint with a value, an exception, a callable or a Replies queue of any of those
    def script(self, endpoint, response):
        FakeRiotAPIClient.responses[endpoint] = response

    # Returns every recorded request to one endpoint
    def requests_to(self, endpoint):
        return [call for call in FakeRiotAPIClient.calls if call["endpoint"] == endpoint]


# Exposes the imported module to every test
@pytest.fixture
def lm_module():
    return lm


@pytest.fixture(autouse=True)
# Pins the process timezone so rendered timestamps do not depend on the machine running the suite
def utc_timezone(monkeypatch):
    monkeypatch.setenv("TZ", "UTC")
    if hasattr(time, "tzset"):
        time.tzset()
    yield
    monkeypatch.undo()
    if hasattr(time, "tzset"):
        time.tzset()


# Resets the module globals the offline helpers read so every test starts from the same baseline
@pytest.fixture(autouse=True)
def deterministic_globals(monkeypatch):
    monkeypatch.setattr(lm, "ASCII_LOG_SEPARATORS", "Auto", raising=False)
    monkeypatch.setattr(lm, "HORIZONTAL_LINE", 20, raising=False)
    monkeypatch.setattr(lm, "STATUS_NOTIFICATION", False, raising=False)
    monkeypatch.setattr(lm, "ERROR_NOTIFICATION", False, raising=False)
    monkeypatch.setattr(lm, "LOL_CHECK_INTERVAL", 150, raising=False)
    monkeypatch.setattr(lm, "LOL_ACTIVE_CHECK_INTERVAL", 45, raising=False)
    monkeypatch.setattr(lm, "LOL_ACTIVE_CHECK_SIGNAL_VALUE", 30, raising=False)
    monkeypatch.setattr(lm, "LIVENESS_CHECK_INTERVAL", 43200, raising=False)
    monkeypatch.setattr(lm, "LIVENESS_CHECK_COUNTER", 288, raising=False)
    monkeypatch.setattr(lm, "INCLUDE_FORBIDDEN_MATCHES", False, raising=False)
    monkeypatch.setattr(lm, "RIOT_API_KEY", "riot-api-key-test-value", raising=False)
    monkeypatch.setattr(lm, "SMTP_HOST", "smtp.example.test", raising=False)
    monkeypatch.setattr(lm, "SMTP_PORT", 587, raising=False)
    monkeypatch.setattr(lm, "SMTP_USER", "monitor@example.test", raising=False)
    monkeypatch.setattr(lm, "SMTP_PASSWORD", "not-a-real-password", raising=False)
    monkeypatch.setattr(lm, "SMTP_SSL", True, raising=False)
    monkeypatch.setattr(lm, "SENDER_EMAIL", "monitor@example.test", raising=False)
    monkeypatch.setattr(lm, "RECEIVER_EMAIL", "alerts@example.test", raising=False)
    monkeypatch.setattr(lm, "CSV_FILE", "", raising=False)
    monkeypatch.setattr(lm, "DOTENV_FILE", "", raising=False)
    monkeypatch.setattr(lm, "DISABLE_LOGGING", True, raising=False)
    monkeypatch.setattr(lm, "CLEAR_SCREEN", False, raising=False)
    # Champion names come from Data Dragon over the network, so start from a known cache in every test
    monkeypatch.setattr(lm, "_champion_id_to_name_cache", {}, raising=False)
    yield


# Collects every email the code under test tries to send instead of contacting an SMTP server
@pytest.fixture
def sent_emails(monkeypatch):
    delivered = []

    # Records one notification and reports success
    def fake_send_email(subject, body, body_html, use_ssl, smtp_timeout=15):
        delivered.append({"subject": subject, "body": body, "body_html": body_html, "use_ssl": use_ssl})
        return 0

    monkeypatch.setattr(lm, "send_email", fake_send_email)
    return delivered


# Replaces wall clock reads and sleeps inside the module with a controllable fake clock
@pytest.fixture
def fake_clock(monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(lm.time, "time", clock.time)
    monkeypatch.setattr(lm.time, "sleep", clock.sleep)
    return clock


# Installs the Riot API double and returns the controller that scripts its responses
@pytest.fixture
def riot_api(monkeypatch):
    double = RiotApiDouble()
    monkeypatch.setattr(lm, "RiotAPIClient", FakeRiotAPIClient)
    return double
