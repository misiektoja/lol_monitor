# lol_monitor

lol_monitor is a tool that allows for real-time monitoring of LoL (League of Legends) players' activities. 

## Features

- Real-time tracking of LoL users' gaming activity (including detection when a user starts or finishes a match)
- Most important statistics for finished matches:
  - game mode
  - victory or defeat
  - kills, deaths, assists
  - champion name
  - achieved level
  - role
  - lane
  - team members
- Email notifications for different events (player starts or finishes a match, match summary, errors)
- Saving all gaming activities with timestamps to a CSV file
- Possibility to control the running copy of the script via signals

<p align="center">
   <img src="./assets/lol_monitor.png" alt="lol_monitor_screenshot" width="70%"/>
</p>

## Change Log

Release notes can be found [here](RELEASE_NOTES.md)

## Requirements

The tool requires Python 3.12 or higher.

It uses [pulsefire](https://github.com/iann838/pulsefire) library, also requests and python-dateutil.

It has been tested successfully on:
- macOS (Ventura, Sonoma & Sequoia)
- Linux:
   - Raspberry Pi OS (Bullseye & Bookworm)
   - Ubuntu 24
   - Rocky Linux (8.x, 9.x)
   - Kali Linux (2024, 2025)
- Windows (10 & 11)

It should work on other versions of macOS, Linux, Unix and Windows as well.

## Installation

Install the required Python packages:

```sh
python3 -m pip install requests python-dateutil pulsefire
```

Or from requirements.txt:

```sh
pip3 install -r requirements.txt
```

Copy the *[lol_monitor.py](lol_monitor.py)* file to the desired location. 

You might want to add executable rights if on Linux/Unix/macOS:

```sh
chmod a+x lol_monitor.py
```

## Configuration

Edit the *[lol_monitor.py](lol_monitor.py)* file and change any desired configuration variables in the marked **CONFIGURATION SECTION** (all parameters have detailed description in the comments).

### Riot API key

You can get the development Riot API key valid for 24 hours here: [https://developer.riotgames.com](https://developer.riotgames.com)

However it is recommended to apply for persistent personal or production Riot API key here: [https://developer.riotgames.com/app-type](https://developer.riotgames.com/app-type)

It takes few days to get the approval.

Change the `RIOT_API_KEY` variable to the respective value (or use **-r** parameter).

### SMTP settings

If you want to use email notifications functionality you need to change the SMTP settings (host, port, user, password, sender, recipient) in the *[lol_monitor.py](lol_monitor.py)* file. If you leave the default settings then no notifications will be sent.

You can verify if your SMTP settings are correct by using **-z** parameter (the tool will try to send a test email notification):

```sh
./lol_monitor.py -z
```

### Other settings

All other variables can be left at their defaults, but feel free to experiment with it.

## Getting started

### List of supported parameters

To get the list of all supported parameters:

```sh
./lol_monitor.py -h
```

or 

```sh
python3 ./lol_monitor.py -h
```

### Monitoring mode

To monitor specific user activity, just type player's LoL Riot ID & region as parameters (**lol_user_id#EUNE** and **eun1** in the example below):

```sh
./lol_monitor.py "lol_user_id#EUNE" eun1
```

If you have not changed`RIOT_API_KEY` variable in the *[lol_monitor.py](lol_monitor.py)* file, you can use **-r** parameter:

```sh
./lol_monitor.py "lol_user_id#EUNE" eun1 -r "your_riot_api_key"
```

LoL Riot ID consists of Riot ID game name (*lol_user_id* in the example above) and tag line (*#EUNE*). 

For the region you need to use the short form of it. You can find a list below:

| Region short form | Description |
| ----------- | ----------- |
| eun1 | Europe Nordic & East (EUNE) |
| euw1 | Europe West (EUW) |
| na1 | North America (NA) |
| na2 | North America (NA) |
| br1 | Brazil (BR) |
| la1 | Latin America North (LAN) |
| la2 | Latin America South (LAS) |
| jp1 | Japan |
| kr | Korea |
| tr1 | Turkey (TR1) |
| ru | Russia |
| ph2 | The Philippines |
| sg2 | Singapore, Malaysia, & Indonesia |
| tw2 | Taiwan, Hong Kong, and Macao |
| th2 | Thailand |
| vn2 | Vietnam |
| oc1 | Oceania |

The tool will run indefinitely and monitor the player until the script is interrupted (Ctrl+C) or terminated in another way.

You can monitor multiple LoL players by running multiple instances of the script.

It is recommended to use something like **tmux** or **screen** to keep the script running after you log out from the server (unless you are running it on your desktop).

The tool automatically saves its output to *lol_monitor_{riotid_name}.log* file (can be changed in the settings via `LOL_LOGFILE` variable or disabled completely with **-d** parameter).

### Listing mode

There is also another mode of the tool which prints and/or saves the recent matches for the user (**-l** parameter). You can also add **-n** to define how many recent matches you want to display/save; by default, it shows the last 2 matches:

```sh
./lol_monitor.py "lol_user_id#EUNE" eun1 -l -n 25
```

You can also define the range of matches to display/save by specifying the minimal match to display (**-m** parameter). So for example, to display recent matches in the range of 20-50:

```sh
./lol_monitor.py "lol_user_id#EUNE" eun1 -l -m 20 -n 50
```

If you specify the **-b** parameter (with a CSV file name) together with the **-l** parameter, it will not only display the recent matches, but also save them to the specified CSV file. For example, to display and save recent matches in the range of 5-10 for the user:

```sh
./lol_monitor.py "lol_user_id#EUNE" eun1 -l -m 5 -n 10 -b lol_games_lol_user_id.csv
```

You can use the **-l** functionality regardless if the monitoring is used or not (it does not interfere). 

## How to use other features

### Email notifications

If you want to receive email notifications when the user starts or finishes the match, use the **-s** parameter.

```sh
./lol_monitor.py "lol_user_id#EUNE" eun1 -s
```

Make sure you defined your SMTP settings earlier (see [SMTP settings](#smtp-settings)).

Example email:

<p align="center">
   <img src="./assets/lol_monitor_email_notifications.png" alt="lol_monitor_email_notifications" width="80%"/>
</p>

### Saving gaming activity to the CSV file

If you want to save the gaming activity of the LoL user, use **-b** parameter with the name of the file (it will be automatically created if it does not exist):

```sh
./lol_monitor.py "lol_user_id#EUNE" eun1 -b lol_games_lol_user_id.csv
```

### Check intervals

If you want to change the check interval when the user is in game to 60 seconds, use **-k** parameter and when the user is NOT in game to 2 mins (120 seconds), use **-c** parameter:

```sh
./lol_monitor.py "lol_user_id#EUNE" eun1 -k 60 -c 120
```

### Controlling the script via signals (only macOS/Linux/Unix)

The tool has several signal handlers implemented which allow to change behavior of the tool without a need to restart it with new parameters.

List of supported signals:

| Signal | Description |
| ----------- | ----------- |
| USR1 | Toggle email notifications when user starts/finishes the match (-s) |
| TRAP | Increase the check timer for player activity when user is in game (by 30 seconds) |
| ABRT | Decrease check timer for player activity when user is in game (by 30 seconds) |

So if you want to change functionality of the running tool, just send the proper signal to the desired copy of the script.

I personally use **pkill** tool, so for example to toggle email notifications when user starts/finishes playing the game, for the tool instance monitoring the *lol_user_id* user:

```sh
pkill -f -USR1 "python3 ./lol_monitor.py lol_user_id"
```

As Windows supports limited number of signals, this functionality is available only on Linux/Unix/macOS.

### Other

Check other supported parameters using **-h**.

You can combine all the parameters mentioned earlier in monitoring mode (listing mode only supports **-l**, **-n**, **-m** and **-b**).

## Coloring log output with GRC

If you use [GRC](https://github.com/garabik/grc) and want to have the tool's log output properly colored you can use the configuration file available [here](grc/conf.monitor_logs)

Change your grc configuration (typically *.grc/grc.conf*) and add this part:

```
# monitoring log file
.*_monitor_.*\.log
conf.monitor_logs
```

Now copy the *conf.monitor_logs* to your *.grc* directory and lol_monitor log files should be nicely colored when using *grc* tool.

## License

This project is licensed under the GPLv3 - see the [LICENSE](LICENSE) file for details
