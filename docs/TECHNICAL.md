# How it works

Notes on the US "AGP Enhanced" release of G-Police (Psygnosis, 1997), `GPOLICE.EXE` version 1.18
(linked 28 October 1997, Watcom C, MD5 `cae83e6a7b67df3303961ffca6f4418f`). Addresses are virtual
addresses in that exe. Watcom functions take their arguments in eax, edx, ebx, ecx and keep every
other register; the new code keeps all of them.

## The disc and the installer

Track 1 is a Mode 2 (CD-XA, Form 1) data track; tracks 2-11 are the music. The ten `*.DA` entries in
the disc's root are the audio tracks themselves (their extents are tracks 2-11) and are left out.
The InstallShield 5 installer's `data1.cab` holds only its file list; every file is read from the
disc. `build.py` copies its "Essential Files" and "Data Files" (`LINGO.DAT`, the `RES.*` and
`DISK*.RDT` data) plus the MPEG-1 movies it leaves on the CD, which the game reads from its
"Resource Path". Left out: the installer, the uninstaller, autorun, DirectX 5.

The renderers: software 8-bit, Direct3D (DirectX 5, `IDirect3D2` on DirectDraw) and an ATI Rage
driver; no Glide.

## The patches

`patch_exe.py` adds a section `.rdeck` (VA 0x845000, 4 KB, at the end of the file) holding the new
code from `caves.s`. Its header lists each site's bytes and how it was found.

| Patch | Hooks | Was | Now |
|---|---|---|---|
| `nodialog` | WinMain's `DialogBoxParamA` (0x46948e), the start-up dialog ("Version v1.18") | A Windows dialog before the game: renderer, 3D device, "Hi-Res Movies" | The dialog's own defaults taken as OK at once: Direct3D hardware when there's a device, the list's last device, hi-res movies with MMX |
| `noreg` | the start-up registry read 0x46aabc: `HKLM\SOFTWARE\Psygnosis\Studios\G-Police` | "Configuration File", "Saved Game File", "Resource Path" (the CD) from the installer; without them the game quits | `.\GPOLICE.CFG`, `.\GPOLICE.SAV`, the "CD" = the working directory. Values the game writes there itself are still read |
| `nocdtoc` | the CD check 0x46adc4 ("Please Insert G-Police CD"): its validator 0x412fd0 reads the CD's table of contents over MCI and compares each track's length with one of two tables | ogg-winmm's lengths (from the OGGs, rounded to milliseconds) never match | The loop's "passed?" test is always true (0x46adde `jne` -> `jmp`); the MCI CD device is still opened and used for the music |
| `nocdscan` | 0x46af58: every CD-ROM drive is searched for `CAM1A.MPG` and that drive made the working directory | Data and movies from the CD | Returns at once; the working directory stays the exe's folder |
| `noff` | the joystick set-up (0x4828da): a force-feedback DirectInput device is taken for a SideWinder Force Feedback stick | An Xbox pad that reports rumble as force feedback would bypass the winmm read `pad` uses | Always the winmm joystick (0x4828e1 `je` -> `jmp`) |
| `analogue` | the winmm set-up (0x482d09): a stick resting at exactly the middle is taken for a digital pad | Steam Input's dead zone rests exactly in the middle ("hyper sensitive", as the game's own readme warns) | Always analogue (0x482d0f `jne` -> `jmp`) |
| `pad` | the joystick read 0x483730 and its three callers: flight (0x468825), menus (0x42c8e6), the start-up warm-up (0x428339) | Under Proton an Xbox pad's triggers are one shared Z axis and no buttons; the right stick isn't read | With an XInput pad connected, the reading comes from XInput: left stick = X / Y, LT - RT = Z (the analogue throttle), A B X Y LB RB = buttons 1-6, right stick up / down past half = buttons 7 / 8 (missions only), Start = button 9 (the game's fixed Esc), View 10, L3 11, R3 12, D-pad = the hat |
| `horplus` | the focal length at each mode set (0x469cf4: 0x469d20 / 0x469d89 / 0x469dab / 0x469ddb, one per view depth) | K x width / 320 (K = 230-273): a fixed horizontal view, so a wide mode loses the top and bottom (Vert-) | K x height / 240: identical at 4:3, a wide mode shows more at the sides (Hor+) |
| `widescreen` | the 2D's widths and origin (below) | In a wide mode every HUD element, the pause menu and the loading screen stretched across the screen | Laid out for a 4:3 width and moved into the middle; at 4:3 the original exactly |
| `movieskip` | the movie player's `PeekMessageA` (0x4d9a27) | Only Enter / Esc stopped a movie | A, B, X, Y, Start or View stop it the way Enter does |
| `nocursor` | `WM_SETCURSOR` (0x469643) | `SetCursor(arrow)` | `SetCursor(NULL)` |

Not patched: the frame rate (the game moves its world in fixed 16 ms steps up to the elapsed time,
0x468332, so its speed doesn't depend on the frame rate; dgVoodoo's vsync and `FPSLimit = 60` hold
60), the memory checks (read unsigned: no large-address-aware or big-VRAM trouble).

## Widescreen

- **3D** (`horplus`): one focal length for both axes, set at each mode set from the width, so a wide
  mode kept the 4:3 view's width and lost the top and bottom. Now it follows the height. The 3D
  frustum already takes the real screen width (0x471b94), so culling covers the wider view.
- **2D** (`widescreen`): the HUD (several modules), the pause menu and the loading screen are laid
  out from the play mode's width (HUD rectangles as x * width / 320, y * height / 240; integer
  scales width / 320 and height / 200 or 240), so they stretched across a wide screen. They're now
  handed W2D = 4 x height / 3 (1066 at 800 lines) and lay out an unstretched 4:3 screen, and the
  view's 2D origin (which every absolute 2D primitive adds) becomes X0 = (width - W2D) / 2, putting
  that HUD in the middle. The four 2D line primitives drawn relative to the projection centre (lines
  in the 3D, target leads) skip the origin. The cockpit HUD's vertical integer scale is held to its
  horizontal one. At 4:3 resolutions, W2D = the width and X0 = 0: the original exactly.

## Picture and display modes

dgVoodoo2 2.79.3: `Resolution = max` (the 3D at the largest size of the mode's shape that fits the
screen), `ScalingMode = stretched_ar` (black bars, no stretching), VRAM 256 MB, vsync,
`FPSLimit = 60`. The game keeps only the first 16 16-bit modes DirectDraw lists (0x4b069c), so
`DefaultEnumeratedResolutions = none` with an explicit `ExtraEnumeratedResolutions` list (320x200
to 1920x1080) gives it exactly those; a configured resolution it can't find falls back to the
list's first. The MPEG-1 movies are decoded by the game into its own DirectDraw surfaces, also
through dgVoodoo.

## Pad

The game reads a winmm joystick with up to 8 bindable buttons, a POV hat and an analogue throttle
axis; the bindings are `GPOLICE.CFG`'s `Jy_*` lines (`JOY_F1`-`JOY_F8` = buttons 1-8). The kit's
starting `GPOLICE.CFG` sets `Primary_Controller = JOYSTICK`, `Throttle = ENABLED`,
`POV_Hat = VIRTUAL_COCKPIT`, and binds A fire, B airbrake, X previous weapon, Y view, LB next weapon,
RB scan, and the right stick's buttons 7 / 8 as hover up / down (the game's altitude control has no
analogue input). Esc is the game's own pause key, hence View = Esc in Steam Input on the Deck.

## ogg-winmm

ogg-winmm v2025.01.16 answers the string command "open cdaudio" by passing `MCI_OPEN` on to the
real winmm with a NULL parameter block. Windows' winmm fails and the result is ignored; Wine's
writes the device ID back through the NULL pointer, an access violation inside `winmm.dll`.
`oggwinmm_fix.py` replaces that one call with `add esp,0x10 ; xor eax,eax` (the same stack, result 0).
