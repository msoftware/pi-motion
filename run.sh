#!/bin/sh

screen -dmS pir bash
screen -S pir -p 0 -X exec "./main.sh"
