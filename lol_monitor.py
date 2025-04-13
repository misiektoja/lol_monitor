#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v1.6

Tool implementing real-time tracking of LoL (League of Legends) players activities:
https://github.com/misiektoja/lol_monitor/

Python pip3 requirements:

pulsefire
python-dateutil
requests
python-dotenv (optional)
"""

VERSION = 1.6

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
# Can also be enabled via the -s parameter
STATUS_NOTIFICATION = False

# Whether to send an email on errors
# Can also be disabled via the -e parameter
ERROR_NOTIFICATION = True

# How often to check for player activity when the user is NOT in a game; in seconds
# Can also be set using the -c parameter
LOL_CHECK_INTERVAL = 150  # 2,5 min

# How often to check for player activity when the user is IN a game; in seconds
# Can also be set using the -k parameter
LOL_ACTIVE_CHECK_INTERVAL = 45  # 45 seconds

# If the user has been in-game for longer than the time below, begin checking for new historical matches
# This helps work around occasional issues with the Riot API reporting a "stuck" in-game status
LOL_HANGED_INGAME_INTERVAL = 1800  # 30 mins

# How often to print a "liveness check" message to the output; in seconds
# Set to 0 to disable
LIVENESS_CHECK_INTERVAL = 43200  # 12 hours

# URL used to verify internet connectivity at startup
CHECK_INTERNET_URL = 'https://europe.api.riotgames.com/'

# Timeout used when checking initial internet connectivity; in seconds
CHECK_INTERNET_TIMEOUT = 5

# CSV file to write all game status changes
# Can also be set using the -b parameter
CSV_FILE = ""

# Location of the optional dotenv file which can keep secrets
# If not specified it will try to auto-search for .env files
# To disable auto-search, set this to the literal string "none"
# Can also be set using the --env-file parameter
DOTENV_FILE = ""

# Base name of the log file. The tool will save its output to lol_monitor_<riot_id_name>.log file
LOL_LOGFILE = "lol_monitor"

# Whether to disable logging to lol_monitor_<riot_id_name>.log
# Can also be disabled via the -d parameter
DISABLE_LOGGING = False

# Width of horizontal line (─)
HORIZONTAL_LINE = 113

# Whether to clear the terminal screen after starting the tool
CLEAR_SCREEN = True

# Value used by signal handlers to increase or decrease the in-game activity check interval (LOL_ACTIVE_CHECK_INTERVAL); in seconds
LOL_ACTIVE_CHECK_SIGNAL_VALUE = 30  # 30 seconds
"""

# -------------------------
# CONFIGURATION SECTION END
# -------------------------

region_to_continent = {
    "eun1": "europe",   # Europe Nordic & East (EUNE)
    "euw1": "europe",   # Europe West (EUW)
    "tr1": "europe",    # Turkey (TR1)
    "ru": "europe",     # Russia
    "na1": "americas",  # North America (NA) – now the sole NA endpoint
    "br1": "americas",  # Brazil (BR)
    "la1": "americas",  # Latin America North (LAN)
    "la2": "americas",  # Latin America South (LAS)
    "jp1": "asia",      # Japan (JP)
    "kr": "asia",       # Korea (KR)
    "sg2": "sea",       # Southeast Asia (SEA) – Singapore, Malaysia, Indonesia (+ Thailand & Philippines since Jan 9, 2025)
    "tw2": "sea",       # Taiwan, Hong Kong & Macao (TW/HK/MO)
    "vn2": "sea",       # Vietnam (VN)
    "oc1": "sea"        # Oceania (OC)
}

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
    "ULTBOOK": "Ultimate Spellbook"
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
LOL_HANGED_INGAME_INTERVAL = 0
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

exec(CONFIG_BLOCK, globals())

# Default name for the optional config file
DEFAULT_CONFIG_FILENAME = "lol_monitor.conf"

# List of secret keys to load from env/config
SECRET_KEYS = ("RIOT_API_KEY", "SMTP_PASSWORD")

LIVENESS_CHECK_COUNTER = LIVENESS_CHECK_INTERVAL / LOL_CHECK_INTERVAL

stdout_bck = None
csvfieldnames = ['Match Start', 'Match Stop', 'Duration', 'Victory', 'Kills', 'Deaths', 'Assists', 'Champion', 'Team 1', 'Team 2']

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
from typing import Optional
try:
    from pulsefire.clients import RiotAPIClient
except ModuleNotFoundError:
    raise SystemExit("Error: Couldn't find the Pulsefire library !\n\nTo install it, run:\n    pip3 install pulsefire\n\nOnce installed, re-run this tool. For more help, visit:\nhttps://pulsefire.iann838.com/usage/basic/installation/")
import shutil
from pathlib import Path


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
def write_csv_entry(csv_file_name, start_date_ts, stop_date_ts, duration_ts, victory, kills, deaths, assists, champion, team1, team2):
    try:

        with open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8") as csv_file:
            csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
            csvwriter.writerow({'Match Start': start_date_ts, 'Match Stop': stop_date_ts, 'Duration': duration_ts, 'Victory': victory, 'Kills': kills, 'Deaths': deaths, 'Assists': assists, 'Champion': champion, 'Team 1': team1, 'Team 2': team2})

    except Exception as e:
        raise RuntimeError(f"Failed to write to CSV file '{csv_file_name}': {e}")


# Returns the current date/time in human readable format; eg. Sun 21 Apr 2024, 15:08:45
def get_cur_ts(ts_str=""):
    return (f'{ts_str}{calendar.day_abbr[(datetime.fromtimestamp(int(time.time()))).weekday()]}, {datetime.fromtimestamp(int(time.time())).strftime("%d %b %Y, %H:%M:%S")}')


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
            account = await client.get_account_v1_by_riot_id(region=region_to_continent.get(region, "europe"), game_name=riotid_name, tag_line=riotid_tag)
            puuid = account["puuid"]
        except Exception as e:
            print(f"* Error while converting Riot ID to PUUID: {e}")
            puuid = None

    return puuid


# Gets summoner details
async def get_summoner_details(puuid: str, region: str):

    summoner_id = ""
    summoner_accountid = ""
    summoner_level = ""

    async with RiotAPIClient(default_headers={"X-Riot-Token": RIOT_API_KEY}) as client:
        try:
            summoner = await client.get_lol_summoner_v4_by_puuid(region=region, puuid=puuid)

            summoner_id = str(summoner["id"])
            summoner_accountid = str(summoner["accountId"])
            summoner_level = str(summoner["summonerLevel"])

        except Exception as e:
            print(f"* Error while getting summoner details: {e}")

    return summoner_id, summoner_accountid, summoner_level


# Returns start & stop timestamps and duration of last played match
async def get_last_match_start_ts(puuid: str, region: str):

    match_start_ts = 0

    async with RiotAPIClient(default_headers={"X-Riot-Token": RIOT_API_KEY}) as client:

        try:

            matches_history = await client.get_lol_match_v5_match_ids_by_puuid(region=region_to_continent.get(region, "europe"), puuid=puuid, queries={"start": 0, "count": 1})

            match = await client.get_lol_match_v5_match(region=region_to_continent.get(region, "europe"), id=matches_history[0])

            match_start_ts = int((match["info"]["gameStartTimestamp"]) / 1000)

        except Exception as e:
            print(f"* Error while getting last match start timestamp: {e}")
            print_cur_ts("Timestamp:\t\t\t")

    return match_start_ts


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
async def print_current_match(puuid: str, riotid_name: str, region: str, last_match_start_ts: int, last_match_stop_ts: int, status_notification_flag):

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

            if game_modes_mapping.get(gamemode):
                gamemode = game_modes_mapping.get(gamemode)

            if match_start_ts < 1000000000:
                match_start_ts = int(time.time())

            print(f"*** LoL user {riotid_name} is in game now (after {calculate_timespan(match_start_ts, int(last_match_stop_ts))})\n")

            print(f"User played last time:\t\t{get_range_of_dates_from_tss(last_match_start_ts, last_match_stop_ts)}\n")

            print(f"Match ID:\t\t\t{match_id}")
            print(f"Game mode:\t\t\t{gamemode}")

            print(f"\nMatch start date:\t\t{get_date_from_ts(match_start_ts)}")

            if match_duration > 0:
                current_match_duration = display_time(int(match_duration))
            else:
                current_match_duration = "just starting ..."
                match_duration = 0

            print(f"Match duration:\t\t\t{current_match_duration}")

            current_teams = []
            u_champion_id = ""

            for p in current_match.get("participants"):
                u_riotid = p.get("riotId")
                if u_riotid:
                    u_riotid_name = u_riotid.split('#', 1)[0]
                    # u_riotid_tag=u_riotid.split('#', 1)[1]
                else:
                    u_riotid_name = "unknown"

                u_teamid = p.get("teamId", 0)

                add_new_team_member(current_teams, u_teamid, u_riotid_name)

                if u_riotid_name == riotid_name:
                    u_champion_id = p["championId"]

                    print(f"\nChampion ID:\t\t\t{u_champion_id}")

            current_teams_number = len(current_teams)
            print(f"Teams:\t\t\t\t{current_teams_number}")

            current_teams_str = ""

            for team in current_teams:
                teamid_str = f'\nTeam id {team["id"]}:'
                current_teams_str += f"{teamid_str}\n"
                print(teamid_str)

                for member in team["members"]:
                    member_str = f"- {member}"
                    current_teams_str += f"{member_str}\n"
                    print(member_str)

            m_subject = f"LoL user {riotid_name} is in game now (after {calculate_timespan(match_start_ts, int(last_match_stop_ts), show_seconds=False)} - {get_short_date_from_ts(last_match_stop_ts)})"
            m_body = f"LoL user {riotid_name} is in game now (after {calculate_timespan(match_start_ts, int(last_match_stop_ts))})\n\nUser played last time: {get_range_of_dates_from_tss(last_match_start_ts, last_match_stop_ts)}\n\nMatch ID: {match_id}\nGame mode: {gamemode}\n\nMatch start date: {get_date_from_ts(match_start_ts)}\nMatch duration: {current_match_duration}\n\nChampion ID: {u_champion_id}\nTeams: {current_teams_number}\n{current_teams_str}{get_cur_ts(nl_ch + 'Timestamp: ')}"

            if status_notification_flag:
                print(f"Sending email notification to {RECEIVER_EMAIL}")
                send_email(m_subject, m_body, "", SMTP_SSL)

            return match_start_ts
        else:
            print("User is not in game currently")
            return 0


# Prints history of matches with relevant details
async def print_match_history(puuid: str, riotid_name: str, region: str, matches_min: int, matches_num: int, status_notification_flag, csv_file_name):

    match_start_ts = 0
    match_stop_ts = 0
    match_duration = 0

    async with RiotAPIClient(default_headers={"X-Riot-Token": RIOT_API_KEY}) as client:

        matches_history = await client.get_lol_match_v5_match_ids_by_puuid(region=region_to_continent.get(region, "europe"), puuid=puuid, queries={"start": 0, "count": matches_num})

        if matches_history:

            for i in reversed(range(matches_min - 1, matches_num)):

                u_victory = 0
                u_champion = ""
                u_kills = 0
                u_deaths = 0
                u_assists = 0
                u_level = ""
                u_role = ""
                u_lane = ""
                u_role_str = ""
                u_lane_str = ""

                match = await client.get_lol_match_v5_match(region=region_to_continent.get(region, "europe"), id=matches_history[i])

                match_id = match["metadata"].get("matchId", 0)
                match_creation_ts = int((match["info"].get("gameCreation", 0)) / 1000)
                match_start_ts = int((match["info"].get("gameStartTimestamp", 0)) / 1000)
                match_stop_ts = int((match["info"].get("gameEndTimestamp", 0)) / 1000)
                match_duration = match["info"].get("gameDuration", 0)

                gamemode = match["info"].get("gameMode")

                if game_modes_mapping.get(gamemode):
                    gamemode = game_modes_mapping.get(gamemode)

                if matches_num > 1:
                    print(f"Match number:\t\t\t{i + 1}")
                print(f"Match ID:\t\t\t{match_id}")
                print(f"Game mode:\t\t\t{gamemode}")
                print(f"\nMatch start-end date:\t\t{get_range_of_dates_from_tss(match_start_ts, match_stop_ts)}")
                print(f"Match creation:\t\t\t{get_date_from_ts(match_creation_ts)}")
                print(f"Match duration:\t\t\t{display_time(int(match_duration))}")

                last_played = calculate_timespan(int(time.time()), match_stop_ts)
                if i == 0:
                    print(f"\nUser played last time:\t\t{last_played} ago")

                teams = []

                for p in match["info"].get("participants"):
                    u_riotid_name = p.get("riotIdGameName", None)
                    if not u_riotid_name:
                        u_riotid_name = p.get("summonerName", None)  # supporting old matches

                    u_teamid = p.get("teamId", 0)

                    add_new_team_member(teams, u_teamid, u_riotid_name)

                    if u_riotid_name == riotid_name:
                        u_victory = p.get("win", 0)
                        u_champion = p.get("championName")
                        u_kills = p.get("kills", 0)
                        u_deaths = p.get("deaths", 0)
                        u_assists = p.get("assists", 0)
                        u_level = p.get("champLevel")
                        u_role = p.get("role")
                        u_lane = p.get("lane")

                        print(f"\nVictory:\t\t\t{u_victory}")
                        print(f"Kills/Deaths/Assists:\t\t{u_kills}/{u_deaths}/{u_assists}")

                        print(f"\nChampion:\t\t\t{u_champion}")
                        print(f"Level:\t\t\t\t{u_level}")
                        if u_role and u_role != "NONE":
                            print(f"Role:\t\t\t\t{u_role}")
                            u_role_str = f"\nRole: {u_role}"
                        else:
                            u_role_str = ""
                        if u_lane and u_lane != "NONE":
                            print(f"Lane:\t\t\t\t{u_lane}")
                            u_lane_str = f"\nLane: {u_lane}"
                        else:
                            u_lane_str = ""

                u_teams_number = len(teams)
                print(f"Teams:\t\t\t\t{u_teams_number}")

                # We display all teams in the console and emails
                teams_str = ""

                # We save only first two teams to CSV file
                team1 = []
                team2 = []

                x = 0
                for team in teams:
                    x += 1
                    teamid_str = f'\nTeam id {team["id"]}:'
                    teams_str += f"{teamid_str}\n"
                    print(teamid_str)

                    for member in team["members"]:
                        member_str = f"- {member}"
                        teams_str += f"{member_str}\n"
                        print(member_str)
                        if x == 1:
                            team1.append(member)
                        elif x == 2:
                            team2.append(member)

                team1_str = " ".join(f"'{x}'" for x in team1)
                team2_str = " ".join(f"'{x}'" for x in team2)

                try:
                    if csv_file_name:
                        write_csv_entry(csv_file_name, str(datetime.fromtimestamp(match_start_ts)), str(datetime.fromtimestamp(match_stop_ts)), display_time(int(match_duration)), u_victory, u_kills, u_deaths, u_assists, u_champion, team1_str, team2_str)
                except Exception as e:
                    print(f"* Error: {e}")

                if status_notification_flag and i == 0:
                    m_subject = f"LoL user {riotid_name} match summary ({get_range_of_dates_from_tss(match_start_ts, match_stop_ts, short=True)}, {display_time(int(match_duration), granularity=1)}, {u_victory})"
                    m_body = f"LoL user {riotid_name} last match summary\n\nMatch ID: {match_id}\nGame mode: {gamemode}\n\nMatch start-end date: {get_range_of_dates_from_tss(match_start_ts, match_stop_ts)}\nMatch creation: {get_date_from_ts(match_creation_ts)}\nMatch duration: {display_time(int(match_duration))}\n\nVictory: {u_victory}\nKills/deaths/assists: {u_kills}/{u_deaths}/{u_assists}\n\nChampion: {u_champion}\nLevel: {u_level}{u_role_str}{u_lane_str}\nTeams: {u_teams_number}\n{teams_str}{get_cur_ts(nl_ch + 'Timestamp: ')}"
                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                    send_email(m_subject, m_body, "", SMTP_SSL)

                if matches_num > 1:
                    print("─" * HORIZONTAL_LINE)

    return match_start_ts, match_stop_ts


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
        await print_match_history(puuid, riotid_name, region, matches_min, matches_num, False, csv_file_name)


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


# Main function that monitors gaming activity of the specified LoL user
async def lol_monitor_user(riotid, region, csv_file_name):

    alive_counter = 0
    last_match_start_ts = 0
    last_match_stop_ts = 0

    try:
        if csv_file_name:
            init_csv_file(csv_file_name)
    except Exception as e:
        print(f"* Error: {e}")

    puuid = await get_user_puuid(riotid, region)

    if not puuid:
        print("* Error: Cannot get PUUID, the Riot ID or region might be wrong !")
        sys.exit(2)

    riotid_name, riotid_tag = get_user_riot_name_tag(riotid)

    summoner_id, summoner_accountid, summoner_level = await get_summoner_details(puuid, region)

    print(f"Riot ID (name#tag):\t\t{riotid}")
    print(f"Riot PUUID:\t\t\t{puuid}")
    # print(f"Summoner ID:\t\t\t{summoner_id}")
    # print(f"Summoner account ID:\t\t{summoner_accountid}")
    print(f"Summoner level:\t\t\t{summoner_level}")
    print()

    print("User last played match:\n")
    try:
        last_match_start_ts, last_match_stop_ts = await print_match_history(puuid, riotid_name, region, 1, 1, False, None)
    except Exception as e:
        if 'Forbidden' in str(e) or 'Unknown patch name' in str(e):
            print("* API key might not be valid anymore or new patch deployed!")
        print(f"* Error while getting last played match: {e}")

    if not last_match_start_ts:
        print("* Error: Cannot get last match details !")

    last_match_start_ts_old = last_match_start_ts
    ingame = False
    ingameold = False
    game_finished_ts = 0
    alive_counter = 0
    email_sent = False
    current_match_start_ts = 0

    print_cur_ts("\nTimestamp:\t\t\t")

    while True:

        ingame = await is_user_in_match(puuid, region)

        try:

            if ingame != ingameold:

                # User is playing new match
                if ingame:
                    current_match_start_ts = await print_current_match(puuid, riotid_name, region, last_match_start_ts, last_match_stop_ts, STATUS_NOTIFICATION)

                # User stopped playing the match
                else:
                    print(f"*** LoL user {riotid_name} stopped playing !")
                    m_subject = f"LoL user {riotid_name} stopped playing"
                    m_body = f"LoL user {riotid_name} stopped playing{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"

                    game_finished_ts = int(time.time())

                    if STATUS_NOTIFICATION:
                        print(f"Sending email notification to {RECEIVER_EMAIL}")
                        send_email(m_subject, m_body, "", SMTP_SSL)

                print_cur_ts("\nTimestamp:\t\t\t")

            ingameold = ingame
            alive_counter += 1

            if ingame or (not ingame and game_finished_ts and (int(time.time()) - game_finished_ts) <= LOL_CHECK_INTERVAL):
                time.sleep(LOL_ACTIVE_CHECK_INTERVAL)
            else:
                time.sleep(LOL_CHECK_INTERVAL)

            if not ingame or (ingame and current_match_start_ts and (int(time.time()) - current_match_start_ts) > LOL_HANGED_INGAME_INTERVAL):
                last_match_start_ts_new = await get_last_match_start_ts(puuid, region)

                if last_match_start_ts_new and last_match_start_ts_new != last_match_start_ts_old:

                    print("User last played match:\n")
                    last_match_start_ts_new, last_match_stop_ts_new = await print_match_history(puuid, riotid_name, region, 1, 1, STATUS_NOTIFICATION, csv_file_name)

                    if last_match_start_ts_new and last_match_stop_ts_new:
                        last_match_start_ts = last_match_start_ts_new
                        last_match_stop_ts = last_match_stop_ts_new
                        last_match_start_ts_old = last_match_start_ts
                    else:
                        print("* Error while getting last match details!")

                    print_cur_ts("\nTimestamp:\t\t\t")

            email_sent = False

            if LIVENESS_CHECK_COUNTER and alive_counter >= LIVENESS_CHECK_COUNTER:
                print_cur_ts("Liveness check, timestamp: ")
                alive_counter = 0
        except Exception as e:
            print(f"* Error, retrying in {display_time(LOL_CHECK_INTERVAL)}: {e}")
            if 'Forbidden' in str(e) or 'Unknown patch name' in str(e):
                print("* API key might not be valid anymore or new patch deployed!")
                if ERROR_NOTIFICATION and not email_sent:
                    m_subject = f"lol_monitor: API key error! (user: {riotid_name})"
                    m_body = f"API key might not be valid anymore or new patch deployed: {e}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                    send_email(m_subject, m_body, "", SMTP_SSL)
                    email_sent = True
            print_cur_ts("Timestamp:\t\t\t")
            time.sleep(LOL_CHECK_INTERVAL)
            continue


def main():
    global CLI_CONFIG_PATH, DOTENV_FILE, LIVENESS_CHECK_COUNTER, RIOT_API_KEY, CSV_FILE, DISABLE_LOGGING, LOL_LOGFILE, STATUS_NOTIFICATION, ERROR_NOTIFICATION, LOL_CHECK_INTERVAL, LOL_ACTIVE_CHECK_INTERVAL, SMTP_PASSWORD, stdout_bck

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

    # Features & Output
    opts = parser.add_argument_group("Features & output")
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

    if not region_to_continent.get(args.region):
        print("* Error: REGION might be wrong as it is not present in 'region_to_continent' dictionary")
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
        if args.recent_matches_count and args.recent_matches_count > 0:
            matches_num = args.recent_matches_count
        else:
            matches_num = 2

        if args.min_of_recent_matches and args.min_of_recent_matches > 0:
            matches_min = args.min_of_recent_matches
        else:
            matches_min = 1

        if matches_min > matches_num:
            print("* min_of_recent_matches cannot be > number_of_recent_matches")
            sys.exit(1)

        list_operation = "* Listing & saving" if CSV_FILE else "* Listing"

        if matches_min != matches_num:
            print(f"{list_operation} recent matches from {matches_num} to {matches_min} for '{args.riot_id}':\n")
        else:
            print(f"{list_operation} recent match for '{args.riot_id}':\n")

        try:
            asyncio.run(print_save_recent_matches(args.riot_id, args.region, matches_min, matches_num, CSV_FILE))
        except Exception as e:
            if 'Forbidden' in str(e) or 'Unknown patch name' in str(e):
                print("* API key might not be valid anymore or new patch deployed!")
            print(f"* Error: {e}")
        sys.exit(0)

    riotid_name, riotid_tag = get_user_riot_name_tag(args.riot_id)

    if not riotid_name or not riotid_tag:
        sys.exit(1)

    if args.disable_logging is True:
        DISABLE_LOGGING = True

    if not DISABLE_LOGGING:
        log_path = Path(os.path.expanduser(LOL_LOGFILE))
        if log_path.is_dir():
            raise SystemExit(f"* Error: LOL_LOGFILE '{log_path}' is a directory, expected a filename")
        if log_path.suffix == "":
            log_path = log_path.with_name(f"{log_path.name}_{riotid_name}.log")
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
    print("-" * len(out))

    asyncio.run(lol_monitor_user(args.riot_id, args.region, CSV_FILE))

    sys.stdout = stdout_bck
    sys.exit(0)


if __name__ == "__main__":
    main()
