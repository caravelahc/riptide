#!/usr/bin/env sh
INPUT=$1
OUTPUT=$2

pdftotext -layout -nopgbrk $INPUT - | awk -F' {2,}' '{print $1}' | tee $OUTPUT > /dev/null
