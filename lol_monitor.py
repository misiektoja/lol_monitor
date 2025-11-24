#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v1.8

Tool implementing real-time tracking of LoL (League of Legends) players activities:
https://github.com/misiektoja/lol_monitor/

Python pip3 requirements:

pulsefire
requests
python-dateutil
python-dotenv (optional)
"""

VERSION = "1.8"

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
CSV_FILE = ""
DOTENV_FILE = ""
LOL_LOGFILE = ""
DISABLE_LOGGING = False
HORIZONTAL_LINE = 0
CLEAR_SCREEN = False
LOL_ACTIVE_CHECK_SIGNAL_VALUE = 0
REGION_TO_CONTINENT = {}

exec(CONFIG_BLOCK, globals())

# Default name for the optional config file
DEFAULT_CONFIG_FILENAME = "lol_monitor.conf"

# List of secret keys to load from env/config
SECRET_KEYS = ("RIOT_API_KEY", "SMTP_PASSWORD")

LIVENESS_CHECK_COUNTER = LIVENESS_CHECK_INTERVAL / LOL_CHECK_INTERVAL

stdout_bck = None
csvfieldnames = ['Match Start', 'Match Stop', 'Duration', 'Game Mode', 'Victory', 'Kills', 'Deaths', 'Assists', 'Champion', 'Level', 'Role', 'Lane', 'Team 1', 'Team 2']

CLI_CONFIG_PATH = None

# to solve the issue: 'SyntaxError: f-string expression part cannot include a backslash'
nl_ch = "\n"


import sys

if sys.version_info < (3, 12):
    print("* Error: Python version 3.12 or higher required !")
    sys.exit(1)

import time
import string
import os
from datetime import datetime
from dateutil import relativedelta
import calendar
import requests as req
import signal
import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import argparse
import csv
import platform
import re
import ipaddress
import asyncio
import html
try:
    from pulsefire.clients import RiotAPIClient
except ModuleNotFoundError:
    raise SystemExit("Error: Couldn't find the Pulsefire library !\n\nTo install it, run:\n    pip3 install pulsefire\n\nOnce installed, re-run this tool. For more help, visit:\nhttps://pulsefire.iann838.com/usage/basic/installation/")
import shutil
from pathlib import Path
from typing import Optional, Any, Dict, List, Tuple


# Logger class to output messages to stdout and log file
class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.logfile = open(filename, "a", buffering=1, encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.logfile.write(message)
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
def check_internet(url=CHECK_INTERNET_URL, timeout=CHECK_INTERNET_TIMEOUT):
    try:
        _ = req.get(url, timeout=timeout)
        return True
    except req.RequestException as e:
        print(f"* No connectivity, please check your network:\n\n{e}")
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

    if not SMTP_USER or not isinstance(SMTP_USER, str) or SMTP_USER == "your_smtp_user" or not SMTP_PASSWORD or not isinstance(SMTP_PASSWORD, str) or SMTP_PASSWORD == "your_smtp_password":
        print("Error sending email - SMTP settings are incorrect (check SMTP_USER & SMTP_PASSWORD variables)")
        return 1

    if not subject or not isinstance(subject, str):
        print("Error sending email - SMTP settings are incorrect (subject is not a string or is empty)")
        return 1

    if not body and not body_html:
        print("Error sending email - SMTP settings are incorrect (body and body_html cannot be empty at the same time)")
        return 1

    try:
        if use_ssl:
            ssl_context = ssl.create_default_context()
            smtpObj = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=smtp_timeout)
            smtpObj.starttls(context=ssl_context)
        else:
            smtpObj = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=smtp_timeout)
        smtpObj.login(SMTP_USER, SMTP_PASSWORD)
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
    except Exception as e:
        print(f"Error sending email: {e}")
        return 1
    return 0


# Initializes the CSV file
def init_csv_file(csv_file_name):
    try:
        if not os.path.isfile(csv_file_name) or os.path.getsize(csv_file_name) == 0:
            with open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
                writer.writeheader()
    except Exception as e:
        raise RuntimeError(f"Could not initialize CSV file '{csv_file_name}': {e}")


# Writes CSV entry
def write_csv_entry(csv_file_name, start_date_ts, stop_date_ts, duration_ts, game_mode, victory, kills, deaths, assists, champion, level, role, lane, team1, team2):
    try:

        with open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8") as csv_file:
            csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
            csvwriter.writerow({'Match Start': start_date_ts, 'Match Stop': stop_date_ts, 'Duration': duration_ts, 'Game Mode': game_mode, 'Victory': victory, 'Kills': kills, 'Deaths': deaths, 'Assists': assists, 'Champion': champion, 'Level': level, 'Role': role, 'Lane': lane, 'Team 1': team1, 'Team 2': team2})

    except Exception as e:
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
            from dotenv import load_dotenv, find_dotenv
            if DOTENV_FILE:
                env_path = DOTENV_FILE
            else:
                env_path = find_dotenv()
            if env_path:
                load_dotenv(env_path, override=True)
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
                print(f"* Reloaded {secret} from {env_path}")

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
    if not game_type:
        return "Unknown"
    return game_type_mapping.get(game_type, game_type.replace("_", " ").title())


# Returns a short patch label (major.minor) and full build when available
def format_game_version_label(game_version: Optional[str]) -> str:
    if not game_version:
        return "Unknown"

    version = str(game_version).strip()
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
def get_participant_display_name(participant: dict) -> str:
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


# Returns Riot game name & tag line for specified Riot ID
def get_user_riot_name_tag(riotid: str):

    try:
        riotid_name = riotid.split('#', 1)[0]
        riotid_tag = riotid.split('#', 1)[1]
    except IndexError:
        print("* Error while extracting name and tagline from Riot ID ! It needs to be in name#tag format.")
        return "", ""

    return riotid_name, riotid_tag


# Converts Riot ID to PUUID
async def get_user_puuid(riotid: str, region: str) -> Optional[str]:

    riotid_name, riotid_tag = get_user_riot_name_tag(riotid)

    async with RiotAPIClient(default_headers={"X-Riot-Token": RIOT_API_KEY}) as client:
        try:
            account = await client.get_account_v1_by_riot_id(region=REGION_TO_CONTINENT.get(region, "europe"), game_name=riotid_name, tag_line=riotid_tag)
            puuid = account["puuid"]
        except Exception as e:
            print(f"* Error while converting Riot ID to PUUID: {e}")
            if 'Unauthorized' in str(e):
                print("* API key might not be valid anymore!")
            puuid = None

    return puuid


# Gets summoner details
async def get_summoner_details(puuid: str, region: str):

    summoner_info = {
        "summoner_level": "N/A",
        "revision_date": "N/A"
    }

    async with RiotAPIClient(default_headers={"X-Riot-Token": RIOT_API_KEY}) as client:
        try:
            summoner = await client.get_lol_summoner_v4_by_puuid(region=region, puuid=puuid)

            summoner_info["summoner_level"] = str(summoner.get("summonerLevel", "N/A"))

            # revisionDate is in milliseconds
            revision_date_ts = summoner.get("revisionDate", 0)
            if revision_date_ts:
                revision_date = datetime.fromtimestamp(revision_date_ts / 1000)
                summoner_info["revision_date"] = get_date_from_ts(revision_date)

        except Exception as e:
            print(f"* Error while getting summoner details: {e}")

    return summoner_info


# Gets ranked information
async def get_ranked_info(puuid: str, region: str):
    ranked_info = {
        "solo_duo": {"tier": "N/A", "rank": "N/A", "lp": "N/A", "wins": 0, "losses": 0},
        "flex": {"tier": "N/A", "rank": "N/A", "lp": "N/A", "wins": 0, "losses": 0}
    }

    if not puuid or puuid == "N/A":
        return ranked_info

    async with RiotAPIClient(default_headers={"X-Riot-Token": RIOT_API_KEY}) as client:
        try:
            league_entries = await client.get_lol_league_v4_entries_by_puuid(region=region, puuid=puuid)

            if not league_entries:
                return ranked_info

            for entry in league_entries:
                queue_type = entry.get("queueType", "")
                tier = entry.get("tier", "UNRANKED")
                rank = entry.get("rank", "")
                lp = entry.get("leaguePoints", 0)
                wins = entry.get("wins", 0)
                losses = entry.get("losses", 0)

                if queue_type == "RANKED_SOLO_5x5":
                    ranked_info["solo_duo"] = {
                        "tier": tier,
                        "rank": rank,
                        "lp": str(lp),
                        "wins": wins,
                        "losses": losses
                    }
                elif queue_type == "RANKED_FLEX_SR":
                    ranked_info["flex"] = {
                        "tier": tier,
                        "rank": rank,
                        "lp": str(lp),
                        "wins": wins,
                        "losses": losses
                    }
        except Exception as e:
            # Player might not be ranked, this is not an error
            pass

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
            versions_response = req.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=5)
            if versions_response.status_code == 200:
                versions = versions_response.json()
                latest_version = versions[0]

                # Get champion data
                champions_url = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/en_US/champion.json"
                champions_response = req.get(champions_url, timeout=5)
                if champions_response.status_code == 200:
                    champions_data = champions_response.json().get("data", {})
                    for champion_name, champion_info in champions_data.items():
                        champ_id = int(champion_info.get("key", 0))
                        if champ_id:
                            _champion_id_to_name_cache[champ_id] = champion_name
        except Exception:
            # If Data Dragon fails, this will return None
            pass

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

    async with RiotAPIClient(default_headers={"X-Riot-Token": RIOT_API_KEY}) as client:
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
        except Exception as e:
            # Champion mastery might not be available, this is not an error
            pass

    return mastery_info


# Checks if the player is currently in game
async def is_user_in_match(puuid: str, region: str):

    async with RiotAPIClient(default_headers={"X-Riot-Token": RIOT_API_KEY}) as client:

        try:
            current_match = await client.get_lol_spectator_v5_active_game_by_summoner(region=region, puuid=puuid)
            if current_match:
                return True
        except Exception:
            return False


# Prints details of the current player's match (user is in game)
async def print_current_match(puuid: str, riotid_name: str, region: str, last_match_start_ts: int, last_match_stop_ts: int, status_notification_flag: bool):

    async with RiotAPIClient(default_headers={"X-Riot-Token": RIOT_API_KEY}) as client:

        try:
            current_match = await client.get_lol_spectator_v5_active_game_by_summoner(region=region, puuid=puuid)
        except Exception:
            current_match = False

        if current_match:

            match_id = current_match.get("gameId", 0)
            match_start_ts = int((current_match.get("gameStartTime", 0)) / 1000)
            match_duration = current_match.get("gameLength", 0)

            gamemode = current_match.get("gameMode")
            queue_id = current_match.get("gameQueueConfigId")
            map_id = current_match.get("mapId")
            game_type_raw = current_match.get("gameType")
            game_type = humanize_game_type(game_type_raw)
            game_version_raw = current_match.get("gameVersion")
            game_version = format_game_version_label(game_version_raw)

            if game_modes_mapping.get(gamemode):
                gamemode = game_modes_mapping.get(gamemode)

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
                    u_riotid_name = u_riotid.split('#', 1)[0]
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

    try:
        async with RiotAPIClient(default_headers={'X-Riot-Token': RIOT_API_KEY}) as client:
            # If count <= 100, make a single request
            if count <= MAX_MATCHES_PER_REQUEST:
                matches = await client.get_lol_match_v5_match_ids_by_puuid(
                    region=REGION_TO_CONTINENT.get(region, 'europe'),
                    puuid=puuid,
                    queries={'start': start, 'count': count}
                )
                return matches if matches else []

            # For counts > 100, paginate with multiple requests
            current_start = start
            remaining = count

            while remaining > 0:
                # Request up to MAX_MATCHES_PER_REQUEST matches per call
                request_count = min(remaining, MAX_MATCHES_PER_REQUEST)

                matches = await client.get_lol_match_v5_match_ids_by_puuid(
                    region=REGION_TO_CONTINENT.get(region, 'europe'),
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

            return all_matches[:count]  # Return exactly the requested count (or less if not available)

    except Exception as e:
        print(f"* Error: Cannot fetch latest match IDs: {e}")
        print_cur_ts("Timestamp:\t\t\t")
        return []


# Fetches all available match IDs to determine total count
async def get_total_match_count(puuid: str, region: str) -> int:
    MAX_MATCHES_PER_REQUEST = 100
    all_matches = []
    start = 0

    try:
        async with RiotAPIClient(default_headers={'X-Riot-Token': RIOT_API_KEY}) as client:
            while True:
                matches = await client.get_lol_match_v5_match_ids_by_puuid(
                    region=REGION_TO_CONTINENT.get(region, 'europe'),
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

            return len(all_matches)

    except Exception as e:
        print(f"* Error: Cannot determine total match count: {e}")
        return 0


# Processes and prints details for a single match id, handling forbidden matches
async def process_and_print_single_match(match_id: str, puuid: str, riotid_name: str, region: str, status_notification_flag: bool, csv_file_name: Optional[str], cached_match_data: Optional[Any] = None) -> tuple[int, int]:

    # Use cached match data if provided, otherwise fetch it
    if cached_match_data:
        match = cached_match_data
    else:
        async with RiotAPIClient(default_headers={"X-Riot-Token": RIOT_API_KEY}) as client:
            try:
                match = await client.get_lol_match_v5_match(region=REGION_TO_CONTINENT.get(region, 'europe'), id=match_id)
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
                                f"Match ID: {html.escape(str(match_id))}<br>"
                                f"{get_cur_ts('<br>Timestamp: ')}"
                                f"</body></html>"
                            )
                            print(f"\nSending email notification to {RECEIVER_EMAIL}")
                            send_email(m_subject, m_body, m_body_html, SMTP_SSL)
                    return 0, 0
                else:
                    print(f"* An unexpected error occurred while processing match {match_id}: {e}")
                    return 0, 0

    try:
        match_info = match.get("info", {})
        match_metadata = match.get("metadata", {})

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

    async with RiotAPIClient(default_headers={"X-Riot-Token": RIOT_API_KEY}) as client:
        # Process in batches
        for batch_start in range(0, len(all_fetched_ids), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(all_fetched_ids))
            batch_ids = all_fetched_ids[batch_start:batch_end]

            # Fetch and process this batch
            for match_id in batch_ids:
                try:
                    # Fetch match details
                    match = await client.get_lol_match_v5_match(region=REGION_TO_CONTINENT.get(region, 'europe'), id=match_id)

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
        print(f"* Error: {e}")

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
    async with RiotAPIClient(default_headers={"X-Riot-Token": RIOT_API_KEY}) as client:
        try:
            current_match = await client.get_lol_spectator_v5_active_game_by_summoner(region=region, puuid=puuid)
        except Exception:
            return {}

    if not current_match:
        return {}

    gamemode_raw = current_match.get("gameMode")
    gamemode = game_modes_mapping.get(gamemode_raw, gamemode_raw)

    start_ts = int((current_match.get("gameStartTime", 0)) / 1000)
    if start_ts < 1000000000:
        start_ts = int(time.time())

    participants = []
    for p in current_match.get("participants", []):
        riot_id = p.get("riotId")
        if riot_id:
            riotid_name = riot_id.split("#", 1)[0]
        else:
            riotid_name = p.get("riotIdGameName") or p.get("summonerName") or "Unknown Player"

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
    summoner_level = "N/A"
    started_announced = False

    try:
        if csv_file_name:
            init_csv_file(csv_file_name)
    except Exception as e:
        print(f"* Error: {e}")

    puuid = await get_user_puuid(riotid, region)

    if not puuid:
        sys.exit(2)

    riotid_name, riotid_tag = get_user_riot_name_tag(riotid)

    summoner_info = {}
    ranked_info = {}
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
        ranked_info = {"solo_duo": {"tier": "N/A", "rank": "N/A", "lp": "N/A"}, "flex": {"tier": "N/A", "rank": "N/A", "lp": "N/A"}}

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

    while True:

        try:

            processed_new_match_in_this_cycle = False

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
                            is_custom = (game_type == "CUSTOM_GAME" or
                                       (mode_raw and mode_raw not in game_modes_mapping))

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

            if LIVENESS_CHECK_COUNTER and alive_counter >= LIVENESS_CHECK_COUNTER:
                print_cur_ts("Liveness check, timestamp:\t")
                alive_counter = 0

            if ingame or (game_finished_ts and (int(time.time()) - game_finished_ts) <= LOL_CHECK_INTERVAL):
                time.sleep(LOL_ACTIVE_CHECK_INTERVAL)
            else:
                time.sleep(LOL_CHECK_INTERVAL)

        except Exception as e:
            print(f"* Error, retrying in {display_time(LOL_CHECK_INTERVAL)}: {e}")
            if 'Unauthorized' in str(e):
                print("* API key might not be valid anymore!")
                if ERROR_NOTIFICATION and not email_sent:
                    m_subject = f"lol_monitor: API key error! (user: {riotid_name})"
                    m_body = f"API key might not be valid anymore or new patch deployed: {e}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                    m_body_html = (
                        f"<html><head></head><body>"
                        f"API key might not be valid anymore or new patch deployed: <b>{html.escape(str(e))}</b>"
                        f"{get_cur_ts('<br><br>Timestamp: ')}"
                        f"</body></html>"
                    )
                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                    send_email(m_subject, m_body, m_body_html, SMTP_SSL)
                    email_sent = True
            print_cur_ts("Timestamp:\t\t\t")
            time.sleep(LOL_CHECK_INTERVAL)
            continue


def main():
    global CLI_CONFIG_PATH, DOTENV_FILE, LIVENESS_CHECK_COUNTER, RIOT_API_KEY, CSV_FILE, DISABLE_LOGGING, LOL_LOGFILE, STATUS_NOTIFICATION, ERROR_NOTIFICATION, LOL_CHECK_INTERVAL, LOL_ACTIVE_CHECK_INTERVAL, SMTP_PASSWORD, stdout_bck, REGION_TO_CONTINENT, INCLUDE_FORBIDDEN_MATCHES

    if "--generate-config" in sys.argv:
        print(CONFIG_BLOCK.strip("\n"))
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
        description=("Monitor a League of Legends user's playing status and send customizable email alerts [ https://github.com/misiektoja/lol_monitor/ ]"), formatter_class=argparse.RawTextHelpFormatter
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
        help="Location of the optional config file",
    )
    conf.add_argument(
        "--generate-config",
        action="store_true",
        help="Print default config template and exit",
    )
    conf.add_argument(
        "--env-file",
        dest="env_file",
        metavar="PATH",
        help="Path to optional dotenv file (auto-search if not set, disable with 'none')",
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

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    if args.config_file:
        CLI_CONFIG_PATH = os.path.expanduser(args.config_file)

    cfg_path = find_config_file(CLI_CONFIG_PATH)

    if not cfg_path and CLI_CONFIG_PATH:
        print(f"* Error: Config file '{CLI_CONFIG_PATH}' does not exist")
        sys.exit(1)

    if cfg_path:
        try:
            with open(cfg_path, "r") as cf:
                exec(cf.read(), globals())
        except Exception as e:
            print(f"* Error loading config file '{cfg_path}': {e}")
            sys.exit(1)

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
                    print(f"* Warning: dotenv file '{env_path}' does not exist\n")
                else:
                    load_dotenv(env_path, override=True)
            else:
                env_path = find_dotenv() or None
                if env_path:
                    load_dotenv(env_path, override=True)
        except ImportError:
            env_path = DOTENV_FILE if DOTENV_FILE else None
            if env_path:
                print(f"* Warning: Cannot load dotenv file '{env_path}' because 'python-dotenv' is not installed\n\nTo install it, run:\n    pip3 install python-dotenv\n\nOnce installed, re-run this tool\n")

    if env_path:
        for secret in SECRET_KEYS:
            val = os.getenv(secret)
            if val is not None:
                globals()[secret] = val

    if not check_internet():
        sys.exit(1)

    if args.send_test_email:
        print("* Sending test email notification ...\n")
        if send_email("lol_monitor: test email", "This is test email - your SMTP settings seems to be correct !", "", SMTP_SSL, smtp_timeout=5) == 0:
            print("* Email sent successfully !")
        else:
            sys.exit(1)
        sys.exit(0)

    if not args.riot_id or not args.region:
        print("* Error: RIOT_ID and REGION arguments are required !")
        sys.exit(1)

    if not REGION_TO_CONTINENT.get(args.region):
        print("* Error: REGION might be wrong as it is not present in 'REGION_TO_CONTINENT' dictionary")
        sys.exit(1)

    if args.riot_api_key:
        RIOT_API_KEY = args.riot_api_key

    if not RIOT_API_KEY or RIOT_API_KEY == "your_riot_api_key":
        print("* Error: RIOT_API_KEY (-r / --riot_api_key) value is empty or incorrect\n")
        sys.exit(1)

    if args.check_interval:
        LOL_CHECK_INTERVAL = args.check_interval
        LIVENESS_CHECK_COUNTER = LIVENESS_CHECK_INTERVAL / LOL_CHECK_INTERVAL

    if args.active_interval:
        LOL_ACTIVE_CHECK_INTERVAL = args.active_interval

    if args.include_forbidden_matches is True:
        INCLUDE_FORBIDDEN_MATCHES = True

    if args.csv_file:
        CSV_FILE = os.path.expanduser(args.csv_file)
    else:
        if CSV_FILE:
            CSV_FILE = os.path.expanduser(CSV_FILE)

    if CSV_FILE:
        try:
            with open(CSV_FILE, 'a', newline='', buffering=1, encoding="utf-8") as _:
                pass
        except Exception as e:
            print(f"* Error: CSV file cannot be opened for writing: {e}")
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
                print(f"* Error: {e}")
                if 'Unauthorized' in str(e):
                    print("* API key might not be valid anymore!")
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
            print(f"* Error: {e}")
            if 'Unauthorized' in str(e):
                print("* API key might not be valid anymore!")
        sys.exit(0)

    riotid_name, riotid_tag = get_user_riot_name_tag(args.riot_id)

    if not riotid_name or not riotid_tag:
        sys.exit(1)

    if args.disable_logging is True:
        DISABLE_LOGGING = True

    if not DISABLE_LOGGING:
        log_path = Path(os.path.expanduser(LOL_LOGFILE))
        if log_path.parent != Path('.'):
            if log_path.suffix == "":
                log_path = log_path.parent / f"{log_path.name}_{riotid_name}.log"
        else:
            if log_path.suffix == "":
                log_path = Path(f"{log_path.name}_{riotid_name}.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        FINAL_LOG_PATH = str(log_path)
        sys.stdout = Logger(FINAL_LOG_PATH)
    else:
        FINAL_LOG_PATH = None

    if args.notify_status is True:
        STATUS_NOTIFICATION = True

    if args.notify_errors is False:
        ERROR_NOTIFICATION = False

    if SMTP_HOST.startswith("your_smtp_server_"):
        STATUS_NOTIFICATION = False
        ERROR_NOTIFICATION = False

    print(f"* LoL polling intervals:\t[NOT in game: {display_time(LOL_CHECK_INTERVAL)}] [in game: {display_time(LOL_ACTIVE_CHECK_INTERVAL)}]")
    print(f"* Email notifications:\t\t[status changes = {STATUS_NOTIFICATION}] [errors = {ERROR_NOTIFICATION}]")
    print(f"* Include forbidden matches:\t{INCLUDE_FORBIDDEN_MATCHES}")
    print(f"* Liveness check:\t\t{bool(LIVENESS_CHECK_INTERVAL)}" + (f" ({display_time(LIVENESS_CHECK_INTERVAL)})" if LIVENESS_CHECK_INTERVAL else ""))
    print(f"* CSV logging enabled:\t\t{bool(CSV_FILE)}" + (f" ({CSV_FILE})" if CSV_FILE else ""))
    print(f"* Output logging enabled:\t{not DISABLE_LOGGING}" + (f" ({FINAL_LOG_PATH})" if not DISABLE_LOGGING else ""))
    print(f"* Configuration file:\t\t{cfg_path}")
    print(f"* Dotenv file:\t\t\t{env_path or 'None'}\n")

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
