#!/usr/bin/env python3
"""Question: what share of one MN10300 firmware's distinct >=8-char printable
ASCII strings occurs verbatim in another's?  (kn2400-kn2600.md quotes
74.3 % (11310/15220) KN2400<->KN7000 and 23.6 % (3587/15220) KN2400<->KN6000;
kn6000-roadmap.md quotes 4,479 of the KN6000's 5,234 in the KN7000.)
Reads even/odd ROM halves from a private ROM directory (read only), weaves
them as ROM_LOAD32_WORD does.  Usage: string_share.py ROMDIR [minlen]"""
import re, sys
def il(e,o):
    E=open(e,'rb').read(); O=open(o,'rb').read(); out=bytearray()
    for i in range(0,len(E),2): out+=E[i:i+2]+O[i:i+2]
    return bytes(out)
base=sys.argv[1]; n=int(sys.argv[2]) if len(sys.argv)>2 else 8
def img(m, part='program'):
    return il(f'{base}/{m}/{m}_{part}_even.rom', f'{base}/{m}/{m}_{part}_odd.rom')
ims={'kn2400':img('kn2400'),'kn6000':img('kn6000'),'kn7000':img('kn7000')}
try: ims['kn7000+table']=ims['kn7000']+img('kn7000','table')
except Exception as e: print('no kn7000 table',e)
pat=re.compile(rb'[\x20-\x7e]{%d,}'%n)
S={k:set(pat.findall(v)) for k,v in ims.items()}
for k,v in S.items(): print(k,'distinct',len(v))
for a,b in [('kn2400','kn7000'),('kn2400','kn7000+table'),('kn2400','kn6000'),('kn6000','kn7000'),('kn6000','kn7000+table')]:
    sh=len(S[a]&S[b]); print(f'{a} in {b}: {sh}/{len(S[a])} = {100*sh/len(S[a]):.1f} %')
    # substring containment variant

# Variant: the KN6000 as first extracted (IK1 only, the low 2 MB), the state
# of kn7000_mame before the boot fix "Root cause 1" (notes/kn6000-kn6500-boot.md).
low=ims['kn6000'][:0x200000]; L=set(pat.findall(low))
print('kn6000 low 2 MB (IK1 only) distinct', len(L))
sh=len(S['kn2400']&L); print(f'kn2400 in kn6000-IK1-only: {sh}/{len(S["kn2400"])} = {100*sh/len(S["kn2400"]):.1f} %')
sh=len(L&S['kn7000']); print(f'kn6000-IK1-only in kn7000: {sh}/{len(L)} = {100*sh/len(L):.1f} %')
