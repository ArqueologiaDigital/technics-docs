#!/usr/bin/env python3
"""Question: what is the layout of the KN6000 rhythm-genre records that
kn6000-names.md places at IK2 offset 0x0580f8 (72-byte records: name, then
"10 x u16 params and 9 x 0x4C25xxxx pattern pointers")?
Usage: rhythm_records.py ROMDIR"""
import sys, struct
def il(e,o):
    E=open(e,'rb').read(); O=open(o,'rb').read(); out=bytearray()
    for i in range(0,len(E),2): out+=E[i:i+2]+O[i:i+2]
    return bytes(out)
b=sys.argv[1]
d=il(f'{b}/kn6000/kn6000_program_even.rom',f'{b}/kn6000/kn6000_program_odd.rom')
base=0x200000+0x0580f8
for k in range(4):
    r=d[base+72*k:base+72*(k+1)]
    name=r[:17]
    u16=struct.unpack_from('<9H',r,18)
    ptrs=struct.unpack_from('<9I',r,36)
    print(repr(name), 'byte17=%02x'%r[17], [hex(x) for x in u16], [hex(p) for p in ptrs])
