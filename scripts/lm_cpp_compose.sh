#!/bin/bash
set -e

# default options
NEW_DECODER="$(readlink -f "`dirname $0`/../..")"
DATA_DIR="$NEW_DECODER/decoder/data"
arpa_fname="$DATA_DIR/test.arpa"
dict_src="$NEW_DECODER/decoder/s3data/wsj_all.dic"
output_fname=""

# help message
USAGE="Usage: `basename $0` [-d dictionary] [-a arpa_file] [-o fst_output_file_name] [-D data_directory] [-n new_decoder_directory] <model_type>\n"
USAGE="$USAGE\t-d\t\t: Dictionary to use for translation from words to phonemes.\n"
USAGE="$USAGE\t-a\t\t: ARPA file from which to compose an FST graph.\n"
USAGE="$USAGE\t-o\t\t: Name to use for the resulting FST file (stored under data_directory/model_type/).\n"
USAGE="$USAGE\t-D\t\t: Directory in which to store all of the intermediate files.\n"
USAGE="$USAGE\t-n\t\t: Fully qualified path to the \"new_decoder\" directory.\n"
USAGE="$USAGE\t<model_type>\t: Model type to compose."

# parse options
while getopts ":d:a:o:D:n:h" opt; do
	case $opt in
		d)
			dict_src="$OPTARG"
			;;
		a)
			arpa_fname="$OPTARG"
			;;
		o)
			output_fname="$OPTARG"
			;;
		D)
			DATA_DIR="$OPTARG"
			;;
		n)
			NEW_DECODER="$OPTARG"
			;;
		h)
			echo -e $USAGE
			exit 0
			;;
		\?)
			echo "Invalid Option: -$OPTARG" >&2
			echo -e $USAGE >&2
			exit 1
			;;
		:)
			echo "Option -$OPTARG requires an additional argument" >&2
			echo -e $USAGE >&2
			exit 1
			;;
	esac
done

DECODER="$NEW_DECODER/decoder"
FST_BIN="$NEW_DECODER/build/decoder/openfst-1.3.1/src/bin"
TOKEN_MAPPERS="$NEW_DECODER/language_model/token_mappers"
SOURCE_DIR="$NEW_DECODER/language_model/scripts"

# make sure the correct number of positional arguments was given
num_ops=`echo "$# - $OPTIND + 1" | bc`
if [[ $num_ops -ne 1 ]]; then
	echo "Error: Missing <model_type> argument" >&2
	echo -e $USAGE >&2
	exit 65
fi

model_type="${@: -1}"

# default output path
if [[ -z "$output_fname" ]]; then
	output_fname="$DATA_DIR/$model_type/wsj.fst"
fi

# get absolute paths
arpa_fname=`readlink -f "$arpa_fname"`
output_fname=`readlink -f "$output_fname"`

prefix=tam
g_prefix="$prefix.tsaurus"
osyms="$g_prefix.g.osyms"

# create symlink to dictionary in data directory
rm "$DATA_DIR/dict" &> /dev/null || true
ln -s "$dict_src" "$DATA_DIR/dict"

# keep track of the current directory
pushd "$DATA_DIR" > /dev/null

# create the temporary data conversion folder for the specified model type
mkdir -p "$DATA_DIR/tmp_data_conversion"
mkdir -p "$DATA_DIR/tmp_data_conversion/$model_type"

rm "$DATA_DIR/tmp_data_conversion/$model_type"/* >& /dev/null || true

# switch to the temporary data conversion folder for the specified model type
pushd tmp_data_conversion > /dev/null
pushd "$model_type" > /dev/null

# compile tam.tsaurus.g.fst
echo "compiling $g_prefix.g.fst"
python << EOL
#!/usr/bin/env python
import sys
sys.path.insert(0, '$DECODER/scripts/transducersaurus-0.0.1/python/')
from arpa2fst import ArpaLM

arpa = ArpaLM(
	'$arpa_fname',
	'$g_prefix.g.fst.txt',
	sil='<SIL>',
	prefix='$g_prefix',
	eps='<eps>',
	boff='#b')
arpa.arpa2fst( )
arpa.print_all_syms( )
EOL

fstcompile \
	--arc_type=log \
	--acceptor=true \
	"--ssymbols=$g_prefix.g.ssyms" \
	"--isymbols=$g_prefix.g.isyms" \
	"--osymbols=$osyms" \
	--keep_isymbols --keep_osymbols \
	"$g_prefix.g.fst.txt" | fstarcsort --sort_type=ilabel - > "$g_prefix.g.fst"

# for debugging only
# LM_FST="$DATA_DIR/test.fst"
# regex2fst "A (testa|testb)" "$LM_FST"
# fstprint --isymbols="$TOKEN_MAPPERS/test.fst.osyms" --osymbols="$TOKEN_MAPPERS/test.fst.osyms" "$LM_FST" "$LM_FST.txt"
# "$FST_BIN"/fstcompile --arc_type=log --isymbols="$TOKEN_MAPPERS/test.fst.osyms" --osymbols="$TOKEN_MAPPERS/test.fst.osyms" --keep_isymbols --keep_osymbols "$LM_FST.txt" "$LM_FST"
# ISYMS="$TOKEN_MAPPERS/test.fst.osyms"
# output_syms=`cat $TOKEN_MAPPERS/test.fst.osyms`

LM_FST="$g_prefix.g.fst"
ISYMS="$DATA_DIR/tmp_data_conversion/$model_type/$osyms"
# output_syms=`cat "$ISYMS"`

# echo "Removing epsilon arcs"
# "$FST_BIN"/fstrmepsilon "$LM_FST" "$LM_FST"

# echo "Minimizing LM FST"
# fstminimize "$LM_FST" "$LM_FST"
# fstprint --save_osymbols="$ISYMS" "$LM_FST" > /dev/null

# i=0
# tokens=( "date" "time" "num" )
# for token in "${tokens[@]}"; do
# 	if [[ $output_syms == *"<$token>"* ]]; then # if the lm FST contains the current token as an output symbol
# 		if [[ i -gt 0 ]]; then
# 			# save the output symbol table as the input symbol table for the next mapper fst
# 			echo "Saving output symbol table"
# 			fstprint --save_osymbols="$ISYMS" "$LM_FST" > /dev/null
# 		fi
		
# 		# create the replacement grammar-level FST for current token, pulling the regular
# 		# expression for numbers directly from the file containing it's backus-naur form
# 		# for easier reasoning about the regular expression
# 		# create_fst_mapper.sh <regex> <path/token_prefix> <input_symbols_file> <output_symbols_file> <new_decoder_directory>
# 		echo "Building <$token> mapper FST"
# 		"$TOKEN_MAPPERS"/create_fst_mapper.sh \
# 			"`python "$SOURCE_DIR/bnf2regex.py" "$TOKEN_MAPPERS/${token}_bnf"`" \
# 			"$DATA_DIR/$token" \
# 			"$ISYMS" \
# 			"$TOKEN_MAPPERS/${token}_mapper.osyms" \
# 			"$NEW_DECODER"
		
# 		# replace the output symbols matching the current token with the mapped fst
# 		echo "Replacing <$token> tokens"
# 		"$FST_BIN"/fstcompose "$LM_FST" "$DATA_DIR/${token}_mapper.fst" "$LM_FST"
		
# 		# project output labels onto input labels
# 		echo "Projecting output symbols"
# 		"$FST_BIN"/fstproject --project_output "$LM_FST" "$LM_FST"
		
# 		echo "Removing superfluous epsilon arcs"
# 		"$FST_BIN"/fstrmepsilon "$LM_FST" "$LM_FST"
# 		# echo "Minimizing"
# 		# "$FST_BIN"/fstminimize "$LM_FST" "$LM_FST"
		
# 		i+=1
# 	fi
# done

"$NEW_DECODER/build/decoder/utils/ComposeAll" \
	"$DATA_DIR" \
	"$model_type" \
	"$g_prefix.g.fst" \
	ptt \
	"$output_fname" \
	"$prefix"

popd > /dev/null
popd > /dev/null
popd > /dev/null

exit 0
