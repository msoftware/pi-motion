#!/bin/sh


# Screen is a full-screen window manager
apt-get install screen

# JSON on the command line with jq
apt-get install jq

# A Portable Foreign Function Interface Library
apt-get install libffi-dev

# Other dependencies needed for python-telegram-bot python lib
apt-get install build-essential libssl-dev libffi-dev python-dev

echo Install python package "configparser"
pip install configparser

echo Install python package "psutil"
pip install psutil

echo Install python package "qhue"
pip install qhue

echo Install python package "telegram bot"
pip install python-telegram-bot
