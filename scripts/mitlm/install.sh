#!/bin/bash
set -e

fullpath (){
	# this lets me run this script on my mac
	[[ `uname` == Darwin* ]] && realpath "$@" || readlink -f "$@"
}

MITLM_DIR="`dirname $(fullpath $0)`"
pushd "$MITLM_DIR"

tar xzf mitlm-0.4.1.tar.gz
mv mitlm-0.4.1/* .
rmdir mitlm-0.4.1

./configure --prefix=`pwd` && make && make install

popd
