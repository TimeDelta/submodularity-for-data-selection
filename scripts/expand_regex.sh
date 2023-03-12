#!/bin/bash
set -e
fid="`date +%s`_$$_$RANDOM"
while [[ -e ${fid} ]]; do fid=`echo \`date +%s\`_$$_$RANDOM`; done
regex="`< $1 tr -d '\r' | awk 'NF > 0 {print ")|("$0} END {print ")"}' | tr -d '\n' | sed s/^\)\|//`"
regex2fst "$regex" "$fid" > /dev/null
fstprintallpaths "$fid"
rm "$fid" "$fid.osyms"
