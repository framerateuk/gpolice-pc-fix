#!/usr/bin/env python3
"""Build a ready-to-run G-Police folder for modern PCs from your own CD.

Usage:
  python3 build.py DISC.cue|DISC.ccd --dgvoodoo DGVOODOO.zip --ogg-winmm OGG-WINMM.zip [--out DIR] [--windows]

  DISC          your G-Police CD (Psygnosis, 1997, the US "AGP Enhanced" release, v1.18) as .cue + .bin or
                .ccd + .img, with its 10 audio tracks
  --dgvoodoo    dgVoodoo2 2.79.3 zip (or its unpacked folder)
  --ogg-winmm   ogg-winmm v2025.01.16 release zip (or folder)
  --out         where to create G-Police/ (default: this folder)
  --windows     a folder for Windows only: the same game/ folder, without the Steam Deck launch script

Needs Python 3.8+ and an Ogg Vorbis encoder on the PATH: oggenc (vorbis-tools) or ffmpeg.
Nothing from the game is in this repository: every game file comes from your disc.
"""
import argparse, hashlib, os, shutil, struct, subprocess, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import disc, oggwinmm_fix, patch_exe

DATA_MD5 = {"RES.RDR": "6d0e3f962a35d6b0c4d0c18c8fe0a9b2", "DISK1.RDT": "24c0d01551f2aa9ac07d6076ec5947d1"}
PATCHED_MD5 = "16d6c6c771e96a1c8896e12cee724797"
# The installer's "Essential Files" + "Data Files" (every file is read from the disc), plus the movies it leaves on
# the CD. The *.DA entries in the disc's root are the audio tracks themselves: the music comes from the rip.
FILES = ["LINGO.DAT", "RES.RDR", "RES.RDA", "RES.RDI", "RES.RDT", "RES.RDX", "DISK1.RDT", "DISK2.RDT"] + \
        [f"CAM{i}A.MPG" for i in range(1, 8)] + [f"STR{i}A.MPG" for i in range(1, 7)] + \
        ["INTA.MPG", "INTH.MPG", "HORTA.MPG", "OUTA.MPG"]
SPARE = [("GPOLICE.EXE", "GPOLICE.EXE"), ("GPOLICE.CFG", "GPOLICE-1997.CFG"), ("README.TXT", "README-1997.TXT")]


def md5(data): return hashlib.md5(data).hexdigest()


def encoder():
    if shutil.which("oggenc"): return lambda wav, ogg: ["oggenc", "-Q", "-q", "7", wav, "-o", ogg]
    if shutil.which("ffmpeg"):
        return lambda wav, ogg: ["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-c:a", "libvorbis", "-q:a", "7", ogg]
    sys.exit("needs oggenc (vorbis-tools) or ffmpeg on the PATH to encode the soundtrack")


def rip(tracks, music):
    enc = encoder(); os.makedirs(music, exist_ok=True); n = 0
    with tempfile.TemporaryDirectory() as tmp:
        for t in tracks:
            if t.kind != "AUDIO": continue
            data = disc.audio(t)          # INDEX 01 to the next track's start: lengths match the disc's TOC
            wav = os.path.join(tmp, f"track{t.n:02d}.wav")
            with open(wav, "wb") as o:
                o.write(b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " +
                        struct.pack("<IHHIIHH", 16, 1, 2, 44100, 176400, 4, 16) + b"data" +
                        struct.pack("<I", len(data)) + data)
            subprocess.run(enc(wav, os.path.join(music, f"Track{t.n:02d}.ogg")), check=True); os.remove(wav)
            print(f"  Music/Track{t.n:02d}.ogg  {len(data) / 2352 / 75:6.1f} s"); n += 1
    if n != 10: sys.exit(f"expected 10 audio tracks (the game's music), found {n}: is the image missing them?")


def take(src, member):
    """Bytes of the file whose path ends with `member` (case-insensitive) in a zip or folder."""
    want = member.lower()
    if os.path.isdir(src):
        for d, _, fs in os.walk(src):
            for f in fs:
                p = os.path.join(d, f)
                if os.path.relpath(p, src).replace(os.sep, "/").lower().endswith(want): return open(p, "rb").read()
    else:
        with zipfile.ZipFile(src) as z:
            for name in z.namelist():
                if name.lower().endswith(want): return z.read(name)
    sys.exit(f"{member} not found in {src}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("disc"); ap.add_argument("--dgvoodoo", required=True); ap.add_argument("--ogg-winmm", required=True)
    ap.add_argument("--out", default=HERE); ap.add_argument("--windows", action="store_true")
    a = ap.parse_args()

    tracks = disc.tracks(a.disc)
    data = [t for t in tracks if t.kind != "AUDIO"]
    if not data: sys.exit("no data track in " + a.disc)
    dt = disc.DataTrack(data[0])
    entries = {p.upper(): (p, is_dir, l, s) for p, is_dir, l, s in dt.walk()}
    for key, want in [("GPOLICE.EXE", patch_exe.MD5)] + list(DATA_MD5.items()):
        if key not in entries: sys.exit(f"no {key} on this CD: it isn't the G-Police disc the kit was made for")
        got = md5(dt.read_file(*entries[key][2:]))
        if got != want:
            sys.exit(f"this CD's {key} is not the US v1.18 one the kit was made for (MD5 {got}); "
                     "nothing else is supported yet")
    winmm = oggwinmm_fix.patch(take(a.ogg_winmm, "winmm.dll"))    # before anything is written: the release must match

    pkg = os.path.join(os.path.abspath(a.out), "G-Police"); game = os.path.join(pkg, "game")
    if os.path.exists(pkg): sys.exit(f"{pkg} already exists: move or delete it first")

    print("1/5 game files from the CD")
    for f in FILES:
        dt.copy_file(*entries[f][2:], os.path.join(game, f))
    for f, dst in SPARE:
        dt.copy_file(*entries[f][2:], os.path.join(game, "_spare", dst))
    shutil.copyfile(os.path.join(HERE, "config", "GPOLICE.CFG"), os.path.join(game, "GPOLICE.CFG"))   # the pad set-up

    print("2/5 exe patches")
    out = patch_exe.patch(dt.read_file(*entries["GPOLICE.EXE"][2:]))
    if md5(out) != PATCHED_MD5: sys.exit("patching gave an unexpected GPOLICE.EXE")
    open(os.path.join(game, "GPOLICE.EXE"), "wb").write(out)

    print("3/5 soundtrack")
    rip(tracks, os.path.join(game, "Music"))

    print("4/5 wrappers and settings")
    for member, name in [("MS/x86/DDraw.dll", "ddraw.dll"), ("MS/x86/D3DImm.dll", "d3dimm.dll")]:
        open(os.path.join(game, name), "wb").write(take(a.dgvoodoo, member))
    open(os.path.join(game, "winmm.dll"), "wb").write(winmm)
    for f in ("dgVoodoo.conf", "winmm.ini"):
        shutil.copyfile(os.path.join(HERE, "config", f), os.path.join(game, f))

    print("5/5 Steam Deck launch script" if not a.windows else "5/5 done")
    if not a.windows:
        launch = os.path.join(pkg, "gpolice_launch.sh")
        shutil.copyfile(os.path.join(HERE, "steamdeck", "gpolice_launch.sh"), launch); os.chmod(launch, 0o755)
    print(f"\ndone: {pkg}  (see README.md)")


if __name__ == "__main__":
    main()
