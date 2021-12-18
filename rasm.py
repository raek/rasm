import argparse
import collections
import enum
import re
import struct


class OperandType(collections.namedtuple("OperandType", "name, value_type, min_value, max_value, post, offset")):

    def __new__(cls, name, value_type, min_value=None, max_value=None, post=None, offset=False):
        return super(OperandType, cls).__new__(cls, name, value_type, min_value, max_value, post, offset)

    def fit_value(self, val, typ, current_addr):
        assert typ == self.value_type
        if self.min_value is not None:
            assert val >= self.min_value
        if self.max_value is not None:
            assert val <= self.max_value
        if self.offset:
            val -= current_addr
        if self.post is not None:
            return self.post(val)
        else:
            return val


class ValueType(enum.Enum):
    NONE      =  0
    REG       =  1
    REG_PAIR  =  2
    XREG      =  3
    XREG_INC  =  4
    XREG_DEC  =  5
    YREG      =  6
    YREG_INC  =  7
    YREG_DEC  =  8
    YREG_DISP =  9
    ZREG      = 10
    ZREG_INC  = 12
    ZREG_DEC  = 13
    ZREG_DISP = 14
    NUMBER    = 15
    IDENT     = 16


Value = collections.namedtuple("Value", ["val", "typ"])


OPERAND_TYPES = {
    " ": OperandType("NONE",        ValueType.NONE),
    "A": OperandType("ADDR",        ValueType.NUMBER),
    "a": OperandType("ADDR_OFFSET", ValueType.NUMBER,           post=(lambda x: x % 0x10000), offset=True),
    "i": OperandType("IO32",        ValueType.NUMBER,    0, 31),
    "I": OperandType("IO64",        ValueType.NUMBER,    0, 63),
    "b": OperandType("BIT",         ValueType.NUMBER,    0, 7),
    "r": OperandType("REG32",       ValueType.REG,       0, 31),
    "h": OperandType("REG16",       ValueType.REG,      16, 31, post=lambda x: x - 16),
    "H": OperandType("REG8",        ValueType.REG,      16, 23, post=lambda x: x - 16),
    "p": OperandType("REG_PAIR16",  ValueType.REG_PAIR,  0, 30, post=lambda x: x >> 1),
    "P": OperandType("REG_PAIR4",   ValueType.REG_PAIR, 24, 30, post=lambda x: x >> 1),
    "x": OperandType("XREG",        ValueType.XREG),
    "u": OperandType("XREG_INC",    ValueType.XREG_INC),
    "U": OperandType("XREG_DEC",    ValueType.XREG_DEC),
    "y": OperandType("YREG",        ValueType.YREG),
    "v": OperandType("YREG_INC",    ValueType.YREG_INC),
    "V": OperandType("YREG_DEC",    ValueType.YREG_DEC),
    "Y": OperandType("YREG_DISP",   ValueType.YREG_DISP, 0, 63),
    "z": OperandType("ZREG",        ValueType.ZREG),
    "w": OperandType("ZREG_INC",    ValueType.ZREG_INC),
    "W": OperandType("ZREG_DEC",    ValueType.ZREG_DEC),
    "Z": OperandType("ZREG_DISP",   ValueType.ZREG_DISP, 0, 63),
    "k": OperandType("IMM",         ValueType.NUMBER),
    "K": OperandType("IMM_INV",     ValueType.NUMBER,           post=lambda x: 0xFF - x),
}


INSTRUCTION_SPECS = [
    ("nop",    "  ", "0000 0000 0000 0000"),
    ("movw",   "pp", "0000 0001 aaaa bbbb"),
    ("muls",   "hh", "0000 0010 aaaa bbbb"),
    ("mulsu",  "HH", "0000 0011 0aaa 0bbb"),
    ("fmul",   "HH", "0000 0011 0aaa 1bbb"),
    ("fmulsu", "HH", "0000 0011 1aaa 1bbb"),
    ("fmuls",  "HH", "0000 0011 1aaa 0bbb"),
    ("cpc",    "rr", "0000 01ba aaaa bbbb"),
    ("sbc",    "rr", "0000 10ba aaaa bbbb"),
    ("add",    "rr", "0000 11ba aaaa bbbb"),
    ("lsl",    "r ", "0000 11Aa aaaa AAAA"),
    ("cpse",   "rr", "0001 00ba aaaa bbbb"),
    ("cp",     "rr", "0001 0110 0000 1111"),
    ("sub",    "rr", "0001 10ba aaaa bbbb"),
    ("adc",    "rr", "0001 11ba aaaa bbbb"),
    ("rol",    "r ", "0001 11Aa aaaa AAAA"),
    ("and",    "rr", "0010 00ba aaaa bbbb"),
    ("tst",    "r ", "0010 00Aa aaaa AAAA"),
    ("eor",    "rr", "0010 01ba aaaa bbbb"),
    ("clr",    "r ", "0010 01Aa aaaa AAAA"),
    ("or",     "rr", "0010 10ba aaaa bbbb"),
    ("mov",    "rr", "0010 11ba aaaa bbbb"),
    ("cpi",    "hk", "0011 bbbb aaaa bbbb"),
    ("sbci",   "hk", "0100 bbbb aaaa bbbb"),
    ("subi",   "hk", "0101 bbbb aaaa bbbb"),
    ("ori",    "hk", "0110 bbbb aaaa bbbb"),
    ("sbr",    "hk", "0110 bbbb aaaa bbbb"),
    ("andi",   "hk", "0111 bbbb aaaa bbbb"),
    ("cbr",    "hK", "0111 bbbb aaaa bbbb"),
    ("ldd",    "rZ", "10b0 bb0a aaaa 0bbb"),
    ("std",    "Zr", "10a0 aa1b bbbb 0aaa"),
    ("ldd",    "rY", "10b0 bb0a aaaa 1bbb"),
    ("std",    "Yr", "10a0 aa1b bbbb 1aaa"),
    ("ld",     "rz", "1000 000a aaaa 0000"),
    ("ld",     "ry", "1000 000a aaaa 1000"),
    ("st",     "zr", "1000 001b bbbb 0000"),
    ("st",     "yr", "1000 001b bbbb 1000"),
    ("lds",    "rA", "1001 000a aaaa 0000 bbbb bbbb bbbb bbbb"),
    ("ld",     "rw", "1001 000a aaaa 0001"),
    ("ld",     "rW", "1001 000a aaaa 0010"),
    ("lpm",    "rz", "1001 000a aaaa 0100"),
    ("lpm",    "rw", "1001 000a aaaa 0101"),
    ("elpm",   "rz", "1001 000a aaaa 0110"),
    ("elpm",   "rw", "1001 000a aaaa 0111"),
    ("ld",     "rv", "1001 000a aaaa 1001"),
    ("ld",     "rV", "1001 000a aaaa 1010"),
    ("ld",     "rx", "1001 000a aaaa 1100"),
    ("ld",     "ru", "1001 000a aaaa 1101"),
    ("ld",     "rU", "1001 000a aaaa 1110"),
    ("pop",    "r ", "1001 000a aaaa 1111"),
    ("sts",    "Ar", "1001 001b bbbb 0000 aaaa aaaa aaaa aaaa"),
    ("st",     "wr", "1001 001b bbbb 0001"),
    ("st",     "Wr", "1001 001b bbbb 0010"),
    ("xch",    "zr", "1001 001b bbbb 0100"),
    ("lac",    "zr", "1001 001b bbbb 0110"),
    ("las",    "zr", "1001 001b bbbb 0101"),
    ("lat",    "zr", "1001 001b bbbb 0111"),
    ("st",     "vr", "1001 001b bbbb 1001"),
    ("st",     "Vr", "1001 001b bbbb 1010"),
    ("st",     "xr", "1001 001b bbbb 1100"),
    ("st",     "ur", "1001 001b bbbb 1101"),
    ("st",     "Ur", "1001 001b bbbb 1110"),
    ("push",   "r ", "1001 001a aaaa 1111"),
    ("ijmp",   "  ", "1001 0100 0000 1001"),
    ("des",    "k ", "1001 0100 aaaa 1011"),
    ("com",    "r ", "1001 010a aaaa 0000"),
    ("neg",    "r ", "1001 010a aaaa 0001"),
    ("swap",   "r ", "1001 010a aaaa 0010"),
    ("inc",    "r ", "1001 010a aaaa 0011"),
    ("asr",    "r ", "1001 010a aaaa 0101"),
    ("lsr",    "r ", "1001 010a aaaa 0110"),
    ("ror",    "r ", "1001 010a aaaa 0111"),
    ("dec",    "r ", "1001 010a aaaa 1010"),
    ("jmp",    "A ", "1001 010a aaaa 110a aaaa aaaa aaaa aaaa"),
    ("call",   "A ", "1001 010a aaaa 111a aaaa aaaa aaaa aaaa"),
    ("bset",   "b ", "1001 0100 0aaa 1000"),
    ("sec",    "  ", "1001 0100 0000 1000"),
    ("sez",    "  ", "1001 0100 0001 1000"),
    ("eijmp",  "  ", "1001 0100 0001 1001"),
    ("sen",    "  ", "1001 0100 0010 1000"),
    ("sev",    "  ", "1001 0100 0011 1000"),
    ("ses",    "  ", "1001 0100 0100 1000"),
    ("seh",    "  ", "1001 0100 0101 1000"),
    ("set",    "  ", "1001 0100 0110 1000"),
    ("sei",    "  ", "1001 0100 0111 1000"),
    ("bclr",   "b ", "1001 0100 1aaa 1000"),
    ("clc",    "  ", "1001 0100 1000 1000"),
    ("clz",    "  ", "1001 0100 1001 1000"),
    ("cln",    "  ", "1001 0100 1010 1000"),
    ("clv",    "  ", "1001 0100 1011 1000"),
    ("cls",    "  ", "1001 0100 1100 1000"),
    ("clh",    "  ", "1001 0100 1101 1000"),
    ("clt",    "  ", "1001 0100 1110 1000"),
    ("cli",    "  ", "1001 0100 1111 1000"),
    ("ret",    "  ", "1001 0101 0000 1000"),
    ("icall",  "  ", "1001 0101 0000 1001"),
    ("reti",   "  ", "1001 0101 0001 1000"),
    ("eicall", "  ", "1001 0101 0001 1001"),
    ("sleep",  "  ", "1001 0101 1000 1000"),
    ("break",  "  ", "1001 0101 1001 1000"),
    ("wdr",    "  ", "1001 0101 1010 1000"),
    ("lpm",    "  ", "1001 0101 1100 1000"),
    ("elpm",   "  ", "1001 0101 1101 1000"),
    ("spm",    "  ", "1001 0101 1110 1000"),
    ("spm",    "w ", "1001 0101 1111 1000"),
    ("adiw",   "Pk", "1001 0110 bbaa bbbb"),
    ("sbiw",   "Pk", "1001 0111 bbaa bbbb"),
    ("cbi",    "ib", "1001 1000 aaaa abbb"),
    ("sbic",   "ib", "1001 1001 aaaa abbb"),
    ("sbi",    "ib", "1001 1010 aaaa abbb"),
    ("sbis",   "ib", "1001 1011 aaaa abbb"),
    ("mul",    "rr", "1001 11ba aaaa bbbb"),
    ("in",     "rI", "1011 0bba aaaa bbbb"),
    ("out",    "Ir", "1011 1aab bbbb aaaa"),
    ("rjmp",   "a ", "1100 aaaa aaaa aaaa"),
    ("rcall",  "a ", "1101 aaaa aaaa aaaa"),
    ("ldi",    "hk", "1110 bbbb aaaa bbbb"),
    ("ser",    "h ", "1110 1111 aaaa 1111"),
    ("brbs",   "ba", "1111 00bb bbbb baaa"),
    ("brcs",   "a ", "1111 00aa aaaa a000"),
    ("brlo",   "a ", "1111 00aa aaaa a000"),
    ("breq",   "a ", "1111 00aa aaaa a001"),
    ("brmi",   "a ", "1111 00aa aaaa a010"),
    ("brvs",   "a ", "1111 00aa aaaa a011"),
    ("brlt",   "a ", "1111 00aa aaaa a100"),
    ("brhs",   "a ", "1111 00aa aaaa a101"),
    ("brts",   "a ", "1111 00aa aaaa a110"),
    ("brie",   "a ", "1111 00aa aaaa a111"),
    ("brbc",   "ba", "1111 01bb bbbb baaa"),
    ("brcc",   "a ", "1111 01aa aaaa a000"),
    ("brsh",   "a ", "1111 01aa aaaa a000"),
    ("brne",   "a ", "1111 01aa aaaa a001"),
    ("brpl",   "a ", "1111 01aa aaaa a010"),
    ("brvc",   "a ", "1111 01aa aaaa a011"),
    ("brge",   "a ", "1111 01aa aaaa a100"),
    ("brhc",   "a ", "1111 01aa aaaa a101"),
    ("brtc",   "a ", "1111 01aa aaaa a110"),
    ("brid",   "a ", "1111 01aa aaaa a111"),
    ("bld",    "rb", "1111 100a aaaa 0bbb"),
    ("bst",    "rb", "1111 101a aaaa 0bbb"),
    ("sbrc",   "rb", "1111 110a aaaa 0bbb"),
    ("sbrs",   "rb", "1111 111a aaaa 0bbb"),
]


INSTRUCTIONS = {}
for op, operand_types, bit_pattern in INSTRUCTION_SPECS:
    size = len(bit_pattern) // 16
    operand1_type = OPERAND_TYPES[operand_types[0]]
    operand2_type = OPERAND_TYPES[operand_types[1]]
    variant = bit_pattern, operand1_type, operand2_type
    if op in INSTRUCTIONS:
        insn_size, variants = INSTRUCTIONS[op]
        assert size == insn_size
        variants.append(variant)
    else:
        INSTRUCTIONS[op] = size, [variant]


class Label(collections.namedtuple("Label", ["symbol", "weak"])):

    def __new__(cls, symbol, weak=False):
        return super(Label, cls).__new__(cls, symbol, weak)


class Insn(collections.namedtuple("Insn", ["op", "arg1", "arg2", "size", "variants"])):

    def __new__(cls, op, arg1=Value(None, ValueType.NONE), arg2=Value(None, ValueType.NONE)):
        if op in INSTRUCTIONS:
            size, variants = INSTRUCTIONS[op]
            return super(Insn, cls).__new__(cls, op, arg1, arg2, size, variants)
        else:
            raise Exception("Unknown instruction: " + op)


Equ = collections.namedtuple("Equ", ["var", "expr", "weak"])


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
        for word in insns:
            outfile.write(struct.pack("<H", word))


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
    m = re.match(r"\s+(?P<op>\w+)(\s+(?P<arg1>[\w:+-]+)(,\s*(?P<arg2>[\w:+-]+))?)?\s*(;.*)?$", line)
    if m:
        arg1 = parse_expr(m.group("arg1"))
        arg2 = parse_expr(m.group("arg2"))
        return Insn(m.group("op"), arg1, arg2)
    m = re.match(r".(?P<dir>equ|default)\s+(?P<var>[A-Za-z_][0-9A-Za-z_]*)\s*=\s*(?P<expr>.*?)\s*(;.*)?$", line)
    if m:
        expr = parse_expr(m.group("expr"))
        weak = {"equ": False, "default": True}[m.group("dir")]
        return Equ(m.group("var"), expr, weak)
    m = re.match(r"\s*(;.*)?$", line)
    if m:
        return None
    raise Exception("syntax error: " + line)


def parse_expr(arg):
    regs = {
        "x":  ValueType.XREG,
        "x+": ValueType.XREG_INC,
        "-x": ValueType.XREG_DEC,
        "y":  ValueType.YREG,
        "y+": ValueType.YREG_INC,
        "-y": ValueType.YREG_DEC,
        "z":  ValueType.ZREG,
        "z+": ValueType.ZREG_INC,
        "-z": ValueType.ZREG_DEC,
    }
    if arg is None:
        return Value(None, ValueType.NONE)
    if arg in regs:
        return Value(None, regs[arg])
    m = re.match(r"r(\d+)$", arg)
    if m:
        reg = int(m.group(1))
        assert reg >= 0 and reg <= 31
        return Value(reg, ValueType.REG)
    m = re.match(r"r(\d+):r(\d+)$", arg)
    if m:
        hi_reg = int(m.group(1))
        lo_reg = int(m.group(2))
        assert hi_reg == lo_reg + 1
        assert lo_reg % 2 == 0
        assert lo_reg >= 0 and lo_reg <= 30
        return Value(lo_reg, ValueType.REG_PAIR)
    m = re.match(r"([yz])\+(0|[1-9][0-9]*)", arg)
    if m:
        types = {
            "y": ValueType.YREG_DISP,
            "z": ValueType.ZREG_DISP,
        }
        reg = m.group(1)
        disp = int(m.group(2))
        assert disp >= 0 and disp <= 63
        return Value(disp, types[reg])
    m = re.match(r"-?(0|[1-9][0-9]*)$", arg)
    if m:
        return Value(int(arg), ValueType.NUMBER)
    m = re.match(r"[A-Za-z_][0-9A-Za-z_]*$", arg)
    if m:
        return Value(arg, ValueType.IDENT)
    raise Exception("expression syntax error: " + arg)


def emit_interrupt_vector_table():
    interrupts = 26
    # Interrupt vector table
    yield Label("__vectors")
    yield Equ("RESET", Value("__bad_interrupt", ValueType.IDENT), weak=True)
    yield Insn("jmp", Value("RESET", ValueType.IDENT))
    for _ in range(interrupts - 1):
        yield Insn("jmp", Value("__bad_interrupt", ValueType.IDENT))
    # Bad interrupt handler
    yield Label("__bad_interrupt")
    yield Insn("jmp", Value("__vectors", ValueType.IDENT))


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
                assert stmt.symbol not in weak_labels
                weak_labels[stmt.symbol] = Value(addr, ValueType.NUMBER)
            else:
                assert stmt.symbol not in labels
                labels[stmt.symbol] = Value(addr, ValueType.NUMBER)
        elif isinstance(stmt, Insn):
            addr += stmt.size
        elif isinstance(stmt, Equ):
            if stmt.weak:
                assert stmt.var not in weak_labels
                weak_labels[stmt.var] = stmt.expr
            else:
                assert stmt.var not in labels
                labels[stmt.var] = stmt.expr
        else:
            raise ValueError(stmt)
    result = dict(weak_labels)
    for label, addr in labels.items():
        result[label] = addr
    return result


def fix(program, labels):
    addr = 0
    for stmt in program:
        if isinstance(stmt, Insn):
            addr += stmt.size
            arg1 = eval_arg(stmt.arg1, labels)
            arg2 = eval_arg(stmt.arg2, labels)
            yield from fix_insn(stmt, arg1, arg2, addr)


def eval_arg(arg, env):
    if arg.typ == ValueType.IDENT:
        assert arg.val in env
        return eval_arg(env[arg.val], env)
    else:
        return arg


def fix_insn(insn, arg1, arg2, current_addr):
    valid_variant_words = []
    for variant in insn.variants:
        words = try_variant(variant, arg1, arg2, current_addr)
        if words is not None:
            valid_variant_words.append(words)
    assert len(valid_variant_words) == 1
    return valid_variant_words[0]


def try_variant(variant, arg1, arg2, current_addr):
    bit_pattern, operand1_type, operand2_type = variant
    try:
        op1 = operand1_type.fit_value(arg1.val, arg1.typ, current_addr)
        op2 = operand2_type.fit_value(arg2.val, arg2.typ, current_addr)
    except AssertionError:
        return None
    return insn_words(bit_pattern, op1, op2)


def insn_words(bit_pattern, arg1, arg2):
    arg1_dupe = arg1
    words = []
    word = 0
    i = 0
    for bit_type in reversed(bit_pattern):
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


if __name__ == "__main__":
    main()
