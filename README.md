# rasm

This is an 8-bit AVR assembler I wrote for myself.

## Usage

See the help from the command:

    python3 rasm.py --help

## Development

This tool is written in Python 3. To run the tests you also need
`avr-objdump`, `colordiff`, and `xxd`. On Debian or Ubuntu, these can
be installed like this:

    sudo apt install python3, binutils-avt, colordiff, xxd

To run the test suite, just invoke:

    ./run_tests.sh
