#!/bin/sh

if [ ! -f installed.pttp ]; then
  sudo ./PTTP_Setup.sh
fi
cd wallet
perl wallet.cgi
cd ..
