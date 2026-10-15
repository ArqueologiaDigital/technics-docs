#!/usr/bin/env python3
"""Question: does a model's woven program image match the SMCK*.INF checksum
oracle shipped with its update (32-bit total + 16-bit sum per 0x40000 block,
same rule as kn7000_extraction/kn7000_extract.py verify_checksums)?
Usage: inf_check.py ROMDIR SRCDIR MODEL LENGTH(hex) INFNAME"""
import re, sys
def il(e,o):
    E=open(e,'rb').read(); O=open(o,'rb').read(); out=bytearray()
    for i in range(0,len(E),2): out+=E[i:i+2]+O[i:i+2]
    return bytes(out)
romdir,srcdir,m,ln,inf=sys.argv[1:6]
img=il(f'{romdir}/{m}/{m}_program_even.rom',f'{romdir}/{m}/{m}_program_odd.rom')[:int(ln,16)]
e=[int(x,16) for x in re.findall(r'@([0-9A-F]+)',open(f'{srcdir}/{m}/{inf}').read())]
tot=sum(img)&0xffffffff
ok=[ (sum(img[i*0x40000:(i+1)*0x40000])&0xffff)==b for i,b in enumerate(e[1:])]
print(m,'total',hex(tot),'expected',hex(e[0]),'match' if tot==e[0] else 'MISMATCH','blocks',sum(ok),'/',len(ok))
