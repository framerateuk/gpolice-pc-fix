# G-Police (GPOLICE.EXE, the disc's v1.18 exe, 1,486,848 bytes, linked 28 Oct 1997, Watcom C; Psygnosis): new code
# for patch_exe.py. It goes into a section patch_exe.py adds to the exe, ".rdeck" at VA 0x845000 (file offset
# 0x16b000, the end of the file, 0x1000 bytes, readable / writable / executable): this code from 0x845000, its
# variables from 0x845c00 (zero when the exe loads). The exe always loads at its 0x400000 base (no dynamic-base flag;
# the patch also marks it "relocations stripped"), so absolute addresses are used throughout.
#
# Assembled with Apple clang (integrated assembler):
#   clang -target i386-pc-linux-gnu -c caves.s -o caves.o
# patch_exe.py carries the resulting bytes (CAVE) and checks them against this file when clang is around
# (patch_exe.py --check-caves). docs/TECHNICAL.md explains each routine.
#
# The game is Watcom-compiled: its own functions take their arguments in eax, edx, ebx, ecx and keep every other
# register. The routines here keep every register but the result (pushad / popad), so the game sees no difference.
# Lesson kept from Speedster (23 Oct 2026): never keep a value in ecx / edx across an API call (Proton's
# timeGetTime and friends change them); values live in ebx / esi / edi / ebp or memory across calls.
.intel_syntax noprefix
.set BASE, 0x845000

# imports used (IAT slots of GPOLICE.EXE)
.set GetProcAddress,   0x4f84c0
.set LoadLibraryA,     0x4f84e8
.set PeekMessageA,     0x4f83f8

# game (docs/TECHNICAL.md says how each was found)
.set JOYREAD,   0x483730             # int JoyRead(eax = winmm joystick id, edx = JOYSTATE *): joyGetPosEx ->
                                     #   +0 X, +4 Y, +8 Z, +0xc R, +0x10 U, +0x14 V (floats -1..1), +0x18 buttons,
                                     #   +0x1c POV (hundredths of a degree, 0xffff = centred), +0x20 the joystick's
                                     #   capability bits (4 = Z / throttle, 0x80 = POV); returns 0 = a reading
.set REGGET,    0x46a708             # int RegGet(eax = value name, edx = out, ebx = key under HKLM): 0 = found
.set ENUMDEV,   0x4af850             # flags = EnumDevices(eax = &count): the 3D devices (bit 4 Direct3D hardware,
                                     #   bit 0x10 the ATI Rage driver); count = how many the dialog lists
.set HASMMX,    0x4bdfc0             # eax != 0: the CPU has MMX (the dialog's "Hi-Res Movies" default)
.set MOVIESTOP, 0x4abbf0             # stop the playing movie (what Enter does in the window procedure)
.set MOVIEON,   0x53256c             # 1 while a movie that Enter / Esc may skip plays
.set DEVFLAGS,  0x532530             # the dialog's copy of ENUMDEV's flags
.set RENDER,    0x5326ac             # renderer: 0 software 8-bit, 3 Direct3D device, 4 the ATI Rage driver
.set DEVICE,    0x5326b0             # which Direct3D device (the dialog's list position)
.set HIRESMOV,  0x5326b8             # 1 = hi-res movies
.set DLGOK,     0x5326a8             # 1 = the dialog was left with OK (WinMain goes on only then)
.set CFGPATH,   0x5328e0             # "Configuration File" (the registry value it replaces)
.set SAVPATH,   0x5327d8             # "Saved Game File"
.set RESPATH,   0x5326d0             # "Resource Path" (the CD root the movies are read from)
.set CTRLMETH,  0x5326c0             # "Control Method" (KEYBOARD / MOUSE / JOYSTICK; the cfg file decides later)
.set SYSCHK,    0x532af0             # "SysChk" (the result of the game's first-start speed test)
.set S_KEY,     0x4fd06c             # "SOFTWARE\Psygnosis\Studios\G-Police" (the game's own copies of the names)
.set S_CTRL,    0x4fd090             # "Control Method"
.set S_KEY2,    0x4fd09f             # "SOFTWARE\Psygnosis\Studios\G-Police"
.set S_SYSCHK,  0x4fd0c3             # "SysChk"
.set SCRW,      0x531938             # the play mode's width / height (written at the mode set 0x469e02)
.set SCRH,      0x53193c
.set VIEWSET,   0x48f9b4             # view_set(eax = view, edx / ebx / ecx / 3 stack args = its rectangle and centre)
.set ORIGIN_X,  0x5318a8             # the in-game view (0x531878) + 0x30: its 2D origin x, added by every
                                     #   absolute 2D primitive (sprites, boxes, text, the HUD), not by the 3D
.set HUDXS,     0x509c40             # the cockpit HUD's x scale (width / 320) and y scale (height / 200)
.set HUDYS,     0x509c44
.set DISPLAY,   0x53e0b8             # -> the display: +4 -> the screen size {width, height}

# our variables (.rdeck from 0x845c00, zero at load)
.set XGS,     0x845c00               # XInputGetState (0 = no XInput DLL)
.set XINIT,   0x845c04               # 1 once readpad has looked for XInput
.set PB,      0x845c08               # the pad as readpad last read it: XInput wButtons (DPAD_UP 1, DOWN 2, LEFT 4,
.set PLX,     0x845c0c               #   RIGHT 8, START 0x10, BACK 0x20, L3 0x40, R3 0x80, LB 0x100, RB 0x200,
.set PLY,     0x845c10               #   A 0x1000, B 0x2000, X 0x4000, Y 0x8000); left stick X / Y (signed, up +)
.set PRX,     0x845c14               #   right stick X / Y
.set PRY,     0x845c18
.set PLT,     0x845c1c               #   left / right trigger 0..255
.set PRT,     0x845c20
.set PPB,     0x845c24               # wButtons of the reading before (movieskip: "newly pressed")
.set XS,      0x845c40               # an XINPUT_STATE (16 bytes)
.set W2D,     0x845c50               # widescreen: the width the 2D (HUD, menus, loading screen) is laid out for:
                                     #   the play mode's width, or 4 x height / 3 when the mode is wider than 4:3
.set X0,      0x845c54               # widescreen: where that 4:3 area starts, (width - W2D) / 2 (0 at 4:3)

.set TDZT,    8                      # trigger dead zone, of 255 (the game has none on its throttle axis)
.set RSHALF,  16384                  # the right stick counts as climb / descend past half way

.macro PUSHI v                       # push imm32 (clang's intel syntax would make "push offset" 16-bit)
  .byte 0x68
  .long \v
.endm
.macro CALLA a                       # call an absolute address in the game
  .byte 0xe8
  .long \a - (BASE + (. + 4 - start))
.endm

.text
start:

# ---------------------------------------------------------------------------------------------------------------
# joygame / joymenu (patch pad): the game's three joystick reads, "mov eax, id; mov edx, out; call JOYREAD": the
# flight controls (0x468825, every frame in a mission), the menus (0x42c8e6) and the start-up warm-up reads
# (0x428339) now call here. The game's own read runs first (it fills the capability bits and the result); then, with
# an XInput pad connected, the whole reading is written from the pad (joyfill) and the result is 0 = a reading.
# joymenu also turns the D-pad into the stick (the menus move only with the stick); joygame keeps the D-pad as the
# POV hat (looking around in the cockpit view).
joygame:
  push ebp
  xor ebp, ebp
  jmp joycommon
joymenu:
  push ebp
  mov ebp, 1
joycommon:
  push edx
  CALLA JOYREAD
  pop edx
  pushad
  mov esi, edx                       # JOYSTATE *
  call readpad
  test eax, eax
  jz 9f
  call joyfill
  mov dword ptr [esp + 0x1c], 0      # eax (pushad's slot) = 0: a reading
9:
  popad
  pop ebp
  ret

# joyfill: esi = the game's JOYSTATE, ebp = 1 in the menus. From readpad's reading (winmm sense: right / down +):
#   +0x00 X, +0x04 Y   the left stick, -1..1 (no dead zone here: the game has its own, 20 %); in the menus the
#                      D-pad overrides with full deflection
#   +0x08 Z            the throttle (Options "Throttle" on): (LT - RT), -1..1: RT held = -1 (full forward thrust),
#                      both released = 0 (no thrust: slow to a hover), LT = +1 (backwards); dead zone TDZT each
#   +0x0c R, +0x10 U, +0x14 V   0 (the game uses V only for a pad type it never selects)
#   +0x18 buttons      bit 0 A, 1 B, 2 X, 3 Y, 4 LB, 5 RB (the cfg's JOY_F1..JOY_F6), 6 right stick up past half,
#                      7 right stick down past half (JOY_F7 / JOY_F8: climb / descend; in a mission only, the menus
#                      take any single button as an event), 8 Start (the game's fixed "button 9 = Esc"), 9 View,
#                      10 L3, 11 R3
#   +0x1c POV          the D-pad: 0 up, 9000 right, 18000 down, 27000 left, the diagonals between, 0xffff centred
#   +0x20 capabilities | 0x84 (Z and POV: the game drops its Throttle / POV_Hat options for a pad without them)
joyfill:
  mov ebx, dword ptr [PB]
  mov eax, dword ptr [PLX]
  call axisf
  test ebp, ebp
  jz 2f
  test bl, 4
  jz 1f
  fstp st(0)
  fld1
  fchs
1:
  test bl, 8
  jz 2f
  fstp st(0)
  fld1
2:
  fstp dword ptr [esi]
  mov eax, dword ptr [PLY]
  call axisf
  fchs                               # XInput up = +, winmm up = -
  test ebp, ebp
  jz 4f
  test bl, 1
  jz 3f
  fstp st(0)
  fld1
  fchs
3:
  test bl, 2
  jz 4f
  fstp st(0)
  fld1
4:
  fstp dword ptr [esi + 4]
  mov eax, dword ptr [PLT]
  call trigv
  mov ecx, eax
  mov eax, dword ptr [PRT]
  call trigv
  sub ecx, eax                       # LT - RT, -247..247
  push ecx
  fild dword ptr [esp]
  fmul dword ptr [A_TRSCALE]
  pop ecx
  fstp dword ptr [esi + 8]
  xor eax, eax
  mov dword ptr [esi + 0xc], eax
  mov dword ptr [esi + 0x10], eax
  mov dword ptr [esi + 0x14], eax
  xor ecx, ecx                       # buttons
  .byte 0xbf                         # mov edi, btnmap
  .long A_BTNMAP
  xor edx, edx
5:
  movzx eax, word ptr [edi + edx*2]
  test eax, eax
  jz 6f                              # 0: a right-stick slot
  test ebx, eax
  jz 6f
  bts ecx, edx
6:
  inc edx
  cmp edx, 12
  jb 5b
  test ebp, ebp
  jnz 8f                             # the menus: no right-stick buttons
  mov eax, dword ptr [PRY]
  cmp eax, RSHALF
  jle 7f
  or ecx, 0x40                       # right stick up = button 7 (JOY_F7, climb)
7:
  cmp eax, -RSHALF
  jge 8f
  or ecx, 0x80                       # right stick down = button 8 (JOY_F8, descend)
8:
  mov dword ptr [esi + 0x18], ecx
  mov eax, ebx
  and eax, 0xf                       # D-pad bits
  .byte 0x0f, 0xb7, 0x04, 0x45       # movzx eax, word ptr [povmap + eax*2]
  .long A_POVMAP
  mov dword ptr [esi + 0x1c], eax
  or dword ptr [esi + 0x20], 0x84
  ret

# axisf: eax = a stick axis (-32768..32767) -> st(0) = -1..1. Changes eax.
axisf:
  cmp eax, -32767
  jge 1f
  mov eax, -32767
1:
  push eax
  fild dword ptr [esp]
  fmul dword ptr [A_AXSCALE]
  pop eax
  ret

# trigv: eax = a trigger (0..255) -> eax = 0..247, 0 inside the dead zone TDZT and counted from its edge.
trigv:
  sub eax, TDZT
  jg 1f
  xor eax, eax
1:
  ret

# ---------------------------------------------------------------------------------------------------------------
# readpad: the pad into PB / PLX / PLY / PRX / PRY / PLT / PRT (XInput layout), the buttons before into PPB: XInput
# pad 0..3, the first connected one. The first call looks for XInputGetState in xinput1_4.dll, else xinput1_3.dll,
# else xinput9_1_0.dll (Proton has all three; Windows 8+ has 1_4 and 9_1_0; the exe imports none of them).
# Returns eax = 1 with a reading, 0 without (no XInput, no pad). Keeps every other register.
readpad:
  pushad
  mov eax, dword ptr [PB]
  mov dword ptr [PPB], eax
  cmp dword ptr [XINIT], 0
  jne 10f
  mov dword ptr [XINIT], 1
  .byte 0xbe                         # mov esi, the three names (16 bytes each)
  .long A_XINPUT
  mov ebx, 3
2:
  push esi
  call dword ptr [LoadLibraryA]
  test eax, eax
  jz 3f
  PUSHI BASE + (s_xgs - start)
  push eax
  call dword ptr [GetProcAddress]
  test eax, eax
  jz 3f
  mov dword ptr [XGS], eax
  jmp 10f
3:
  add esi, 16
  dec ebx
  jnz 2b
10:
  cmp dword ptr [XGS], 0
  je 99f
  xor ebx, ebx                       # pad index
11:
  PUSHI XS
  push ebx
  call dword ptr [XGS]
  test eax, eax
  jz 12f
  inc ebx
  cmp ebx, 4
  jb 11b
  jmp 99f
12:
  movzx eax, word ptr [XS + 4]
  mov dword ptr [PB], eax
  movzx eax, byte ptr [XS + 6]
  mov dword ptr [PLT], eax
  movzx eax, byte ptr [XS + 7]
  mov dword ptr [PRT], eax
  movsx eax, word ptr [XS + 8]
  mov dword ptr [PLX], eax
  movsx eax, word ptr [XS + 10]
  mov dword ptr [PLY], eax
  movsx eax, word ptr [XS + 12]
  mov dword ptr [PRX], eax
  movsx eax, word ptr [XS + 14]
  mov dword ptr [PRY], eax
  popad
  mov eax, 1
  ret
99:
  xor eax, eax
  mov dword ptr [PB], eax
  mov dword ptr [PLX], eax
  mov dword ptr [PLY], eax
  mov dword ptr [PRX], eax
  mov dword ptr [PRY], eax
  mov dword ptr [PLT], eax
  mov dword ptr [PRT], eax
  popad
  xor eax, eax
  ret

# ---------------------------------------------------------------------------------------------------------------
# movpeek (patch movieskip): the movie player's decode loop (0x4d9a27) calls PeekMessageA once per step; the call
# now comes here first. While a skippable movie plays (MOVIEON, the same test the window procedure makes for Enter /
# Esc), A, B, X, Y, Start or View newly pressed on the pad stops it the way Enter does (MOVIESTOP). Then on to
# PeekMessageA with the caller's arguments still on the stack.
movpeek:
  pushad
  cmp dword ptr [MOVIEON], 1
  jne 9f
  call readpad
  test eax, eax
  jz 9f
  mov eax, dword ptr [PB]
  mov ecx, dword ptr [PPB]
  not ecx
  and eax, ecx                       # newly pressed
  test eax, 0xf030                   # A B X Y View Start
  jz 9f
  CALLA MOVIESTOP
9:
  popad
  jmp dword ptr [PeekMessageA]

# ---------------------------------------------------------------------------------------------------------------
# nodialog (patch nodialog): WinMain's start-up dialog ("DialogBoxParamA(hInst, 101, 0, 0x46a258, 0)", 0x46948e:
# renderer, 3D device, Hi-Res Movies, OK / Cancel) now comes here: the dialog's own defaults, chosen as if OK were
# pressed at once (its WM_INITDIALOG and OK code, 0x46a2a4 / 0x46a5c0): the Direct3D hardware renderer when there is
# one (else software), the last device of its list, hi-res movies when the CPU has MMX. stdcall, 5 arguments.
nodialog:
  pushad
  push 0                             # count
  mov eax, esp
  CALLA ENUMDEV
  pop edx                            # count
  mov dword ptr [DEVFLAGS], eax
  xor ecx, ecx                       # software 8-bit
  test al, 0x14
  jz 1f
  mov ecx, 3                         # a hardware device
1:
  mov dword ptr [RENDER], ecx
  lea ebx, [edx - 1]                 # the list's default: its last entry
  cmp ecx, 3
  jne 2f
  test byte ptr [DEVFLAGS], 0x10
  jz 2f
  cmp ebx, 1
  jne 2f
  mov dword ptr [RENDER], 4          # entry 1 is the ATI Rage driver when there is one
2:
  cmp ebx, 1
  jle 3f
  dec ebx
3:
  mov dword ptr [DEVICE], ebx
  CALLA HASMMX
  neg eax
  sbb eax, eax
  neg eax
  mov dword ptr [HIRESMOV], eax
  mov dword ptr [DLGOK], 1
  popad
  mov eax, 1
  ret 0x14

# ---------------------------------------------------------------------------------------------------------------
# regpaths (patch noreg): the start-up registry read (0x46aabc, called at 0x4697a5) wanted the installer's
# HKLM\SOFTWARE\Psygnosis\Studios\G-Police values (else its first-run branch quits for want of "Path"). The call now
# comes here: the configuration and save files and the "CD" are the working directory (the exe's folder, Steam's
# Start In); "Control Method" and "SysChk" (which the game itself writes to that key) are still read when they are
# there, as before.
regpaths:
  pushad
  .byte 0xbe                         # mov esi, ".\GPOLICE.CFG"
  .long BASE + (s_cfg - start)
  .byte 0xbf                         # mov edi, CFGPATH
  .long CFGPATH
  call strcopy
  .byte 0xbe
  .long BASE + (s_sav - start)
  .byte 0xbf
  .long SAVPATH
  call strcopy
  .byte 0xbe
  .long BASE + (s_res - start)
  .byte 0xbf
  .long RESPATH
  call strcopy
  .byte 0xbb                         # mov ebx, key
  .long S_KEY
  .byte 0xba                         # mov edx, out
  .long CTRLMETH
  .byte 0xb8                         # mov eax, value name
  .long S_CTRL
  CALLA REGGET
  .byte 0xbb
  .long S_KEY2
  .byte 0xba
  .long SYSCHK
  .byte 0xb8
  .long S_SYSCHK
  CALLA REGGET
  popad
  ret

# strcopy: copy the 0-terminated string at esi to edi. Changes eax, esi, edi.
strcopy:
  mov al, byte ptr [esi]
  mov byte ptr [edi], al
  inc esi
  inc edi
  test al, al
  jnz strcopy
  ret


# ---------------------------------------------------------------------------------------------------------------
# Widescreen (patch widescreen, docs/TECHNICAL.md, "Widescreen"). The 3D is made Hor+ in patch_exe.py (the focal length follows the
# height). The 2D of a mission (HUD, pause menu, loading screen) is laid out by the game from the play mode's width
# (each HUD module gets width x height at the mission start, 0x458276...) and drawn with absolute 2D primitives
# that add the current view's origin (view + 0x30); the 3D and the few centre-relative 2D lines do not add it. So:
# every 2D module is handed W2D (4:3: 4 x height / 3) instead of the width, and the in-game view's origin is X0,
# which moves all of that 2D, unstretched, into a 4:3 area in the middle of the wide screen, while the 3D fills it.
# At 4:3 (and narrower) W2D = the width and X0 = 0: exactly the original.

# modeset: the mode set's "mov [SCRW], esi; mov [SCRH], edi" (0x469e02, 12 bytes) comes here: the same, plus W2D
# and X0 for that mode.
modeset:
  mov dword ptr [SCRW], esi
  mov dword ptr [SCRH], edi
  push eax
  push ecx
  push edx
  mov eax, edi
  call w43
  cmp eax, esi
  jb 1f                              # 4 x height / 3 narrower than the mode: a wide mode
  mov eax, esi
1:
  mov dword ptr [W2D], eax
  mov ecx, esi
  sub ecx, eax
  shr ecx, 1
  mov dword ptr [X0], ecx
  pop edx
  pop ecx
  pop eax
  ret

# w43: eax = a height -> eax = 4 x height / 3. Changes edx.
w43:
  push ecx
  shl eax, 2
  xor edx, edx
  mov ecx, 3
  div ecx
  pop ecx
  ret

# viewset: the in-game view's set-up at each mode set (0x458ca0, "call VIEWSET" at 0x458cd4, the full screen) comes
# here: the same, then the view's 2D origin x = X0.
viewset:
  push dword ptr [esp + 0xc]
  push dword ptr [esp + 0xc]
  push dword ptr [esp + 0xc]         # the three stack arguments again
  CALLA VIEWSET
  push ecx
  mov ecx, dword ptr [X0]
  mov dword ptr [ORIGIN_X], ecx
  pop ecx
  ret 0xc

# w2dstore: each frame the renderer copies the screen size into the screen struct 0x541d20 (0x492632: "mov ebx,
# [ebx]; mov [edx + 0xc], ebx"); its width (+0xc) is read only by 2D code (a radar scale, an effect's centre, a
# projected 2D position) and by the 3D view's frustum (frust, below). Now +0xc = the 2D width: the screen's width,
# or 4 x height / 3 when wider (computed from the screen itself: the menus' 640x480 is set without the mode set).
# ebx = the screen size {width, height}, edx = the struct; eax (the display) is kept for the code after.
w2dstore:
  push eax
  push ecx
  push edx
  mov ecx, ebx
  mov ebx, dword ptr [ecx]           # width
  mov eax, dword ptr [ecx + 4]       # height
  call w43
  cmp eax, ebx
  jae 1f
  mov ebx, eax
1:
  pop edx
  mov dword ptr [edx + 0xc], ebx
  pop ecx
  pop eax
  ret

# frust: the 3D view's frustum (0x471b94: "mov ecx, [edx + 8]; mov ebx, [edx + 0xc]; mov esi, [edx + 0x10]", the
# focal length, width, height from the screen struct) keeps the real screen width (w2dstore changed +0xc): the 3D
# culls for the whole wide picture.
frust:
  mov ecx, dword ptr [edx + 8]
  .byte 0x8b, 0x1d                   # mov ebx, [DISPLAY]
  .long DISPLAY
  mov ebx, dword ptr [ebx + 4]
  mov ebx, dword ptr [ebx]           # the screen's width
  mov esi, dword ptr [edx + 0x10]
  ret

# hudys: the cockpit HUD's set-up (0x44aae0) keeps two integer scales, x = width / 320 (0x509c40) and y = height /
# 200 (0x509c44, "mov [0x509c44], eax" at 0x44ac72 comes here). In a wide mode the HUD gets W2D x height (4:3), and
# for the Deck's 1066 x 800 that would be 3 and 4, a size no 4:3 mode has; then y = x (3 and 3, as at 1024x768).
# At 4:3 (X0 = 0) the game's own values.
hudys:
  cmp dword ptr [X0], 0
  je 1f
  cmp eax, dword ptr [HUDXS]
  jbe 1f
  mov eax, dword ptr [HUDXS]
1:
  mov dword ptr [HUDYS], eax
  ret
# ---------------------------------------------------------------------------------------------------------------
  .p2align 2
btnmap:    .short 0x1000, 0x2000, 0x4000, 0x8000, 0x0100, 0x0200, 0, 0, 0x0010, 0x0020, 0x0040, 0x0080
                                     # game buttons 0-11 (A B X Y LB RB [RS up] [RS down] Start View L3 R3) as XInput bits
povmap:    .short 0xffff, 0, 18000, 0xffff, 27000, 31500, 22500, 27000, 9000, 4500, 13500, 9000, 0xffff, 0, 18000, 0xffff
                                     # D-pad bits (up 1, down 2, left 4, right 8) -> POV; up+down / left+right cancel
  .p2align 2
f_axscale: .long 0x38000100          # 1 / 32767
f_trscale: .long 0x3b84a9fa          # 1 / (255 - TDZT) = 1 / 247
s_xgs:     .asciz "XInputGetState"
s_cfg:     .asciz ".\\GPOLICE.CFG"
s_sav:     .asciz ".\\GPOLICE.SAV"
s_res:     .asciz ".\\"
  .p2align 4
s_xinput:  .asciz "xinput1_4.dll"
  .p2align 4
           .asciz "xinput1_3.dll"
  .p2align 4
           .asciz "xinput9_1_0.dll"
.set A_AXSCALE, BASE + (f_axscale - start)
.set A_TRSCALE, BASE + (f_trscale - start)
.set A_XINPUT, BASE + (s_xinput - start)
.set A_BTNMAP, BASE + (btnmap - start)
.set A_POVMAP, BASE + (povmap - start)
