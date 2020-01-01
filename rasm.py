import argparse
import collections
import enum
import re
import struct


class ArgType(enum.Enum):
    NONE          =  0
    ADDR          =  1
    ADDR_OFFSET   =  2
    IO32          =  3
    IO64          =  4
    BIT           =  5
    REG32         =  6 # r0, r1, ..., r31
    REG16         =  7 # r16, r17, ..., r31
    REG8          =  8 # r16, r17, ..., r23
    REG_PAIR16    =  9 # r1:r0, r3:r2, ..., r31:r30
    REG_PAIR4     = 10 # r25:r24, r27:26, r29:r28, r31:r30
    IMMEDIATE     = 11
    IMMEDIATE_INV = 12


ARG_TYPE_CHARS = {
    " ": ArgType.NONE,
    "A": ArgType.ADDR,
    "a": ArgType.ADDR_OFFSET,
    "i": ArgType.IO32,
    "I": ArgType.IO64,
    "b": ArgType.BIT,
    "r": ArgType.REG32,
    "h": ArgType.REG16,
    "H": ArgType.REG8,
    "p": ArgType.REG_PAIR16,
    "P": ArgType.REG_PAIR4,
    "k": ArgType.IMMEDIATE,
    "K": ArgType.IMMEDIATE_INV,
}


INSTRUCTIONS = {
    "nop":    ("  ", "0000 0000 0000 0000"),
    "movw":   ("pp", "0000 0001 aaaa bbbb"),
    "muls":   ("hh", "0000 0010 aaaa bbbb"),
    "mulsu":  ("HH", "0000 0011 0aaa 0bbb"),
    "fmul":   ("HH", "0000 0011 0aaa 1bbb"),
    "fmulsu": ("HH", "0000 0011 1aaa 1bbb"),
    "fmuls":  ("HH", "0000 0011 1aaa 0bbb"),
    "cpc":    ("rr", "0000 01ba aaaa bbbb"),
    "sbc":    ("rr", "0000 10ba aaaa bbbb"),
    "add":    ("rr", "0000 11ba aaaa bbbb"),
    "lsl":    ("r ", "0000 11Aa aaaa AAAA"),
    "cpse":   ("rr", "0001 00ba aaaa bbbb"),
    "cp":     ("rr", "0001 0110 0000 1111"),
    "sub":    ("rr", "0001 10ba aaaa bbbb"),
    "adc":    ("rr", "0001 11ba aaaa bbbb"),
    "rol":    ("r ", "0001 11Aa aaaa AAAA"),
    "and":    ("rr", "0010 00ba aaaa bbbb"),
    "tst":    ("r ", "0010 00Aa aaaa AAAA"),
    "eor":    ("rr", "0010 01ba aaaa bbbb"),
    "clr":    ("r ", "0010 01Aa aaaa AAAA"),
    "or":     ("rr", "0010 10ba aaaa bbbb"),
    "mov":    ("rr", "0010 11ba aaaa bbbb"),
    "cpi":    ("hk", "0011 bbbb aaaa bbbb"),
    "sbci":   ("hk", "0100 bbbb aaaa bbbb"),
    "subi":   ("hk", "0101 bbbb aaaa bbbb"),
    "ori":    ("hk", "0110 bbbb aaaa bbbb"),
    "sbr":    ("hk", "0110 bbbb aaaa bbbb"),
    "andi":   ("hk", "0111 bbbb aaaa bbbb"),
    "cbr":    ("hK", "0111 bbbb aaaa bbbb"),
    "lds":    ("rA", "1001 000a aaaa 0000 bbbb bbbb bbbb bbbb"),
    "pop":    ("r ", "1001 000a aaaa 1111"),
    "sts":    ("Ar", "1001 001b bbbb 0000 aaaa aaaa aaaa aaaa"),
    "push":   ("r ", "1001 001a aaaa 1111"),
    "ijmp":   ("  ", "1001 0100 0000 1001"),
    "des":    ("k ", "1001 0100 aaaa 1011"),
    "com":    ("r ", "1001 010a aaaa 0000"),
    "neg":    ("r ", "1001 010a aaaa 0001"),
    "swap":   ("r ", "1001 010a aaaa 0010"),
    "inc":    ("r ", "1001 010a aaaa 0011"),
    "asr":    ("r ", "1001 010a aaaa 0101"),
    "lsr":    ("r ", "1001 010a aaaa 0110"),
    "ror":    ("r ", "1001 010a aaaa 0111"),
    "dec":    ("r ", "1001 010a aaaa 1010"),
    "jmp":    ("A ", "1001 010a aaaa 110a aaaa aaaa aaaa aaaa"),
    "call":   ("A ", "1001 010a aaaa 111a aaaa aaaa aaaa aaaa"),
    "bset":   ("b ", "1001 0100 0aaa 1000"),
    "sec":    ("  ", "1001 0100 0000 1000"),
    "sez":    ("  ", "1001 0100 0001 1000"),
    "eijmp":  ("  ", "1001 0100 0001 1001"),
    "sen":    ("  ", "1001 0100 0010 1000"),
    "sev":    ("  ", "1001 0100 0011 1000"),
    "ses":    ("  ", "1001 0100 0100 1000"),
    "seh":    ("  ", "1001 0100 0101 1000"),
    "set":    ("  ", "1001 0100 0110 1000"),
    "sei":    ("  ", "1001 0100 0111 1000"),
    "bclr":   ("b ", "1001 0100 1aaa 1000"),
    "clc":    ("  ", "1001 0100 1000 1000"),
    "clz":    ("  ", "1001 0100 1001 1000"),
    "cln":    ("  ", "1001 0100 1010 1000"),
    "clv":    ("  ", "1001 0100 1011 1000"),
    "cls":    ("  ", "1001 0100 1100 1000"),
    "clh":    ("  ", "1001 0100 1101 1000"),
    "clt":    ("  ", "1001 0100 1110 1000"),
    "cli":    ("  ", "1001 0100 1111 1000"),
    "ret":    ("  ", "1001 0101 0000 1000"),
    "icall":  ("  ", "1001 0101 0000 1001"),
    "reti":   ("  ", "1001 0101 0001 1000"),
    "eicall": ("  ", "1001 0101 0001 1001"),
    "sleep":  ("  ", "1001 0101 1000 1000"),
    "break":  ("  ", "1001 0101 1001 1000"),
    "wdr":    ("  ", "1001 0101 1010 1000"),
    "adiw":   ("Pk", "1001 0110 bbaa bbbb"),
    "sbiw":   ("Pk", "1001 0111 bbaa bbbb"),
    "cbi":    ("ib", "1001 1000 aaaa abbb"),
    "sbic":   ("ib", "1001 1001 aaaa abbb"),
    "sbi":    ("ib", "1001 1010 aaaa abbb"),
    "sbis":   ("ib", "1001 1011 aaaa abbb"),
    "mul":    ("rr", "1001 11ba aaaa bbbb"),
    "in":     ("rI", "1011 0bba aaaa bbbb"),
    "out":    ("Ir", "1011 1aab bbbb aaaa"),
    "rjmp":   ("a ", "1100 aaaa aaaa aaaa"),
    "rcall":  ("a ", "1101 aaaa aaaa aaaa"),
    "ldi":    ("rk", "1110 bbbb aaaa bbbb"),
    "ser":    ("r ", "1110 1111 aaaa 1111"),
    "brbs":   ("ba", "1111 00bb bbbb baaa"),
    "brcs":   ("a ", "1111 00aa aaaa a000"),
    "brlo":   ("a ", "1111 00aa aaaa a000"),
    "breq":   ("a ", "1111 00aa aaaa a001"),
    "brmi":   ("a ", "1111 00aa aaaa a010"),
    "brvs":   ("a ", "1111 00aa aaaa a011"),
    "brlt":   ("a ", "1111 00aa aaaa a100"),
    "brhs":   ("a ", "1111 00aa aaaa a101"),
    "brts":   ("a ", "1111 00aa aaaa a110"),
    "brie":   ("a ", "1111 00aa aaaa a111"),
    "brbc":   ("ba", "1111 01bb bbbb baaa"),
    "brcc":   ("a ", "1111 01aa aaaa a000"),
    "brsh":   ("a ", "1111 01aa aaaa a000"),
    "brne":   ("a ", "1111 01aa aaaa a001"),
    "brpl":   ("a ", "1111 01aa aaaa a010"),
    "brvc":   ("a ", "1111 01aa aaaa a011"),
    "brge":   ("a ", "1111 01aa aaaa a100"),
    "brhc":   ("a ", "1111 01aa aaaa a101"),
    "brtc":   ("a ", "1111 01aa aaaa a110"),
    "brid":   ("a ", "1111 01aa aaaa a111"),
    "bld":    ("rb", "1111 100a aaaa 0bbb"),
    "bst":    ("rb", "1111 101a aaaa 0bbb"),
    "sbrc":   ("rb", "1111 110a aaaa 0bbb"),
    "sbrs":   ("rb", "1111 111a aaaa 0bbb"),
}


class Label(collections.namedtuple("Label", ["symbol", "weak"])):

    def __new__(cls, symbol, weak=False):
        return super(Label, cls).__new__(cls, symbol, weak)


class Insn(collections.namedtuple("Insn", ["op", "arg1", "arg2", "bit_pattern", "size", "arg1_type", "arg2_type"])):

    def __new__(cls, op, arg1=None, arg2=None):
        if op in INSTRUCTIONS:
            arg_types, bit_pattern = INSTRUCTIONS[op]
            arg1_type = ARG_TYPE_CHARS[arg_types[0]]
            arg2_type = ARG_TYPE_CHARS[arg_types[1]]
            size = len(bit_pattern) // 16
            return super(Insn, cls).__new__(cls, op, arg1, arg2, bit_pattern, size, arg1_type, arg2_type)
        else:
            raise Exception("Unknown instruction: " + op)

    def words(self):
        arg1 = self.arg1
        arg2 = self.arg2
        arg1_dupe = self.arg1
        words = []
        word = 0
        i = 0
        for bit_type in reversed(self.bit_pattern):
            if bit_type == " ":
                continue
            elif bit_type == "0":
                bit = 0
            elif bit_type == "1":
                bit = 1
            elif bit_type == "a":
                bit = arg1 & 1
                arg1 >>= 1
            elif bit_type == "b":
                bit = arg2 & 1
                arg2 >>= 1
            elif bit_type == "A":
                bit = arg1_dupe & 1
                arg1_dupe >>= 1
            else:
                raise ValueError(bit_type)
            word |= bit << i
            i += 1
            if i == 16:
                words.insert(0, word)
                i = 0
                word = 0
        return words


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("infile", nargs="+")
    parser.add_argument("-o", "--outfile", required=True)
    parser.add_argument("--vectors", dest="vectors", action="store_true")
    parser.add_argument("--no-vectors", dest="vectors", action="store_false")
    parser.set_defaults(vectors=True)
    args = parser.parse_args()
    program = []
    if args.vectors:
        program += emit_interrupt_vector_table()
    for infile_name in args.infile:
        with open(infile_name, "rt") as infile:
            program += assemble(infile)
    insns = link(program)
    with open(args.outfile, "wb") as outfile:
        write_program(outfile, insns)


def assemble(infile):
    for line in infile:
        line = line.rstrip("\n")
        stmt = parse_line(line)
        if stmt:
            yield stmt


def parse_line(line):
    m = re.match(r"(?P<label>\w+):\s*(;.*)?$", line)
    if m:
        return Label(m.group("label"))
    m = re.match(r"\s+(?P<op>\w+)(\s+(?P<arg1>[\w:-]+)(,\s*(?P<arg2>[\w:-]+))?)?\s*(;.*)?$", line)
    if m:
        return Insn(*m.group("op", "arg1", "arg2"))
    m = re.match(r"\s*(;.*)?$", line)
    if m:
        return None
    raise Exception("syntax error: " + line)


def emit_interrupt_vector_table():
    interrupts = 26
    # Interrupt vector table
    yield Label("__vectors")
    yield Insn("jmp", "RESET")
    for _ in range(interrupts-1):
        yield Insn("jmp", "__bad_interrupt")
    # Bad interrupt handler
    yield Label("__bad_interrupt")
    yield Label("RESET", weak=True)
    yield Insn("jmp", "__vectors")


def link(program):
    labels = scan(program)
    return list(fix(program, labels))


def scan(program):
    addr = 0
    labels = {}
    weak_labels = {}
    for stmt in program:
        if isinstance(stmt, Label):
            if stmt.weak:
                if stmt.symbol in weak_labels:
                    raise Exception("Weak label mutliply-defined: " + stmt.symbol)
                weak_labels[stmt.symbol] = addr
            else:
                if stmt.symbol in labels:
                    raise Exception("Label mutliply-defined: " + stmt.symbol)
                labels[stmt.symbol] = addr
        elif isinstance(stmt, Insn):
            addr += stmt.size
        else:
            raise ValueError(stmt)
    result = dict(weak_labels)
    for label, addr in labels.items():
        result[label] = addr
    return result


def fix(program, labels):
    addr = 0
    for stmt in program:
        if isinstance(stmt, Label):
            pass
        elif isinstance(stmt, Insn):
            addr += stmt.size
            arg1 = eval_arg(stmt.arg1_type, stmt.arg1, labels, addr)
            arg2 = eval_arg(stmt.arg2_type, stmt.arg2, labels, addr)
            yield stmt._replace(arg1=arg1, arg2=arg2)
        else:
            raise ValueError(stmt)


def eval_arg(arg_type, arg, labels, current_addr):
    if arg_type == ArgType.NONE:
        assert arg is None
        return None
    if arg_type == ArgType.ADDR:
        try:
            dest_addr = int(arg)
        except ValueError:
            dest_addr = labels[arg]
        return dest_addr
    elif arg_type == ArgType.ADDR_OFFSET:
        try:
            offset = int(arg)
        except:
            dest_addr = labels[arg]
            offset = dest_addr - current_addr
        return offset % 0x10000
    elif arg_type == ArgType.IO32:
        addr = int(arg)
        assert addr >= 0 and addr <= 32
        return addr
    elif arg_type == ArgType.IO64:
        addr = int(arg)
        assert addr >= 0 and addr <= 64
        return addr
    elif arg_type == ArgType.BIT:
        value = int(arg)
        assert value >= 0 and value <= 8
        return value
    elif arg_type == ArgType.REG32:
        assert arg.startswith("r")
        reg = int(arg[1:])
        assert reg >= 0 and reg <= 31
        return reg
    elif arg_type == ArgType.REG16:
        assert arg.startswith("r")
        reg = int(arg[1:])
        assert reg >= 16 and reg <= 31
        return reg - 16
    elif arg_type == ArgType.REG8:
        assert arg.startswith("r")
        reg = int(arg[1:])
        assert reg >= 16 and reg <= 23
        return reg - 16
    elif arg_type == ArgType.REG_PAIR16:
        m = re.match(r"r(\d+):r(\d+)", arg)
        assert m
        hreg = int(m.group(1))
        lreg = int(m.group(2))
        assert hreg == lreg + 1
        assert lreg % 2 == 0
        assert lreg >= 0 and lreg <= 30
        return lreg >> 1
    elif arg_type == ArgType.REG_PAIR4:
        m = re.match(r"r(\d+):r(\d+)", arg)
        assert m
        hreg = int(m.group(1))
        lreg = int(m.group(2))
        assert hreg == lreg + 1
        assert lreg in [24, 26, 28, 30]
        return (lreg - 24) >> 1
    elif arg_type == ArgType.IMMEDIATE:
        val = int(arg)
        assert val >= 0 and val <= 255
        return val
    elif arg_type == ArgType.IMMEDIATE_INV:
        val = int(arg)
        assert val >= 0 and val <= 255
        val = 255 - val
        return val
    else:
        raise ValueError(arg_type)


def write_program(outfile, insns):
    for insn in insns:
        for word in insn.words():
            write_word(outfile, word)


def write_word(outfile, word):
    outfile.write(struct.pack("<H", word))


if __name__ == "__main__":
    main()