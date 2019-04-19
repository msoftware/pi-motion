#!/bin/sh
#set -x

IP=`curl -s https://www.meethue.com/api/nupnp | jq '.[0].internalipaddress' | sed 's/"//g'`

while :
do
    echo "Get HUE Username ..."
    RESPONSE=`curl -s -H "Accept: application/json" -X POST --data '{"devicetype":"PI-Motion"}' "http://$IP/api"`
    if [ `echo $RESPONSE | grep -c "success" ` -gt 0 ]
    then
       echo Success
       echo #######
       echo
       echo "IP Address:"
       echo $IP
       echo
       echo "Username:"
       USER=`echo $RESPONSE | jq '.[0].success.username' | sed 's/"//g'`
       echo $USER
       curl -s http://$IP/api/$USER | jq '.lights' > hue-lamps.txt
       echo
       echo "Find lamps info in hue-lamps.txt"
       exit 0
    else
        echo "Fail: Press the hue bridge link button!";
    fi
    sleep 1
    echo 
    echo "Try again"
    echo 
    sleep 1
done



