#!/bin/sh

exists() {
  command -v "$1" >/dev/null 2>&1
}

if exists perl; then
  pm='apt'; upd='update'; inst='install'
  if exists pacman; then pm='pacman'; upd='-Syu'; inst='-S'; fi
  if exists dnf; then pm='dnf'; upd='upgrade'; fi
  if exists zypper; then pm='zypper'; fi
  if exists emerge; then pm='emerge'; upd='-u world'; inst='-a'; fi
  echo Package manager: $pm
  echo Updating repository ..
  cmd="$pm $upd"; eval $cmd
  echo Installing compiler ..
  cmd="$pm $inst gcc"; eval $cmd
  cmd="$pm $inst make"; eval $cmd
  echo Installing tar ..
  cmd="$pm $inst tar"; eval $cmd
  echo Installing zlib ..
  cd install
  tar xzf zlib-1.2.11.tar.gz
  cd zlib-1.2.11
  ./configure
  make
  make install
  cd ..
  echo Installing dependencies for Perl .. 
  cpan install Time::HiRes JSON Crypt::Ed25519 URL::Encode Browser::Open Gzip::Faster Digest::SHA1
  perl install.cgi
  cd ..
  echo -e "\n\n"
  echo PTTP is succesfully installed.
  echo Doubleclick 'PTTP_Wallet' to create your first wallet.
  echo 1 > installed.pttp
  if $1 != 1; then    
    read -p "Press any key to continue... " -n1 -s
  fi
else
  echo Please install Perl first
  read -p "Press any key to continue... " -n1 -s
fi
echo -e "\n"

