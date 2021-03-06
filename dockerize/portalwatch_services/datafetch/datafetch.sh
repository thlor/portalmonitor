#!/bin/bash

#initially kill running processes
pkill  -f DataFetch

DATE=`date +%Y-%m-%d`
week=`date +"%y%V"`
echo "Writting logs to $LOGS for week $week"

PORTALS=("data_gv_at" "www_opendataportal_at")

for pName in "${PORTALS[@]}"
do
    LOGF=data-fetch_"$pName"_$week
    SCRIPT="odpw -c $ADEQUATE/portalmonitor.conf DataFetch -p $pName "
    cmd="$SCRIPT 1>> $LOGS/$LOGF.out 2> $LOGS/$LOGF.err"
    echo $cmd
    eval $cmd
    gzip $LOGS/$LOGF.*
done
