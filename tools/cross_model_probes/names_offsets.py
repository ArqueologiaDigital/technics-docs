#!/usr/bin/env python3
"""Question: do the IK2/IKV2 offsets quoted on kn6000-names.md hold the strings
the page says?  Offsets are into the decompressed IK2.SLD / IKV2.SLD, i.e. full
program image offset + 0x200000.  Usage: names_offsets.py ROMDIR"""
import sys
def il(e,o):
    E=open(e,'rb').read(); O=open(o,'rb').read(); out=bytearray()
    for i in range(0,len(E),2): out+=E[i:i+2]+O[i:i+2]
    return bytes(out)
b=sys.argv[1]
k6=il(f'{b}/kn6000/kn6000_program_even.rom',f'{b}/kn6000/kn6000_program_odd.rom')
import os
k65=None
if os.path.exists(f'{b}/kn6500'):
    k65=il(f'{b}/kn6500/kn6500_program_even.rom',f'{b}/kn6500/kn6500_program_odd.rom')
for name,img,off in [('kn6000',k6,0x0a32cc),('kn6000',k6,0x0580f8),('kn6000',k6,0x065aec),('kn6500',k65,0x0a7d50)]:
    if img is None: print(name,'missing'); continue
    o=0x200000+off
    print(name, hex(off), 'cpu', hex(0x48600000+off), repr(img[o:o+96]))
