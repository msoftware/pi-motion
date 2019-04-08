#!/bin/sh

echo "4" > /sys/class/gpio/export
echo "in" > /sys/class/gpio/gpio4/direction

while :
do
    DATE=`date $s`
    VALUE=`cat /sys/class/gpio/gpio4/value`
    if [ $VALUE -eq "1" ];
    then
        echo $DATE Motion detected
    else
        echo $DATE No motion detected
    fi
    sleep 0.1
done
