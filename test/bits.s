RESET:
    cbi     31, 0
    clc
    clh
    cli
    cln
    cls
    clt
    clv
    clz
    sbi     31, 0
    sec
    seh
    sei
    sen
    ses
    set
    sev
    sez
    jmp     RESET
