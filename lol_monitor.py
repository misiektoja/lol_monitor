#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v1.0

Script implementing real-time monitoring of LoL (League of Legends) players activity:
https://github.com/misiektoja/lol_monitor/

Python pip3 requirements:

cassiopeia
pytz
python-dateutil
requests
"""

VERSION=1.0

# ---------------------------
# CONFIGURATION SECTION START
# ---------------------------

# Get the development RIOT API key valid for 24 hours here: https://developer.riotgames.com
# Apply for persistent personal or production RIOT API key here: https://developer.riotgames.com/app-type
RIOT_API_KEY = "your_RIOT_API_key"

# How often do we perform checks for player activity when user is NOT in game; in seconds
LOL_CHECK_INTERVAL=150 # 2,5 min

# How often do we perform checks for player activity when user is in game; in seconds
LOL_ACTIVE_CHECK_INTERVAL=60 # 1 min

# How long do we wait after match has finished to grab its statistics
# Stats are not available right away, so the default 2 mins is a good compromise
LOL_GAME_FINISHED_CHECK_INTERVAL=120 # 2 min

# Specify your local time zone so we convert RIOT API timestamps to your time
LOCAL_TIMEZONE='Europe/Warsaw'

# Cassiopeia settings file location
CASSIOPEIA_SETTINGS_JSON_FILE="cassiopeia_settings.json"

# How often do we perform alive check by printing "alive check" message in the output; in seconds
TOOL_ALIVE_INTERVAL=21600 # 6 hours

# Default value for network-related timeouts in functions + alarm signal handler; in seconds
FUNCTION_TIMEOUT=30 # 30 seconds

# URL we check in the beginning to make sure we have internet connectivity
CHECK_INTERNET_URL='http://www.google.com/'

# Default value for initial checking of internet connectivity; in seconds
CHECK_INTERNET_TIMEOUT=5

# SMTP settings for sending email notifications
SMTP_HOST = "your_smtp_server_ssl"
SMTP_PORT = 587
SMTP_USER = "your_smtp_user"
SMTP_PASSWORD = "your_smtp_password"
SMTP_SSL = True
SENDER_EMAIL = "your_sender_email"
#SMTP_HOST = "your_smtp_server_plaintext"
#SMTP_PORT = 25
#SMTP_USER = "your_smtp_user"
#SMTP_PASSWORD = "your_smtp_password"
#SMTP_SSL = False
#SENDER_EMAIL = "your_sender_email"
RECEIVER_EMAIL = "your_receiver_email"

# The name of the .log file; the tool by default will output its messages to lol_monitor_username.log file
lol_logfile="lol_monitor"

# Value used by signal handlers increasing/decreasing the check for player activity when user is in game (LOL_ACTIVE_CHECK_INTERVAL); in seconds
LOL_ACTIVE_CHECK_SIGNAL_VALUE=30 # 30 seconds

# -------------------------
# CONFIGURATION SECTION END
# -------------------------

TOOL_ALIVE_COUNTER=TOOL_ALIVE_INTERVAL/LOL_CHECK_INTERVAL

stdout_bck = None
csvfieldnames = ['Match Start', 'Match Stop', 'Duration', 'Victory', 'Kills', 'Deaths', 'Assists', 'Champion', 'Blue team', 'Red team']

status_notification=False

import sys
import time
import string
import os
from datetime import datetime
from dateutil import relativedelta
import calendar
import requests as req
import signal
import smtplib, ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import argparse
import csv
import pytz
import cassiopeia

# Logger class to output messages to stdout and log file
class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.logfile = open(filename, "a", buffering=1)

    def write(self, message):
        self.terminal.write(message)
        self.logfile.write(message)
        self.terminal.flush()
        self.logfile.flush()

    def flush(self):
        pass  

# Class used to generate timeout exceptions
class TimeoutException(Exception):
    pass

# Signal handler for SIGALRM when the operation times out
def timeout_handler(sig, frame):
    raise TimeoutException

# Signal handler when user presses Ctrl+C
def signal_handler(sig, frame):
    sys.stdout = stdout_bck
    print('\n* You pressed Ctrl+C, tool is terminated.')
    sys.exit(0)

# Function to check internet connectivity
def check_internet():
    url=CHECK_INTERNET_URL
    try:
        _ = req.get(url, timeout=CHECK_INTERNET_TIMEOUT)
        print("OK")
        return True
    except Exception as e:
        print("No connectivity, please check your network -", e)
        sys.exit(1)
    return False

# Function to convert absolute value of seconds to human readable format
def display_time(seconds, granularity=2):
    intervals = (
        ('years', 31556952), # approximation
        ('months', 2629746), # approximation
        ('weeks', 604800),  # 60 * 60 * 24 * 7
        ('days', 86400),    # 60 * 60 * 24
        ('hours', 3600),    # 60 * 60
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
                result.append("{} {}".format(value, name))
        return ', '.join(result[:granularity])
    else:
        return '0 seconds'

# Function to calculate time span between two timestamps in seconds
def calculate_timespan(timestamp1, timestamp2, show_weeks=True, show_hours=True, show_minutes=True, show_seconds=False, granularity=3):
    result = []
    intervals=['years', 'months', 'weeks', 'days', 'hours', 'minutes', 'seconds']
    ts1=timestamp1
    ts2=timestamp2

    if type(timestamp1) is int:
        dt1=datetime.fromtimestamp(int(ts1))
    elif type(timestamp1) is datetime:
        dt1=timestamp1
        ts1=int(round(dt1.timestamp()))
    else:
        return ""

    if type(timestamp2) is int:
        dt2=datetime.fromtimestamp(int(ts2))
    elif type(timestamp2) is datetime:
        dt2=timestamp2
        ts2=int(round(dt2.timestamp()))
    else:
        return ""

    if ts1>=ts2:
        ts_diff=ts1-ts2
    else:
        ts_diff=ts2-ts1
        dt1, dt2 = dt2, dt1

    if ts_diff>0:
        date_diff=relativedelta.relativedelta(dt1, dt2)
        years=date_diff.years
        months=date_diff.months
        weeks=date_diff.weeks
        if not show_weeks:
            weeks=0
        days=date_diff.days
        if weeks > 0:
            days=days-(weeks*7)
        hours=date_diff.hours
        if (not show_hours and ts_diff>86400):
            hours=0
        minutes=date_diff.minutes
        if (not show_minutes and ts_diff>3600):
            minutes=0
        seconds=date_diff.seconds
        if (not show_seconds and ts_diff>60):
            seconds=0
        date_list=[years, months, weeks, days, hours, minutes, seconds]

        for index, interval in enumerate(date_list):
            if interval>0:
                name=intervals[index]
                if interval==1:
                    name = name.rstrip('s')
                result.append("{} {}".format(interval, name))
#        return ', '.join(result)
        return ', '.join(result[:granularity])
    else:
        return '0 seconds'

# Function to send email notification
def send_email(subject,body,body_html,use_ssl):

    try:     
        if use_ssl:
            ssl_context = ssl.create_default_context()
            smtpObj = smtplib.SMTP(SMTP_HOST,SMTP_PORT)
            smtpObj.starttls(context=ssl_context)
        else:
            smtpObj = smtplib.SMTP(SMTP_HOST,SMTP_PORT)
        smtpObj.login(SMTP_USER,SMTP_PASSWORD)
        email_msg = MIMEMultipart('alternative')
        email_msg["From"] = SENDER_EMAIL
        email_msg["To"] = RECEIVER_EMAIL
        email_msg["Subject"] =  Header(subject, 'utf-8')

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
        print("Error sending email -", e)
        return 1
    return 0

# Function to write CSV entry
def write_csv_entry(csv_file_name, start_date_ts, stop_date_ts, duration_ts, victory, kills, deaths, assists, champion, blue_team, red_team):
    try:
        csv_file=open(csv_file_name, 'a', newline='', buffering=1)
        csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
        csvwriter.writerow({'Match Start': start_date_ts, 'Match Stop': stop_date_ts, 'Duration': duration_ts, 'Victory': victory, 'Kills': kills, 'Deaths': deaths, 'Assists': assists, 'Champion': champion, 'Blue team': blue_team, 'Red team': red_team })
        csv_file.close()
    except Exception as e:
        raise

# Function to convert UTC string returned by RIOT API to datetime object in specified timezone
def convert_utc_str_to_tz_datetime(utc_string, timezone):
    utc_string_sanitize=utc_string.split('+', 1)[0]
    utc_string_sanitize=utc_string_sanitize.split('.', 1)[0]
    dt_utc = datetime.strptime(utc_string_sanitize, '%Y-%m-%dT%H:%M:%S')

    old_tz = pytz.timezone("UTC")
    new_tz = pytz.timezone(timezone)
    dt_new_tz = old_tz.localize(dt_utc).astimezone(new_tz)
    return dt_new_tz

# Function to return the timestamp in human readable format; eg. Sun, 21 Apr 2024, 15:08:45
def get_cur_ts(ts_str=""):
    return (str(ts_str) + str(calendar.day_abbr[(datetime.fromtimestamp(int(time.time()))).weekday()]) + ", " + str(datetime.fromtimestamp(int(time.time())).strftime("%d %b %Y, %H:%M:%S")))

# Function to print the current timestamp in human readable format; eg. Sun, 21 Apr 2024, 15:08:45
def print_cur_ts(ts_str=""):
    print(get_cur_ts(str(ts_str)))
    print("-----------------------------------------------------------------------------------")

# Function to return the timestamp in human readable format (long version); eg. Sun, 21 Apr 2024, 15:08:45
def get_date_from_ts(ts):
    return (str(calendar.day_abbr[(datetime.fromtimestamp(ts)).weekday()]) + " " + str(datetime.fromtimestamp(ts).strftime("%d %b %Y, %H:%M:%S")))

# Function to return the timestamp in human readable format (short version); eg. Sun 21 Apr 15:08
def get_short_date_from_ts(ts):
    return (str(calendar.day_abbr[(datetime.fromtimestamp(ts)).weekday()]) + " " + str(datetime.fromtimestamp(ts).strftime("%d %b %H:%M")))

# Function to return the timestamp in human readable format (only hour, minutes and optionally seconds): eg. 15:08:12
def get_hour_min_from_ts(ts,show_seconds=False):
    if show_seconds:
        out_strf="%H:%M:%S"
    else:
        out_strf="%H:%M"
    return (str(datetime.fromtimestamp(ts).strftime(out_strf)))

# Function to return the range between two timestamps; eg. Sun 21 Apr 14:09 - 14:15
def get_range_of_dates_from_tss(ts1,ts2,between_sep=" - ", short=False):
    ts1_strf=datetime.fromtimestamp(ts1).strftime("%Y%m%d")
    ts2_strf=datetime.fromtimestamp(ts2).strftime("%Y%m%d")

    if ts1_strf == ts2_strf:
        if short:
            out_str=get_short_date_from_ts(ts1) + between_sep + get_hour_min_from_ts(ts2)
        else:
            out_str=get_date_from_ts(ts1) + between_sep + get_hour_min_from_ts(ts2,show_seconds=True)
    else:
        if short:
            out_str=get_short_date_from_ts(ts1) + between_sep + get_short_date_from_ts(ts2)
        else:
            out_str=get_date_from_ts(ts1) + between_sep + get_date_from_ts(ts2)       
    return (str(out_str))

# Signal handler for SIGUSR1 allowing to switch game playing status changes email notifications
def toggle_status_changes_notifications_signal_handler(sig, frame):
    global status_notification
    status_notification=not status_notification
    sig_name=signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [status changes = " + str(status_notification) + "]")
    print_cur_ts("Timestamp:\t\t")

# Signal handler for SIGTRAP allowing to increase check timer for player activity when user is in game by LOL_ACTIVE_CHECK_SIGNAL_VALUE seconds
def increase_active_check_signal_handler(sig, frame):
    global LOL_ACTIVE_CHECK_INTERVAL
    LOL_ACTIVE_CHECK_INTERVAL=LOL_ACTIVE_CHECK_INTERVAL+LOL_ACTIVE_CHECK_SIGNAL_VALUE
    sig_name=signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print("* LoL timers: [active check interval: " + display_time(LOL_ACTIVE_CHECK_INTERVAL) + "]")
    print_cur_ts("Timestamp:\t\t")

# Signal handler for SIGABRT allowing to decrease check timer for player activity when user is in game by LOL_ACTIVE_CHECK_SIGNAL_VALUE seconds
def decrease_active_check_signal_handler(sig, frame):
    global LOL_ACTIVE_CHECK_INTERVAL
    if LOL_ACTIVE_CHECK_INTERVAL-LOL_ACTIVE_CHECK_SIGNAL_VALUE>0:
        LOL_ACTIVE_CHECK_INTERVAL=LOL_ACTIVE_CHECK_INTERVAL-LOL_ACTIVE_CHECK_SIGNAL_VALUE
    sig_name=signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print("* LoL timers: [active check interval: " + display_time(LOL_ACTIVE_CHECK_INTERVAL) + "]")
    print_cur_ts("Timestamp:\t\t")

# Function checking if player is currently in game
def is_user_in_match(username: str, region: str):
    cassiopeia.configuration.settings.expire_sinks()
    cassiopeia.configuration.settings.clear_sinks()
    summoner = cassiopeia.get_summoner(name=username, region=region)
    try:
        match = summoner.current_match
        if match:
            return True
        else:
            return False
    except Exception as e:
        print("is_user_in_match() error:",e)
        return False

# Function printing details of the current player's match (user is in game)
def print_current_match(username: str, region: str, last_match_stop_ts: int):
    summoner = cassiopeia.get_summoner(name=username, region=region)

    match = summoner.current_match

    if match:

        match_creation=convert_utc_str_to_tz_datetime(str(match.creation),LOCAL_TIMEZONE)
        match_creation_ts=int(match_creation.timestamp())
        if match_creation_ts<1000000000:
            match_creation=datetime.fromtimestamp(int(time.time()))
            match_creation_str=get_cur_ts("")
        else:
            match_creation=datetime.fromtimestamp(int(match_creation_ts))
            match_creation_str=get_date_from_ts(int(match_creation_ts))
        match_duration_ts=int(match.duration.total_seconds())

        print("*** LoL user " + username + " is in game now (after " + calculate_timespan(match_creation,int(last_match_stop_ts)) + ")\n")

        print("User played last time:\t" + get_date_from_ts(last_match_stop_ts) + "\n")

        print("Match ID:\t\t" + str(match.id))

        print("\nMatch creation date:\t" + str(match_creation_str))
        if match_duration_ts > 0:
            print("Match duration:\t\t" + display_time(int(match.duration.total_seconds())))
        else:
            print("Match duration:\t\tjust starting ...")
            match_duration_ts=0

        p = match.participants[summoner]
        print("\nChampion:\t\t" + str(p.champion.name))
        print("Map:\t\t\t" + str(match.map.name))

        blue_team=[]
        print("\nBLUE team:")
        for mp in match.blue_team.participants:
            try:
                print("-",str(mp.summoner.name))
                blue_team.append(mp.summoner.name)
            except Exception as e:
                # Workaround for recent RIOT API changes not reflected in Cassiopeia yet
                if 'object has already been loaded':
                    print("-",str(username))
                    blue_team.append(str(username))
                else:
                    print("- (error getting summoner name in match - " + str(e) + ")")
                    blue_team.append("")
                continue                
        print()

        red_team=[]
        print("RED team:")
        for mp in match.red_team.participants:
            try:
                print("-",str(mp.summoner.name))
                red_team.append(mp.summoner.name)
            except Exception as e:
                # Workaround for recent RIOT API changes not reflected in Cassiopeia yet
                if 'object has already been loaded':
                    print("-",str(username))
                    red_team.append(str(username))
                else:
                    print("- (error getting summoner name in match - " + str(e) + ")")
                    red_team.append("")
                continue                
        print()

        return match_creation_ts, match_creation, match_creation_str, blue_team, red_team, match_duration_ts
    else:
        print("User is not in game currently")
        return int(time.time()), datetime.fromtimestamp(int(time.time())), "", [], [], 0

# Functioning printing history of matches with relevant details
def print_match_history(username: str, region: str, matches_num: int, status_notification_flag, csv_file_name):
    summoner = cassiopeia.get_summoner(name=username, region=region)
    matches_history = summoner.match_history
    match_start_ts = 0
    match_stop_ts = 0

    for i in reversed(range(matches_num)):
        match = matches_history[i]
        match_creation=convert_utc_str_to_tz_datetime(str(match.creation),LOCAL_TIMEZONE)
        match_start=convert_utc_str_to_tz_datetime(str(match.start),LOCAL_TIMEZONE)
        match_start_ts=int(match_start.timestamp())
        match_start=datetime.fromtimestamp(int(match_start_ts))
        match_stop_ts=match_start_ts+int(match.duration.total_seconds())
        match_stop=datetime.fromtimestamp(int(match_stop_ts))
        print("Match ID:\t\t" + str(match.id))
        print(f"\nMatch start-end date:\t" + get_range_of_dates_from_tss(match_start_ts,match_stop_ts))
        print("Match duration:\t\t" + display_time(int(match.duration.total_seconds())))
        last_played=calculate_timespan(int(time.time()), match_stop_ts)       
        if i==0:
            print(f"\nUser played last time:\t{last_played} ago")

        p = match.participants[summoner]
        # Below code to overcome bug with iteration when accessing multiple times
        u_victory=p.team.win
        u_champion=p.champion.name
        u_kills=p.stats.kills
        u_deaths=p.stats.deaths
        u_assists=p.stats.assists
        u_level=p.stats.level
        print("\nVictory:\t\t" + str(u_victory))
        print("Champion:\t\t" + str(u_champion))
        print(f"Kills/Deaths/Assists:\t{u_kills}/{u_deaths}/{u_assists}")
        print("Level:\t\t\t" + str(u_level))
        print("Map:\t\t\t" + str(match.map.name))

        blue_team=[]
        print("\nBLUE team:")
        for mp in match.blue_team.participants:
            try:
                print("-",str(mp.summoner.name))
                blue_team.append(mp.summoner.name)
            except Exception as e:
                # Workaround for recent RIOT API changes not reflected in Cassiopeia yet
                if 'object has already been loaded':
                    print("-",str(username))
                    blue_team.append(str(username))
                else:
                    print("- (error getting summoner name in match - " + str(e) + ")")
                    blue_team.append("")
                continue
        print()
        blue_team_str=" ".join(f"'{x}'" for x in blue_team)

        red_team=[]
        print("RED team:")
        for mp in match.red_team.participants:
            try:
                print("-",str(mp.summoner.name))
                red_team.append(mp.summoner.name)
            except Exception as e:
                # Workaround for recent RIOT API changes not reflected in Cassiopeia yet
                if 'object has already been loaded':
                    print("-",str(username))
                    red_team.append(str(username))
                else:
                    print("- (error getting summoner name in match - " + str(e) + ")")
                    red_team.append("")
                continue
        red_team_str=" ".join(f"'{x}'" for x in red_team)

        try:
            if csv_file_name:
                 write_csv_entry(csv_file_name, match_start, match_stop, display_time(int(match.duration.total_seconds())), u_victory, u_kills, u_deaths, u_assists, u_champion, blue_team_str, red_team_str)
        except Exception as e:
            print("* Cannot write CSV entry -", e)

        if status_notification_flag and i==0:
            m_subject="LoL user " + username + " match summary (" + get_range_of_dates_from_tss(match_start_ts,match_stop_ts,short=True) + ", " + display_time(int(match.duration.total_seconds()),granularity=1) + ", " + str(u_victory) + ")"
            m_body="LoL user " + username + " last match summary\n\nMatch ID: " + str(match.id) + "\n\nMatch start-end date: " + get_range_of_dates_from_tss(match_start_ts,match_stop_ts) + "\nMatch duration: " + display_time(int(match.duration.total_seconds())) + "\n\nVictory: " + str(u_victory) + "\nChampion: " + str(u_champion) + "\nKills/deaths/assists: " + str(u_kills) + "/" + str(u_deaths) + "/" + str(u_assists) + "\nLevel: " + str(u_level) + "\nMap: " + str(match.map.name) + "\n\nBlue team: " + blue_team_str + "\n\nRed team: " + red_team_str + get_cur_ts("\n\nTimestamp: ")
            print("Sending email notification to",RECEIVER_EMAIL)
            send_email(m_subject,m_body,"",SMTP_SSL)

        if matches_num>1:
            print("-----------------------------------------------------------------------------------")
    return match_start_ts, match_stop_ts

# Main function monitoring gaming activity of the specified LoL user
def lol_monitor_user(username, region, error_notification, csv_file_name, csv_exists):

    alive_counter = 0
    last_match_start_ts = 0
    last_match_stop_ts = 0
    csvwriter = None   

    try:
        if csv_file_name:
            csv_file=open(csv_file_name, 'a', newline='', buffering=1)
            csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
            if not csv_exists:
                csvwriter.writeheader()
            csv_file.close()
    except Exception as e:
        print("* Error -", e)
  
    summoner = cassiopeia.get_summoner(name=username, region=region)

    print("Summoner name:\t\t" + str(summoner.name))
    #print("Summoner ID:\t\t" + str(summoner.id))
    #print("Summoner account ID:\t" + str(summoner.account_id))
    print("Summoner level:\t\t" + str(summoner.level))
    print("Summoner region:\t" + str(summoner.region))
    print()

    print("User last played match:\n")
    try:
        last_match_start_ts,last_match_stop_ts=print_match_history(username, region, 1, False, None)
    except Exception as e:
        if 'Forbidden' in str(e) or 'Unknown patch name' in str(e):
            print("* API key might not be valid anymore or new patch deployed!")
        print("* Error -", e)
    last_match_start_ts_old=last_match_start_ts
    ingame=False
    ingameold=False
    gamefinished=False
    alive_counter = 0

    print_cur_ts("\nTimestamp:\t\t")

    while True:

        # Sometimes is_user_in_match() can halt, so to overcome this we use alarm signal functionality to kill it inevitably
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(FUNCTION_TIMEOUT)
        try:
            ingame=is_user_in_match(username, region)
            signal.alarm(0)
        except TimeoutException:
            signal.alarm(0)
            print("is_user_in_match() timeout, retrying in", display_time(FUNCTION_TIMEOUT))
            print_cur_ts("Timestamp:\t\t")
            time.sleep(FUNCTION_TIMEOUT)           
            continue   
        except Exception as e:
            signal.alarm(0)
            print("Retrying in", display_time(LOL_CHECK_INTERVAL), ", error -", e)
            print_cur_ts("Timestamp:\t\t")
            time.sleep(LOL_CHECK_INTERVAL)         
            continue

        try:
            # User is playing new match
            if ingame != ingameold:
                if ingame:

                    current_match_creation_ts, current_match_creation, current_match_creation_str, current_blue_team, current_red_team, current_match_duration_ts=print_current_match(username, region, last_match_stop_ts)

                    current_blue_team_str=" ".join(f"'{x}'" for x in current_blue_team)
                    current_red_team_str=" ".join(f"'{x}'" for x in current_red_team)
                    if current_match_duration_ts > 0:
                        current_match_duration=display_time(current_match_duration_ts)
                    else:
                        current_match_duration="just starting ..."
                    m_subject="LoL user " + username + " is in game now (after " + calculate_timespan(current_match_creation,int(last_match_stop_ts),show_seconds=False) + " - " + get_short_date_from_ts(last_match_stop_ts) + ")"
                    m_body="LoL user " + username + " is in game now (after " + calculate_timespan(current_match_creation,int(last_match_stop_ts)) + ")\n\nUser played last time: " + get_date_from_ts(last_match_stop_ts) + "\n\nMatch creation date: " + str(current_match_creation_str) + "\n\nMatch duration: " + current_match_duration + "\n\nBlue team: " + current_blue_team_str + "\n\nRed team: " + current_red_team_str + get_cur_ts("\n\nTimestamp: ")
                    gamefinished=False
                else:
                    print("*** LoL user",username,"stopped playing !")
                    m_subject="LoL user " + username + " stopped playing"
                    m_body="LoL user " + username + " stopped playing" + get_cur_ts("\n\nTimestamp: ")
                    gamefinished=True

                if status_notification:
                    print("Sending email notification to",RECEIVER_EMAIL)
                    send_email(m_subject,m_body,"",SMTP_SSL)

                print_cur_ts("\nTimestamp:\t\t")

            ingameold=ingame
            alive_counter+=1

            # User finished playing the match
            if gamefinished:
                time.sleep(LOL_GAME_FINISHED_CHECK_INTERVAL)
                print("*** Getting details of last played match for",username,"...\n")
                cassiopeia.configuration.settings.expire_sinks()
                cassiopeia.configuration.settings.clear_sinks()
                summoner = cassiopeia.get_summoner(name=username, region=region)
                last_match = summoner.match_history[0]
                last_match_start=convert_utc_str_to_tz_datetime(str(last_match.start),LOCAL_TIMEZONE)
                last_match_start_ts=int(last_match_start.timestamp())
                last_match_start=datetime.fromtimestamp(int(last_match_start_ts))
 
                if last_match_start_ts != last_match_start_ts_old:
                    last_match_stop_ts=last_match_start_ts+int(last_match.duration.total_seconds())

                    print("User last played match:\n")
                    last_match_start_ts,last_match_stop_ts=print_match_history(username, region, 1, status_notification, csv_file_name)
                    last_match_start_ts_old=last_match_start_ts

                gamefinished=False
                ingame=False
                ingameold=False
                print_cur_ts("\nTimestamp:\t\t")
                continue

            if ingame:
                time.sleep(LOL_ACTIVE_CHECK_INTERVAL)
            else:
                time.sleep(LOL_CHECK_INTERVAL)

            if alive_counter >= TOOL_ALIVE_COUNTER:
                print_cur_ts("Alive check, timestamp: ")
                alive_counter = 0
        except Exception as e:
            print("Retrying in", display_time(LOL_CHECK_INTERVAL), ", error -", e)
            if 'Forbidden' in str(e) or 'Unknown patch name' in str(e):
                if gamefinished:
                    gamefinished=False
                print("* API key might not be valid anymore or new patch deployed!")
                if error_notification:
                    m_subject="lol_monitor: API key error! (user: " + str(username) + ")"
                    m_body="API key might not be valid anymore or new patch deployed: " + str(e) + get_cur_ts("\n\nTimestamp: ")
                    print("Sending email notification to",RECEIVER_EMAIL)
                    send_email(m_subject,m_body,"",SMTP_SSL)
            print_cur_ts("Timestamp:\t\t")
            time.sleep(LOL_CHECK_INTERVAL)
            continue

if __name__ == "__main__":

    stdout_bck = sys.stdout

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        os.system('clear')
    except:
        print("* Cannot clear the screen contents")

    print("League of Legends Monitoring Tool",VERSION,"\n")

    parser = argparse.ArgumentParser("lol_monitor")
    parser.add_argument("username", nargs="?", help="User's LoL username", type=str)
    parser.add_argument("region", nargs="?", help="User's LoL region", type=str)
    parser.add_argument("-l","--list_recent_matches", help="List recent matches for the user", action='store_true')
    parser.add_argument("-n", "--number_of_recent_matches", help="Number of recent matches to display if used with -l", type=int)
    parser.add_argument("-b", "--csv_file", help="Write all game playing status changes to CSV file", type=str, metavar="CSV_FILENAME")
    parser.add_argument("-s","--status_notification", help="Send email notification once user changes game playing status", action='store_true')
    parser.add_argument("-e","--error_notification", help="Disable sending email notifications in case of errors like invalid API key", action='store_false')
    parser.add_argument("-c", "--check_interval", help="Time between monitoring checks if user is not in game, in seconds", type=int)
    parser.add_argument("-k", "--active_check_interval", help="Time between monitoring checks if user is in game, in seconds", type=int)
    parser.add_argument("-d", "--disable_logging", help="Disable logging to file 'lol_monitor_user.log' file", action='store_true')
    parser.add_argument("-r", "--riot_api_key", help="Specify RIOT API key if not defined within the script", type=str)
    args = parser.parse_args()

    if not args.username or not args.region:
        print("* username and region arguments are required")
        sys.exit(1)

    sys.stdout.write("* Checking internet connectivity ... ")
    sys.stdout.flush()
    check_internet()
    print("")

    if args.check_interval:
        LOL_CHECK_INTERVAL=args.check_interval
        TOOL_ALIVE_COUNTER=TOOL_ALIVE_INTERVAL/LOL_CHECK_INTERVAL

    if args.active_check_interval:
        LOL_ACTIVE_CHECK_INTERVAL=args.active_check_interval

    if args.riot_api_key:
        RIOT_API_KEY=args.riot_api_key

    cassiopeia.apply_settings(CASSIOPEIA_SETTINGS_JSON_FILE)

    cassiopeia.set_riot_api_key(RIOT_API_KEY)

    if args.list_recent_matches:
        if args.number_of_recent_matches and args.number_of_recent_matches>0:
            matches_n=args.number_of_recent_matches
        else:
            matches_n=2
        print("* Listing " + str(matches_n) + " recent matches for " + str(args.username) + ":\n")
        try:
            print_match_history(args.username, args.region, matches_n, False, None)
        except Exception as e:                     
            if 'Forbidden' in str(e) or 'Unknown patch name' in str(e):
                print("* API key might not be valid anymore or new patch deployed!")
            print("* Error -", e)
        sys.exit(0)

    if args.csv_file:
        csv_enabled=True
        csv_exists=os.path.isfile(args.csv_file)
        try:
            csv_file=open(args.csv_file, 'a', newline='', buffering=1)
        except Exception as e:
            print("\n* Error, CSV file cannot be opened for writing -", e)
            sys.exit(1)
        csv_file.close()
    else:
        csv_enabled=False
        csv_file=None
        csv_exists=False

    if not args.disable_logging:
        lol_logfile = lol_logfile + "_" + str(args.username) + ".log"
        sys.stdout = Logger(lol_logfile)

    status_notification=args.status_notification

    print("* LoL timers: [check interval: " + display_time(LOL_CHECK_INTERVAL) + "] [active check interval: " + display_time(LOL_ACTIVE_CHECK_INTERVAL) + "]")
    print("* Email notifications: [status changes = " + str(status_notification) + "] [errors = " + str(args.error_notification) + "]")
    print("* Output logging disabled:",str(args.disable_logging))
    print("* CSV logging enabled:",str(csv_enabled),"\n")

    signal.signal(signal.SIGUSR1, toggle_status_changes_notifications_signal_handler)
    signal.signal(signal.SIGTRAP, increase_active_check_signal_handler)
    signal.signal(signal.SIGABRT, decrease_active_check_signal_handler)

    lol_monitor_user(args.username,args.region,args.error_notification,args.csv_file,csv_exists)

    sys.stdout = stdout_bck
    sys.exit(0)

