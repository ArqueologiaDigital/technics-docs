#!/usr/bin/env python3
"""Question: what share of one MN10300 firmware's 16-byte windows occurs
byte-identically ANYWHERE in another (a relocation-tolerant match)?
kn2400-kn2600.md quotes 38.9 % (KN2400->KN7000) and 11.0 % (KN2400->KN6000)
"of non-trivial windows".  The original producer is not committed; this is a
re-derivation with explicit, guessed definitions:
  window   = 16 bytes at every 16-byte-aligned offset of the source image
  trivial  = fewer than MINDISTINCT distinct byte values, or >= 12 printable ASCII
Usage: code_windows.py ROMDIR [MINDISTINCT]"""
import sys
def il(e,o):
    E=open(e,'rb').read(); O=open(o,'rb').read(); out=bytearray()
    for i in range(0,len(E),2): out+=E[i:i+2]+O[i:i+2]
    return bytes(out)
b=sys.argv[1]; md=int(sys.argv[2]) if len(sys.argv)>2 else 6
k={m:il(f'{b}/{m}/{m}_program_even.rom',f'{b}/{m}/{m}_program_odd.rom') for m in ('kn2400','kn6000','kn7000')}
k['kn6000-IK1']=k['kn6000'][:0x200000]
def idx(d):
    s=set()
    for i in range(0,len(d)-15): s.add(d[i:i+16])
    return s
def nontriv(w):
    return len(set(w))>=md and sum(32<=c<127 for c in w)<12
src=k['kn2400'][:0x3965D3]
W=[src[i:i+16] for i in range(0,len(src)-15,16)]
W=[w for w in W if nontriv(w)]
print('kn2400 non-trivial windows',len(W))
for t in ('kn7000','kn6000','kn6000-IK1'):
    S=idx(k[t]); h=sum(w in S for w in W)
    print(f'kn2400 -> {t}: {h}/{len(W)} = {100*h/len(W):.1f} %')
