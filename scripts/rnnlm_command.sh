#!/bin/bash
if [ $# -ne 5 ]
then
  echo "Usage: ./rnnlm_command.sh <corpus> <training ratio> <bptt> <words> <>"
  exit 65
fi

# variables
corpus=$1
ratio=$2
validratio=`echo "1 - $ratio" | bc`
trainingset="train"$ratio
validationset="valid"$validratio
bptt=$3
words=$4
rnnlm=$trainingset"_class1_min-improv1_bptt"$bptt
rnnlmfile=$rnnlm".rnnlm"
description=$rnnlm"_words"$words
seed=$5

# split corpus into training and validation data sets
python splitcorpus.py -i $corpus -t $trainingset -v $validationset -r $ratio

# create the RNN-LM
./rnnlm -class 1 -min-improvement 1 -bptt $bptt -rnnlm $rnnlmfile -train $trainingset -valid $validationset -rand-seed $seed

# remove the log file from RNN-LM creation
rm -f $rnnlmfile.output.txt

# generate a new corpus of specified length from the RNN-LM
./rnnlm -rnnlm $rnnlmfile -gen $words > $description.corpus

# remove the first two lines in the new corpus file b/c they're junk
tail -n +3 $description.corpus > $description.corpus

# create Witten-Bell (backoff) smoothed ARPA file
python wbsmooth.py $description.corpus $description.trigram.arpa

# create clustered Witten-Bell (backoff) smoothed ARPA file

