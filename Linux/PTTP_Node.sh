#!/bin/sh

if [ ! -f installed.pttp ]; then
  sudo ./PTTP_Setup.sh
fi
cd node
perl startnode.cgi
cd ..
