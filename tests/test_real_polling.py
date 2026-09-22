"""Transport-level regression tests for primary Riot polling and completion delivery."""

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import aiohttp
import pytest
import requests

from test_match_reporting import PUUID, USER, match_payload


# Stops an otherwise unbounded monitor after its test observations are complete
class PollingFinished(BaseException):
    pass


# Routes the real Riot and webhook clients through a deterministic loopback service
@pytest.fixture
def riot_transport(lm_module, monkeypatch):
    state = {"cycle": -1, "scenario": "completion", "detail_calls": 0, "requests": [], "deliveries": []}
    live = {"gameId": 1, "gameStartTime": 1767226500000, "gameLength": 300, "gameMode": "CLASSIC", "gameQueueConfigId": 420, "mapId": 11, "participants": [{"puuid": PUUID, "riotId": USER + "#TAG", "teamId": 100, "championId": 103}], "bannedChampions": []}

    # Returns realistic provider responses and records the requests made by real dependencies
    class Handler(BaseHTTPRequestHandler):
        # Keeps access logs out of the application transcript
        def log_message(self, format, *args):
            pass

        # Selects the response at the HTTP boundary
        def do_GET(self):
            path = urlsplit(self.path).path
            status, payload = 200, {}
            if "/accounts/by-riot-id/" in path:
                payload = {"puuid": PUUID, "gameName": USER, "tagLine": "TAG"}
            elif "/summoners/by-puuid/" in path:
                payload = {"puuid": PUUID, "summonerLevel": 42, "revisionDate": 1767226800000}
            elif "/entries/by-puuid/" in path or "/champion-masteries/" in path:
                payload = []
            elif path.endswith("/ids"):
                payload = ["EUN1_1"] if state["scenario"] != "outage" and state["cycle"] >= 1 else []
                if state["scenario"] == "outage" and state["cycle"] >= 2:
                    status = 401
                if state["scenario"] == "rate_limit" and state["cycle"] >= 1:
                    status = 429
            elif path.endswith("/EUN1_1"):
                state["detail_calls"] += 1
                payload = match_payload()
                if state["scenario"] == "retry" and state["detail_calls"] == 1:
                    status = 404
                if state["scenario"] == "protected":
                    status = 403
            elif "/active-games/" in path:
                payload = live
                if state["cycle"] >= 1:
                    status = 401 if state["scenario"] == "outage" else 404
            elif path.endswith("/versions.json"):
                payload = ["15.19.1"]
            elif path.endswith("/champion.json"):
                payload = {"data": {"Ahri": {"key": "103"}}}
            else:
                raise AssertionError(path)
            state["requests"].append((path, status))
            if status != 200:
                payload = {"status": {"status_code": status, "message": "Unauthorized" if status == 401 else "Data not found"}}
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        # Captures actual serialized Discord or ntfy delivery without contacting a recipient
        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
            state["deliveries"].append((dict(self.headers), body))
            self.send_response(204)
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    original_request = aiohttp.ClientSession._request
    original_send = requests.Session.send

    # Preserves Pulsefire middleware and aiohttp response behavior while changing only the destination
    async def route_aiohttp(session, method, url, **kwargs):
        parsed = urlsplit(str(url))
        if parsed.path.endswith("/ids") and parse_qs(parsed.query).get("count") == ["10"]:
            state["cycle"] += 1
        if state["scenario"] == "descriptor" and "/active-games/" in parsed.path:
            raise OSError(24, "Too many open files")
        return await original_request(session, method, origin + parsed.path + ("?" + parsed.query if parsed.query else ""), **kwargs)

    # Preserves Requests preparation and serialization while delivering to loopback
    def route_requests(session, request, **kwargs):
        parsed = urlsplit(request.url)
        request.url = origin + parsed.path
        return original_send(session, request, **kwargs)

    monkeypatch.setattr(aiohttp.ClientSession, "_request", route_aiohttp)
    monkeypatch.setattr(requests.Session, "send", route_requests)
    session = requests.Session()
    monkeypatch.setattr(lm_module, "WEBHOOK_SESSION", session)
    monkeypatch.setattr(lm_module, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(lm_module, "WEBHOOK_STATUS_NOTIFICATION", True)
    monkeypatch.setattr(lm_module, "WEBHOOK_ERROR_NOTIFICATION", True)
    monkeypatch.setattr(lm_module, "WEBHOOK_URL", "https://discord.com/api/webhooks/123456789/test-value")
    monkeypatch.setattr(lm_module, "LIVENESS_REMINDER_SECONDS", 1)
    monkeypatch.setattr(lm_module, "COLORED_OUTPUT", False)
    clock = {"now": 1767226800, "sleeps": 0}

    # Advances the monitor clock without replacing time in third-party clients
    def sleep(seconds):
        clock["now"] += seconds
        clock["sleeps"] += 1
        if clock["sleeps"] >= 6:
            raise PollingFinished

    monkeypatch.setattr(lm_module, "time", SimpleNamespace(time=lambda: clock["now"], sleep=sleep))
    yield state
    session.close()
    server.shutdown()
    server.server_close()
    thread.join()


# Confirms real HTTP failures reach outage delivery without creating a false stopped or healthy state
def test_real_primary_failures_preserve_status(lm_module, riot_transport, capsys):
    riot_transport["scenario"] = "outage"
    with pytest.raises(PollingFinished):
        asyncio.run(lm_module.lol_monitor_user(USER + "#TAG", "eun1", None))
    transcript = capsys.readouterr().out
    assert "stopped playing" not in transcript
    assert "Monitoring healthy" not in transcript
    delivered = " ".join(body for _headers, body in riot_transport["deliveries"])
    assert "Riot rejected the configured API key" in delivered


# Confirms retryable detail failures are retried and live summaries reach either independent webhook provider
@pytest.mark.parametrize("scenario", ["completion", "retry", "protected"])
@pytest.mark.parametrize("provider", ["discord", "ntfy"])
def test_real_completed_match_delivery(lm_module, riot_transport, tmp_path, monkeypatch, scenario, provider):
    riot_transport["scenario"] = scenario
    monkeypatch.setattr(lm_module, "WEBHOOK_PROVIDER", provider)
    monkeypatch.setattr(lm_module, "INCLUDE_FORBIDDEN_MATCHES", scenario == "protected")
    if provider == "ntfy":
        monkeypatch.setattr(lm_module, "WEBHOOK_URL", "https://ntfy.sh/private-test-topic")
    csv_path = tmp_path / "matches.csv"
    with pytest.raises(PollingFinished):
        asyncio.run(lm_module.lol_monitor_user(USER + "#TAG", "eun1", str(csv_path)))
    assert riot_transport["detail_calls"] == (2 if scenario == "retry" else 1)
    delivered = " ".join(body for _headers, body in riot_transport["deliveries"])
    assert ("forbidden match" if scenario == "protected" else "match summary") in delivered
    assert len(csv_path.read_text(encoding="utf-8").splitlines()) == (1 if scenario == "protected" else 2)


# Confirms a historical report stays quiet even when the webhook channel is enabled
def test_real_history_listing_does_not_notify(lm_module, riot_transport):
    asyncio.run(lm_module.process_and_print_single_match("EUN1_1", PUUID, USER, "eun1", False, None))
    assert riot_transport["deliveries"] == []


# Confirms descriptor exhaustion is fatal before polling schedules more work
def test_primary_descriptor_exhaustion_stops(lm_module, riot_transport):
    riot_transport["scenario"] = "descriptor"
    with pytest.raises(SystemExit) as stopped:
        asyncio.run(lm_module.is_user_in_match(PUUID, "eun1"))
    assert stopped.value.code == 1
    assert riot_transport["requests"] == []


# Confirms exhausted real Pulsefire retries still reach the monitor's delayed outage alert
def test_persistent_rate_limit_delivers_one_error_alert(lm_module, riot_transport, monkeypatch):
    riot_transport["scenario"] = "rate_limit"
    monkeypatch.setattr(lm_module, "WEBHOOK_STATUS_NOTIFICATION", False)
    monkeypatch.setattr(lm_module, "LOL_ACTIVE_CHECK_INTERVAL", 150)
    monkeypatch.setattr(lm_module, "LOL_CHECK_INTERVAL", 150)
    with pytest.raises(PollingFinished):
        asyncio.run(lm_module.lol_monitor_user(USER + "#TAG", "eun1", None))
    assert len(riot_transport["deliveries"]) == 1
    assert "LoL Monitor error: Riot is rate limiting requests" in riot_transport["deliveries"][0][1]
