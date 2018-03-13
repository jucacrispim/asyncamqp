#!/bin/bash

flakes=`pyflakes "$@"`

if [ "$flakes" != "" ]
then
    echo "\nYou need to look at something...\n"
    echo "$flakes"
    exit 1;
else
    echo "Uhu!! Nothing to complain about!"
    exit 0;
fi
