.equ zero = r1
.equ temp = r16
.equ data = r17
.equ length = r18

.equ LINE_T = 1024                   ; 64 us
.equ SYNC_T = 75                     ; 4.7 us
.equ BACK_PORCH_T = 91               ; 5.7 us

;.section .data
;pattern:
;        .rept   45
;        .byte   0xFF
;        .endr

;.section .text

;pattern_rom:
;        .rept   5
;        .byte   0xFF
;        .endr
;        .rept   40
;        .byte   0x00
;        .endr
;pattern_rom_end:
;        .align  2

;.global main
main:
        cli
        clr     zero
        rcall   init_timer
        rcall   init_usart
        rcall   copy_pattern
        sei
1:
        rjmp    1b
1:
        ldi     length, pattern_rom_end-pattern_rom
        ldi     r27, hi8(pattern)
        ldi     r26, lo8(pattern)
2:
        in      temp, _SFR_IO_ADDR(TIFR1)
        sbrs    temp, OCF1B
        rjmp    2b
        sbi     _SFR_IO_ADDR(TIFR1), OCF1B
        rcall   TIMER1_COMPB_vect
        rjmp    1b

.global TIMER1_COMPB_vect
TIMER1_COMPB_vect:
        .rept   BACK_PORCH_T-17
        nop
        .endr
        ldi     length, pattern_rom_end-pattern_rom
        ldi     r27, hi8(pattern)
        ldi     r26, lo8(pattern)
2:
        ld      data, x+
        com     data
        sts     UDR0, data
        dec     length
        .rept   8
        nop
        .endr
        brne    2b
        reti

init_timer:
        sbi     _SFR_IO_ADDR(DDRB), 2
        sts     TCNT1H, zero
        sts     TCNT1L, zero
        ldi     temp, hi8(LINE_T-1)
        sts     OCR1AH, temp
        ldi     temp, lo8(LINE_T-1)
        sts     OCR1AL, temp
        ldi     temp, hi8(SYNC_T-1)
        sts     OCR1BH, temp
        ldi     temp, lo8(SYNC_T-1)
        sts     OCR1BL, temp
        ldi     temp, (0<<ICIE1)|(1<<OCIE1B)|(0<<OCIE1A)|(0<<TOIE1)
        sts     TIMSK1, temp
        ldi     temp, (0<<COM1A1)|(0<<COM1A0)|(1<<COM1B1)|(0<<COM1B0)|(1<<WGM11)|(1<<WGM10)
        sts     TCCR1A, temp
        ldi     temp, (0<<ICNC1)|(0<<ICES1)|(1<<WGM13)|(1<<WGM12)|(0<<CS12)|(0<<CS11)|(1<<CS10)
        sts     TCCR1B, temp
        ret

init_usart:
        sts     UBRR0H, zero
        sts     UBRR0L, zero
        sbi     _SFR_IO_ADDR(DDRD), 4
        ldi     temp, (1<<UMSEL00)|(1<<UMSEL01)|(0<<UDORD0)
        sts     UCSR0C, temp
        ldi     temp, (0<<RXEN0)|(1<<TXEN0)
        sts     UCSR0B, temp
        ret

copy_pattern:
        ldi     length, pattern_rom_end-pattern_rom
        ldi     r27, hi8(pattern)
        ldi     r26, lo8(pattern)
        ldi     r31, hi8(pattern_rom)
        ldi     r30, lo8(pattern_rom)
1:
        lpm     data, z+
        st      x+, data
        dec     length
        brne    1b
        ret

;.end
