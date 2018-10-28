#!/usr/bin/perl

print <<EOT;

Welcome to

  PPPPP   TTTTTTT  TTTTTTT   PPPPP
  P    P     T        T      P    P     Power to the People Coin v1.21
  PPPPP      T        T      PPPPP
  P          T        T      P                  INSTALLATION
  P          T        T      P

EOT

my $revslash=0;
my $cmd;
my $source="modules/*";
my $target; 

print "Your operating system: ";
if ($^O eq 'MSWin32') {
  print "Windows\n"; $cmd="xcopy /S /Y /R"; $revslash=1; $source.='.*'
} elsif ($^O eq 'linux') {
  print "Linux\n"; $cmd="yes | cp -rfv"
} elsif ($^O eq 'MacOS') {
  print "Macintosh\n"; $cmd="cp -Rfv"
} else {
  print "$^O\n"
}

print "Target directory: ";

sub search {
  my ($goal) = @_;
  my $numinc=$#INC; my $i=0; my $ofs=-length($goal);
  while (!$target && ($i<=$numinc)) {
    my $inc=$INC[$i]; $i++; $inc =~ s/\\/\//g;
    if (lc(substr($inc,$ofs)) eq lc($goal)) { $target=$inc }
  }
}

search('/site/lib');
if (!$target) { search('/lib') }
if (!$target) { $target=$INC[0] }
print "$target\n";
if ($revslash) { $target =~ s/\//\\/g; $source =~ s/\//\\/g }

if (!$cmd) {
  print "Your operating system is not supported by default\nPlease copy all files recursively from $source to $target manually.\n\n"; exit
}

print "Copying files:\n";
system "$cmd $source $target";
print "\nDone.\n\n"

# EOF PTTP install (Chaosje 2018)