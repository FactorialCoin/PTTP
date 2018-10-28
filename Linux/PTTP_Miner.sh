#!/bin/sh

if [ ! -f installed.pttp ]; then
  sudo ./PTTP_Setup.sh
fi
cd miner
perl pttpminer.cgi
cd ..
