import argparse
import struct


def assemble(infile):
    pass


def write_binary(outfile):
    interrupts = 26
    jmp = 0x940C
    bad_interrupt = interrupts * 2
    reset = 0x0000
    for _ in range(interrupts):
        write_word(outfile, jmp)
        write_word(outfile, bad_interrupt)
    write_word(outfile, jmp)
    write_word(outfile, reset)


def write_word(outfile, word):
    outfile.write(struct.pack("<H", word))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("infile", nargs="+")
    parser.add_argument("-o", "--outfile", required=True)
    args = parser.parse_args()
    for infile_name in args.infile:
        with open(infile_name, "rt") as infile:
            assemble(infile)
    with open(args.outfile, "wb") as outfile:
        write_binary(outfile)