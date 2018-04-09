#!/bin/bash

SENDER=$1
ROOM=$2

curl -N "http://localhost:8888/room/$ROOM?format=shell" -o - &
CURLPID=$!

trap ctrl_c INT

function ctrl_c() {
    echo "** Trapped CTRL-C killing bkgd curl"
    kill -HUP "$CURLPID"
    exit
}

echo -n "> "
while read line
do
    curl -X POST  "http://localhost:8888/room/$ROOM" -d "format=shell&message=<$SENDER>: $line"
    echo
    echo -n "$SENDER >> "
done <&0 

kill -HUP "$CURLPID"
