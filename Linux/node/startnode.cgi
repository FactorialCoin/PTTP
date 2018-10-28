#!/usr/bin/perl

$SIG{'INT'}=\&intquit;

sub intquit {
  exit
}

do {
  system "perl node.cgi"
} until (0)