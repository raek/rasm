#!/usr/bin/env bash

set -u
export LANG=C

mkdir -p test_out

function error() {
    echo "$1"
    exit 1
}

function check() {
    (cd test && avr-objdump -b binary -m avr -D "$1".bin > "$1"_dis.txt) || error "disassembly failed"
    python3 rasm.py test/"$1".s -o test_out/"$1".bin || error "rasm.py failed"
    (cd test_out && avr-objdump -b binary -m avr -D "$1".bin > "$1"_dis.txt) || error "disassembly failed"
    colordiff -u test/"$1"_dis.txt test_out/"$1"_dis.txt || error "output not correct"
}

check empty
check jumps
check bits
