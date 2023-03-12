#!/bin/bash
set -e

fullpath (){
	# this lets me run this script on my mac
	[[ `uname` == Darwin* ]] && realpath "$@" || readlink -f "$@"
}

# make sure to be in correct directory (same dir as this script)
pushd "$(dirname `fullpath "$0"`)"

# extract
tar xzf srilm-1.7.1.tar.gz

# build
make SRILM="`pwd`"

popd
