# G-Police (PC, 1997) on modern PCs and the Steam Deck

## Why this exists

G-Police felt extremely cinematic and open world at the time, and modern controls, mainly dual
analogue sticks, make it even better: flying on one stick, altitude on the other, thrust on the
triggers. On modern systems it stops at a CD check that ripped music can't pass, asks for the
installer's registry key, and a modern pad's triggers and right stick don't work. This kit sorts
that out, and adds proper widescreen, so it can be played again.

## What this does

Turns **your own** G-Police CD into a folder that runs on the Steam Deck (Proton) or on Windows
10/11, with no installer, no start-up dialog and no CD:

- **Real widescreen**: the game plays at wide resolutions but crops the top and bottom of the view
  and stretches the HUD across the screen. The exe is patched so a wide screen shows more city at
  the sides (Hor+), with the HUD, pause menu and loading screen kept 4:3 and unstretched in the
  middle. It starts at 1280x800. At 4:3 nothing changes. The menus and movies stay 640x480 with
  black bars.
- **Direct3D through dgVoodoo2**, sharp and scaled to your screen, 60 frames a second (the game's
  speed doesn't depend on it).
- **CD soundtrack** from OGG files ripped from your disc.
- **Gamepad**: an Xbox-style pad (the Steam Deck's included) is read directly: analogue flying on
  the left stick, analogue thrust on the triggers, altitude on the right stick. The pad skips the
  movies.
- **The CD check**: the game checks every audio track's length on the disc, which ripped music can
  never pass, so the check always passes; it also no longer searches CD drives for its data. The
  start-up dialog and the installer's registry key aren't needed either.
- No mouse pointer over the game.

**No game files are in this repository.** Everything from the game comes from your disc when you
run `build.py`.

## What you need

| | |
|---|---|
| The game | The **US G-Police CD, the "AGP Enhanced" release** (Psygnosis, 1997, exe version 1.18) as `.cue` + `.bin` or CloneCD `.ccd` + `.img`, with its 10 audio tracks. `build.py` checks the exe and the game data and stops on another version (other editions have different exes). |
| Python | 3.8 or newer (python.org on Windows; already on macOS/Linux). |
| An OGG encoder | `oggenc` (vorbis-tools; Windows builds at rarewares.org) or `ffmpeg`, on the PATH. |
| dgVoodoo2 **2.79.3** | by Dege: [GitHub release v2.79.3](https://github.com/dege-diosg/dgVoodoo2/releases/tag/v2.79.3). Use 2.79.3: newer versions don't start under Wine/Proton. Keep the zip as downloaded. |
| ogg-winmm **v2025.01.16** | by AyuanX: [GitHub releases](https://github.com/ayuanx/ogg-winmm/releases). This exact release: `build.py` patches one call in its `winmm.dll` and checks the file first. Keep the zip as downloaded. |

## Build

```
python3 build.py GPolice.cue --dgvoodoo dgVoodoo2_79_3.zip --ogg-winmm ogg-winmm_binary.zip
```

creates `G-Police/` with `game/` and `gpolice_launch.sh` (for the Steam Deck), in under a minute.
The same `game/` folder runs on Windows; `--windows` leaves out the launch script. `--out DIR` puts
the result somewhere else. The disc's original exe, settings file and readme are kept in
`game/_spare/`.

## Play on the Steam Deck

1. Copy `G-Police/` to the Deck, for example to `/home/deck/Games/G-Police/`.
2. Desktop Mode: Steam > Add a Non-Steam Game > Browse > `.../G-Police/game/GPOLICE.EXE`.
   Rename the shortcut "G-Police".
3. Properties > Compatibility: force **Proton 9.0**. Pin it rather than floating on Experimental.
4. Properties > Launch Options:
   ```
   /home/deck/Games/G-Police/gpolice_launch.sh %command%
   ```
5. Controller layout: start from the standard **Gamepad** layout and set **Start = Enter** and
   **View = Esc** (keyboard keys). Esc is the game's pause; everything else is the pad as itself.

## Play on Windows

Run `game/GPOLICE.EXE`. An Xbox pad works as on the Deck; Start is the game's Esc (pause), and
Enter is on the keyboard (or map it in Steam or your pad software). The game writes two values of
its own under `HKLM\SOFTWARE\Psygnosis\Studios\G-Police`; without admin rights Windows keeps them
in its VirtualStore, which is fine.

## Controls

| Pad | In a mission | In the menus |
|---|---|---|
| Left stick | pitch and turn (analogue; up = nose down) | move |
| RT / LT | thrust forward / back (analogue; both released: no thrust, slows to a hover) | |
| Right stick up / down | climb / descend | |
| A | fire the selected weapon | choose |
| RB | next target | |
| LB / X | next / previous weapon | |
| B | airbrake | |
| Y | change view | |
| D-pad | look around (cockpit view) | move |
| Start (Enter) | | choose |
| View (Esc) | pause menu | back |
| A, B, X, Y, Start or View | skip a movie | |

Options > Controls in the game changes all of it (saved in `game/GPOLICE.CFG`). The keyboard
(`Primary_Controller = KEYBOARD`): arrows fly, left Ctrl fire, right Shift / right Ctrl thrust,
left Alt airbrake, C scan, S / X up / down, Space view, A / Z weapons.

## Settings

Settings and pad bindings are in `game/GPOLICE.CFG` (the game rewrites it); saved games in
`game/GPOLICE.SAV`. The kit's starting `GPOLICE.CFG` sets the pad, analogue throttle, the hat as
cockpit look, every detail option at its highest, and 1280x800.

- **4:3 instead**: Options > Graphics > Resolution 1024x768 (or 640x480 / 800x600), or
  `GFX2_Resolution = 1024x768` in `GPOLICE.CFG`. At 4:3 the patched exe draws exactly like the
  original.
- **Other resolutions**: the game lists 320x200 up to 1920x1080 (`ExtraEnumeratedResolutions` in
  `game/dgVoodoo.conf`; it only takes the first 16 modes it's offered, so keep the list short).
  dgVoodoo scales the picture to your screen.
- Deck renderer: `RENDERER=wined3d` before the script path in the launch options uses Wine's own
  Direct3D instead of dgVoodoo.

## Troubleshooting

- *"Please Insert G-Police CD"* or a start-up dialog: you're running the unpatched exe from
  `_spare/`.
- *No music*: on the Deck `launch.log` must show `WINEDLLOVERRIDES=...;winmm=n,b` (no log: the
  launch option is missing `%command%`), and `game/Music/Track02.ogg` must exist.
- *Plays at 4:3 or with the old controls*: a `GPOLICE.CFG` from another install; replace it with the
  one from `config/`.
- *Judder on a G-Sync / FreeSync monitor*: turn variable refresh off for this game.

## What's in this repository

| File | What |
|---|---|
| `build.py` | Builds the folder: copies the CD's game files, patches the exe, rips the soundtrack, adds the wrappers and settings. Python standard library only. |
| `patch_exe.py` | The exe patches, each explained; adds a code section to the exe. Also runs on its own. |
| `caves.s` | The new code's source (x86 assembly), the widescreen layout included. `python3 patch_exe.py --check-caves` re-assembles it with clang and checks it against the bytes in `patch_exe.py`. |
| `oggwinmm_fix.py` | A 5-byte fix to ogg-winmm v2025.01.16 (its "open cdaudio" string command crashes under Wine). |
| `disc.py` | Reads the CD image: `.cue`/`.bin` or `.ccd`/`.img`, ISO 9660 (CD-XA too) and audio tracks. |
| `config/` | The game's starting settings and pad set-up, dgVoodoo2's and ogg-winmm's settings. |
| `steamdeck/gpolice_launch.sh` | Proton launch wrapper: DLL overrides. |
| `docs/TECHNICAL.md` | How the game works and what each patch does. |

## Credits

- **Psygnosis** made and published G-Police. Please own the game: this kit needs your disc.
- **Dege**: dgVoodoo2. **AyuanX**: ogg-winmm.

## License

The scripts and docs in this repository: MIT (see `LICENSE`). The license covers only this
repository's own files, not the game, dgVoodoo2 or ogg-winmm.

Not affiliated with or endorsed by the game's rights holders.
