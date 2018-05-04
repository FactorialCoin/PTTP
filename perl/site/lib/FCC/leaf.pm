#!/usr/bin/perl

package FCC::leaf;

#############################################################
#                                                           #
#     FCC Leaf v2.01                                        #
#                                                           #
#    (C) 2018 Chaosje Domero                                #
#    Leaves are less strict, the node will check all        #
#                                                           #
#############################################################

use strict;
no strict 'refs';
use warnings;
use Exporter;
use vars qw($VERSION @ISA @EXPORT @EXPORT_OK);

$VERSION     = '2.01';
@ISA         = qw(Exporter gclient);
@EXPORT      = qw();
@EXPORT_OK   = qw(startleaf leafloop outnode closeleaf balance);

use JSON;
use gerr qw(error);
use gfio 1.10;
use Digest::SHA qw(sha256_hex sha512_hex);
use IO::Socket::INET;
use gclient 7.2.2;
use gserv 3.1.2 qw(prtm);
use Time::HiRes qw(gettimeofday usleep);
use FCC::global;
use FCC::wallet 2.01 qw(validwallet);
use FCC::fcc;

my $DEBUG = 0;

my $LOOPWAIT = 1000; # be nice, release CPU for other processes
my $FCCFUNCTION='leaf';
my $CALLER;
my $LEAVES=[];
my $LEAFID=0;
my $VERS=join('.',substr($FCCVERSION,0,2)>>0,substr($FCCVERSION,2,2));
my $TRANSID=((int(rand(1000000))+10000)<<20)+int(rand(1000000));

1;

sub startleaf {
  my ($host,$port,$caller,$active,$miner) = @_;
  if (!defined $caller || (ref($caller) ne 'CODE')) { error "Caller-function missing in FCC::leaf::start" }
  $CALLER=$caller;
  if (!$host) { $host='127.0.0.1' }
  if (!$port) { $port=7050 }
  $FCCFUNCTION='leaf'; if ($miner) { $FCCFUNCTION='miner' }
  $LEAFID++;
  my $leaf=gclient::websocket($host,$port,$active,\&handle_leaf);
  if ($leaf->{error}) { print "\nError connecting $FCCFUNCTION: $leaf->{error}\n\n"; return $leaf }
  elsif ($active) {
    start(@_)
  }
  $leaf->{connected}=0;
  $leaf->{leafcaller}=$caller;
  $leaf->{passive}=1;
  $leaf->{leafid}=$LEAFID;
  $leaf->{outbuffer}=[];
  bless($leaf); 
  push @$LEAVES,$leaf;
  return $leaf
}

sub handle_leaf {
  my ($leaf,$command,$data) = @_;
  if (!$data) { $data="" }
  if ($command eq 'init') {
    if (!$leaf->{passive}) {
      # maybe this is a bit too much but enables multiple processes using active leaves within the same run-spece.
      $leaf->{connected}=0;
      $leaf->{leafcaller}=$CALLER;
      $leaf->{fccfunction}=$FCCFUNCTION;
      $leaf->{leafid}=$LEAFID;
      $leaf->{outbuffer}=[];
    }
  }
  my $func=$leaf->{leafcaller};
  if (!$func) { $func=$CALLER }
  if ($DEBUG && ($command ne 'loop')) {
    print " < [LEAF]: $command - $data\n";
  }
  if ($command eq 'loop') {
  } elsif ($command eq 'input') {
    handleinput($leaf,$data)
  } elsif ($command eq 'error') {
    &$func($leaf,'disconnect',{ error => $data });
    gclient::wsquit($leaf);
    print "Leaf exited with error: $data\n\n";
  } elsif ($command eq 'quit') {
    &$func($leaf,'disconnect',{ error => $data });
    print "Lost connection to node: $data\n\n";
  } elsif ($command eq 'close') {
    &$func($leaf,'disconnect',{ error => $data });
    print "Lost connection to node: $data\n\n";
  } elsif ($command eq 'connect') {
    my ($tm,$ip) = split(/ /,$data);
    $leaf->{connected}=1;
    if ($DEBUG) {
      print prtm()."Connected as $leaf->{fccfunction} v$VERS at $leaf->{localip} to $ip\n"
    }
  }
}

################## SYSTEM FUNCTIONS ###########################

sub outnode {
  my ($leaf,$k) = @_;
  if (ref($k) ne 'HASH') {
    error "Not a hash-reference given in FCC::leaf::outnode"
  }
  push @{$leaf->{outbuffer}},$k;
}

sub leafloop {
  # in passive mode.. call this yourself!
  foreach my $leaf (@$LEAVES) {
    if ($leaf->{connected}) {
      if ( $#{$leaf->{outbuffer}} >= 0 ) {
        gclient::wsout($leaf,encode_json(shift @{$leaf->{outbuffer}}));
      }
    }
    $leaf->takeloop()
  }
}

sub closeleaf {
  my ($leaf,$msg) = @_;
  if (!$msg) { $msg='Closed' }
  my $func=$leaf->{leafcaller};
  &$func($leaf,'terminated', { message => $msg });
  if ($leaf->{connected}) {
    $leaf->wsquit($msg)
  } else {
    $leaf->quit($msg)
  }
}

################## CALLABLE FUNCTIONS #####################################

sub balance {
  my ($leaf,$wallet) = @_;
  if (ref($wallet)) { $wallet=$wallet->{wallet} }
  outnode($leaf,{ command => 'balance', wallet => $wallet })
}

sub transfer {
  my ($leaf,$pubkey,$changewallet,$tolist) = @_;
  # tolist = { wallet, amount(doggy), fee(doggyfee) }
  $TRANSID++;
  outnode($leaf,{ command => 'newtransaction', transid => $TRANSID, pubkey => $pubkey, to => $tolist })
}

sub sign {
  my ($leaf,$transid,$signature) = @_;
  outnode($leaf, { command => 'signtransaction', transid => $transid, signature => $signature })  
}

sub history {
  my ($leaf,$wallet) = @_;
}

sub solution {
  my ($leaf,$wallet,$solhash) = @_;
  outnode($leaf,{ command => 'solution', wallet => $wallet, solhash => $solhash })
}

################# HANDLE INPUT ########################################

sub handleinput {
  my ($leaf,$data) = @_;
  my $k=decode_json($data);
  my $cmd=$k->{command};
  my $func=$leaf->{leafcaller};
  if ($k->{error}) {
    &$func($leaf,'error',{ command => 'error', message => $cmd, error => $k->{error} });
    return
  }
  my $proc="c_$cmd";
  if (defined &$proc) {
    &$proc($leaf,$k)
  } else {
    print "Illegal command sent to leaf: $cmd\n"
  }
}

sub c_error {
  my ($leaf,$k) = @_;
  print "Error: $k->{message}\n";
  outnode($leaf,{ command => 'quit' });
  gclient::quit($leaf);
  exit
}

sub c_hello {
  my ($leaf,$k) = @_;
  outnode($leaf,{ command => 'identify', type => $leaf->{fccfunction}, version => $FCCVERSION });
  my $func=$leaf->{leafcaller};
  &$func($leaf,'response',{ node => "$k->{host}:$k->{port}", version => $k->{version} })
}

sub c_quit {
  my ($leaf,$k) = @_;
  $leaf->quit()
}

sub c_balance {
  my ($leaf,$k) = @_;
  my $func=$leaf->{leafcaller};
  &$func($leaf,'balance',{ balance => $k->{balance}, wallet => $k->{wallet} })
}

sub c_newtransaction {
  my ($leaf,$k) = @_;
  my $func=$leaf->{leafcaller};
  if ($k->{error}) {
    &$func($leaf,'transstatus',{ error => $k->{error}, transid => $k->{transid}, transhash => $k->{transhash} })
  } else {
    &$func($leaf,'sign',{ data => $k->{sign}, transid => $k->{transid} });
  }
}

sub c_signtransaction {
  my ($leaf,$k) = @_;
  my $func=$leaf->{leafcaller};
  &$func($leaf,'transstatus',{ error => $k->{error}, transid => $k->{transid}, transhash => $k->{transhash} })
}

sub c_processed {
  my ($leaf,$k) = @_;
  my $func=$leaf->{leafcaller};
  if ($k->{error}) {
    &$func($leaf,'transstatus',{ error => $k->{error}, transhash => $k->{transhash} })
  } else {
    &$func($leaf,'transstatus',{ status => 'success', transhash => $k->{transhash}, wallet => $k->{wallet}, amount => $k->{amount}, fee => $k->{fee} })
  }
}

sub c_history {
  my ($leaf,$k) = @_;
  my $func=$leaf->{leafcaller};
#  &$func($k->{wallet},$k->{history})
}

sub c_mine {
  my ($leaf,$k) = @_;
  my $func=$leaf->{leafcaller};
  &$func($leaf,'mine',$k)
}

sub c_solution {
  my ($leaf,$k) = @_;
  my $func=$leaf->{leafcaller};
  &$func($leaf,'solution',$k)  
}

# EOF leaf.pm (C) 2018 Chaosje, Domero 