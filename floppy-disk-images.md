---
layout: page
title: Floppy Disk Images
permalink: /floppy-disk-images/
---

# Floppy disk images: how we build them, and what the instruments' own formatters write

MAME's floppy software lists for the Technics instruments (`kn5000_flop`, `kn6000_flop`,
`kn7000_flop`) hold disks that no one has dumped yet. They are reconstructions, made from the
"disk creator" installers that were distributed for these instruments. This page sets out the
rule those reconstructions follow, and why. It also records what the KN5000, KN6000 and KN7000
write when they format a floppy, measured by running their own FORMAT in MAME on 2026-10-18.

The tools, the blank disks the formatters wrote, and the command recipes that produced them are
in the kn7000_mame repository, `tools/floppy-images/`, whose README carries every number quoted
here.

## The rule

1. **A dump of a real disk wins.** When one exists, it is the software-list entry.
2. **Otherwise, start from a blank disk formatted by the instrument the list is for.** A
   `kn5000_flop` entry is built on a disk the KN5000 formatted, a `kn6000_flop` entry on one the
   KN6000 formatted, a `kn7000_flop` entry on one the KN7000 formatted, and so on for any model
   we add later. The formatting is done by the instrument's own firmware, running in MAME
   (DISK, DISK TOOLS, FLOPPY DISK FORMAT, 1.44M), and the result is saved as a raw `.img`.
3. **Name the disk after its software-list entry,** the way a user would on the instrument's
   DISK NAMING screen: `ca6fp01` is labelled `CA6FP01____`.
4. **Add the files the way the installer adds them** (below), and check the result against the
   blank disk and the installer before it goes anywhere.

### Why the installer cannot give us the disk

All 79 installers in the CA software mirror (`ca6fp01.exe`, `idd7000.exe`, and the rest) are ZIP
archives behind a self-extractor stub: 70 use WinZip Self-Extractor, a 16-bit Windows program,
and 9 use Mijenix ZipMagic, a 32-bit one. Run on a PC, they copy their files onto a disk that
is already formatted. ZipMagic's prompt says so: "Bitte legen Sie eine leere HD-Diskette ein -
Please insert a formatted HD-disk". They never write a boot sector, a FAT or a volume label.

So the archive fixes the content of every file, and `unzip -t` checks each one against its
CRC-32. The rest of the disk comes from whatever formatted it. Running an installer under Wine
would only put the same files into a folder on the host. Running it in DOSBox needs a Windows
installation, and the layout would then come from the PC's FORMAT command. These disks were made
to be read on the instrument, so its own format is the base we use.

The first software-list builds did not follow this. They came from a Python FAT library and
have 12-sector FATs, a FAT that starts `F0 0F FF`, a pinned serial number and zeroed dates. The
KN6000 and KN7000 media checks reject them; see
[KN7000 slide shows]({{ site.baseurl }}/kn7000-slideshow/) and
[KN6000 roadmap]({{ site.baseurl }}/kn6000-roadmap/).

### How the files go on

The builder writes the disk as a PC writing to a freshly formatted floppy would:

- files go in archive order, each in contiguous clusters starting at the first free one;
- directory entries go into the first free root-directory slots, after the label;
- each name is the 8.3 name in upper case, with no long-file-name entries;
- each file keeps the DOS attribute byte and the write date and time stored in the archive, and
  the creation and access fields stay 0, as DOS and Windows 3.1 leave them;
- bytes after the end of a file in its last sector are 0;
- every sector no file uses keeps the instrument's fill byte.

Only the last three points are choices: a real PC run could differ there. For example, Windows
95/98 may add long-name entries for the 1,050 member names that are not all upper case, and it
fills in creation dates (not tested).

## What the formatters write

The KN5000 (v10), KN6000 and KN7000 (941) formatters produce **byte-identical** blank disks
(SHA-1 `32d74744faf9d0648663fd29b13338a2267c7193` with the name left empty).

| region         | sectors    | content                                                                                                                                                                                                                                                                 |
|----------------|------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| boot sector    | 0          | `EB 1C 90`, OEM `Technics`, DOS 3.x parameter block (512-byte sectors, 1 per cluster, 1 reserved, 2 FATs of 9 sectors, 224 root entries, 2880 sectors, media `F0`, 18 sectors per track, 2 heads), then `EB FE` (a jump to itself) and zeros. **No `55 AA` signature.** |
| FAT 1 and 2    | 1-9, 10-18 | `F0 FF FF`, then zeros                                                                                                                                                                                                                                                  |
| root directory | 19-32      | entry 0 is the volume label: attribute `0x28`, no date, time, cluster or size; the rest is zeros                                                                                                                                                                        |
| data           | 33-2879    | every byte `E5`                                                                                                                                                                                                                                                         |

- **The label** is the typed name padded with `_` to 11 characters. With no name typed it is
  eleven `_`. Typing "KN" on the KN6000 changed exactly two bytes.
- **The fill byte `E5`** comes from the FORMAT TRACK command, which all three send with 512-byte
  sectors, 18 per track, gap length `0x6C` and fill `E5`, on all 80 cylinders and both heads.
  After that they write sectors 0-32 one at a time, write the label sector (19) again, and read
  back cylinder 79, sector 18.
- **The KN5000 and KN7000 traces match command for command.** The KN6000 run, taken without the
  trace, produced the same disk.
- **All three ask for the name after formatting.** The KN5000 and KN6000 open DISK NAMING
  straight away. The KN7000 first shows a message box, which EXIT closes.
- **The 32-byte boot head is a table in each program ROM,** next to a 720 KB twin (media `F9`,
  3-sector FATs, 2 sectors per cluster). The file offsets of the 1.44 MB head are: KN5000 v10
  `0x450DA` (`FDC_Format2HD_BootSectorHead` at `0xE450DA`), KN5000 v5 `0x450BA`, KN6000
  `0x385097` (program pair interleaved by 16-bit words), KN7000 941 `0x3360DF`. The KN5000
  formatter (`FDC_Format2HD_*` in the disassembly) zero-fills every sector it writes, which is
  why the area after `EB FE` and the empty FAT and root sectors are zeros.

`fsck.fat -n` exits 1 on these disks, including the blank one exactly as the instrument wrote
it, for one reason. There is no extended boot record, so it finds no boot-sector label to match
the root's. It also reports 4,276,813,824 hidden sectors, because it reads the bytes
`00 00 EB FE` at offset `0x1C` as one 32-bit field. Both come from how the instruments format a
disk; neither is a defect in a built image.

## The first image built this way

`ca6fp01`, the first KN6000 feature presentation disk ("Weserbergland"), was built on the
KN6000's blank disk with the label `CA6FP01`. Two builds give the same SHA-1,
`e5f4f3d28ab9cb70621fc17f609f8f707bfeed03`.

- **The checker passes all 28 checks.** It is written separately from the builder and confirms
  that every file matches the archive in name, attribute, date and content, that the clusters
  are laid out contiguously, and that every other byte is still the blank disk's.
- **`fsck.fat`** reports only the label note above.
- **On the emulated KN6000** (DEMONSTRATION screen, insert the disk) it loads directly, with no
  relayout step, and the slides play from t = 69 s onwards.

The remaining entries are to be rebuilt the same way, each on its own instrument's blank disk,
before any of them goes upstream.

## What it took to run the formatters in MAME

Formatting a disk exercises paths that loading one does not. Six driver defects turned up, all
now fixed in the kn7000_mame overlay (details in the driver comments and the
[FDC subsystem]({{ site.baseurl }}/fdc-subsystem/) page).

| model  | defect                                                                                                                                                              | effect                                                                 |
|--------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------|
| KN5000 | only MAME's flux-level floppy formats registered, not the raw sector `.img`                                                                                         | every `.img`, all 14 `kn5000_flop` entries included, failed to load    |
| KN5000 | FD.I/O (Port D bit 6) fed from MAME's disk-change latch, which only a head step clears                                                                              | a disk inserted at run time was never seen ("ERROR 02")                |
| KN5000 | drive attached as unit 0; the firmware addresses unit 1 in every command                                                                                            | every command came back "not ready"                                    |
| KN5000 | controller RDY taken from the drive; the firmware seeks about 5 ms after switching the motor on, so RDY must be tied active on the board (inferred; net not traced) | "not ready" again, once the unit was right                             |
| KN5000 | the data-rate auxiliary command (`0x4B` = 500 kbit/s, `0x0B` = 250 kbit/s) acknowledged but not applied                                                             | everything ran at 250 kbit/s; MAME saved the formatted disk as 720 KB  |
| KN6000 | the DMA-end interrupt makes one dummy read of the DMA acknowledge port; the emulation let that read take a byte from the controller                                 | FORMAT TRACK lost its last sector ID: sector 18 of every track missing |

The KN5000 ones also mean that the `kn5000_flop` list in mainline MAME cannot be loaded at all
yet. That is an upstream fix to make before the rebuilt images are sent.
