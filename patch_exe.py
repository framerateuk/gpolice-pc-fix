#!/usr/bin/env python3
"""Patch G-Police's exe (the disc's GPOLICE.EXE, 1,486,848 bytes, MD5 cae83e6a7b67df3303961ffca6f4418f, linked
28 Oct 1997, Watcom C; Psygnosis, "v1.18" in its start-up dialog) into a copy.

  patch_exe.py <GPOLICE.EXE> <out.exe>   write the patched exe (refuses, writes nothing, on any unexpected byte)
  patch_exe.py --check-caves             re-assemble caves.s with clang and compare with CAVE below

New code (caves.s, assembled bytes in CAVE) goes into a section the patch adds: ".rdeck", VA 0x845000, 0x1000 bytes
at file offset 0x16b000 (the end of the file, after .rsrc), readable / writable / executable; its variables from
0x845c00. The section table had room for a seventh entry (it ended at 0x268, the first section starts at 0x400);
SizeOfImage 0x445000 -> 0x446000. The exe has no checksum and loads at its 0x400000 base (no dynamic-base flag); the
header now also says "relocations stripped", so no loader ever moves it. Watcom's register calling convention:
arguments in eax, edx, ebx, ecx (docs/TECHNICAL.md).

  rdeck       the section (above) with the code of caves.s.
  nodialog    WinMain's start-up dialog (DialogBoxParamA, resource 101, procedure 0x46a258, called at 0x46948e:
              "rendering type" software / hardware, the 3D device list, Hi-Res Movies, OK / Cancel; found from its
              "Version %s" / "v1.18" / "D3D Device %d" strings) is replaced by nodialog: the dialog's own defaults
              taken as OK at once (Direct3D hardware when there is a device, the list's last device, hi-res movies
              with MMX). "call cs:[DialogBoxParamA]" (7 bytes) -> "call nodialog; nop; nop".
  noreg       the start-up registry read 0x46aabc (called at 0x4697a5; found from the "SOFTWARE\\Psygnosis\\Studios\\
              G-Police" / "Configuration File" / "Resource Path" strings) wanted the installer's HKLM values; with
              "Configuration File" missing its first-run branch 0x46a930 reads "Path" and quits without it. The
              call now goes to regpaths: GPOLICE.CFG, GPOLICE.SAV and the "CD" (Resource Path, where the movies are
              read from) are ".\\" = the working directory; "Control Method" / "SysChk", which the game writes into
              that key itself, are still read when there.
  nocdtoc     the CD check 0x46adc4 (the "Please Insert G-Police CD" MessageBoxA retry loop, 0x46ae11): it calls
              the CD validator 0x412fd0, which reads the disc's table of contents over MCI and compares each
              track's length (next start - start - 150 frames) with one of two tables in the exe (0x5005e0 /
              0x50060c), as Wipeout 2097's; ogg-winmm's millisecond-rounded TOC never matches. The loop's
              "failed?" test (0x46adde, "jne" past the box when it passed) is now "jmp": always passed. The MCI
              device is still opened and used for the music as before.
  nocdscan    0x46af58 looks through every DRIVE_CDROM drive for CAM1A.MPG and makes that drive's root the working
              directory (data and movies then come from the CD). Now "ret" at once: the working directory stays the
              exe's folder (no fake drive, and a real G-Police CD in a PC's drive changes nothing).
  noff        the joystick set-up 0x482750 takes a DirectInput device that reports force feedback (DIDC_FORCEFEEDBACK,
              "test byte [0x53be19], 1" at 0x4828da) as a SideWinder Force Feedback stick and then reads it through
              DirectInput (0x483aa4) instead of winmm. An Xbox pad under Proton can report force feedback (rumble);
              the "je" at 0x4828e1 is now "jmp": always the winmm joystick, which the pad patch reads.
  analogue    the winmm joystick set-up (0x482d09) takes a stick whose resting position reads exactly the middle of
              its range (32768, 32768) as a digital pad (README.TXT: "a perfectly centred Analogue joystick can be
              mistaken for a digital joystick ... hyper sensitive"). Steam Input's dead zone gives exactly that. The
              "jne 0x48310d" (= analogue) at 0x482d0f is now "jmp": always analogue.
  pad         the joystick read JOYREAD 0x483730 (joyGetPosEx -> X Y Z R U V floats, buttons, POV, capability bits;
              found from its joyGetPosEx call and the "Joystick %d found, Caps:" set-up) and its three callers: the
              flight controls 0x468825 -> joygame, the menus 0x42c8e6 and the start-up warm-up reads 0x428339 ->
              joymenu. The game's own read runs first; with an XInput pad its reading is then written from the pad:
              left stick = X / Y, LT - RT = Z (the analogue throttle: RT forward, LT back), A B X Y LB RB = buttons
              1-6, the right stick up / down past half = buttons 7 / 8 (in a mission only), Start = button 9 (the
              game's fixed Esc), D-pad = the POV hat (in the menus: the stick). Under Proton an Xbox pad's triggers
              are one shared axis and not buttons. The layout: triggers = throttle, right stick =
              altitude, A = fire.
  movieskip   the movie player's decode loop calls PeekMessageA at 0x4d9a27 (found from the player's stop flag
              0x52a7e8, which Enter / Esc set through 0x4abbf0 in the window procedure): "call cs:[PeekMessageA]" ->
              "call movpeek; nop; nop": A, B, X, Y, Start or View newly pressed stops a skippable movie as Enter does.
  nocursor    the window procedure answers WM_SETCURSOR with SetCursor(the arrow from LoadCursorA, [0x53253c])
              (0x469643): now SetCursor(NULL), no pointer over the game. "mov ebp, [0x53253c]" -> "xor ebp, ebp".

  horplus     the 3D's focal length, set at each mode set 0x469cf4 (0x469d20 / 0x469d89 / 0x469dab / 0x469ddb, one
              per view depth): K * width / 320 (K = 230 / 240 / 245 / 273) -> K * height / 240. The projection uses
              one focal length for both axes, so the old one kept a wide mode's view as wide as at 4:3 and cut the
              top and bottom (PCGamingWiki: Vert-); now a wide mode shows more at the sides (Hor+). Identical at 4:3.
              The same engine as Overboard (Psygnosis Stroud, 1997-98; its patch_exe.py widescreen).
  widescreen  the 2D of a mission in a wide mode, kept 4:3 and unstretched in the middle (caves.s "Widescreen"):
              the HUD modules, the pause menu and the loading screen lay themselves out from the mode's width
              (0x531938, handed to them at the mission start 0x458276-0x4584a1 and read by the loading screen
              0x458d68-0x459c63): those 26 reads now read W2D (4 x height / 3 in a wide mode); every absolute 2D
              primitive adds the current view's origin x (view + 0x30) and the in-game view's origin becomes X0 =
              (width - W2D) / 2 (viewset, after its set-up 0x458cd4), which moves all that 2D into the middle; the
              3D primitives never add the origin. The four 2D line primitives that are relative to the projection
              centre (0x494dc0, 0x495640, 0x495a48, 0x495e5c) no longer add the origin x (it was 0 in every view they
              draw in). The screen struct's width (0x541d2c, copied each frame at 0x492632, read by 2D code) holds
              the 2D width too (w2dstore); the 3D frustum (0x471b94) reads the real width (frust). The cockpit HUD's
              y scale is held to its x scale in a wide mode (hudys, 0x44ac72). The mode set (0x469e02) computes W2D
              and X0 (modeset). At 4:3: W2D = the width, X0 = 0, the original exactly.

Not patched (docs/TECHNICAL.md): the frame rate (the game runs its world in fixed 16 ms steps up to the elapsed time, 0x468332,
so any frame rate plays at the right speed; dgVoodoo holds 60 with vsync), the memory checks (GlobalMemoryStatus
read unsigned, "shr 20"; no large-address-aware trouble). The play resolution is the game's own setting (GPOLICE.CFG
GFXn_Resolution, the starting copy 1280x800; dgVoodoo.conf lists the modes).
"""
import hashlib, os, struct, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SIZE, MD5 = 1486848, "cae83e6a7b67df3303961ffca6f4418f"
DELTA = 0x400c00                       # AUTO (code, VA 0x401000, file offset 0x400): file offset = VA - 0x400c00
def T(va):
    assert 0x401000 <= va < 0x4f7a00, hex(va)
    return va - DELTA

def rel32(src, dst, op):               # e8 / e9 at src (5 bytes) -> dst
    return bytes([op]) + (dst - (src + 5)).to_bytes(4, "little", signed=True)

SECT_VA, SECT_RVA, SECT_OFF, SECT_SIZE = 0x845000, 0x445000, 0x16b000, 0x1000
CAVE_VA = SECT_VA
CAVE = bytes.fromhex(
    "5531edeb0655bd0100000052e81fe7c3ff5a6089d6e80f01000085c0740de80b000000c744241c00000000615dc38b1d"
    "085c8400a10c5c8400e8cb00000085ed7414f6c3047406ddd8d9e8d9e0f6c3087404ddd8d9e8d91ea1105c8400e8a700"
    "0000d9e085ed7414f6c3017406ddd8d9e8d9e0f6c3027404ddd8d9e8d95e04a11c5c8400e89800000089c1a1205c8400"
    "e88c00000029c151db0424d80d1054840059d95e0831c089460c89461089461431c9bfd453840031d20fb7045785c074"
    "0785c374030fabd14283fa0c72eb85ed751ca1185c84003d004000007e0383c9403d00c0ffff7d0681c980000000894e"
    "1889d883e00f0fb70445ec53840089461c814e2084000000c33d0180ffff7d05b80180ffff50db0424d80d0c54840058"
    "c383e8087f0231c0c360a1085c8400a3245c8400833d045c840000753cc705045c840001000000be50548400bb030000"
    "0056ff15e8844f0085c07417681454840050ff15c0844f0085c07407a3005c8400eb0683c6104b75d8833d005c840000"
    "747531db68405c840053ff15005c840085c074084383fb0472eaeb5b0fb705445c8400a3085c84000fb605465c8400a3"
    "1c5c84000fb605475c8400a3205c84000fbf05485c8400a30c5c84000fbf054a5c8400a3105c84000fbf054c5c8400a3"
    "145c84000fbf054e5c8400a3185c840061b801000000c331c0a3085c8400a30c5c8400a3105c8400a3145c8400a3185c"
    "8400a31c5c8400a3205c84006131c0c360833d6c255300017524e8fafeffff85c0741ba1085c84008b0d245c8400f7d1"
    "21c8a930f000007405e8a269c6ff61ff25f8834f00606a0089e0e8f1a5c6ff5aa33025530031c9a8147405b903000000"
    "890dac2653008d5aff83f9037518f6053025530010740f83fb01750ac705ac2653000400000083fb017e014b891db026"
    "5300e8198dc7fff7d819c0f7d8a3b8265300c705a82653000100000061b801000000c2140060be23548400bfe0285300"
    "e848000000be31548400bfd8275300e839000000be3f548400bfd0265300e82a000000bb6cd04f00bac0265300b890d0"
    "4f00e80154c2ffbb9fd04f00baf02a5300b8c3d04f00e8ed53c2ff61c38a068807464784c075f6c3893538195300893d"
    "3c19530050515289f8e81b00000039f0720289f0a3505c840089f129c1d1e9890d545c84005a5958c351c1e00231d2b9"
    "03000000f7f159c3ff74240cff74240cff74240ce83ba6c4ff518b0d545c8400890da818530059c20c0050515289d98b"
    "198b4104e8c0ffffff39d8730289c35a895a0c5958c38b4a088b1db8e053008b5b048b1b8b7210c3833d545c84000074"
    "0d3b05409c50007605a1409c5000a3449c5000c3001000200040008000010002000000001000200040008000ffff0000"
    "5046ffff78690c7be457786928239411bc342823ffff00005046ffff00010038faa9843b58496e707574476574537461"
    "7465002e5c47504f4c4943452e434647002e5c47504f4c4943452e534156002e5c00662e0f1f8400000000000f1f4000"
    "78696e707574315f342e646c6c00669078696e707574315f332e646c6c00669078696e707574395f315f302e646c6c00")
SYM = {"joygame": 0x000, "joymenu": 0x005, "movpeek": 0x220, "nodialog": 0x255, "regpaths": 0x2c5, "modeset": 0x328, "viewset": 0x368, "w2dstore": 0x38a, "frust": 0x3a6, "hudys": 0x3b8}   # labels of caves.s
def C(name): return CAVE_VA + SYM[name]

JOYREAD = 0x483730
def build():
    """(va, old bytes, new bytes) for every patch site."""
    e = []
    # nodialog: "call cs:[DialogBoxParamA]" -> "call nodialog; nop; nop"
    e.append((0x46948e, bytes.fromhex("2eff15c0834f00"), rel32(0x46948e, C("nodialog"), 0xe8) + b"\x90\x90"))
    # noreg: "call 0x46aabc" -> "call regpaths"
    e.append((0x4697a5, rel32(0x4697a5, 0x46aabc, 0xe8), rel32(0x4697a5, C("regpaths"), 0xe8)))
    # nocdtoc: "jne 0x46ae2f" (the check passed) -> "jmp 0x46ae2f"
    e.append((0x46adde, bytes.fromhex("754f"), bytes.fromhex("eb4f")))
    # nocdscan: "push ebx" at the drive scan's entry -> "ret"
    e.append((0x46af58, bytes.fromhex("53"), bytes.fromhex("c3")))
    # noff: "je 0x482bab" (no force feedback: the winmm joystick) -> "jmp 0x482bab; nop"
    e.append((0x4828e1, bytes.fromhex("0f84c4020000"), rel32(0x4828e1, 0x482bab, 0xe9) + b"\x90"))
    # analogue: "jne 0x48310d" (not centred exactly: analogue) -> "jmp 0x48310d; nop"
    e.append((0x482d0f, bytes.fromhex("0f85f8030000"), rel32(0x482d0f, 0x48310d, 0xe9) + b"\x90"))
    # pad: the three "call JOYREAD"
    e.append((0x468825, rel32(0x468825, JOYREAD, 0xe8), rel32(0x468825, C("joygame"), 0xe8)))
    for va in (0x42c8e6, 0x428339):
        e.append((va, rel32(va, JOYREAD, 0xe8), rel32(va, C("joymenu"), 0xe8)))
    # movieskip: "call cs:[PeekMessageA]" -> "call movpeek; nop; nop"
    e.append((0x4d9a27, bytes.fromhex("2eff15f8834f00"), rel32(0x4d9a27, C("movpeek"), 0xe8) + b"\x90\x90"))
    # nocursor: "mov ebp, [0x53253c]" (the arrow cursor) -> "xor ebp, ebp" (SetCursor(NULL))
    e.append((0x469643, bytes.fromhex("8b2d3c255300"), bytes.fromhex("31ed90909090")))
    # horplus: the focal length at the mode set, K * width / 320 (K = 273 / 245 / 240 / 230 by the view depth) ->
    # K * height / 240 (esi = width -> edi = height; 0x140 -> 0xf0); identical at 4:3
    e.append((0x469d20, bytes.fromhex("69d6e6000000b940010000"), bytes.fromhex("69d7e6000000b9f0000000")))
    e.append((0x469d89, bytes.fromhex("c1e60489f2c1e20429f2b940010000"), bytes.fromhex("c1e70489fac1e20429fab9f0000000")))
    e.append((0x469dab, bytes.fromhex("89f0c1e00301f0c1e00229f08d14c50000000029c2b940010000"),
              bytes.fromhex("89f8c1e00301f8c1e00229f88d14c50000000029c2b9f0000000")))
    e.append((0x469ddb, bytes.fromhex("89f2c1e20401f2c1e20401f2b940010000"), bytes.fromhex("89fac1e20401fac1e20401fab9f0000000")))
    # widescreen: the mode set's "mov [0x531938], esi; mov [0x53193c], edi" -> "call modeset" (+ W2D, X0)
    e.append((0x469e02, bytes.fromhex("893538195300893d3c195300"), rel32(0x469e02, C("modeset"), 0xe8) + b"\x90" * 7))
    # the in-game view's set-up "call 0x48f9b4" -> "call viewset" (its 2D origin x = X0)
    e.append((0x458cd4, rel32(0x458cd4, VIEWSET, 0xe8), rel32(0x458cd4, C("viewset"), 0xe8)))
    # the screen struct's width each frame "mov ebx, [ebx]; mov [edx + 0xc], ebx" -> "call w2dstore" (the 2D width)
    e.append((0x492632, bytes.fromhex("8b1b895a0c"), rel32(0x492632, C("w2dstore"), 0xe8)))
    # the 3D frustum's "mov ecx, [edx+8]; mov ebx, [edx+0xc]; mov esi, [edx+0x10]" -> "call frust" (the real width)
    e.append((0x471b94, bytes.fromhex("8b4a088b5a0c8b7210"), rel32(0x471b94, C("frust"), 0xe8) + b"\x90" * 4))
    # the cockpit HUD's y scale "mov [0x509c44], eax" -> "call hudys" (no larger than the x scale in a wide mode)
    e.append((0x44ac72, bytes.fromhex("a3449c5000"), rel32(0x44ac72, C("hudys"), 0xe8)))
    # the four centre-relative 2D line primitives (they add the projection centre, 0x5429d0): "add r16, [env + 8]"
    # (the view's origin x) -> nothing, so X0 does not move them (the in-game view's origin was 0 before)
    for va, old in ((0x494dd6, "66037808"), (0x494dde, "66035808"), (0x495659, "66037a08"), (0x495661, "66035a08"),
                    (0x495a5f, "66034208"), (0x495a67, "66035a08"), (0x495e77, "66034208"), (0x495e7f, "66035a08")):
        e.append((va, bytes.fromhex(old), b"\x90" * 4))
    # the 2D modules' and the loading screen's reads of the mode's width [0x531938] -> [W2D] (not the 3D view's
    # set-up at 0x458ca6, nor the mode set's write)
    for va, ins in W2D_SITES:
        old = bytes.fromhex(ins); i = old.index(bytes.fromhex("38195300"))
        e.append((va, old, old[:i] + struct.pack("<I", W2D) + old[i + 4:]))
    return e

VIEWSET, W2D = 0x48f9b4, 0x845c50
W2D_SITES = [(0x45827c, "a138195300"), (0x45828c, "a138195300"), (0x4582a1, "a138195300"), (0x4582b6, "a138195300"),
             (0x4582e4, "a138195300"), (0x458461, "a138195300"), (0x458471, "a138195300"), (0x458481, "a138195300"),
             (0x458491, "a138195300"), (0x4584a1, "a138195300"), (0x458d68, "813d3819530080020000"),
             (0x458d9d, "db0538195300"), (0x458fc0, "a138195300"), (0x45901f, "a138195300"), (0x45906d, "a138195300"),
             (0x4590ce, "a138195300"), (0x459111, "8b1538195300"), (0x45919f, "8b1538195300"), (0x4592da, "a138195300"),
             (0x459339, "a138195300"), (0x459387, "a138195300"), (0x4593e8, "a138195300"), (0x45942b, "8b1538195300"),
             (0x4594b9, "8b1538195300"), (0x459c45, "66a138195300"), (0x459c63, "a138195300")]

def add_section(data):
    lfanew = struct.unpack_from("<I", data, 0x3c)[0]
    nsec = struct.unpack_from("<H", data, lfanew + 6)[0]
    optsize = struct.unpack_from("<H", data, lfanew + 20)[0]
    sh = lfanew + 24 + optsize + 40 * nsec
    if nsec != 6 or sh != 0x268 or any(data[sh:sh + 40]) or len(data) != SECT_OFF:
        sys.exit("unexpected PE header; nothing written")
    struct.pack_into("<8sIIIIIIHHI", data, sh, b".rdeck", SECT_SIZE, SECT_RVA, SECT_SIZE, SECT_OFF, 0, 0, 0, 0,
                     0xE0000060)       # code | initialised data | execute | read | write
    struct.pack_into("<H", data, lfanew + 6, nsec + 1)
    chars = struct.unpack_from("<H", data, lfanew + 22)[0]
    struct.pack_into("<H", data, lfanew + 22, chars | 1)     # IMAGE_FILE_RELOCS_STRIPPED
    if struct.unpack_from("<I", data, lfanew + 24 + 56)[0] != SECT_RVA: sys.exit("unexpected SizeOfImage")
    struct.pack_into("<I", data, lfanew + 24 + 56, SECT_RVA + SECT_SIZE)
    data += CAVE + bytes(SECT_SIZE - len(CAVE))

def elf_text(path):                    # .text bytes and label offsets of an i386 ELF object (no relocations)
    d = open(path, "rb").read()
    shoff = struct.unpack_from("<I", d, 0x20)[0]; shentsize, shnum, shstrndx = struct.unpack_from("<HHH", d, 0x2e)
    secs = [struct.unpack_from("<10I", d, shoff + i * shentsize) for i in range(shnum)]
    names = [d[secs[shstrndx][4] + x[0]:].split(b"\0")[0].decode() for x in secs]
    if any(n.startswith(".rel") and x[5] for n, x in zip(names, secs)): sys.exit("caves.o has relocations")
    ti = names.index(".text"); text = d[secs[ti][4]:secs[ti][4] + secs[ti][5]]; syms = {}
    for x in secs:
        if x[1] != 2: continue                                   # SHT_SYMTAB
        strs = secs[x[6]]
        for i in range(x[5] // 16):
            nm, val, size, info, oth, shn = struct.unpack_from("<IIIBBH", d, x[4] + 16 * i)
            if shn == ti: syms[d[strs[4] + nm:].split(b"\0")[0].decode()] = val
    return text, syms

ENTRIES = ("joygame", "joymenu", "movpeek", "nodialog", "regpaths", "modeset", "viewset", "w2dstore", "frust", "hudys")
def check_caves():
    with tempfile.TemporaryDirectory() as t:
        o = os.path.join(t, "caves.o")
        subprocess.run(["clang", "-target", "i386-pc-linux-gnu", "-c", os.path.join(HERE, "caves.s"), "-o", o], check=True)
        text, syms = elf_text(o)
    ok = text == CAVE and all(syms.get(k) == SYM.get(k) for k in ENTRIES)
    print("caves.s matches CAVE" if ok else "caves.s differs from CAVE / SYM: update patch_exe.py")
    if not ok:
        print("CAVE =", text.hex()); print("SYM =", {k: hex(syms[k]) for k in ENTRIES})
    return ok

def patch(data, label="GPOLICE.EXE"):
    """Returns the patched exe; exits on any unexpected byte."""
    data = bytearray(data)
    if len(data) != SIZE or hashlib.md5(data).hexdigest() != MD5:
        sys.exit(f"{label}: not the disc's GPOLICE.EXE (size {SIZE}, MD5 {MD5}); nothing written")
    assert 0 < len(CAVE) < 0xc00, "CAVE empty or running into the variables at 0x845c00"
    edits = build()
    for va, old, new in edits:
        off = T(va)
        if bytes(data[off:off + len(old)]) != old or len(old) != len(new):
            sys.exit(f"unexpected bytes at VA {va:#x}; nothing written")
    for va, old, new in edits:
        data[T(va):T(va) + len(new)] = new
    add_section(data)
    print(f"  rdeck nodialog noreg nocdtoc nocdscan noff analogue pad movieskip nocursor horplus widescreen "
          f"({len(edits)} edits)")
    return bytes(data)

def main(src, dst):
    data = patch(open(src, "rb").read(), src)
    tmp = dst + ".tmp"
    open(tmp, "wb").write(data)
    os.replace(tmp, dst)
    print(f"{dst}: MD5 {hashlib.md5(data).hexdigest()}")

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--check-caves": sys.exit(0 if check_caves() else 1)
    if len(sys.argv) != 3: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
