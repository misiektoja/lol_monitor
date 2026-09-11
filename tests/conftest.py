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


# Stands in for the session pulsefire builds on entry, so the TLS replacement has something real to replace
class FakeClientSession:
    def __init__(self, connector=None):
        self.connector = connector
        self.closed = False

    # Closes the session the way aiohttp does
    async def close(self):
        self.closed = True


# Replays scripted Riot API responses and records how each endpoint was called
class FakeRiotAPIClient:
    responses: dict = {}
    calls: list = []

    def __init__(self, default_headers=None):
        self.default_headers = default_headers or {}
        self.session = None
        FakeRiotAPIClient.calls.append({"endpoint": "__init__", "headers": self.default_headers})

    # Enters the async context the tool wraps every request in, building the session pulsefire builds here
    async def __aenter__(self):
        self.session = FakeClientSession()
        return self

    # Leaves the async context, closing whatever session the client ended up holding
    async def __aexit__(self, exc_type, exc, traceback):
        if self.session is not None:
            await self.session.close()
            self.session = None
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


# Stands in for smtplib.SMTP and records everything the tool asks it to do
class FakeSMTP:
    last = None

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.login_args = None
        self.sent = None
        self.quit_called = False
        FakeSMTP.last = self

    # Records that the connection was upgraded to TLS
    def starttls(self, context=None):
        self.started_tls = True
        self.tls_context = context

    # Records the credentials the tool authenticated with
    def login(self, user, password):
        self.login_args = (user, password)

    # Records the delivered message
    def sendmail(self, sender, receiver, message):
        self.sent = {"sender": sender, "receiver": receiver, "message": message}

    # Records that the session was closed
    def quit(self):
        self.quit_called = True


# Refuses an SMTP connection a test never asked for, so no run can reach a real mail server
class RefusedSMTP:
    def __init__(self, host, port, timeout=None):
        raise AssertionError(f"this test opened an SMTP connection to {host}:{port} without the smtp_double fixture")


@pytest.fixture(autouse=True)
# Keeps every test offline on the SMTP side, whether or not it expects the code under test to connect
def no_unexpected_smtp(monkeypatch):
    monkeypatch.setattr(lm.smtplib, "SMTP", RefusedSMTP)


# Records every webhook request and replays scripted responses instead of contacting a real service
class FakeWebhookSession:
    def __init__(self, responses=None, icons=None):
        self.responses = list(responses or [])
        self.icons = list(icons or [])
        self.posts = []
        self.gets = []

    # Records one delivery and returns or raises the next scripted response
    def post(self, url, **kwargs):
        self.posts.append({"url": url, **kwargs})
        if not self.responses:
            raise AssertionError(f"this test posted {len(self.posts)} webhooks but scripted fewer responses")
        scripted = self.responses.pop(0)
        if isinstance(scripted, BaseException):
            raise scripted
        return scripted

    # Records one champion icon download and returns or raises the next scripted image response
    def get(self, url, **kwargs):
        self.gets.append({"url": url, **kwargs})
        if not self.icons:
            raise AssertionError(f"this test fetched {len(self.gets)} images but scripted fewer image responses")
        scripted = self.icons.pop(0)
        if isinstance(scripted, BaseException):
            raise scripted
        return scripted


# Stands in for one champion icon response, carrying only what the download path reads
class FakeImageResponse:
    def __init__(self, content=b"", headers=None, status_code=200, error=None):
        self.content = content
        self.headers = {"Content-Type": "image/png", "Content-Length": str(len(content))} if headers is None else headers
        self.status_code = status_code
        self.error = error

    # Raises the scripted failure the way requests does for an error status
    def raise_for_status(self):
        if self.error is not None:
            raise self.error

    # Yields the image in one chunk, which is all a small icon needs
    def iter_content(self, chunk_size=1):
        yield self.content

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


# Stands in for one webhook HTTP response, carrying only what the delivery path reads
class FakeWebhookResponse:
    def __init__(self, status_code=204, headers=None, payload=None):
        self.status_code = status_code
        self.headers = headers or {}
        self._payload = payload

    # Returns the scripted JSON body, or raises the way requests does when there is none
    def json(self):
        if self._payload is None:
            raise ValueError("no JSON body")
        return self._payload


# Refuses a webhook delivery a test never asked for, so no run can reach a real webhook service
class RefusedWebhookSession:
    # Fails the test rather than letting an unscripted delivery leave the machine
    def post(self, url, **kwargs):
        raise AssertionError(f"this test posted a webhook to {url} without the webhook_session fixture")

    # The same for the champion icon download, which shares the webhook session
    def get(self, url, **kwargs):
        raise AssertionError(f"this test fetched {url} without the webhook_session fixture")


@pytest.fixture(autouse=True)
# Keeps every test offline on the webhook side, whether or not it expects the code under test to deliver
def no_unexpected_webhook(monkeypatch):
    monkeypatch.setattr(lm, "WEBHOOK_SESSION", RefusedWebhookSession(), raising=False)


@pytest.fixture(autouse=True)
# Clears the marked player and the icons one test downloaded, since both outlive the call that set them
def no_leaked_notification_state(monkeypatch):
    monkeypatch.setattr(lm, "MONITORED_PLAYER_NAME", "", raising=False)
    monkeypatch.setattr(lm, "_champion_icon_cache", {}, raising=False)


@pytest.fixture
# Replaces the webhook session with the recording double, scripted through its responses list
def webhook_session(monkeypatch):
    session = FakeWebhookSession()
    monkeypatch.setattr(lm, "WEBHOOK_SESSION", session, raising=False)
    return session


@pytest.fixture
# Replaces the SMTP client with the recording double
def smtp_double(monkeypatch):
    FakeSMTP.last = None
    monkeypatch.setattr(lm.smtplib, "SMTP", FakeSMTP)
    return FakeSMTP


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


# Keeps a secret exported by the developer, or left in os.environ by an earlier test, out of the run under test
@pytest.fixture(autouse=True)
def isolated_secret_environment():
    saved = {secret: os.environ.pop(secret, None) for secret in lm.SECRET_KEYS}
    yield
    for secret, value in saved.items():
        os.environ.pop(secret, None)
        if value is not None:
            os.environ[secret] = value


# Resets the module globals the offline helpers read so every test starts from the same baseline
@pytest.fixture(autouse=True)
def deterministic_globals(monkeypatch):
    monkeypatch.setattr(lm, "ASCII_LOG_SEPARATORS", "Auto", raising=False)
    monkeypatch.setattr(lm, "HORIZONTAL_LINE", 20, raising=False)
    monkeypatch.setattr(lm, "TRUNCATE_CHARS", 0, raising=False)
    monkeypatch.setattr(lm, "STATUS_NOTIFICATION", False, raising=False)
    monkeypatch.setattr(lm, "ERROR_NOTIFICATION", False, raising=False)
    monkeypatch.setattr(lm, "EMAIL_IMAGES", False, raising=False)
    monkeypatch.setattr(lm, "NTFY_IMAGES", False, raising=False)
    monkeypatch.setattr(lm, "WEBHOOK_ENABLED", False, raising=False)
    monkeypatch.setattr(lm, "WEBHOOK_PROVIDER", "discord", raising=False)
    monkeypatch.setattr(lm, "WEBHOOK_URL", "", raising=False)
    monkeypatch.setattr(lm, "WEBHOOK_USERNAME", "", raising=False)
    monkeypatch.setattr(lm, "WEBHOOK_AVATAR_URL", "", raising=False)
    monkeypatch.setattr(lm, "WEBHOOK_STATUS_NOTIFICATION", False, raising=False)
    monkeypatch.setattr(lm, "WEBHOOK_ERROR_NOTIFICATION", False, raising=False)
    monkeypatch.setattr(lm, "WEBHOOK_HEADERS", {}, raising=False)
    monkeypatch.setattr(lm, "WEBHOOK_TRANSFORMS", [], raising=False)
    monkeypatch.setattr(lm, "NTFY_ACCESS_TOKEN", "", raising=False)
    monkeypatch.setattr(lm, "LOL_CHECK_INTERVAL", 150, raising=False)
    monkeypatch.setattr(lm, "LOL_ACTIVE_CHECK_INTERVAL", 45, raising=False)
    monkeypatch.setattr(lm, "LOL_ACTIVE_CHECK_SIGNAL_VALUE", 30, raising=False)
    monkeypatch.setattr(lm, "LIVENESS_CHECK_INTERVAL", 43200, raising=False)
    monkeypatch.setattr(lm, "LIVENESS_REMINDER_SECONDS", 43200, raising=False)
    monkeypatch.setattr(lm, "INCLUDE_FORBIDDEN_MATCHES", False, raising=False)
    monkeypatch.setattr(lm, "RIOT_API_KEY", "riot-api-key-test-value", raising=False)
    monkeypatch.setattr(lm, "RIOT_ID", "", raising=False)
    monkeypatch.setattr(lm, "REGION", "", raising=False)
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
    monkeypatch.setattr(lm, "VERBOSE_MODE", False, raising=False)
    monkeypatch.setattr(lm, "DEBUG_MODE", False, raising=False)
    # Champion names come from Data Dragon over the network, so start from a known cache in every test
    monkeypatch.setattr(lm, "_champion_id_to_name_cache", {}, raising=False)
    yield


# Collects every email the code under test tries to send instead of contacting an SMTP server
@pytest.fixture
def sent_emails(monkeypatch):
    delivered = []

    # Records one notification and reports success
    def fake_send_email(subject, body, body_html, use_ssl, smtp_timeout=15, image_bytes=None, image_subtype="png", image_name=lm.EMAIL_CHAMPION_ICON_CONTENT_ID, report_delivery=True):
        delivered.append({"subject": subject, "body": body, "body_html": body_html, "use_ssl": use_ssl, "image_bytes": image_bytes, "image_subtype": image_subtype})
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
