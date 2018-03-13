#!/bin/bash

flake=`flake8 asyncamqp tests`;


if [ "$flake" != "" ]
then
    echo "#### Ops! some thing went WRONG! ####";
    echo "$flake";
    exit 1
else
    echo "hell yeah! nice code, mate.";
    exit 0;
fi
