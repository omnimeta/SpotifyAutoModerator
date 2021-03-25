#!/bin/sh

py setup4win.py py2exe
mv dist/main.exe dist/spautomod.exe
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
if [ -d dist/data/images ]; then
  rm -r dist/data/images
fi

mv dist spautomod4win
echo 'Start-Process -FilePath "spautomod.exe" -ArgumentList "--loop" -Wait -WindowStyle Maximized' > spautomod4win/spautomod-loop.ps1
