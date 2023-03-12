#!/bin/bash
set -e

# constants
model=16000_i
prefix=tam
g_prefix="$prefix.tsaurus"
osyms="$g_prefix.g.osyms"
TESTS_DIR="$HOME/build_dirs_in_use"
BUILD_DIRS_FILE="$HOME/.build_dirs"
SCRIPTS_DIR="`dirname $(readlink -f "$0")`"
TRUNK="$(readlink -f "$SCRIPTS_DIR/../..")"
DECODER="$TRUNK/decoder"

[[ ! -e "$BUILD_DIRS_FILE" ]] && touch "$BUILD_DIRS_FILE"

# help message
usage (){
	echo "Usage: `basename $0` [options] <arpa_file> <build_name>"
	echo "Options:"
	echo "   -b <build_directory>"
	echo "       Specify the location of the build directory to use. By default, waits for"
	echo "       a build folder to become available as specified in the following file:"
	echo "       $BUILD_DIRS_FILE"
	echo "       Each line should contain the absolute path to a single build directory."
	echo "   -B"
	echo "       Display build directories that are currently in use and exit."
	# echo "   -D <data_directory>:"
	# echo "       Specify the directory in which to store intermediate files."
	# echo "   -d <pronunciation_dictionary>:"
	# echo "       Specify the pronunciation dictionary to use when compiling the FST."
	echo "   -g"
	echo "       Regenerate the acoustic models before building the FSTs."
	echo "   -z <directory>"
	echo "       Create any intermediate files under this directory."
	echo "Arguments:"
	echo "   <arpa_file>"
	echo "       The ARPA file to test."
	echo "   <build_name>"
	echo "       The string that will be attached to the test results in the database."
}

# important files
dict_src="$DECODER/s3data/wsj_all.dic"

# default options
GEN_AM=""
# NOTE: custom data directory works for fst generation but not implemented for automated testing
DATA_DIR="$DECODER/data"
working_dir="."

# parse options
while getopts ":d:D:ghb:Bz:" opt; do
	case $opt in
		# D) DATA_DIR="$OPTARG" ;;
		# d) DICT="$OPTARG" ;;
		g) GEN_AM="-g" ;;
		h) usage; exit 0 ;;
		b) BUILD_DIR="`readlink -f "$OPTARG"`" ;;
		B) ls -1 "$TESTS_DIR" | sed 's:\\:/:g'; exit 0 ;;
		z) working_dir="$OPTARG" ;;
		\?)
			echo "Invalid Option: -$OPTARG" >&2
			usage >&2
			exit 1 ;;
		:)
			echo "Option -$OPTARG requires an additional argument" >&2
			usage >&2
			exit 1 ;;
	esac
done

# make sure that the specified data directory exists
if [[ ! -d "$DATA_DIR" ]]; then
	echo "\"$DATA_DIR\" does not exist or is not a directory." >&2
	exit 1
fi

shift $(($OPTIND-1))

# make sure the correct number of positional arguments were given
if [[ $# -ne 2 ]]; then
	echo "Error: Incorrect number of positional arguments" >&2
	usage >&2
	exit 65
fi

# get the positional arguments
arpa_fname="$1"
build_name="$2"

# get absolute paths
fst_fname="$DATA_DIR/$model/`basename ${arpa_fname%.arpa}.fst`"
arpa_fname="`readlink -f "$arpa_fname"`"
fst_fname="`readlink -f "$fst_fname"`"

# check if the specified build directory is currently being used for another test
mkdir -p "$TESTS_DIR"
if [[ -n "$BUILD_DIR" ]]; then
	BUILD_DIR="${BUILD_DIR%/}" # in case the slash was added to the end of the directory by e.g. tab completion
	BUILD_DIR_ALT="`echo "$BUILD_DIR" | sed 's:/:\\\:g'`"
	if [[ -e "$TESTS_DIR/$BUILD_DIR_ALT" ]]; then
		echo "\"$BUILD_DIR\" is marked as in use for another test you are running." >&2
		exit 1
	fi
else
	if [[ ! -s "$BUILD_DIRS_FILE" ]]; then # if file is empty (-s makes sure file size is not 0)
		echo "No build directory was specified and you have not set any default build" >&2
		echo "directories. Please use the -b option to specify the build directory." >&2
		exit 1
	fi
	BUILD_DIR="`ls -1 "$TESTS_DIR" | sed 's:\\\:/:g' | grep -Fvxf - "$BUILD_DIRS_FILE" | head -1`"
	[[ -z "$BUILD_DIR" ]] && echo "Waiting for available build directory"
	while [[ -z "$BUILD_DIR" ]]; do
		sleep 10 # to avoid wasting cpu time on this script while it's waiting for an available build directory
		BUILD_DIR="`ls -1 "$TESTS_DIR" | sed 's:\\:/:g' | grep -Fvxf - "$BUILD_DIRS_FILE" | head -1`"
	done
	BUILD_DIR_ALT="`echo "$BUILD_DIR" | sed 's:/:\\\:g'`"
fi

# handle automatic tracking of build directories that are being used for testing
mkdir -p "$TESTS_DIR/$BUILD_DIR_ALT"

# in case script unexpectedly stops, trap signals to clean up automatic build directory usage tracking
trap "rm -rf \"$TESTS_DIR/$BUILD_DIR_ALT\"; trap - ERR SIGHUP SIGINT SIGTERM" ERR SIGHUP SIGINT SIGTERM

# set the build name, fst file and data directory
pushd "$BUILD_DIR" >& /dev/null
cmake -DBUILDNAME="$build_name" -DFST="`basename "$fst_fname"`" "$TRUNK" #-DDATADIR="$DATA_DIR" ..
popd >& /dev/null

# compose the FST
if [[ -n $DICT ]]; then DICT_ARGS="-d \"$DICT\""; fi
$SCRIPTS_DIR/arpa2fst -b "$BUILD_DIR" -z "$working_dir" $DICT_ARGS $GEN_AM "$arpa_fname" "$fst_fname"

# run the test
pushd "$BUILD_DIR" >& /dev/null
make Experimental
popd >& /dev/null

rm -rf "$TESTS_DIR/$BUILD_DIR_ALT"
trap - ERR SIGHUP SIGINT SIGTERM
