#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v1.5

Tool implementing real-time tracking of LoL (League of Legends) players activities:
https://github.com/misiektoja/lol_monitor/

Python pip3 requirements:

pulsefire
python-dateutil
requests
"""

VERSION = 1.5

# ---------------------------
# CONFIGURATION SECTION START
# ---------------------------

# Get the development Riot API key valid for 24 hours here: https://developer.riotgames.com
# Or apply for persistent personal or production Riot API key here: https://developer.riotgames.com/app-type
# Put your Riot API key below (or use -r parameter)
RIOT_API_KEY = "your_riot_api_key"

# SMTP settings for sending email notifications, you can leave it as it is below and no notifications will be sent
SMTP_HOST = "your_smtp_server_ssl"
SMTP_PORT = 587
SMTP_USER = "your_smtp_user"
SMTP_PASSWORD = "your_smtp_password"
SMTP_SSL = True
SENDER_EMAIL = "your_sender_email"
# SMTP_HOST = "your_smtp_server_plaintext"
# SMTP_PORT = 25
# SMTP_USER = "your_smtp_user"
# SMTP_PASSWORD = "your_smtp_password"
# SMTP_SSL = False
# SENDER_EMAIL = "your_sender_email"
RECEIVER_EMAIL = "your_receiver_email"

# How often do we perform checks for player activity when user is NOT in game, you can also use -c parameter; in seconds
LOL_CHECK_INTERVAL = 150  # 2,5 min

# How often do we perform checks for player activity when user is in game, you can also use -k parameter; in seconds
LOL_ACTIVE_CHECK_INTERVAL = 45  # 45 seconds

# If user is in game for longer than time defined below, we start checking for new historical matches
# It is to address sporadic issues with hanging in-game status reported by Riot API
LOL_HANGED_INGAME_INTERVAL = 1800  # 30 mins

# How often do we perform alive check by printing "alive check" message in the output; in seconds
TOOL_ALIVE_INTERVAL = 21600  # 6 hours

# URL we check in the beginning to make sure we have internet connectivity
CHECK_INTERNET_URL = 'http://www.google.com/'

# Default value for initial checking of internet connectivity; in seconds
CHECK_INTERNET_TIMEOUT = 5

# The name of the .log file; the tool by default will output its messages to lol_monitor_riotidname.log file
LOL_LOGFILE = "lol_monitor"

# Value used by signal handlers increasing/decreasing the check for player activity when user is in game (LOL_ACTIVE_CHECK_INTERVAL); in seconds
LOL_ACTIVE_CHECK_SIGNAL_VALUE = 30  # 30 seconds

# -------------------------
# CONFIGURATION SECTION END
# -------------------------

region_to_continent = {
    "eun1": "europe",   # Europe Nordic & East (EUNE)
    "euw1": "europe",   # Europe West (EUW)
    "na1": "americas",  # North America (NA)
    "na2": "americas",  # North America (NA)
    "br1": "americas",  # Brazil (BR)
    "la1": "americas",  # Latin America North (LAN)
    "la2": "americas",  # Latin America South (LAS)
    "jp1": "asia",      # Japan
    "kr": "asia",       # Korea
    "tr1": "europe",      # Turkey (TR1)
    "ru": "europe",       # Russia
    "ph2": "sea",      # The Philippines
    "sg2": "sea",      # Singapore, Malaysia, & Indonesia
    "tw2": "sea",      # Taiwan, Hong Kong, and Macao
    "th2": "sea",      # Thailand
    "vn2": "sea",      # Vietnam
    "oc1": "sea"        # Oceania
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

TOOL_ALIVE_COUNTER = TOOL_ALIVE_INTERVAL / LOL_CHECK_INTERVAL

stdout_bck = None
csvfieldnames = ['Match Start', 'Match Stop', 'Duration', 'Victory', 'Kills', 'Deaths', 'Assists', 'Champion', 'Team 1', 'Team 2']

status_notification = False

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
from pulsefire.clients import RiotAPIClient


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


# Function to check internet connectivity
def check_internet():
    url = CHECK_INTERNET_URL
    try:
        _ = req.get(url, timeout=CHECK_INTERNET_TIMEOUT)
        print("OK")
        return True
    except Exception as e:
        print(f"No connectivity, please check your network - {e}")
        sys.exit(1)
    return False


# Function to convert absolute value of seconds to human readable format
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


# Function to calculate time span between two timestamps in seconds
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


# Function to send email notification
def send_email(subject, body, body_html, use_ssl, smtp_timeout=15):
    fqdn_re = re.compile(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}\.?$)')
    email_re = re.compile(r'[^@]+@[^@]+\.[^@]+')

    try:
        is_ip = ipaddress.ip_address(str(SMTP_HOST))
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
        email_msg["Subject"] = Header(subject, 'utf-8')

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
        print(f"Error sending email - {e}")
        return 1
    return 0


# Function to write CSV entry
def write_csv_entry(csv_file_name, start_date_ts, stop_date_ts, duration_ts, victory, kills, deaths, assists, champion, team1, team2):
    try:
        csv_file = open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8")
        csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
        csvwriter.writerow({'Match Start': start_date_ts, 'Match Stop': stop_date_ts, 'Duration': duration_ts, 'Victory': victory, 'Kills': kills, 'Deaths': deaths, 'Assists': assists, 'Champion': champion, 'Team 1': team1, 'Team 2': team2})
        csv_file.close()
    except Exception as e:
        raise


# Function to return the timestamp in human readable format; eg. Sun, 21 Apr 2024, 15:08:45
def get_cur_ts(ts_str=""):
    return (f'{ts_str}{calendar.day_abbr[(datetime.fromtimestamp(int(time.time()))).weekday()]}, {datetime.fromtimestamp(int(time.time())).strftime("%d %b %Y, %H:%M:%S")}')


# Function to print the current timestamp in human readable format; eg. Sun, 21 Apr 2024, 15:08:45
def print_cur_ts(ts_str=""):
    print(get_cur_ts(str(ts_str)))
    print("-----------------------------------------------------------------------------------")


# Function to return the timestamp/datetime object in human readable format (long version); eg. Sun, 21 Apr 2024, 15:08:45
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


# Function to return the timestamp/datetime object in human readable format (short version); eg.
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


# Function to return the timestamp/datetime object in human readable format (only hour, minutes and optionally seconds): eg. 15:08:12
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


# Function to return the range between two timestamps/datetime objects; eg. Sun 21 Apr 14:09 - 14:15
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
    global status_notification
    status_notification = not status_notification
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [status changes = {status_notification}]")
    print_cur_ts("Timestamp:\t\t")


# Signal handler for SIGTRAP allowing to increase check timer for player activity when user is in game by LOL_ACTIVE_CHECK_SIGNAL_VALUE seconds
def increase_active_check_signal_handler(sig, frame):
    global LOL_ACTIVE_CHECK_INTERVAL
    LOL_ACTIVE_CHECK_INTERVAL = LOL_ACTIVE_CHECK_INTERVAL + LOL_ACTIVE_CHECK_SIGNAL_VALUE
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* LoL timers: [active check interval: {display_time(LOL_ACTIVE_CHECK_INTERVAL)}]")
    print_cur_ts("Timestamp:\t\t")


# Signal handler for SIGABRT allowing to decrease check timer for player activity when user is in game by LOL_ACTIVE_CHECK_SIGNAL_VALUE seconds
def decrease_active_check_signal_handler(sig, frame):
    global LOL_ACTIVE_CHECK_INTERVAL
    if LOL_ACTIVE_CHECK_INTERVAL - LOL_ACTIVE_CHECK_SIGNAL_VALUE > 0:
        LOL_ACTIVE_CHECK_INTERVAL = LOL_ACTIVE_CHECK_INTERVAL - LOL_ACTIVE_CHECK_SIGNAL_VALUE
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* LoL timers: [active check interval: {display_time(LOL_ACTIVE_CHECK_INTERVAL)}]")
    print_cur_ts("Timestamp:\t\t")


# Adding new participant to the team
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


# Function returning Riot game name & tag line for specified Riot ID
def get_user_riot_name_tag(riotid: str):

    try:
        riotid_name = riotid.split('#', 1)[0]
        riotid_tag = riotid.split('#', 1)[1]
    except IndexError:
        print("Error while extracting name and tagline from Riot ID ! It needs to be in name#tag format.")
        return "", ""

    return riotid_name, riotid_tag


# Function converting Riot ID to PUUID
async def get_user_puuid(riotid: str, region: str):

    riotid_name, riotid_tag = get_user_riot_name_tag(riotid)

    async with RiotAPIClient(default_headers={"X-Riot-Token": RIOT_API_KEY}) as client:

            try:
                account = await client.get_account_v1_by_riot_id(region=region_to_continent.get(region), game_name=riotid_name, tag_line=riotid_tag)
                puuid = account["puuid"]
            except Exception as e:
                print(f"Error while converting Riot ID to PUUID - {e}")
                puuid = 0

    return puuid


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
                print(f"Error while getting summoner details - {e}")

    return summoner_id, summoner_accountid, summoner_level


# Functioning returning start & stop timestamps and duration of last played match
async def get_last_match_start_ts(puuid: str, region: str):

    match_start_ts = 0

    async with RiotAPIClient(default_headers={"X-Riot-Token": RIOT_API_KEY}) as client:

        try:

            matches_history = await client.get_lol_match_v5_match_ids_by_puuid(region=region_to_continent.get(region), puuid=puuid, queries={"start": 0, "count": 1})

            match = await client.get_lol_match_v5_match(region=region_to_continent.get(region), id=matches_history[0])

            match_start_ts = int((match["info"]["gameStartTimestamp"]) / 1000)

        except Exception as e:
            print(f"Error while getting last match start timestamp - {e}")
            print_cur_ts("Timestamp:\t\t")

    return match_start_ts


# Function checking if player is currently in game
async def is_user_in_match(puuid: str, region: str):

    async with RiotAPIClient(default_headers={"X-Riot-Token": RIOT_API_KEY}) as client:

        try:
            current_match = await client.get_lol_spectator_v5_active_game_by_summoner(region=region, puuid=puuid)
            if current_match:
                return True
        except Exception as e:
            return False


# Function printing details of the current player's match (user is in game)
async def print_current_match(puuid: str, riotid_name: str, region: str, last_match_start_ts: int, last_match_stop_ts: int, status_notification_flag):

    async with RiotAPIClient(default_headers={"X-Riot-Token": RIOT_API_KEY}) as client:

        try:
            current_match = await client.get_lol_spectator_v5_active_game_by_summoner(region=region, puuid=puuid)
        except Exception as e:
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

            print(f"User played last time:\t{get_range_of_dates_from_tss(last_match_start_ts, last_match_stop_ts)}\n")

            print(f"Match ID:\t\t{match_id}")
            print(f"Game mode:\t\t{gamemode}")

            print(f"\nMatch start date:\t{get_date_from_ts(match_start_ts)}")

            if match_duration > 0:
                current_match_duration = display_time(int(match_duration))
            else:
                current_match_duration = "just starting ..."
                match_duration = 0

            print(f"Match duration:\t\t{current_match_duration}")

            current_teams = []

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

                    print(f"\nChampion ID:\t\t{u_champion_id}")

            current_teams_number = len(current_teams)
            print(f"Teams:\t\t\t{current_teams_number}")

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


# Functioning printing history of matches with relevant details
async def print_match_history(puuid: str, riotid_name: str, region: str, matches_min: int, matches_num: int, status_notification_flag, csv_file_name):

    match_start_ts = 0
    match_stop_ts = 0
    match_duration = 0

    async with RiotAPIClient(default_headers={"X-Riot-Token": RIOT_API_KEY}) as client:

        matches_history = await client.get_lol_match_v5_match_ids_by_puuid(region=region_to_continent.get(region), puuid=puuid, queries={"start": 0, "count": matches_num})

        if matches_history:

            for i in reversed(range(matches_min - 1, matches_num)):

                match = await client.get_lol_match_v5_match(region=region_to_continent.get(region), id=matches_history[i])

                match_id = match["metadata"].get("matchId", 0)
                match_creation_ts = int((match["info"].get("gameCreation", 0)) / 1000)
                match_start_ts = int((match["info"].get("gameStartTimestamp", 0)) / 1000)
                match_stop_ts = int((match["info"].get("gameEndTimestamp", 0)) / 1000)
                match_duration = match["info"].get("gameDuration", 0)

                gamemode = match["info"].get("gameMode")

                if game_modes_mapping.get(gamemode):
                    gamemode = game_modes_mapping.get(gamemode)

                if matches_num > 1:
                    print(f"Match number:\t\t{i + 1}")
                print(f"Match ID:\t\t{match_id}")
                print(f"Game mode:\t\t{gamemode}")
                print(f"\nMatch start-end date:\t{get_range_of_dates_from_tss(match_start_ts, match_stop_ts)}")
                print(f"Match creation:\t\t{get_date_from_ts(match_creation_ts)}")
                print(f"Match duration:\t\t{display_time(int(match_duration))}")

                last_played = calculate_timespan(int(time.time()), match_stop_ts)
                if i == 0:
                    print(f"\nUser played last time:\t{last_played} ago")

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

                        print(f"\nVictory:\t\t{u_victory}")
                        print(f"Kills/Deaths/Assists:\t{u_kills}/{u_deaths}/{u_assists}")

                        print(f"\nChampion:\t\t{u_champion}")
                        print(f"Level:\t\t\t{u_level}")
                        if u_role and u_role != "NONE":
                            print(f"Role:\t\t\t{u_role}")
                            u_role_str = f"\nRole: {u_role}"
                        else:
                            u_role_str = ""
                        if u_lane and u_lane != "NONE":
                            print(f"Lane:\t\t\t{u_lane}")
                            u_lane_str = f"\nLane: {u_lane}"
                        else:
                            u_lane_str = ""

                u_teams_number = len(teams)
                print(f"Teams:\t\t\t{u_teams_number}")

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
                    print(f"* Cannot write CSV entry - {e}")

                if status_notification_flag and i == 0:
                    m_subject = f"LoL user {riotid_name} match summary ({get_range_of_dates_from_tss(match_start_ts, match_stop_ts, short=True)}, {display_time(int(match_duration), granularity=1)}, {u_victory})"
                    m_body = f"LoL user {riotid_name} last match summary\n\nMatch ID: {match_id}\nGame mode: {gamemode}\n\nMatch start-end date: {get_range_of_dates_from_tss(match_start_ts, match_stop_ts)}\nMatch creation: {get_date_from_ts(match_creation_ts)}\nMatch duration: {display_time(int(match_duration))}\n\nVictory: {u_victory}\nKills/deaths/assists: {u_kills}/{u_deaths}/{u_assists}\n\nChampion: {u_champion}\nLevel: {u_level}{u_role_str}{u_lane_str}\nTeams: {u_teams_number}\n{teams_str}{get_cur_ts(nl_ch + 'Timestamp: ')}"
                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                    send_email(m_subject, m_body, "", SMTP_SSL)

                if matches_num > 1:
                    print("-----------------------------------------------------------------------------------")

    return match_start_ts, match_stop_ts


# Function printing last n matches for the user
async def print_save_recent_matches(riotid: str, region: str, matches_min: int, matches_num: int, csv_file_name, csv_exists):

    try:
        if csv_file_name:
            csv_file = open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8")
            csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
            if not csv_exists:
                csvwriter.writeheader()
            csv_file.close()
    except Exception as e:
        print(f"* Error - {e}")

    puuid = await get_user_puuid(riotid, region)
    riotid_name, riotid_tag = get_user_riot_name_tag(riotid)

    await print_match_history(puuid, riotid_name, region, matches_min, matches_num, False, csv_file_name)


# Main function monitoring gaming activity of the specified LoL user
async def lol_monitor_user(riotid, region, error_notification, csv_file_name, csv_exists):

    alive_counter = 0
    last_match_start_ts = 0
    last_match_stop_ts = 0
    csvwriter = None

    try:
        if csv_file_name:
            csv_file = open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8")
            csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
            if not csv_exists:
                csvwriter.writeheader()
            csv_file.close()
    except Exception as e:
        print(f"* Error - {e}")

    puuid = await get_user_puuid(riotid, region)

    if not puuid:
        print("* Error - cannot get PUUID, the Riot ID or region might be wrong !")
        sys.exit(2)

    riotid_name, riotid_tag = get_user_riot_name_tag(riotid)

    summoner_id, summoner_accountid, summoner_level = await get_summoner_details(puuid, region)

    print(f"Riot ID (name#tag):\t{riotid}")
    print(f"Riot PUUID:\t\t{puuid}")
    # print(f"Summoner ID:\t\t{summoner_id}")
    # print(f"Summoner account ID:\t{summoner_accountid}")
    print(f"Summoner level:\t\t{summoner_level}")
    print()

    print("User last played match:\n")
    try:
        last_match_start_ts, last_match_stop_ts = await print_match_history(puuid, riotid_name, region, 1, 1, False, None)
    except Exception as e:
        if 'Forbidden' in str(e) or 'Unknown patch name' in str(e):
            print("* API key might not be valid anymore or new patch deployed!")
        print(f"* Error while getting last played match - {e}")

    if not last_match_start_ts:
                print("* Error - cannot get last match details !")

    last_match_start_ts_old = last_match_start_ts
    ingame = False
    ingameold = False
    game_finished_ts = 0
    alive_counter = 0
    email_sent = False

    print_cur_ts("\nTimestamp:\t\t")

    while True:

        ingame = await is_user_in_match(puuid, region)

        try:

            if ingame != ingameold:

                # User is playing new match
                if ingame:
                    current_match_start_ts = await print_current_match(puuid, riotid_name, region, last_match_start_ts, last_match_stop_ts, status_notification)

                # User stopped playing the match
                else:
                    print(f"*** LoL user {riotid_name} stopped playing !")
                    m_subject = f"LoL user {riotid_name} stopped playing"
                    m_body = f"LoL user {riotid_name} stopped playing{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"

                    game_finished_ts = int(time.time())

                    if status_notification:
                        print(f"Sending email notification to {RECEIVER_EMAIL}")
                        send_email(m_subject, m_body, "", SMTP_SSL)

                print_cur_ts("\nTimestamp:\t\t")

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
                    last_match_start_ts_new, last_match_stop_ts_new = await print_match_history(puuid, riotid_name, region, 1, 1, status_notification, csv_file_name)

                    if last_match_start_ts_new and last_match_stop_ts_new:
                        last_match_start_ts = last_match_start_ts_new
                        last_match_stop_ts = last_match_stop_ts_new
                        last_match_start_ts_old = last_match_start_ts
                    else:
                        print("Error while getting last match details!")

                    print_cur_ts("\nTimestamp:\t\t")

            email_sent = False

            if alive_counter >= TOOL_ALIVE_COUNTER:
                print_cur_ts("Alive check, timestamp: ")
                alive_counter = 0
        except Exception as e:
            print(f"Error, retrying in {display_time(LOL_CHECK_INTERVAL)} - {e}")
            if 'Forbidden' in str(e) or 'Unknown patch name' in str(e):
                print("* API key might not be valid anymore or new patch deployed!")
                if error_notification and not email_sent:
                    m_subject = f"lol_monitor: API key error! (user: {username})"
                    m_body = f"API key might not be valid anymore or new patch deployed: {e}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                    send_email(m_subject, m_body, "", SMTP_SSL)
                    email_sent = True
            print_cur_ts("Timestamp:\t\t")
            time.sleep(LOL_CHECK_INTERVAL)
            continue

if __name__ == "__main__":

    stdout_bck = sys.stdout

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        if platform.system() == 'Windows':
            os.system('cls')
        else:
            os.system('clear')
    except:
        print("* Cannot clear the screen contents")

    print(f"League of Legends Monitoring Tool v{VERSION}\n")

    parser = argparse.ArgumentParser("lol_monitor")
    parser.add_argument("RIOT_ID", nargs="?", help="User's LoL Riot ID", type=str)
    parser.add_argument("REGION", nargs="?", help="User's LoL region (e.g. eun1, na1, br1 etc.)", type=str)
    parser.add_argument("-r", "--riot_api_key", help="Riot API key to override the value defined within the script (RIOT_API_KEY)", type=str)
    parser.add_argument("-s", "--status_notification", help="Send email notification once user changes game playing status", action='store_true')
    parser.add_argument("-e", "--error_notification", help="Disable sending email notifications in case of errors like invalid API key", action='store_false')
    parser.add_argument("-c", "--check_interval", help="Time between monitoring checks if user is NOT in game, in seconds", type=int)
    parser.add_argument("-k", "--active_check_interval", help="Time between monitoring checks if user is in game, in seconds", type=int)
    parser.add_argument("-b", "--csv_file", help="Write all game playing status changes to CSV file", type=str, metavar="CSV_FILENAME")
    parser.add_argument("-l", "--list_recent_matches", help="List recent matches for the user", action='store_true')
    parser.add_argument("-n", "--number_of_recent_matches", help="Number of recent matches to display/save if used with -l and/or -b", type=int)
    parser.add_argument("-m", "--min_of_recent_matches", help="Minimal match to display/save if used with -l and -n, it will limit range of matches from min_of_recent_matches (e.g. 300) to number_of_recent_matches (e.g. 500)", type=int)
    parser.add_argument("-d", "--disable_logging", help="Disable logging to file 'lol_monitor_user.log' file", action='store_true')
    parser.add_argument("-z", "--send_test_email_notification", help="Send test email notification to verify SMTP settings defined in the script", action='store_true')
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    sys.stdout.write("* Checking internet connectivity ... ")
    sys.stdout.flush()
    check_internet()
    print("")

    if args.send_test_email_notification:
        print("* Sending test email notification ...\n")
        if send_email("lol_monitor: test email", "This is test email - your SMTP settings seems to be correct !", "", SMTP_SSL, smtp_timeout=5) == 0:
                print("* Email sent successfully !")
        else:
            sys.exit(1)
        sys.exit(0)

    if not args.RIOT_ID or not args.REGION:
        print("* Error: RIOT_ID and REGION arguments are required !")
        sys.exit(1)

    if not region_to_continent.get(args.REGION):
        print("* Error: REGION might be wrong as it is not present in 'region_to_continent' dict in .py file")
        sys.exit(1)

    if args.riot_api_key:
        RIOT_API_KEY = args.riot_api_key

    if not RIOT_API_KEY or RIOT_API_KEY == "your_riot_api_key":
        print("* Error: RIOT_API_KEY (-r / --riot_api_key) value is empty or incorrect\n")
        sys.exit(1)

    if args.check_interval:
        LOL_CHECK_INTERVAL = args.check_interval
        TOOL_ALIVE_COUNTER = TOOL_ALIVE_INTERVAL / LOL_CHECK_INTERVAL

    if args.active_check_interval:
        LOL_ACTIVE_CHECK_INTERVAL = args.active_check_interval

    if args.csv_file:
        csv_enabled = True
        csv_exists = os.path.isfile(args.csv_file)
        try:
            csv_file = open(args.csv_file, 'a', newline='', buffering=1, encoding="utf-8")
        except Exception as e:
            print(f"* Error: CSV file cannot be opened for writing - {e}")
            sys.exit(1)
        csv_file.close()
    else:
        csv_enabled = False
        csv_file = None
        csv_exists = False

    if args.list_recent_matches:
        if args.number_of_recent_matches and args.number_of_recent_matches > 0:
            matches_num = args.number_of_recent_matches
        else:
            matches_num = 2

        if args.min_of_recent_matches and args.min_of_recent_matches > 0:
            matches_min = args.min_of_recent_matches
        else:
            matches_min = 1

        if matches_min > matches_num:
            print("* min_of_recent_matches cannot be > number_of_recent_matches")
            sys.exit(1)

        if args.csv_file:
            list_operation = "* Listing & saving"
        else:
            list_operation = "* Listing"

        if matches_min != matches_num:
            print(f"{list_operation} recent matches from {matches_num} to {matches_min} for {args.RIOT_ID}:\n")
        else:
            print(f"{list_operation} recent match for {args.RIOT_ID}:\n")

        try:
            asyncio.run(print_save_recent_matches(args.RIOT_ID, args.REGION, matches_min, matches_num, args.csv_file, csv_exists))
        except Exception as e:
            if 'Forbidden' in str(e) or 'Unknown patch name' in str(e):
                print("* API key might not be valid anymore or new patch deployed!")
            print(f"* Error - {e}")
        sys.exit(0)

    riotid_name, riotid_tag = get_user_riot_name_tag(args.RIOT_ID)

    if not riotid_name or not riotid_tag:
        sys.exit(1)

    if not args.disable_logging:
        LOL_LOGFILE = f"{LOL_LOGFILE}_{riotid_name}.log"
        sys.stdout = Logger(LOL_LOGFILE)

    status_notification = args.status_notification

    print(f"* LoL timers:\t\t\t[check interval: {display_time(LOL_CHECK_INTERVAL)}] [active check interval: {display_time(LOL_ACTIVE_CHECK_INTERVAL)}]")
    print(f"* Email notifications:\t\t[status changes = {status_notification}] [errors = {args.error_notification}]")
    if not args.disable_logging:
        print(f"* Output logging enabled:\t{not args.disable_logging} ({LOL_LOGFILE})")
    else:
        print(f"* Output logging enabled:\t{not args.disable_logging}")
    if csv_enabled:
        print(f"* CSV logging enabled:\t\t{csv_enabled} ({args.csv_file})\n")
    else:
        print(f"* CSV logging enabled:\t\t{csv_enabled}\n")

    # We define signal handlers only for Linux & MacOS since Windows has limited number of signals supported
    if platform.system() != 'Windows':
        signal.signal(signal.SIGUSR1, toggle_status_changes_notifications_signal_handler)
        signal.signal(signal.SIGTRAP, increase_active_check_signal_handler)
        signal.signal(signal.SIGABRT, decrease_active_check_signal_handler)

    out = f"Monitoring user {args.RIOT_ID}"
    print(out)
    print("-" * len(out))

    asyncio.run(lol_monitor_user(args.RIOT_ID, args.REGION, args.error_notification, args.csv_file, csv_exists))

    sys.stdout = stdout_bck
    sys.exit(0)
