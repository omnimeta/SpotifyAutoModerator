#!/bin/sh

py setup4win.py py2exe
mv dist/main.exe dist/
cp -r data/ dist/data

if [ ! -d dist/data/backups ]; then
  mkdir dist/data/backups
fi

if [ ! -d dist/data/logs ]; then
  mkdir dist/data/logs
fi

if [ -d dist/data/test ]; then
  rm -r dist/data/test
fi

mv dist spautomod4win
