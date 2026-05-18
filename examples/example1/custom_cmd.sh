#!/usr/bin/env sh
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 ENTRY1 ENTRY2"
    exit 1
fi
echo $RANDOM > $1.txt
echo $RANDOM > $2.txt