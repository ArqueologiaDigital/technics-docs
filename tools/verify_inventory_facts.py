#!/usr/bin/env python3
"""Re-verify two inventory facts quoted on source-tree-inventory.md (read-only).
1. KN1500 IC15: which 256 KiB blocks have every odd byte 0xFF.
2. KN7000 table 80 vs SP7001 table 83: interleave even/odd halves (ROM_LOAD32_WORD:
   2 bytes even, 2 bytes odd) and compare the first 0x3E0660 bytes.
"""
import sys
R='/home/fsanches/compartilhado/technics_roms/roms/kn1500/technics_qsigt3c16079_5y68-j079_japan_9649eai.ic15'
d=open(R,'rb').read()
blk=256*1024
print('KN1500 ic15 size', len(d))
for i in range(0,len(d),blk):
    b=d[i:i+blk]
    odd=b[1::2]; even=b[0::2]
    print(f'  block 0x{i:06X}: odd 0xFF {odd.count(0xff)/len(odd)*100:5.1f}%  even 0xFF {even.count(0xff)/len(even)*100:5.1f}%')
T='/home/fsanches/compartilhado/technics_romsets/kn7000/'
def il(e,o):
    e=open(T+e,'rb').read(); o=open(T+o,'rb').read()
    out=bytearray(len(e)+len(o))
    out[0::4]=e[0::2]; out[1::4]=e[1::2]; out[2::4]=o[0::2]; out[3::4]=o[1::2]
    return bytes(out)
t80=il('kn7000_table_even_b80.ic17','kn7000_table_odd_b80.ic16')
t83=il('kn7000_table_even_sp7001_b83.ic17','kn7000_table_odd_sp7001_b83.ic16')
end=0x3E0660
diffs=[i for i in range(end) if t80[i]!=t83[i]]
print('table80 last non-FF:', hex(max(i for i,b in enumerate(t80) if b!=0xff)))
print('diffs in first 0x3E0660:', len(diffs), [(hex(i), chr(t80[i]), chr(t83[i])) for i in diffs[:5]])
print('table 80 tail after 0x3E0660 all FF:', all(b==0xff for b in t80[end:]))
