"""Offline end-to-end test: the real CLI, one monitoring cycle and Riot fixtures served over loopback."""

import csv
import json
import os
import subprocess
import sys
import textwrap
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = PROJECT_ROOT / "lol_monitor.py"

# A placeholder rather than a Riot-shaped key: nothing offline validates the format, and a realistic one
# only adds a finding to every secret scan
API_KEY = "riot-api-key-offline-test-value"
RIOT_ID = "offlineuser#EUNE"
PUUID = "offline-puuid-0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
MATCH_ID = "EUN1_7654321000"
NEW_MATCH_ID = "EUN1_7654321001"
MATCH_START = 1767225000

# One finished match in the shape the match endpoint returns, with the monitored player on the winning team
MATCH = {"info": {"gameStartTimestamp": MATCH_START * 1000, "gameEndTimestamp": (MATCH_START + 1500) * 1000, "gameCreation": (MATCH_START - 60) * 1000, "gameDuration": 1500, "gameMode": "CLASSIC", "queueId": 420, "mapId": 11, "gameType": "MATCHED_GAME", "gameVersion": "15.19.700.1234", "teams": [], "participants": [
    {"puuid": PUUID, "riotIdGameName": "offlineuser", "riotIdTagline": "EUNE", "teamId": 100, "championName": "Ahri", "championId": 103, "win": True, "kills": 9, "deaths": 3, "assists": 12, "champLevel": 16, "role": "SOLO", "lane": "MIDDLE"},
    {"puuid": "offline-puuid-rival", "riotIdGameName": "offlinerival", "riotIdTagline": "EUNE", "teamId": 200, "championName": "Zed", "championId": 238, "win": False, "kills": 3, "deaths": 9, "assists": 4, "champLevel": 15, "role": "SOLO", "lane": "MIDDLE"},
]}}

# The match the player finishes during the run, which is what the second cycle has to detect
NEW_MATCH = json.loads(json.dumps(MATCH))
NEW_MATCH["info"]["gameStartTimestamp"] = (MATCH_START + 3600) * 1000
NEW_MATCH["info"]["gameEndTimestamp"] = (MATCH_START + 5100) * 1000
NEW_MATCH["info"]["gameCreation"] = (MATCH_START + 3540) * 1000
NEW_MATCH["info"]["participants"][0]["championName"] = "Lux"
NEW_MATCH["info"]["participants"][0]["win"] = False

# The ranked entry the league endpoint returns for a placed player
LEAGUE_ENTRIES = [{"queueType": "RANKED_SOLO_5x5", "tier": "GOLD", "rank": "II", "leaguePoints": 47, "wins": 62, "losses": 55}]

# The two Data Dragon documents the champion name lookup reads
DDRAGON_VERSIONS = ["15.19.1", "15.18.1"]
DDRAGON_CHAMPIONS = {"data": {"Ahri": {"key": "103", "name": "Ahri"}, "Zed": {"key": "238", "name": "Zed"}}}


# Answers the Riot API, Data Dragon and the connectivity probe from one deterministic fixture
class OfflineRiotHandler(BaseHTTPRequestHandler):
    requested_paths: list = []
    # Counts the history reads so the fixture can finish a match between two cycles
    history_reads: int = 0

    # Serves whichever endpoint the path names, recording it so the test can prove the call really happened
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        OfflineRiotHandler.requested_paths.append(path)

        if path.endswith(f"/by-riot-id/offlineuser/{RIOT_ID.split('#')[1]}"):
            return self.reply({"puuid": PUUID, "gameName": "offlineuser", "tagLine": "EUNE"})
        if path == f"/lol/summoner/v4/summoners/by-puuid/{PUUID}":
            return self.reply({"summonerLevel": 421, "revisionDate": MATCH_START * 1000})
        if path == f"/lol/league/v4/entries/by-puuid/{PUUID}":
            return self.reply(LEAGUE_ENTRIES)
        if path == f"/lol/champion-mastery/v4/champion-masteries/by-puuid/{PUUID}/top":
            return self.reply([{"championId": 103, "championLevel": 42, "championPoints": 512345}])
        if path == f"/lol/spectator/v5/active-games/by-summoner/{PUUID}":
            return self.reply({"status": {"status_code": 404, "message": "Data not found"}}, status=404)
        if path == f"/lol/match/v5/matches/by-puuid/{PUUID}/ids":
            OfflineRiotHandler.history_reads += 1
            # The startup read and the first poll see the same history, then a new match finishes
            return self.reply([MATCH_ID] if OfflineRiotHandler.history_reads <= 2 else [NEW_MATCH_ID, MATCH_ID])
        if path == f"/lol/match/v5/matches/{MATCH_ID}":
            return self.reply(MATCH)
        if path == f"/lol/match/v5/matches/{NEW_MATCH_ID}":
            return self.reply(NEW_MATCH)
        if path == "/api/versions.json":
            return self.reply(DDRAGON_VERSIONS)
        if path.endswith("/data/en_US/champion.json"):
            return self.reply(DDRAGON_CHAMPIONS)
        # Anything else is the connectivity probe, which only needs to answer
        return self.reply({})

    # Writes one JSON body with the status the caller asked for
    def reply(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # Keeps the fixture server silent so its logging does not land in the captured output
    def log_message(self, fmt, *args):
        return


# Writes the configuration file the offline run is started with
def write_offline_config(tmp_path, port):
    config_path = tmp_path / "offline.conf"
    config_path.write_text(
        f'RIOT_API_KEY = "{API_KEY}"\n'
        f'RIOT_ID = "{RIOT_ID}"\n'
        'REGION = "eun1"\n'
        f'CHECK_INTERNET_URL = "http://127.0.0.1:{port}/"\n'
        'CSV_FILE = "matches.csv"\n'
        'LOL_LOGFILE = "offline_run.log"\n'
        "LOL_CHECK_INTERVAL = 300\n"
        "LIVENESS_CHECK_INTERVAL = 0\n"
        "CLEAR_SCREEN = False\n",
        encoding="utf-8",
    )
    return config_path


# Builds the program that runs the real CLI against the loopback fixture and stops after one cycle
def offline_run_source(config_path, port):
    return textwrap.dedent(f"""
        import functools
        import runpy
        import socket

        # Nothing in this run may leave the machine. A client that ignores the injected base URL would
        # otherwise reach the real Riot API and read as a fixture failure
        real_connect = socket.socket.connect

        def loopback_only(self, address):
            host = address[0] if isinstance(address, tuple) else ""
            if host not in ("127.0.0.1", "::1", "localhost"):
                raise AssertionError(f"the offline run tried to reach {{host}}")
            return real_connect(self, address)

        socket.socket.connect = loopback_only

        module = runpy.run_path({str(CLI_PATH)!r}, run_name="lol_monitor_offline_e2e")
        runtime = module["main"].__globals__
        runtime["sys"].argv = [{str(CLI_PATH)!r}, "--config-file", {str(config_path)!r}, "--env-file", "none"]
        # The region is templated into the base URL by pulsefire, so one loopback origin serves every platform
        runtime["RiotAPIClient"] = functools.partial(runtime["RiotAPIClient"], base_url="http://127.0.0.1:{port}")

        real_get = runtime["req"].get

        # Sends the Data Dragon lookups to the same fixture, leaving the request and the JSON parsing real
        def loopback_get(url, *args, **kwargs):
            return real_get(url.replace("https://ddragon.leagueoflegends.com", "http://127.0.0.1:{port}"), *args, **kwargs)

        runtime["req"].get = loopback_get
        waits = {{"count": 0}}

        # Ends the run on the second wait, so one quiet cycle and one that finds a finished match are measured
        def stop_after_two_cycles(seconds):
            waits["count"] += 1
            if waits["count"] >= 2:
                raise SystemExit(0)

        runtime["time"].sleep = stop_after_two_cycles
        module["main"]()
    """)


@pytest.fixture
# Serves the Riot fixtures on a loopback port for the duration of one test
def offline_riot_server():
    OfflineRiotHandler.requested_paths = []
    OfflineRiotHandler.history_reads = 0
    server = ThreadingHTTPServer(("127.0.0.1", 0), OfflineRiotHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_port, OfflineRiotHandler
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


# Verifies one complete run: the config is loaded, the real client talks to the fixture and the cycle reports the account
def test_one_monitoring_cycle_against_a_local_riot_fixture(offline_riot_server, tmp_path):
    port, handler = offline_riot_server
    config_path = write_offline_config(tmp_path, port)
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    environment.pop("NO_COLOR", None)
    result = subprocess.run([sys.executable, "-c", offline_run_source(config_path, port)], cwd=tmp_path, env=environment, check=False, capture_output=True, text=True, timeout=120)

    assert result.returncode == 0, result.stdout + result.stderr
    # The startup summary describes the run the config asked for
    assert "* Target:" in result.stdout and RIOT_ID in result.stdout
    assert "* Polling intervals:" in result.stdout
    assert str(config_path) in result.stdout
    assert "offline_run.log" in result.stdout and "matches.csv" in result.stdout
    # The account the fixture serves is reported rather than a placeholder
    assert f"Monitoring user {RIOT_ID}" in result.stdout
    assert "Summoner level:" in result.stdout and "421" in result.stdout
    assert "GOLD II" in result.stdout
    # The match history behind the account is read and the last known match reported
    assert MATCH_ID in result.stdout
    assert "Ahri" in result.stdout
    # No secret from the config reaches the screen
    assert API_KEY not in result.stdout
    # The match finished during the run is reported as new rather than replayed from the startup history
    assert "Ahri" in result.stdout and "Lux" in result.stdout
    assert result.stdout.count(NEW_MATCH_ID) >= 1
    # The champion names came from Data Dragon rather than from a hardcoded table
    assert "/api/versions.json" in handler.requested_paths
    # The real endpoints were called rather than stubbed out
    assert f"/lol/summoner/v4/summoners/by-puuid/{PUUID}" in handler.requested_paths
    assert f"/lol/match/v5/matches/{MATCH_ID}" in handler.requested_paths
    assert f"/lol/match/v5/matches/{NEW_MATCH_ID}" in handler.requested_paths
    assert f"/lol/spectator/v5/active-games/by-summoner/{PUUID}" in handler.requested_paths
    # Every file the configured run promised is on disk, and the log carries the same cycle
    log_text = (tmp_path / "offline_run.log").read_text(encoding="utf-8")
    assert f"Monitoring user {RIOT_ID}" in log_text
    assert API_KEY not in log_text
    # The finished match reached the CSV history with the values the fixture served
    rows = list(csv.DictReader((tmp_path / "matches.csv").open(encoding="utf-8")))
    assert [row["Champion"] for row in rows] == ["Lux"]
    assert rows[0]["Victory"] == "No" and rows[0]["Kills"] == "9"
