#!/usr/bin/env python3
"""Question: is the KN2400 crt0 (reset target) byte-identical to the KN7000's,
apart from the stack address?  Reads the even/odd program ROM halves (private
archive, read-only), weaves them as ROM_LOAD32_WORD does, decodes the `dc d32`
reset jump at offset 0, and compares N bytes at both targets.
Usage: crt0_compare.py ROMDIR [N]"""
import sys
def il(e,o):
    E=open(e,'rb').read(); O=open(o,'rb').read(); out=bytearray()
    for i in range(0,len(E),2): out+=E[i:i+2]+O[i:i+2]
    return bytes(out)
base=sys.argv[1]; N=int(sys.argv[2],0) if len(sys.argv)>2 else 0x200
img={m:il(f'{base}/{m}/{m}_program_even.rom',f'{base}/{m}/{m}_program_odd.rom') for m in ('kn7000','kn2400','kn6000')}
tgt={}
for m,d in img.items():
    assert d[0] in (0xcc,0xdc), (m, d[:5].hex())
    tgt[m]=int.from_bytes(d[1:3] if d[0]==0xcc else d[1:5],'little',signed=True)
    print(m,'reset jmp ->',hex(0x48400000+tgt[m]))
a=img['kn7000'][tgt['kn7000']:tgt['kn7000']+N]; b=img['kn2400'][tgt['kn2400']:tgt['kn2400']+N]
diff=[i for i in range(N) if a[i]!=b[i]]
print('bytes compared',N,'differing',len(diff))
for i in diff[:40]: print(f'  +{i:#06x}: kn7000 {a[i]:02x} kn2400 {b[i]:02x}')
