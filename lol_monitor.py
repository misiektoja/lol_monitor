#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v1.8.2

Tool implementing real-time tracking of LoL (League of Legends) players activities:
https://github.com/misiektoja/lol_monitor/

Python pip3 requirements:

pulsefire
requests
python-dateutil
python-dotenv (optional)
"""

VERSION = "1.8.2"

# ---------------------------
# CONFIGURATION SECTION START
# ---------------------------

CONFIG_BLOCK = """
# Get your development Riot API key (valid for 24 hours) from:
# https://developer.riotgames.com
#
# To request a persistent personal or production key, go to:
# https://developer.riotgames.com/app-type
#
# Provide the RIOT_API_KEY secret using one of the following methods:
#   - Pass it at runtime with -r / --riot-api-key
#   - Set it as an environment variable (e.g. export RIOT_API_KEY=...)
#   - Add it to ".env" file (RIOT_API_KEY=...) for persistent use
# Fallback:
#   - Hard-code it in the code or config file
RIOT_API_KEY = "your_riot_api_key"

# User to monitor, written as riot_id_name#tag, and the region code the account belongs to
# Saving them here means running the tool without repeating them every time
# Both are overridden by the positional arguments when those are passed
RIOT_ID = ""
REGION = ""

# SMTP settings for sending email notifications
# If left as-is, no notifications will be sent
#
# Provide the SMTP_PASSWORD secret using one of the following methods:
#   - Set it as an environment variable (e.g. export SMTP_PASSWORD=...)
#   - Add it to ".env" file (SMTP_PASSWORD=...) for persistent use
# Fallback:
#   - Hard-code it in the code or config file
SMTP_HOST = "your_smtp_server_ssl"
SMTP_PORT = 587
SMTP_USER = "your_smtp_user"
SMTP_PASSWORD = "your_smtp_password"
SMTP_SSL = True
SENDER_EMAIL = "your_sender_email"
RECEIVER_EMAIL = "your_receiver_email"

# Whether to send an email when user's playing status changes
# Can also be enabled via the -s flag
STATUS_NOTIFICATION = False

# Whether to send an email on errors
# Can also be disabled via the -e flag
ERROR_NOTIFICATION = True

# How often to check for player activity when the user is NOT in a game; in seconds
# Can also be set using the -c flag
LOL_CHECK_INTERVAL = 150  # 2,5 min

# How often to check for player activity when the user is IN a game; in seconds
# Can also be set using the -k flag
LOL_ACTIVE_CHECK_INTERVAL = 45  # 45 seconds

# Whether to include forbidden matches (requiring OAuth (RSO) access-token) in the output
# Forbidden matches are skipped silently when False or shown with a notice when True
# Can also be set using the -f flag
INCLUDE_FORBIDDEN_MATCHES = False

# How often to print a "liveness check" message to the output; in seconds
# Set to 0 to disable
LIVENESS_CHECK_INTERVAL = 43200  # 12 hours

# URL used to verify internet connectivity at startup
CHECK_INTERNET_URL = 'https://europe.api.riotgames.com/'

# Timeout used when checking initial internet connectivity; in seconds
CHECK_INTERNET_TIMEOUT = 5

# Whether to verify TLS certificates on every outbound connection, email delivery included
# Only set this to False on a network that intercepts TLS with its own certificate authority
# Switching it off removes the protection against an intercepted connection
VERIFY_SSL = True

# CSV file to write all game status changes
# Can also be set using the -b flag
CSV_FILE = ""

# Location of the optional dotenv file which can keep secrets
# If not specified it will try to auto-search for .env files
# To disable auto-search, set this to the literal string "none"
# Can also be set using the --env-file flag
DOTENV_FILE = ""

# Base name for the log file. Output will be saved to lol_monitor_<riot_id_name>.log
# Can include a directory path to specify the location, e.g. ~/some_dir/lol_monitor
LOL_LOGFILE = "lol_monitor"

# Whether to disable logging to lol_monitor_<riot_id_name>.log
# Can also be disabled via the -d flag
DISABLE_LOGGING = False

# Whether to print extra startup and runtime detail
# Independent of DEBUG_MODE, so enable both to see everything
# Can also be enabled via the --verbose flag, which turns it on regardless of this setting
VERBOSE_MODE = False

# Whether to print timestamped diagnostic detail, including every outbound call,
# each notification delivery attempt and the technical cause of failures
# Independent of VERBOSE_MODE, so enable both to see everything
# Can also be enabled via the --debug flag, which turns it on regardless of this setting
DEBUG_MODE = False

# Controls conversion of separator-only log lines to ASCII:
#   "Auto" - enable on Windows only (default)
#   "On"   - enable on every operating system
#   "Off"  - preserve Unicode separators in logs
ASCII_LOG_SEPARATORS = "Auto"

# Width of horizontal line
HORIZONTAL_LINE = 113

# Whether to clear the terminal screen after starting the tool
CLEAR_SCREEN = True

# Value used by signal handlers increasing/decreasing the check for player activity
# when user is in-game (LOL_ACTIVE_CHECK_INTERVAL); in seconds
LOL_ACTIVE_CHECK_SIGNAL_VALUE = 30  # 30 seconds

# LoL's region to continent mapping
REGION_TO_CONTINENT = {
    "eun1": "europe",   # Europe Nordic & East (EUNE)
    "euw1": "europe",   # Europe West (EUW)
    "tr1": "europe",    # Turkey (TR1)
    "ru": "europe",     # Russia
    "na1": "americas",  # North America (NA) - now the sole NA endpoint
    "br1": "americas",  # Brazil (BR)
    "la1": "americas",  # Latin America North (LAN)
    "la2": "americas",  # Latin America South (LAS)
    "jp1": "asia",      # Japan (JP)
    "kr": "asia",       # Korea (KR)
    "sg2": "sea",       # Southeast Asia (SEA) - Singapore, Malaysia, Indonesia (+ Thailand & Philippines since Jan 9, 2025)
    "tw2": "sea",       # Taiwan, Hong Kong & Macao (TW/HK/MO)
    "vn2": "sea",       # Vietnam (VN)
    "oc1": "sea"        # Oceania (OC)
}
"""

# -------------------------
# CONFIGURATION SECTION END
# -------------------------

game_modes_mapping = {
    "CLASSIC": "Summoner's Rift",
    "CHERRY": "Arena",
    "TUTORIAL": "Tutorial",
    "ONEFORALL": "One for All",
    "ARSR": "All Random Summoner's Rift",
    "ODIN": "Dominion/Crystal Scar",
    "SIEGE": "Nexus Siege",
    "ASSASSINATE": "Blood Hunt Assassin",
    "GAMEMODEX": "Nexus Blitz",
    "NEXUSBLITZ": "Nexus Blitz",
    "ULTBOOK": "Ultimate Spellbook",
    "ARAM": "ARAM",
    "URF": "Ultra Rapid Fire"
}

game_queue_mapping = {
    400: "Draft Pick (SR)",
    420: "Ranked Solo/Duo",
    430: "Blind Pick (SR)",
    440: "Ranked Flex (SR)",
    450: "ARAM",
    460: "Twisted Treeline (Blind)",
    470: "Twisted Treeline (Ranked)",
    490: "Normal (Quickplay SR)",
    700: "Clash",
    720: "ARAM Clash",
    830: "Co-op vs AI (Intro)",
    840: "Co-op vs AI (Beginner)",
    850: "Co-op vs AI (Intermediate)",
    900: "URF",
    920: "Legend of the Poro King",
    1020: "One for All",
    1300: "Nexus Blitz",
    1400: "Ultimate Spellbook",
    1700: "Arena"
}

map_id_mapping = {
    1: "Summoner's Rift (Autumn)",
    2: "Summoner's Rift (Summer)",
    3: "The Proving Grounds",
    4: "Twisted Treeline (Original)",
    8: "The Crystal Scar",
    10: "Twisted Treeline",
    11: "Summoner's Rift",
    12: "Howling Abyss",
    14: "Butcher's Bridge",
    16: "Cosmic Ruins",
    18: "Valoran City Park",
    19: "Substructure 43",
    20: "Crash Site",
    21: "Nexus Blitz",
    22: "Convergence",
    30: "Butcher's Bridge (Legacy)",
    76: "Cosmic Ruins",
    83: "Valoran City Park",
    100: "Overcharge",
    200: "Convergence",
    2100: "Arena"
}

game_type_mapping = {
    "MATCHED": "Matched",
    "MATCHED_GAME": "Matched",
    "CUSTOM_GAME": "Custom",
    "NORMAL_GAME": "Normal",
    "RANKED_GAME": "Ranked",
    "TUTORIAL_GAME": "Tutorial",
    "BOT": "Co-op vs AI",
    "ARAM_UNRANKED_5x5": "ARAM",
    "ONEFORALL": "One for All"
}


# Default dummy values so linters shut up
# Do not change values below - modify them in the configuration section or config file instead
RIOT_API_KEY = ""
RIOT_ID = ""
REGION = ""
SMTP_HOST = ""
SMTP_PORT = 0
SMTP_USER = ""
SMTP_PASSWORD = ""
SMTP_SSL = False
SENDER_EMAIL = ""
RECEIVER_EMAIL = ""
STATUS_NOTIFICATION = False
ERROR_NOTIFICATION = False
LOL_CHECK_INTERVAL = 0
LOL_ACTIVE_CHECK_INTERVAL = 0
INCLUDE_FORBIDDEN_MATCHES = False
LIVENESS_CHECK_INTERVAL = 0
CHECK_INTERNET_URL = ""
CHECK_INTERNET_TIMEOUT = 0
VERIFY_SSL = True
CSV_FILE = ""
DOTENV_FILE = ""
LOL_LOGFILE = ""
DISABLE_LOGGING = False
VERBOSE_MODE = False
DEBUG_MODE = False
ASCII_LOG_SEPARATORS = "Auto"
HORIZONTAL_LINE = 0
CLEAR_SCREEN = False
LOL_ACTIVE_CHECK_SIGNAL_VALUE = 0
REGION_TO_CONTINENT = {}

exec(CONFIG_BLOCK, globals())

# Default name for the optional config file
DEFAULT_CONFIG_FILENAME = "lol_monitor.conf"

# Documentation links, kept as constants so error messages, help text and the guides they point at cannot drift apart
PROJECT_URL = "https://github.com/misiektoja/lol_monitor"
DOCS_BASE_URL = "https://misiektoja.github.io/lol_monitor"
QUICK_START_GUIDE_URL = f"{DOCS_BASE_URL}/setup-and-first-run/"
CONFIG_FILE_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#configuration-file"
INTERVALS_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#check-intervals"
RIOT_API_KEY_GUIDE_URL = f"{DOCS_BASE_URL}/setup-and-first-run/#riot-api-key"
REGION_GUIDE_URL = f"{DOCS_BASE_URL}/setup-and-first-run/#region-codes"
SMTP_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#smtp-settings"
TLS_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#tls-verification"
INSTALL_GUIDE_URL = f"{DOCS_BASE_URL}/installation/"
DOCTOR_GUIDE_URL = f"{DOCS_BASE_URL}/troubleshooting/#doctor-preflight"
SECRETS_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#storing-secrets"
OUTPUT_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#output-and-files"
USAGE_GUIDE_URL = f"{DOCS_BASE_URL}/usage/"
RIOT_API_KEY_REGISTRATION_URL = "https://developer.riotgames.com"

# The accepted forms of the two positionals, named once so every message that asks for them agrees
RIOT_ID_FORMS = "Riot ID written as riot_id_name#tag"
REGION_FORMS = "region code such as eun1, euw1 or na1"

# What a rejected positional is told, kept beside the forms it names so the two cannot drift apart
RIOT_ID_INPUT_ERROR = "That is not a complete Riot ID, the name and tagline could not be read"
REGION_INPUT_ERROR = "That is not a region code this tool knows"

# One spelling per positional, so a printed command, a help example and a fix line cannot name it differently
RIOT_ID_PLACEHOLDER = "<riot_id>"
REGION_PLACEHOLDER = "<region>"

# List of secret keys to load from env/config
SECRET_KEYS = ("RIOT_API_KEY", "SMTP_PASSWORD")

# Secrets whose length is a fixed, published property of the credential itself. A Riot API key is the RGAPI-
# prefix plus a UUID, and a truncated paste is the usual way one arrives broken, so the length diagnoses that
# without revealing anything the format does not already. A password the user chose reports presence only
FIXED_LENGTH_SECRET_KEYS = frozenset(("RIOT_API_KEY",))

# Shortest secret replaced by plain substring search. Sanitizing runs over normal monitoring output, so a
# short value such as a simple SMTP password would otherwise redact ordinary words like champion names.
# Every credential this tool handles is far longer, and shorter ones stay covered by the shape patterns
# in sanitize_error_text that match the assignment and header forms an error can actually expose.
MIN_REDACTABLE_SECRET_LENGTH = 12

LIVENESS_CHECK_COUNTER = LIVENESS_CHECK_INTERVAL / LOL_CHECK_INTERVAL

stdout_bck = None
csvfieldnames = ['Match Start', 'Match Stop', 'Duration', 'Game Mode', 'Victory', 'Kills', 'Deaths', 'Assists', 'Champion', 'Level', 'Role', 'Lane', 'Team 1', 'Team 2']

CLI_CONFIG_PATH = None

# Secrets already exported when the process started, which a dotenv file must not overwrite
EXPORTED_SECRET_KEYS = frozenset()

# Secrets supplied as command line arguments, which override every other source
COMMAND_LINE_SECRET_KEYS = frozenset()

# Set when --config-file is given the literal string "none", which switches off the search rather than naming a file
CONFIG_DISCOVERY_DISABLED = False

# The exception the last connectivity check raised, so a quiet caller can classify what it did not print
LAST_CONNECTIVITY_ERROR = None

# to solve the issue: 'SyntaxError: f-string expression part cannot include a backslash'
nl_ch = "\n"


import sys

# Declared once so the startup gate, the packaging metadata and any later environment check cannot disagree
MINIMUM_PYTHON_VERSION = (3, 12)
MINIMUM_PYTHON_VERSION_TEXT = ".".join(str(part) for part in MINIMUM_PYTHON_VERSION)

if sys.version_info < MINIMUM_PYTHON_VERSION:
    print(f"* Error: Python version {MINIMUM_PYTHON_VERSION_TEXT} or higher required !")
    sys.exit(1)

import time
import os
from datetime import datetime
from dateutil import relativedelta
import calendar
import requests as req
import urllib3
import signal
import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import argparse
import ast
import csv
import platform
import re
import ipaddress
import asyncio
import html
import importlib.util
try:
    import aiohttp
    from pulsefire.clients import RiotAPIClient
except ModuleNotFoundError:
    raise SystemExit("Error: Couldn't find the Pulsefire library !\n\nTo install it, run:\n    pip3 install pulsefire\n\nOnce installed, re-run this tool. For more help, visit:\nhttps://pulsefire.iann838.com/usage/basic/installation/")
import shlex
import shutil
import tempfile
import unicodedata
from contextlib import asynccontextmanager, contextmanager
from collections import namedtuple
from pathlib import Path
from typing import Optional, Any, Dict, List, Mapping, Tuple, TypedDict


class RankedQueueInfo(TypedDict):
    tier: str
    rank: str
    lp: str
    wins: int
    losses: int


class RankedInfo(TypedDict):
    solo_duo: RankedQueueInfo
    flex: RankedQueueInfo


# Install methods the tool can detect, used to tailor every command it prints
INSTALL_METHOD_PYPI = "pip"
INSTALL_METHOD_SCRIPT = "manual"
INSTALL_METHOD_ENV_VAR = "LOL_MONITOR_INSTALL_METHOD"


# Returns True when the tool runs inside a container, so printed commands and paths can be adjusted for it
def running_in_container():
    if os.environ.get("LOL_MONITOR_IN_CONTAINER", "").strip().casefold() in ("1", "true", "yes"):
        return True
    if os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv"):
        return True
    try:
        with open("/proc/1/cgroup", encoding="utf-8", errors="replace") as cgroup_file:
            return any(marker in cgroup_file.read() for marker in ("docker", "containerd", "kubepods", "podman"))
    except OSError:
        return False


# Returns how the tool was started, either as the installed console script or as a downloaded standalone script
def install_method():
    override = os.environ.get(INSTALL_METHOD_ENV_VAR, "").strip().casefold()
    if override in (INSTALL_METHOD_PYPI, INSTALL_METHOD_SCRIPT):
        return override
    if os.path.basename(sys.argv[0] or "").casefold().endswith(".py"):
        return INSTALL_METHOD_SCRIPT
    return INSTALL_METHOD_PYPI


# Returns a readable name for the detected install method
def install_method_display_name(method=None):
    selected = install_method() if method is None else method
    base = {"pip": "PyPI install", "manual": "downloaded script"}.get(selected, selected)
    return f"{base} in a container" if running_in_container() else base


# Returns the argv prefix that invokes this tool for the detected install method
def install_command_prefix():
    if install_method() == INSTALL_METHOD_SCRIPT:
        return ["python3", os.path.basename(sys.argv[0]) or "lol_monitor.py"]
    return ["lol_monitor"]


# Returns one command-line argument quoted for the shell the user is most likely pasting into
def quote_command_argument(argument):
    text = str(argument)
    # A <placeholder> is documentation for the reader to replace, so quoting it would only be noise
    if text.startswith("<") and text.endswith(">"):
        return text
    if platform.system() == "Windows":
        return f'"{text}"' if (not text or any(char.isspace() for char in text)) else text
    return shlex.quote(text)


# True when a command writes the dotenv file itself, so it refuses an --env-file that switches dotenv loading off
def command_writes_dotenv(arguments=()):
    return any(str(argument) == "--setup" or str(argument).startswith("--set-") for argument in arguments)


# Returns a copy-pasteable command line for the detected install method, carrying the config and dotenv files this run was given
def render_command(arguments=None, include_paths=True, config_path=None, env_path=None):
    parts = list(install_command_prefix())
    parts.extend(str(argument) for argument in (arguments or []))
    # An explicitly passed path is always rendered, while include_paths only governs falling back to the active ones
    active_config = CLI_CONFIG_PATH or ("none" if CONFIG_DISCOVERY_DISABLED else None)
    selected_config = config_path if config_path is not None else (active_config if include_paths else None)
    selected_env = env_path if env_path is not None else (DOTENV_FILE if include_paths else None)
    if selected_config:
        parts.extend(["--config-file", str(selected_config)])
    # The "none" sentinel is carried so the printed command reads the setup this run read, except into a command
    # that writes the dotenv file, since those refuse the sentinel at their own argument gate
    if selected_env and not (str(selected_env).casefold() == "none" and command_writes_dotenv(arguments or ())):
        parts.extend(["--env-file", str(selected_env)])
    return " ".join(quote_command_argument(part) for part in parts)


# Returns the command that installs one package with the interpreter running this tool, never a bare pip
def pip_install_command(requirement):
    return " ".join(quote_command_argument(part) for part in (sys.executable or "python3", "-m", "pip", "install", requirement))


# Returns the keys a dotenv file itself defines, used to tell a file-supplied secret from an exported one
def dotenv_file_keys(env_path=None):
    if not env_path or not os.path.isfile(str(env_path)):
        return frozenset()
    try:
        from dotenv import dotenv_values
    except ImportError:
        return frozenset()
    try:
        return frozenset(name for name, value in dotenv_values(str(env_path)).items() if value is not None)
    except Exception:
        return frozenset()


# Returns where each effective environment secret came from, keeping an exported value ahead of the same name in a file
def secret_sources(env_path=None, exported_keys=None):
    file_keys = dotenv_file_keys(env_path)
    protected_keys = EXPORTED_SECRET_KEYS if exported_keys is None else frozenset(exported_keys)
    sources = {}
    for secret in SECRET_KEYS:
        if os.getenv(secret) is None:
            continue
        sources[secret] = "environment" if secret in protected_keys or secret not in file_keys else str(env_path)
    return sources


# Reloads dotenv secrets into the environment without replacing values that were exported when the process started
def reload_dotenv_secrets(env_path, exported_keys=None):
    from dotenv import dotenv_values
    protected_keys = EXPORTED_SECRET_KEYS if exported_keys is None else frozenset(exported_keys)
    values = dotenv_values(str(env_path))
    for secret in SECRET_KEYS:
        value = values.get(secret)
        if secret not in protected_keys and value is not None:
            os.environ[secret] = value
            debug_print("Secret reloaded", name=secret, source=str(env_path), value=secret_fingerprint(value, secret))


# Copies exported secrets into module globals and returns the applied names paired with whether the value changed
def load_secrets_from_environment(namespace=None):
    selected_namespace = globals() if namespace is None else namespace
    applied = []
    for secret in SECRET_KEYS:
        value = os.getenv(secret)
        if value is None:
            continue
        applied.append((secret, selected_namespace.get(secret) != value))
        selected_namespace[secret] = value
        debug_print("Secret resolved", name=secret, source="environment", value=secret_fingerprint(value, secret))
    return applied


# Groups the secrets that are set by the source each value actually came from, in the order precedence resolved them
def group_secrets_by_source(env_path=None):
    environment_sources = secret_sources(env_path)
    from_file, from_environment, from_settings, from_command_line = [], [], [], []
    for key in SECRET_KEYS:
        if not doctor_value_is_set(globals().get(key)):
            continue
        source = environment_sources.get(key)
        # An argument overrides whatever the dotenv file or the environment held, so it is checked first
        if key in COMMAND_LINE_SECRET_KEYS:
            from_command_line.append(key)
        elif source == "environment":
            from_environment.append(key)
        elif source:
            from_file.append(key)
        else:
            from_settings.append(key)
    return from_file, from_environment, from_settings, from_command_line


# Describes where each secret in effect came from, by name and never by value
def describe_secret_sources(env_path=None):
    from_file, from_environment, from_settings, from_command_line = group_secrets_by_source(env_path)
    described = []
    for names, label in ((from_command_line, "command line"), (from_environment, "environment"), (from_file, "dotenv file"), (from_settings, "configuration")):
        if names:
            described.append(f"{', '.join(names)} ({label})")
    return "; ".join(described) if described else "None"


# Matches every ANSI escape sequence, so third-party text cannot move the cursor or repaint the terminal
ANSI_ESCAPE_RE = re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]")


# Renders one diagnostic line as an operation followed by comma-separated key=value fields, dropping unset ones
def format_diagnostic_line(operation, fields):
    rendered = ", ".join(f"{key}={value}" for key, value in fields.items() if value is not None)
    return f"{operation}: {rendered}" if rendered else str(operation)


# Prints one timestamped and sanitized diagnostic line only when debug mode is enabled
def debug_print(_operation, **fields):
    if DEBUG_MODE:
        # Sanitized here rather than at each call site, since one caller interpolating a secret is enough to leak it
        message = format_diagnostic_line(_operation, fields)
        # The scanner does not treat the sanitizer as a barrier, so it reports the masked line as a leak
        # codeql[py/clear-text-logging-sensitive-data]
        print(f"[DEBUG {datetime.now().strftime('%H:%M:%S')}] {sanitize_error_text(message)}")


# Prints one sanitized operational detail only when verbose mode is enabled
def verbose_print(message):
    if VERBOSE_MODE:
        print(f"* {sanitize_error_text(message)}")


# Records a swallowed exception in debug output so a silently degraded feature can still be diagnosed
def debug_swallowed_exception(context, exc):
    debug_print(context, outcome="failed", error=f"{type(exc).__name__}: {exc}")


# Applies only the explicitly supplied --verbose and --debug flags so the command line always wins over the config file
def apply_diagnostic_cli_flags(args):
    global VERBOSE_MODE, DEBUG_MODE
    if getattr(args, "verbose", None):
        VERBOSE_MODE = True
    if getattr(args, "debug", None):
        DEBUG_MODE = True


# Strips terminal control sequences and other C0/C1 characters from third-party text before it reaches a console or a log
def sanitize_untrusted_text(value, max_length=256):
    if value is None:
        return ""
    text = ANSI_ESCAPE_RE.sub("", str(value))
    # Everything Riot sends is hostile until proven otherwise, so drop the control range outright
    text = "".join(character for character in text if character == " " or not unicodedata.category(character).startswith("C"))
    text = text.strip()
    if max_length and len(text) > max_length:
        text = text[:max_length] + "..."
    return text


# Reports whether a secret holds a real value rather than being empty or one of the shipped placeholders
def doctor_value_is_set(value):
    return isinstance(value, str) and bool(value.strip()) and not value.strip().startswith("your_")


# Describes a secret in diagnostic output without revealing any part of it
def secret_fingerprint(value, key=None):
    if not doctor_value_is_set(value):
        return "not set"
    return f"set, {len(value)} chars" if key in FIXED_LENGTH_SECRET_KEYS else "set"


# Returns the secret values long enough to replace wherever they appear, skipping the shipped placeholders
def known_secret_values():
    return [value for value in (globals().get(key) for key in SECRET_KEYS) if isinstance(value, str) and len(value) >= MIN_REDACTABLE_SECRET_LENGTH and not value.startswith("your_")]


# Redacts configured secrets and Riot credentials from one error-shaped value
def sanitize_error_text(value):
    text = str(value or "")
    for secret in sorted(known_secret_values(), key=len, reverse=True):
        text = text.replace(secret, "<redacted>")
    # Anchored on the assignment, header and URL forms an error can expose, so they hold at any secret length
    patterns = (
        (r"(?m)(\b(?:RIOT_API_KEY|SMTP_PASSWORD)\b\s*=\s*).*$", r"\1<redacted>"),
        (r"(?i)(['\"]?x-riot-token['\"]?\s*[:=]\s*['\"]?)[^\s,;'\"}]+", r"\1<redacted>"),
        (r"(?i)\bRGAPI-[A-Za-z0-9-]+", "<redacted>"),
        (r"(?i)([?&]api_key=)[^&#\s]+", r"\1<redacted>"),
    )
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text


# Every recovery category the tool can report, kept closed so a message is testable, deduplicable and translatable later
RECOVERY_CODES = frozenset({
    "config.missing", "config.invalid", "config.insecure",
    "dependency.missing",
    "secret.missing",
    "auth.api_key_invalid",
    "network.unavailable", "network.timeout",
    "riot.rate_limited", "riot.unavailable",
    "target.missing", "target.invalid", "target.region", "target.not_found",
    "smtp.invalid", "smtp.authentication", "smtp.connection",
    "file.exists", "file.unwritable",
    "unknown",
})

# A namedtuple rather than a dataclass, matching the shape every sibling monitor carries advice in
RecoveryAdvice = namedtuple("RecoveryAdvice", ["code", "summary", "fix", "retryable", "detail"])
RecoveryAdvice.__new__.__defaults__ = ("",)


# Carries structured recovery advice across an exception boundary without exposing technical detail
class RecoveryError(Exception):
    # Initializes a structured recovery exception, keeping the original cause attached for debug output
    def __init__(self, advice, cause=None):
        self.advice = advice
        self.cause = cause
        if cause is not None:
            self.__cause__ = cause
        super().__init__(advice.summary)


# Builds one piece of recovery advice, refusing any code outside the closed set and sanitizing every field
def make_recovery_advice(code, summary, fix, retryable, detail=""):
    if code not in RECOVERY_CODES:
        raise ValueError(f"Unsupported recovery code: {code}")
    return RecoveryAdvice(code, sanitize_error_text(summary), sanitize_error_text(fix), bool(retryable), sanitize_error_text(detail) if detail else "")


# Adds a directly relevant documentation link on its own line
def recovery_fix_with_guide(fix, guide_url):
    return f"{fix}\nGuide: {guide_url}"


# Returns the HTTP status carried by an error, when it has one
def recovery_http_status(error):
    status = getattr(error, "status", None)
    if not isinstance(status, int):
        status = getattr(getattr(error, "response", None), "status_code", None)
    return status if isinstance(status, int) else None


# Maps one exception plus its HTTP status and calling context to stable recovery advice
def classify_recovery_error(error=None, context="runtime", detail=""):
    if isinstance(error, RecoveryError):
        return error.advice
    message = str(detail or error or "").lower()
    safe_detail = sanitize_error_text(detail or error) if (detail or error) else ""
    status = recovery_http_status(error)

    # Builds one piece of advice, attaching the guide line only where a page actually covers the row
    def advice(code, summary, fix, retryable, guide_url=None):
        return make_recovery_advice(code, summary, recovery_fix_with_guide(fix, guide_url) if guide_url else fix, retryable, safe_detail)

    if context == "config":
        if "does not exist" in message:
            return advice("config.missing", safe_detail or "The configuration file was not found", f"Create one with '{render_command(['--generate-config', DEFAULT_CONFIG_FILENAME], include_paths=False)}' or correct the --config-file path", False, CONFIG_FILE_GUIDE_URL)
        return advice("config.invalid", safe_detail or "The configuration file could not be read", f"Correct the reported line, or start from a fresh template with '{render_command(['--generate-config', DEFAULT_CONFIG_FILENAME], include_paths=False)}'", False, CONFIG_FILE_GUIDE_URL)

    if context == "credentials":
        return advice("secret.missing", "No Riot API key reached the tool", f"Pass it with -r, export RIOT_API_KEY or add it to a dotenv file, then run {render_command([RIOT_ID_PLACEHOLDER, REGION_PLACEHOLDER])}", False, SECRETS_GUIDE_URL)

    if context == "target.missing":
        return advice("target.missing", safe_detail or "No player was provided", f"Pass a {RIOT_ID_FORMS} and a {REGION_FORMS}: {render_command([RIOT_ID_PLACEHOLDER, REGION_PLACEHOLDER])}", False, QUICK_START_GUIDE_URL)

    if context == "target.region":
        return advice("target.region", safe_detail or "That is not a region code this tool knows", f"Pass a {REGION_FORMS}, which is the short code and not the display name", False, REGION_GUIDE_URL)

    if context == "target":
        if status == 429 or "rate limit" in message:
            return advice("riot.rate_limited", "Riot rate limited the player lookup", "Wait for the reported period then try again", True, INTERVALS_GUIDE_URL)
        if "timed out" in message or "timeout" in message:
            return advice("network.timeout", "The Riot API request timed out", "Check connectivity then try again", True)
        if status in (401, 403) or "unauthorized" in message or "forbidden" in message:
            return advice("auth.api_key_invalid", "Riot rejected the configured API key", f"A development key expires 24 hours after it is issued, so copy a fresh one from {RIOT_API_KEY_REGISTRATION_URL}", False, RIOT_API_KEY_GUIDE_URL)
        if "region_to_continent" in message:
            return advice("target.region", safe_detail or REGION_INPUT_ERROR, f"Pass a {REGION_FORMS}, which is the short code and not the display name", False, REGION_GUIDE_URL)
        if "name and tagline" in message or "name#tag" in message:
            return advice("target.invalid", safe_detail or "That is not a complete Riot ID", f"Pass a {RIOT_ID_FORMS}, where the part after the # is the tag line and not the region", False, USAGE_GUIDE_URL)
        return advice("target.not_found", safe_detail or "Riot has no account for that Riot ID", "Check the game name and the tag line, since a renamed account cannot be monitored", False, USAGE_GUIDE_URL)

    if context == "connectivity":
        # Classified from the error, because the detail names the endpoint rather than the failure
        cause = str(error or "").lower()
        if "timed out" in cause or "timeout" in cause:
            return advice("network.timeout", "The connectivity endpoint did not answer in time", "Check network, DNS, proxy and the CHECK_INTERNET_URL setting", True)
        return advice("network.unavailable", "The connectivity endpoint could not be reached", "Check network, DNS, proxy and the CHECK_INTERNET_URL setting", True)

    if context == "email":
        if any(term in message for term in ("authentication", "auth", "username and password", "535")):
            return advice("smtp.authentication", "The SMTP server rejected the sign-in", "Check SMTP_USER and SMTP_PASSWORD, and use an app password if the provider requires one", False, SMTP_GUIDE_URL)
        if any(term in message for term in ("settings are incorrect", "incomplete", "invalid")):
            return advice("smtp.invalid", safe_detail or "The SMTP settings are incomplete or invalid", "Check SMTP_HOST, SMTP_PORT, SENDER_EMAIL and RECEIVER_EMAIL in the configuration file", False, SMTP_GUIDE_URL)
        return advice("smtp.connection", "The SMTP server could not be reached", "Check SMTP_HOST, SMTP_PORT and SMTP_SSL, then confirm the host is reachable from this machine", True, SMTP_GUIDE_URL)

    if context == "file.exists":
        return advice("file.exists", safe_detail or "The destination file already exists", f"Re-run with --force to replace it after a timestamped backup, or write to a different path with '{render_command(['--generate-config', '<new_file>'], include_paths=False)}'", False, CONFIG_FILE_GUIDE_URL)

    if context == "file":
        return advice("file.unwritable", safe_detail or "A file the tool writes could not be opened", "Check that the directory exists and is writable, or choose another path", False, OUTPUT_GUIDE_URL)

    # Runtime, which is the monitoring loop and every Riot API call it makes
    if status == 429 or "rate limit" in message or "too many requests" in message:
        return advice("riot.rate_limited", "Riot is rate limiting requests", "The tool will wait and retry. Increase the polling intervals if this repeats", True, INTERVALS_GUIDE_URL)
    if status in (401, 403) or "forbidden" in message or "unauthorized" in message:
        return advice("auth.api_key_invalid", "Riot rejected the configured API key", f"A development key expires 24 hours after it is issued, so copy a fresh one from {RIOT_API_KEY_REGISTRATION_URL}", False, RIOT_API_KEY_GUIDE_URL)
    if status == 404 or "not found" in message:
        return advice("target.not_found", "Riot has no account for the monitored Riot ID", "Check the game name and the tag line, since a renamed account cannot be monitored", False, USAGE_GUIDE_URL)
    if (status is not None and status >= 500) or any(term in message for term in ("internal server error", "service unavailable", "bad gateway")):
        return advice("riot.unavailable", "The Riot API is temporarily unavailable", "This is usually a Riot outage. The tool will keep retrying", True)
    if "timed out" in message or "timeout" in message:
        return advice("network.timeout", "The Riot API request timed out", "Check connectivity. The tool will keep retrying", True)
    if any(term in message for term in ("connection", "name resolution", "network is unreachable", "no connectivity")):
        return advice("network.unavailable", "Riot could not be reached", "Check connectivity, DNS and any proxy. The tool will keep retrying", True)
    return advice("unknown", safe_detail or "The request could not be completed", "Check the technical detail below and the monitoring log for the failing request", True)


# Renders one structured failure as the shared Error, To fix and optional Technical detail block
def render_recovery_error(error=None, context="runtime", debug=None, detail=""):
    advice = classify_recovery_error(error, context, detail)
    # Resolved here rather than at each call site, so one flag decides whether the technical line is printed
    show_debug = DEBUG_MODE if debug is None else debug
    lines = [f"* Error: {advice.summary}", f"To fix: {advice.fix}"]
    # A detail that only repeats the summary spends a line saying nothing, which is section 15.52's rule for rows
    if show_debug and advice.detail and advice.detail != advice.summary:
        lines.append(f"Technical detail: {sanitize_error_text(advice.detail)}")
    return "\n".join(lines)


# Prints one structured recovery error and returns its stable advice
def print_recovery_error(error=None, context="runtime", debug=None, detail=""):
    advice = classify_recovery_error(error, context, detail)
    print(render_recovery_error(RecoveryError(advice), debug=debug))
    return advice


# Tracks the last uninterrupted recovery category so a long outage cannot repeat the same hint every cycle
class RecoveryHintTracker:
    # Starts with no category, so the first failure of any kind always renders its hint
    def __init__(self):
        self.last_code = None

    # Returns True for the first category and again only when the failure category changes
    def should_render(self, advice):
        if advice.code == self.last_code:
            return False
        self.last_code = advice.code
        return True

    # Clears suppression after a successful cycle, so a recurrence is reported again
    def reset(self):
        self.last_code = None


# Restores Python's default Ctrl+C behavior while a prompt waits, so the prompt reports the outcome instead of the signal handler
@contextmanager
def default_interrupt_handling():
    try:
        previous_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, signal.default_int_handler)
    except (ValueError, OSError):
        # Handlers can only be replaced from the main thread, which is where every prompt runs
        yield
        return
    try:
        yield
    finally:
        try:
            signal.signal(signal.SIGINT, previous_handler)
        except (ValueError, OSError):
            pass


# Reads one visible answer with Python's default Ctrl+C behavior
def read_interactively(reader, *args, **kwargs):
    with default_interrupt_handling():
        return reader(*args, **kwargs)


# Copies an existing file to a timestamped private backup before it is replaced, returning the backup path or None
def create_timestamped_backup(destination, attempts=100):
    destination_path = Path(destination).expanduser()
    if not destination_path.is_file():
        return None
    existing_bytes = destination_path.read_bytes()
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    for attempt in range(attempts):
        suffix = f".{stamp}.bak" if attempt == 0 else f".{stamp}-{attempt}.bak"
        backup_path = destination_path.with_name(destination_path.name + suffix)
        try:
            # O_EXCL so a backup can never overwrite an earlier one, even under a concurrent run
            descriptor = os.open(str(backup_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            continue
        try:
            with os.fdopen(descriptor, "wb") as backup_file:
                backup_file.write(existing_bytes)
                backup_file.flush()
                os.fsync(backup_file.fileno())
        except Exception:
            try:
                os.unlink(str(backup_path))
            except OSError:
                pass
            raise
        return str(backup_path)
    raise OSError(f"Could not create a unique backup for '{destination_path}' after {attempts} attempts")


# Writes the configuration atomically, backing up whatever was there first
def write_config_file(destination, content):
    destination_path = Path(destination).expanduser()
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path = create_timestamped_backup(destination_path)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", prefix=f".{destination_path.name}.", suffix=".tmp", dir=str(destination_path.parent), delete=False) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(str(temporary_path), str(destination_path))
        temporary_path = None
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    debug_print("Config file written", path=str(destination_path), backup=backup_path, outcome="OK")
    return {"path": str(destination_path), "backup_path": backup_path}


# Asks before replacing a config file that already exists, so a generated template cannot land silently
def confirm_generated_config_replacement(destination, force=False, interactive=None, input_func=input):
    destination_path = Path(destination).expanduser()
    if not destination_path.exists() or force:
        return True
    terminal_is_interactive = bool(sys.stdin.isatty()) if interactive is None else bool(interactive)
    if not terminal_is_interactive:
        raise FileExistsError(f"Config file '{destination_path}' already exists and there is no terminal to confirm replacing it")
    try:
        answer = str(read_interactively(input_func, f"Config file '{destination_path}' exists. Replace it and keep a timestamped backup? [y/N]: ")).strip().casefold()
    except (EOFError, KeyboardInterrupt):
        print()
        answer = ""
    return answer in ("y", "yes")


# Writes one generated config atomically, backing up whatever was there first
def write_generated_config(output_file, content, force=False, interactive=None, input_func=input):
    destination = Path(output_file).expanduser()
    if not confirm_generated_config_replacement(destination, force, interactive, input_func):
        return None, False
    return write_config_file(destination, content)["backup_path"], True


# Silences the repeated certificate warning once verification is off, so the choice is reported by the startup summary instead of on every request
def apply_tls_verification_setting():
    if not VERIFY_SSL:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Returns the TLS context every outbound connection uses, unverified while VERIFY_SSL is off
def tls_context():
    context = ssl.create_default_context()
    if not VERIFY_SSL:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context


# Yields a Riot API client whose session honors the configured TLS verification setting
@asynccontextmanager
async def riot_api_client():
    async with RiotAPIClient(default_headers={"X-Riot-Token": RIOT_API_KEY}) as client:
        if not VERIFY_SSL:
            # pulsefire builds its own session on entry, so an unverified connector can only be applied by replacing it
            entered_session = getattr(client, "session", None)
            debug_print("TLS verification", target="Riot API session", outcome="OK" if entered_session is not None else "degraded")
            if entered_session is None:
                # A release that moves the session should still run, verifying, rather than fail on a missing attribute
                print("* Warning: TLS verification stays on for the Riot API session, which this pulsefire release does not expose")
            else:
                client.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=tls_context()))
                await entered_session.close()
        yield client


# The settings email delivery needs before any notification can be sent
EMAIL_DELIVERY_SETTINGS = ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SENDER_EMAIL", "RECEIVER_EMAIL")


# Returns the email settings still holding a shipped placeholder or no value at all
def unset_email_settings():
    return [name for name in EMAIL_DELIVERY_SETTINGS if not doctor_value_is_set(globals().get(name))]


# Reports whether separator-only log lines should use ASCII on this system
def ascii_log_separators_enabled():
    mode = str(ASCII_LOG_SEPARATORS).strip().lower()
    if mode not in {"auto", "on", "off"}:
        raise ValueError("ASCII_LOG_SEPARATORS must be 'Auto', 'On' or 'Off'")
    return mode == "on" or (mode == "auto" and platform.system() == "Windows")


# Converts Unicode-only horizontal separator lines to ASCII when configured
def normalize_log_separators(message):
    if not ascii_log_separators_enabled():
        return message
    return re.sub(r"(?m)^─+$", lambda match: match.group(0).replace("─", "-"), message)


# Returns the log file monitoring will actually write, which takes its name from the Riot ID
def build_log_path(base_path, suffix):
    log_path = Path(os.path.expanduser(str(base_path)))
    if log_path.suffix == "" and suffix:
        log_path = log_path.parent / f"{log_path.name}_{suffix}.log"
    return log_path


# Logger class to output messages to stdout and log file
class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.logfile = open(filename, "a", buffering=1, encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.logfile.write(normalize_log_separators(message.expandtabs(8)))
        self.terminal.flush()
        self.logfile.flush()

    def flush(self):
        pass


# Signal handler when user presses Ctrl+C
def signal_handler(sig, frame):
    sys.stdout = stdout_bck
    print('\n* You pressed Ctrl+C, tool is terminated.')
    sys.exit(0)


# Checks internet connectivity
def check_internet(url=None, timeout=None, quiet=False):
    global LAST_CONNECTIVITY_ERROR
    # Read at call time, since a default bound at import would ignore whatever the config file set
    selected_url = CHECK_INTERNET_URL if url is None else url
    selected_timeout = CHECK_INTERNET_TIMEOUT if timeout is None else timeout
    debug_print("Connectivity check", url=selected_url, timeout=f"{selected_timeout}s", verify_ssl=VERIFY_SSL)
    try:
        _ = req.get(selected_url, timeout=selected_timeout, verify=VERIFY_SSL)
        LAST_CONNECTIVITY_ERROR = None
        debug_print("Connectivity check", url=selected_url, outcome="OK")
        return True
    except req.RequestException as e:
        # A quiet caller renders the failure itself, which the doctor needs so nothing lands on its progress line
        LAST_CONNECTIVITY_ERROR = e
        debug_print("Connectivity check", url=selected_url, outcome="failed", error=f"{type(e).__name__}: {e}")
        if not quiet:
            print_recovery_error(e, context="connectivity")
        return False


# Clears the terminal screen
def clear_screen(enabled=True):
    if not enabled:
        return
    try:
        if platform.system() == 'Windows':
            os.system('cls')
        else:
            os.system('clear')
    except Exception:
        print("* Cannot clear the screen contents")


# Converts absolute value of seconds to human readable format
def display_time(seconds, granularity=2):
    intervals = (
        ('years', 31556952),  # approximation
        ('months', 2629746),  # approximation
        ('weeks', 604800),    # 60 * 60 * 24 * 7
        ('days', 86400),      # 60 * 60 * 24
        ('hours', 3600),      # 60 * 60
        ('minutes', 60),
        ('seconds', 1),
    )
    result = []

    if seconds > 0:
        for name, count in intervals:
            value = seconds // count
            if value:
                seconds -= value * count
                if value == 1:
                    name = name.rstrip('s')
                result.append(f"{value} {name}")
        return ', '.join(result[:granularity])
    else:
        return '0 seconds'


# Calculates time span between two timestamps, accepts timestamp integers, floats and datetime objects
def calculate_timespan(timestamp1, timestamp2, show_weeks=True, show_hours=True, show_minutes=True, show_seconds=False, granularity=3):
    result = []
    intervals = ['years', 'months', 'weeks', 'days', 'hours', 'minutes', 'seconds']
    ts1 = timestamp1
    ts2 = timestamp2

    if type(timestamp1) is int:
        dt1 = datetime.fromtimestamp(int(ts1))
    elif type(timestamp1) is float:
        ts1 = int(round(ts1))
        dt1 = datetime.fromtimestamp(ts1)
    elif type(timestamp1) is datetime:
        dt1 = timestamp1
        ts1 = int(round(dt1.timestamp()))
    else:
        return ""

    if type(timestamp2) is int:
        dt2 = datetime.fromtimestamp(int(ts2))
    elif type(timestamp2) is float:
        ts2 = int(round(ts2))
        dt2 = datetime.fromtimestamp(ts2)
    elif type(timestamp2) is datetime:
        dt2 = timestamp2
        ts2 = int(round(dt2.timestamp()))
    else:
        return ""

    if ts1 >= ts2:
        ts_diff = ts1 - ts2
    else:
        ts_diff = ts2 - ts1
        dt1, dt2 = dt2, dt1

    if ts_diff > 0:
        date_diff = relativedelta.relativedelta(dt1, dt2)
        years = date_diff.years
        months = date_diff.months
        weeks = date_diff.weeks
        if not show_weeks:
            weeks = 0
        days = date_diff.days
        if weeks > 0:
            days = days - (weeks * 7)
        hours = date_diff.hours
        if (not show_hours and ts_diff > 86400):
            hours = 0
        minutes = date_diff.minutes
        if (not show_minutes and ts_diff > 3600):
            minutes = 0
        seconds = date_diff.seconds
        if (not show_seconds and ts_diff > 60):
            seconds = 0
        date_list = [years, months, weeks, days, hours, minutes, seconds]

        for index, interval in enumerate(date_list):
            if interval > 0:
                name = intervals[index]
                if interval == 1:
                    name = name.rstrip('s')
                result.append(f"{interval} {name}")
        return ', '.join(result[:granularity])
    else:
        return '0 seconds'


# Opens one authenticated SMTP session and leaves closing it to the caller
def smtp_connect_and_login(use_ssl, smtp_timeout=15):
    smtp_object = smtplib.SMTP(SMTP_HOST, int(SMTP_PORT), timeout=smtp_timeout)
    try:
        if use_ssl:
            smtp_object.starttls(context=tls_context())
        smtp_object.login(SMTP_USER, SMTP_PASSWORD)
        return smtp_object
    except Exception:
        try:
            smtp_object.quit()
        except Exception:
            pass
        raise


# Sends email notification
def send_email(subject, body, body_html, use_ssl, smtp_timeout=15):
    fqdn_re = re.compile(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}\.?$)')
    email_re = re.compile(r'[^@]+@[^@]+\.[^@]+')

    try:
        ipaddress.ip_address(str(SMTP_HOST))
    except ValueError:
        if not fqdn_re.search(str(SMTP_HOST)):
            print("Error sending email - SMTP settings are incorrect (invalid IP address/FQDN in SMTP_HOST)")
            return 1

    try:
        port = int(SMTP_PORT)
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        print("Error sending email - SMTP settings are incorrect (invalid port number in SMTP_PORT)")
        return 1

    if not email_re.search(str(SENDER_EMAIL)) or not email_re.search(str(RECEIVER_EMAIL)):
        print("Error sending email - SMTP settings are incorrect (invalid email in SENDER_EMAIL or RECEIVER_EMAIL)")
        return 1

    if not doctor_value_is_set(SMTP_USER) or not doctor_value_is_set(SMTP_PASSWORD):
        print("Error sending email - SMTP settings are incorrect (check SMTP_USER & SMTP_PASSWORD variables)")
        return 1

    if not subject or not isinstance(subject, str):
        print("Error sending email - SMTP settings are incorrect (subject is not a string or is empty)")
        return 1

    if not body and not body_html:
        print("Error sending email - SMTP settings are incorrect (body and body_html cannot be empty at the same time)")
        return 1

    try:
        smtpObj = smtp_connect_and_login(use_ssl, smtp_timeout=smtp_timeout)
        email_msg = MIMEMultipart('alternative')
        email_msg["From"] = SENDER_EMAIL
        email_msg["To"] = RECEIVER_EMAIL
        email_msg["Subject"] = str(Header(subject, 'utf-8'))

        if body:
            part1 = MIMEText(body, 'plain')
            part1 = MIMEText(body.encode('utf-8'), 'plain', _charset='utf-8')
            email_msg.attach(part1)

        if body_html:
            part2 = MIMEText(body_html, 'html')
            part2 = MIMEText(body_html.encode('utf-8'), 'html', _charset='utf-8')
            email_msg.attach(part2)

        smtpObj.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, email_msg.as_string())
        smtpObj.quit()
        debug_print("Email delivery", recipient=RECEIVER_EMAIL, outcome="OK")
    except Exception as e:
        debug_print("Email delivery", recipient=RECEIVER_EMAIL, outcome="failed", error=f"{type(e).__name__}: {e}")
        print_recovery_error(e, context="email")
        return 1
    verbose_print(f"Email delivered to {RECEIVER_EMAIL}")
    return 0


# Initializes the CSV file
def init_csv_file(csv_file_name):
    try:
        if not os.path.isfile(csv_file_name) or os.path.getsize(csv_file_name) == 0:
            with open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
                writer.writeheader()
            debug_print("CSV file initialized", path=csv_file_name, outcome="OK")
    except Exception as e:
        debug_print("CSV file initialized", path=csv_file_name, outcome="failed", error=f"{type(e).__name__}: {e}")
        raise RuntimeError(f"Could not initialize CSV file '{csv_file_name}': {e}")


# Writes CSV entry
def write_csv_entry(csv_file_name, start_date_ts, stop_date_ts, duration_ts, game_mode, victory, kills, deaths, assists, champion, level, role, lane, team1, team2):
    try:

        with open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8") as csv_file:
            csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
            csvwriter.writerow({'Match Start': start_date_ts, 'Match Stop': stop_date_ts, 'Duration': duration_ts, 'Game Mode': game_mode, 'Victory': victory, 'Kills': kills, 'Deaths': deaths, 'Assists': assists, 'Champion': champion, 'Level': level, 'Role': role, 'Lane': lane, 'Team 1': team1, 'Team 2': team2})

        debug_print("CSV row written", path=csv_file_name, outcome="OK")
    except Exception as e:
        debug_print("CSV row written", path=csv_file_name, outcome="failed", error=f"{type(e).__name__}: {e}")
        raise RuntimeError(f"Failed to write to CSV file '{csv_file_name}': {e}")


# Returns the current date/time in human readable format; eg. Sun 21 Apr 2024, 15:08:45
def get_cur_ts(ts_str=""):
    return (f'{ts_str}{calendar.day_abbr[(datetime.fromtimestamp(int(time.time()))).weekday()]} {datetime.fromtimestamp(int(time.time())).strftime("%d %b %Y, %H:%M:%S")}')


# Prints the current date/time in human readable format with separator; eg. Sun 21 Apr 2024, 15:08:45
def print_cur_ts(ts_str=""):
    print(get_cur_ts(str(ts_str)))
    print("─" * HORIZONTAL_LINE)


# Returns the timestamp/datetime object in human readable format (long version); eg. Sun 21 Apr 2024, 15:08:45
def get_date_from_ts(ts):
    if type(ts) is datetime:
        ts_new = int(round(ts.timestamp()))
    elif type(ts) is int:
        ts_new = ts
    elif type(ts) is float:
        ts_new = int(round(ts))
    else:
        return ""

    return (f'{calendar.day_abbr[(datetime.fromtimestamp(ts_new)).weekday()]} {datetime.fromtimestamp(ts_new).strftime("%d %b %Y, %H:%M:%S")}')


# Returns the timestamp/datetime object in human readable format (short version); eg.
# Sun 21 Apr 15:08
# Sun 21 Apr 24, 15:08 (if show_year == True and current year is different)
# Sun 21 Apr (if show_hour == False)
def get_short_date_from_ts(ts, show_year=False, show_hour=True):
    if type(ts) is datetime:
        ts_new = int(round(ts.timestamp()))
    elif type(ts) is int:
        ts_new = ts
    elif type(ts) is float:
        ts_new = int(round(ts))
    else:
        return ""

    if show_hour:
        hour_strftime = " %H:%M"
    else:
        hour_strftime = ""

    if show_year and int(datetime.fromtimestamp(ts_new).strftime("%Y")) != int(datetime.now().strftime("%Y")):
        if show_hour:
            hour_prefix = ","
        else:
            hour_prefix = ""
        return (f'{calendar.day_abbr[(datetime.fromtimestamp(ts_new)).weekday()]} {datetime.fromtimestamp(ts_new).strftime(f"%d %b %y{hour_prefix}{hour_strftime}")}')
    else:
        return (f'{calendar.day_abbr[(datetime.fromtimestamp(ts_new)).weekday()]} {datetime.fromtimestamp(ts_new).strftime(f"%d %b{hour_strftime}")}')


# Returns the timestamp/datetime object in human readable format (only hour, minutes and optionally seconds): eg. 15:08:12
def get_hour_min_from_ts(ts, show_seconds=False):
    if type(ts) is datetime:
        ts_new = int(round(ts.timestamp()))
    elif type(ts) is int:
        ts_new = ts
    elif type(ts) is float:
        ts_new = int(round(ts))
    else:
        return ""

    if show_seconds:
        out_strf = "%H:%M:%S"
    else:
        out_strf = "%H:%M"
    return (str(datetime.fromtimestamp(ts_new).strftime(out_strf)))


# Returns the range between two timestamps/datetime objects; eg. Sun 21 Apr 14:09 - 14:15
def get_range_of_dates_from_tss(ts1, ts2, between_sep=" - ", short=False):
    if type(ts1) is datetime:
        ts1_new = int(round(ts1.timestamp()))
    elif type(ts1) is int:
        ts1_new = ts1
    elif type(ts1) is float:
        ts1_new = int(round(ts1))
    else:
        return ""

    if type(ts2) is datetime:
        ts2_new = int(round(ts2.timestamp()))
    elif type(ts2) is int:
        ts2_new = ts2
    elif type(ts2) is float:
        ts2_new = int(round(ts2))
    else:
        return ""

    ts1_strf = datetime.fromtimestamp(ts1_new).strftime("%Y%m%d")
    ts2_strf = datetime.fromtimestamp(ts2_new).strftime("%Y%m%d")

    if ts1_strf == ts2_strf:
        if short:
            out_str = f"{get_short_date_from_ts(ts1_new)}{between_sep}{get_hour_min_from_ts(ts2_new)}"
        else:
            out_str = f"{get_date_from_ts(ts1_new)}{between_sep}{get_hour_min_from_ts(ts2_new, show_seconds=True)}"
    else:
        if short:
            out_str = f"{get_short_date_from_ts(ts1_new)}{between_sep}{get_short_date_from_ts(ts2_new)}"
        else:
            out_str = f"{get_date_from_ts(ts1_new)}{between_sep}{get_date_from_ts(ts2_new)}"
    return (str(out_str))


# Signal handler for SIGUSR1 allowing to switch game playing status changes email notifications
def toggle_status_changes_notifications_signal_handler(sig, frame):
    global STATUS_NOTIFICATION
    STATUS_NOTIFICATION = not STATUS_NOTIFICATION
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [status changes = {STATUS_NOTIFICATION}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGTRAP allowing to increase check timer for player activity when user is in game by LOL_ACTIVE_CHECK_SIGNAL_VALUE seconds
def increase_active_check_signal_handler(sig, frame):
    global LOL_ACTIVE_CHECK_INTERVAL
    LOL_ACTIVE_CHECK_INTERVAL = LOL_ACTIVE_CHECK_INTERVAL + LOL_ACTIVE_CHECK_SIGNAL_VALUE
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* LoL timers: [active check interval: {display_time(LOL_ACTIVE_CHECK_INTERVAL)}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGABRT allowing to decrease check timer for player activity when user is in game by LOL_ACTIVE_CHECK_SIGNAL_VALUE seconds
def decrease_active_check_signal_handler(sig, frame):
    global LOL_ACTIVE_CHECK_INTERVAL
    if LOL_ACTIVE_CHECK_INTERVAL - LOL_ACTIVE_CHECK_SIGNAL_VALUE > 0:
        LOL_ACTIVE_CHECK_INTERVAL = LOL_ACTIVE_CHECK_INTERVAL - LOL_ACTIVE_CHECK_SIGNAL_VALUE
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* LoL timers: [active check interval: {display_time(LOL_ACTIVE_CHECK_INTERVAL)}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGHUP allowing to reload secrets from .env
def reload_secrets_signal_handler(sig, frame):
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")

    # disable autoscan if DOTENV_FILE set to none
    if DOTENV_FILE and DOTENV_FILE.lower() == 'none':
        env_path = None
    else:
        # reload .env if python-dotenv is installed
        try:
            from dotenv import find_dotenv
            if DOTENV_FILE:
                env_path = DOTENV_FILE
            else:
                env_path = find_dotenv()
            if env_path:
                # An exported secret keeps winning after a reload, so precedence is the same before and after it
                reload_dotenv_secrets(env_path)
            else:
                print("* No .env file found, skipping env-var reload")
        except ImportError:
            env_path = None
            print("* python-dotenv not installed, skipping env-var reload")

    if env_path:
        for secret in SECRET_KEYS:
            old_val = globals().get(secret)
            val = os.getenv(secret)
            if val is not None and val != old_val:
                globals()[secret] = val
                print(f"* Reloaded {secret} from {env_path} ({secret_fingerprint(val, secret)})")

    print_cur_ts("Timestamp:\t\t\t")


# Adds new participant to the team
def add_new_team_member(list_of_teams, teamid, member):
    if not list_of_teams:
        list_of_teams.append({"id": teamid, "members": [member]})
        return

    teamid_exists = False
    if list_of_teams:
        for team in list_of_teams:
            if team.get("id") == teamid:
                team["members"].append(member)
                teamid_exists = True

    if not teamid_exists:
        list_of_teams.append({"id": teamid, "members": [member]})


# Converts Riot's gameType to a human-friendly label
def humanize_game_type(game_type: Optional[str]) -> str:
    # Sanitized before the lookup and the title casing, since an escape sequence inside the value corrupts both
    game_type = sanitize_untrusted_text(game_type, max_length=64)
    if not game_type:
        return "Unknown"
    return game_type_mapping.get(game_type, game_type.replace("_", " ").title())


# Returns a short patch label (major.minor) and full build when available
def format_game_version_label(game_version: Optional[str]) -> str:
    if not game_version:
        return "Unknown"

    version = sanitize_untrusted_text(game_version, max_length=64)
    if not version or version.lower() == "unknown":
        return "Unknown"

    parts = version.split(".")
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
        short_version = f"{parts[0]}.{parts[1]}"
        if short_version != version:
            return f"{short_version} ({version})"
        return short_version

    return version


# Returns the best available Riot name for a participant
def get_participant_display_name(participant: Mapping[str, Any]) -> str:
    return sanitize_untrusted_text(resolve_participant_display_name(participant), max_length=64) or "unknown"


# Reads the first display name a participant record carries, in the order Riot fills the fields
def resolve_participant_display_name(participant: Mapping[str, Any]) -> str:
    if not participant:
        return "unknown"

    riot_game_name = participant.get("riotIdGameName")
    if riot_game_name:
        return riot_game_name

    riot_id = participant.get("riotId")
    if isinstance(riot_id, dict):
        game_name = riot_id.get("gameName")
        if game_name:
            return game_name
        riot_str = riot_id.get("riotId")
        if isinstance(riot_str, str) and riot_str:
            return riot_str.split('#', 1)[0]
    elif isinstance(riot_id, str) and riot_id:
        return riot_id.split('#', 1)[0]

    summoner_name = participant.get("summonerName")
    if summoner_name:
        return summoner_name

    return "unknown"


# Builds printable lines for banned champions grouped by team
def format_banned_champions_output(bans_by_team: Dict[int, List[Tuple[Optional[int], str]]]):
    total_bans = sum(len(bans) for bans in bans_by_team.values())
    if total_bans == 0:
        return [], False

    non_empty_team_ids = [team_id for team_id, bans in bans_by_team.items() if bans]
    shared_pool = len(non_empty_team_ids) <= 1
    lines: List[str] = []

    if shared_pool:
        combined_bans: List[Tuple[Optional[int], str]] = []
        for team_id in non_empty_team_ids:
            combined_bans.extend(bans_by_team.get(team_id, []))
        combined_bans.sort(key=lambda x: x[0] or 0)
        for pick_turn, champ_label in combined_bans:
            pick_info = f"pick {pick_turn}" if pick_turn else "pick ?"
            lines.append(f"- {champ_label} ({pick_info})")
    else:
        for idx, team_id in enumerate(sorted(bans_by_team.keys())):
            if idx > 0:
                lines.append("")
            team_line = f"Team id {team_id}:"
            lines.append(team_line)
            team_bans = bans_by_team.get(team_id, [])
            if team_bans:
                sorted_bans = sorted(team_bans, key=lambda x: x[0] or 0)
                for pick_turn, champ_label in sorted_bans:
                    pick_info = f"pick {pick_turn}" if pick_turn else "pick ?"
                    lines.append(f"- {champ_label} ({pick_info})")
            else:
                lines.append("- No bans listed")

    return lines, shared_pool


# Formats team members for HTML email, bolding the monitored username
def format_team_member_html(member_str: str, monitored_username: str) -> str:
    if not member_str:
        return ""

    # Extract username (everything before the first "(" if present)
    if " (" in member_str:
        username, rest = member_str.split(" (", 1)
        champion_part = f" ({rest}"
    else:
        username = member_str
        champion_part = ""

    # Bold the username if it matches the monitored user
    if username == monitored_username:
        username_html = f"<b>{html.escape(username)}</b>"
    else:
        username_html = html.escape(username)

    return username_html + html.escape(champion_part) if champion_part else username_html


# Formats team list for HTML email
def format_teams_html(teams_lines: List[str], monitored_username: str) -> str:
    if not teams_lines:
        return ""

    html_lines = []
    for line in teams_lines:
        if not line:
            html_lines.append("<br>")
        elif line.startswith("Team id "):
            # Team header - convert to HTML
            html_lines.append(f"<b>{html.escape(line)}</b><br>")
        elif line.startswith("- "):
            # Team member - bold username if it's the monitored user
            member_str = line[2:]  # Remove "- " prefix
            member_html = format_team_member_html(member_str, monitored_username)
            html_lines.append(f"- {member_html}<br>")
        else:
            html_lines.append(f"{html.escape(line)}<br>")

    return "".join(html_lines)


# Formats banned champions for HTML email
def format_banned_champions_html(ban_lines: List[str]) -> str:
    if not ban_lines:
        return ""

    html_lines = []
    for line in ban_lines:
        if not line:
            html_lines.append("<br>")
        elif line.startswith("Team id "):
            html_lines.append(f"<b>{html.escape(line)}</b><br>")
        else:
            html_lines.append(f"{html.escape(line)}<br>")

    return "".join(html_lines)


# Returns one Riot ID in the form the tool stores, rejecting anything that is not a name and a tag line
def normalize_riot_id(value):
    if isinstance(value, bool) or value is None:
        raise ValueError(RIOT_ID_INPUT_ERROR)
    name, separator, tag = str(value).strip().partition("#")
    name, tag = name.strip(), tag.strip()
    if not separator or not name or not tag or "#" in tag:
        raise ValueError(RIOT_ID_INPUT_ERROR)
    return f"{name}#{tag}"


# Returns one region code in the lower-case form the routing table is keyed by, so EUN1 and eun1 are the same region
def normalize_region(value):
    if isinstance(value, bool) or value is None:
        raise ValueError(REGION_INPUT_ERROR)
    text = str(value).strip().casefold()
    if not text:
        raise ValueError(REGION_INPUT_ERROR)
    return text


# Returns the routing continent for one region code, which the startup check guarantees is a known one
def region_continent(region):
    continent = REGION_TO_CONTINENT.get(region)
    if not continent:
        raise ValueError(f"'{region}' is not present in REGION_TO_CONTINENT")
    return continent


# Returns Riot game name & tag line for specified Riot ID
def get_user_riot_name_tag(riotid: str):

    try:
        riotid_name = riotid.split('#', 1)[0]
        riotid_tag = riotid.split('#', 1)[1]
    except IndexError:
        print_recovery_error(context="target", detail=RIOT_ID_INPUT_ERROR)
        return "", ""

    return riotid_name, riotid_tag


# Converts Riot ID to PUUID
async def get_user_puuid(riotid: str, region: str) -> Optional[str]:

    riotid_name, riotid_tag = get_user_riot_name_tag(riotid)

    debug_print("Riot account lookup", riot_id=riotid, region=region)
    async with riot_api_client() as client:
        try:
            account = await client.get_account_v1_by_riot_id(region=region_continent(region), game_name=riotid_name, tag_line=riotid_tag)
            puuid = account["puuid"]
            debug_print("Riot account lookup", riot_id=riotid, outcome="OK")
        except Exception as e:
            debug_swallowed_exception("Riot account lookup", e)
            print_recovery_error(e, context="target")
            puuid = None

    return puuid


# Gets summoner details
async def get_summoner_details(puuid: str, region: str):

    summoner_info = {
        "summoner_level": "N/A",
        "revision_date": "N/A"
    }

    debug_print("Summoner details", region=region)
    async with riot_api_client() as client:
        try:
            summoner = await client.get_lol_summoner_v4_by_puuid(region=region, puuid=puuid)

            summoner_info["summoner_level"] = str(summoner.get("summonerLevel", "N/A"))

            # revisionDate is in milliseconds
            revision_date_ts = summoner.get("revisionDate", 0)
            if revision_date_ts:
                revision_date = datetime.fromtimestamp(revision_date_ts / 1000)
                summoner_info["revision_date"] = get_date_from_ts(revision_date)

            debug_print("Summoner details", region=region, outcome="OK", level=summoner_info["summoner_level"])

        except Exception as e:
            debug_swallowed_exception("Summoner details", e)
            print(f"* Error while getting summoner details: {e}")

    return summoner_info


# Gets ranked information
async def get_ranked_info(puuid: str, region: str) -> RankedInfo:
    ranked_info: RankedInfo = {
        "solo_duo": {"tier": "N/A", "rank": "N/A", "lp": "N/A", "wins": 0, "losses": 0},
        "flex": {"tier": "N/A", "rank": "N/A", "lp": "N/A", "wins": 0, "losses": 0}
    }

    if not puuid or puuid == "N/A":
        return ranked_info

    debug_print("Ranked information", region=region)
    async with riot_api_client() as client:
        try:
            league_entries = await client.get_lol_league_v4_entries_by_puuid(region=region, puuid=puuid)

            if not league_entries:
                return ranked_info

            for entry in league_entries:
                queue_type = entry.get("queueType", "")
                tier = str(entry.get("tier", "UNRANKED"))
                rank = str(entry.get("rank", ""))
                lp = str(entry.get("leaguePoints", 0))
                wins = int(entry.get("wins", 0))
                losses = int(entry.get("losses", 0))

                if queue_type == "RANKED_SOLO_5x5":
                    ranked_info["solo_duo"] = {
                        "tier": tier,
                        "rank": rank,
                        "lp": lp,
                        "wins": wins,
                        "losses": losses
                    }
                elif queue_type == "RANKED_FLEX_SR":
                    ranked_info["flex"] = {
                        "tier": tier,
                        "rank": rank,
                        "lp": lp,
                        "wins": wins,
                        "losses": losses
                    }
            debug_print("Ranked information", region=region, outcome="OK", queues=len(league_entries))
        except Exception as e:
            # Player might not be ranked, this is not an error
            debug_swallowed_exception("Ranked information", e)

    return ranked_info


# Gets champion ID to name mapping from Data Dragon
_champion_id_to_name_cache = None


# Gets champion name from champion ID using Data Dragon
def get_champion_name(champion_id: int) -> Optional[str]:
    global _champion_id_to_name_cache

    if _champion_id_to_name_cache is None:
        _champion_id_to_name_cache = {}
        try:
            # Get latest Data Dragon version
            versions_response = req.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=5, verify=VERIFY_SSL)
            if versions_response.status_code == 200:
                versions = versions_response.json()
                latest_version = versions[0]

                # Get champion data
                champions_url = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/en_US/champion.json"
                champions_response = req.get(champions_url, timeout=5, verify=VERIFY_SSL)
                if champions_response.status_code == 200:
                    champions_data = champions_response.json().get("data", {})
                    for champion_name, champion_info in champions_data.items():
                        champ_id = int(champion_info.get("key", 0))
                        if champ_id:
                            _champion_id_to_name_cache[champ_id] = sanitize_untrusted_text(champion_name, max_length=64)
                # An empty cache means champion names stay numeric for the rest of the run, which is worth telling apart from a clean fetch
                debug_print("Data Dragon champion data", version=latest_version, outcome="OK" if _champion_id_to_name_cache else "degraded", champions=len(_champion_id_to_name_cache))
            else:
                debug_print("Data Dragon champion data", status=versions_response.status_code, outcome="degraded")
        except Exception as e:
            # If Data Dragon fails, this will return None
            debug_swallowed_exception("Data Dragon champion data", e)

    if not champion_id:
        return None

    return _champion_id_to_name_cache.get(champion_id)


# Returns name when available, otherwise fall back to numeric identifier
def format_named_value(name: Optional[str], identifier: Optional[int]) -> str:
    if name and name != "Unknown":
        return name

    if identifier is not None and identifier != 0:
        return str(identifier)

    return "Unknown"


# Gets champion mastery information
async def get_champion_mastery(puuid: str, region: str, top_n: int = 3):
    mastery_info = []

    if not puuid or puuid == "N/A":
        return mastery_info

    async with riot_api_client() as client:
        try:
            champion_masteries = await client.get_lol_champion_v4_top_masteries_by_puuid(region=region, puuid=puuid)

            if not champion_masteries:
                return mastery_info

            # Sort by mastery points and get top N
            sorted_masteries = sorted(champion_masteries, key=lambda x: x.get("championPoints", 0), reverse=True)[:top_n]

            for mastery in sorted_masteries:
                champion_id = mastery.get("championId", 0)
                champion_level = mastery.get("championLevel", 0)
                champion_points = mastery.get("championPoints", 0)
                champion_name = get_champion_name(champion_id)
                if not champion_name:
                    champion_name = str(champion_id) if champion_id else "Unknown"
                mastery_info.append({
                    "champion_id": champion_id,
                    "champion_name": champion_name,
                    "level": champion_level,
                    "points": champion_points
                })
            debug_print("Champion mastery", region=region, outcome="OK", champions=len(mastery_info))
        except Exception as e:
            # Champion mastery might not be available, this is not an error
            debug_swallowed_exception("Champion mastery", e)

    return mastery_info


# Checks if the player is currently in game
async def is_user_in_match(puuid: str, region: str):

    async with riot_api_client() as client:

        try:
            current_match = await client.get_lol_spectator_v5_active_game_by_summoner(region=region, puuid=puuid)
            debug_print("In-game check", region=region, outcome="OK", in_game=bool(current_match))
            return bool(current_match)
        except Exception as e:
            # Riot answers a player who is not in a game with a 404, so that is the ordinary path and anything
            # else is a check the run could not make but still treats as not in game
            debug_print("In-game check", region=region, outcome="OK" if recovery_http_status(e) == 404 else "degraded", in_game=False, error=f"{type(e).__name__}: {e}")
            return False


# Prints details of the current player's match (user is in game)
async def print_current_match(puuid: str, riotid_name: str, region: str, last_match_start_ts: int, last_match_stop_ts: int, status_notification_flag: bool):

    async with riot_api_client() as client:

        try:
            current_match = await client.get_lol_spectator_v5_active_game_by_summoner(region=region, puuid=puuid)
            debug_print("Live match details", region=region, outcome="OK")
        except Exception as e:
            debug_swallowed_exception("Live match details", e)
            current_match = False

        if current_match:

            match_id = current_match.get("gameId", 0)
            match_start_ts = int((current_match.get("gameStartTime", 0)) / 1000)
            match_duration = current_match.get("gameLength", 0)

            gamemode_raw = current_match.get("gameMode")
            gamemode = game_modes_mapping.get(gamemode_raw, gamemode_raw or "Unknown")
            queue_id = current_match.get("gameQueueConfigId")
            map_id = current_match.get("mapId")
            game_type_raw = current_match.get("gameType")
            game_type = humanize_game_type(game_type_raw)
            game_version_raw = current_match.get("gameVersion")
            game_version = format_game_version_label(game_version_raw)

            if queue_id is not None:
                queue_desc = format_named_value(game_queue_mapping.get(queue_id), queue_id)
            else:
                queue_desc = "Unknown"

            if map_id is not None:
                map_desc = format_named_value(map_id_mapping.get(map_id), map_id)
            else:
                map_desc = "Unknown"

            if match_start_ts < 1000000000:
                match_start_ts = int(time.time())

            print(f"*** LoL user {riotid_name} is in game now (after {calculate_timespan(match_start_ts, int(last_match_stop_ts))})\n")

            print(f"User played last time:\t\t{get_range_of_dates_from_tss(last_match_start_ts, last_match_stop_ts)}\n")

            print(f"Match ID:\t\t\t{match_id}")
            print(f"Game mode:\t\t\t{gamemode}")
            print(f"Queue:\t\t\t\t{queue_desc}")
            print(f"Map:\t\t\t\t{map_desc}")
            print(f"Game type:\t\t\t{game_type}")
            print(f"Game version:\t\t\t{game_version}")

            print(f"\nMatch start date:\t\t{get_date_from_ts(match_start_ts)}")

            if match_duration > 0:
                current_match_duration = display_time(int(match_duration))
            else:
                current_match_duration = "just starting ..."
                match_duration = 0

            print(f"Match duration:\t\t\t{current_match_duration}")

            current_teams = []
            detailed_teams = {}
            u_champion_id = 0
            u_champion_name = None
            u_teamid = None

            for p in current_match.get("participants", []):
                u_riotid = p.get("riotId")
                if u_riotid:
                    u_riotid_name = sanitize_untrusted_text(u_riotid.split('#', 1)[0], max_length=64)
                    # u_riotid_tag=u_riotid.split('#', 1)[1]
                else:
                    u_riotid_name = "unknown"

                p_teamid = p.get("teamId", 0)

                add_new_team_member(current_teams, p_teamid, u_riotid_name)

                champion_id = p.get("championId", 0)
                champion_name = get_champion_name(champion_id) if champion_id else None
                champion_display = format_named_value(champion_name, champion_id)

                member_display = u_riotid_name
                if champion_display != "Unknown":
                    member_display = f"{u_riotid_name} ({champion_display})"
                detailed_teams.setdefault(p_teamid, []).append(member_display)

                if u_riotid_name == riotid_name:
                    u_champion_id = champion_id
                    u_champion_name = champion_name
                    u_teamid = p_teamid

            champion_line = format_named_value(u_champion_name, u_champion_id)
            print(f"\nChampion:\t\t\t{champion_line}")

            current_teams_number = len(current_teams)
            print(f"Teams:\t\t\t\t{current_teams_number}")

            current_teams_str_lines = []
            for team_index, team in enumerate(current_teams):
                if team_index == 0:
                    print()
                else:
                    print()
                    current_teams_str_lines.append("")
                # Add star marker if this is the monitored user's team
                team_marker = " ⭐" if u_teamid is not None and team['id'] == u_teamid else ""
                teamid_str = f"Team id {team['id']}:{team_marker}"
                print(teamid_str)
                current_teams_str_lines.append(teamid_str)

                members_to_print = detailed_teams.get(team["id"], team["members"])
                for member in members_to_print:
                    member_str = f"- {member}"
                    current_teams_str_lines.append(member_str)
                    print(member_str)

            current_teams_str = "\n".join(current_teams_str_lines) + "\n" if current_teams_str_lines else ""

            banned_champions = current_match.get("bannedChampions") or []
            banned_champions_str = ""
            ban_lines = []
            if banned_champions:
                bans_by_team = {}
                for ban in banned_champions:
                    team_id = ban.get("teamId", 0)
                    champ_id = ban.get("championId", 0)
                    pick_turn = ban.get("pickTurn")
                    if champ_id and champ_id > 0:
                        champ_display = format_named_value(get_champion_name(champ_id), champ_id)
                    else:
                        champ_display = "No ban"
                    bans_by_team.setdefault(team_id, []).append((pick_turn, champ_display))

                ban_lines, shared_pool = format_banned_champions_output(bans_by_team)
                if ban_lines:
                    print("\nBanned champions:\n")
                    for line in ban_lines:
                        if line:
                            print(line)
                        else:
                            print()
                    banned_champions_str = "\n".join(ban_lines) + "\n"

            m_subject = f"LoL user {riotid_name} is in game now (after {calculate_timespan(match_start_ts, int(last_match_stop_ts), show_seconds=False)} - {get_short_date_from_ts(last_match_stop_ts)})"
            bans_email_section = f"\nBanned champions:\n\n{banned_champions_str}" if banned_champions_str else ""
            m_body = (
                f"LoL user {riotid_name} is in game now (after {calculate_timespan(match_start_ts, int(last_match_stop_ts))})\n\n"
                f"User played last time: {get_range_of_dates_from_tss(last_match_start_ts, last_match_stop_ts)}\n\n"
                f"Match ID: {match_id}\nGame mode: {gamemode}\nQueue: {queue_desc}\nMap: {map_desc}\nGame type: {game_type}\nGame version: {game_version}\n\n"
                f"Match start date: {get_date_from_ts(match_start_ts)}\nMatch duration: {current_match_duration}\n\n"
                f"Champion: {champion_line}\nTeams: {current_teams_number}\n\n{current_teams_str}{bans_email_section}"
                f"{get_cur_ts(nl_ch + 'Timestamp: ')}"
            )

            # HTML version
            bans_email_section_html = f"<br><b>Banned champions:</b><br><br>{format_banned_champions_html(ban_lines)}" if banned_champions_str else ""
            current_teams_html = format_teams_html(current_teams_str_lines, riotid_name)
            timespan_str = calculate_timespan(match_start_ts, int(last_match_stop_ts))
            m_body_html = (
                f"<html><head></head><body>"
                f"LoL user <b>{html.escape(riotid_name)}</b> is in game now (after <b>{html.escape(timespan_str)}</b>)<br><br>"
                f"User played last time: <b>{html.escape(get_range_of_dates_from_tss(last_match_start_ts, last_match_stop_ts))}</b><br><br>"
                f"Match ID: {html.escape(str(match_id))}<br>"
                f"Game mode: <b>{html.escape(gamemode)}</b><br>"
                f"Queue: {html.escape(queue_desc)}<br>"
                f"Map: {html.escape(map_desc)}<br>"
                f"Game type: {html.escape(game_type)}<br>"
                f"Game version: {html.escape(game_version)}<br><br>"
                f"Match start date: <b>{html.escape(get_date_from_ts(match_start_ts))}</b><br>"
                f"Match duration: {html.escape(current_match_duration)}<br><br>"
                f"Champion: <b>{html.escape(champion_line)}</b><br>"
                f"Teams: {current_teams_number}<br><br>"
                f"{current_teams_html}{bans_email_section_html}"
                f"{get_cur_ts('<br>Timestamp: ')}"
                f"</body></html>"
            )

            if status_notification_flag:
                print(f"Sending email notification to {RECEIVER_EMAIL}")
                send_email(m_subject, m_body, m_body_html, SMTP_SSL)

            return match_start_ts
        else:
            print("User is not in game currently")
            return 0


# Gets recent match IDs
async def get_latest_match_ids(puuid: str, region: str, count: int = 10, start: int = 0) -> list:
    """
    Fetches match IDs from Riot API with pagination support.
    The Riot API has a maximum limit of 100 matches per request.
    For requests > 100, this function automatically paginates.

    Args:
        puuid: Player's PUUID
        region: Region code
        count: Number of matches to fetch
        start: Starting index (0-based, where 0 is the newest match)
    """
    MAX_MATCHES_PER_REQUEST = 100
    all_matches = []

    debug_print("Match ID fetch", region=region, start=start, count=count)
    try:
        async with riot_api_client() as client:
            # If count <= 100, make a single request
            if count <= MAX_MATCHES_PER_REQUEST:
                matches = await client.get_lol_match_v5_match_ids_by_puuid(
                    region=region_continent(region),
                    puuid=puuid,
                    queries={'start': start, 'count': count}
                )
                debug_print("Match ID fetch", region=region, outcome="OK", matches=len(matches or []))
                return matches if matches else []

            # For counts > 100, paginate with multiple requests
            current_start = start
            remaining = count

            while remaining > 0:
                # Request up to MAX_MATCHES_PER_REQUEST matches per call
                request_count = min(remaining, MAX_MATCHES_PER_REQUEST)

                matches = await client.get_lol_match_v5_match_ids_by_puuid(
                    region=region_continent(region),
                    puuid=puuid,
                    queries={'start': current_start, 'count': request_count}
                )

                if not matches:
                    # No more matches available
                    break

                all_matches.extend(matches)

                # If we got fewer matches than requested, we've reached the end
                if len(matches) < request_count:
                    break

                current_start += len(matches)
                remaining -= len(matches)

            debug_print("Match ID fetch", region=region, outcome="OK", matches=len(all_matches[:count]), pages=True)
            return all_matches[:count]  # Return exactly the requested count (or less if not available)

    except Exception as e:
        debug_swallowed_exception("Match ID fetch", e)
        print(f"* Error: Cannot fetch latest match IDs: {e}")
        print_cur_ts("Timestamp:\t\t\t")
        return []


# Fetches all available match IDs to determine total count
async def get_total_match_count(puuid: str, region: str) -> int:
    MAX_MATCHES_PER_REQUEST = 100
    all_matches = []
    start = 0

    debug_print("Total match count", region=region)
    try:
        async with riot_api_client() as client:
            while True:
                matches = await client.get_lol_match_v5_match_ids_by_puuid(
                    region=region_continent(region),
                    puuid=puuid,
                    queries={'start': start, 'count': MAX_MATCHES_PER_REQUEST}
                )

                if not matches:
                    break

                all_matches.extend(matches)

                # If we got fewer than requested, we've reached the end
                if len(matches) < MAX_MATCHES_PER_REQUEST:
                    break

                start += len(matches)

            debug_print("Total match count", region=region, outcome="OK", matches=len(all_matches))
            return len(all_matches)

    except Exception as e:
        debug_swallowed_exception("Total match count", e)
        print(f"* Error: Cannot determine total match count: {e}")
        return 0


# Processes and prints details for a single match id, handling forbidden matches
async def process_and_print_single_match(match_id: str, puuid: str, riotid_name: str, region: str, status_notification_flag: bool, csv_file_name: Optional[str], cached_match_data: Optional[Any] = None) -> tuple[int, int]:

    # Use cached match data if provided, otherwise fetch it
    if cached_match_data:
        match = cached_match_data
    else:
        debug_print("Match details", match=match_id, region=region)
        async with riot_api_client() as client:
            try:
                match = await client.get_lol_match_v5_match(region=region_continent(region), id=match_id)
                debug_print("Match details", match=match_id, outcome="OK")
            except Exception as e:
                if getattr(e, 'status', None) == 403:
                    debug_print("Match details", match=match_id, outcome="skipped", reason="requires an RSO token")
                    if INCLUDE_FORBIDDEN_MATCHES:
                        print(f"Match ID:\t\t\t{match_id}")
                        print(f"Match details require RSO token")
                        if status_notification_flag:
                            m_subject = f"LoL user {riotid_name} new forbidden match detected"
                            m_body = (f"LoL user {riotid_name} finished a forbidden match whose details are protected (requires RSO token)\n\nMatch ID: {match_id}\n{get_cur_ts(nl_ch + 'Timestamp: ')}")
                            m_body_html = (
                                f"<html><head></head><body>"
                                f"LoL user <b>{html.escape(riotid_name)}</b> finished a forbidden match whose details are protected (requires RSO token)<br><br>"
                                f"Match ID: {html.escape(str(match_id))}<br>"
                                f"{get_cur_ts('<br>Timestamp: ')}"
                                f"</body></html>"
                            )
                            print(f"\nSending email notification to {RECEIVER_EMAIL}")
                            send_email(m_subject, m_body, m_body_html, SMTP_SSL)
                    return 0, 0
                else:
                    debug_swallowed_exception("Match details", e)
                    print(f"* An unexpected error occurred while processing match {match_id}: {e}")
                    return 0, 0

    try:
        match_info = match.get("info", {})

        match_start_ts = int(match_info.get("gameStartTimestamp", 0) / 1000)
        match_stop_ts = int(match_info.get("gameEndTimestamp", 0) / 1000)
        match_creation_ts = int(match_info.get("gameCreation", 0) / 1000)
        match_duration = match_info.get("gameDuration", 0)
        gamemode = game_modes_mapping.get(match_info.get("gameMode"), match_info.get("gameMode"))
        queue_id = match_info.get("queueId")
        map_id = match_info.get("mapId")
        match_type_raw = match_info.get("gameType") or match_info.get("matchType")
        match_type = humanize_game_type(match_type_raw)
        game_version = format_game_version_label(match_info.get("gameVersion"))

        if queue_id is not None:
            queue_desc = format_named_value(game_queue_mapping.get(queue_id), queue_id)
        else:
            queue_desc = "Unknown"

        if map_id is not None:
            map_desc = format_named_value(map_id_mapping.get(map_id), map_id)
        else:
            map_desc = "Unknown"

        print(f"Match ID:\t\t\t{match_id}")
        print(f"Game mode:\t\t\t{gamemode}")
        print(f"Queue:\t\t\t\t{queue_desc}")
        print(f"Map:\t\t\t\t{map_desc}")
        print(f"Game type:\t\t\t{match_type}")
        print(f"Game version:\t\t\t{game_version}")
        print(f"\nMatch start-end date:\t\t{get_range_of_dates_from_tss(match_start_ts, match_stop_ts)}")
        print(f"Match creation:\t\t\t{get_date_from_ts(match_creation_ts)}")
        print(f"Match duration:\t\t\t{display_time(int(match_duration))}")

        last_played = calculate_timespan(int(time.time()), match_stop_ts)
        print(f"\nMatch finished:\t\t\t{last_played} ago")

        teams = []
        team_roster_details = {}
        user_participant = None

        for p in match_info.get("participants", []):
            if p.get("puuid") == puuid:
                user_participant = p

            p_riotid_name = get_participant_display_name(p)
            p_teamid = p.get("teamId", 0)
            champion_played_name = p.get("championName")
            champion_played_id = p.get("championId")
            champion_display = format_named_value(champion_played_name, champion_played_id)
            add_new_team_member(teams, p_teamid, p_riotid_name)
            if champion_display != "Unknown":
                team_roster_details.setdefault(p_teamid, []).append(f"{p_riotid_name} ({champion_display})")
            else:
                team_roster_details.setdefault(p_teamid, []).append(p_riotid_name)

        u_victory = "No"
        u_champion_name, u_level, u_role, u_lane = "N/A", "N/A", "N/A", "N/A"
        u_champion_id = None
        u_kills, u_deaths, u_assists = 0, 0, 0
        u_teamid = None
        if user_participant:
            u_victory = "Yes" if user_participant.get("win", False) else "No"
            u_champion_name = user_participant.get("championName")
            u_champion_id = user_participant.get("championId")
            u_kills = user_participant.get("kills", 0)
            u_deaths = user_participant.get("deaths", 0)
            u_assists = user_participant.get("assists", 0)
            u_level = user_participant.get("champLevel")
            u_role = user_participant.get("role")
            u_lane = user_participant.get("lane")
            u_teamid = user_participant.get("teamId")

        print(f"\nVictory:\t\t\t{u_victory}")
        print(f"Kills/Deaths/Assists:\t\t{u_kills}/{u_deaths}/{u_assists}")

        u_champion_display = format_named_value(u_champion_name, u_champion_id)
        print(f"\nChampion:\t\t\t{u_champion_display}")

        print(f"Level:\t\t\t\t{u_level}")

        if u_role and u_role != "NONE":
            print(f"Role:\t\t\t\t{u_role}")

        if u_lane and u_lane != "NONE":
            print(f"Lane:\t\t\t\t{u_lane}")

        print(f"Teams:\t\t\t\t{len(teams)}")
        teams_lines = []
        for team_index, team in enumerate(teams):
            if team_index == 0:
                print()
            else:
                print()
                teams_lines.append("")
            # Add star marker if this is the monitored user's team
            team_marker = " ⭐" if u_teamid is not None and team["id"] == u_teamid else ""
            team_header = f'Team id {team["id"]}:{team_marker}'
            print(team_header)
            teams_lines.append(team_header)
            members_to_print = team_roster_details.get(team["id"], team["members"])
            for member in members_to_print:
                detail_line = f"- {member}"
                print(detail_line)
                teams_lines.append(detail_line)
        teams_detailed_str = "\n".join(teams_lines) + "\n" if teams_lines else ""

        banned_champions_email_str = ""
        ban_lines = []
        match_team_data = match_info.get("teams", [])
        if match_team_data:
            team_bans_dict = {}
            for team in match_team_data:
                team_id = team.get("teamId", 0)
                team_bans = []
                for ban in team.get("bans", []):
                    champ_id = ban.get("championId", 0)
                    pick_turn = ban.get("pickTurn")
                    if champ_id and champ_id > 0:
                        champ_display = format_named_value(get_champion_name(champ_id), champ_id)
                    else:
                        champ_display = "No ban"
                    team_bans.append((pick_turn, champ_display))
                team_bans_dict[team_id] = team_bans

            ban_lines, shared_pool = format_banned_champions_output(team_bans_dict)
            if ban_lines:
                print("\nBanned champions:\n")
                for line in ban_lines:
                    if line:
                        print(line)
                    else:
                        print()
                banned_champions_email_str = "\n".join(ban_lines) + "\n"
        if csv_file_name:
            try:
                team1_str = " ".join(f"'{p}'" for p in teams[0]["members"]) if len(teams) > 0 else ""
                team2_str = " ".join(f"'{p}'" for p in teams[1]["members"]) if len(teams) > 1 else ""
                # Convert None values to "N/A" for CSV
                csv_level = u_level if u_level is not None else "N/A"
                csv_role = u_role if (u_role is not None and u_role != "NONE") else "N/A"
                csv_lane = u_lane if (u_lane is not None and u_lane != "NONE") else "N/A"
                write_csv_entry(csv_file_name, str(datetime.fromtimestamp(match_start_ts)), str(datetime.fromtimestamp(match_stop_ts)), display_time(int(match_duration)), gamemode, u_victory, u_kills, u_deaths, u_assists, u_champion_display, csv_level, csv_role, csv_lane, team1_str, team2_str)
            except Exception as e:
                print(f"* Error: {e}")

        if status_notification_flag:
            teams_str = teams_detailed_str if teams_detailed_str else ""

            u_role_str = f"{nl_ch}Role: {u_role}" if u_role and u_role != "NONE" else ""
            u_lane_str = f"{nl_ch}Lane: {u_lane}" if u_lane and u_lane != "NONE" else ""

            bans_email_section = f"\nBanned champions:\n\n{banned_champions_email_str}" if banned_champions_email_str else ""

            m_subject = f"LoL user {riotid_name} match summary ({get_range_of_dates_from_tss(match_start_ts, match_stop_ts, short=True)}, {display_time(int(match_duration), granularity=1)}, {u_victory})"
            m_body = (
                f"LoL user {riotid_name} last match summary\n\n"
                f"Match ID: {match_id}\nGame mode: {gamemode}\nQueue: {queue_desc}\nMap: {map_desc}\nGame type: {match_type}\nGame version: {game_version}\n\n"
                f"Match start-end date: {get_range_of_dates_from_tss(match_start_ts, match_stop_ts)}\nMatch creation: {get_date_from_ts(match_creation_ts)}\nMatch duration: {display_time(int(match_duration))}\n\n"
                f"Victory: {u_victory}\nKills/deaths/assists: {u_kills}/{u_deaths}/{u_assists}\n\n"
                f"Champion: {u_champion_display}\nLevel: {u_level}{u_role_str}{u_lane_str}\nTeams: {len(teams)}\n\n"
                f"{teams_str}{bans_email_section}"
                f"{get_cur_ts(nl_ch + 'Timestamp: ')}"
            )

            # HTML version
            u_role_str_html = f"<br>Role: {html.escape(u_role)}" if u_role and u_role != "NONE" else ""
            u_lane_str_html = f"<br>Lane: {html.escape(u_lane)}" if u_lane and u_lane != "NONE" else ""
            bans_email_section_html = f"<br><b>Banned champions:</b><br><br>{format_banned_champions_html(ban_lines)}" if banned_champions_email_str else ""
            teams_html = format_teams_html(teams_lines, riotid_name)
            m_body_html = (
                f"<html><head></head><body>"
                f"LoL user <b>{html.escape(riotid_name)}</b> last match summary<br><br>"
                f"Match ID: {html.escape(str(match_id))}<br>"
                f"Game mode: <b>{html.escape(gamemode)}</b><br>"
                f"Queue: {html.escape(queue_desc)}<br>"
                f"Map: {html.escape(map_desc)}<br>"
                f"Game type: {html.escape(match_type)}<br>"
                f"Game version: {html.escape(game_version)}<br><br>"
                f"Match start-end date: <b>{html.escape(get_range_of_dates_from_tss(match_start_ts, match_stop_ts))}</b><br>"
                f"Match creation: {html.escape(get_date_from_ts(match_creation_ts))}<br>"
                f"Match duration: <b>{html.escape(display_time(int(match_duration)))}</b><br><br>"
                f"Victory: <b>{html.escape(u_victory)}</b><br>"
                f"Kills/deaths/assists: <b>{u_kills}/{u_deaths}/{u_assists}</b><br><br>"
                f"Champion: <b>{html.escape(u_champion_display)}</b><br>"
                f"Level: {html.escape(str(u_level))}{u_role_str_html}{u_lane_str_html}<br>"
                f"Teams: {len(teams)}<br><br>"
                f"{teams_html}{bans_email_section_html}"
                f"{get_cur_ts('<br>Timestamp: ')}"
                f"</body></html>"
            )
            print(f"\nSending email notification to {RECEIVER_EMAIL}")
            send_email(m_subject, m_body, m_body_html, SMTP_SSL)

        return match_start_ts, match_stop_ts

    except Exception as e:
        if getattr(e, 'status', None) == 403:
            if INCLUDE_FORBIDDEN_MATCHES:
                print(f"Match ID:\t\t\t{match_id}")
                print(f"Match details require RSO token")
                if status_notification_flag:
                    m_subject = f"LoL user {riotid_name} new forbidden match detected"

                    m_body = (f"LoL user {riotid_name} finished a forbidden match whose details are protected (requires RSO token)\n\nMatch ID: {match_id}\n{get_cur_ts(nl_ch + 'Timestamp: ')}")
                    m_body_html = (
                        f"<html><head></head><body>"
                        f"LoL user <b>{html.escape(riotid_name)}</b> finished a forbidden match whose details are protected (requires RSO token)<br><br>"
                        f"Match ID: <b>{html.escape(str(match_id))}</b><br>"
                        f"{get_cur_ts('<br>Timestamp: ')}"
                        f"</body></html>"
                    )
                    print(f"\nSending email notification to {RECEIVER_EMAIL}")
                    send_email(m_subject, m_body, m_body_html, SMTP_SSL)
        else:
            print(f"* An unexpected error occurred while processing match {match_id}: {e}")

        return 0, 0


# Prints history of matches with relevant details
async def print_match_history(puuid: str, riotid_name: str, region: str, matches_min: int, matches_num: int, csv_file_name):

    if matches_min > matches_num:
        return 0, 0

    # Convert 1-based match numbers to 0-based indices
    # Match #1 (newest) = index 0, Match #101 = index 100
    start_index = matches_min - 1
    range_size = matches_num - matches_min + 1

    # First, fetch all match IDs
    print(f"* Fetching match IDs ({range_size} matches)...")
    all_fetched_ids = await get_latest_match_ids(puuid, region, count=range_size, start=start_index)

    if not all_fetched_ids:
        print("* Error: No match history found")
        return 0, 0

    # Reverse immediately so we process oldest to newest
    # The API returns newest to oldest, so reversing gives us oldest first
    all_fetched_ids = list(reversed(all_fetched_ids))

    print(f"* Processing matches in batches of 10 (oldest to newest)...\n")

    last_start_ts, last_stop_ts = 0, 0
    BATCH_SIZE = 10
    processed_count = 0
    accessible_match_ids = []

    async with riot_api_client() as client:
        # Process in batches
        for batch_start in range(0, len(all_fetched_ids), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(all_fetched_ids))
            batch_ids = all_fetched_ids[batch_start:batch_end]

            # Fetch and process this batch
            for match_id in batch_ids:
                try:
                    # Fetch match details
                    match = await client.get_lol_match_v5_match(region=region_continent(region), id=match_id)

                    # Calculate match number
                    # Since we reversed the list, oldest is at index 0
                    # Match numbers go from matches_num (oldest) down to matches_min (newest)
                    match_index_in_reversed = all_fetched_ids.index(match_id)
                    match_number = matches_num - match_index_in_reversed

                    print(f"Match number:\t\t\t{match_number}\n")

                    # Process and display (this also writes to CSV)
                    start_ts, stop_ts = await process_and_print_single_match(match_id, puuid, riotid_name, region, False, csv_file_name, cached_match_data=match)

                    print("─" * HORIZONTAL_LINE)

                    accessible_match_ids.append(match_id)
                    processed_count += 1

                    # Track the last match for return value (newest match in the range)
                    if match_index_in_reversed == len(all_fetched_ids) - 1:
                        last_start_ts, last_stop_ts = start_ts, stop_ts

                except Exception as e:
                    if getattr(e, 'status', None) == 403:  # Forbidden match
                        if INCLUDE_FORBIDDEN_MATCHES:
                            match_index_in_reversed = all_fetched_ids.index(match_id)
                            match_number = matches_num - match_index_in_reversed
                            print(f"Match number:\t\t\t{match_number}\n")
                            print(f"Match ID:\t\t\t{match_id}")
                            print(f"Match details require RSO token\n")
                            print("─" * HORIZONTAL_LINE)
                            accessible_match_ids.append(match_id)
                            processed_count += 1
                    else:
                        print(f"* Warning: Error processing match {match_id}: {e}")

    if len(accessible_match_ids) < range_size:
        print(f"* Warning: Not enough displayable matches found. Requested {range_size} matches (from #{matches_min} to #{matches_num}), found: {len(accessible_match_ids)}")

    return last_start_ts, last_stop_ts


# Prints last n matches for the user
async def print_save_recent_matches(riotid: str, region: str, matches_min: int, matches_num: int, csv_file_name):

    try:
        if csv_file_name:
            init_csv_file(csv_file_name)
    except Exception as e:
        print_recovery_error(e, context="file")

    puuid = await get_user_puuid(riotid, region)
    riotid_name, riotid_tag = get_user_riot_name_tag(riotid)

    if puuid:
        await print_match_history(puuid, riotid_name, region, matches_min, matches_num, csv_file_name)


# Finds an optional config file
def find_config_file(cli_path=None):
    """
    Search for an optional config file in:
      1) CLI-provided path (must exist if given)
      2) ./{DEFAULT_CONFIG_FILENAME}
      3) ~/.{DEFAULT_CONFIG_FILENAME}
      4) script-directory/{DEFAULT_CONFIG_FILENAME}
    """

    if cli_path:
        p = Path(os.path.expanduser(cli_path))
        return str(p) if p.is_file() else None

    candidates = [
        Path.cwd() / DEFAULT_CONFIG_FILENAME,
        Path.home() / f".{DEFAULT_CONFIG_FILENAME}",
        Path(__file__).parent / DEFAULT_CONFIG_FILENAME,
    ]

    for p in candidates:
        if p.is_file():
            return str(p)
    return None


# Settings an older version wrote that this version no longer defines, ignored instead of rejected
RETIRED_CONFIG_SETTINGS = frozenset(("LOL_HANGED_INGAME_INTERVAL", ))


# Collects the setting names the built-in configuration template defines
def _config_allowed_names():
    template_tree = ast.parse(CONFIG_BLOCK, "<built-in-config>", "exec")
    return frozenset(statement.targets[0].id for statement in template_tree.body if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name))


# Parses allowlisted literal config assignments without executing any file content
def parse_config_content(content, filename="<config>", retired_out=None, reference_values=None):
    tree = ast.parse(content, filename, "exec")
    allowed_names = _config_allowed_names()
    parsed_values = {}
    for statement in tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
            raise ValueError(f"Line {getattr(statement, 'lineno', '?')}: only NAME = value assignments are allowed")
        name = statement.targets[0].id
        if name in RETIRED_CONFIG_SETTINGS and name not in allowed_names:
            if retired_out is not None and name not in retired_out:
                retired_out.append(name)
            continue
        if name not in allowed_names:
            raise ValueError(f"Line {statement.lineno}: unsupported configuration setting {name!r}")
        # One setting may reuse another, which the built-in template does and existing configs copy
        if isinstance(statement.value, ast.Name):
            referenced = statement.value.id
            if referenced not in allowed_names:
                raise ValueError(f"Line {statement.lineno}: {name} may only reference another configuration setting")
            source = parsed_values if referenced in parsed_values else (reference_values if reference_values is not None else globals())
            if referenced not in source:
                raise ValueError(f"Line {statement.lineno}: {name} references {referenced!r} before it has a value")
            parsed_values[name] = source[referenced]
            continue
        try:
            parsed_values[name] = ast.literal_eval(statement.value)
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError) as exc:
            raise ValueError(f"Line {statement.lineno}: {name} must be a plain value such as a number, string, True, False, None, list, tuple or dict") from exc
    return parsed_values


# Validates config content through the same restricted parser used at startup
def validate_config_content(content, filename="<generated-config>"):
    parse_config_content(content, filename)

# Reports settings an older version wrote that this version no longer defines
def describe_retired_settings(names, quoted_path):
    listed = ", ".join(sorted(names))
    return f"Config file {quoted_path} contains settings this version no longer uses, which were ignored: {listed}"


# Loads a config file as data and applies only recognized literal settings
def load_config_file(config_path, namespace=None, report_errors=True):
    selected_namespace = globals() if namespace is None else namespace
    retired_settings = []
    try:
        content = Path(config_path).read_text(encoding="utf-8")
        # Parsed as data rather than executed, so a config file picked up from the working directory cannot run code
        parsed_values = parse_config_content(content, str(config_path), retired_settings)
        selected_namespace.update(parsed_values)
        if retired_settings and report_errors:
            print(f"* Note: {describe_retired_settings(retired_settings, chr(39) + str(config_path) + chr(39))}")
        return True
    except SyntaxError as exc:
        detail = f"Config file '{config_path}' has invalid Python syntax"
        if exc.lineno is not None:
            detail += f" at line {exc.lineno}"
        if exc.text:
            detail += f" | Source: {exc.text.rstrip()}"
        detail += f" | Parser: {exc.msg}"
    # Checked before ValueError because UnicodeDecodeError derives from it
    except UnicodeDecodeError:
        detail = f"Config file '{config_path}' is not valid UTF-8"
    except ValueError as exc:
        detail = f"Config file '{config_path}' contains unsupported content: {exc}"
    except Exception as exc:
        detail = f"Config file '{config_path}' failed with {type(exc).__name__}: {exc}"
    if report_errors:
        print_recovery_error(context="config", detail=detail)
    return False


# Resolves an executable path by checking if it's a valid file or searching in $PATH
def resolve_executable(path):
    if os.path.isfile(path) and os.access(path, os.X_OK):
        return path

    found = shutil.which(path)
    if found:
        return found

    raise FileNotFoundError(f"Could not find executable '{path}'")


# Returns a compact snapshot of the current live match with mode, start_ts, and participants
async def get_current_match_details(puuid: str, region: str) -> dict:
    async with riot_api_client() as client:
        try:
            current_match = await client.get_lol_spectator_v5_active_game_by_summoner(region=region, puuid=puuid)
            debug_print("Live match snapshot", region=region, outcome="OK")
        except Exception as e:
            debug_swallowed_exception("Live match snapshot", e)
            return {}

    if not current_match:
        return {}

    gamemode_raw = current_match.get("gameMode")
    gamemode_raw = sanitize_untrusted_text(gamemode_raw, max_length=64) or gamemode_raw
    gamemode = game_modes_mapping.get(gamemode_raw, gamemode_raw)

    start_ts = int((current_match.get("gameStartTime", 0)) / 1000)
    if start_ts < 1000000000:
        start_ts = int(time.time())

    participants = []
    for p in current_match.get("participants", []):
        riot_id = p.get("riotId")
        if riot_id:
            riotid_name = sanitize_untrusted_text(riot_id.split("#", 1)[0], max_length=64)
        else:
            riotid_name = sanitize_untrusted_text(p.get("riotIdGameName") or p.get("summonerName"), max_length=64) or "Unknown Player"

        participants.append({
            "riotIdName": riotid_name,
            "teamId": p.get("teamId", 0),
            "championId": p.get("championId", 0),
        })

    game_type_raw = current_match.get("gameType")

    return {
        "mode": gamemode,
        "mode_raw": gamemode_raw,
        "game_type": game_type_raw,
        "start_ts": start_ts,
        "participants": participants,
    }


# Append a CSV row from a live snapshot for custom game matches that never show up in match history
async def save_custom_match_to_csv(snapshot: dict, riotid_name: str, start_ts: int, stop_ts: int, csv_file_name: str) -> None:
    if not csv_file_name or not snapshot:
        return

    snap_start = int(snapshot.get('start_ts') or 0)
    if snap_start:
        start_ts = snap_start

    start_dt_str = str(datetime.fromtimestamp(start_ts)) if start_ts else ""

    stop_dt_str = str(datetime.fromtimestamp(stop_ts)) if stop_ts else ""
    duration_sec = max(0, (stop_ts or 0) - (start_ts or 0))
    duration_str = display_time(int(duration_sec))

    teams_map = {}  # teamId -> [names]
    for p in snapshot.get("participants", []):
        t = p.get("teamId", 0)
        teams_map.setdefault(t, []).append(p.get("riotIdName", "Unknown Player"))

    team_ids_sorted = sorted(teams_map.keys())
    team1_members = teams_map.get(team_ids_sorted[0], []) if team_ids_sorted else []
    team2_members = teams_map.get(team_ids_sorted[1], []) if len(team_ids_sorted) > 1 else []

    team1_str = " ".join(f"'{n}'" for n in team1_members)
    team2_str = " ".join(f"'{n}'" for n in team2_members)

    user_champion = "N/A"
    for p in snapshot.get("participants", []):
        if p.get("riotIdName") == riotid_name:
            user_champion = p.get("championId", "N/A")
            break

    victory = "N/A"
    kills = "N/A"
    deaths = "N/A"
    assists = "N/A"
    level = "N/A"
    role = "N/A"
    lane = "N/A"
    game_mode = snapshot.get('mode', 'N/A')

    write_csv_entry(csv_file_name=csv_file_name, start_date_ts=start_dt_str, stop_date_ts=stop_dt_str, duration_ts=duration_str, game_mode=game_mode, victory=victory, kills=kills, deaths=deaths, assists=assists, champion=user_champion, level=level, role=role, lane=lane, team1=team1_str, team2=team2_str)


# Main function that monitors gaming activity of the specified LoL user
async def lol_monitor_user(riotid, region, csv_file_name):

    alive_counter = 0
    last_match_start_ts = 0
    last_match_stop_ts = 0
    puuid = None
    riotid_name = ""
    started_announced = False
    hint_tracker = RecoveryHintTracker()

    try:
        if csv_file_name:
            init_csv_file(csv_file_name)
    except Exception as e:
        print_recovery_error(e, context="file")

    puuid = await get_user_puuid(riotid, region)

    if not puuid:
        sys.exit(2)

    riotid_name, riotid_tag = get_user_riot_name_tag(riotid)

    summoner_info = {}
    ranked_info: RankedInfo = {
        "solo_duo": {"tier": "N/A", "rank": "N/A", "lp": "N/A", "wins": 0, "losses": 0},
        "flex": {"tier": "N/A", "rank": "N/A", "lp": "N/A", "wins": 0, "losses": 0},
    }
    mastery_info = []

    try:
        summoner_info = await get_summoner_details(puuid, region)
    except Exception as e:
        print(f"* Warning: Could not fetch summoner details: {e}")
        summoner_info = {"summoner_level": "N/A", "revision_date": "N/A"}

    try:
        ranked_info = await get_ranked_info(puuid, region)
    except Exception as e:
        print(f"* Warning: Could not fetch ranked information: {e}")
        ranked_info = {
            "solo_duo": {"tier": "N/A", "rank": "N/A", "lp": "N/A", "wins": 0, "losses": 0},
            "flex": {"tier": "N/A", "rank": "N/A", "lp": "N/A", "wins": 0, "losses": 0},
        }

    try:
        mastery_info = await get_champion_mastery(puuid, region, top_n=3)
    except Exception as e:
        print(f"* Warning: Could not fetch champion mastery: {e}")

    print(f"Riot ID (name#tag):\t\t{riotid}")
    print(f"Riot PUUID:\t\t\t{puuid}")
    print(f"Summoner level:\t\t\t{summoner_info.get('summoner_level', 'N/A')}")
    print(f"Last modified:\t\t\t{summoner_info.get('revision_date', 'N/A')}")

    print("─" * HORIZONTAL_LINE)

    print("Ranked Information:\n")

    solo = ranked_info.get("solo_duo", {})
    if solo.get("tier") != "N/A" and solo.get("tier") != "UNRANKED":
        solo_wins = solo.get("wins", 0)
        solo_losses = solo.get("losses", 0)
        solo_total = solo_wins + solo_losses
        solo_wr = f"{(solo_wins / solo_total * 100):.1f}%" if solo_total > 0 else "N/A"
        print(f"Solo/Duo:\t\t\t{solo.get('tier', 'N/A')} {solo.get('rank', 'N/A')} ({solo.get('lp', 'N/A')} LP) - Wins: {solo_wins} / Losses: {solo_losses} (Winrate: {solo_wr})")
    else:
        print(f"Solo/Duo:\t\t\tUnranked")

    flex = ranked_info.get("flex", {})
    if flex.get("tier") != "N/A" and flex.get("tier") != "UNRANKED":
        flex_wins = flex.get("wins", 0)
        flex_losses = flex.get("losses", 0)
        flex_total = flex_wins + flex_losses
        flex_wr = f"{(flex_wins / flex_total * 100):.1f}%" if flex_total > 0 else "N/A"
        print(f"Flex:\t\t\t\t{flex.get('tier', 'N/A')} {flex.get('rank', 'N/A')} ({flex.get('lp', 'N/A')} LP) - Wins: {flex_wins} / Losses: {flex_losses} (Winrate: {flex_wr})")
    else:
        print(f"Flex:\t\t\t\tUnranked")

    if mastery_info:
        print("─" * HORIZONTAL_LINE)
        print(f"Top Champion Mastery:\t\t")
        for i, mastery in enumerate(mastery_info, 1):
            champion_name = mastery.get("champion_name", "Unknown")
            level = mastery.get("level", 0)
            points = mastery.get("points", 0)
            # Format points with commas for readability
            points_str = f"{points:,}" if points > 0 else "0"
            name_label = f"{i}. {champion_name}:"
            print(f"\t\t\t\t{name_label:<20} Level {level} ({points_str} points)")

    print("─" * HORIZONTAL_LINE)

    processed_match_ids = set()
    initial_match_ids = []

    CUSTOM_SAVE_DELAY = LOL_ACTIVE_CHECK_INTERVAL * 2
    current_custom_snapshot = None
    current_match_start_ts = 0
    pending_custom = None

    try:
        initial_match_ids = await get_latest_match_ids(puuid, region, count=20)
    except Exception as e:
        print(f"* Warning: Could not fetch initial match history due to an error: {e}")
        print("* The tool will start with no history and detect the first new match played")

    if initial_match_ids:
        processed_match_ids.update(initial_match_ids)
        print("User last played match:\n")
        try:
            last_match_start_ts, last_match_stop_ts = await process_and_print_single_match(initial_match_ids[0], puuid, riotid_name, region, False, None)
        except Exception as e:
            print(f"* Warning: Could not display details for the last known match: {e}")
    else:
        print("* Warning: Could not fetch initial match history. Will detect first new match played")

    ingame = False
    ingame_old = False
    game_finished_ts = 0
    email_sent = False

    print_cur_ts("\nTimestamp:\t\t\t")

    check_count = 0

    while True:

        try:

            processed_new_match_in_this_cycle = False
            check_count += 1
            debug_print("Monitoring check", check=f"#{check_count}", user=riotid, in_game=ingame)

            latest_match_ids = await get_latest_match_ids(puuid, region, count=10)

            if latest_match_ids:

                new_match_ids = [mid for mid in latest_match_ids if mid not in processed_match_ids]

                if new_match_ids:
                    print(f"*** Found {len(new_match_ids)} new completed match(es)")
                    # Any completion arriving cancels a pending custom game save (assume it corresponds to the last stop)
                    if pending_custom:
                        pending_custom = None
                        current_custom_snapshot = None
                        current_match_start_ts = 0

                    for match_id in reversed(new_match_ids):
                        print("─" * HORIZONTAL_LINE)

                        start_ts, stop_ts = await process_and_print_single_match(match_id, puuid, riotid_name, region, STATUS_NOTIFICATION, csv_file_name)

                        if start_ts:
                            last_match_start_ts = start_ts

                        if stop_ts:
                            last_match_stop_ts = stop_ts

                        processed_match_ids.add(match_id)

                        processed_new_match_in_this_cycle = True

                        started_announced = False

                    print_cur_ts("\nTimestamp:\t\t\t")

            ingame = await is_user_in_match(puuid, region)

            if ingame != ingame_old:

                # User is playing new match
                if ingame:
                    ts = await print_current_match(puuid, riotid_name, region, last_match_start_ts, last_match_stop_ts, STATUS_NOTIFICATION)
                    if ts and ts > 0:
                        started_announced = True

                    # Capture snapshot for custom games so we can persist it later if no completion arrives
                    try:
                        snap = await get_current_match_details(puuid, region)
                        if snap:
                            # Check if it's a custom game: gameType is CUSTOM_GAME or gameMode is unknown
                            game_type = snap.get('game_type')
                            mode_raw = snap.get('mode_raw')
                            is_custom = (game_type == "CUSTOM_GAME" or (mode_raw and mode_raw not in game_modes_mapping))

                            if is_custom:
                                current_custom_snapshot = snap
                                current_match_start_ts = int(snap.get('start_ts') or 0)
                            else:
                                current_custom_snapshot = None
                                current_match_start_ts = 0
                        else:
                            current_custom_snapshot = None
                            current_match_start_ts = 0
                    except Exception as e:
                        print(f"* Warning: Could not capture current match details: {e}")
                        current_custom_snapshot = None
                        current_match_start_ts = 0

                    print_cur_ts("\nTimestamp:\t\t\t")

                # User stopped playing the match
                elif not ingame and not processed_new_match_in_this_cycle and started_announced:
                    print(f"*** LoL user {riotid_name} stopped playing !")
                    m_subject = f"LoL user {riotid_name} stopped playing"
                    m_body = f"LoL user {riotid_name} stopped playing{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                    m_body_html = (
                        f"<html><head></head><body>"
                        f"LoL user <b>{html.escape(riotid_name)}</b> stopped playing"
                        f"{get_cur_ts('<br><br>Timestamp: ')}"
                        f"</body></html>"
                    )

                    game_finished_ts = int(time.time())

                    # If the last active game was a custom game, arm a delayed save in case no completion arrives
                    if current_custom_snapshot:
                        pending_custom = {
                            'deadline': game_finished_ts + CUSTOM_SAVE_DELAY,
                            'snapshot': current_custom_snapshot,
                            'start_ts': current_match_start_ts or last_match_start_ts or 0,
                            'stop_ts': game_finished_ts,
                        }

                    started_announced = False

                    if STATUS_NOTIFICATION:
                        print(f"Sending email notification to {RECEIVER_EMAIL}")
                        send_email(m_subject, m_body, m_body_html, SMTP_SSL)

                    print_cur_ts("\nTimestamp:\t\t\t")

            # Fire pending custom game save if deadline passed and no completion arrived
            if pending_custom and int(time.time()) >= pending_custom['deadline']:
                try:
                    await save_custom_match_to_csv(
                        pending_custom['snapshot'],
                        riotid_name,
                        pending_custom['start_ts'],
                        pending_custom['stop_ts'],
                        csv_file_name
                    )
                    print(f"*** Saved custom game match to CSV (no completion within {display_time(CUSTOM_SAVE_DELAY)})")
                    print_cur_ts("\nTimestamp:\t\t\t")
                except Exception as e:
                    print(f"* Warning: Could not save custom game match to CSV: {e}")
                    print_cur_ts("\nTimestamp:\t\t\t")
                finally:
                    pending_custom = None
                    current_custom_snapshot = None
                    current_match_start_ts = 0

            ingame_old = ingame
            alive_counter += 1
            email_sent = False
            hint_tracker.reset()

            if LIVENESS_CHECK_COUNTER and alive_counter >= LIVENESS_CHECK_COUNTER:
                print_cur_ts("Liveness check, timestamp:\t")
                alive_counter = 0

            wait_seconds = LOL_ACTIVE_CHECK_INTERVAL if (ingame or (game_finished_ts and (int(time.time()) - game_finished_ts) <= LOL_CHECK_INTERVAL)) else LOL_CHECK_INTERVAL
            debug_print("Monitoring check", check=f"#{check_count}", user=riotid, outcome="OK", in_game=ingame, next_check=f"{wait_seconds}s")
            time.sleep(wait_seconds)

        except Exception as e:
            advice = classify_recovery_error(e)
            # The detail carries the failing request, which is how one Riot failure is told from another
            if hint_tracker.should_render(advice):
                print(render_recovery_error(RecoveryError(advice)))
            else:
                print(f"* Error: {advice.summary}")
            debug_print("Monitoring check", check=f"#{check_count}", outcome="failed", code=advice.code, error=f"{type(e).__name__}: {e}")
            print(f"* Retrying in {display_time(LOL_CHECK_INTERVAL)}")
            if advice.code == "auth.api_key_invalid":
                if ERROR_NOTIFICATION and not email_sent:
                    m_subject = f"lol_monitor: API key error! (user: {riotid_name})"
                    m_body = f"{advice.summary}: {sanitize_error_text(e)}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                    m_body_html = (
                        f"<html><head></head><body>"
                        f"{html.escape(advice.summary)}: <b>{html.escape(sanitize_error_text(e))}</b>"
                        f"{get_cur_ts('<br><br>Timestamp: ')}"
                        f"</body></html>"
                    )
                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                    send_email(m_subject, m_body, m_body_html, SMTP_SSL)
                    email_sent = True
            print_cur_ts("Timestamp:\t\t\t")
            debug_print("Retry wait", check=f"#{check_count}", next_check=f"{LOL_CHECK_INTERVAL}s")
            time.sleep(LOL_CHECK_INTERVAL)
            continue


# The four shared status markers. A fifth neutral marker is the single biggest source of drift between these
# tools, because every state it would cover is a state the others already call PASS
DOCTOR_STATUSES = ("PASS", "WARN", "FAIL", "SKIP")

# Riot's development key allows 100 requests every two minutes and each in-game cycle spends several of them,
# so an active interval below this leaves no headroom for the extra calls a live match report makes
DOCTOR_MIN_SAFE_ACTIVE_INTERVAL = 10

# Preflight rows wait far less than a real delivery, so an unreachable host cannot stall the whole report
DOCTOR_PASSIVE_TIMEOUT = 5

# The passing label of the email row, pinned so the wording cannot drift from the sibling monitors
SMTP_READY_CHECK_LABEL = "SMTP connection and login succeeded"

# The one label for a channel that is switched on and cannot deliver, shared with every sibling monitor
EMAIL_UNUSABLE_CHECK_LABEL = "Email alerts are enabled but unusable"


# One doctor result, held until the whole report is rendered
DoctorCheck = namedtuple("DoctorCheck", ["section", "status", "label", "detail", "advice"])
DoctorCheck.__new__.__defaults__ = ("", None)


# Collects doctor checks plus the work later checks reuse, so nothing is fetched or authenticated twice
class DoctorReport:
    # Starts an empty report with no validated key, no resolved account and no channel marked ready for a delivery test
    def __init__(self):
        self.checks = []
        self.api_key_valid = False
        self.account = None
        # Why the target lookup cannot run, phrased as a clause the skipped row completes
        self.target_skip_reason = ""
        # Structural flag, so offering a delivery test never depends on matching a rendered label
        self.email_ready = False


# Builds one doctor check, keeping construction in one place so the shape cannot drift between sections
def make_doctor_check(section, status, label, detail="", advice=None):
    if status not in DOCTOR_STATUSES:
        raise ValueError(f"Unsupported doctor status: {status}")
    # A row the user has to act on is useless without an action, so the row is rejected rather than printed bare
    if status in ("WARN", "FAIL") and (advice is None or not advice.fix):
        raise ValueError(f"Doctor {status} rows require a fix")
    # Several advice objects carry the same text as their summary and printing it twice reads as two problems
    return DoctorCheck(section, status, label, "" if str(detail).strip() == str(label).strip() else detail, advice)


# Joins setting names the way every doctor detail and action in this family lists them
def join_setting_names(names, conjunction):
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} {conjunction} {names[-1]}"


# Returns enabled email notification category names in display order
def email_notification_categories():
    return [label for enabled, label in ((STATUS_NOTIFICATION, "status changes"), (ERROR_NOTIFICATION, "errors")) if enabled]


# Reports the running Python version plus every required and optional dependency
def doctor_check_environment(version_info=None, spec_finder=None):
    checks = []
    selected_version = sys.version_info if version_info is None else version_info
    version_text = ".".join(str(part) for part in tuple(selected_version)[:3])
    minimum_detail = f"Minimum supported version: {MINIMUM_PYTHON_VERSION_TEXT}"
    if tuple(selected_version)[:2] >= MINIMUM_PYTHON_VERSION:
        checks.append(make_doctor_check("Environment", "PASS", f"Python {version_text} is supported", minimum_detail))
    else:
        advice = make_recovery_advice("dependency.missing", f"Python {version_text} is unsupported", f"Install Python {MINIMUM_PYTHON_VERSION_TEXT} or newer then retry", False)
        checks.append(make_doctor_check("Environment", "FAIL", advice.summary, minimum_detail, advice))

    find_spec = importlib.util.find_spec if spec_finder is None else spec_finder

    # Returns whether one module can be located, treating an unimportable parent as absent
    def module_present(module_name):
        try:
            return find_spec(module_name) is not None
        except (ImportError, ValueError):
            return False

    for module_name, package_name in (("pulsefire", "pulsefire"), ("requests", "requests"), ("dateutil", "python-dateutil")):
        if module_present(module_name):
            checks.append(make_doctor_check("Environment", "PASS", f"Required dependency {package_name} is installed"))
        else:
            advice = make_recovery_advice("dependency.missing", f"Required dependency {package_name} is missing", recovery_fix_with_guide(f"Install it with: {pip_install_command(package_name)}", INSTALL_GUIDE_URL), False)
            checks.append(make_doctor_check("Environment", "FAIL", advice.summary, advice=advice))

    if module_present("dotenv"):
        checks.append(make_doctor_check("Environment", "PASS", "Optional dependency python-dotenv is installed", "Used only for reading secrets from a dotenv file"))
    else:
        advice = make_recovery_advice("dependency.missing", "Optional dependency python-dotenv is not installed", recovery_fix_with_guide(f"Install it with: {pip_install_command('python-dotenv')}. Or export the secrets as environment variables", INSTALL_GUIDE_URL), False)
        checks.append(make_doctor_check("Environment", "WARN", advice.summary, "Secrets can only come from environment variables or the configuration file. Every other feature is unaffected", advice))
    return checks


# Reports which secrets are in effect and where each one was read from, by name and never by value
def doctor_secret_checks(env_path=None):
    from_file, from_environment, from_settings, from_command_line = group_secrets_by_source(env_path)
    checks = []
    if from_file:
        checks.append(make_doctor_check("Configuration", "PASS", "Secrets loaded from the dotenv file", ", ".join(from_file)))
    if from_environment:
        checks.append(make_doctor_check("Configuration", "PASS", "Secrets loaded from the environment", ", ".join(from_environment)))
    if from_settings:
        checks.append(make_doctor_check("Configuration", "PASS", "Secrets loaded from the configuration file", ", ".join(from_settings)))
    if from_command_line:
        checks.append(make_doctor_check("Configuration", "PASS", "Secrets loaded from the command line", ", ".join(from_command_line)))
    if not checks:
        checks.append(make_doctor_check("Configuration", "PASS", "No secrets loaded", "Nothing was read from a dotenv file, the environment, the configuration file or the command line"))
    return checks


# Returns the closest parent that exists, so writability is judged without creating anything
def nearest_existing_parent(path):
    candidate = Path(path).expanduser()
    if candidate.exists():
        return candidate if candidate.is_dir() else candidate.parent
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


# Reports whether one file monitoring will write can be created, without creating anything
def doctor_destination_check(label, destination):
    selected = Path(destination).expanduser()
    parent = nearest_existing_parent(selected)
    if parent.is_dir() and os.access(parent, os.W_OK):
        return make_doctor_check("Configuration", "PASS", f"{label} appears writable", f"Path: {selected}")
    advice = classify_recovery_error(context="file", detail=f"{label} is not writable: {selected}")
    return make_doctor_check("Configuration", "FAIL", advice.summary, advice.detail, advice)


# Reports each file monitoring will write, resolving the log name once a Riot ID is known
def doctor_output_destination_checks(riot_id=None):
    checks = []
    if DISABLE_LOGGING:
        checks.append(make_doctor_check("Configuration", "PASS", "Output logging is disabled"))
    elif LOL_LOGFILE:
        # The log name carries the part of the Riot ID before the tag, which is known without any Riot lookup
        suffix = str(riot_id or "").partition("#")[0]
        if suffix or Path(os.path.expanduser(str(LOL_LOGFILE))).suffix:
            checks.append(doctor_destination_check("Log destination", build_log_path(LOL_LOGFILE, suffix)))
        else:
            checks.append(make_doctor_check("Configuration", "PASS", "Log destination will be finalized after a target is selected", f"Base path: {Path(os.path.expanduser(str(LOL_LOGFILE)))}"))
    if CSV_FILE:
        checks.append(doctor_destination_check("CSV destination", CSV_FILE))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "CSV logging is disabled"))
    return checks


# Returns all type and range errors in settings that control runtime timing or counts
def runtime_configuration_errors():
    errors = []
    positive_numbers = (("LOL_CHECK_INTERVAL", LOL_CHECK_INTERVAL), ("LOL_ACTIVE_CHECK_INTERVAL", LOL_ACTIVE_CHECK_INTERVAL), ("CHECK_INTERNET_TIMEOUT", CHECK_INTERNET_TIMEOUT))
    nonnegative_numbers = (("LIVENESS_CHECK_INTERVAL", LIVENESS_CHECK_INTERVAL), ("LOL_ACTIVE_CHECK_SIGNAL_VALUE", LOL_ACTIVE_CHECK_SIGNAL_VALUE))
    for name, value in positive_numbers:
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
            errors.append(f"{name} must be a number greater than zero, not {value!r}")
    for name, value in nonnegative_numbers:
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            errors.append(f"{name} must be a number zero or greater, not {value!r}")
    if not isinstance(SMTP_PORT, int) or isinstance(SMTP_PORT, bool) or not 1 <= SMTP_PORT <= 65535:
        errors.append(f"SMTP_PORT must be an integer from 1 through 65535, not {SMTP_PORT!r}")
    return errors


# Reports the region routing the run will use, which is the choice the tool can no longer make on its own
def doctor_region_checks(region=None):
    if not region:
        return []
    try:
        continent = region_continent(region)
    except ValueError:
        advice = classify_recovery_error(context="target.region", detail=f"Region: {region}")
        return [make_doctor_check("Configuration", "FAIL", REGION_INPUT_ERROR, f"Region: {region}", advice)]
    return [make_doctor_check("Configuration", "PASS", "The region routes to a Riot continent", f"Region {region} is routed through the {continent} host")]


# Reports the configuration and dotenv files in effect plus every file the tool will write
def doctor_check_configuration(config_path=None, env_path=None, riot_id=None, region=None):
    checks = []
    if config_path:
        checks.append(make_doctor_check("Configuration", "PASS", "Configuration file loaded", f"Path: {config_path}"))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "No configuration file selected", "Using built-in defaults and command-line overrides"))
    if env_path and os.path.isfile(str(env_path)):
        checks.append(make_doctor_check("Configuration", "PASS", "Dotenv file loaded", f"Path: {env_path}"))
    elif env_path:
        advice = make_recovery_advice("config.missing", "The requested dotenv file was not found", recovery_fix_with_guide("Create the file or select an existing path with --env-file", SECRETS_GUIDE_URL), False, f"Path: {env_path}")
        checks.append(make_doctor_check("Configuration", "WARN", advice.summary, advice.detail, advice))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "No dotenv file selected", "Using environment variables and other configured sources"))
    checks.extend(doctor_secret_checks(env_path))
    checks.extend(doctor_region_checks(region))

    if isinstance(LOL_ACTIVE_CHECK_INTERVAL, (int, float)) and not isinstance(LOL_ACTIVE_CHECK_INTERVAL, bool) and 0 < LOL_ACTIVE_CHECK_INTERVAL < DOCTOR_MIN_SAFE_ACTIVE_INTERVAL:
        intervals = f"{display_time(LOL_CHECK_INTERVAL)} out of game, {display_time(LOL_ACTIVE_CHECK_INTERVAL)} in game"
        advice = make_recovery_advice("riot.rate_limited", "Check intervals are short enough to be rate limited", recovery_fix_with_guide(f"Raise LOL_ACTIVE_CHECK_INTERVAL to at least {DOCTOR_MIN_SAFE_ACTIVE_INTERVAL} seconds", INTERVALS_GUIDE_URL), True)
        checks.append(make_doctor_check("Configuration", "WARN", "Check intervals are short", intervals, advice))

    if VERIFY_SSL:
        checks.append(make_doctor_check("Configuration", "PASS", "TLS certificate verification is on", "Every outbound request checks the server certificate"))
    else:
        advice = make_recovery_advice("config.insecure", "TLS certificate verification is off", recovery_fix_with_guide("Set VERIFY_SSL back to True unless this network intercepts TLS with its own certificate authority", TLS_GUIDE_URL), False)
        checks.append(make_doctor_check("Configuration", "WARN", "TLS certificate verification is off", "VERIFY_SSL is False, so an intercepted connection cannot be told apart from the real service", advice))

    numeric_errors = runtime_configuration_errors()
    if numeric_errors:
        numeric_detail = "Invalid numeric settings: " + "; ".join(numeric_errors)
        advice = make_recovery_advice("config.invalid", "One or more numeric settings are invalid", recovery_fix_with_guide("Correct the reported settings in the configuration file", CONFIG_FILE_GUIDE_URL), False, numeric_detail)
        checks.append(make_doctor_check("Configuration", "FAIL", "One or more numeric settings are invalid", numeric_detail, advice))

    try:
        ascii_log_separators_enabled()
    except ValueError as exc:
        advice = make_recovery_advice("config.invalid", "The log separator mode is not one this tool knows", recovery_fix_with_guide('Set ASCII_LOG_SEPARATORS to "Auto", "On" or "Off"', OUTPUT_GUIDE_URL), False, sanitize_error_text(str(exc)))
        checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, f"Mode: {ASCII_LOG_SEPARATORS}", advice))

    checks.extend(doctor_output_destination_checks(riot_id))
    return checks


# Confirms the configured connectivity endpoint is reachable, reusing the settings monitoring will use
def doctor_check_connectivity():
    if check_internet(quiet=True):
        return [make_doctor_check("Connectivity", "PASS", "The connectivity endpoint is reachable", f"Endpoint: {CHECK_INTERNET_URL}")]
    advice = classify_recovery_error(LAST_CONNECTIVITY_ERROR, context="connectivity", detail=f"Could not reach {CHECK_INTERNET_URL}")
    return [make_doctor_check("Connectivity", "FAIL", "The connectivity endpoint could not be reached", f"Endpoint: {CHECK_INTERNET_URL}", advice)]


# Asks Riot for the platform status, which is the cheapest call that answers whether the key is accepted
async def riot_api_key_probe(region):
    async with riot_api_client() as client:
        return await client.get_lol_status_v4_platform_data(region=region)


# Asks Riot for the account behind one Riot ID, the same lookup monitoring makes before it starts
async def riot_account_probe(riot_id, region):
    riotid_name, riotid_tag = riot_id.split("#", 1)
    async with riot_api_client() as client:
        return await client.get_account_v1_by_riot_id(region=region_continent(region), game_name=riotid_name, tag_line=riotid_tag)


# Validates the Riot API key against the configured region, recording why a later lookup cannot run
def doctor_check_authentication(report, region=None):
    if not doctor_value_is_set(RIOT_API_KEY):
        report.target_skip_reason = "No Riot API key is configured"
        advice = classify_recovery_error(context="credentials")
        return [make_doctor_check("Authentication", "FAIL", "No Riot API key is configured", "Nothing can be monitored without one", advice)]
    if not region:
        report.target_skip_reason = "No region was given"
        return [make_doctor_check("Authentication", "SKIP", "The Riot API key was not checked", "No region was given, so no request was attempted")]
    if not REGION_TO_CONTINENT.get(region):
        report.target_skip_reason = "The region is not one this tool knows"
        return [make_doctor_check("Authentication", "SKIP", "The Riot API key was not checked", "The region is not one this tool knows, so no request was attempted")]
    debug_print("Riot API key check", region=region)
    try:
        asyncio.run(riot_api_key_probe(region))
        debug_print("Riot API key check", region=region, outcome="OK")
    except Exception as exc:
        debug_print("Riot API key check", region=region, outcome="failed", error=f"{type(exc).__name__}: {exc}")
        report.target_skip_reason = "The Riot API key did not validate"
        advice = classify_recovery_error(exc, context="target")
        return [make_doctor_check("Authentication", "FAIL", advice.summary, advice.detail, advice)]
    report.api_key_valid = True
    return [make_doctor_check("Authentication", "PASS", "Riot accepted the configured API key", "The key itself was not displayed")]


# Confirms the monitored account exists, reusing the key the authentication check already validated
def doctor_check_target(report, riot_id=None, region=None, target_error=None):
    if target_error:
        advice = classify_recovery_error(context="target", detail=target_error)
        return [make_doctor_check("Target", "FAIL", advice.summary, advice.detail, advice)]
    missing = [name for name, value in (("Riot ID", riot_id), ("region", region)) if not value]
    if missing:
        # Both positionals are required, so a run started from this state stops before it monitors anything
        detail = f"No {' and no '.join(missing)} {'was' if len(missing) == 1 else 'were'} provided"
        advice = classify_recovery_error(context="target.missing", detail=detail)
        return [make_doctor_check("Target", "FAIL", advice.summary, "Nothing can be monitored until both are given", advice)]
    if not report.api_key_valid:
        return [make_doctor_check("Target", "SKIP", "The monitored account was not checked", f"{report.target_skip_reason or 'The Riot API key did not validate'}, so no lookup was attempted")]
    debug_print("Monitored account check", region=region)
    try:
        account = asyncio.run(riot_account_probe(riot_id, region))
        debug_print("Monitored account check", region=region, outcome="OK")
    except Exception as exc:
        debug_print("Monitored account check", region=region, outcome="failed", error=f"{type(exc).__name__}: {exc}")
        advice = classify_recovery_error(exc, context="target")
        return [make_doctor_check("Target", "FAIL", advice.summary, advice.detail, advice)]
    report.account = account
    game_name = sanitize_untrusted_text(account.get("gameName"))
    tag_line = sanitize_untrusted_text(account.get("tagLine"))
    return [make_doctor_check("Target", "PASS", "The monitored account exists", f"Riot ID: {game_name}#{tag_line}")]


# Returns the doctor row for email alerts whose settings cannot deliver, worded the same way by every sibling monitor
def doctor_email_unusable_check(detail, fix):
    advice = make_recovery_advice("smtp.invalid", EMAIL_UNUSABLE_CHECK_LABEL, recovery_fix_with_guide(fix, SMTP_GUIDE_URL), False, detail)
    return make_doctor_check("Notifications", "WARN", EMAIL_UNUSABLE_CHECK_LABEL, detail, advice)


# Checks email alert settings then confirms the SMTP sign-in without sending anything
def doctor_check_email_notifications(report):
    enabled_categories = email_notification_categories()
    unset = unset_email_settings()
    # The error alert ships on by default, so it alone cannot mean the channel is switched on
    deliberate_categories = [category for category in enabled_categories if category != "errors"]
    if not deliberate_categories and len(unset) == len(EMAIL_DELIVERY_SETTINGS):
        return [make_doctor_check("Notifications", "PASS", "Email notifications are disabled", "No SMTP connection was attempted and no email was sent")]
    if unset:
        return [doctor_email_unusable_check(f"{join_setting_names(unset, 'or')} is empty or still set to its placeholder", f"Set {join_setting_names(unset, 'and')} or turn the email alerts off")]
    if not enabled_categories:
        advice = make_recovery_advice("smtp.invalid", "Email is configured but no alert types are selected", recovery_fix_with_guide("Turn on at least one email alert in the configuration file", SMTP_GUIDE_URL), False)
        return [make_doctor_check("Notifications", "WARN", advice.summary, "Nothing would ever be emailed", advice)]
    smtp_object = None
    debug_print("SMTP sign-in check", host=SMTP_HOST, port=SMTP_PORT, use_ssl=SMTP_SSL)
    try:
        smtp_object = smtp_connect_and_login(SMTP_SSL, smtp_timeout=DOCTOR_PASSIVE_TIMEOUT)
        debug_print("SMTP sign-in check", host=SMTP_HOST, outcome="OK")
    except Exception as exc:
        debug_print("SMTP sign-in check", host=SMTP_HOST, outcome="failed", error=f"{type(exc).__name__}: {exc}")
        advice = classify_recovery_error(exc, "email")
        return [make_doctor_check("Notifications", "FAIL", advice.summary, advice.detail, advice)]
    finally:
        if smtp_object is not None:
            try:
                smtp_object.quit()
            except Exception as exc:
                debug_swallowed_exception("SMTP session close", exc)
    report.email_ready = True
    return [make_doctor_check("Notifications", "PASS", SMTP_READY_CHECK_LABEL, f"Alerts: {', '.join(enabled_categories)}. No email was sent during this passive check")]


# The fixed section order the report renders in, chosen so each section depends only on the ones above it
DOCTOR_SECTIONS = ("Environment", "Configuration", "Authentication", "Connectivity", "Target", "Notifications")

# Delivery results are printed as they happen rather than inside a section, but they still count in the summary
DOCTOR_DELIVERY_SECTION = "Optional delivery tests"

# The theme entry each doctor result marker is drawn in, so a failure reads as one at a glance
DOCTOR_MARK_STYLES = {"PASS": "boolean_true", "WARN": "warning", "FAIL": "error", "SKIP": "info"}

# Width of the transient progress line currently on screen, so the next write can erase exactly what it drew
DOCTOR_PROGRESS_WIDTH = 0


# Renders one doctor result marker, which the colour engine styles by status
def render_doctor_marker(status):
    return f"[{status}]"


# Prints one result the way the report renders it, so a row printed after the report matches the rows above it
def print_doctor_check(check):
    print(f"{render_doctor_marker(check.status)} {check.label}")
    if check.detail:
        print(f"  {check.detail}")


# Renders the heading and every non-empty section, with a fix line on the rows that are not a pass
def render_doctor_sections(report):
    # The install method is context rather than a check: it cannot fail, so it is stated once here
    # instead of occupying a result row that no marker describes
    lines = ["Doctor", f"Detected install method: {install_method()}"]
    for section in DOCTOR_SECTIONS:
        section_checks = [check for check in report.checks if check.section == section]
        if not section_checks:
            continue
        lines.extend(("", section))
        for check in section_checks:
            lines.append(f"{render_doctor_marker(check.status)} {check.label}")
            if check.detail:
                lines.append(f"  {check.detail}")
            if check.status != "PASS" and check.advice is not None:
                # The fix carries its own guide line, so each line is indented on its own
                lines.extend(f"  {advice_line}" for advice_line in f"To fix: {check.advice.fix}".splitlines())
    return sanitize_error_text("\n".join(lines))


# Renders the one sentence that says whether the setup is usable and where to read more
def render_doctor_summary(checks):
    failures = sum(check.status == "FAIL" for check in checks)
    warnings = sum(check.status == "WARN" for check in checks)
    if failures:
        summary_line = f"  {failures} check(s) failed, {warnings} warning(s). Fix the failures above before relying on the tool."
    elif warnings:
        summary_line = f"  All critical checks passed with {warnings} warning(s). Review the warnings above."
    else:
        summary_line = "  All checks passed. You are good to go!"
    return "\n".join(("", "Summary", summary_line, "", f"Guide: {DOCTOR_GUIDE_URL}"))


# Returns the real terminal underneath the logger wrapper, so progress can move the cursor safely
def doctor_terminal_stream():
    stream = sys.stdout
    while isinstance(stream, Logger):
        stream = stream.terminal
    return stream


# Shows one transient doctor step, only on an interactive terminal
# The line stays uncoloured on purpose: it is erased by writing exactly len(line) spaces, and escape
# sequences would make that width wrong and leave a styled remnant behind
def doctor_progress(label):
    global DOCTOR_PROGRESS_WIDTH
    terminal = doctor_terminal_stream()
    if terminal.isatty():
        if DOCTOR_PROGRESS_WIDTH:
            terminal.write("\r" + (" " * DOCTOR_PROGRESS_WIDTH) + "\r")
        line = f"* Checking {ANSI_ESCAPE_RE.sub('', sanitize_untrusted_text(label))} ..."
        DOCTOR_PROGRESS_WIDTH = len(line)
        terminal.write("\r" + line)
        terminal.flush()


# Clears the transient doctor progress line on an interactive terminal
def doctor_progress_clear():
    global DOCTOR_PROGRESS_WIDTH
    terminal = doctor_terminal_stream()
    if terminal.isatty() and DOCTOR_PROGRESS_WIDTH:
        terminal.write("\r" + (" " * DOCTOR_PROGRESS_WIDTH) + "\r")
        terminal.flush()
    DOCTOR_PROGRESS_WIDTH = 0


# States what doctor will and will not do, before the first slow check starts rather than after
def render_doctor_notice():
    print("Running preflight checks. No files will be written. The interactive email test runs only after separate approval.\n")


# Prompts for explicit delivery consent and defaults safely to no
def doctor_ask_yes_no(question, input_func=input):
    while True:
        try:
            value = read_interactively(input_func, f"{question} [y/N]: ").strip().casefold()
        except EOFError:
            print("\nDelivery test skipped.")
            return False
        except KeyboardInterrupt:
            # Ctrl+C ends the run here the way it does anywhere else, rather than only declining this one test
            signal_handler(signal.SIGINT, None)
            raise
        if not value or value in ("n", "no"):
            return False
        if value in ("y", "yes"):
            return True
        print("  Please answer 'y' or 'n'.")


# Offers one real delivery per ready channel, only after separate interactive approval
def doctor_offer_notification_tests(report, input_func=input, interactive=None):
    terminal_is_interactive = (sys.stdin.isatty() and sys.stdout.isatty()) if interactive is None else interactive
    if not terminal_is_interactive or not report.email_ready:
        return []
    print("\n" + DOCTOR_DELIVERY_SECTION + "\n")
    print("Doctor will not write files. Each approved test sends one real message.\n")
    if doctor_ask_yes_no("Send one test email now? This will deliver a real message", input_func=input_func):
        debug_print("Doctor test email", recipient=RECEIVER_EMAIL)
        delivered = send_email("lol_monitor: doctor test email", "This test email was sent after approval in --doctor. Your SMTP delivery settings work.", "", SMTP_SSL, smtp_timeout=DOCTOR_PASSIVE_TIMEOUT) == 0
        debug_print("Doctor test email", recipient=RECEIVER_EMAIL, outcome="OK" if delivered else "failed")
        if delivered:
            check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "PASS", "Doctor test email delivered", "One real test email was sent after confirmation")
        else:
            advice = make_recovery_advice("smtp.connection", "Doctor test email delivery failed", recovery_fix_with_guide("Review the SMTP error above and correct the email settings", SMTP_GUIDE_URL), True)
            check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "FAIL", advice.summary, "The approved test email could not be delivered", advice)
    else:
        check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "SKIP", "Test email was not sent", "You declined the real delivery test. Run doctor again and approve the email test when ready")
    # Recorded on the report so the summary sentence and the exit code cannot disagree about the same run
    report.checks.append(check)
    print_doctor_check(check)
    return [check]


# Runs every preflight check, then the approved delivery tests, returning zero only when nothing failed
def run_doctor(riot_id=None, region=None, config_path=None, env_path=None, target_error=None):
    report = DoctorReport()
    progress = doctor_progress if doctor_terminal_stream().isatty() else None
    # A Riot ID the tool rejected names no log file, since the run that would open one cannot start
    log_target = None if target_error else riot_id
    render_doctor_notice()
    try:
        for label, collect in (
            ("environment", lambda: doctor_check_environment()),
            ("configuration", lambda: doctor_check_configuration(config_path, env_path, log_target, region)),
            ("connectivity", lambda: doctor_check_connectivity()),
            ("authentication", lambda: doctor_check_authentication(report, region)),
            ("the monitored account", lambda: doctor_check_target(report, riot_id, region, target_error)),
            ("notifications", lambda: doctor_check_email_notifications(report)),
        ):
            if progress is not None:
                progress(label)
            report.checks.extend(collect())
    finally:
        doctor_progress_clear()
    print(render_doctor_sections(report))
    doctor_offer_notification_tests(report)
    print(render_doctor_summary(report.checks))
    # The next steps block is the one place that prints the monitoring command, so it is not repeated here
    return 1 if any(check.status == "FAIL" for check in report.checks) else 0


# Prints one labelled command on its own indented line, the shared shape across these tools
def print_labelled_command(label, command, suffix=""):
    print(label)
    print(f"    {command}{suffix}\n")


# Returns the target arguments a printed command needs, leaving out a pair the configuration file already supplies
def command_target_arguments(riot_id=None, region=None, riot_id_saved=False, region_saved=False):
    if not riot_id or not region:
        # Monitoring cannot run without both, so the placeholders stay while the doctor reports the gap itself
        return [riot_id or RIOT_ID_PLACEHOLDER, region or REGION_PLACEHOLDER]
    if riot_id_saved and region_saved:
        return []
    return [riot_id, region]


# Prints the command that starts monitoring with the files this run checked, so a report read on its own
# ends with the next action rather than leaving the reader to assemble the command
def print_doctor_next_steps(riot_id=None, region=None, riot_id_saved=False, region_saved=False, doctor_exit=0):
    print("\nNext steps\n")
    label = "After Doctor passes, start monitoring:" if doctor_exit else "Start monitoring:"
    print_labelled_command(label, render_command(command_target_arguments(riot_id, region, riot_id_saved, region_saved)))
    # No trailing blank line: the command printer already left one and the report must not end on two
    print(f"Guide: {QUICK_START_GUIDE_URL}")



def main():
    global CLI_CONFIG_PATH, CONFIG_DISCOVERY_DISABLED, COMMAND_LINE_SECRET_KEYS, EXPORTED_SECRET_KEYS, DOTENV_FILE, LIVENESS_CHECK_COUNTER, RIOT_API_KEY, CSV_FILE, DISABLE_LOGGING, LOL_LOGFILE, STATUS_NOTIFICATION, ERROR_NOTIFICATION, LOL_CHECK_INTERVAL, LOL_ACTIVE_CHECK_INTERVAL, SMTP_PASSWORD, stdout_bck, REGION_TO_CONTINENT, INCLUDE_FORBIDDEN_MATCHES, DEBUG_MODE

    if "--generate-config" in sys.argv:
        config_content = CONFIG_BLOCK.strip("\n") + "\n"
        try:
            idx = sys.argv.index("--generate-config")
            if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith("-"):
                # Written directly rather than redirected, which avoids the UTF-16 encoding PowerShell applies to '>'
                output_file = sys.argv[idx + 1]
                backup_path, written = write_generated_config(output_file, config_content, force="--force" in sys.argv)
                if not written:
                    print("Config was not replaced. The existing file is unchanged")
                    sys.exit(1)
                print(f"Config written to: {output_file}")
                if backup_path:
                    print(f"Previous config backed up to: {backup_path}")
                sys.exit(0)
        except (ValueError, IndexError):
            pass
        except FileExistsError as exc:
            print_recovery_error(exc, context="file.exists", detail=str(exc))
            sys.exit(1)
        except OSError as exc:
            print_recovery_error(exc, context="file", detail=f"The config file could not be written: {exc}")
            sys.exit(1)
        sys.stdout.buffer.write(config_content.encode("utf-8"))
        sys.stdout.buffer.flush()
        sys.exit(0)

    if "--version" in sys.argv:
        print(f"{os.path.basename(sys.argv[0])} v{VERSION}")
        sys.exit(0)

    stdout_bck = sys.stdout

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    clear_screen(CLEAR_SCREEN)

    print(f"League of Legends Monitoring Tool v{VERSION}\n")

    parser = argparse.ArgumentParser(
        prog="lol_monitor",
        description=(f"Monitor a League of Legends user's playing status and send customizable email alerts [ {PROJECT_URL}/ ]"), formatter_class=argparse.RawTextHelpFormatter
    )

    # Positional
    parser.add_argument(
        "riot_id",
        nargs="?",
        metavar="RIOT_ID",
        help="User's LoL Riot ID",
        type=str
    )
    parser.add_argument(
        "region",
        nargs="?",
        metavar="REGION",
        help="User's LoL region (e.g. eun1, na1, br1 etc.)",
        type=str
    )

    # Version, just to list in help, it is handled earlier
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s v{VERSION}"
    )

    # Configuration & dotenv files
    conf = parser.add_argument_group("Configuration & dotenv files")
    conf.add_argument(
        "--config-file",
        dest="config_file",
        metavar="PATH",
        help="Location of the optional config file (auto-search if not set, disable with 'none')",
    )
    conf.add_argument(
        "--generate-config",
        nargs="?",
        const=True,
        metavar="FILENAME",
        help="Print default config template and exit (on Windows PowerShell, specify a filename to avoid redirect encoding issues)",
    )
    conf.add_argument(
        "--force",
        dest="force",
        action="store_true",
        help="Let --generate-config replace an existing file without asking, after a timestamped backup",
    )
    conf.add_argument(
        "--env-file",
        dest="env_file",
        metavar="PATH",
        help="Path to optional dotenv file (auto-search if not set, disable with 'none')",
    )
    conf.add_argument(
        "--doctor",
        dest="doctor",
        action="store_true",
        default=None,
        help="Run read-only preflight checks and report what is ready and what is not",
    )

    # API credentials
    creds = parser.add_argument_group("API credentials")
    creds.add_argument(
        "-r", "--riot-api-key",
        dest="riot_api_key",
        metavar="RIOT_API_KEY",
        type=str,
        help="Riot API key"
    )

    # Notifications
    notify = parser.add_argument_group("Notifications")
    notify.add_argument(
        "-s", "--notify-status",
        dest="notify_status",
        action="store_true",
        default=None,
        help="Email when user's playing status changes"
    )
    notify.add_argument(
        "-e", "--no-error-notify",
        dest="notify_errors",
        action="store_false",
        default=None,
        help="Disable email on errors (e.g. invalid API key)"
    )
    notify.add_argument(
        "--send-test-email",
        dest="send_test_email",
        action="store_true",
        help="Send test email to verify SMTP settings"
    )

    # Intervals & timers
    times = parser.add_argument_group("Intervals & timers")
    times.add_argument(
        "-c", "--check-interval",
        dest="check_interval",
        metavar="SECONDS",
        type=int,
        help="Polling interval when user is not in game"
    )
    times.add_argument(
        "-k", "--active-interval",
        dest="active_interval",
        metavar="SECONDS",
        type=int,
        help="Polling interval when user is in game"
    )

    # Listing mode
    listing = parser.add_argument_group("Listing")

    listing.add_argument(
        "-l", "--list-recent-matches",
        dest="list_recent_matches",
        action="store_true",
        help="List recent matches for the user"
    )
    listing.add_argument(
        "-n", "--recent-matches-count",
        dest="recent_matches_count",
        metavar="N",
        type=int,
        help="Number of recent matches to list/save"
    )
    listing.add_argument(
        "-m", "--min-recent-matches",
        dest="min_of_recent_matches",
        metavar="M",
        type=int,
        help="Minimum match index when listing recent matches"
    )
    listing.add_argument(
        "-a", "--all-matches",
        dest="all_matches",
        action="store_true",
        help="Fetch all available matches (use with -l)"
    )

    # Features & Output
    opts = parser.add_argument_group("Features & output")
    opts.add_argument(
        "-f", "--include-forbidden-matches",
        dest="include_forbidden_matches",
        action="store_true",
        help="Include forbidden matches (requiring RSO token) in the output"
    )
    opts.add_argument(
        "-b", "--csv-file",
        dest="csv_file",
        metavar="CSV_FILENAME",
        type=str,
        help="Write game status changes to CSV file"
    )
    opts.add_argument(
        "-d", "--disable-logging",
        dest="disable_logging",
        action="store_true",
        default=None,
        help="Disable logging to lol_monitor_<riot_id_name>.log"
    )
    opts.add_argument(
        "--verbose",
        dest="verbose",
        action="store_true",
        default=None,
        help="Print extra startup and runtime detail (overrides VERBOSE_MODE)"
    )
    opts.add_argument(
        "--debug",
        dest="debug",
        action="store_true",
        default=None,
        help="Print timestamped diagnostic detail including outbound calls and failure causes (overrides DEBUG_MODE)"
    )

    args = parser.parse_args()

    # Applied here so config-load failures and startup checks can already print diagnostics
    apply_diagnostic_cli_flags(args)

    CONFIG_DISCOVERY_DISABLED = args.config_file is not None and str(args.config_file).casefold() == "none"
    if CONFIG_DISCOVERY_DISABLED:
        CLI_CONFIG_PATH = None
    elif args.config_file:
        CLI_CONFIG_PATH = os.path.expanduser(args.config_file)

    cfg_path = None if CONFIG_DISCOVERY_DISABLED else find_config_file(CLI_CONFIG_PATH)

    if not cfg_path and CLI_CONFIG_PATH:
        print_recovery_error(context="config", detail=f"Config file '{CLI_CONFIG_PATH}' does not exist")
        sys.exit(1)

    if cfg_path:
        debug_print("Loading configuration file", path=cfg_path)
        if not load_config_file(cfg_path):
            sys.exit(1)
    else:
        debug_print("No configuration file found, using built-in defaults")

    # Reapplied because the config file may carry VERBOSE_MODE or DEBUG_MODE values that must not beat an explicit flag
    apply_diagnostic_cli_flags(args)

    # Resolved right after the config file is read, so every later message sees the target this run will actually use
    riot_id_saved = not args.riot_id and bool(RIOT_ID)
    region_saved = not args.region and bool(REGION)
    if riot_id_saved:
        args.riot_id = RIOT_ID
    if region_saved:
        args.region = REGION

    # Normalized once, so the log file name, every printed command and every Riot lookup see the same text.
    # A rejected Riot ID is recorded rather than raised here, so --doctor can report it as a row of its own
    target_input_error = None
    if args.riot_id:
        try:
            args.riot_id = normalize_riot_id(args.riot_id)
        except ValueError as exc:
            target_input_error = str(exc)
    if args.region:
        args.region = normalize_region(args.region)

    # Recorded before the dotenv file is read, so an exported value stays ahead of the same name in that file
    EXPORTED_SECRET_KEYS = frozenset(secret for secret in SECRET_KEYS if os.getenv(secret) is not None)

    if args.env_file:
        DOTENV_FILE = os.path.expanduser(args.env_file)
    else:
        if DOTENV_FILE:
            DOTENV_FILE = os.path.expanduser(DOTENV_FILE)

    if DOTENV_FILE and DOTENV_FILE.lower() == 'none':
        env_path = None
    else:
        try:
            from dotenv import load_dotenv, find_dotenv

            if DOTENV_FILE:
                env_path = DOTENV_FILE
                if not os.path.isfile(env_path):
                    debug_print("Dotenv file", path=env_path, outcome="skipped", reason="the file does not exist")
                    print(f"* Warning: dotenv file '{env_path}' does not exist\n")
                else:
                    load_dotenv(env_path, override=False)
                    debug_print("Dotenv file", path=env_path, outcome="OK")
            else:
                env_path = find_dotenv() or None
                if env_path:
                    load_dotenv(env_path, override=False)
                    debug_print("Dotenv file", path=env_path, outcome="OK", source="search")
                else:
                    debug_print("Dotenv file", outcome="skipped", reason="the search found no file")
        except ImportError:
            env_path = DOTENV_FILE if DOTENV_FILE else None
            if env_path:
                retry_command = render_command([args.riot_id, args.region]) if args.riot_id and args.region else None
                retry_line = f"Once installed, re-run this tool with:\n    {retry_command}\n" if retry_command else "Once installed, re-run this tool\n"
                print(f"* Warning: Cannot load dotenv file '{env_path}' because 'python-dotenv' is not installed\n\nTo install it, run:\n    pip3 install python-dotenv\n\n{retry_line}")

    # Exported secrets apply on their own, so a dotenv file is an alternative to the environment rather than a precondition
    load_secrets_from_environment()

    apply_tls_verification_setting()

    if args.riot_api_key:
        RIOT_API_KEY = args.riot_api_key

    # Assigned once from the arguments rather than accumulated, so a second run in one process starts clean
    COMMAND_LINE_SECRET_KEYS = frozenset(name for name, supplied in (("RIOT_API_KEY", args.riot_api_key), ) if supplied)

    # Applied before the report so every row it prints describes the run this command line asked for
    if args.check_interval:
        LOL_CHECK_INTERVAL = args.check_interval
        LIVENESS_CHECK_COUNTER = LIVENESS_CHECK_INTERVAL / LOL_CHECK_INTERVAL

    if args.active_interval:
        LOL_ACTIVE_CHECK_INTERVAL = args.active_interval

    if args.include_forbidden_matches is True:
        INCLUDE_FORBIDDEN_MATCHES = True

    if args.notify_status is True:
        STATUS_NOTIFICATION = True

    if args.notify_errors is False:
        ERROR_NOTIFICATION = False

    if args.disable_logging is True:
        DISABLE_LOGGING = True

    if args.csv_file:
        CSV_FILE = os.path.expanduser(args.csv_file)
    else:
        if CSV_FILE:
            CSV_FILE = os.path.expanduser(CSV_FILE)

    # A target is optional only for the modes that legitimately finish without one. Checked after the dotenv
    # file is resolved, so the command this prints carries the same files the run was given
    if (not args.riot_id or not args.region) and not (args.doctor or args.send_test_email):
        missing = "No Riot ID was provided" if not args.riot_id else "No region was provided"
        print_recovery_error(context="target.missing", detail=missing)
        sys.exit(1)

    if args.doctor:
        doctor_exit = run_doctor(riot_id=args.riot_id, region=args.region, config_path=cfg_path, env_path=env_path, target_error=target_input_error)
        # A target the configuration file already carries is left out, so the command stays as short as a saved run needs
        print_doctor_next_steps(args.riot_id, args.region, riot_id_saved, region_saved, doctor_exit)
        sys.exit(doctor_exit)

    if target_input_error:
        print_recovery_error(context="target", detail=target_input_error)
        sys.exit(1)

    if not check_internet():
        sys.exit(1)

    if args.send_test_email:
        print("* Sending test email notification ...\n")
        if send_email("lol_monitor: test email", "This is test email - your SMTP settings seems to be correct !", "", SMTP_SSL, smtp_timeout=5) == 0:
            print("* Email sent successfully !")
        else:
            sys.exit(1)
        sys.exit(0)

    # Kept at its old position as a backstop, so every path below this line is known to have both positionals
    if not args.riot_id or not args.region:
        missing = "No Riot ID was provided" if not args.riot_id else "No region was provided"
        print_recovery_error(context="target.missing", detail=missing)
        sys.exit(1)

    if not REGION_TO_CONTINENT.get(args.region):
        print_recovery_error(context="target.region", detail=f"'{args.region}' is not present in REGION_TO_CONTINENT")
        sys.exit(1)

    if not doctor_value_is_set(RIOT_API_KEY):
        print_recovery_error(context="credentials")
        sys.exit(1)

    if CSV_FILE:
        try:
            with open(CSV_FILE, 'a', newline='', buffering=1, encoding="utf-8") as _:
                pass
        except Exception as e:
            print_recovery_error(e, context="file", detail=f"CSV file '{CSV_FILE}' cannot be opened for writing")
            sys.exit(1)

    if args.list_recent_matches:
        if args.all_matches:
            # Fetch all available matches
            print("* Determining total number of available matches...")
            try:
                async def get_all_matches_info():
                    puuid = await get_user_puuid(args.riot_id, args.region)
                    if puuid:
                        total_count = await get_total_match_count(puuid, args.region)
                        return puuid, total_count
                    return None, 0

                puuid, total_count = asyncio.run(get_all_matches_info())
                if puuid and total_count > 0:
                    matches_num = total_count
                    matches_min = 1
                    print(f"* Found {total_count} total matches available\n")
                else:
                    if not puuid:
                        print("* Error: Could not get PUUID for user")
                    else:
                        print("* Error: Could not determine total match count")
                    sys.exit(1)
            except Exception as e:
                print_recovery_error(e)
                sys.exit(1)
        else:
            if args.recent_matches_count and args.recent_matches_count > 0:
                matches_num = args.recent_matches_count
            else:
                matches_num = 2

            if args.min_of_recent_matches and args.min_of_recent_matches > 0:
                matches_min = args.min_of_recent_matches
            else:
                matches_min = 1

        if matches_min > matches_num:
            print(f"* Min matches ({matches_min}) cannot be greater than max matches ({matches_num})")
            sys.exit(1)

        list_operation = "* Listing & saving" if CSV_FILE else "* Listing"
        csv_destination_str = f" to '{CSV_FILE}'" if CSV_FILE else ""

        if matches_min != matches_num:
            print(f"{list_operation} recent matches from {matches_min} to {matches_num} for '{args.riot_id}'{csv_destination_str}:\n")
        else:
            print(f"{list_operation} recent match for '{args.riot_id}'{csv_destination_str}:\n")

        try:
            asyncio.run(print_save_recent_matches(args.riot_id, args.region, matches_min, matches_num, CSV_FILE))
        except Exception as e:
            print_recovery_error(e)
        sys.exit(0)

    riotid_name, riotid_tag = get_user_riot_name_tag(args.riot_id)

    if not riotid_name or not riotid_tag:
        sys.exit(1)

    try:
        ascii_log_separators_enabled()
    except ValueError as e:
        print_recovery_error(RecoveryError(make_recovery_advice("config.invalid", str(e), recovery_fix_with_guide('Set ASCII_LOG_SEPARATORS to "Auto", "On" or "Off"', OUTPUT_GUIDE_URL), False)))
        sys.exit(1)

    if not DISABLE_LOGGING:
        log_path = build_log_path(LOL_LOGFILE, riotid_name)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        FINAL_LOG_PATH = str(log_path)
        sys.stdout = Logger(FINAL_LOG_PATH)
        debug_print("Log file opened", path=FINAL_LOG_PATH, outcome="OK")
    else:
        FINAL_LOG_PATH = None

    unset_email = unset_email_settings()
    if unset_email:
        verbose_print(f"Email notifications are off because {', '.join(unset_email)} {'is' if len(unset_email) == 1 else 'are'} not set")
        STATUS_NOTIFICATION = False
        ERROR_NOTIFICATION = False

    print(f"* LoL polling intervals:\t[NOT in game: {display_time(LOL_CHECK_INTERVAL)}] [in game: {display_time(LOL_ACTIVE_CHECK_INTERVAL)}]")
    print(f"* Email notifications:\t\t[status changes = {STATUS_NOTIFICATION}] [errors = {ERROR_NOTIFICATION}]")
    print(f"* Include forbidden matches:\t{INCLUDE_FORBIDDEN_MATCHES}")
    print(f"* Liveness check:\t\t{bool(LIVENESS_CHECK_INTERVAL)}" + (f" ({display_time(LIVENESS_CHECK_INTERVAL)})" if LIVENESS_CHECK_INTERVAL else ""))
    print(f"* CSV logging enabled:\t\t{bool(CSV_FILE)}" + (f" ({CSV_FILE})" if CSV_FILE else ""))
    print(f"* Output logging enabled:\t{not DISABLE_LOGGING}" + (f" ({FINAL_LOG_PATH})" if not DISABLE_LOGGING else ""))
    print(f"* ASCII log separators:\t\t{ascii_log_separators_enabled()} (mode: {ASCII_LOG_SEPARATORS})")
    print(f"* TLS verification:\t\t{'On' if VERIFY_SSL else 'Off, server certificates are not checked'}")
    print(f"* Configuration file:\t\t{cfg_path or ('Discovery disabled' if CONFIG_DISCOVERY_DISABLED else 'None')}")
    print(f"* Dotenv file:\t\t\t{env_path or 'None'}")
    print(f"* Secrets in effect:\t\t{describe_secret_sources(env_path)}")
    print(f"* Install method:\t\t{install_method_display_name()}\n")

    # We define signal handlers only for Linux & MacOS since Windows has limited number of signals supported
    if platform.system() != 'Windows':
        signal.signal(signal.SIGUSR1, toggle_status_changes_notifications_signal_handler)
        signal.signal(signal.SIGTRAP, increase_active_check_signal_handler)
        signal.signal(signal.SIGABRT, decrease_active_check_signal_handler)
        signal.signal(signal.SIGHUP, reload_secrets_signal_handler)

    out = f"Monitoring user {args.riot_id}"
    print(out)
    # print("-" * len(out))
    print("─" * HORIZONTAL_LINE)

    asyncio.run(lol_monitor_user(args.riot_id, args.region, CSV_FILE))

    sys.stdout = stdout_bck
    sys.exit(0)


if __name__ == "__main__":
    main()
