#!/usr/bin/perl

my $VERSION="2.01";

use strict;
no strict 'refs';
use warnings;
use Time::HiRes qw(usleep gettimeofday);
use gfio;
use gclient;
use FCC::global;
use FCC::leaf qw(solution);
use FCC::miner;
use FCC::wallet qw(validwallet);
use gthreads;

setcoin('PTTP');

print ">>>>>>>>>>>> PTTP Miner $VERSION <<<<<<<<<<<<\n\n";
print "On how many threads should I mine? (3) > ";
my $THREADS=<STDIN>; chomp $THREADS;
if (!$THREADS) { $THREADS=3 }
elsif ($THREADS =~ /[^0-9]/) {
  print "> I don't understand!\n"; exit
}

my $WALLET;

if (!-e 'minerwallet.fcc') {
  print "Enter a PTTP wallet to mine to: ";
  $WALLET=<STDIN>; chomp($WALLET);
  if (!validwallet($WALLET)) {
    print "> Invalid wallet\n"; exit
  }
  gfio::create("minerwallet.pttp",$WALLET)
} else {
  $WALLET=gfio::content("minerwallet.pttp");
  print "Wallet = $WALLET\n"
}

my $NODEIP = '141.138.137.123';
my $NODEPORT = 9633;

if (-e 'minernode.pttp') {
  ($NODEIP,$NODEPORT)=split(/\:/,gfio::content('minernode.pttp'))
} elsif (!-e 'minerrandom.pttp') {
  print "Node to mine to [ip:port] (Leave blank for random node): ";
  my $node=<STDIN>; chomp($node);
  if (!$node) {
    gfio::create('minerrandom.pttp',1)
  } else {
    if ($node =~ /[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+\:[0-9]+/) {
      gfio::create('minernode.pttp',$node);
      ($NODEIP,$NODEPORT)=split(/\:/,$node)
    } else {
      print "> Invalid node (must be ip.ip.ip.ip:port)\n"; exit
    }
  }
}
if (-e 'minerrandom.pttp') {
  my $nodes=gclient::website('https://factorialcoin.nl:9612/?nodelist');
  if ($nodes->{content}) {
    my @nl=split(/\s/,$nodes->{content});
    my $node=$nl[int(rand(1+$#nl))];
    ($NODEIP,$NODEPORT)=split(/\:/,$node)
  }
}

print "\n * Mining on node $NODEIP:$NODEPORT\n\n";

my $PROBLEM;
my $PSIZE = 0;
my $PREST = 0;
my $FAC = 0;
my $POS = 0;
my $HINTS = "";
my $HINTPOS = 0;
my $HINT = "";
my $EHINTS = "";
my $EHINT = "";
my $EHINTPOS = 0;
my $START = 0;
my $LOOP = 0;
my $SOLUTION = "";
my $STARTTIME = 0;
my $DISPTIME = time;
my $HASHSTART = 0;
my $BEGIN = 0;
my $RUNTIME = time;

gthreads::createset('miner');
gthreads::write('miner','tothash',0);
gthreads::write('miner','problemcount',0);
gthreads::write('miner','success',0);
gthreads::write('miner','start',time);
gthreads::write('miner','new',0);
gthreads::write('miner','solution',"");

my $leaf=FCC::leaf::startleaf($NODEIP,$NODEPORT,\&handle,0,1);
if ($leaf->{error}) { print $leaf->{error}."\n"; exit }

while ($leaf && !$leaf->{quit}) {
  mineloop();
  $leaf->leafloop()
}
if ($leaf->{error}) { print $leaf->{error}."\n" }
else { print "Terminated OK\n" }
exit;

sub addhash {
  my ($num) = @_;
  gthreads::inc('miner','tothash',$num)
}

sub hashrate {
  my $th=gthreads::read('miner','tothash');
  my $start=gthreads::read('miner','start');
  my $dtm=time-$start;
  return int(1000 * $th / $dtm) / 1000
}

sub newproblem {
  my ($data) = @_;
  if (!$data->{ehints}) { $data->{ehints}="" }
  $PROBLEM = $data;
  print "\n"; print ">"x79; print "\n";
  print "New challenge [$data->{coincount}]: diff=$data->{diff} len=$data->{length} hints=$data->{hints} ehints=$data->{ehints}\n";
  print "<"x79; print "\n";
  gthreads::inc('miner','problemcount',1);
  $HASHSTART=gthreads::read('miner','tothash');
  if ($data->{hints}) {
    $FAC=fac($data->{length}-1);
    $HINTS=perm($data->{hints},int(rand(fac(length($HINTS)))));
    $HINTPOS=0;
    $HINT=substr($HINTS,$HINTPOS,1);
    if ($data->{ehints}) {
      $FAC=fac($data->{length}-2);
      $EHINTS=perm($data->{ehints},int(rand(fac(length($EHINTS)))));
    }
  } else {
    $FAC=fac($data->{length});
    $HINTS=""; $HINT=""; $EHINTS="";
  }
  $PSIZE = int($FAC / $THREADS);
  $PREST = $FAC % $THREADS;
  $POS = int(rand($FAC));
  $START = $POS;
  $LOOP = 0;
  # signal active miners
  my $tm=gettimeofday();
  if ($STARTTIME) {
    my $ptm=int( ( $tm - $STARTTIME ) * 1000 ) / 1000;
    my $min=int($ptm / 60);
    my $sec=sprintf("%02d",$ptm % 60);
    my $avg='[n/a]';
    if (!$BEGIN) {
      $BEGIN=time
    } else {
      my $num=gthreads::read("miner",'problemcount'); $num-=2;
      my $vtm=time - $BEGIN;
      my $vdtm = int($vtm / $num);
      my $vmin = int($vdtm / 60);
      my $vsec=sprintf("%02d",$vdtm % 60);
      $avg=$vmin.'m'.$vsec.'s';
    }
    print "Coinbase Circulation Time: $min".'m'.$sec.'s'." Average: $avg\n\n";
  }
  gthreads::write('miner','new',1);
  $STARTTIME=$tm
}

sub minerblock {
  my ($id,$init,$challenge,$coincount,$pos,$fac,$psize,$hint,$ehint) = @_;
  my $stm=gettimeofday(); my $mc=0; my $cnt=0; my $try; my $perm; my $m; my $dn; my $ind; my $thint=$hint.$ehint; my $ilen=length($init);
  while ($psize>0) {
    $cnt=0; my $todo=50000;
    if ($todo>$psize) { $todo=$psize }
    $psize-=$todo;
    for (my $i=0; $i<$todo; $i++) {
      $cnt++;
      $try=$init; $perm=""; $m=$pos; $dn=$ilen;
      while ($dn>0) {
        $ind=$m % $dn;
        $m=$m / $dn;  
        $dn--;
        $perm.=substr($try,$ind,1,substr($try,$dn,1));
      }
      #$perm=perm($init,$pos);
      my $hash=minehash($coincount,$thint.$perm);
      if ($hash eq $challenge) {
        gthreads::write('miner','solution',$thint.$perm);
        addhash($cnt);
        return 1
      }
      $pos++; if ($pos >= $fac) { $pos = 0 }      
    }
    $mc++; addhash($todo);
    # new challenge signalled?
    if (gthreads::read('miner','new')) {
      return 1
    }
    if ($mc == 10) {
      $mc=0;
      my $tm=gettimeofday();
      my $dtm=$tm-$stm;
      $stm=$tm;
      my $hr=int(500000 / $dtm);
      print " [ HR $id = $hint : $hr Fhs ]\n"
    }
  }
  return 0
}

sub minerthread {
  my ($id,$problem,$pos,$fac,$psize,$hint,$ehints) = @_;
  print "Thread $id: pos=$pos, fac=$fac, psize=$psize, hint=$hint, ehints=$ehints\n";
  my $init=""; my $ehint="";
  if ($ehints) {
    for (my $ehp=0; $ehp<length($ehints); $ehp++) {
      $ehint=substr($ehints,$ehp,1);
      if ($ehint eq $hint) { next }
      $init="";
      for (my $i=0;$i<$problem->{length};$i++) {
        my $c=chr(65+$i);
        if (($c ne $hint) && ($c ne $ehint)) { $init.=$c }
      }
      my $end=$pos+$psize-1;
      if ($end > $fac) {
        my $rst=$end-$fac; $end="$fac..$rst"
      }
      print " -> $id $hint$ehint [$pos..$end]\n";
      if (minerblock($id,$init,$problem->{challenge},$problem->{coincount},$pos,$fac,$psize,$hint,$ehint)) {
        gthreads::done($id); return
      }
    }
  } else {
    for (my $i=0;$i<$problem->{length};$i++) {
      my $c=chr(65+$i);
      if ($c ne $hint) { $init.=$c }
    }
    minerblock($id,$init,$problem->{challenge},$problem->{coincount},$pos,$fac,$psize,$hint,"")
  }
  gthreads::done($id);
}

sub mineloop {
  if (!$PROBLEM) {
    usleep(10000); return
  }
  if (gthreads::read('miner','new')) {
    if (gthreads::running() > 0) {
      return
    } else {
      gthreads::write('miner','new',0)
    }
  }
  if (gthreads::running() < $THREADS) {
    $LOOP++;
    print "Starting thread $LOOP/$THREADS ($POS, $HINT, $EHINTS)\n";
    if ($LOOP == $THREADS) {
      gthreads::start('miner',\&minerthread,$PROBLEM,$POS,$FAC,$PSIZE+$PREST,$HINT,$EHINTS);
      $LOOP = 0;
      $POS+=$PSIZE+$PREST;
      if ($HINT) {
        $HINTPOS++;
        $HINT=substr($HINTS,$HINTPOS,1)
      }
    } else {
      gthreads::start('miner',\&minerthread,$PROBLEM,$POS,$FAC,$PSIZE,$HINT,$EHINTS);
      $POS+=$PSIZE;
    }
    if ($POS>$FAC) { $POS-=$FAC }
  }
  my $sol=gthreads::read('miner','solution');
  if ($sol && ($sol ne $SOLUTION)) {
    my $txt="* SOLUTION: $sol .. Yeah! :) *";
    my $sl=length($txt);
    print "\n"; print '*'x$sl; print "\n$txt\n"; print '*'x$sl; print "\n\n";
    solution($leaf,$WALLET,solhash($WALLET,$sol));
    $SOLUTION=$sol;
  }
  if (time - $DISPTIME > 60) {
    $DISPTIME = time;
    my $hr=hashrate();
    my $p=gthreads::read('miner','problemcount');
    my $s=gthreads::read('miner','success');
    my $dp = $p - 1; my $perc='0';
    if ($dp) { $perc = int (10000 * $s / $dp) / 100 }
    my $str="$hr Fhs - Problems $p - Found solutions $s ($perc %) - Threads $THREADS";
    my $th=gthreads::read('miner','tothash');
    my $dh=$th-$HASHSTART;
    my $hp=int(10000 * $dh / $PROBLEM->{diff}) / 100;
    my $dtm=int((time - $RUNTIME) / 60);
    my $hour=int($dtm / 60); my $min=sprintf("%02d",$dtm % 69);
    my $days = int($hour / 24); $hour=sprintf("%02d",$hour % 24);
    my $str2="$days".'d'.":$hour".'h'.$min."m Curr: $hp% Diff=$PROBLEM->{diff} Len=$PROBLEM->{length} Hints=$PROBLEM->{hints} ($PROBLEM->{ehints})";
    my $sl=length($str);
    my $sp=(90-$sl)>>2;
    my $spl=""; if ($sl % 2) { $spl=' ' }
    print '   '; print '-'x73; print "\n";
    print ' 'x$sp; print "$str\n";
    print ' 'x$sp; print "$str2\n";
    print '   '; print '-'x73; print "\n";
  }
  usleep(100000)
}

sub handle {
  my ($leaf,$command,$data) = @_;
  if (($command eq 'disconnect') || ($command eq 'terminated') || ($command eq 'error')) {
    my $msg; if ($data->{message}) { $msg=$data->{message} }
    if ($data->{error}) { $msg=$data->{error} }
    print "Exit: $msg\n"
  } elsif ($command eq 'response') {
    print "Connected to node!\n"
  } elsif ($command eq 'mine') {
    my $p = 0; my $d = 1;
    if ($PROBLEM) {
      $p=$PROBLEM->{coincount};
      $d=$data->{coincount}
    }
    if ($p < $d) {
      newproblem($data)
    }
  } elsif ($command eq 'solution') {
    if ($data->{error}) {
      print " * The core REJECTED our solution :( boehoooooo *\n * -> $data->{error}\n"
    } else {
      print " * The core accepted our solution :) *\n";
      gthreads::inc('miner','success',1);
    }
  }
}

# EOF multithreading PTTP miner (C) 2018 Chaosje