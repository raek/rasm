        adc     r0, r31
        add     r0, r31
        adiw    r25:r24, 63
        and     r0, r31
        andi    r16, 255
        cbr     r16, 255
        clr     r0
        com     r0
        dec     r0
        des     15
        eor     r0, r31
        fmul    r16, r23
        fmuls   r16, r23
        fmulsu  r16, r23
        inc     r0
        mul     r0, r31
        muls    r16, r31
        mulsu   r16, r23
        neg     r0
        or      r0, r31
        ori     r16, 255
        sbc     r0, r31
        sbci    r16, 255
        sbiw    r25:r24, 63
        sbr     r16, 255
        ser     r0
        sub     r0, r31
        subi    r16, 255
        tst     r0
