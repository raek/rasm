start:
    brbc    0, start
    brbs    0, start
    brcc    start
    brcs    start
    breq    start
    brge    start
    brhc    start
    brhs    start
    brid    start
    brie    start
    brlo    start
    brlt    start
    brmi    start
    brne    start
    brpl    start
    brsh    start
    brtc    start
    brts    start
    brvc    start
    brvs    start
    call    0
    cp      r0, r31
    cpc     r0, r31
    cpi     r16, 255
    cpse    r0, r31
    eicall
    eijmp
    icall
    ijmp
    jmp     0
    rcall   start
    ret
    reti
    rjmp    start
    sbic    31, 0
    sbis    31, 0
    sbrc    r0, 7
    sbrs    r0, 7
