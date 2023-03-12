#!/bin/bash
set -e

# This script creates a minimized fst from a regex that
# can then be composed with the fst generated from an
# arpa to expand a token.

if [[ $# -ne 5 ]]; then
	echo "Wrong number of arguments" >&2
	echo "Usage: `basename $0` <regex> <path/token_prefix> <input_symbols_file> <output_symbols_file> <new_decoder_directory>" >&2
	exit 65
fi

DECODER="$5/build/decoder"
FST_BIN="$DECODER/openfst-1.3.1/src/bin"
UTILS="$DECODER/utils"
TOKEN_MAPPERS="$5/language_model/token_mappers"

# turn regex into minimized fst
"$DECODER"/grammar/regex2fst "$1" "$2.fst" > /dev/null
"$FST_BIN"/fstminimize "$2.fst" "$2.min.fst"

"$FST_BIN"/fstprint --isymbols="$2.fst.osyms" --osymbols="$2.fst.osyms" "$2.min.fst" > "$2.min.txt"
# add <token>:<eps> arc at beginning of fst and shift state indices accordingly
echo "0 1 <`basename $2`> <eps>" > "$2.min.txt2"
awk '{line=$1+1; if (NF > 2) line = line" "$2+1" <eps> "$4" "$5; else if (NF > 1) line = line" "$2; print line;}' "$2.min.txt" >> "$2.min.txt2"
mv "$2.min.txt2" "$2.min.txt"

# prepare for the auxillary symbol loops to be added to the mapper fst
awk -v token=".*<`basename $2`>.*" '$0 !~ token {print $1}' "$3" > "$2_aux_syms"    # add all of the lm fst's output symbols except <token> to the auxillary symbol list
i=`cat "$4" | awk 'END {print $2}'`                                                 # get highest existing output symbol index
cat "$4" > "$2_osyms"                                                               # start with all of the original output symbols
cat "$2_aux_syms" | awk -v i=$i '{print $0" "++i}' >> "$2_osyms"                    # add the auxillary symbols as output symbols for the mapper fst
cat "$2_osyms" | awk '!seen[$1]++' > "$2_osyms_temp"; mv "$2_osyms_temp" "$2_osyms" # make sure no symbol names are repeated in the lm fst's output symbol table

# recompile minimized mapper fst to make it's input symbol table match the lm fst's output symbol table
"$FST_BIN"/fstcompile --arc_type=log --isymbols="$3" --osymbols="$2_osyms" --keep_isymbols --keep_osymbols "$2.min.txt" "$2_mapper.fst"

# in order to accept <token>*
"$FST_BIN"/fstclosure "$2_mapper.fst" "$2_mapper.fst"

# remove superfluous <eps>:<eps> arcs and invert input & output symbols to "unconfuse" fstaddauxloops
"$FST_BIN"/fstrmepsilon "$2_mapper.fst" "$2_mapper.fst"
"$FST_BIN"/fstinvert "$2_mapper.fst" "$2_mapper.fst"

# if there are output symbols in the lm's fst that are not matched to any input
# symbol in the mapper fst, the arcs containing the unmatched output symbols in
# the lm's fst will be discarded. this fixes that by adding a loop to all final
# states, and any state that has arcs with a non-epsilon output label.
"$UTILS"/fstaddauxloops "$2_aux_syms" "$2_mapper.fst"

# uninvert input & output symbols and remove superfluous <eps>:<eps> arcs
"$FST_BIN"/fstinvert "$2_mapper.fst" "$2_mapper.fst"
"$FST_BIN"/fstrmepsilon "$2_mapper.fst" "$2_mapper.fst"

# make sure that the input labels are sorted, otherwise the composition will fail
"$FST_BIN"/fstarcsort --sort_type=ilabel "$2_mapper.fst" "$2_mapper.fst"
