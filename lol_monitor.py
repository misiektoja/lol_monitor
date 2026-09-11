#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v1.9

Tool implementing real-time tracking of LoL (League of Legends) players activities:
https://github.com/misiektoja/lol_monitor/

Python pip3 requirements:

pulsefire
requests
python-dateutil
python-dotenv (optional)
"""

VERSION = "1.9"

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

# ----------------------------
# Webhook Notifications
# ----------------------------

# Master switch for webhook notifications through Discord or ntfy
# The event settings below select which notifications are sent
# Can also be enabled via the --webhook flag
WEBHOOK_ENABLED = False

# Service used to deliver webhook notifications: "discord" or "ntfy"
# Known Discord and ntfy.sh URLs correct a mismatched configured value at runtime
# Can also be set via the --webhook-provider flag
WEBHOOK_PROVIDER = "discord"

# Private destination used to send webhook notifications
# Discord: Edit Channel -> Integrations -> Webhooks -> New Webhook -> Copy Webhook URL
# ntfy: complete topic URL such as https://ntfy.sh/your-private-topic
# Prefer --set-webhook-url, an environment variable or a dotenv file instead of storing this private URL here
# The --webhook-url flag is available for one-run overrides but may leave the private URL in shell history
WEBHOOK_URL = "your_webhook_url"

# Discord display name (leave empty to use the webhook default)
# Applies only when WEBHOOK_PROVIDER is "discord" (ignored by the ntfy provider)
WEBHOOK_USERNAME = "LoL Monitor"

# Discord avatar URL (leave empty to use the webhook default)
# Applies only when WEBHOOK_PROVIDER is "discord" (ignored by the ntfy provider)
WEBHOOK_AVATAR_URL = ""

# Whether to send a webhook notification when the user's playing status changes
# Can also be enabled via the --webhook-status flag
WEBHOOK_STATUS_NOTIFICATION = False

# Whether to send a webhook notification on monitoring errors
# Can also be enabled via --webhook-errors or disabled via --no-webhook-error-notify
WEBHOOK_ERROR_NOTIFICATION = True

# Optional request headers for advanced webhook integrations
# Values support the same placeholders as WEBHOOK_TEMPLATE
WEBHOOK_HEADERS = {}

# ----------------------------
# Advanced Webhook Settings
# ----------------------------

# Discord-format webhook request payload template
# Applies only when WEBHOOK_PROVIDER is "discord". The "ntfy" provider needs no template and ignores this
# value: it sends the alert body as a native ntfy message with the subject as its title. Use WEBHOOK_HEADERS
# to add ntfy options such as priority or tags
# Supported placeholders include title, description, version, image_url, fields, fields_str, color, timestamp,
# username and avatar_url
WEBHOOK_TEMPLATE = {
    "username": "{username}",
    "avatar_url": "{avatar_url}",
    "allowed_mentions": {
        "parse": [],
    },
    "embeds": [{
        "title": "{title}",
        "description": "{description}",
        "color": "{color}",
        "footer": {
            "text": "LoL Monitor v{version}",
        },
        "timestamp": "{timestamp}",
        "thumbnail": {
            "url": "{image_url}",
        },
    }],
}

# Optional transformations applied to WEBHOOK_TEMPLATE and WEBHOOK_HEADERS values
# Tuple format: (field_to_target, method_name, *optional_arguments)
#
# Examples:
#   [
#       ("title", "upper"),
#       ("description", "replace", "**", ""),
#       ("description", "strip"),
#   ]
WEBHOOK_TRANSFORMS = []

# Optional ntfy access token for Bearer authentication
# Prefer an environment variable or dotenv file instead of storing this token here
NTFY_ACCESS_TOKEN = ""

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
LIVENESS_CHECK_INTERVAL = 86400  # 24 hours

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

# Max characters per line when printing to screen, to stop long lines from wrapping
# Does not affect log file output
# Set to 999 to auto-detect the terminal width
# Applies only when DISABLE_LOGGING is False
# Needs the optional wcwidth library, otherwise lines are printed in full
# Can also be set via the --truncate flag
TRUNCATE_CHARS = 0

# Width of horizontal line
HORIZONTAL_LINE = 113

# Whether to clear the terminal screen after starting the tool
CLEAR_SCREEN = True

# Whether terminal output is coloured
# Colour is switched off automatically when the output is not a terminal, when NO_COLOR is set
# and when the --no-color flag is passed. Log files are never coloured
COLORED_OUTPUT = True

# Colour used for each part of the output, shipped commented out so the tool's own defaults apply
# and a later change to them reaches you. Uncomment and edit any line to override one part
# Styles combine a colour with optional attributes, for example "bright_cyan underline"
# COLOR_THEME = {
#     # Headings and commands the tool tells you to run
#     "header": "bright_cyan",
#     "section": "bright_white",
#     # Identity
#     "username": "bright_cyan underline",
#     "id": "bright_magenta",
#     # Playing status values
#     "status_active": "green",
#     "status_inactive": "red",
#     # Match information
#     "champion": "bright_yellow",
#     "game_mode": "yellow",
#     "rank": "bright_green",
#     "duration": "green",
#     # Dates
#     "date": "magenta",
#     "date_range": "magenta",
#     # Timestamps
#     "timestamp_label": "",
#     "timestamp_value": "cyan",
#     # Notices
#     "info": "cyan",
#     "warning": "yellow",
#     "error": "red",
#     "signal": "yellow",
#     "email": "bright_cyan",
#     "webhook": "bright_blue",
#     # Boolean values
#     "boolean_true": "green",
#     "boolean_false": "red",
#     "link": "blue underline",
# }

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
WEBHOOK_ENABLED = False
WEBHOOK_PROVIDER = ""
WEBHOOK_URL = ""
WEBHOOK_USERNAME = ""
WEBHOOK_AVATAR_URL = ""
WEBHOOK_STATUS_NOTIFICATION = False
WEBHOOK_ERROR_NOTIFICATION = False
WEBHOOK_HEADERS = {}
WEBHOOK_TEMPLATE = {}
WEBHOOK_TRANSFORMS = []
NTFY_ACCESS_TOKEN = ""
LOL_CHECK_INTERVAL = 0
LOL_ACTIVE_CHECK_INTERVAL = 0
INCLUDE_FORBIDDEN_MATCHES = False
LIVENESS_CHECK_INTERVAL = 0
LIVENESS_REMINDER_SECONDS = 0
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
TRUNCATE_CHARS = 0
HORIZONTAL_LINE = 0
CLEAR_SCREEN = False
COLORED_OUTPUT = True
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
DIAGNOSTICS_GUIDE_URL = f"{DOCS_BASE_URL}/troubleshooting/#verbose-and-debug-output"
SECRETS_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#storing-secrets"
OUTPUT_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#output-and-files"
USAGE_GUIDE_URL = f"{DOCS_BASE_URL}/usage/"
WEBHOOK_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#webhook-settings"
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
SECRET_KEYS = ("RIOT_API_KEY", "SMTP_PASSWORD", "WEBHOOK_URL", "NTFY_ACCESS_TOKEN")

# Secrets whose length is a fixed, published property of the credential itself. A Riot API key is the RGAPI-
# prefix plus a UUID, and a truncated paste is the usual way one arrives broken, so the length diagnoses that
# without revealing anything the format does not already. A password the user chose reports presence only
FIXED_LENGTH_SECRET_KEYS = frozenset(("RIOT_API_KEY",))

# Shortest secret replaced by plain substring search. Sanitizing runs over normal monitoring output, so a
# short value such as a simple SMTP password would otherwise redact ordinary words like champion names.
# Every credential this tool handles is far longer, and shorter ones stay covered by the shape patterns
# in sanitize_error_text that match the assignment and header forms an error can actually expose.
MIN_REDACTABLE_SECRET_LENGTH = 12

# One short retry absorbs a transient failure without waiting a whole polling interval
TRANSIENT_RETRY_SECONDS = 5
# How long a failure the tool can retry away must last before it is alerted, a failure it cannot is alerted at once
ERROR_ALERT_AFTER_SECONDS = 300  # 5 minutes

# Riot names its own wait on a rate limit, but a header the tool cannot vouch for is not allowed to stall a run
RIOT_MAX_RETRY_AFTER_SECONDS = 3600.0

stdout_bck = None
csvfieldnames = ['Match Start', 'Match Stop', 'Duration', 'Game Mode', 'Victory', 'Kills', 'Deaths', 'Assists', 'Champion', 'Level', 'Role', 'Lane', 'Team 1', 'Team 2']

CLI_CONFIG_PATH = None

# Secrets already exported when the process started, which a dotenv file must not overwrite
EXPORTED_SECRET_KEYS = frozenset()

# Secrets supplied as command line arguments, which override every other source
COMMAND_LINE_SECRET_KEYS = frozenset()

# The one-shot commands that only write a secret, so the other early-exit flags do not swallow them
SECRET_ACTION_FLAGS = ("--set-riot-api-key", "--set-smtp-password", "--set-webhook-url")

# Set when --config-file is given the literal string "none", which switches off the search rather than naming a file
CONFIG_DISCOVERY_DISABLED = False

# The exception the last connectivity check raised, so a quiet caller can classify what it did not print
LAST_CONNECTIVITY_ERROR = None

# One retry, because an alert that has already waited out a backoff is stale news
WEBHOOK_MAX_ATTEMPTS = 2
WEBHOOK_MAX_RETRY_AFTER_SECONDS = 5.0
WEBHOOK_FALLBACK_RETRY_SECONDS = 1.0
WEBHOOK_TIMEOUT_SECONDS = 10

# Discord's own documented limits, applied before sending so a long value is shortened rather than rejected
WEBHOOK_EMBED_TITLE_LIMIT = 256
WEBHOOK_EMBED_DESCRIPTION_LIMIT = 4096

# The Discord embed stripe, by what the alert reports. League of Legends gold, with a green start,
# a grey stop and the family's shared red for a failure
WEBHOOK_EVENT_COLORS = {"status": 0x3CB371, "error": 0xE74C3C}
WEBHOOK_DEFAULT_COLOR = 0xC8AA6E

# ntfy rejects a body over 4 KB outright, so it is cut with a marker instead
NTFY_MESSAGE_LIMIT_BYTES = 4095
NTFY_TRUNCATION_SUFFIX = "\n\n[Notification truncated to fit ntfy's 4 KB message limit]"

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
from email.utils import parsedate_to_datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import argparse
import ast
import csv
import platform
import re
import ipaddress
import math
import asyncio
import html
import importlib.util
try:
    import aiohttp
    from pulsefire.clients import RiotAPIClient
except ModuleNotFoundError:
    raise SystemExit("Error: Couldn't find the Pulsefire library !\n\nTo install it, run:\n    pip3 install pulsefire\n\nOnce installed, re-run this tool. For more help, visit:\nhttps://pulsefire.iann838.com/usage/basic/installation/")
import functools
import getpass
import shlex
import shutil
import subprocess
import tempfile
import textwrap
import unicodedata
from contextlib import asynccontextmanager, contextmanager
from collections import namedtuple
from pathlib import Path
from urllib.parse import urlsplit
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


# One session for every webhook delivery, so connections are reused across a long run
WEBHOOK_SESSION = req.Session()


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
def render_command(arguments=None, include_paths=True, *, config_path=None, env_path=None):
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


# Returns advice for an optional library that is missing, naming the exact install command for this interpreter
def missing_dependency_advice(package, effect, alternative=""):
    return make_recovery_advice("dependency.missing", f"{effect} because the optional '{package}' library is missing", recovery_fix_with_guide(f"Install it with: {pip_install_command(package)}" + (f". {alternative}" if alternative else ""), INSTALL_GUIDE_URL), False)


# Raised when a private setting cannot be checked or saved safely
class SecretConfigurationError(Exception):
    pass


# Quotes one secret value for lossless parsing by python-dotenv
def _format_dotenv_value(value):
    if not isinstance(value, str):
        raise TypeError("Dotenv secret values must be strings")
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n")
    return f'"{escaped}"'


# Resolves a private dotenv destination without searching parent directories
def resolve_secret_env_path(env_file=None, cwd=None):
    if env_file is not None and str(env_file).casefold() == "none":
        raise SecretConfigurationError("Private secret entry requires a dotenv destination. Replace '--env-file none' with a writable path.")
    base_directory = Path.cwd() if cwd is None else Path(cwd)
    destination = base_directory / ".env" if env_file is None else Path(env_file).expanduser()
    return destination.resolve()


# Checks whether a dotenv file already contains one named assignment
def _dotenv_contains_key(destination, key):
    destination_path = Path(destination)
    if not destination_path.exists():
        return False
    try:
        lines = destination_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        raise SecretConfigurationError(f"Could not read dotenv destination '{destination_path}'. Check that it is a readable UTF-8 file.")
    assignment_pattern = re.compile(rf"^\s*(?:export\s+)?{re.escape(key)}\s*=")
    return any(assignment_pattern.match(line) for line in lines)


# Updates supported secrets in a dotenv file through an atomic replacement
def update_dotenv_file(destination, updates):
    if not hasattr(updates, "items"):
        raise TypeError("Dotenv updates must be a mapping")
    update_items = list(updates.items())
    for key, value in update_items:
        if not isinstance(key, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", key) or key not in SECRET_KEYS:
            raise ValueError(f"Unsupported dotenv key: {key!r}")
        if not isinstance(value, str):
            raise TypeError(f"Dotenv value for {key} must be a string")

    destination_path = Path(destination).expanduser()
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        existing_lines = destination_path.read_text(encoding="utf-8").splitlines() if destination_path.exists() else []
    except (OSError, UnicodeError) as exc:
        raise SecretConfigurationError(f"Could not read dotenv destination '{destination_path}'. Check that it is a readable UTF-8 file.") from exc
    update_keys = {key for key, _ in update_items}
    values_by_key = dict(update_items)
    seen_keys = set()
    output_lines = []
    assignment_pattern = re.compile(r"^(\s*(?:export\s+)?)([A-Za-z_][A-Za-z0-9_]*)\s*=")
    for line in existing_lines:
        match = assignment_pattern.match(line)
        key = match.group(2) if match else None
        written_prefix = match.group(1) if match else ""
        if key not in update_keys:
            output_lines.append(line)
            continue
        if key in seen_keys:
            continue
        seen_keys.add(key)
        # A secret cleared by its owner is removed rather than emptied, so a disabled value cannot linger here
        if not values_by_key[key]:
            continue
        # An "export " the owner wrote is kept, since dropping it changes what a shell sourcing the file exports
        output_lines.append(f"{written_prefix}{key}={_format_dotenv_value(values_by_key[key])}")
    for key, value in update_items:
        if key not in seen_keys and value:
            output_lines.append(f"{key}={_format_dotenv_value(value)}")
            seen_keys.add(key)

    content = "\n".join(output_lines)
    if output_lines:
        content += "\n"
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", prefix=f".{destination_path.name}.", suffix=".tmp", dir=str(destination_path.parent), delete=False) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        if os.name == "posix":
            os.chmod(str(temporary_path), 0o600)
        # No backup is taken here: a copy of the credential being replaced is the one thing not worth keeping
        os.replace(str(temporary_path), str(destination_path))
        temporary_path = None
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return {"path": str(destination_path), "updated_keys": tuple(key for key, _ in update_items)}


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
            debug_print("Secret reload", name=secret, path=str(env_path), **secret_fields(value, secret))


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


# Returns the source each configured secret resolved from, so a debug run and the doctor cannot disagree
def secret_source_labels(env_path=None):
    grouped = zip(("dotenv file", "environment", "configuration file", "command line"), group_secrets_by_source(env_path), strict=True)
    labels = {name: source for source, names in grouped for name in names}
    return {name: labels[name] for name in SECRET_KEYS if name in labels}


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


# Silences debug output while a raw secret is entered or validated, then restores the previous mode
@contextmanager
def debug_output_suppressed():
    global DEBUG_MODE
    previous_debug_mode = DEBUG_MODE
    DEBUG_MODE = False
    try:
        yield
    finally:
        DEBUG_MODE = previous_debug_mode


# Silences debug output for the whole of a function that handles a raw secret
def suppresses_debug_output(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with debug_output_suppressed():
            return func(*args, **kwargs)
    return wrapper


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
    fields = secret_fields(value, key)
    return f"{fields['value']}, {fields['chars']} chars" if fields["chars"] else fields["value"]


# Returns the diagnostic fields describing one secret, keeping the length out of the value so a line still splits on ", "
def secret_fields(value, key=None):
    return {"value": "set" if doctor_value_is_set(value) else "not set", "chars": len(str(value).strip()) if key in FIXED_LENGTH_SECRET_KEYS and doctor_value_is_set(value) else None}


# Returns the secret values long enough to replace wherever they appear, skipping the shipped placeholders
def known_secret_values():
    return [value for value in (globals().get(key) for key in SECRET_KEYS) if isinstance(value, str) and len(value) >= MIN_REDACTABLE_SECRET_LENGTH and not value.startswith("your_")]


# Redacts configured secrets and Riot credentials from one error-shaped value, plus any value not yet stored
def sanitize_error_text(value, extra_secrets=()):
    text = str(value or "")
    entered = [secret for secret in extra_secrets if isinstance(secret, str) and len(secret) >= MIN_REDACTABLE_SECRET_LENGTH]
    for secret in sorted(known_secret_values() + entered, key=len, reverse=True):
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
    "secret.missing", "secret.entry",
    "auth.api_key_invalid",
    "network.unavailable", "network.timeout",
    "riot.rate_limited", "riot.unavailable",
    "target.missing", "target.invalid", "target.region", "target.not_found",
    "smtp.invalid", "smtp.authentication", "smtp.connection",
    "file.exists", "file.unreadable", "file.unwritable",
    "resource.exhausted",
    "webhook.invalid", "webhook.rate_limited", "webhook.rejected", "webhook.connection",
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


# Escapes text for an HTML email body and keeps its line breaks, which HTML would otherwise collapse into spaces
def html_text(text):
    return html.escape(text).replace("\n", "<br>")


# Returns the advice a cancelled secret entry reports, worded the same way by every one-shot secret command
def secret_entry_cancelled_advice(subject, flag, guide_url):
    return make_recovery_advice("secret.entry", f"{subject[:1].upper()}{subject[1:]} setup was cancelled and the dotenv file was not changed", recovery_fix_with_guide(f"Run {flag} again when you have the value ready", guide_url), False)


# Returns the advice a declined secret replacement reports, which is a decision rather than a cancellation
def secret_replacement_declined_advice(subject, flag, guide_url):
    return make_recovery_advice("secret.entry", f"The saved {subject} was left as it is and the dotenv file was not changed", recovery_fix_with_guide(f"Run {flag} again and answer y to replace the saved value", guide_url), False)


# Returns the HTTP status carried by an error, when it has one
def recovery_http_status(error):
    status = getattr(error, "status", None)
    if not isinstance(status, int):
        status = getattr(getattr(error, "response", None), "status_code", None)
    return status if isinstance(status, int) else None


# Yields the exception and each cause or context up to max_depth, to walk an exception chain
def iter_exc_chain(error, max_depth=8):
    current = error
    for _ in range(max_depth):
        if current is None:
            return
        yield current
        current = getattr(current, "__cause__", None) or getattr(current, "__context__", None)


# Reports whether any exception in the chain is the local file descriptor limit rather than a remote failure
def is_too_many_open_files(error):
    for current in iter_exc_chain(error):
        if isinstance(current, OSError) and getattr(current, "errno", None) == 24:
            return True
        message = str(current).lower()
        if "too many open files" in message or re.search(r"\berrno 24\b", message):
            return True
    return False


# Returns the next step for a failure no rule recognized, since a run already printing the technical cause cannot be told to re-run for it
def unknown_failure_fix():
    return "Check the monitoring log for the failing request, then open an issue with this output if it continues" if DEBUG_MODE else "Re-run with --debug to see the technical cause"


# Maps one exception plus its HTTP status and calling context to stable recovery advice
def classify_recovery_error(error=None, context="runtime", detail=""):
    if isinstance(error, RecoveryError):
        return error.advice
    # Both are matched, since a caller that adds context would otherwise hide the error text the rules read
    message = " ".join(part for part in (str(detail or ""), str(error or "")) if part).lower()
    safe_detail = sanitize_error_text(detail or error) if (detail or error) else ""
    status = recovery_http_status(error)

    # Builds one piece of advice, attaching the guide line only where a page actually covers the row
    def advice(code, summary, fix, retryable, guide_url=None):
        return make_recovery_advice(code, summary, recovery_fix_with_guide(fix, guide_url) if guide_url else fix, retryable, safe_detail)

    # Checked ahead of every context, since a local descriptor limit is not a failure of whatever call hit it
    if error is not None and is_too_many_open_files(error):
        return advice("resource.exhausted", "This process ran out of file descriptors, which is a local limit and not a Riot problem", "Raise the file descriptor limit, for example with 'ulimit -n 4096', or set LimitNOFILE= if you run under systemd, then restart the tool", False, DIAGNOSTICS_GUIDE_URL)

    if context == "config":
        if "does not exist" in message:
            return advice("config.missing", safe_detail or "The configuration file was not found", f"Create one with '{render_command(['--generate-config', DEFAULT_CONFIG_FILENAME], include_paths=False)}' or correct the --config-file path", False, CONFIG_FILE_GUIDE_URL)
        return advice("config.invalid", safe_detail or "The configuration file could not be read", f"Correct the reported line, or start from a fresh template with '{render_command(['--generate-config', DEFAULT_CONFIG_FILENAME], include_paths=False)}'", False, CONFIG_FILE_GUIDE_URL)

    if context == "webhook":
        if status == 429 or "rate limit" in message:
            return advice("webhook.rate_limited", "The webhook service is rate limiting deliveries", "Reduce how many alert types are enabled, or wait for the service to accept deliveries again", True, WEBHOOK_GUIDE_URL)
        if any(term in message for term in ("must contain", "must be discord", "could not be formatted", "header", "priority", "tags")):
            return advice("webhook.invalid", safe_detail or "The webhook configuration is not usable", f"Check WEBHOOK_URL, WEBHOOK_PROVIDER and the alert settings, then verify with '{render_command(['--send-test-webhook'])}'", False, WEBHOOK_GUIDE_URL)
        if any(term in message for term in ("could not be reached", "connection", "timed out")):
            return advice("webhook.connection", "The webhook service could not be reached", "Check connectivity and the webhook host, then try again", True, WEBHOOK_GUIDE_URL)
        return advice("webhook.rejected", safe_detail or "The webhook service refused the delivery", f"Confirm the webhook still exists and the URL is current, then verify with '{render_command(['--send-test-webhook'])}'", status is not None and status >= 500, WEBHOOK_GUIDE_URL)

    if context in ("set_riot_api_key", "set_smtp_password", "set_webhook_url"):
        flag = {"set_riot_api_key": "--set-riot-api-key", "set_smtp_password": "--set-smtp-password"}.get(context, "--set-webhook-url")
        guide = {"set_riot_api_key": RIOT_API_KEY_GUIDE_URL, "set_smtp_password": SMTP_GUIDE_URL}.get(context, WEBHOOK_GUIDE_URL)
        if "interactive terminal" in message:
            return advice("unknown", f"{flag} requires an interactive terminal", f"Run {flag} in a terminal window so the value stays hidden while you paste it", False, guide)
        if "cancelled" in message:
            return advice("secret.entry", safe_detail or "Setup was cancelled", f"Run {flag} again when you have the value ready", False, guide)
        if any(term in message for term in ("could not save", "file permissions", "writable path", "dotenv destination")):
            return advice("file.unwritable", safe_detail or "The private settings file could not be updated", "Check file permissions or choose another path with --env-file PATH", False, SECRETS_GUIDE_URL)
        if context == "set_riot_api_key":
            return advice("auth.api_key_invalid", safe_detail or "Riot rejected the entered API key", f"A development key expires 24 hours after it is issued, so copy a fresh one from {RIOT_API_KEY_REGISTRATION_URL} then run {flag} again", False, guide)
        if context == "set_smtp_password":
            if "settings are incomplete" in message:
                return advice("smtp.invalid", safe_detail or "The mail server settings are incomplete", "Set SMTP_HOST, SMTP_USER, SENDER_EMAIL and RECEIVER_EMAIL first", False, guide)
            return advice("smtp.authentication", safe_detail or "The mail server did not accept the password", f"Use an app password when the provider requires one then run {flag} again", False, guide)
        return advice("webhook.invalid", safe_detail or "The webhook URL was not changed", f"Copy a complete Discord or ntfy webhook URL then run {flag} again", False, guide)

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
            return advice("network.timeout", "The Riot API request timed out", "Check connectivity then try again", True, DIAGNOSTICS_GUIDE_URL)
        if status in (401, 403) or "unauthorized" in message or "forbidden" in message:
            return advice("auth.api_key_invalid", "Riot rejected the configured API key", f"A development key expires 24 hours after it is issued, so copy a fresh one from {RIOT_API_KEY_REGISTRATION_URL}", False, RIOT_API_KEY_GUIDE_URL)
        if "region_to_continent" in message:
            return advice("target.region", safe_detail or REGION_INPUT_ERROR, f"Pass a {REGION_FORMS}, which is the short code and not the display name", False, REGION_GUIDE_URL)
        if "name and tagline" in message or "name#tag" in message:
            return advice("target.invalid", safe_detail or "That is not a complete Riot ID", f"Pass a {RIOT_ID_FORMS}, where the part after the # is the tag line and not the region", False, USAGE_GUIDE_URL)
        return advice("target.not_found", safe_detail or "Riot has no account for that Riot ID", "Check the game name and the tag line, since a renamed account cannot be monitored", False, USAGE_GUIDE_URL)

    if context == "connectivity":
        # Classified from the error, because the detail names the endpoint rather than the failure. No guide,
        # since no page covers this check and the doctor report already ends with the troubleshooting link
        cause = str(error or "").lower()
        if "timed out" in cause or "timeout" in cause:
            return advice("network.timeout", "The connectivity endpoint did not answer in time", "Check network, DNS, proxy and CHECK_INTERNET_URL settings", True)
        return advice("network.unavailable", "The connectivity endpoint could not be reached", "Check network, DNS, proxy and CHECK_INTERNET_URL settings", True)

    if context == "email":
        if any(term in message for term in ("authentication", "auth", "username and password", "535")):
            return advice("smtp.authentication", "The SMTP server rejected the sign-in", "Check SMTP_USER and SMTP_PASSWORD, and use an app password if the provider requires one", False, SMTP_GUIDE_URL)
        if any(term in message for term in ("settings are incorrect", "incomplete", "invalid")):
            return advice("smtp.invalid", safe_detail or "The SMTP settings are incomplete or invalid", "Check SMTP_HOST, SMTP_PORT, SENDER_EMAIL and RECEIVER_EMAIL in the configuration file", False, SMTP_GUIDE_URL)
        return advice("smtp.connection", "The SMTP server could not be reached", "Check SMTP_HOST, SMTP_PORT and SMTP_SSL, then confirm the host is reachable from this machine", True, SMTP_GUIDE_URL)

    if context == "file.exists":
        return advice("file.exists", safe_detail or "The destination file already exists", f"Re-run with --force to replace it after a timestamped backup, or write to a different path with '{render_command(['--generate-config', '<new-file>'], include_paths=False)}'", False, CONFIG_FILE_GUIDE_URL)

    if context == "file.unwritable":
        # The wizard reaches this either because a destination was switched off or because the path cannot be written
        if "nowhere to write the private settings" in message:
            return advice("file.unwritable", safe_detail or "--setup has nowhere to write the private settings", "Replace '--env-file none' with a writable path, or drop the flag to write .env in the current directory", False, SECRETS_GUIDE_URL)
        if "nowhere to write the configuration" in message:
            return advice("file.unwritable", safe_detail or "--setup has nowhere to write the configuration", f"Replace '--config-file none' with a writable path, or drop the flag to write {DEFAULT_CONFIG_FILENAME} in the current directory", False, CONFIG_FILE_GUIDE_URL)
        return advice("file.unwritable", safe_detail or "A setup destination cannot be written", "Choose a path inside an existing directory you can write to with --config-file or --env-file", False, CONFIG_FILE_GUIDE_URL)

    if context == "file":
        # The only read failure reaching this branch is an existing dotenv file the secret writer could not decode
        if any(term in message for term in ("could not read dotenv", "unreadable", "not valid utf-8")):
            return advice("file.unreadable", safe_detail or "The private settings file could not be read", "Check that the file is readable UTF-8 text, or choose another path with --env-file", False, SECRETS_GUIDE_URL)
        return advice("file.unwritable", safe_detail or "A file the tool writes could not be opened", "Check that the directory exists and is writable, or choose another path", False, OUTPUT_GUIDE_URL)

    # Runtime, which is the monitoring loop and every Riot API call it makes
    if status == 429 or "rate limit" in message or "too many requests" in message:
        return advice("riot.rate_limited", "Riot is rate limiting requests", "The tool will wait and retry. Increase the polling intervals if this repeats", True, INTERVALS_GUIDE_URL)
    if status in (401, 403) or "forbidden" in message or "unauthorized" in message:
        return advice("auth.api_key_invalid", "Riot rejected the configured API key", f"A development key expires 24 hours after it is issued, so copy a fresh one from {RIOT_API_KEY_REGISTRATION_URL}", False, RIOT_API_KEY_GUIDE_URL)
    if status == 404 or "not found" in message:
        return advice("target.not_found", "Riot has no account for the monitored Riot ID", "Check the game name and the tag line, since a renamed account cannot be monitored", False, USAGE_GUIDE_URL)
    if (status is not None and status >= 500) or any(term in message for term in ("internal server error", "service unavailable", "bad gateway")):
        return advice("riot.unavailable", "The Riot API is temporarily unavailable", "This is usually a Riot outage. The tool will keep retrying", True, DIAGNOSTICS_GUIDE_URL)
    if "timed out" in message or "timeout" in message:
        return advice("network.timeout", "The Riot API request timed out", "Check connectivity. The tool will keep retrying", True, DIAGNOSTICS_GUIDE_URL)
    if any(term in message for term in ("connection", "name resolution", "network is unreachable", "no connectivity")):
        return advice("network.unavailable", "Riot could not be reached", "Check connectivity, DNS and any proxy. The tool will keep retrying", True, DIAGNOSTICS_GUIDE_URL)
    return advice("unknown", safe_detail or "The request could not be completed", unknown_failure_fix(), True, DIAGNOSTICS_GUIDE_URL)


# Renders one built advice as the shared Error, To fix and optional Technical detail block
def render_recovery_advice(advice, debug=None, retry_note="", with_fix=True, label="Error"):
    lines = [f"* {label}: {advice.summary}" + (f" ({retry_note})" if retry_note else "")]
    if with_fix:
        lines.append(f"To fix: {advice.fix}")
        # A detail that only repeats the summary spends a line saying nothing, which is section 15.52's rule for rows
        if (DEBUG_MODE if debug is None else debug) and advice.detail and advice.detail != advice.summary:
            lines.append(f"Technical detail: {sanitize_error_text(advice.detail)}")
    return "\n".join(lines)


# Classifies one failure and renders it through the shared recovery block
def render_recovery_error(error=None, context="runtime", debug=None, detail="", retry_note="", with_fix=True, label="Error"):
    return render_recovery_advice(classify_recovery_error(error, context, detail), debug, retry_note, with_fix, label)


# Prints one built advice through the shared recovery block and returns it
def print_recovery_advice(advice, debug=None, retry_note="", with_fix=True, label="Error"):
    print(render_recovery_advice(advice, debug, retry_note, with_fix, label))
    return advice


# Classifies one failure, prints it through the shared recovery block and returns its stable advice
def print_recovery_error(error=None, context="runtime", debug=None, detail="", retry_note="", with_fix=True, label="Error"):
    return print_recovery_advice(classify_recovery_error(error, context, detail), debug, retry_note, with_fix, label)


# Decides how a lasting failure is reported: in full when it is new, then on the liveness cadence while it lasts
# How long a reported failure may go on before the run reminds about it, whatever the liveness banner is set to
OUTAGE_REMINDER_SECONDS = 3600  # 1 hour


# Returns the family a failure code belongs to, so the DNS and timeout failures of one internet outage count as one
def outage_family(code):
    return "network" if str(code or "").startswith("network.") else str(code or "")


class OutageReporter:
    # Starts with no failure recorded and reports a new retryable failure once confirm_checks checks in a row failed
    def __init__(self, confirm_checks=1):
        self.confirm_checks = max(1, confirm_checks)
        self.code = None
        self.since = 0
        self.reported_at = 0
        self.failures = 0
        self.reported = False

    # Records one failed check and returns "full" when the failure is to be reported in full, "changed" when a
    # reported outage moved to another failure family, "reminder" once OUTAGE_REMINDER_SECONDS passed since the
    # last report or "" while nothing new is to be said
    def failed(self, advice):
        now = int(time.time())
        if not self.code:
            self.since = now
        self.failures += 1
        changed = self.code is not None and outage_family(advice.code) != outage_family(self.code)
        self.code = advice.code
        if not self.reported:
            # A failure the tool cannot retry away is reported at once, one it can waits for the next check to confirm it
            if advice.retryable and self.failures < self.confirm_checks:
                return ""
            self.reported = True
            self.reported_at = now
            return "full"
        if changed:
            self.reported_at = now
            return "changed" if advice.retryable else "full"
        # Timed rather than counted, because a failing run usually retries on a different interval than a healthy one
        if now - self.reported_at >= OUTAGE_REMINDER_SECONDS:
            self.reported_at = now
            return "reminder"
        return ""

    # Clears the failure after a successful check and returns how long it lasted, or None when nothing was reported
    def recovered(self):
        lasted = int(time.time()) - self.since if self.code and self.reported else None
        self.code = None
        self.since = 0
        self.reported_at = 0
        self.failures = 0
        self.reported = False
        return lasted


# Reports that nothing changed, so a quiet run still says it is alive on the liveness cadence
def print_liveness_banner(message):
    print(f"* {sanitize_error_text(message)}")
    print_cur_ts("Liveness check, timestamp:\t")


# Reminds about a lasting failure once an hour, so a broken run still says it is alive without repeating itself
def print_outage_liveness(target, advice, since, failures=0):
    count = f", {failures} failed {'check' if failures == 1 else 'checks'}" if failures else ""
    print(f"* Monitoring degraded for {target}. {advice.summary} since {get_date_from_ts(since)}{count}")
    print_cur_ts("Liveness check, timestamp:\t")


# Notes that a reported outage now fails differently, in one line rather than a second full report
def print_outage_change(target, advice):
    print(f"* Monitoring failure changed for {target}. {advice.summary}")


# Reports that a failure cleared, since a throttled failure no longer stops printing when it is over
def print_outage_recovery(target, lasted):
    print(f"* Monitoring recovered for {target} after {display_time(max(1, lasted))}")
    print_cur_ts("Timestamp:\t\t\t")


# Returns the wait Riot asked for on a rate limit, falling back to the polling interval when it named none
def riot_retry_after_seconds(error, fallback):
    headers = getattr(getattr(error, "response", None), "headers", {}) or {}
    candidates = [headers.get("Retry-After"), headers.get("X-Rate-Limit-Retry-After")] if hasattr(headers, "get") else []
    for candidate in candidates:
        seconds = parse_retry_after_seconds(candidate)
        if seconds is not None:
            return max(1, int(round(min(max(0.0, seconds), RIOT_MAX_RETRY_AFTER_SECONDS))))
    # The fallback is the tool's own polling interval, so the cap on what a service asked for does not apply to it
    return max(1, int(round(fallback)))


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


# Reads one hidden answer with Python's default Ctrl+C behavior. Kept apart from the visible reader so a
# secret typed here is never confused with an ordinary answer that is later printed back to the user
def read_secret_interactively(reader, *args, **kwargs):
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


# Asks Riot for the platform status, which is the cheapest call that answers whether the key is accepted
async def riot_api_key_probe(region):
    async with riot_api_client() as client:
        return await client.get_lol_status_v4_platform_data(region=region)


# Asks Riot for the account behind one Riot ID, the same lookup monitoring makes before it starts
async def riot_account_probe(riot_id, region):
    riotid_name, riotid_tag = riot_id.split("#", 1)
    async with riot_api_client() as client:
        return await client.get_account_v1_by_riot_id(region=region_continent(region), game_name=riotid_name, tag_line=riotid_tag)


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


# The only escape sequence this tool emits is an SGR colour or style change, so it is the only one worth keeping
SGR_SEQUENCE_RE = re.compile(r"\x1b\[[0-9;]*m")

# Internal flag and style map for colour handling
COLOR_ENABLED = False
_COLOR_STYLES: dict = {}

# Default built-in colour theme. Values can be overridden via COLOR_THEME in the configuration file
DEFAULT_COLOR_THEME = {
    # Headings and commands the tool tells you to run
    "header": "bright_cyan",
    "section": "bright_white",
    # Identity
    "username": "bright_cyan underline",
    "id": "bright_magenta",
    # Playing status values
    "status_active": "green",
    "status_inactive": "red",
    # Match information
    "champion": "bright_yellow",
    "game_mode": "yellow",
    "rank": "bright_green",
    "duration": "green",
    # Dates
    "date": "magenta",
    "date_range": "magenta",
    # Timestamps
    "timestamp_label": "",
    "timestamp_value": "cyan",
    # Notices
    "info": "cyan",
    "warning": "yellow",
    "error": "red",
    "signal": "yellow",
    "email": "bright_cyan",
    "webhook": "bright_blue",
    # Boolean values
    "boolean_true": "green",
    "boolean_false": "red",
    "link": "blue underline",
}

# A block style paints a whole line and keeps the colours already inside it, so a value drawn in the block's
# own colour would disappear inside it and the two sets are kept disjoint. Warnings are not on the block
# list: yellow is the game mode colour, so a warning marks its own opening word instead of painting the line
BLOCK_STYLE_PARTS = ("error", "email", "webhook", "info")
NAME_STYLE_PARTS = ("username", "id", "champion", "game_mode", "rank", "link")

ANSI_RESET = "\033[0m"

# Mapping of style names to ANSI SGR codes
_STYLE_CODES = {
    "bold": "1",
    "dim": "2",
    "underline": "4",
    "blink": "5",
    "black": "30",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
    "bright_black": "90",
    "bright_red": "91",
    "bright_green": "92",
    "bright_yellow": "93",
    "bright_blue": "94",
    "bright_magenta": "95",
    "bright_cyan": "96",
    "bright_white": "97",
}

# Output labels whose value is coloured with one theme style, longest label first so a prefix cannot win. Of the
# four rows that describe a match, only the game mode is coloured: the queue, map and game type sit right under
# it and painting all four the same turned the block into a wall of one colour that marked nothing
_LABEL_STYLES = (
    (("Riot ID (name#tag):", "Summoner name:", "Target:"), "username"),
    (("Riot PUUID:", "Match ID:"), "id"),
    (("Champion:",), "champion"),
    (("Game mode:",), "game_mode"),
    (("Match duration:", "Match finished:"), "duration"),
)

# Pre-compiled regexes used for line-level colourisation
# The monitored player named inside a sentence, tagged only after the words that introduce one
_USER_TAG_RE = re.compile(r"((?:LoL user|Monitoring user|for user))([\t ]+)([^\s,.:!']+)")
# A labelled or key=value 'user' field names its value directly, which is the shape the debug trace uses
_USER_FIELD_RE = re.compile(r"(\buser)(:[\t ]+|=)([^\s,]+)")
# One roster entry: the player who was in the match and the champion they played
_ROSTER_ENTRY_RE = re.compile(r"^(-\s+)(.+?)(\s+\()([^()]+)(\)\s*)$")
# One champion mastery entry, whose name column is padded to a fixed width before the level it reports
_MASTERY_ENTRY_RE = re.compile(r"^(\s+\d+\.\s+)([^:]+)(:\s+Level\s+\d+\b)")
# A ranked standing, which is a tier and division or the word for having none
_RANK_RE = re.compile(r"\b(?:IRON|BRONZE|SILVER|GOLD|PLATINUM|EMERALD|DIAMOND|MASTER|GRANDMASTER|CHALLENGER)(?:\s+(?:I|II|III|IV))?\b|\bUnranked\b")
_DURATION_RE = re.compile(r"~?\b[0-9]{1,20}[ \t]{1,20}(?:seconds?|minutes?|hours?|days?|weeks?|months?|years?)\b", re.IGNORECASE)
_LONG_DATE_RE = re.compile(r"\b(?:\w{3}\s+)?\d{1,2}\s+\w{3}(?:\s+\d{2,4})?[\s,]*\d{2}:\d{2}(:\d{2})?(\s*[AP]M)?\b", re.IGNORECASE)
_TIME_ONLY_RE = re.compile(r"(?<![\w:])(~?(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?(?:\s*[AP]M)?)(?![\w:])", re.IGNORECASE)
_DATE_RANGE_RE = re.compile(r"\b\w{3}\s+\d{1,2}\s+\w{3}(?:\s+\d{2,4})?[\s,]*\d{2}:\d{2}(:\d{2})?(\s*[AP]M)?\s*-\s*\d{2}:\d{2}(:\d{2})?(\s*[AP]M)?\b", re.IGNORECASE)
# Sentence punctuation, a closing bracket or a closing quote right after a link is not part of it
_URL_RE = re.compile(r"(https?://[^\s\]]+?)(?=[.,;:!?'\")>]*(?:[\s\]]|$))")
_BOOLEAN_TRUE_RE = re.compile(r"\bTrue\b|\bEnabled\b")
_BOOLEAN_FALSE_RE = re.compile(r"\bFalse\b|\bDisabled\b")
# The TLS row reports a word rather than a boolean, and its off state is the one setting that weakens
# a security property, so the state word is coloured like a boolean
_TLS_STATE_RE = re.compile(r"^(\* TLS verification:\s+)(On|Off)(.*)$")
_NOTIFICATION_SUMMARY_STATE_RE = re.compile(r"^(\* Notifications \((?:email|webhook)\):\s+)(On|Off)(.*)$")
# The two events this tool exists to report
_IN_GAME_RE = re.compile(r"\bis in game now\b")
_STOPPED_PLAYING_RE = re.compile(r"\bstopped playing\b|\bis not in game currently\b")
# Words that report a problem. The same word used as a key in a 'key=value' diagnostic detail names a setting
# such as 'timeout=15', so it leaves its line unpainted
_ERROR_KEYWORD_RE = re.compile(r"\b(?:failures?|failed|timeout)\b(?!\s*=)")
# A debug trace line records what the tool tried, including attempts that fail and are then handled, so it
# keeps its own colours instead of being painted as the failure it reports
_DEBUG_LINE_RE = re.compile(r"^\[debug \d{2}:\d{2}:\d{2}\]")
# Doctor status markers, coloured with the theme parts the report already names for them
_DOCTOR_MARK_RE = re.compile(r"^\[(PASS|WARN|FAIL|SKIP)\]")
# A heading that opens a block of report rows, written as a label with nothing after it
_SECTION_HEADING_RE = re.compile(r"^(?:Ranked Information|Banned champions|User last played match):?$")
# The doctor report's own headings, which sit on a line of their own. A test pins these against DOCTOR_SECTIONS
_REPORT_TITLE_RE = re.compile(r"^(?:Doctor|Summary|Next steps)$")
_REPORT_SECTION_RE = re.compile(r"^(?:Environment|Configuration|Authentication|Connectivity|Target|Notifications)$")
# A quoted value, with at least one word character so a run of ASCII art between two apostrophes is not read
# as a name. The closing quote has to be followed by whitespace, punctuation or the end of the line, so a
# name's own apostrophe does not end it early: "Tom Clancy's Rainbow Six Siege"
_QUOTED_CONTENT_RE = re.compile(r"(')([^\n]*?\w[^\n]*?)(')(?=[\s.,;:!?)\]]|$)")
# A quoted value is only a name where the words before it introduce one, since most quoted values this tool
# prints are file paths, region codes and setting names
_QUOTED_NAME_CONTEXT_RE = re.compile(r"\b(?:for|user)\s+$", re.IGNORECASE)
# Quoted values shaped like a file name or a filesystem path stay plain, since a log or CSV destination is
# not a name
_QUOTED_FILE_LIKE_RE = re.compile(r"^[~.]?[\\/]|^[A-Za-z]:[\\/]|\.[A-Za-z0-9]{1,8}$")
# A quoted '<name>' inside a printed command is the placeholder the reader has to replace, not a name
_QUOTED_PLACEHOLDER_RE = re.compile(r"^<[^<>]*>$")
# A quoted command-line option is an instruction to retype, not a name
_QUOTED_OPTION_RE = re.compile(r"^-")
# A quoted piece of a URL. Only a leading '?' or '&' counts, so a name may end in a question mark
_QUOTED_URL_PART_RE = re.compile(r"^[?&]|://")
# The opening word of a warning and the name of a reported signal, marked instead of painting the line
_WARNING_LABEL_RE = re.compile(r"^\*+\s*(Warning:|Note:|Caution:)")
_SIGNAL_NAME_RE = re.compile(r"(?<=^\* Signal )(\w+)(?= received$)")


# Builds an ANSI escape sequence from a style description string
def _build_ansi_sequence(style_str):
    if not style_str:
        return ""
    codes = [_STYLE_CODES[part] for part in re.split(r"[+ ]+", style_str.strip().lower()) if part in _STYLE_CODES]
    return f"\033[{';'.join(codes)}m" if codes else ""


# Detects whether the given output stream likely supports ANSI colours
def _stream_supports_color(stream):
    if not hasattr(stream, "isatty") or not stream.isatty():
        return False
    if os.getenv("NO_COLOR"):
        return False
    if os.getenv("TERM", "").lower() in ("", "dumb", "unknown"):
        return False
    # A piped stdin usually means the run is inside a pipeline such as tee, where escapes would reach a file
    if hasattr(sys.stdin, "isatty") and not sys.stdin.isatty():
        return False
    return True


# Initializes colour handling from the configured theme and the capabilities of the given stream
def init_color_output(stream):
    global COLOR_ENABLED, _COLOR_STYLES
    COLOR_ENABLED = bool(globals().get("COLORED_OUTPUT", False)) and _stream_supports_color(stream)
    if not COLOR_ENABLED:
        _COLOR_STYLES = {}
        return
    user_theme = globals().get("COLOR_THEME") if isinstance(globals().get("COLOR_THEME"), dict) else {}
    theme = {**DEFAULT_COLOR_THEME, **(user_theme or {})}
    _COLOR_STYLES = {name: sequence for name, sequence in ((name, _build_ansi_sequence(style)) for name, style in theme.items()) if sequence}


# Applies a configured colour style, named by the logical part, to the given text
def colorize(part, text):
    if not COLOR_ENABLED:
        return text
    start = _COLOR_STYLES.get(part)
    return f"{start}{text}{ANSI_RESET}" if start else text


# Returns a coloured representation of a textual playing status, leaving an unrecognised one plain
def colorize_status(status_text):
    status = (status_text or "").strip().lower()
    if status in ("yes", "active", "in game"):
        return colorize("status_active", status_text)
    if status in ("no", "inactive", "offline"):
        return colorize("status_inactive", status_text)
    return status_text


# Splits a recognized output label from its value without applying a backtracking expression
def _split_output_label(value, labels):
    body = value.rstrip("\n")
    cursor = len(body) - len(body.lstrip())
    if body[cursor:cursor + 1] == "*":
        cursor += 1
        cursor += len(body[cursor:]) - len(body[cursor:].lstrip())
    for label in labels:
        if not body.startswith(label, cursor):
            continue
        value_start = cursor + len(label)
        value_start += len(body[value_start:]) - len(body[value_start:].lstrip())
        if value_start == cursor + len(label):
            return None
        return body[:value_start], body[value_start:]
    return None


# Applies a block style while preserving the highlights already inside the line
def _apply_style_nested(line, style_name):
    start_style = _COLOR_STYLES.get(style_name)
    if not start_style:
        return line
    # Each internal reset returns to the block style instead of to plain, so one value cannot end the block
    line = f"{start_style}{line}{ANSI_RESET}"
    line = line.replace(ANSI_RESET, f"{ANSI_RESET}{start_style}")
    if line.endswith(f"{ANSI_RESET}{start_style}"):
        line = line[:-len(start_style)]
    return line


# Applies one substitution only to the parts of a line that are not already inside a colour span, so a later
# rule cannot reclaim text an earlier rule has already coloured
def _sub_outside_color(pattern, replacement, line):
    if ANSI_RESET not in line:
        return pattern.sub(replacement, line)
    parts = []
    position = 0
    inside = False
    for match in SGR_SEQUENCE_RE.finditer(line):
        segment = line[position:match.start()]
        parts.append(segment if inside else pattern.sub(replacement, segment))
        parts.append(match.group(0))
        inside = match.group(0) != ANSI_RESET
        position = match.end()
    trailing = line[position:]
    parts.append(trailing if inside else pattern.sub(replacement, trailing))
    return "".join(parts)


# Colours one quoted value as a name, unless what is between the quotes says it is something else
def _colorize_quoted_name(match, style_name):
    name = match.group(2)
    if _QUOTED_FILE_LIKE_RE.search(name) or _QUOTED_PLACEHOLDER_RE.match(name) or _QUOTED_OPTION_RE.match(name) or _QUOTED_URL_PART_RE.search(name):
        return match.group(0)
    # What sits right before the quote decides whether this is a name at all
    if not _QUOTED_NAME_CONTEXT_RE.search(match.string[:match.start()]):
        return match.group(0)
    return f"{match.group(1)}{colorize(style_name, name)}{match.group(3)}"


# Applies colour rules to a single output line
def _colorize_line(line):
    lowered = line.lower()

    # The notification summary row carries its own On/Off state word
    notification_match = _NOTIFICATION_SUMMARY_STATE_RE.match(line)
    if notification_match:
        prefix, state, suffix = notification_match.groups()
        return f"{prefix}{colorize('boolean_true' if state == 'On' else 'boolean_false', state)}{suffix}"

    # The TLS row reports its state as a word rather than as a boolean
    tls_match = _TLS_STATE_RE.match(line)
    if tls_match:
        prefix, state, suffix = tls_match.groups()
        return f"{prefix}{colorize('boolean_true' if state == 'On' else 'boolean_false', state)}{suffix}"

    # Doctor status markers keep the rest of their line plain so long labels stay readable
    doctor_match = _DOCTOR_MARK_RE.match(line)
    if doctor_match:
        return colorize(DOCTOR_MARK_STYLES[doctor_match.group(1)], doctor_match.group(0)) + line[doctor_match.end():]

    # A heading names what follows rather than reporting a value
    body = line.rstrip("\n")
    newline = "\n" if line.endswith("\n") else ""
    if _REPORT_TITLE_RE.match(body):
        return colorize("header", body) + newline
    if _SECTION_HEADING_RE.match(body) or _REPORT_SECTION_RE.match(body):
        return colorize("section", body) + newline

    # Timestamp lines get a dimmed label and a coloured value
    labeled_value = _split_output_label(line, ("Liveness check, timestamp:", "Timestamp:"))
    if labeled_value:
        label, rest = labeled_value
        return f"{colorize('timestamp_label', label)}{colorize('timestamp_value', rest)}" + ("\n" if line.endswith("\n") else "")

    # Any '<something> URL:' row is a link, checked before the label table so a URL row is not read as a name
    if _split_output_label(line, ("URL:",)) or " URL:" in line:
        return _sub_outside_color(_URL_RE, lambda mo: colorize("link", mo.group(0)), line)

    # Rows whose value reports whether something happened
    labeled_value = _split_output_label(line, ("Victory:",))
    if labeled_value:
        label, status = labeled_value
        return f"{label}{colorize_status(status)}" + ("\n" if line.endswith("\n") else "")

    # Labelled match and account rows keep their label plain and colour only the value
    for labels, style_name in _LABEL_STYLES:
        labeled_value = _split_output_label(line, labels)
        if not labeled_value:
            continue
        label, rest = labeled_value
        return f"{label}{colorize(style_name, rest)}" + ("\n" if line.endswith("\n") else "")

    # One roster entry names a player and the champion they played
    roster_match = _ROSTER_ENTRY_RE.match(line.rstrip("\n"))
    if roster_match:
        colored = f"{roster_match.group(1)}{colorize('username', roster_match.group(2))}{roster_match.group(3)}{colorize('champion', roster_match.group(4))}{roster_match.group(5)}"
        return colored + ("\n" if line.endswith("\n") else "")

    # One champion mastery entry names the champion before the level and the points it reports
    line = _sub_outside_color(_MASTERY_ENTRY_RE, lambda mo: f"{mo.group(1)}{colorize('champion', mo.group(2))}{mo.group(3)}", line)

    # Highlight the monitored player named inside a sentence
    line = _sub_outside_color(_USER_TAG_RE, lambda mo: f"{mo.group(1)}{mo.group(2)}{colorize('username', mo.group(3))}", line)
    line = _sub_outside_color(_USER_FIELD_RE, lambda mo: f"{mo.group(1)}{mo.group(2)}{colorize('username', mo.group(3))}", line)

    # Highlight how long something took
    line = _sub_outside_color(_DURATION_RE, lambda mo: colorize("duration", mo.group(0)), line)

    # Highlight a date range before a single date, so a range is not split into two dates
    line = _sub_outside_color(_DATE_RANGE_RE, lambda mo: colorize("date_range", mo.group(0)), line)
    line = _sub_outside_color(_LONG_DATE_RE, lambda mo: colorize("date", mo.group(0)), line)
    line = _sub_outside_color(_TIME_ONLY_RE, lambda mo: colorize("date", mo.group(0)), line)

    # Highlight links
    line = _sub_outside_color(_URL_RE, lambda mo: colorize("link", mo.group(0)), line)

    # Highlight a ranked standing and a quoted name
    line = _sub_outside_color(_RANK_RE, lambda mo: colorize("rank", mo.group(0)), line)
    line = _sub_outside_color(_QUOTED_CONTENT_RE, lambda mo: _colorize_quoted_name(mo, "username"), line)

    # Highlight boolean values
    line = _sub_outside_color(_BOOLEAN_TRUE_RE, lambda mo: colorize("boolean_true", mo.group(0)), line)
    line = _sub_outside_color(_BOOLEAN_FALSE_RE, lambda mo: colorize("boolean_false", mo.group(0)), line)

    # Mark the opening word of a warning and the name of a reported signal, rather than painting the line
    line = _sub_outside_color(_WARNING_LABEL_RE, lambda mo: mo.group(0)[:mo.start(1) - mo.start(0)] + colorize("warning", mo.group(1)), line)
    line = _sub_outside_color(_SIGNAL_NAME_RE, lambda mo: colorize("signal", mo.group(0)), line)

    # Highlight the two events this tool exists to report
    line = _sub_outside_color(_IN_GAME_RE, lambda mo: colorize("status_active", mo.group(0)), line)
    line = _sub_outside_color(_STOPPED_PLAYING_RE, lambda mo: colorize("status_inactive", mo.group(0)), line)

    # Block highlighting, applied last so the colours above survive the nesting logic
    is_debug_line = bool(_DEBUG_LINE_RE.match(lowered))
    is_error = not is_debug_line and (bool(_ERROR_KEYWORD_RE.search(lowered)) or ("* error" in lowered and "[errors =" not in lowered))

    if lowered.lstrip().startswith("to fix:"):
        line = _apply_style_nested(line, "info")
    elif is_error:
        line = _apply_style_nested(line, "error")
    elif "sending email" in lowered or "email sent successfully" in lowered:
        line = _apply_style_nested(line, "email")
    elif "sending webhook" in lowered or "webhook sent successfully" in lowered:
        line = _apply_style_nested(line, "webhook")

    return line


# Applies colourisation to multi-line text, preserving line breaks
def apply_color_to_text(text):
    if not COLOR_ENABLED or not isinstance(text, str):
        return text
    parts = []
    for chunk in text.splitlines(keepends=True):
        if chunk.endswith(("\n", "\r")):
            stripped = chunk.rstrip("\r\n")
            parts.append(_colorize_line(stripped) + chunk[len(stripped):])
        else:
            parts.append(_colorize_line(chunk))
    return "".join(parts)


# Returns the underlying terminal behind any number of colouring stream wrappers
def unwrap_terminal_stream(stream):
    while isinstance(stream, ColorStream):
        stream = stream.terminal
    return stream


# Marker appended to a line the terminal truncation cut, so a shortened line never looks complete
TRUNCATION_MARKER = "..."

# A separator line carries nothing that could be cut off, so a marker on one would report a loss that did not happen
SEPARATOR_ONLY_RE = re.compile(r"^(\S)\1*$")

# Value of TRUNCATE_CHARS that means "measure the terminal instead of using a fixed width"
TERMINAL_WIDTH_SENTINEL = 999


# Truncates each line to a display width, expanding tabs and counting double-width characters correctly
def truncate_string_per_line(message, truncate_width, tabsize=8):
    try:
        from wcwidth import wcwidth
    except ImportError:
        # Without a way to measure display width, cutting by character count would break wide glyphs
        return message
    marker_width = len(TRUNCATION_MARKER)
    truncated_lines = []
    for line in message.split("\n"):
        expanded_line = line.expandtabs(tabsize)
        current_width = 0
        truncated = []
        position = 0
        cut = False
        while position < len(expanded_line):
            # A colour sequence is copied through free of charge, so styling never eats into the visible width
            escape = SGR_SEQUENCE_RE.match(expanded_line, position)
            if escape:
                truncated.append(escape.group(0))
                position = escape.end()
                continue
            character = expanded_line[position]
            character_width = wcwidth(character)
            if character_width is None or character_width < 0:
                character_width = 0
            if current_width + character_width > truncate_width:
                cut = True
                break
            truncated.append(character)
            current_width += character_width
            position += 1
        if cut and truncate_width > marker_width and not SEPARATOR_ONLY_RE.match(SGR_SEQUENCE_RE.sub("", expanded_line)):
            # The marker replaces the last characters kept, so the line still fits the width that was asked for
            while truncated and current_width > truncate_width - marker_width:
                dropped = truncated.pop()
                if not SGR_SEQUENCE_RE.fullmatch(dropped):
                    width = wcwidth(dropped)
                    current_width -= width if width and width > 0 else 0
            truncated.append(TRUNCATION_MARKER)
        truncated_lines.append("".join(truncated))
    return "\n".join(truncated_lines)


# Applies the configured terminal truncation to text on its way to the screen, before any colour is added
def truncate_for_terminal(message):
    return truncate_string_per_line(message, TRUNCATE_CHARS) if TRUNCATE_CHARS else message


# Resolves the CLI and configured truncation settings, expanding the terminal-width sentinel
def resolve_truncate_chars(cli_value, configured_value, logging_disabled):
    truncate_chars = configured_value if cli_value is None else cli_value
    # A run with no log file has no full copy of a cut line, so truncation would lose output for good
    if logging_disabled:
        return 0
    if truncate_chars == TERMINAL_WIDTH_SENTINEL:
        terminal_size = shutil.get_terminal_size()
        verbose_print(f"The detected terminal screen width is: {terminal_size.columns} characters")
        return terminal_size.columns
    return max(0, truncate_chars)


# Colour-aware stdout wrapper installed before the logging policy is known, so output written
# before then is coloured exactly once by the same rules the Logger uses afterwards
class ColorStream(object):
    def __init__(self, stream):
        self.terminal = stream

    def write(self, message):
        self.terminal.write(apply_color_to_text(truncate_for_terminal(message)))
        self.terminal.flush()

    # Writes one message to the terminal while matching the Logger interface
    def terminal_only(self, message):
        self.write(message)

    # Discards log-only output, since this stream is used exactly when there is no log file
    def log_only(self, message):
        return

    def flush(self):
        self.terminal.flush()

    # Forwards the remaining stream attributes to the wrapped terminal
    def __getattr__(self, name):
        return getattr(self.terminal, name)


# Logger class to output messages to stdout and log file
class Logger(object):
    def __init__(self, filename):
        # The early colouring stream is unwrapped so colour is applied exactly once. Writing through it would
        # colourise every line twice, and the second pass no longer sees the label it already coloured
        self.terminal = unwrap_terminal_stream(sys.stdout)
        self.logfile = open(filename, "a", buffering=1, encoding="utf-8")

    def write(self, message):
        # Colour codes are stripped on the way to the file, so a log stays plain text
        self.logfile.write(normalize_log_separators(ANSI_ESCAPE_RE.sub("", message).expandtabs(8)))
        self.terminal.write(apply_color_to_text(truncate_for_terminal(message)))
        self.terminal.flush()
        self.logfile.flush()

    # Writes text the log file should keep but the terminal has already shown, or does not need
    def log_only(self, message):
        self.logfile.write(normalize_log_separators(ANSI_ESCAPE_RE.sub("", message).expandtabs(8)))
        self.logfile.flush()

    # Writes text meant for the reader at the terminal, which the log file has its own version of
    def terminal_only(self, message):
        self.terminal.write(apply_color_to_text(truncate_for_terminal(message)))
        self.terminal.flush()

    def flush(self):
        pass


# The startup banner every tool in this family opens with: a boxed glyph beside the tool name, the shared
# "Monitor" wordmark under it and the version on its own line. The wordmarks are pyfiglet's standard font
STARTUP_BANNER = r"""
 .---------------.    _          _
|  \\        //  |   | |    ___ | |
|   \\======//   |   | |   / _ \| |
|   //======\\   |   | |__| (_) | |___
|  //        \\  |   |_____\___/|_____|
 '---------------'
                      __  __             _ _
                     |  \/  | ___  _ __ (_) |_ ___  _ __
                     | |\/| |/ _ \| '_ \| | __/ _ \| '__|
                     | |  | | (_) | | | | | || (_) | |
                     |_|  |_|\___/|_| |_|_|\__\___/|_|"""

# Where both wordmarks start, which the version line shares so the three read as one block
STARTUP_BANNER_WORDMARK_COLUMN = 21


# Prints the ASCII startup banner with a separately aligned version
def print_startup_banner():
    # Coloured line by line: one span around the whole block would leave every line after the first plain,
    # and a per-line span also keeps the apostrophes in the art out of the quoted-name rule
    print("\n".join(colorize("header", line) if line else line for line in STARTUP_BANNER.splitlines()))
    print(colorize("info", f"{'':{STARTUP_BANNER_WORDMARK_COLUMN}}v{VERSION}") + "\n")


# Flags whose output the user reads rather than watches, so the screen they were run from has to stay scrollable
KEEP_HISTORY_FLAGS = ("--doctor", "--send-test-email", "--list-recent-matches", "-l", "--help", "-h")


# Returns True when the running command is a one-shot whose output has to stay scrollable
def keep_terminal_history():
    return any(flag in sys.argv for flag in KEEP_HISTORY_FLAGS)


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
    # A redirected stdout has no screen to clear, and the clear command reports its own missing TERM into the output
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
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
            print_recovery_error(context="email", detail="The SMTP settings are incorrect (invalid IP address/FQDN in SMTP_HOST)")
            return 1

    try:
        port = int(SMTP_PORT)
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        print_recovery_error(context="email", detail="The SMTP settings are incorrect (invalid port number in SMTP_PORT)")
        return 1

    if not email_re.search(str(SENDER_EMAIL)) or not email_re.search(str(RECEIVER_EMAIL)):
        print_recovery_error(context="email", detail="The SMTP settings are incorrect (invalid email in SENDER_EMAIL or RECEIVER_EMAIL)")
        return 1

    if not doctor_value_is_set(SMTP_USER) or not doctor_value_is_set(SMTP_PASSWORD):
        print_recovery_error(context="email", detail="The SMTP settings are incorrect (check SMTP_USER & SMTP_PASSWORD variables)")
        return 1

    if not subject or not isinstance(subject, str):
        print_recovery_error(context="email", detail="The SMTP settings are incorrect (subject is not a string or is empty)")
        return 1

    if not body and not body_html:
        print_recovery_error(context="email", detail="The SMTP settings are incorrect (body and body_html cannot be empty at the same time)")
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
    verbose_print(f"Email delivered to {RECEIVER_EMAIL}: {subject}")
    return 0


# The settings a sign-in needs before a password can be checked against the mail server
MAIL_SIGN_IN_SETTINGS = ("SMTP_HOST", "SMTP_USER", "SENDER_EMAIL", "RECEIVER_EMAIL")
MAIL_SETTINGS_INCOMPLETE_MESSAGE = "The mail server settings are incomplete"

# A Riot key is not scoped to a platform, so any live one proves it. The configured region is preferred so the
# check reaches the same host a real run does
RIOT_API_KEY_PROBE_REGION = "euw1"


# Returns the settings a mail sign-in needs that still hold no real value, so every refusal names the same ones
def mail_sign_in_settings_missing():
    return [name for name in MAIL_SIGN_IN_SETTINGS if not doctor_value_is_set(globals().get(name))]


# Words the refusal so the reader learns which settings to fill in rather than being sent to check all four
def mail_settings_incomplete_message(missing):
    return f"{MAIL_SETTINGS_INCOMPLETE_MESSAGE}, {join_setting_names(missing, 'and')} {'is' if len(missing) == 1 else 'are'} not set"


# Signs in to the configured mail server with one entered password, so nothing is saved that cannot deliver
def smtp_sign_in(password, timeout=15):
    global SMTP_PASSWORD

    candidate = str(password or "")
    if not candidate or candidate == "your_smtp_password":
        raise SecretConfigurationError("No SMTP password was entered. The private settings file was not changed.")
    missing = mail_sign_in_settings_missing()
    if missing:
        raise SecretConfigurationError(mail_settings_incomplete_message(missing))
    previous_password = SMTP_PASSWORD
    SMTP_PASSWORD = candidate
    smtp_object = None
    try:
        smtp_object = smtp_connect_and_login(SMTP_SSL, smtp_timeout=timeout)
    finally:
        if smtp_object is not None:
            try:
                smtp_object.quit()
            except Exception:
                pass
        SMTP_PASSWORD = previous_password
    return str(SMTP_USER)


# Validates a Riot API key against the same status endpoint the doctor uses, without exposing the key
def validate_riot_api_key(api_key):
    global RIOT_API_KEY

    candidate = str(api_key or "").strip()
    if not candidate or candidate.startswith("your_"):
        return False
    region = REGION if REGION_TO_CONTINENT.get(str(REGION or "").strip().casefold()) else RIOT_API_KEY_PROBE_REGION
    previous_key = RIOT_API_KEY
    RIOT_API_KEY = candidate
    try:
        asyncio.run(riot_api_key_probe(str(region).strip().casefold()))
        return True
    except Exception as exc:
        debug_swallowed_exception("Riot API key check", exc)
        return False
    finally:
        RIOT_API_KEY = previous_key


# Privately validates and atomically stores one Riot API key
@suppresses_debug_output
def run_set_riot_api_key(env_file=None, interactive=None, input_func=None, getpass_func=None, validator=None):
    destination = resolve_secret_env_path(env_file)
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else interactive
    if not terminal_is_interactive:
        raise SecretConfigurationError("--set-riot-api-key requires an interactive terminal. Run it in a terminal window so the API key stays hidden while you paste it.")
    prompt = input if input_func is None else input_func
    if _dotenv_contains_key(destination, "RIOT_API_KEY"):
        try:
            confirmed = read_interactively(prompt, f"Replace the saved Riot API key in '{destination}'? [y/N]: ").strip().casefold() in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            print()
            raise RecoveryError(secret_entry_cancelled_advice("Riot API key", "--set-riot-api-key", RIOT_API_KEY_GUIDE_URL)) from None
        if not confirmed:
            raise RecoveryError(secret_replacement_declined_advice("Riot API key", "--set-riot-api-key", RIOT_API_KEY_GUIDE_URL))
    hidden_prompt = getpass.getpass if getpass_func is None else getpass_func
    try:
        api_key = read_secret_interactively(hidden_prompt, "Paste the Riot API key (input hidden): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise RecoveryError(secret_entry_cancelled_advice("Riot API key", "--set-riot-api-key", RIOT_API_KEY_GUIDE_URL)) from None
    validate = validate_riot_api_key if validator is None else validator
    print("* Checking the entered Riot API key before changing the private settings file ...")
    if not validate(api_key):
        raise SecretConfigurationError("The entered Riot API key is invalid or could not be verified. The private settings file was not changed.")
    try:
        update_dotenv_file(destination, {"RIOT_API_KEY": api_key})
    except Exception:
        raise SecretConfigurationError(f"Could not save the Riot API key in '{destination}'. Check file permissions or choose another path with --env-file.")
    print("* Riot API key is valid")
    print(f"* Updated private settings file: {destination}")
    print()
    print_labelled_command("Check setup again:", render_command(["--doctor"], include_paths=False, env_path=destination))
    print_labelled_command("After Doctor passes, start monitoring:", render_command(command_target_arguments(RIOT_ID or None, REGION or None), include_paths=False, env_path=destination))
    return str(destination)


# Privately checks one SMTP password against the mail server and atomically stores it
@suppresses_debug_output
def run_set_smtp_password(env_file=None, interactive=None, input_func=None, getpass_func=None, sign_in=None):
    destination = resolve_secret_env_path(env_file)
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else interactive
    if not terminal_is_interactive:
        raise SecretConfigurationError("--set-smtp-password requires an interactive terminal. Run it in a terminal window so the password stays hidden while you type it.")
    # Checked before the prompts, so nobody types a password only to be told the mail server was never configured
    missing = mail_sign_in_settings_missing()
    if missing:
        raise SecretConfigurationError(mail_settings_incomplete_message(missing))
    prompt = input if input_func is None else input_func
    if _dotenv_contains_key(destination, "SMTP_PASSWORD"):
        try:
            confirmed = read_interactively(prompt, f"Replace the saved SMTP password in '{destination}'? [y/N]: ").strip().casefold() in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            print()
            raise RecoveryError(secret_entry_cancelled_advice("SMTP password", "--set-smtp-password", SMTP_GUIDE_URL)) from None
        if not confirmed:
            raise RecoveryError(secret_replacement_declined_advice("SMTP password", "--set-smtp-password", SMTP_GUIDE_URL))
    print(f"* The password is checked by signing in to {SMTP_HOST} as {SMTP_USER}. Nothing is sent")
    hidden_prompt = getpass.getpass if getpass_func is None else getpass_func
    try:
        smtp_password = str(read_secret_interactively(hidden_prompt, "Enter the SMTP password (input hidden): ")).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise RecoveryError(secret_entry_cancelled_advice("SMTP password", "--set-smtp-password", SMTP_GUIDE_URL)) from None
    check = smtp_sign_in if sign_in is None else sign_in
    try:
        signed_in_user = check(smtp_password, timeout=SECRET_ENTRY_SMTP_TIMEOUT)
    except SecretConfigurationError:
        raise
    except Exception as exc:
        # The entered password is not stored yet, so it is named here rather than left to the configured secrets
        raise SecretConfigurationError(f"The mail server did not accept the password: {type(exc).__name__}: {sanitize_error_text(exc, (smtp_password,))}. The private settings file was not changed.") from None
    try:
        update_dotenv_file(destination, {"SMTP_PASSWORD": smtp_password})
    except Exception:
        raise SecretConfigurationError(f"Could not save the SMTP password in '{destination}'. Check file permissions or choose another path with --env-file.")
    print(f"* The mail server accepted the password for {signed_in_user}")
    print(f"* Updated private settings file: {destination}")
    print()
    print_labelled_command("Send a test email:", render_command(["--send-test-email"], include_paths=False, env_path=destination))
    print_labelled_command("Check setup again:", render_command(["--doctor"], include_paths=False, env_path=destination))
    return str(destination)


# Privately validates and atomically stores one webhook URL
@suppresses_debug_output
def run_set_webhook_url(env_file=None, interactive=None, input_func=None, getpass_func=None):
    destination = resolve_secret_env_path(env_file)
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else interactive
    if not terminal_is_interactive:
        raise SecretConfigurationError("--set-webhook-url requires an interactive terminal. Run it in a terminal window so the webhook URL stays hidden while you paste it.")
    prompt = input if input_func is None else input_func
    if _dotenv_contains_key(destination, "WEBHOOK_URL"):
        try:
            confirmed = read_interactively(prompt, f"Replace the saved webhook URL in '{destination}'? [y/N]: ").strip().casefold() in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            print()
            raise RecoveryError(secret_entry_cancelled_advice("webhook URL", "--set-webhook-url", WEBHOOK_GUIDE_URL)) from None
        if not confirmed:
            raise RecoveryError(secret_replacement_declined_advice("webhook URL", "--set-webhook-url", WEBHOOK_GUIDE_URL))
    hidden_prompt = getpass.getpass if getpass_func is None else getpass_func
    try:
        webhook_url = read_secret_interactively(hidden_prompt, "Paste the Discord or ntfy webhook URL (input hidden): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise RecoveryError(secret_entry_cancelled_advice("webhook URL", "--set-webhook-url", WEBHOOK_GUIDE_URL)) from None
    if not validate_webhook_url(webhook_url):
        raise SecretConfigurationError("That does not look like a complete HTTPS webhook URL. The private settings file was not changed.")
    try:
        update_dotenv_file(destination, {"WEBHOOK_URL": webhook_url})
    except Exception:
        raise SecretConfigurationError(f"Could not save the webhook URL in '{destination}'. Check file permissions or choose another path with --env-file.")
    detected_provider = detect_webhook_provider(webhook_url)
    print(f"* Webhook URL looks valid ({webhook_provider_display_name(detected_provider)})" if detected_provider else "* Webhook URL looks valid")
    print(f"* Updated private settings file: {destination}")
    print()
    print_labelled_command("Send a test webhook:", render_command(["--send-test-webhook"], include_paths=False, env_path=destination))
    print_labelled_command("Check setup again:", render_command(["--doctor"], include_paths=False, env_path=destination))
    return str(destination)


# Returns whether a webhook URL is a complete private HTTPS link
def validate_webhook_url(url=None):
    selected_url = WEBHOOK_URL if url is None else url
    if not isinstance(selected_url, str) or not selected_url.strip():
        return False
    try:
        parsed = urlsplit(selected_url.strip())
    except ValueError:
        return False
    return parsed.scheme.casefold() == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password and bool(parsed.path.strip("/"))


# Accepts a complete HTTPS ntfy URL or a bare ntfy.sh topic name and returns the full URL
def normalize_ntfy_topic_url(value):
    if not isinstance(value, str):
        return ""
    normalized = value.strip()
    if validate_webhook_url(normalized):
        return normalized
    if re.fullmatch(r"[-_A-Za-z0-9]{1,64}", normalized):
        return f"https://ntfy.sh/{normalized}"
    return ""


# Detects Discord and public ntfy webhook providers from distinctive URL shapes
def detect_webhook_provider(url):
    if not validate_webhook_url(url):
        return ""
    try:
        parsed = urlsplit(str(url).strip())
    except ValueError:
        return ""
    hostname = parsed.hostname.casefold() if parsed.hostname else ""
    if hostname == "ntfy.sh":
        return "ntfy"
    discord_host = hostname in ("discord.com", "discordapp.com") or hostname.endswith(".discord.com") or hostname.endswith(".discordapp.com")
    discord_path = re.match(r"^/api(?:/v[0-9]+)?/webhooks/[0-9]+/[^/]+/?$", parsed.path) is not None
    return "discord" if discord_host and discord_path else ""


# Returns the normalized configured webhook provider or an empty string when unsupported
def normalized_webhook_provider(provider=None):
    selected_provider = WEBHOOK_PROVIDER if provider is None else provider
    if not isinstance(selected_provider, str):
        return ""
    normalized = selected_provider.strip().casefold()
    return normalized if normalized in ("discord", "ntfy") else ""


# Returns the spelling each webhook service uses for itself, since the stored value is casefolded for comparisons
def webhook_provider_display_name(provider=None):
    normalized = normalized_webhook_provider(provider)
    return {"discord": "Discord", "ntfy": "ntfy"}.get(normalized, normalized or "an unset provider")


# Returns the webhook destination's host alone, so a trace can name it without exposing the private path
def webhook_destination_host():
    try:
        return urlsplit(str(WEBHOOK_URL or "").strip()).hostname or ""
    except ValueError:
        return ""


# Returns whether one configured webhook alert is enabled independently of the email settings
def webhook_event_enabled(notification_type):
    settings = {"status": WEBHOOK_STATUS_NOTIFICATION, "error": WEBHOOK_ERROR_NOTIFICATION}
    return bool(WEBHOOK_ENABLED and settings.get(notification_type, False))


# Returns the webhook alert types selected in the configuration, ignoring the master switch
def _selected_webhook_notification_categories():
    settings = ((WEBHOOK_STATUS_NOTIFICATION, "status changes"), (WEBHOOK_ERROR_NOTIFICATION, "errors"))
    return [label for enabled, label in settings if enabled]


# Returns enabled webhook notification category names in display order
def _startup_webhook_notification_categories():
    return _selected_webhook_notification_categories() if WEBHOOK_ENABLED else []


# Parses one numeric or HTTP-date retry value into seconds
def parse_retry_after_seconds(candidate):
    if candidate is None or candidate == "":
        return None
    try:
        seconds = float(candidate)
        return seconds if math.isfinite(seconds) else None
    except (TypeError, ValueError):
        try:
            retry_at = parsedate_to_datetime(str(candidate))
            seconds = (retry_at - datetime.now(retry_at.tzinfo)).total_seconds()
            return seconds if math.isfinite(seconds) else None
        except Exception:
            return None


# Returns the first valid retry delay bounded between zero and a caller-selected maximum
def bounded_retry_after_seconds(candidates, fallback, maximum):
    for candidate in candidates:
        seconds = parse_retry_after_seconds(candidate)
        if seconds is not None:
            return max(0.0, min(seconds, maximum))
    return max(0.0, min(float(fallback), maximum))


# Parses a webhook rate-limit delay and caps untrusted server values to a short wait
def webhook_retry_after_seconds(response):
    headers = getattr(response, "headers", {}) or {}
    candidates = [headers.get("Retry-After")] if hasattr(headers, "get") else []
    try:
        payload = response.json()
    except Exception:
        payload = None
    if isinstance(payload, dict):
        candidates.append(payload.get("retry_after"))
    return bounded_retry_after_seconds(candidates, WEBHOOK_FALLBACK_RETRY_SECONDS, WEBHOOK_MAX_RETRY_AFTER_SECONDS)


# Substitutes the supported placeholders through one webhook template of any shape
def format_payload(template, payload):
    if isinstance(template, dict):
        return {key: format_payload(value, payload) for key, value in template.items()}
    if isinstance(template, list):
        return [format_payload(value, payload) for value in template]
    if isinstance(template, tuple):
        return tuple(format_payload(value, payload) for value in template)
    if isinstance(template, str):
        if template == "{fields}":
            return payload.get("fields", [])
        if template == "{color}":
            return payload.get("color", WEBHOOK_DEFAULT_COLOR)
        try:
            return template.format(**payload)
        except KeyError:
            return template
    return template


# Returns a configuration error for unsafe or unsupported webhook customization
def validate_webhook_customization(provider=None):
    selected_provider = normalized_webhook_provider(provider)
    if selected_provider == "discord":
        if not isinstance(WEBHOOK_USERNAME, str):
            return "WEBHOOK_USERNAME must be a string"
        if not isinstance(WEBHOOK_AVATAR_URL, str):
            return "WEBHOOK_AVATAR_URL must be a string"
        if WEBHOOK_AVATAR_URL.strip() and not validate_webhook_url(WEBHOOK_AVATAR_URL):
            return "WEBHOOK_AVATAR_URL must contain a complete HTTPS link without embedded credentials"
        if not isinstance(WEBHOOK_TEMPLATE, (dict, list, str)):
            return "WEBHOOK_TEMPLATE must be a dictionary, list or string"
    if not isinstance(WEBHOOK_TRANSFORMS, (list, tuple)):
        return "WEBHOOK_TRANSFORMS must be a list or tuple"
    for index, transform in enumerate(WEBHOOK_TRANSFORMS):
        if not isinstance(transform, (list, tuple)) or len(transform) < 2 or not isinstance(transform[0], str) or not isinstance(transform[1], str):
            return f"WEBHOOK_TRANSFORMS entry {index + 1} must contain a field name and string method name"
        if transform[1].startswith("_") or not callable(getattr("", transform[1], None)):
            return f"WEBHOOK_TRANSFORMS entry {index + 1} uses an unsupported string method"
    return None


# Applies configured string transformations to one webhook value mapping
def apply_webhook_transforms(payload):
    transformed = dict(payload)
    for index, transform in enumerate(WEBHOOK_TRANSFORMS):
        field = transform[0]
        method_name = transform[1]
        if field not in transformed or not isinstance(transformed[field], str):
            continue
        try:
            transformed[field] = getattr(transformed[field], method_name)(*transform[2:])
        except Exception:
            raise ValueError(f"WEBHOOK_TRANSFORMS entry {index + 1} could not apply {field}.{method_name}")
    return transformed


# Builds bounded placeholder values shared by webhook templates and providers
def build_webhook_values(title, description, notification_type, image_url=""):
    safe_title = re.sub(r"[\r\n]+", " ", sanitize_error_text(title)).strip()[:WEBHOOK_EMBED_TITLE_LIMIT] or "LoL Monitor"
    safe_description = re.sub(r"\r\n?", "\n", sanitize_error_text(description)).strip()[:WEBHOOK_EMBED_DESCRIPTION_LIMIT]
    username = WEBHOOK_USERNAME.strip()[:80] if isinstance(WEBHOOK_USERNAME, str) else ""
    avatar_url = WEBHOOK_AVATAR_URL.strip() if isinstance(WEBHOOK_AVATAR_URL, str) else ""
    payload = {"title": safe_title, "description": safe_description, "version": VERSION, "image_url": str(image_url or ""), "fields": [], "fields_str": "", "color": WEBHOOK_EVENT_COLORS.get(notification_type, WEBHOOK_DEFAULT_COLOR), "timestamp": datetime.now().astimezone().isoformat(), "username": username, "avatar_url": avatar_url}
    return apply_webhook_transforms(payload)


# Builds one customized Discord-format payload while keeping mentions disabled
def build_webhook_payload(title, description, notification_type, image_url="", payload_values=None):
    values = build_webhook_values(title, description, notification_type, image_url) if payload_values is None else payload_values
    try:
        payload = format_payload(WEBHOOK_TEMPLATE, values)
    except Exception:
        raise ValueError("WEBHOOK_TEMPLATE could not be formatted with the supported placeholders")
    if isinstance(payload, dict):
        if payload.get("username") == "":
            payload.pop("username")
        if payload.get("avatar_url") == "":
            payload.pop("avatar_url")
        payload["allowed_mentions"] = {"parse": []}
        embeds = payload.get("embeds")
        if isinstance(embeds, list):
            for embed in embeds:
                if isinstance(embed, dict) and isinstance(embed.get("thumbnail"), dict) and not embed["thumbnail"].get("url"):
                    embed.pop("thumbnail")
    return payload


# Truncates text to a UTF-8 byte limit without returning a partial character
def truncate_utf8_bytes(text, max_bytes, suffix=""):
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    encoded_suffix = suffix.encode("utf-8")
    if len(encoded_suffix) >= max_bytes:
        return encoded_suffix[:max_bytes].decode("utf-8", errors="ignore")
    return encoded[:max_bytes - len(encoded_suffix)].decode("utf-8", errors="ignore") + suffix


# Builds one bounded ntfy title and message pair
def build_ntfy_webhook_message(title, description):
    safe_title = re.sub(r"[\r\n]+", " ", sanitize_error_text(title)).strip()[:WEBHOOK_EMBED_TITLE_LIMIT] or "LoL Monitor"
    safe_message = truncate_utf8_bytes(re.sub(r"\r\n?", "\n", sanitize_error_text(description)).strip(), NTFY_MESSAGE_LIMIT_BYTES, NTFY_TRUNCATION_SUFFIX)
    return safe_title, safe_message


# Returns a validation error for unsupported ntfy priority or tag values
def validate_ntfy_metadata(priority, tags):
    if not isinstance(priority, int) or isinstance(priority, bool) or not 0 <= priority <= 5:
        return "ntfy priority must be 0 to omit it or an integer from 1 through 5"
    if not isinstance(tags, str):
        return "ntfy tags must be a comma-separated string"
    if "\r" in tags or "\n" in tags:
        return "ntfy tags must not contain line breaks"
    return None


# Returns a safe validation error for one custom webhook header mapping
def _validate_webhook_header_mapping(headers):
    if not isinstance(headers, dict):
        return "WEBHOOK_HEADERS must be a dictionary of string header names and values"
    normalized_names = set()
    for name, value in headers.items():
        if not isinstance(name, str) or not re.fullmatch(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+", name):
            return "WEBHOOK_HEADERS contains an invalid HTTP header name"
        normalized_name = name.casefold()
        if normalized_name in normalized_names:
            return "WEBHOOK_HEADERS contains duplicate case-insensitive header names"
        normalized_names.add(normalized_name)
        if not isinstance(value, str):
            return f"WEBHOOK_HEADERS value for {name} must be a string"
        if "\r" in value or "\n" in value:
            return f"WEBHOOK_HEADERS value for {name} must not contain line breaks"
    return None


# Returns a safe configuration error for custom webhook headers or ntfy access tokens
def validate_webhook_headers(provider=None):
    selected_provider = normalized_webhook_provider(provider)
    header_error = _validate_webhook_header_mapping(WEBHOOK_HEADERS)
    if header_error is not None:
        return header_error
    if selected_provider == "ntfy":
        if not isinstance(NTFY_ACCESS_TOKEN, str):
            return "NTFY_ACCESS_TOKEN must be a string"
        token = NTFY_ACCESS_TOKEN.strip()
        if "\r" in token or "\n" in token:
            return "NTFY_ACCESS_TOKEN must not contain line breaks"
        if token.casefold().startswith(("bearer ", "basic ")):
            return "NTFY_ACCESS_TOKEN must contain only the access token without an Authorization scheme"
    return None


# Builds provider-specific headers with custom placeholders and private ntfy authentication
def build_webhook_headers(provider, payload):
    validation_error = validate_webhook_headers(provider)
    if validation_error is not None:
        raise ValueError(validation_error)
    try:
        formatted_headers = format_payload(WEBHOOK_HEADERS, payload)
    except Exception:
        raise ValueError("WEBHOOK_HEADERS could not be formatted with the supported placeholders")
    formatted_error = _validate_webhook_header_mapping(formatted_headers)
    if formatted_error is not None:
        raise ValueError(formatted_error)
    if not isinstance(formatted_headers, dict):
        raise ValueError("WEBHOOK_HEADERS must be a dictionary of string header names and values")
    headers = {str(name): str(value) for name, value in formatted_headers.items()}
    if not any(name.casefold() == "user-agent" for name in headers):
        headers["User-Agent"] = f"LoLMonitor/{VERSION}"
    if provider == "ntfy":
        headers = {name: value for name, value in headers.items() if name.casefold() != "content-type"}
        headers["Content-Type"] = "text/plain; charset=utf-8"
        token = NTFY_ACCESS_TOKEN.strip()
        if token:
            headers = {name: value for name, value in headers.items() if name.casefold() != "authorization"}
            headers["Authorization"] = f"Bearer {token}"
    return headers


# Applies the webhook command line overrides, correcting a provider the destination contradicts
def apply_webhook_cli_overrides(args, parser):
    global WEBHOOK_ENABLED, WEBHOOK_URL, WEBHOOK_PROVIDER, WEBHOOK_STATUS_NOTIFICATION, WEBHOOK_ERROR_NOTIFICATION
    if args.webhook_provider is not None:
        WEBHOOK_PROVIDER = str(args.webhook_provider)
    if args.webhook_url is not None:
        if not validate_webhook_url(args.webhook_url):
            parser.error("--webhook-url must contain a complete HTTPS link without embedded credentials")
        WEBHOOK_URL = str(args.webhook_url).strip()
        WEBHOOK_ENABLED = True
    if args.webhook_enabled is not None:
        WEBHOOK_ENABLED = args.webhook_enabled
    if args.webhook_status is True:
        WEBHOOK_ENABLED = True
        WEBHOOK_STATUS_NOTIFICATION = True
    if args.webhook_errors is not None:
        WEBHOOK_ERROR_NOTIFICATION = args.webhook_errors
        if args.webhook_errors:
            WEBHOOK_ENABLED = True
    if args.webhook_provider is None:
        detected_provider = detect_webhook_provider(WEBHOOK_URL)
        configured_provider = normalized_webhook_provider()
        if detected_provider and detected_provider != configured_provider:
            WEBHOOK_PROVIDER = detected_provider
            print(f"* Warning: Configured webhook provider did not match the URL. Using {webhook_provider_display_name(detected_provider)}.")


# Reports one webhook failure through the recovery block, without revealing private URLs, tokens or response bodies
def print_webhook_error(message, error=None):
    print_recovery_error(error, context="webhook", detail=str(message))


# Sends one webhook request with the destination, deadline and redirect policy every delivery shares
def post_webhook_request(**request_kwargs):
    destination = str(WEBHOOK_URL or "").strip()
    # Revalidated here because a dotenv reload can replace the destination after the delivery started
    if not validate_webhook_url(destination):
        raise req.exceptions.InvalidURL("WEBHOOK_URL must contain a complete HTTPS link")
    return WEBHOOK_SESSION.post(destination, timeout=WEBHOOK_TIMEOUT_SECONDS, verify=VERIFY_SSL, allow_redirects=False, **request_kwargs)


# Sends one webhook through an isolated bounded retry path
def send_webhook(title, description, notification_type="status", force=False, sleeper=None, image_url="", ntfy_priority=0, ntfy_tags=""):
    if not force and not webhook_event_enabled(notification_type):
        return 1
    if not validate_webhook_url():
        print_webhook_error("WEBHOOK_URL must contain a complete HTTPS link")
        return 1
    provider = normalized_webhook_provider()
    if not provider:
        print_webhook_error("WEBHOOK_PROVIDER must be discord or ntfy")
        return 1
    metadata_error = validate_ntfy_metadata(ntfy_priority, ntfy_tags) if provider == "ntfy" else None
    if metadata_error is not None:
        print_webhook_error(metadata_error)
        return 1
    customization_error = validate_webhook_customization(provider)
    if customization_error is not None:
        print_webhook_error(customization_error)
        return 1
    header_error = validate_webhook_headers(provider)
    if header_error is not None:
        print_webhook_error(header_error)
        return 1
    try:
        webhook_values = build_webhook_values(title, description, notification_type, image_url)
        request_headers = build_webhook_headers(provider, webhook_values)
        discord_payload = build_webhook_payload(title, description, notification_type, "", webhook_values) if provider == "discord" else None
    except ValueError as exc:
        print_webhook_error(str(exc))
        return 1
    debug_print("Webhook delivery", event=notification_type, channel=provider, host=webhook_destination_host())
    sleep_func = time.sleep if sleeper is None else sleeper
    ntfy_title, ntfy_message = build_ntfy_webhook_message(str(webhook_values["title"]), str(webhook_values["description"])) if provider == "ntfy" else ("", "")
    ntfy_params = {"title": ntfy_title}  # type: Dict[str, Any]
    if provider == "ntfy" and ntfy_priority:
        ntfy_params["priority"] = ntfy_priority
    if provider == "ntfy" and ntfy_tags.strip():
        ntfy_params["tags"] = ntfy_tags.strip()
    for attempt in range(WEBHOOK_MAX_ATTEMPTS):
        debug_print("Webhook delivery", channel=provider, attempt=f"{attempt + 1}/{WEBHOOK_MAX_ATTEMPTS}")
        try:
            if provider == "ntfy":
                response = post_webhook_request(data=ntfy_message.encode("utf-8"), params=ntfy_params, headers=request_headers)
            elif isinstance(discord_payload, str):
                response = post_webhook_request(data=discord_payload, headers=request_headers)
            else:
                response = post_webhook_request(json=discord_payload, headers=request_headers)
            if 200 <= response.status_code <= 299:
                verbose_print(f"Webhook delivered through {provider}: {webhook_values['title']}")
                debug_print("Webhook delivery", channel=provider, status=response.status_code, outcome="OK")
                return 0
            retryable = response.status_code == 429 or 500 <= response.status_code <= 599
            debug_print("Webhook delivery", channel=provider, status=response.status_code, retryable=retryable, outcome="failed")
            if not retryable or attempt == WEBHOOK_MAX_ATTEMPTS - 1:
                print_webhook_error(f"The webhook service returned HTTP {response.status_code}", req.HTTPError(response=response))
                return 1
            delay = webhook_retry_after_seconds(response) if response.status_code == 429 else WEBHOOK_FALLBACK_RETRY_SECONDS
            debug_print("Webhook delivery", channel=provider, retry_in=f"{delay}s")
            sleep_func(delay)
        except req.RequestException as exc:
            debug_swallowed_exception("Webhook request", exc)
            if attempt == WEBHOOK_MAX_ATTEMPTS - 1:
                print_webhook_error(f"The webhook service could not be reached ({type(exc).__name__})")
                return 1
            sleep_func(WEBHOOK_FALLBACK_RETRY_SECONDS)
    print_webhook_error("The webhook delivery did not complete")
    return 1


# Sends one alert through the enabled email and webhook channels
def send_notification_channels(notification_type, subject, body, body_html="", email_enabled=False, webhook_enabled=None, image_url="", ntfy_priority=0, ntfy_tags=""):
    email_attempted = bool(email_enabled)
    webhook_attempted = webhook_event_enabled(notification_type) if webhook_enabled is None else bool(webhook_enabled)
    email_delivered = False
    webhook_delivered = False
    if email_attempted:
        print(f"Sending email notification to {RECEIVER_EMAIL}")
        email_delivered = send_email(subject, body, body_html, SMTP_SSL) == 0
        debug_print("Email channel", event=notification_type, outcome="OK" if email_delivered else "failed")
    if webhook_attempted:
        print("Sending webhook notification")
        webhook_delivered = send_webhook(subject, body, notification_type, force=True, image_url=image_url, ntfy_priority=ntfy_priority, ntfy_tags=ntfy_tags) == 0
        debug_print("Webhook channel", event=notification_type, outcome="OK" if webhook_delivered else "failed")
    # Delivery, not the attempt, so a channel that failed is retried while one that succeeded is not resent
    return email_delivered, webhook_delivered


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
            print_recovery_advice(missing_dependency_advice("python-dotenv", "The env-var reload was skipped"), label="Warning")

    global WEBHOOK_PROVIDER
    webhook_url_changed = False
    if env_path:
        for secret in SECRET_KEYS:
            old_val = globals().get(secret)
            val = os.getenv(secret)
            if val is not None and val != old_val:
                globals()[secret] = val
                webhook_url_changed = webhook_url_changed or secret == "WEBHOOK_URL"
                print(f"* Reloaded {secret} from {env_path} ({secret_fingerprint(val, secret)})")

    # A reloaded destination can belong to the other service, and a Discord payload posted to an ntfy topic is rejected
    if webhook_url_changed:
        detected_provider = detect_webhook_provider(WEBHOOK_URL)
        if detected_provider and detected_provider != normalized_webhook_provider():
            WEBHOOK_PROVIDER = detected_provider
            print(f"* Updated webhook provider to {webhook_provider_display_name(detected_provider)}")

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


# Parses one duration written as plain seconds or with s/m/h/d units, returning whole seconds
def parse_duration_input(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        # Rounded and re-checked like the text path, so a fraction of a second is refused rather than read as zero
        seconds = int(round(value))
        return seconds if seconds > 0 else None
    if not isinstance(value, str):
        return None
    text = value.strip().casefold().replace(",", ".")
    if not text:
        return None
    units = {"s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1,
             "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60,
             "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600,
             "d": 86400, "day": 86400, "days": 86400}
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*([a-z]*)", text)
    # Anything the pattern did not fully consume is rejected, so "5x" or "abc" cannot read as a bare number
    if not matches or re.sub(r"(\d+(?:\.\d+)?)\s*([a-z]*)", "", text).strip():
        return None
    total = 0.0
    for amount, unit in matches:
        if unit and unit not in units:
            return None
        total += float(amount) * units.get(unit, 1)
    seconds = int(round(total))
    return seconds if seconds > 0 else None


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
            print_recovery_error(e, detail=f"Cannot read the summoner details: {e}")

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


# The Riot asset host the champion names and the champion icons both come from
DDRAGON_BASE_URL = "https://ddragon.leagueoflegends.com"

# Gets champion ID to name mapping from Data Dragon
_champion_id_to_name_cache = None

# The Data Dragon release the champion names were read from, so an icon URL points at that same release
_ddragon_version_cache = ""


# Gets champion name from champion ID using Data Dragon
def get_champion_name(champion_id: int) -> Optional[str]:
    global _champion_id_to_name_cache, _ddragon_version_cache

    if _champion_id_to_name_cache is None:
        _champion_id_to_name_cache = {}
        try:
            # Get latest Data Dragon version
            versions_response = req.get(f"{DDRAGON_BASE_URL}/api/versions.json", timeout=5, verify=VERIFY_SSL)
            if versions_response.status_code == 200:
                versions = versions_response.json()
                latest_version = versions[0]
                _ddragon_version_cache = str(latest_version)

                # Get champion data
                champions_url = f"{DDRAGON_BASE_URL}/cdn/{latest_version}/data/en_US/champion.json"
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


# Returns the Data Dragon icon URL for one champion, or nothing when the run has no release or no usable name
def champion_image_url(champion_name):
    # Both halves are checked rather than escaped, since anything outside these shapes is not a Data Dragon
    # asset path and has no business being interpolated into a URL the tool then sends to a webhook
    if not isinstance(champion_name, str) or not re.fullmatch(r"[A-Za-z0-9]{1,40}", champion_name):
        return ""
    if not re.fullmatch(r"\d[\d.]{0,15}", _ddragon_version_cache):
        return ""
    return f"{DDRAGON_BASE_URL}/cdn/{_ddragon_version_cache}/img/champion/{champion_name}.png"


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

            send_notification_channels("status", m_subject, m_body, m_body_html, email_enabled=status_notification_flag, image_url=champion_image_url(u_champion_name))

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
        print_recovery_error(e, detail=f"Cannot fetch the latest match IDs: {e}")
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
        print_recovery_error(e, detail=f"Cannot determine the total match count: {e}")
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
                            print()
                            send_notification_channels("status", m_subject, m_body, m_body_html, email_enabled=True)
                    return 0, 0
                else:
                    debug_swallowed_exception("Match details", e)
                    print_recovery_error(e, detail=f"Cannot process match {match_id}: {e}")
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
                print_recovery_error(e, context="file")

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
            print()
            send_notification_channels("status", m_subject, m_body, m_body_html, email_enabled=True, image_url=champion_image_url(u_champion_name))

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
                    print()
                    send_notification_channels("status", m_subject, m_body, m_body_html, email_enabled=True)
        else:
            print_recovery_error(e, detail=f"Cannot process match {match_id}: {e}")

        return 0, 0


# Returns the advice an account with no readable match history carries, worded the same in the listing and the count
def no_match_history_advice():
    return make_recovery_advice("target.not_found", "Riot returned no match history for this account", recovery_fix_with_guide("Check the Riot ID and the region, since match history is kept per region", USAGE_GUIDE_URL), False)


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
        print_recovery_error(RecoveryError(no_match_history_advice()))
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
                        print_recovery_error(e, detail=f"Cannot process match {match_id}: {e}")

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

# Settings the template ships commented out, so a configuration file that sets one is still accepted
COMMENTED_CONFIG_SETTINGS = frozenset({"COLOR_THEME"})


# Collects the setting names the built-in configuration template defines
def _config_allowed_names():
    template_tree = ast.parse(CONFIG_BLOCK, "<built-in-config>", "exec")
    return frozenset(statement.targets[0].id for statement in template_tree.body if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name)) | COMMENTED_CONFIG_SETTINGS


# Returns the value the built-in configuration template ships for every setting it assigns
@functools.lru_cache(maxsize=1)
def _config_template_defaults():
    defaults = {}
    for statement in ast.parse(CONFIG_BLOCK, "<built-in-config>", "exec").body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
            continue
        try:
            defaults[statement.targets[0].id] = ast.literal_eval(statement.value)
        except ValueError:
            continue
    return defaults


# Renders one configuration file from the built-in template with the chosen values substituted in
def generate_config_with_current_values(config_values):
    tree = ast.parse(CONFIG_BLOCK, "<built-in-config>", "exec")
    template_defaults = _config_template_defaults()
    replacements = {}
    for statement in tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
            continue
        name = statement.targets[0].id
        # A secret belongs in the dotenv file, so its template placeholder stays even when the running values hold the real one
        if name not in config_values or name in SECRET_KEYS:
            continue
        # A setting still holding what the template ships keeps the template's own lines, so a multi-line
        # value such as WEBHOOK_TEMPLATE is not collapsed into one unreadable line by a wizard that changed nothing
        if name in template_defaults and config_values[name] == template_defaults[name] and type(config_values[name]) is type(template_defaults[name]):
            continue
        replacements[name] = (statement.lineno, getattr(statement, "end_lineno", statement.lineno), repr(config_values[name]))
    lines = CONFIG_BLOCK.strip("\n").split("\n")
    # The template keeps its own leading blank line, so template line numbers are one ahead of this list
    offset = 1 if CONFIG_BLOCK.startswith("\n") else 0
    skip_until = 0
    output = []
    for number, line in enumerate(lines, 1):
        template_line = number + offset
        if template_line < skip_until:
            continue
        replaced = next((name for name, (start, _end, _value) in replacements.items() if start == template_line), None)
        if replaced is None:
            output.append(line)
            continue
        start, end, rendered = replacements[replaced]
        output.append(f"{replaced} = {rendered}")
        skip_until = end + 1
    return "\n".join(output) + "\n"


# Keeps argparse from colouring its own help, so the help screen is coloured by this tool alone and
# --no-color is not left with a second palette to silence. From Python 3.14 argparse colours help by default
def argparse_color_kwargs() -> Dict[str, Any]:
    return {"color": False} if sys.version_info >= (3, 14) else {}


# Returns the --config-file value from the raw arguments, before argparse has run
def early_config_file_argument(arguments=None):
    values = list(sys.argv[1:] if arguments is None else arguments)
    for index, argument in enumerate(values):
        if argument == "--config-file" and index + 1 < len(values):
            return values[index + 1]
        if argument.startswith("--config-file="):
            return argument.split("=", 1)[1]
    return None


# Applies the configuration settings that take effect before argument parsing, leaving errors to the later
# load. The startup banner and the screen clear both run before argparse, so colour has to be resolved here
# or a configured COLORED_OUTPUT would only take effect after the first output was already written
def apply_early_output_config() -> None:
    global CLEAR_SCREEN, COLORED_OUTPUT
    try:
        cli_path = early_config_file_argument()
        if cli_path is not None and cli_path.strip().casefold() == "none":
            # Config discovery is disabled for this run, so there is nothing to peek at
            return
        config_path = find_config_file(os.path.expanduser(cli_path) if cli_path else None)
        if not config_path:
            return
        # Reading a config no longer runs it, so this early peek cannot have side effects
        values = parse_config_content(Path(config_path).read_text(encoding="utf-8"), str(config_path))
    except Exception:
        # A broken or unreadable config is reported with full detail once the arguments are parsed
        return
    if isinstance(values.get("CLEAR_SCREEN"), bool):
        CLEAR_SCREEN = values["CLEAR_SCREEN"]
    if isinstance(values.get("COLORED_OUTPUT"), bool):
        COLORED_OUTPUT = values["COLORED_OUTPUT"]
    if isinstance(values.get("COLOR_THEME"), dict):
        globals()["COLOR_THEME"] = values["COLOR_THEME"]


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

    alive_since = int(time.time())
    # A blip is confirmed by the short retry before it is printed, since one lost request is not an outage
    outage = OutageReporter(confirm_checks=1 if VERBOSE_MODE else 2)
    transient_retry_used = False
    error_delivery_code = None
    last_match_start_ts = 0
    last_match_stop_ts = 0
    puuid = None
    riotid_name = ""
    started_announced = False

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
        print_recovery_error(e, detail=f"Cannot read the summoner details: {e}")
        summoner_info = {"summoner_level": "N/A", "revision_date": "N/A"}

    try:
        ranked_info = await get_ranked_info(puuid, region)
    except Exception as e:
        print_recovery_error(e, detail=f"Cannot read the ranked information: {e}")
        ranked_info = {
            "solo_duo": {"tier": "N/A", "rank": "N/A", "lp": "N/A", "wins": 0, "losses": 0},
            "flex": {"tier": "N/A", "rank": "N/A", "lp": "N/A", "wins": 0, "losses": 0},
        }

    try:
        mastery_info = await get_champion_mastery(puuid, region, top_n=3)
    except Exception as e:
        print_recovery_error(e, detail=f"Cannot read the champion mastery: {e}")

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
        print_recovery_error(e, detail=f"Cannot read the initial match history: {e}")

    if initial_match_ids:
        processed_match_ids.update(initial_match_ids)
        print("User last played match:\n")
        try:
            last_match_start_ts, last_match_stop_ts = await process_and_print_single_match(initial_match_ids[0], puuid, riotid_name, region, False, None)
        except Exception as e:
            print_recovery_error(e, detail=f"Cannot display the last known match: {e}")
    else:
        print("* No match history to start from, the first new match played will be detected")

    ingame = False
    ingame_old = False
    game_finished_ts = 0
    error_email_sent = False
    error_webhook_sent = False

    print_cur_ts("\nTimestamp:\t\t\t")

    check_count = 0

    while True:

        try:

            processed_new_match_in_this_cycle = False
            check_count += 1
            debug_print("Starting check", check=f"#{check_count}", user=riotid, in_game=ingame)

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
                        print_recovery_error(e, detail=f"Cannot capture the current match details: {e}")
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

                    send_notification_channels("status", m_subject, m_body, m_body_html, email_enabled=STATUS_NOTIFICATION)

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
                    print_recovery_error(e, context="file", detail=f"Cannot save the custom game match to the CSV file: {e}")
                    print_cur_ts("\nTimestamp:\t\t\t")
                finally:
                    pending_custom = None
                    current_custom_snapshot = None
                    current_match_start_ts = 0

            ingame_old = ingame
            error_email_sent = False
            error_webhook_sent = False
            error_delivery_code = None
            transient_retry_used = False

            outage_lasted = outage.recovered()
            if outage_lasted is not None:
                print_outage_recovery(riotid, outage_lasted)
                # The quiet period restarts here, or the recovery line is followed straight away by a healthy banner
                alive_since = int(time.time())

            debug_print("Completed check", check=f"#{check_count}", user=riotid, outcome="OK", in_game=ingame)

            if LIVENESS_REMINDER_SECONDS and int(time.time()) - alive_since >= LIVENESS_REMINDER_SECONDS:
                print_liveness_banner(f"Monitoring healthy for {riotid}. The user is {'in a match' if ingame else 'not in a match'} with no match change since the last check")
                alive_since = int(time.time())

            wait_seconds = LOL_ACTIVE_CHECK_INTERVAL if (ingame or (game_finished_ts and (int(time.time()) - game_finished_ts) <= LOL_CHECK_INTERVAL)) else LOL_CHECK_INTERVAL
            debug_print("Next check", check=f"#{check_count}", due_in=display_time(wait_seconds), reason="user is in a match" if ingame else "user is not in a match")
            time.sleep(wait_seconds)

        except Exception as e:
            sleep_interval = LOL_ACTIVE_CHECK_INTERVAL if ingame else LOL_CHECK_INTERVAL
            advice = classify_recovery_error(e)
            debug_print("Completed check", check=f"#{check_count}", user=riotid, outcome="failed", code=advice.code, error=f"{type(e).__name__}: {e}")
            # A failure that changes family is a different failure, so each channel earns a new alert for it, while an
            # internet outage that flaps between a timeout and an unreachable host stays one failure
            if outage_family(advice.code) != outage_family(error_delivery_code):
                error_email_sent = False
                error_webhook_sent = False
                error_delivery_code = advice.code
            # A failure that has not changed is left to the liveness cadence rather than repeated every check
            outage_outcome = outage.failed(advice)
            delivery_reported = False

            if advice.code == "riot.rate_limited":
                # A rate limit carries its own wait, so it skips the retry path rather than burning an attempt
                retry_after = riot_retry_after_seconds(e, sleep_interval)
                retry_note = f"retrying in {display_time(retry_after)}"
                if outage_outcome == "full":
                    print_recovery_error(e, "runtime", retry_note=retry_note)
                    print_cur_ts("Timestamp:\t\t\t")
                elif outage_outcome == "changed":
                    print_outage_change(riotid, advice)
                    print_cur_ts("Timestamp:\t\t\t")
                elif outage_outcome == "reminder":
                    print_outage_liveness(riotid, advice, outage.since, outage.failures)
                debug_print("Retry wait", check=f"#{check_count}", due_in=display_time(retry_after), reason="riot rate limited the request")
                time.sleep(retry_after)
                continue

            # One short retry absorbs a blip without waiting a whole polling interval
            transient_retry = advice.retryable and not transient_retry_used
            retry_note = f"retrying in {display_time(TRANSIENT_RETRY_SECONDS if transient_retry else sleep_interval)}"
            if outage_outcome == "full":
                print_recovery_error(e, "runtime", retry_note=retry_note)
            elif outage_outcome == "changed":
                print_outage_change(riotid, advice)
            elif outage_outcome == "reminder":
                print_outage_liveness(riotid, advice, outage.since, outage.failures)
            if transient_retry:
                transient_retry_used = True
                if outage_outcome in ("full", "changed"):
                    print_cur_ts("Timestamp:\t\t\t")
                debug_print("Retry wait", check=f"#{check_count}", due_in=display_time(TRANSIENT_RETRY_SECONDS), reason="one short retry before the full interval")
                time.sleep(TRANSIENT_RETRY_SECONDS)
                continue

            if advice.code == "auth.api_key_invalid":
                m_subject = f"lol_monitor: API key error! (user: {riotid_name})"
            else:
                m_subject = f"lol_monitor: monitoring error (user: {riotid_name})"
            m_body = f"{advice.summary}{nl_ch}{nl_ch}To fix: {advice.fix}{nl_ch}{nl_ch}LoL Monitor will retry in {display_time(sleep_interval)}.{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
            m_body_html = (
                f"<html><head></head><body>"
                f"{html_text(advice.summary)}<br><br>To fix: {html_text(advice.fix)}<br><br>"
                f"LoL Monitor will retry in {html.escape(display_time(sleep_interval))}."
                f"{get_cur_ts('<br><br>Timestamp: ')}"
                f"</body></html>"
            )
            # A failure the tool can retry away is alerted once the outage has lasted ERROR_ALERT_AFTER_SECONDS, one it cannot at once
            alert_due = not advice.retryable or int(time.time()) - outage.since >= ERROR_ALERT_AFTER_SECONDS
            if alert_due and ((ERROR_NOTIFICATION and not error_email_sent) or (webhook_event_enabled("error") and not error_webhook_sent)):
                email_delivered, webhook_delivered = send_notification_channels("error", m_subject, m_body, m_body_html, email_enabled=ERROR_NOTIFICATION and not error_email_sent, webhook_enabled=webhook_event_enabled("error") and not error_webhook_sent, ntfy_priority=5, ntfy_tags="warning")
                error_email_sent = error_email_sent or email_delivered
                error_webhook_sent = error_webhook_sent or webhook_delivered
                # A delivery line can land on a check the outage reporter keeps quiet, and a line with nothing
                # under it reads as a run that stopped there
                delivery_reported = email_delivered or webhook_delivered

            if outage_outcome in ("full", "changed") or delivery_reported:
                print_cur_ts("Timestamp:\t\t\t")

            debug_print("Retry wait", check=f"#{check_count}", due_in=display_time(sleep_interval), reason="waiting out the failure")
            time.sleep(sleep_interval)
            continue


# The four shared status markers. A fifth neutral marker is the single biggest source of drift between these
# tools, because every state it would cover is a state the others already call PASS
DOCTOR_STATUSES = ("PASS", "WARN", "FAIL", "SKIP")

# Riot's development key allows 100 requests every two minutes and each in-game cycle spends several of them,
# so an active interval below this leaves no headroom for the extra calls a live match report makes
DOCTOR_MIN_SAFE_ACTIVE_INTERVAL = 10

# Preflight rows wait far less than a real delivery, so an unreachable host cannot stall the whole report
DOCTOR_PASSIVE_TIMEOUT = 5

# The sign-in behind --set-smtp-password is interactive, so it uses the same short deadline the report does
SECRET_ENTRY_SMTP_TIMEOUT = 5

# One wording per test message, shared with every sibling monitor. The subject names the tool, since the
# message lands beside the real alerts, and the body names the command that sent it
TEST_EMAIL_SUBJECT = "lol_monitor: test email"
TEST_EMAIL_BODY = "This test email was sent by --send-test-email. Your SMTP settings work."
TEST_WEBHOOK_TITLE = "lol_monitor: test webhook"
TEST_WEBHOOK_BODY = "This test notification was sent by --send-test-webhook. Your webhook settings work."
DOCTOR_TEST_EMAIL_SUBJECT = "lol_monitor: doctor test email"
DOCTOR_TEST_EMAIL_BODY = "This test email was sent after approval in --doctor. Your SMTP delivery settings work."
DOCTOR_TEST_WEBHOOK_TITLE = "lol_monitor: doctor test webhook"
DOCTOR_TEST_WEBHOOK_BODY = "This test notification was sent after approval in --doctor. Your webhook delivery settings work."

# The passing label of the email row, pinned so the wording cannot drift from the sibling monitors
SMTP_READY_CHECK_LABEL = "SMTP connection and login succeeded"

# The passing label of the webhook row, pinned so the wording cannot drift from the sibling monitors
WEBHOOK_READY_CHECK_LABEL = "Webhook URL, headers and alert choices look valid"

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
        self.webhook_ready = False


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
        advice = make_recovery_advice("dependency.missing", f"Python {version_text} is unsupported", recovery_fix_with_guide(f"Install Python {MINIMUM_PYTHON_VERSION_TEXT} or newer then retry", INSTALL_GUIDE_URL), False)
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

    if module_present("wcwidth"):
        checks.append(make_doctor_check("Environment", "PASS", "Optional dependency wcwidth is installed", "Used only to measure display width for screen truncation"))
    elif TRUNCATE_CHARS:
        advice = make_recovery_advice("dependency.missing", "Optional dependency wcwidth is not installed", recovery_fix_with_guide(f"Install it with: {pip_install_command('wcwidth')}. Or switch terminal truncation off", INSTALL_GUIDE_URL), False)
        checks.append(make_doctor_check("Environment", "WARN", advice.summary, "Terminal truncation is switched on but lines are printed in full. Every other feature is unaffected", advice))
    else:
        # A warning about a library nothing in this run would call is noise, so the row states why it was not needed
        checks.append(make_doctor_check("Environment", "SKIP", "Optional dependency wcwidth was not checked", "Terminal truncation is off, so nothing would measure display width"))
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
        # A preflight run without a target is checking everything else, so the exit code stays clean the way
        # every sibling monitor keeps it: nothing here is broken, the run was simply not told what to watch
        detail = f"No {' and no '.join(missing)} {'was' if len(missing) == 1 else 'were'} provided"
        advice = classify_recovery_error(context="target.missing", detail=detail)
        return [make_doctor_check("Target", "WARN", advice.summary, f"Nothing will be monitored until {'both are' if len(missing) > 1 else 'one is'} given", advice)]
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


# Reports whether the webhook destination, provider and alert choices could deliver, without sending anything
def doctor_check_webhook_notifications(report):
    selected_categories = _selected_webhook_notification_categories()
    # The error alert ships on by default, so it alone cannot mean the channel is switched on
    deliberate_categories = [category for category in selected_categories if category != "errors"]
    if not WEBHOOK_ENABLED and not deliberate_categories:
        return [make_doctor_check("Notifications", "PASS", "Webhook alerts are disabled", "No webhook destination was contacted and no notification was sent")]
    if not WEBHOOK_ENABLED:
        advice = make_recovery_advice("webhook.invalid", "Webhook alert types are selected but webhooks are switched off", recovery_fix_with_guide("Set WEBHOOK_ENABLED to True, or turn the alert types off", WEBHOOK_GUIDE_URL), False)
        return [make_doctor_check("Notifications", "WARN", advice.summary, "Nothing would ever be delivered", advice)]
    if not normalized_webhook_provider():
        advice = classify_recovery_error(context="webhook", detail="WEBHOOK_PROVIDER must be discord or ntfy")
        return [make_doctor_check("Notifications", "FAIL", advice.summary, advice.detail, advice)]
    if not validate_webhook_url():
        advice = classify_recovery_error(context="webhook", detail="WEBHOOK_URL must contain a complete HTTPS link")
        return [make_doctor_check("Notifications", "FAIL", advice.summary, advice.detail, advice)]
    for validation_error in (validate_webhook_customization(normalized_webhook_provider()), validate_webhook_headers(normalized_webhook_provider())):
        if validation_error is not None:
            advice = classify_recovery_error(context="webhook", detail=validation_error)
            return [make_doctor_check("Notifications", "FAIL", advice.summary, advice.detail, advice)]
    if not selected_categories:
        advice = make_recovery_advice("webhook.invalid", "Webhook alerts are on but no alert types are selected", recovery_fix_with_guide("Turn on at least one webhook alert in the configuration file, or set WEBHOOK_ENABLED to False", WEBHOOK_GUIDE_URL), False)
        return [make_doctor_check("Notifications", "WARN", advice.summary, "Nothing would ever be delivered", advice)]
    report.webhook_ready = True
    return [make_doctor_check("Notifications", "PASS", f"{WEBHOOK_READY_CHECK_LABEL} for {webhook_provider_display_name()}", f"Alerts: {', '.join(selected_categories)}. The private link was not displayed. No webhook was sent during this passive check")]


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
    return unwrap_terminal_stream(stream)


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
    print("Running preflight checks. No files will be written. Interactive email and webhook tests run only after separate approval.\n")


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
    if not terminal_is_interactive or not (report.email_ready or report.webhook_ready):
        return []
    print("\n" + DOCTOR_DELIVERY_SECTION + "\n")
    print("Doctor will not write files. Each approved test sends one real message.\n")
    checks = []
    if report.email_ready:
        if doctor_ask_yes_no("Send one test email now? This will deliver a real message", input_func=input_func):
            debug_print("Doctor test email", recipient=RECEIVER_EMAIL)
            delivered = send_email(DOCTOR_TEST_EMAIL_SUBJECT, DOCTOR_TEST_EMAIL_BODY, "", SMTP_SSL, smtp_timeout=DOCTOR_PASSIVE_TIMEOUT) == 0
            debug_print("Doctor test email", recipient=RECEIVER_EMAIL, outcome="OK" if delivered else "failed")
            if delivered:
                check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "PASS", "Doctor test email delivered", "One real test email was sent after confirmation")
            else:
                advice = make_recovery_advice("smtp.connection", "Doctor test email delivery failed", recovery_fix_with_guide("Review the SMTP error above and correct the email settings", SMTP_GUIDE_URL), True)
                check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "FAIL", advice.summary, "The approved test email could not be delivered", advice)
        else:
            check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "SKIP", "Test email was not sent", "You declined the real delivery test. Run doctor again and approve the email test when ready")
        checks.append(check)
        # Recorded on the report so the summary sentence and the exit code cannot disagree about the same run
        report.checks.append(check)
        print_doctor_check(check)
    if report.webhook_ready:
        provider = webhook_provider_display_name()
        if doctor_ask_yes_no(f"Send one test webhook through {provider} now? This will publish a real notification", input_func=input_func):
            debug_print("Doctor test webhook", channel=provider, host=webhook_destination_host())
            delivered = send_webhook(DOCTOR_TEST_WEBHOOK_TITLE, DOCTOR_TEST_WEBHOOK_BODY, "status", force=True) == 0
            debug_print("Doctor test webhook", channel=provider, outcome="OK" if delivered else "failed")
            if delivered:
                check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "PASS", f"Doctor test webhook through {provider} delivered", "One real test webhook was sent after confirmation")
            else:
                advice = make_recovery_advice("webhook.connection", f"Doctor test webhook through {provider} delivery failed", recovery_fix_with_guide("Review the webhook error above and correct the destination settings", WEBHOOK_GUIDE_URL), True)
                check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "FAIL", advice.summary, "The approved test webhook could not be delivered", advice)
        else:
            check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "SKIP", f"Test webhook through {provider} was not sent", "You declined the real delivery test. Run doctor again and approve the webhook test when ready")
        checks.append(check)
        report.checks.append(check)
        print_doctor_check(check)
    return checks


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
            ("notifications", lambda: doctor_check_email_notifications(report) + doctor_check_webhook_notifications(report)),
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
    print(f"    {colorize('section', command)}{colorize('info', suffix) if suffix else ''}\n")


# Returns the target arguments a printed command needs, leaving out a pair the configuration file already supplies
def command_target_arguments(riot_id=None, region=None, riot_id_saved=False, region_saved=False):
    if not riot_id or not region:
        # Monitoring cannot run without both, so the placeholders stay while the doctor reports the gap itself
        return [riot_id or RIOT_ID_PLACEHOLDER, region or REGION_PLACEHOLDER]
    if riot_id_saved and region_saved:
        return []
    return [riot_id, region]


# Returns a saved value fit to show as a prompt default, so a shipped placeholder is never offered back
def _wizard_default(value):
    return str(value) if doctor_value_is_set(value if isinstance(value, str) else str(value or "")) else ""


# Prints the shared line telling the user how defaults and cancelling work
def _wizard_print_default_guidance():
    print("Press Enter to accept the shown default. Ctrl+C cancels.\n")


# Reads one setup line, colorized like the sibling monitors. Cancelling propagates to the one
# handler in run_setup_wizard, which reports that nothing was written
def _wizard_input(prompt_text, input_func=None):
    prompt = input if input_func is None else input_func
    try:
        return read_interactively(prompt, colorize("info", prompt_text))
    except (EOFError, KeyboardInterrupt):
        # The interrupted prompt owns the line break, so every handler prints its message alone
        print()
        raise


# Asks one yes or no question with a visible default
def _wizard_ask_yes_no(question, default=True, input_func=None):
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        answer = _wizard_input(f"{question} {hint}: ", input_func=input_func).strip().casefold()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  Please answer 'y' or 'n'.")


# Offers the one way out after an entry the wizard cannot use, so declining keeps every answer already given
def _wizard_offer_retry(label, consequence="", input_func=None):
    if consequence:
        return not _wizard_ask_yes_no(f"Continue without the {label}? {consequence}", default=False, input_func=input_func)
    return _wizard_ask_yes_no(f"Try entering the {label} again?", default=True, input_func=input_func)


# Asks one free-text question, returning the shown default when the answer is empty
def _wizard_ask_text(question, default="", required=False, input_func=None):
    suffix = f" [{default}]" if default else ""
    while True:
        answer = _wizard_input(f"{question}{suffix}: ", input_func=input_func).strip()
        if not answer:
            answer = default
        if answer or not required:
            return answer
        print("  This value is required.")
        if not _wizard_offer_retry(question, input_func=input_func):
            return ""


# Asks one numbered multiple-choice question and returns the chosen index
def _wizard_ask_choice(question, options, default_index=0, input_func=None):
    print()
    print(question)
    for index, (label, description) in enumerate(options, 1):
        marker = " (default)" if index - 1 == default_index else ""
        print(f"  {colorize('username', str(index))}. {label}{colorize('info', marker)}")
        if description:
            for line in description.splitlines():
                print(f"     {line}")
    while True:
        answer = _wizard_input(f"Choose [1-{len(options)}]: ", input_func=input_func).strip()
        if not answer:
            return default_index
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return int(answer) - 1
        print(f"  Enter a number between 1 and {len(options)}.")


# Trims the parenthetical hint from a question, so the retry offer that repeats it stays one readable line
def _wizard_retry_label(question):
    return question.split(" (")[0].strip()


# Asks until the user provides a positive whole number or accepts the default
def _wizard_ask_positive_int(question, default, maximum=None, input_func=None):
    while True:
        answer = _wizard_ask_text(question, default=str(default), required=True, input_func=input_func)
        # An empty answer means the retry offer was declined, so the default stands instead of asking again
        if not answer:
            return int(default)
        try:
            parsed = int(answer)
        except ValueError:
            parsed = 0
        if parsed > 0 and (maximum is None or parsed <= maximum):
            return parsed
        print(f"  Enter a whole number from 1 through {maximum}." if maximum is not None else "  Enter a positive whole number.")
        # A value the helper cannot use is a rejected entry, so it gets the same way out an empty one gets
        if not _wizard_offer_retry(_wizard_retry_label(question), input_func=input_func):
            print(f"  Keeping {default}.")
            return int(default)


# Renders a wizard duration as raw seconds plus a readable form, so the stored config value stays visible
def _wizard_format_duration(seconds):
    remaining = seconds
    parts = []
    for suffix, count in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        value, remaining = divmod(remaining, count)
        if value:
            parts.append(f"{value}{suffix}")
    raw = f"{seconds}s"
    readable = " ".join(parts) or raw
    return raw if readable == raw else f"{raw} - {readable}"


# Asks one duration, accepting the formats people actually type
def _wizard_ask_duration(question, default, input_func=None):
    prompt_text = f"{question} [{_wizard_format_duration(default)}]: "
    while True:
        answer = _wizard_input(prompt_text, input_func=input_func).strip()
        if not answer:
            return default
        seconds = parse_duration_input(answer)
        if seconds is not None:
            return seconds
        print("  Enter a positive duration such as 120, 2m, 1.5h, 1h 30m or 1d.")
        if not _wizard_offer_retry(_wizard_retry_label(question), input_func=input_func):
            print(f"  Keeping {_wizard_format_duration(default)}.")
            return default


# Asks one secret through a hidden prompt with debug output off, so it never reaches the screen, the shell history or the debug stream
def _wizard_ask_secret(question, getpass_func=None):
    hidden_prompt = getpass.getpass if getpass_func is None else getpass_func
    try:
        # Colorized like the visible prompts, so a hidden answer does not look like a different question
        with debug_output_suppressed():
            return str(read_secret_interactively(hidden_prompt, colorize("info", f"{question}: "))).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise


# Checks one setup destination without creating or modifying it, so an unwritable path is caught before any question
def _wizard_validate_destination(path, label):
    destination = Path(path).expanduser().resolve()
    if destination.exists() and destination.is_dir():
        raise ValueError(f"{label} must be a file path, not a directory")
    parent = nearest_existing_parent(destination)
    if not parent.is_dir():
        raise ValueError(f"{label} does not have a usable parent directory")
    if not os.access(str(parent), os.W_OK):
        raise ValueError(f"{label} is not writable through parent '{parent}'")
    return destination


# Resolves both setup destinations, refusing the disabled settings that leave nowhere to write
def _wizard_destinations(config_file=None, env_file=None):
    if config_file is not None and str(config_file).casefold() == "none":
        raise ValueError("--setup has nowhere to write the configuration")
    if env_file is not None and str(env_file).casefold() == "none":
        raise ValueError("--setup has nowhere to write the private settings")
    config_path = Path(config_file).expanduser() if config_file is not None else Path.cwd() / DEFAULT_CONFIG_FILENAME
    env_path = Path(env_file).expanduser() if env_file is not None else Path.cwd() / ".env"
    return _wizard_validate_destination(config_path, "Configuration destination"), _wizard_validate_destination(env_path, "Dotenv destination")


# Confirms replacing an existing config before any question is asked, so a long run cannot end in a surprise
def _wizard_choose_config_destination(config_path, input_func=None):
    selected = Path(config_path)
    while selected.exists() and not _wizard_ask_yes_no(f"Configuration file '{selected}' exists. A timestamped backup is kept. Rebuild it from your answers, starting from its current settings?", default=False, input_func=input_func):
        alternative = _wizard_ask_text("Another config destination or leave empty to cancel", input_func=input_func)
        if not alternative:
            return None
        try:
            selected = _wizard_validate_destination(alternative, "Configuration destination")
        except ValueError as exc:
            print(f"  {exc}.")
    return selected


# Queues one secret for the save step, asking first when the dotenv file already assigns it
def _wizard_queue_secret(state, key, value, input_func=None):
    if not value:
        return False
    if _dotenv_contains_key(state.env_path, key) and not _wizard_ask_yes_no(f"The dotenv file already contains {key}. Replace that value?", default=False, input_func=input_func):
        print(f"  Existing {key} will be retained without being displayed or rewritten.")
        return False
    state.secret_updates[key] = value
    return True


# Reports whether a usable secret is already saved, without reading its value into the transcript
def _wizard_existing_secret(key, env_path):
    value = None
    path = Path(env_path)
    if path.is_file():
        try:
            from dotenv import dotenv_values
            value = dotenv_values(path, interpolate=False).get(key)
        except Exception:
            value = None
    if value is None:
        value = os.environ.get(key)
    return doctor_value_is_set(value)


# Holds every wizard answer until the user explicitly saves, so nothing is written during questioning
class WizardSetupState:
    # Starts from the values already in effect, which become both the defaults and the revert target
    def __init__(self, config_path, env_path, baseline_values):
        self.config_path = Path(config_path)
        self.env_path = Path(env_path)
        self.baseline_values = dict(baseline_values)
        self.config_values = dict(baseline_values)
        self.secret_updates = {}
        self.riot_id = ""
        self.region = ""
        self.persist_target = True
        self.target_verified = False


# The mail server settings the wizard collects, and how long its sign-in check waits for the server
WIZARD_SMTP_CONFIG_KEYS = ("SMTP_HOST", "SMTP_PORT", "SMTP_SSL", "SMTP_USER", "SENDER_EMAIL", "RECEIVER_EMAIL")
WIZARD_SMTP_TIMEOUT = 5

# The email and webhook alert settings the wizard offers, in the order the questions are asked
WIZARD_EMAIL_NOTIFICATION_KEYS = ("STATUS_NOTIFICATION", "ERROR_NOTIFICATION")
WIZARD_WEBHOOK_NOTIFICATION_KEYS = ("WEBHOOK_STATUS_NOTIFICATION", "WEBHOOK_ERROR_NOTIFICATION")

# Each editable section: internal name, menu label and description, then the keys reverted when it is re-entered
WIZARD_SECTIONS = (
    ("Target", "Target", "Change the Riot ID and region that are monitored.", ("RIOT_ID", "REGION"), ()),
    ("Polling", "Polling interval", "Change how often Riot is checked.", ("LOL_CHECK_INTERVAL", "LOL_ACTIVE_CHECK_INTERVAL"), ()),
    ("Authentication", "Authentication", "Enter the Riot API key again.", (), ("RIOT_API_KEY",)),
    ("Email", "Email notifications", "Change SMTP details and email events.", WIZARD_SMTP_CONFIG_KEYS + WIZARD_EMAIL_NOTIFICATION_KEYS, ("SMTP_PASSWORD",)),
    ("Webhook", "Webhook alerts", "Change Discord or ntfy details and events.", ("WEBHOOK_ENABLED", "WEBHOOK_PROVIDER") + WIZARD_WEBHOOK_NOTIFICATION_KEYS, ("WEBHOOK_URL", "NTFY_ACCESS_TOKEN")),
    ("Output", "Output files", "Change the log and CSV destinations.", ("DISABLE_LOGGING", "CSV_FILE"), ()),
    ("Destinations", "File destinations", "Change the configuration or dotenv output path.", (), ()),
)


# Restores one section to the values setup started with and drops any secret it had queued
def _wizard_reset_section(state, config_keys, secret_keys):
    for key in config_keys:
        if key in state.baseline_values:
            state.config_values[key] = state.baseline_values[key]
        else:
            state.config_values.pop(key, None)
    for key in secret_keys:
        state.secret_updates.pop(key, None)


# Returns one declined section to the built-in template values, so nothing the user turned down is written
def _wizard_clear_section(state, config_keys, secret_keys=()):
    defaults = _config_template_defaults()
    for key in config_keys:
        if key in defaults:
            state.config_values[key] = defaults[key]
        else:
            state.config_values.pop(key, None)
    for key in secret_keys:
        state.secret_updates.pop(key, None)


# Mirrors the settled target into the config values, so an unpersisted target is left out of the file
def _wizard_apply_target(state):
    state.config_values["RIOT_ID"] = state.riot_id if state.persist_target and state.riot_id else ""
    state.config_values["REGION"] = state.region if state.persist_target and state.region else ""


# Asks for the monitored Riot ID and its region, storing both in the one form everything else reads
def _wizard_collect_target_section(state, initial_riot_id=None, initial_region=None, input_func=None):
    state.target_verified = False
    riot_id_question = f"Riot ID to monitor ({RIOT_ID_FORMS})"
    region_question = f"Region ({REGION_FORMS})"
    state.riot_id = ""
    while True:
        answer = _wizard_ask_text(riot_id_question, default=str(initial_riot_id or state.config_values.get("RIOT_ID") or ""), required=True, input_func=input_func)
        if not answer:
            # The question already offered another attempt and it was declined, so the section ends instead of asking again
            break
        try:
            state.riot_id = normalize_riot_id(answer)
            break
        except ValueError as exc:
            print(f"  {exc}")
            if not _wizard_offer_retry(_wizard_retry_label(riot_id_question), input_func=input_func):
                break
    if not state.riot_id:
        print("  No target selected. Nothing can be monitored until one is set. Run --setup again or pass the target on the command line.")
        state.region = ""
        _wizard_apply_target(state)
        return
    while True:
        answer = _wizard_ask_text(region_question, default=str(initial_region or state.config_values.get("REGION") or ""), required=True, input_func=input_func)
        if not answer:
            break
        normalized = normalize_region(answer)
        if REGION_TO_CONTINENT.get(normalized):
            state.region = normalized
            break
        print(f"  '{answer}' is not a region this tool knows. Use the short code rather than the display name.")
        if not _wizard_offer_retry(_wizard_retry_label(region_question), input_func=input_func):
            break
    if not state.region:
        print("  No region selected. Nothing can be monitored until one is set. Run --setup again or pass the region on the command line.")
        state.riot_id = ""
        _wizard_apply_target(state)
        return
    state.persist_target = _wizard_ask_yes_no("Persist this target in the generated config?", default=state.persist_target, input_func=input_func)
    _wizard_apply_target(state)


# Asks Riot whether the collected account exists, using the key the wizard just accepted
def _wizard_verify_target(state):
    api_key = state.secret_updates.get("RIOT_API_KEY") or state.config_values.get("RIOT_API_KEY")
    previous_key = RIOT_API_KEY
    globals()["RIOT_API_KEY"] = api_key
    try:
        asyncio.run(riot_account_probe(state.riot_id, state.region))
        return True
    except Exception as exc:
        debug_swallowed_exception("Wizard target check", exc)
        return False
    finally:
        globals()["RIOT_API_KEY"] = previous_key


# Checks the collected target against Riot once a key is available, so a typo is caught before anything is written
def _wizard_confirm_target(state, input_func=None):
    while state.riot_id and state.region and not state.target_verified:
        api_key = state.secret_updates.get("RIOT_API_KEY") or state.config_values.get("RIOT_API_KEY")
        if not doctor_value_is_set(api_key):
            print(f"  '{state.riot_id}' was not checked with Riot, which needs an API key. Run --doctor once one is set.")
            return
        print("  Checking the Riot ID with Riot ...")
        if _wizard_verify_target(state):
            state.target_verified = True
            print(f"  Riot found {state.riot_id} on {state.region}.")
            return
        print(f"  Riot has no account for '{state.riot_id}' on '{state.region}'. Check the game name, the tag line and the region.")
        if not _wizard_offer_retry("target", "Nothing can be monitored until one is set", input_func=input_func):
            _wizard_clear_section(state, ("RIOT_ID", "REGION"))
            state.riot_id = ""
            state.region = ""
            return
        print()
        _wizard_collect_target_section(state, input_func=input_func)


# Asks how often the tool checks, in whichever duration format the user prefers
def _wizard_collect_polling_section(state, input_func=None):
    state.config_values["LOL_CHECK_INTERVAL"] = _wizard_ask_duration("Riot polling interval while not in game (seconds or use s/m/h/d)", int(state.config_values.get("LOL_CHECK_INTERVAL") or LOL_CHECK_INTERVAL), input_func=input_func)
    state.config_values["LOL_ACTIVE_CHECK_INTERVAL"] = _wizard_ask_duration("Riot polling interval while in game (seconds or use s/m/h/d)", int(state.config_values.get("LOL_ACTIVE_CHECK_INTERVAL") or LOL_ACTIVE_CHECK_INTERVAL), input_func=input_func)


# Asks for the Riot API key through a hidden prompt and validates it against Riot before accepting it
def _wizard_collect_auth_section(state, input_func=None, getpass_func=None, validator=None):
    print(f"Create or view your Riot API key: {RIOT_API_KEY_REGISTRATION_URL}")
    existing = doctor_value_is_set(state.config_values.get("RIOT_API_KEY"))
    if existing and not _wizard_ask_yes_no("Replace the Riot API key already configured?", default=False, input_func=input_func):
        return
    validate = validate_riot_api_key if validator is None else validator
    while True:
        api_key = _wizard_ask_secret("Riot API key", getpass_func=getpass_func)
        if not api_key:
            # Monitoring cannot run without it, so leaving it unset has to be a decision rather than a fallthrough
            if not _wizard_offer_retry("Riot API key", "Nothing can be monitored until one is set", input_func=input_func):
                return
            continue
        # Riot is contacted here, which takes long enough to look like a hang without a notice
        print("  Checking the key with Riot ...")
        if validate(api_key):
            state.secret_updates["RIOT_API_KEY"] = api_key
            print("  Riot accepted the key.")
            return
        print("  Riot rejected that key. A development key expires 24 hours after it is issued.")
        # A key Riot keeps rejecting cannot be corrected from inside the loop, so the wizard must be leavable here too
        if not _wizard_offer_retry("Riot API key", input_func=input_func):
            return


# Switches every email alert off together, so an abandoned answer cannot leave half a mail server configured
def _wizard_disable_email(state):
    _wizard_clear_section(state, WIZARD_SMTP_CONFIG_KEYS, ("SMTP_PASSWORD",))
    # Only the alerts the wizard offers are cleared, so alerts enabled by hand survive a declined email section
    for key in WIZARD_EMAIL_NOTIFICATION_KEYS:
        state.config_values[key] = False


# Signs in to the collected mail server without sending anything, so a refused login is caught during setup
def _wizard_verify_smtp(values, password):
    names = WIZARD_SMTP_CONFIG_KEYS + ("SMTP_PASSWORD",)
    previous = {name: globals()[name] for name in names}
    smtp_object = None
    try:
        globals().update(values)
        # A blank answer keeps the password already stored, which is the one the sign-in must then prove
        globals()["SMTP_PASSWORD"] = password or previous["SMTP_PASSWORD"]
        smtp_object = smtp_connect_and_login(SMTP_SSL, smtp_timeout=WIZARD_SMTP_TIMEOUT)
        return None
    except Exception as exc:
        return classify_recovery_error(exc, "email")
    finally:
        if smtp_object is not None:
            try:
                smtp_object.quit()
            except Exception:
                pass
        globals().update(previous)


# Reports the outcome of the sign-in check: True to continue, False to ask again, None to switch email off
def _wizard_smtp_sign_in_accepted(values, password, input_func=None):
    print("  Checking the sign-in with the mail server ...")
    advice = _wizard_verify_smtp(values, password)
    if advice is None:
        print("  The mail server accepted the sign-in. No email was sent.")
        return True
    print(f"  {advice.summary}: {advice.detail}" if advice.detail else f"  {advice.summary}")
    print(f"  To fix: {advice.fix}")
    if _wizard_offer_retry("mail server settings", input_func=input_func):
        return False
    if advice.retryable:
        # Being offline is the usual reason a correct setup fails here, so the answers are kept rather than discarded
        print("  The settings were kept without being checked. Run --doctor to check the sign-in again.")
        return True
    print("  Email notifications stay off until the mail server accepts the settings.")
    return None


# Reports whether one required mail server answer was abandoned, switching the channel off when it was
def _wizard_email_answer_missing(state, key):
    if state.config_values.get(key):
        return False
    print("  Email notifications stay off until every mail server setting is answered.")
    _wizard_disable_email(state)
    return True


# Reports whether the saved settings already send email, so a rerun proposes keeping the channel it has
def _wizard_email_enabled(config_values):
    # The error alert ships switched on, so on its own it counts only once a mail server has been named
    for key in WIZARD_EMAIL_NOTIFICATION_KEYS:
        if key != "ERROR_NOTIFICATION" and bool(config_values.get(key)):
            return True
    return bool(config_values.get("ERROR_NOTIFICATION")) and doctor_value_is_set(config_values.get("SMTP_HOST"))


# Asks which alerts one channel should send, offering the recommended preset before the per-alert questions
def _wizard_collect_alert_preset(question, recommended_description, custom_description, keys, questions, input_func=None):
    # Every alert this tool has is in the recommended preset, so an 'Every supported event' entry would repeat it
    preset = _wizard_ask_choice(question, [
        ("Status and errors, recommended", recommended_description),
        ("Custom", custom_description),
    ], input_func=input_func)
    if preset == 0:
        return {name: True for name in keys}
    print()
    return {name: _wizard_ask_yes_no(text, default=False, input_func=input_func) for name, text in questions}


# Asks whether to send email alerts and collects only the settings that choice needs
def _wizard_collect_email_section(state, input_func=None, getpass_func=None):
    if not _wizard_ask_yes_no("Configure email notifications?", default=_wizard_email_enabled(state.config_values), input_func=input_func):
        _wizard_disable_email(state)
        return
    while True:
        state.config_values["SMTP_HOST"] = _wizard_ask_text("SMTP host", default=_wizard_default(state.config_values.get("SMTP_HOST")), required=True, input_func=input_func)
        if _wizard_email_answer_missing(state, "SMTP_HOST"):
            return
        state.config_values["SMTP_PORT"] = _wizard_ask_positive_int("SMTP port", int(state.config_values.get("SMTP_PORT") or 587), maximum=65535, input_func=input_func)
        state.config_values["SMTP_SSL"] = _wizard_ask_yes_no("Enable TLS/SSL for SMTP?", default=bool(state.config_values.get("SMTP_SSL")), input_func=input_func)
        state.config_values["SMTP_USER"] = _wizard_ask_text("SMTP username", default=_wizard_default(state.config_values.get("SMTP_USER")), required=True, input_func=input_func)
        if _wizard_email_answer_missing(state, "SMTP_USER"):
            return
        state.config_values["SENDER_EMAIL"] = _wizard_ask_text("Sender email", default=_wizard_default(state.config_values.get("SENDER_EMAIL")), required=True, input_func=input_func)
        if _wizard_email_answer_missing(state, "SENDER_EMAIL"):
            return
        state.config_values["RECEIVER_EMAIL"] = _wizard_ask_text("Receiver email", default=_wizard_default(state.config_values.get("RECEIVER_EMAIL")), required=True, input_func=input_func)
        if _wizard_email_answer_missing(state, "RECEIVER_EMAIL"):
            return
        password = _wizard_ask_secret("SMTP password", getpass_func=getpass_func)
        if password:
            _wizard_queue_secret(state, "SMTP_PASSWORD", password, input_func=input_func)
        outcome = _wizard_smtp_sign_in_accepted({name: state.config_values[name] for name in WIZARD_SMTP_CONFIG_KEYS}, password, input_func=input_func)
        if outcome is None:
            _wizard_disable_email(state)
            return
        if outcome:
            break
    state.config_values.update(_wizard_collect_alert_preset(
        "Which email notifications should be enabled?",
        "Emails when the player starts or stops a match, and when monitoring has a problem.",
        "Choose each notification type separately.",
        WIZARD_EMAIL_NOTIFICATION_KEYS,
        (("STATUS_NOTIFICATION", "Email when the player starts or stops a match?"), ("ERROR_NOTIFICATION", "Email on monitoring errors?")),
        input_func=input_func,
    ))


# Switches the channel and every alert it owns off together, so a half-configured webhook cannot be written
def _wizard_disable_webhook(state):
    _wizard_clear_section(state, ("WEBHOOK_PROVIDER",), ("WEBHOOK_URL", "NTFY_ACCESS_TOKEN"))
    state.config_values["WEBHOOK_ENABLED"] = False
    state.config_values.update({name: False for name in WIZARD_WEBHOOK_NOTIFICATION_KEYS})


# Collects an optional ntfy access token without displaying it or contacting the service
def _wizard_collect_ntfy_access_token(state, input_func=None, getpass_func=None):
    if _wizard_existing_secret("NTFY_ACCESS_TOKEN", state.env_path):
        choice = _wizard_ask_choice("Which ntfy authentication should be used?", [
            ("Keep the saved access token", "Keeps the private value without displaying or changing it."),
            ("Paste a new access token", "Uses a hidden prompt then saves the replacement in .env."),
            ("Do not use an access token", "Disables the saved token. Authentication in the topic URL still works."),
        ], input_func=input_func)
        if choice == 0:
            return
        if choice == 2:
            state.secret_updates["NTFY_ACCESS_TOKEN"] = ""
            print("  The saved ntfy access token will be disabled without being displayed.")
            return
    elif not _wizard_ask_yes_no("Authenticate this ntfy topic with a separate access token?", default=False, input_func=input_func):
        print("  No separate access token selected. Authentication already present in the topic URL still works.")
        return
    while True:
        token = _wizard_ask_secret("Paste the ntfy access token only", getpass_func=getpass_func)
        if not token or ("\r" not in token and "\n" not in token and not token.casefold().startswith(("bearer ", "basic "))):
            if token:
                state.secret_updates["NTFY_ACCESS_TOKEN"] = token
            return
        print("  Paste only the access token without a Bearer or Basic prefix.")
        if not _wizard_offer_retry("ntfy access token", input_func=input_func):
            return


# Asks whether to send webhook alerts and collects the provider, the hidden URL and the alert choices
def _wizard_collect_webhook_section(state, input_func=None, getpass_func=None):
    if not _wizard_ask_yes_no("Set up webhook alerts (Discord, ntfy etc.)?", default=bool(state.config_values.get("WEBHOOK_ENABLED")), input_func=input_func):
        _wizard_disable_webhook(state)
        return
    provider_choice = _wizard_ask_choice("Which webhook service should receive alerts?", [
        ("Discord", "Sends a Discord embed to one channel webhook."),
        ("ntfy", "Sends a native notification to one ntfy topic URL."),
    ], input_func=input_func)
    provider = "discord" if provider_choice == 0 else "ntfy"
    state.config_values["WEBHOOK_PROVIDER"] = provider
    if provider == "discord":
        print("  In Discord: Edit Channel > Integrations > Webhooks > New Webhook > Copy Webhook URL.")
    else:
        print("  In ntfy: choose a hard-to-guess topic. Paste its complete topic URL, or just the topic name when it is hosted on ntfy.sh.")
    replace_webhook = True
    if _wizard_existing_secret("WEBHOOK_URL", state.env_path):
        choice = _wizard_ask_choice("Which webhook URL should be used?", [
            ("Keep the saved URL", "Keeps the private value without displaying or changing it."),
            ("Paste a new URL", "Uses a hidden prompt then saves the new private value in .env."),
        ], input_func=input_func)
        replace_webhook = choice == 1
    if replace_webhook:
        while True:
            answer = _wizard_ask_secret("Paste the Discord webhook URL" if provider == "discord" else "Paste the ntfy topic URL or ntfy.sh topic name", getpass_func=getpass_func)
            webhook_url = normalize_ntfy_topic_url(answer) if provider == "ntfy" else answer.strip()
            if validate_webhook_url(webhook_url):
                state.secret_updates["WEBHOOK_URL"] = webhook_url
                break
            # Nothing can be delivered without a destination, so giving up has to stay reachable from the prompt.
            # The branch is chosen by what was typed rather than by the normalized value, since a rejected ntfy
            # topic normalizes to an empty string and would otherwise be reported as nothing entered
            if not answer.strip():
                if not _wizard_offer_retry("webhook URL", "Webhook alerts stay off until one is set", input_func=input_func):
                    _wizard_disable_webhook(state)
                    return
                continue
            if provider == "ntfy":
                print("  Enter a complete HTTPS ntfy topic URL or a topic name containing up to 64 letters, numbers, dashes or underscores.")
            else:
                print("  That does not look like a complete HTTPS webhook URL. Copy it from the webhook service and try again.")
            if not _wizard_offer_retry("webhook URL", input_func=input_func):
                _wizard_disable_webhook(state)
                return
    if provider == "ntfy":
        _wizard_collect_ntfy_access_token(state, input_func=input_func, getpass_func=getpass_func)
    state.config_values["WEBHOOK_ENABLED"] = True
    state.config_values.update(_wizard_collect_alert_preset(
        "Which webhook alerts should be sent?",
        "Alerts when the player starts or stops a match, and when monitoring has a problem.",
        "Choose each webhook alert separately.",
        WIZARD_WEBHOOK_NOTIFICATION_KEYS,
        (("WEBHOOK_STATUS_NOTIFICATION", "Send a webhook alert when the player starts or stops a match?"), ("WEBHOOK_ERROR_NOTIFICATION", "Send a webhook alert when monitoring has a problem?")),
        input_func=input_func,
    ))


# Adds the .csv extension when the answer carries none, so a bare name still names a CSV file
def _wizard_normalize_csv_path(answer):
    text = str(answer).strip()
    if not text or Path(text).suffix:
        return text
    return text + ".csv"


# Collects the log and CSV output destinations monitoring would write
def _wizard_collect_output_section(state, input_func=None):
    state.config_values["DISABLE_LOGGING"] = not _wizard_ask_yes_no("Write the normal per-target log file?", default=not bool(state.config_values.get("DISABLE_LOGGING")), input_func=input_func)
    state.config_values["CSV_FILE"] = _wizard_normalize_csv_path(_wizard_ask_text("Optional CSV output path (blank disables it)", default=str(state.config_values.get("CSV_FILE") or ""), input_func=input_func))


# Changes where setup writes, re-asking the sections that hold secrets when the dotenv destination moves
def _wizard_collect_destination_section(state, input_func=None, getpass_func=None):
    while True:
        config_text = _wizard_ask_text("Configuration file destination", default=str(state.config_path), required=True, input_func=input_func)
        try:
            selected_config = _wizard_validate_destination(config_text, "Configuration destination")
            break
        except ValueError as exc:
            print(f"  {exc}.")
    # Both sides are compared resolved, so an unchanged answer written a different way is not read as a move
    if selected_config != Path(state.config_path).expanduser().resolve():
        chosen_config = _wizard_choose_config_destination(selected_config, input_func=input_func)
        # Giving up on every offered path keeps the current destination rather than cancelling the whole setup
        if chosen_config is not None:
            state.config_path = chosen_config
    while True:
        env_text = _wizard_ask_text("Dotenv file destination", default=str(state.env_path), required=True, input_func=input_func)
        if env_text.casefold() == "none":
            print("  Setup needs a writable dotenv file and cannot use 'none'.")
            continue
        try:
            selected_env = _wizard_validate_destination(env_text, "Dotenv destination")
        except ValueError as exc:
            print(f"  {exc}.")
            continue
        # One file cannot hold both, since saving the configuration would overwrite the secrets beside it
        if selected_env == Path(state.config_path).expanduser().resolve():
            print("  The dotenv file has to be a different file from the configuration.")
            continue
        break
    state.config_values["DOTENV_FILE"] = str(selected_env)
    if selected_env == Path(state.env_path).expanduser().resolve():
        return
    state.env_path = selected_env
    # A secret kept rather than retyped was never queued, so it would be missing from a dotenv file that just moved
    print("  The dotenv destination changed. Re-enter authentication and notification settings that may contain secrets.")
    _wizard_collect_auth_section(state, input_func=input_func, getpass_func=getpass_func)
    _wizard_confirm_target(state, input_func=input_func)
    print()
    _wizard_collect_email_section(state, input_func=input_func, getpass_func=getpass_func)
    print()
    _wizard_collect_webhook_section(state, input_func=input_func, getpass_func=getpass_func)


# Runs one editable section again after resetting only the keys it owns
def _wizard_edit_setup_section(state, input_func=None, getpass_func=None):
    options = [(label, description) for _name, label, description, _config_keys, _secret_keys in WIZARD_SECTIONS]
    options.append(("Return to summary", "Keep every current answer."))
    choice = _wizard_ask_choice("Which setup section should be changed?", options, input_func=input_func)
    if choice == len(WIZARD_SECTIONS):
        return
    name, _label, _description, config_keys, secret_keys = WIZARD_SECTIONS[choice]
    _wizard_reset_section(state, config_keys, secret_keys)
    if name == "Target":
        state.riot_id = ""
        state.region = ""
    print()
    collectors = {
        "Target": lambda: _wizard_collect_target_section(state, input_func=input_func),
        "Polling": lambda: _wizard_collect_polling_section(state, input_func=input_func),
        "Authentication": lambda: _wizard_collect_auth_section(state, input_func=input_func, getpass_func=getpass_func),
        "Email": lambda: _wizard_collect_email_section(state, input_func=input_func, getpass_func=getpass_func),
        "Webhook": lambda: _wizard_collect_webhook_section(state, input_func=input_func, getpass_func=getpass_func),
        "Output": lambda: _wizard_collect_output_section(state, input_func=input_func),
        "Destinations": lambda: _wizard_collect_destination_section(state, input_func=input_func, getpass_func=getpass_func),
    }
    collectors[name]()
    if name in ("Target", "Authentication"):
        _wizard_confirm_target(state, input_func=input_func)


# The theme part each setup summary row draws its value in, for rows whose value has a known kind
WIZARD_SUMMARY_VALUE_STYLES = {"Target": "username", "Polling interval while not in game": "duration", "Polling interval while in game": "duration"}


# Colours one setup summary value from its row label
def _wizard_summary_value(label, value):
    text = str(value)
    part = WIZARD_SUMMARY_VALUE_STYLES.get(label)
    if part:
        return colorize(part, text)
    if text.startswith("enabled") or text == "complete":
        return colorize("boolean_true", text)
    if text in ("disabled", "incomplete"):
        return colorize("boolean_false", text)
    return text


# Prints one aligned label and value block, so every summary row lines up
def _wizard_print_summary_rows(rows):
    width = max(len(label) for label, _ in rows) + 1
    for label, value in rows:
        print(f"  {(label + ':'):<{width}} {_wizard_summary_value(label, value)}")


# Shows everything that is about to be written, by name and never by secret value
def _wizard_print_setup_summary(state):
    email_labels = {"STATUS_NOTIFICATION": "status changes", "ERROR_NOTIFICATION": "errors"}
    webhook_labels = {"WEBHOOK_STATUS_NOTIFICATION": "status changes", "WEBHOOK_ERROR_NOTIFICATION": "errors"}
    enabled_email = [email_labels[name] for name in WIZARD_EMAIL_NOTIFICATION_KEYS if state.config_values.get(name)]
    enabled_webhooks = [webhook_labels[name] for name in WIZARD_WEBHOOK_NOTIFICATION_KEYS if state.config_values.get(name)] if state.config_values.get("WEBHOOK_ENABLED") else []
    api_key_set = "RIOT_API_KEY" in state.secret_updates or doctor_value_is_set(state.config_values.get("RIOT_API_KEY"))
    webhook_state = f"enabled ({webhook_provider_display_name(state.config_values.get('WEBHOOK_PROVIDER'))})" if state.config_values.get("WEBHOOK_ENABLED") else "disabled"
    rows = [
        ("Target", f"{state.riot_id} ({state.region})" if state.riot_id and state.region else "not set"),
        ("Persist target", "yes" if state.persist_target else "no"),
        ("Polling interval while not in game", _wizard_format_duration(int(state.config_values.get("LOL_CHECK_INTERVAL") or 0))),
        ("Polling interval while in game", _wizard_format_duration(int(state.config_values.get("LOL_ACTIVE_CHECK_INTERVAL") or 0))),
        ("Authentication status", "complete" if api_key_set else "incomplete"),
        ("Email", "enabled" if enabled_email else "disabled"),
        ("Email notifications", ", ".join(enabled_email) if enabled_email else "none"),
        ("Webhook", webhook_state),
        ("Webhook alerts", ", ".join(enabled_webhooks) if enabled_webhooks else "none"),
        ("Output log", "disabled" if state.config_values.get("DISABLE_LOGGING") else "enabled"),
        ("CSV output", state.config_values.get("CSV_FILE") or "disabled"),
        ("Config destination", state.config_path),
        ("Dotenv destination", state.env_path),
        ("Install method", install_method_display_name()),
    ]
    print(colorize("header", "\nSetup summary\n"))
    _wizard_print_summary_rows(rows)


# Loops on the summary until the user saves or explicitly discards, so nothing is written by accident
def _wizard_review_setup(state, input_func=None, getpass_func=None):
    while True:
        _wizard_print_setup_summary(state)
        action = _wizard_ask_choice("What would you like to do?", [
            ("Save settings", "Write the displayed settings to the selected files."),
            ("Review or change settings", "Edit one section without losing the other answers."),
            ("Discard answers and exit", "Leave the destination files unchanged."),
        ], input_func=input_func)
        if action == 0:
            return True
        if action == 1:
            _wizard_edit_setup_section(state, input_func=input_func, getpass_func=getpass_func)
            continue
        print()
        if _wizard_ask_yes_no("Discard all entered answers and exit?", default=False, input_func=input_func):
            return False
        print("  Setup answers retained.")


# Prints where setup will write and which install method the printed commands are written for
def _wizard_print_setup_destinations(method, config_path, env_path):
    print(f"Detected install method: {colorize('username', method)}")
    print(f"Configuration:          {config_path}")
    print(f"Dotenv:                 {env_path}\n")


# Puts the values setup just saved into effect, so doctor checks the written files instead of the pre-setup state
def _wizard_apply_saved_values(state, env_path=None):
    # Config values first: they carry the unset placeholders for every secret, which would otherwise
    # overwrite the secrets applied below and make doctor report a working setup as unconfigured
    globals().update(state.config_values)
    if env_path:
        try:
            reload_dotenv_secrets(str(env_path))
        except Exception:
            # Reading the file back needs python-dotenv, so the entered values are applied directly below
            pass
    load_secrets_from_environment()
    # Secrets exported before startup keep winning here, exactly as they will when monitoring runs
    for key, value in state.secret_updates.items():
        if key not in EXPORTED_SECRET_KEYS and not doctor_value_is_set(globals().get(key)):
            globals()[key] = value


# Builds the exact local command that starts this monitor, used when setup offers to launch it
def _wizard_local_command_args(riot_id=None, region=None, config_path=None, env_path=None):
    executable = sys.executable or ("python" if platform.system() == "Windows" else "python3")
    arguments = [executable, "-m", "lol_monitor"] if install_method() == INSTALL_METHOD_PYPI else [executable, str(Path(__file__).resolve())]
    if riot_id and region:
        arguments.extend([str(riot_id), str(region)])
    if config_path:
        arguments.extend(["--config-file", str(config_path)])
    if env_path:
        arguments.extend(["--env-file", str(env_path)])
    return arguments


# Hands the terminal to the monitor, replacing this process where the platform allows it
def _wizard_launch_monitor(arguments):
    command = [str(argument) for argument in arguments]
    if platform.system() == "Windows":
        try:
            return subprocess.run(command, check=False).returncode
        except KeyboardInterrupt:
            return 0
    os.execv(command[0], command)
    return 0


# Runs the guided setup, holding every answer until the user saves
def run_setup_wizard(initial_riot_id=None, initial_region=None, config_file=None, env_file=None, input_func=None, getpass_func=None, interactive=None):
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else interactive
    if not terminal_is_interactive:
        print("The setup wizard needs an interactive terminal (TTY).")
        print("Run --setup from an interactive shell or use --generate-config and edit the files manually.")
        print(f"Guide: {QUICK_START_GUIDE_URL}")
        return 1

    try:
        config_path, env_path = _wizard_destinations(config_file, env_file)
    except ValueError as exc:
        print_recovery_error(exc, context="file.unwritable", detail=str(exc))
        return 1

    print(colorize("header", "Setup Wizard\n"))
    print("This asks a few questions and writes a ready-to-run configuration.")
    _wizard_print_default_guidance()
    print("Secrets go to the dotenv file. Non-secret settings go to the config file.")
    print()
    _wizard_print_setup_destinations(install_method(), config_path, env_path)

    baseline_values = {name: value for name, value in globals().items() if name in _config_allowed_names()}
    state = WizardSetupState(config_path, env_path, baseline_values)
    state.config_values["DOTENV_FILE"] = str(env_path)

    try:
        # Asked before anything else, so a config that has to be replaced is agreed to rather than discovered at Save
        config_existed = Path(config_path).exists()
        chosen_config = _wizard_choose_config_destination(config_path, input_func=input_func)
        if chosen_config is None:
            print("\n" + colorize("warning", "Setup cancelled. Destination files were not changed."))
            return 1
        state.config_path = chosen_config
        # A destination nothing was asked about printed nothing, so the separator would leave a blank gap
        if config_existed:
            print()
        _wizard_collect_target_section(state, initial_riot_id, initial_region, input_func=input_func)
        print()
        _wizard_collect_polling_section(state, input_func=input_func)
        print()
        _wizard_collect_auth_section(state, input_func=input_func, getpass_func=getpass_func)
        _wizard_confirm_target(state, input_func=input_func)
        print()
        _wizard_collect_email_section(state, input_func=input_func, getpass_func=getpass_func)
        print()
        _wizard_collect_webhook_section(state, input_func=input_func, getpass_func=getpass_func)
        print()
        _wizard_collect_output_section(state, input_func=input_func)
        if not _wizard_review_setup(state, input_func=input_func, getpass_func=getpass_func):
            print("\n" + colorize("warning", "Setup cancelled. Destination files were not changed."))
            return 1
    except (EOFError, KeyboardInterrupt):
        print(colorize("warning", "Setup cancelled. Destination files were not changed."))
        return 1
    except SecretConfigurationError as exc:
        # An existing dotenv file the questions could not read stops setup here rather than at the save step
        print_recovery_error(exc, context="file", detail=str(exc))
        return 1

    # Everything above only filled the state, so this is the first and only point anything reaches disk
    try:
        config_result = write_config_file(state.config_path, generate_config_with_current_values(state.config_values))
    except Exception as exc:
        print_recovery_error(exc, context="file", detail=f"Could not write the configuration to '{state.config_path}'")
        return 1
    dotenv_result = None
    if state.secret_updates:
        try:
            dotenv_result = update_dotenv_file(state.env_path, state.secret_updates)
        except SecretConfigurationError as exc:
            print_recovery_error(exc, context="file", detail=str(exc))
            return 1
        except Exception as exc:
            print_recovery_error(exc, context="file", detail=f"Could not write secrets to '{state.env_path}'")
            return 1

    print(colorize("header", "\nSaved files\n"))
    print(f"  Configuration: {config_result['path']}")
    if config_result["backup_path"]:
        print(f"  Backup:        {config_result['backup_path']}")
    if dotenv_result:
        print(f"  {'Secrets:':<15}{dotenv_result['path']}")

    doctor_offered = bool(state.riot_id and state.region)
    doctor_exit = None
    if doctor_offered:
        print()
    try:
        if doctor_offered and _wizard_ask_yes_no("Run doctor now? It writes no files and offers real delivery tests only with separate approval.", default=True, input_func=input_func):
            print()
            _wizard_apply_saved_values(state, env_path=state.env_path if dotenv_result else None)
            doctor_exit = run_doctor(riot_id=state.riot_id, region=state.region, config_path=str(state.config_path), env_path=str(state.env_path) if dotenv_result else None)
    except (EOFError, KeyboardInterrupt):
        # The files are already written, so an interrupt here only skips the optional check
        print(colorize("warning", "Setup is saved. Use the commands below when ready."))

    env_argument = str(state.env_path) if dotenv_result else ""
    # A persisted target is already in the config file, so the printed commands stay short
    target_arguments = [] if state.persist_target or not state.riot_id else [state.riot_id, state.region]
    print(colorize("header", "\nNext steps\n"))
    print_labelled_command("Check setup again:", render_command(["--doctor"] + target_arguments, config_path=str(state.config_path), env_path=env_argument))
    start_label = "After Doctor passes, start monitoring:" if doctor_exit not in (None, 0) else "Start monitoring:"
    print_labelled_command(start_label, render_command(target_arguments, config_path=str(state.config_path), env_path=env_argument))
    print(f"Guide: {colorize('link', QUICK_START_GUIDE_URL)}\n")

    try:
        # Only a doctor run that passed proves the saved setup can monitor, so the launch offer waits for it
        start_monitoring = bool(state.riot_id and doctor_exit == 0 and _wizard_ask_yes_no("Start monitoring now? Monitoring will continue until Ctrl+C.", default=True, input_func=input_func))
    except (EOFError, KeyboardInterrupt):
        # The files are already written, so an interrupt here only skips the optional launch
        print(colorize("warning", "Setup is saved. Start monitoring with the command above when ready."))
        return 0
    if start_monitoring:
        launch_riot_id = None if state.persist_target else state.riot_id
        launch_arguments = _wizard_local_command_args(riot_id=launch_riot_id, region=None if state.persist_target else state.region, config_path=state.config_path, env_path=state.env_path if dotenv_result else None)
        sys.stdout.flush()
        return _wizard_launch_monitor(launch_arguments)
    return 0


# Renders the --help examples: one heading per task, then a comment and the command it describes
def render_help_examples(groups, guide_url):
    blocks = []
    for title, entries in groups:
        block = [f"{title}:"]
        for comment, command in entries:
            if len(block) > 1:
                block.append("")
            block.extend(f"  # {line}" for line in comment.split("\n"))
            if command:
                block.append(f"  {command}")
        blocks.append("\n".join(block))
    return "Examples:\n\n" + "\n\n".join(blocks) + f"\n\nGuide: {guide_url}\n"


# Returns the --help epilog, listing the commands worth knowing rather than every command there is
def help_examples():
    prefix = render_command(include_paths=False)
    groups = (
        ("Getting started", (
            ("Guided setup, recommended for the first run", f"{prefix} --setup"),
            ("Or save the Riot API key through a hidden prompt", f"{prefix} --set-riot-api-key"),
            ("Check the setup before relying on it", f"{prefix} --doctor <riot_id> <region>"),
            ("Start monitoring", f"{prefix} <riot_id> <region>"),
        )),
        ("Notifications", (
            ("Email when the player starts or finishes a match", f"{prefix} <riot_id> <region> -s"),
            ("Send one test email", f"{prefix} --send-test-email"),
            ("Send one test webhook", f"{prefix} --send-test-webhook"),
        )),
        ("Match history", (
            ("List the 25 most recent matches and exit", f"{prefix} <riot_id> <region> -l -n 25"),
            ("List matches 20 through 50 and save them to CSV", f"{prefix} <riot_id> <region> -l -m 20 -n 50 -b matches.csv"),
            ("Append every reported match to a CSV file while monitoring", f"{prefix} <riot_id> <region> -b matches.csv"),
        )),
        ("Information and diagnostics", (
            ("Show every effective setting at startup", f"{prefix} <riot_id> <region> --verbose"),
            ("Trace what the tool is doing", f"{prefix} <riot_id> <region> --debug"),
        )),
    )
    return render_help_examples(groups, QUICK_START_GUIDE_URL)


# Prints the commands a first-time reader needs and offers the wizard, replacing the argument error a
# bare run used to end in. Returns the exit code, which is 0 only where the screen ended in a question
def print_welcome_screen(input_func=None, interactive=None, config_file=None, env_file=None):
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else bool(interactive)
    print(f"For <riot_id>, use a {RIOT_ID_FORMS}.")
    print(f"For <region>, use a {REGION_FORMS}.\n")
    print_labelled_command("Quickest start (already configured):", render_command(["<riot_id>", "<region>"], include_paths=False))
    # The suffix names the prompt printed below, so it only appears when that prompt does
    print_labelled_command("Easiest start (guided setup wizard):", render_command(["--setup"], include_paths=False), "   (or just answer Y below)" if terminal_is_interactive else "")
    print_labelled_command("Check setup before monitoring:", render_command(["--doctor", "<riot_id>", "<region>"], include_paths=False))
    print_labelled_command("Show recent matches and exit:", render_command(["-l", "<riot_id>", "<region>"], include_paths=False))
    print(f"Full options: {colorize('section', render_command(['--help'], include_paths=False))}")
    print(f"\nGuide:        {colorize('link', QUICK_START_GUIDE_URL)}\n")
    if terminal_is_interactive:
        try:
            start_setup = _wizard_ask_yes_no("Run the guided setup wizard now?", default=True, input_func=input_func)
        except (EOFError, KeyboardInterrupt):
            # This prompt sits outside the wizard, which handles its own interrupts
            print(colorize("warning", "Setup cancelled."))
            return 1
        if start_setup:
            print()
            return run_setup_wizard(config_file=config_file, env_file=env_file, input_func=input_func)
    # Without a terminal there was nothing to answer, so a bare invocation stays the usage error it was
    return 0 if terminal_is_interactive else 1


# Prints the command that starts monitoring with the files this run checked, so a report read on its own
# ends with the next action rather than leaving the reader to assemble the command
def print_doctor_next_steps(riot_id=None, region=None, riot_id_saved=False, region_saved=False, doctor_exit=0):
    print("\nNext steps\n")
    label = "After Doctor passes, start monitoring:" if doctor_exit else "Start monitoring:"
    print_labelled_command(label, render_command(command_target_arguments(riot_id, region, riot_id_saved, region_saved)))
    # No trailing blank line: the command printer already left one and the report must not end on two
    print(f"Guide: {QUICK_START_GUIDE_URL}")


# One startup summary setting, routed to the concise view, the verbose view or both. The log keeps the verbose view
StartupSummaryRow = namedtuple("StartupSummaryRow", ["label", "value", "concise", "full"])
StartupSummaryRow.__new__.__defaults__ = (False, True)

# Wide enough for the longest shared label plus its colon, which keeps the value column in the same place across tools
STARTUP_SUMMARY_LABEL_WIDTH = 30


# Returns whether the full startup summary should be shown, which debug mode also implies
def full_startup_summary_enabled():
    return bool(VERBOSE_MODE or DEBUG_MODE)


# Renders the alert categories one channel would deliver, or reports that the channel is off
def startup_notification_state(categories):
    return "On (" + ", ".join(categories) + ")" if categories else "Off"


# Formats one summary row with an aligned value column, wrapping only the rollup that grows long
def format_startup_summary_row(row):
    prefix = f"* {(row.label + ':'):<{STARTUP_SUMMARY_LABEL_WIDTH}}"
    if row.label in ("Notifications (email)", "Notifications (webhook)"):
        return textwrap.fill(str(row.value), width=100, initial_indent=prefix, subsequent_indent=" " * len(prefix), break_long_words=False, break_on_hyphens=False) + "\n"
    return f"{prefix}{row.value}\n"


# Prints the summary, showing the concise rows unless the full view was asked for. The log file always keeps
# the complete set, so a bug report made from a log carries every effective setting whatever the terminal showed
def emit_startup_summary(rows, show_full=False, stream=None):
    destination = sys.stdout if stream is None else stream
    # A stream that does not split its output has no log file to hold the full view, so those writes go nowhere
    write_log = getattr(destination, "log_only", lambda line: None)
    write_terminal = getattr(destination, "terminal_only", None)
    if write_terminal is None:
        write_terminal = destination.write
    for row in rows:
        line = format_startup_summary_row(row)
        if row.full:
            write_log(line)
        if row.full if show_full else row.concise:
            write_terminal(line)
    write_log("\n")
    write_terminal("\n")
    destination.flush()


# Builds every startup summary row, deciding per row whether it belongs in the concise view, the full view and the log
def build_startup_summary(target=None, config_path=None, env_path=None, log_path=None):
    from_dotenv, from_environment, from_config, from_command_line = group_secrets_by_source(env_path)
    logging_enabled = bool(log_path) and not DISABLE_LOGGING
    output_state = str(log_path) if logging_enabled else "Terminal only (logging disabled)"
    return [
        StartupSummaryRow("Target", str(target) if target else "None", concise=True),
        StartupSummaryRow("Polling intervals", f"[NOT in game: {display_time(LOL_CHECK_INTERVAL)}] [in game: {display_time(LOL_ACTIVE_CHECK_INTERVAL)}]", concise=True),
        StartupSummaryRow("Notifications (email)", startup_notification_state(email_notification_categories()), concise=True),
        StartupSummaryRow("Notifications (webhook)", startup_notification_state(_startup_webhook_notification_categories()), concise=True),
        StartupSummaryRow("Output", output_state, concise=True, full=False),
        StartupSummaryRow("Output logging", str(log_path) if logging_enabled else "Disabled"),
        StartupSummaryRow("Config", str(config_path) if config_path else ("Discovery disabled" if CONFIG_DISCOVERY_DISABLED else "None"), concise=True),
        StartupSummaryRow("Dotenv", str(env_path) if env_path else "None", concise=True),
        # A tracked feature earns a concise row only while it is actually switched on
        StartupSummaryRow("Forbidden matches", str(INCLUDE_FORBIDDEN_MATCHES), concise=bool(INCLUDE_FORBIDDEN_MATCHES)),
        StartupSummaryRow("Liveness output", display_time(LIVENESS_CHECK_INTERVAL) if LIVENESS_CHECK_INTERVAL else "Disabled", concise=bool(LIVENESS_CHECK_INTERVAL)),
        StartupSummaryRow("CSV output", CSV_FILE or "Disabled", concise=bool(CSV_FILE)),
        StartupSummaryRow("Terminal truncation", f"{TRUNCATE_CHARS} chars" if TRUNCATE_CHARS else "Disabled", concise=bool(TRUNCATE_CHARS)),
        StartupSummaryRow("Install method", install_method_display_name()),
        StartupSummaryRow("Secrets from dotenv", ", ".join(sorted(from_dotenv)) if from_dotenv else "None"),
        StartupSummaryRow("Secrets from environment", ", ".join(sorted(from_environment)) if from_environment else "None"),
        StartupSummaryRow("Secrets from config file", ", ".join(sorted(from_config)) if from_config else "None"),
        StartupSummaryRow("Secrets from command line", ", ".join(sorted(from_command_line)) if from_command_line else "None"),
        # Concise while it is off, since a run that stopped checking certificates is worth saying without a flag
        StartupSummaryRow("TLS verification", "On" if VERIFY_SSL else "Off, server certificates are not checked", concise=not VERIFY_SSL),
        StartupSummaryRow("ASCII log separators", f"{ascii_log_separators_enabled()} (mode: {ASCII_LOG_SEPARATORS})"),
        # The resolved state, not the setting: colour also switches itself off when the output is not a terminal
        StartupSummaryRow("Coloured output", f"{COLOR_ENABLED} (setting: {COLORED_OUTPUT})"),
        StartupSummaryRow("Verbose mode", str(VERBOSE_MODE), concise=bool(VERBOSE_MODE)),
        StartupSummaryRow("Debug mode", str(DEBUG_MODE), concise=bool(DEBUG_MODE)),
        # Points at the two modes for a reader who does not know they exist, so the full view drops it
        StartupSummaryRow("More details", "use --verbose or --debug", concise=True, full=False),
    ]


# Names one argument the way the user would have typed it, so a refused combination points at a real option
def argument_display_name(parser, dest, argv=None):
    typed = set(sys.argv[1:] if argv is None else argv)
    # argparse exposes no public listing of its arguments, so the actions it holds are read directly
    for action in getattr(parser, "_actions", ()):
        if action.dest != dest:
            continue
        if not action.option_strings:
            return str(action.metavar or dest.upper())
        return next((option for option in action.option_strings if option in typed), action.option_strings[0])
    return f"--{dest.replace('_', '-')}"


# Rejects unrelated options when a hidden secret-entry action is selected
def validate_secret_action_args(args, parser, action_dest, action_flag, permitted_extra=()):
    permitted = {action_dest, "env_file", "no_color", *permitted_extra}
    conflicts = []
    for name, value in vars(args).items():
        if name in permitted or value is None or value is False:
            continue
        conflicts.append(argument_display_name(parser, name))
    if conflicts:
        parser.error(f"{action_flag} cannot be combined with " + ", ".join(conflicts))


def main():
    global CLI_CONFIG_PATH, CONFIG_DISCOVERY_DISABLED, COMMAND_LINE_SECRET_KEYS, EXPORTED_SECRET_KEYS, DOTENV_FILE, LIVENESS_REMINDER_SECONDS, RIOT_API_KEY, CSV_FILE, DISABLE_LOGGING, LOL_LOGFILE, STATUS_NOTIFICATION, ERROR_NOTIFICATION, LOL_CHECK_INTERVAL, LOL_ACTIVE_CHECK_INTERVAL, SMTP_PASSWORD, stdout_bck, REGION_TO_CONTINENT, INCLUDE_FORBIDDEN_MATCHES, DEBUG_MODE, COLORED_OUTPUT, TRUNCATE_CHARS, WEBHOOK_ENABLED

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

    apply_early_output_config()

    # Read straight from sys.argv because argparse has not run yet, and the banner is printed before it does
    if "--no-color" in sys.argv:
        COLORED_OUTPUT = False
    if "--debug" in sys.argv:
        DEBUG_MODE = True

    init_color_output(stdout_bck)
    # Everything printed before the logging policy is known still goes through one colour pass
    sys.stdout = ColorStream(stdout_bck)

    if CLEAR_SCREEN and DEBUG_MODE:
        debug_print("Terminal screen clear skipped because debug mode is active")
    clear_screen(CLEAR_SCREEN and not keep_terminal_history() and not DEBUG_MODE)

    print_startup_banner()

    parser = argparse.ArgumentParser(
        prog="lol_monitor",
        description=(f"Monitor a League of Legends user's playing status and send customizable email alerts [ {PROJECT_URL}/ ]"),
        epilog=help_examples(),
        formatter_class=argparse.RawTextHelpFormatter,
        **argparse_color_kwargs()
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
        "--setup",
        dest="setup",
        action="store_true",
        help="Run the guided setup and write a ready-to-run configuration"
    )
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
        help="Let --generate-config replace an existing file, after a timestamped backup",
    )
    conf.add_argument(
        "--env-file",
        dest="env_file",
        metavar="PATH",
        help="Path to optional dotenv file (auto-search if not set, disable with 'none')",
    )
    conf.add_argument(
        "--set-riot-api-key",
        dest="set_riot_api_key",
        action="store_true",
        help="Enter the Riot API key privately, check it with Riot and save it to the dotenv file"
    )
    conf.add_argument(
        "--set-smtp-password",
        dest="set_smtp_password",
        action="store_true",
        help="Enter the SMTP password privately, check it against the mail server and save it to the dotenv file"
    )
    conf.add_argument(
        "--set-webhook-url",
        dest="set_webhook_url",
        action="store_true",
        help="Save a Discord or ntfy webhook URL through a hidden prompt"
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

    # Email notifications
    notify = parser.add_argument_group("Email notifications")
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

    # Webhook notifications
    webhook_notify = parser.add_argument_group("Webhook notifications")
    webhook_toggle = webhook_notify.add_mutually_exclusive_group()
    webhook_toggle.add_argument(
        "--webhook",
        dest="webhook_enabled",
        action="store_true",
        default=None,
        help="Enable the configured webhook alerts"
    )
    webhook_toggle.add_argument(
        "--no-webhook",
        dest="webhook_enabled",
        action="store_false",
        default=None,
        help="Disable the configured webhook alerts"
    )
    webhook_notify.add_argument(
        "--webhook-url",
        dest="webhook_url",
        metavar="URL",
        type=str,
        help="Use one Discord webhook or ntfy topic URL for this run (may remain in shell history)"
    )
    webhook_notify.add_argument(
        "--webhook-provider",
        dest="webhook_provider",
        choices=("discord", "ntfy"),
        help="Webhook request format for this run (default: configured provider)"
    )
    webhook_notify.add_argument(
        "--webhook-status",
        dest="webhook_status",
        action="store_true",
        default=None,
        help="Send a webhook alert when the user's playing status changes"
    )
    webhook_error_toggle = webhook_notify.add_mutually_exclusive_group()
    webhook_error_toggle.add_argument(
        "--webhook-errors",
        dest="webhook_errors",
        action="store_true",
        default=None,
        help="Send webhook alerts when monitoring has a problem"
    )
    webhook_error_toggle.add_argument(
        "--no-webhook-error-notify",
        dest="webhook_errors",
        action="store_false",
        default=None,
        help="Disable webhook alerts when monitoring has a problem"
    )
    webhook_notify.add_argument(
        "--send-test-webhook",
        dest="send_test_webhook",
        action="store_true",
        help="Send one test webhook without starting monitoring"
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

    # User information & listing
    listing = parser.add_argument_group("User information & listing")

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
    opts.add_argument(
        "--no-color",
        dest="no_color",
        action="store_true",
        default=None,
        help="Disable coloured output in the terminal"
    )
    opts.add_argument(
        "--truncate",
        dest="truncate",
        metavar="N",
        type=int,
        help="Max characters per screen line (not log), use 999 to auto-detect terminal width, ignored if -d is set"
    )

    args = parser.parse_args()

    # Applied here so config-load failures and startup checks can already print diagnostics
    apply_diagnostic_cli_flags(args)

    selected_secret_actions = [flag for flag, selected in zip(SECRET_ACTION_FLAGS, (args.set_riot_api_key, args.set_smtp_password, args.set_webhook_url), strict=True) if selected]
    if len(selected_secret_actions) > 1:
        parser.error(f"{selected_secret_actions[0]} cannot be combined with {selected_secret_actions[1]}")

    if args.send_test_email and args.send_test_webhook:
        parser.error("--send-test-email cannot be combined with --send-test-webhook")

    if args.set_riot_api_key:
        validate_secret_action_args(args, parser, "set_riot_api_key", "--set-riot-api-key")
        try:
            run_set_riot_api_key(env_file=args.env_file)
        except (SecretConfigurationError, RecoveryError) as exc:
            print_recovery_error(exc, context="set_riot_api_key")
            sys.exit(1)
        sys.exit(0)

    if args.set_webhook_url:
        validate_secret_action_args(args, parser, "set_webhook_url", "--set-webhook-url")
        try:
            run_set_webhook_url(env_file=args.env_file)
        except (SecretConfigurationError, RecoveryError) as exc:
            print_recovery_error(exc, context="set_webhook_url")
            sys.exit(1)
        sys.exit(0)

    CONFIG_DISCOVERY_DISABLED = args.config_file is not None and str(args.config_file).casefold() == "none"
    if CONFIG_DISCOVERY_DISABLED:
        CLI_CONFIG_PATH = None
    elif args.config_file:
        CLI_CONFIG_PATH = os.path.expanduser(args.config_file)

    cfg_path = None if CONFIG_DISCOVERY_DISABLED else find_config_file(CLI_CONFIG_PATH)

    if not cfg_path and CLI_CONFIG_PATH and not args.setup:
        # Setup is allowed to name a file that does not exist yet, since creating it is the point
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

    # Evaluated after the config file is read, so a saved target starts monitoring instead of being welcomed
    if len(sys.argv) == 1 and not (args.riot_id and args.region):
        sys.exit(print_welcome_screen(config_file=args.config_file, env_file=args.env_file))

    # Recorded before the dotenv file is read, so an exported value stays ahead of the same name in that file
    # An empty export is a shell-profile leftover rather than a value, so it is dropped before the dotenv load,
    # which would otherwise keep it and leave the file's value unused
    for secret in SECRET_KEYS:
        if os.environ.get(secret) == "":
            os.environ.pop(secret)
    EXPORTED_SECRET_KEYS = frozenset(secret for secret in SECRET_KEYS if os.getenv(secret))

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
                    # A command that is about to write this file is not warned that it is missing
                    if not command_writes_dotenv(sys.argv[1:]):
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
                alternative = f"Then re-run: {retry_command}" if retry_command else "Or export the secrets as environment variables"
                print_recovery_advice(missing_dependency_advice("python-dotenv", f"The dotenv file '{env_path}' was not loaded", alternative), label="Warning")

    # Exported secrets apply on their own, so a dotenv file is an alternative to the environment rather than a precondition
    load_secrets_from_environment()

    apply_tls_verification_setting()

    if args.riot_api_key:
        RIOT_API_KEY = args.riot_api_key

    # Assigned once from the arguments rather than accumulated, so a second run in one process starts clean
    COMMAND_LINE_SECRET_KEYS = frozenset(name for name, supplied in (("RIOT_API_KEY", args.riot_api_key), ) if supplied)

    # Traced here rather than at each layer, so the line reports the value that survived every later override
    resolved_secrets = secret_source_labels(env_path)
    for secret, source in resolved_secrets.items():
        debug_print("Secret resolution", name=secret, source=source, **secret_fields(globals().get(secret), secret))
    if not resolved_secrets:
        debug_print("No private settings were resolved from config, dotenv, environment or the command line")

    # Applied before the report so every row it prints describes the run this command line asked for
    if args.check_interval:
        LOL_CHECK_INTERVAL = args.check_interval

    if args.active_interval:
        LOL_ACTIVE_CHECK_INTERVAL = args.active_interval

    if args.include_forbidden_matches is True:
        INCLUDE_FORBIDDEN_MATCHES = True

    if args.notify_status is True:
        STATUS_NOTIFICATION = True

    if args.notify_errors is False:
        ERROR_NOTIFICATION = False

    apply_webhook_cli_overrides(args, parser)

    # Timed rather than counted, because a failing run retries on a different interval than a healthy one, so a
    # cadence derived from the polling interval drifts by however much the two differ. Derived after the
    # configuration file is read, so a saved LIVENESS_CHECK_INTERVAL reaches the loop
    LIVENESS_REMINDER_SECONDS = LIVENESS_CHECK_INTERVAL if LIVENESS_CHECK_INTERVAL > 0 else 0

    if args.disable_logging is True:
        DISABLE_LOGGING = True

    TRUNCATE_CHARS = resolve_truncate_chars(args.truncate, TRUNCATE_CHARS, DISABLE_LOGGING)

    if args.csv_file:
        CSV_FILE = os.path.expanduser(args.csv_file)
    else:
        if CSV_FILE:
            CSV_FILE = os.path.expanduser(CSV_FILE)

    # A target is optional only for the modes that legitimately finish without one. Checked after the dotenv
    # file is resolved, so the command this prints carries the same files the run was given
    if (not args.riot_id or not args.region) and not (args.setup or args.doctor or args.send_test_email or args.send_test_webhook or args.set_smtp_password):
        missing = "No Riot ID was provided" if not args.riot_id else "No region was provided"
        print_recovery_error(context="target.missing", detail=missing)
        sys.exit(1)

    if args.set_smtp_password:
        # Runs after the config file so the mail server it signs in to is the one monitoring would use
        validate_secret_action_args(args, parser, "set_smtp_password", "--set-smtp-password", permitted_extra=("config_file",))
        try:
            run_set_smtp_password(env_file=args.env_file or env_path)
        except (SecretConfigurationError, RecoveryError) as exc:
            print_recovery_error(exc, context="set_smtp_password")
            sys.exit(1)
        sys.exit(0)

    if args.setup:
        # Ahead of every connectivity check, so an offline machine can still be set up
        sys.exit(run_setup_wizard(initial_riot_id=args.riot_id, initial_region=args.region, config_file=args.config_file, env_file=args.env_file))

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
        missing = mail_sign_in_settings_missing()
        if missing:
            print_recovery_error(context="set_smtp_password", detail=mail_settings_incomplete_message(missing))
            sys.exit(1)
        print("* Sending test email notification ...\n")
        debug_print("Test email", sender=SENDER_EMAIL, recipient=RECEIVER_EMAIL)
        if send_email(TEST_EMAIL_SUBJECT, TEST_EMAIL_BODY, "", SMTP_SSL, smtp_timeout=5) == 0:
            print("* Email sent successfully !")
        else:
            sys.exit(1)
        sys.exit(0)

    if args.send_test_webhook:
        if not validate_webhook_url():
            print_recovery_error(context="set_webhook_url", detail="No webhook destination is configured")
            sys.exit(1)
        print("* Sending test webhook notification ...\n")
        debug_print("Test webhook", channel=normalized_webhook_provider() or "an unset provider", host=webhook_destination_host())
        if send_webhook(TEST_WEBHOOK_TITLE, TEST_WEBHOOK_BODY, "status", force=True) == 0:
            print("* Webhook sent successfully !")
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
                        print_recovery_error(context="target", detail=f"Riot has no account for {args.riot_id}")
                    else:
                        print_recovery_error(RecoveryError(no_match_history_advice()))
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
            print_recovery_error(RecoveryError(make_recovery_advice("config.invalid", f"The lowest match number ({matches_min}) is above the highest ({matches_num})", recovery_fix_with_guide("Raise -n / --recent-matches-count or lower -m / --min-recent-matches", USAGE_GUIDE_URL), False)))
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

    if WEBHOOK_ENABLED and not validate_webhook_url():
        verbose_print("Webhook notifications are off because WEBHOOK_URL is not a complete HTTPS link")
        WEBHOOK_ENABLED = False

    emit_startup_summary(build_startup_summary(args.riot_id, cfg_path, env_path, FINAL_LOG_PATH), show_full=full_startup_summary_enabled())

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
