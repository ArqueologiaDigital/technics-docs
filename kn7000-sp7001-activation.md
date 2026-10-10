---
layout: page
title: "SP7001 Activation & Key Generator"
permalink: /kn7000-sp7001-activation/
---

# SP7001 PLUG-iN activation — reverse engineering & key generator

The [SP7001 "SD PLUG-iN"]({{ site.baseurl }}/kn7000-sd-plugin/) — KEY SOFT SERVICE's
paid floppy→SD song-conversion add-on for the KN7000 — is gated behind a
**challenge/response licence check**. The instrument shows a per-unit *serial*
(the "Software Code"); the owner typed a 16-character *password* (the "Liberation
Key"); the firmware accepted it only if it matched a value computed from that
serial. KEY SOFT SERVICE has ceased trading and
[published its own key generator]({{ site.baseurl }}/kn7000-sd-plugin/#what-the-vendor-says),
so documenting the scheme here is uncontroversial preservation work.

This page records the algorithm we reverse-engineered from the firmware's
**verification** side, the real serial/password pair for the emulator, an embedded
key generator you can run in the browser, and how our result lines up with the
vendor's original tool.

> Everything here is ordinary preservation reverse engineering of firmware running
> in MAME, so that owners of the defunct product can continue to use software they
> paid for. The activation service is gone; no live system is affected.

## The activation gate

With the SP7001 program/table loaded (`kn7000 -bios sp7001`), inserting a
non-master SD card drops the instrument into the licence screen. In the emulator
the serial is **deterministic**: every unit reports `gpcm_uwp5_namw_lud5`. A wrong
entry shows *"Falsches Passwort"* (the string lives in the table ROM at
`0x483f782c`).

At the firmware level the check is a small MN10300 call graph in the SP7001 table
ROM:

| Routine | Address | Role |
|---|---|---|
| OK-button handler | `0x483e9e1c` | runs the check, then an "apply" that re-validates |
| check dispatcher | `0x483ee8e9` | builds the serial-derived target, calls the comparator |
| comparator | `0x483ef0af` | transforms the typed key and compares it to the target |
| per-char transform | `0x483ef234` | one reversible base-35 substitution step |
| transform driver | `0x483ef1ad` | applies the transform across the 16 characters |
| keystream table | `0x483f8b74` | 26 static 20-char records, one per first letter |

Both the password *check* and the activation *apply* run the comparator, and both
must pass — forcing only one of them is not enough.

### How the activation algorithm works

The activation password is 16 characters over a **base-35 alphabet** — the digits
`1`-`9` and the letters `a`-`z` (there is no `0`). It is entered and displayed as
four groups of four, `XXXX-XXXX-XXXX-XXXX`; the comparator first strips the dashes
to a plain 16-character buffer.

Each character maps to a number with a fixed pair of tables:

- **dec** (char → value): `1`-`9` become `0`-`8`; `a`-`z` become `9`-`34` (i.e.
  subtract `0x58` from the ASCII code).
- **enc** (value → char): `0`-`8` become `1`-`9`; `9`-`31` become `a`-`w`.

The core routine at `0x483ef234` transforms one character at position `i` using
one key character `k`:

```
out_i = enc( ( (dec(in_i) - i) & 0x1f ) XOR dec(k) )
```

This is **position-independent and fully reversible**: each output depends only on
its own input, its index `i`, and its key — there is no running feedback between
characters. Character 0 is copied through unchanged; characters 1-15 are
transformed. (A character whose `dec` value exceeds 31 — `x`, `y`, `z` — is
rejected.)

The key stream is a **static ROM table**: 26 records of 20 base-35 characters
each, starting at `0x483f8b74` with a stride of `0x15` bytes. One record is
selected per transform pass by the password's first character
(`c0 = firstchar − 'a'`), and the key for position `i` is simply the `i`-th
character of that record. The driver (`0x483ef1ad`) applies the transform
**twice**: pass 1 uses record `c0`, pass 2 uses record `c0 + 1`. (The 26 records
tile one master keystream — each record's last four characters equal the previous
record's first four.)

The comparator at `0x483ef0af` does **not** check the whole 16-character result.
It verifies only an 11-character window, positions 1 through 11:

- positions 1-3 (**field 3**) must equal a 3-character constant — for the SP7001
  this is the string `mr7`, stored in ROM at `0x483f8900`;
- positions 4-11 (**field 8**) must equal an 8-character value derived from the
  unit's serial number by the check dispatcher at `0x483ee8e9`.

Position 0 and positions 12-15 are never checked. Because the substitution is
reversible and its key stream is a fixed ROM constant, **recovering a valid
password is just inverting the transform** of any 16-character string whose window
`[1:12]` equals the required `field3 + field8` target: run the two passes
backwards (undo pass 2, then pass 1) to obtain a password the device accepts.

### Where the serial comes in

`field3` is the constant `mr7` (SP7001's plug-in type code; the ROM also holds
`bwa`, `8he`, `nn2` for sibling plug-ins). `field8` is the serial-derived part. The
dispatcher builds it as:

```
buf16 = method_0x340(serial state)      # serial → 16-byte buffer (C++ method, see below)
buf16 = right-pad to 16 with spaces     # 0x483ecc6d
field8 = hash(buf16)                    # 0x483ef275, 16 chars → 8 chars
```

The hash at `0x483ef275` is fully decoded (two 32-bit accumulators — a shift-xor
hash and an ELF-style hash — emitted 5 bits at a time; see
`research-scratch/kn7000-sp7001-activation/param1_hash.py`). The one step still
captured at runtime rather than modelled from first principles is
`method_0x340` — a C++ virtual call through a RAM object pointer (`0x50299298`),
which turns the serial into the 16-byte hash input. For the emulator we read the
resulting `field8` directly at the comparator: **`hmd2r6w2`**.

## The emulator's serial → password

Putting it together for the emulator's fixed serial:

| | value |
|---|---|
| Serial (Software Code) | `gpcm_uwp5_namw_lud5` |
| field 3 (constant) | `mr7` |
| field 8 (from serial) | `hmd2r6w2` |
| **Recovered password** | **`a19a-1s1d-jrdc-n1b2`** |

(The SP7001's SYSTEM-INFO screen that shows this serial also reports the plug-in's
own version — `SOFTWARE V1.0 Aug 23 2003` — now recorded in the `sp7001` MAME BIOS
description; the date string lives in the table ROM at `0x483f8e88`.)

This was **confirmed** in MAME: injected into the comparator, this key makes both
the password check and the activation apply return "accepted" (the transform of
`a19a1s1djrdcn1b2` is `amr7hmd2r6w21111`, whose `[1:12]` is exactly `mr7hmd2r6w2`).
Because positions 0 and 12-15 are unchecked, other keys are valid too — the
generator below picks one.

## Key generator

<div id="sp7001-keygen" style="border:1px solid #bbb;border-radius:8px;padding:1em 1.2em;margin:1em 0;background:rgba(127,127,127,0.06)">
  <p style="margin:0 0 .6em 0"><strong>SP7001 key generator.</strong> Runs entirely in your browser (no data leaves the page). For the MAME emulator the serial is always the same, so the key is fixed; the advanced box generates a key from a captured <code>field 8</code> target for any unit.</p>
  <label>Serial (Software Code):
    <input id="kg-serial" type="text" value="gpcm_uwp5_namw_lud5" size="24" style="font-family:monospace">
  </label>
  <button id="kg-go" type="button">Generate key</button>
  <p id="kg-out" style="font-family:monospace;font-size:1.25em;margin:.6em 0"></p>
  <p id="kg-note" style="font-size:.9em;color:#777;margin:.2em 0"></p>
  <details style="margin-top:.6em">
    <summary style="cursor:pointer">Advanced — generate from a captured target</summary>
    <p style="font-size:.9em;color:#777">If you captured your unit's 8-character <code>field 8</code> target at the comparator (see the research scripts), enter it here. <code>field 3</code> is the constant <code>mr7</code>; first char and tail are free (unchecked).</p>
    <label>field 8: <input id="kg-f8" type="text" value="hmd2r6w2" size="10" style="font-family:monospace"></label>
    <label>field 3: <input id="kg-f3" type="text" value="mr7" size="5" style="font-family:monospace"></label>
    <label>first: <input id="kg-fc" type="text" value="a" size="2" maxlength="1" style="font-family:monospace"></label>
    <label>tail: <input id="kg-tail" type="text" value="1111" size="5" maxlength="4" style="font-family:monospace"></label>
    <button id="kg-go2" type="button">Generate from target</button>
    <p id="kg-out2" style="font-family:monospace;font-size:1.1em;margin:.5em 0"></p>
  </details>
</div>

<script>
/* SP7001 PLUG-iN activation key generator — faithful port of invert.py.
 * Base-35 alphabet {1-9, a-z}. Position-independent double substitution. */
var SP7001_RECORDS = [
  "uiuekiphb848j5gum2ht", "7p4fsohg399udb61uiue", "db61nlekuwbbl5qp7p4f",
  "l5qpl97hlmpbqc99db61", "qc99gopqp33v6efdl5qp", "6efd4s9ioiirfqmlqc99",
  "fqmlfevjij8gk3kl6efd", "k3klagvtl6lmog2bfqml", "og2b6u9ww5quu8ugk3kl",
  "u8ugblkdmj1m6r32og2b", "6r32d47p14su7j8gu8ug", "7j8ggipi9cua7j8g6r32",
  "ern7vfa7lbonern77j8g", "mgfs7u1i2olj97sqern7", "97sqp2792do7mvmemgfs",
  "mvmew844njk8j8og97sq", "j8ogwlphhecumj2kmvme", "mj2kghum4cdkfrhhj8og",
  "frhhpku5d99w8jthmj2k", "8jthgff676lkwhjqfrhh", "whjqhsm19b564rlr8jth",
  "4rlrtara3p7sfgfqwhjq", "fgfql39ipkur4qrs4rlr", "4qrsnwaavg1hktk9fgfq",
  "ktk9d9frapb5j5gu4qrs", "j5guniuhum49uiuektk9", "m2ht1bvqgap26ucfj5gu"
];
function kgDec(ch){var o=ch.charCodeAt(0);if(o>=0x31&&o<=0x39)return o-0x31;if(o>0x39)return o-0x58;return o-0x31;}
function kgEnc(r){return String.fromCharCode(r<=8?r+0x31:r+0x58);}
function kgInvChar(outCh,keyCh,i){var r=kgDec(outCh)&0x1f;var m=r^(kgDec(keyCh)&0x1f);var din=(m+i)&0x1f;return kgEnc(din);}
function kgInvert(target16,c0){var recA=SP7001_RECORDS[c0],recB=SP7001_RECORDS[c0+1];var x=target16.charAt(0),i;
  for(i=1;i<16;i++)x+=kgInvChar(target16.charAt(i),recB.charAt(i),i);
  var p=x.charAt(0);for(i=1;i<16;i++)p+=kgInvChar(x.charAt(i),recA.charAt(i),i);return p;}
function kgMake(firstChar,field8,field3,tail){
  var c0=firstChar.charCodeAt(0)-97;
  if(c0<0||c0>25)return {error:"first char must be a-z"};
  var target=firstChar+field3+field8+tail;
  if(target.length!==16)return {error:"field3("+field3.length+")+field8("+field8.length+") must total 11; got "+(target.length-5)};
  var pw=kgInvert(target,c0);
  var dashed=pw.substr(0,4)+"-"+pw.substr(4,4)+"-"+pw.substr(8,4)+"-"+pw.substr(12,4);
  return {password:pw,dashed:dashed};
}
/* Known serial → field8 targets (field8 is the serial hash; only captured ones are listed). */
var SP7001_KNOWN = { "gpcm_uwp5_namw_lud5": "hmd2r6w2" };
(function(){
  function run(){
    var s=(document.getElementById("kg-serial").value||"").trim();
    var out=document.getElementById("kg-out"), note=document.getElementById("kg-note");
    if(SP7001_KNOWN.hasOwnProperty(s)){
      var r=kgMake("a",SP7001_KNOWN[s],"mr7","1111");
      out.textContent=r.dashed;
      note.textContent="Liberation Key for serial "+s+" (confirmed accepted by the firmware).";
    } else {
      out.textContent="—";
      note.textContent="This serial's field-8 target is not on file. The serial→target step is a firmware hash whose input is captured at the comparator; use the advanced box with your unit's captured field-8 value.";
    }
  }
  function run2(){
    var r=kgMake(
      (document.getElementById("kg-fc").value||"a"),
      (document.getElementById("kg-f8").value||"").trim(),
      (document.getElementById("kg-f3").value||"mr7").trim(),
      (document.getElementById("kg-tail").value||"1111"));
    document.getElementById("kg-out2").textContent = r.error ? ("error: "+r.error) : r.dashed;
  }
  document.getElementById("kg-go").addEventListener("click",run);
  document.getElementById("kg-go2").addEventListener("click",run2);
  run();
})();
</script>

Prefer not to type a 16-character key? The research repository ships an autoboot
Lua script, `unlock_plugin.lua`, that patches the comparator in the running
emulator so it accepts **any** password — a one-click unlock for a defunct-service
DRM. The key generator above exists because it recovers a *genuine* password
(proving the algorithm), not just a bypass.

## Comparison with the original KEY SOFT SERVICE generator

The activation scheme for the SP7001 was not written by Technics. It was supplied
by KEY SOFT SERVICE, a Swiss vendor that licensed several KN7000-era products
through a single, reusable challenge/response mechanism. After the company ceased
trading it published its own generator on its legacy web page
(`keysoftservice.ch/keygenerator.htm`, © 1997/2002), describing it as the tool that
had protected *"unsere Software (HD-TechManager und andere)"* against casual
copying.

**Their tool.** The published artifact is a Windows executable, `KeyGenerator.exe`
(*"keine Installation"*), not JavaScript — the web page is only a download and
information page. An operator ran it with three inputs: the master password
**`soerenberg`**, a **LiberationKeyLength of 16**, and the unit's **Software Code**
(the challenge printed by the instrument). It emitted a **Liberation Key** to be
typed back into the software. It is a *generic* licensing generator, used across
multiple KEY SOFT SERVICE products with the SP7001 as one case.

**Our artifact.** Ours is an independent JavaScript reimplementation, derived by
reverse-engineering the KN7000 firmware's **verification** side rather than
disassembling their binary. It models the confirmed per-character transform, the
26-record keystream recovered from the table ROM, and the comparator's field
checks, then *inverts* them to emit a password for a given unit.

**Corroboration.** The two efforts meet from opposite directions. Their documented
**key length of 16** matches our recovered key exactly (a 16-character base-35
value, shown as four groups of four). Their tool is the forward/generate side; our
RE is the verify/invert side of the *same* scheme — strong mutual corroboration
that we have modelled the real mechanism. The master password `soerenberg` is not
present anywhere in the KN7000 firmware: the checker stores no secret, it only
recomputes the serial's target and compares, so `soerenberg` is internal to the
vendor's generator.

**What is not yet done.** We have the verify side, the full keystream, the decoded
`field8` hash, and a confirmed working key for the emulator's serial. The only
unmodelled link is the firmware method that turns the printed serial into the
hash's 16-byte input (`method_0x340`); we currently read the resulting `field8`
target at the comparator per unit. Their `KeyGenerator.exe` could in principle be
disassembled to confirm the forward derivation end to end, which we have not done.

## Provenance & reproducibility

- Full write-up, the disassembly, the transform model and inverter, the live-trace
  capture scripts and the `field8` hash model:
  `research-scratch/kn7000-sp7001-activation/` (`ALGORITHM.md`, `invert.py`,
  `trace_activation.lua`, `inject_verify.lua`, `param1_hash.py`).
- The key generator on this page is a line-for-line port of `invert.py`, validated
  to reproduce the live comparator trace and to emit the confirmed key
  `a19a-1s1d-jrdc-n1b2` for the emulator serial.
- Vendor context: the [SD PLUG-iN (SP7001) page]({{ site.baseurl }}/kn7000-sd-plugin/)
  and KEY SOFT SERVICE's own product/Q&A and `keygenerator.htm` pages (© 2002).
