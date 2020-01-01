#!/usr/bin/env bash

set -u
export LANG=C

mkdir -p test_out

function error() {
    echo "$1"
    exit 1
}

function hex2bin() {
    xxd -r test/"$1"_hex.txt > test/"$1".bin
}

function disassemble() {
    (cd "$1" && avr-objdump -b binary -m avr -D "$2".bin > "$2"_dis.txt) || error "disassembly failed: $1/$2.bin"
}

function assemble() {
    file="$1"
    shift
    python3 rasm.py --no-vectors "$@" test/"$file".s -o test_out/"$file".bin || error "assembly failed: test/$file"
}

function diff_disassembly() {
    colordiff -u test/"$1"_dis.txt test_out/"$1"_dis.txt || error "output not correct"
}

function diff_binary() {
    cmp test/"$1".bin test_out/"$1".bin || error "output not correct"
}

function check_raw() {
    echo "$1"
    hex2bin "$1"
    assemble "$@"
    diff_binary "$1"
}

function check() {
    echo "$1"
    hex2bin "$1"
    disassemble test "$1"
    assemble "$@"
    disassemble test_out "$1"
    diff_disassembly "$1"
}


check_raw empty
check syntax
check vectors --vectors
check jumps --vectors
check bits
check mcuctrl
check arithlog
