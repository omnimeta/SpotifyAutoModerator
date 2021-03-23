#!/bin/sh

pip3 install -r requirements.txt

if [ ! -d data/backups ]; then
  mkdir data/backups
fi

if [ ! -d data/logs ]; then
  mkdir data/logs
fi
