# rasm

This is an 8-bit AVR assembler I wrote for myself.

## Installation

    pip3 install rasm

## Usage

See the help from the command:

    rasm --help

## Development

This tool is written in Python 3. To run the tests you also need
`avr-objdump`, `colordiff`, and `xxd`. On Debian or Ubuntu, these can
be installed like this:

    sudo apt install python3, python3-pip, python3-setuptools, python3-wheel, binutils-avt, colordiff, xxd

Install the package in editable mode:

    pip3 install -e .

To run the test suite, just invoke:

    ./run_tests.sh
