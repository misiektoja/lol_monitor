"""Tests that VERIFY_SSL reaches every outbound connection the tool makes."""

import ast
import asyncio
import ssl
from pathlib import Path
from types import SimpleNamespace

import pytest

import lol_monitor as monitor

MODULE_SOURCE = Path(monitor.__file__).read_text(encoding="utf-8")


# Returns every call in the module whose target is the named attribute or function
def calls_to(name):
    tree = ast.parse(MODULE_SOURCE)
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = node.func
        rendered = f"{target.value.id}.{target.attr}" if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) else getattr(target, "id", None)
        if rendered == name:
            found.append(node)
    return found


HTTP_METHODS = frozenset(("get", "post", "put", "patch", "delete", "head", "options", "request"))
# The expressions that carry the TLS decision, so a call passing anything else is a second opinion
VERIFY_ARGUMENTS = frozenset(("VERIFY_SSL",))
# A guard against the sweep silently matching nothing after a rename: the tool has 5 call sites today
MINIMUM_HTTP_CALL_SITES = 5


# Returns every name the module binds to a requests session, so a session added later is swept without editing this
def session_receivers():
    return {node.targets[0].id for node in ast.walk(ast.parse(MODULE_SOURCE)) if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Call) and ast.unparse(node.value.func).endswith("Session")}


# Returns every outbound HTTP call in the module as a line number paired with its keyword arguments
def http_call_sites():
    receivers = {"req", "requests"} | session_receivers()
    for node in ast.walk(ast.parse(MODULE_SOURCE)):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        receiver = node.func.value
        if node.func.attr in HTTP_METHODS and isinstance(receiver, ast.Name) and receiver.id in receivers:
            yield node.lineno, {keyword.arg: keyword.value for keyword in node.keywords}


# Records the arguments aiohttp is asked for instead of opening a real connection
class RecordingAiohttp(SimpleNamespace):
    def __init__(self):
        self.connectors = []
        self.sessions = []
        super().__init__()

    # Stands in for aiohttp.TCPConnector, keeping the TLS context it was given
    def TCPConnector(self, ssl=None):
        connector = SimpleNamespace(ssl=ssl)
        self.connectors.append(connector)
        return connector

    # Stands in for aiohttp.ClientSession, keeping the connector it was built on
    def ClientSession(self, connector=None):
        from conftest import FakeClientSession

        session = FakeClientSession(connector=connector)
        self.sessions.append(session)
        return session


@pytest.fixture
# Replaces the aiohttp module the tool imported with a recorder, so no real socket is ever configured
def recording_aiohttp(lm_module, monkeypatch):
    recorder = RecordingAiohttp()
    monkeypatch.setattr(lm_module, "aiohttp", recorder)
    return recorder


# Verifies the shipped default verifies certificates, since the safe choice is the one a user gets without reading anything
def test_verification_is_on_by_default():
    assert monitor.VERIFY_SSL is True
    assert "VERIFY_SSL = True" in monitor.CONFIG_BLOCK


# Verifies the setting is one the config file can carry, so switching it off does not mean editing the source
def test_the_setting_can_be_set_from_a_config_file():
    parsed = monitor.parse_config_content("VERIFY_SSL = False\n", "lol_monitor.conf")

    assert parsed == {"VERIFY_SSL": False}


# Verifies the TLS context is built in exactly one place, so no connection can quietly keep verifying or stop
def test_the_tls_context_is_built_once():
    assert MODULE_SOURCE.count("ssl.create_default_context()") == 1
    assert len(calls_to("ssl.create_default_context")) == 1


# Verifies the default context checks the certificate and the hostname
def test_the_context_verifies_while_the_setting_is_on(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "VERIFY_SSL", True)

    context = lm_module.tls_context()

    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


# Verifies switching the setting off drops both checks, since a hostname check alone would still refuse the connection
def test_the_context_stops_verifying_while_the_setting_is_off(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "VERIFY_SSL", False)

    context = lm_module.tls_context()

    assert context.verify_mode == ssl.CERT_NONE
    assert context.check_hostname is False


# Verifies every plain HTTP request carries the setting rather than the library default. The shared session is
# swept too, since it is created without a verify default and would quietly keep verifying while the setting is off
def test_every_outbound_request_passes_the_setting():
    calls = list(http_call_sites())

    assert len(calls) >= MINIMUM_HTTP_CALL_SITES, f"the sweep found {len(calls)} HTTP calls, so it no longer matches how requests are made"
    missing = [line for line, keywords in calls if "verify" not in keywords or ast.unparse(keywords["verify"]) not in VERIFY_ARGUMENTS]
    assert not missing, f"lol_monitor.py lines {missing} make an HTTP call that does not pass the TLS setting"


# Verifies every outbound request carries a deadline, since a call without one hangs the monitoring loop indefinitely
def test_every_outbound_request_carries_a_deadline():
    # A call forwarding **kwargs takes its deadline from the helper that fills them in, which is not readable here
    missing = [line for line, keywords in http_call_sites() if "timeout" not in keywords and None not in keywords]

    assert not missing, f"lol_monitor.py lines {missing} make an HTTP call without a timeout"


# Verifies the connectivity check follows the setting, which is the first connection a run makes
@pytest.mark.parametrize("enabled", [True, False])
def test_the_connectivity_check_follows_the_setting(lm_module, monkeypatch, enabled):
    monkeypatch.setattr(lm_module, "VERIFY_SSL", enabled)
    seen = {}

    monkeypatch.setattr(lm_module.req, "get", lambda url, timeout=None, verify=True: seen.update(verify=verify) or object())

    assert lm_module.check_internet("https://riot.example.test", 5) is True
    assert seen["verify"] is enabled


# Verifies the champion name lookup follows the setting, since Data Dragon is a separate host from the API
def test_the_champion_lookup_follows_the_setting(lm_module, monkeypatch):
    monkeypatch.setattr(lm_module, "VERIFY_SSL", False)
    monkeypatch.setattr(lm_module, "_champion_id_to_name_cache", None)
    seen = []

    # Serves the version list and then the champion list, recording how each was requested
    def fake_get(url, timeout=None, verify=True):
        seen.append(verify)
        payload = ["15.19.1"] if url.endswith("versions.json") else {"data": {"Ahri": {"key": "103"}}}
        return SimpleNamespace(status_code=200, json=lambda: payload)

    monkeypatch.setattr(lm_module.req, "get", fake_get)

    assert lm_module.get_champion_name(103) == "Ahri"
    assert seen == [False, False]


# Verifies email delivery follows the same switch, so one setting is not silently two
@pytest.mark.parametrize("enabled,expected", [(True, ssl.CERT_REQUIRED), (False, ssl.CERT_NONE)])
def test_email_delivery_follows_the_setting(lm_module, monkeypatch, smtp_double, enabled, expected):
    monkeypatch.setattr(lm_module, "VERIFY_SSL", enabled)

    assert lm_module.send_email("subject", "body", "", True) == 0

    assert smtp_double.last.tls_context.verify_mode == expected


# Verifies the Riot API client is built in one place, since a second construction would bypass the TLS setting
def test_the_riot_client_is_constructed_once():
    constructions = calls_to("RiotAPIClient")

    assert len(constructions) == 1, "RiotAPIClient is constructed outside riot_api_client, which would skip the TLS setting"


# Verifies the client keeps the session pulsefire built while verification is on
def test_the_client_session_is_left_alone_while_the_setting_is_on(lm_module, monkeypatch, riot_api, recording_aiohttp):
    monkeypatch.setattr(lm_module, "VERIFY_SSL", True)

    # Reports the session the helper handed back
    async def enter():
        async with lm_module.riot_api_client() as client:
            return client.session

    session = asyncio.run(enter())

    assert recording_aiohttp.sessions == []
    assert session.connector is None


# Verifies the session is replaced with an unverified one while the setting is off, since pulsefire builds its own on entry
def test_the_client_session_is_replaced_while_the_setting_is_off(lm_module, monkeypatch, riot_api, recording_aiohttp):
    monkeypatch.setattr(lm_module, "VERIFY_SSL", False)
    closed = {}

    # Reports the session the helper handed back and whether the original was closed
    async def enter():
        async with lm_module.riot_api_client() as client:
            closed["original"] = client.session
            return client.session

    session = asyncio.run(enter())

    assert len(recording_aiohttp.sessions) == 1
    assert session is recording_aiohttp.sessions[0]
    assert session.connector.ssl.verify_mode == ssl.CERT_NONE


# Verifies the session pulsefire opened is closed when it is replaced, so switching the setting off does not leak a connection
def test_the_replaced_session_is_closed(lm_module, monkeypatch, riot_api, recording_aiohttp):
    monkeypatch.setattr(lm_module, "VERIFY_SSL", False)
    originals = []

    # Keeps the session pulsefire built before the helper swaps it out
    async def enter():
        async with lm_module.riot_api_client() as client:
            originals.append(client.session)
        return None

    from conftest import FakeRiotAPIClient

    real_aenter = FakeRiotAPIClient.__aenter__

    # Records the session the fake client opened before the helper replaces it
    async def recording_aenter(self):
        entered = await real_aenter(self)
        originals.append(entered.session)
        return entered

    monkeypatch.setattr(FakeRiotAPIClient, "__aenter__", recording_aenter)
    asyncio.run(enter())

    assert originals[0].closed is True


# Verifies a client that no longer exposes a session keeps verifying rather than failing the run
def test_a_moved_session_leaves_verification_on(lm_module, monkeypatch, riot_api, recording_aiohttp, capsys):
    monkeypatch.setattr(lm_module, "VERIFY_SSL", False)

    from conftest import FakeRiotAPIClient

    # Enters without ever exposing a session, the way a future pulsefire release might
    async def sessionless_aenter(self):
        self.session = None
        return self

    monkeypatch.setattr(FakeRiotAPIClient, "__aenter__", sessionless_aenter)

    # Reports that the helper still yielded a usable client
    async def enter():
        async with lm_module.riot_api_client() as client:
            return client

    assert asyncio.run(enter()) is not None
    assert "TLS verification stays on" in capsys.readouterr().out


# Verifies the repeated certificate warning is silenced only when verification is off
@pytest.mark.parametrize("enabled,expected", [(True, False), (False, True)])
def test_the_certificate_warning_is_silenced_only_when_off(lm_module, monkeypatch, enabled, expected):
    monkeypatch.setattr(lm_module, "VERIFY_SSL", enabled)
    disabled = []

    monkeypatch.setattr(lm_module.urllib3, "disable_warnings", lambda category: disabled.append(category))

    lm_module.apply_tls_verification_setting()

    assert bool(disabled) is expected


# Verifies the discovered configuration reaches private API key entry, which checks the key over the network before
# the normal configuration load and would otherwise probe the default region with certificate verification left on
def test_private_key_entry_applies_the_configured_settings(lm_module, tmp_path, monkeypatch):
    (tmp_path / "lol_monitor.conf").write_text('VERIFY_SSL = False\nREGION = "eun1"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    for name in ("VERIFY_SSL", "REGION"):
        monkeypatch.setattr(lm_module, name, getattr(lm_module, name))
    monkeypatch.setattr(lm_module, "VERIFY_SSL", True)
    observed = {}
    monkeypatch.setattr(lm_module, "run_set_riot_api_key", lambda **kwargs: observed.update(verify=lm_module.VERIFY_SSL, region=lm_module.REGION))
    monkeypatch.setattr(lm_module.sys, "argv", ["lol_monitor", "--set-riot-api-key"])

    with pytest.raises(SystemExit):
        lm_module.main()

    assert observed == {"verify": False, "region": "eun1"}
