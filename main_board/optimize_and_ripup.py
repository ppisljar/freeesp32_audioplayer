#!/usr/bin/env python3
"""
Rip up all tracks/vias and move passives closer to the ICs they serve.
Run before Freerouting for cleaner results.
"""
import pcbnew
BOARD = '/Users/ppisljar/Sonatino/kicad_project/esp32audio/esp32audio.kicad_pcb'
b = pcbnew.LoadBoard(BOARD)
def nm(x): return int(x * 1_000_000)

# Rip up all tracks and vias FIRST (before Remove invalidates references)
tracks_list = [t for t in b.GetTracks()]
ripped = {'tracks': 0, 'vias': 0}
for t in tracks_list:
    cls = t.GetClass()
    if cls == 'PCB_TRACK':
        b.Remove(t); ripped['tracks'] += 1
    elif cls == 'PCB_VIA':
        b.Remove(t); ripped['vias'] += 1
print(f"Ripped {ripped['tracks']} tracks, {ripped['vias']} vias")

# Optimized passive positions based on IC pin locations
# U2 CS4344 at (30, 18.5) bottom rotated -90:
#   pin 5 (VQ)    at (31.0, 16.35) north-east
#   pin 6 (FILT+) at (31.0, 20.65) south-east
#   pin 9 (VA)    at (29.5, 20.65) south-center
# U3 APA2068 at (30, 30) bottom rotated -90:
#   pin 4 (BYPASS) ~ near IC body
#   pin 7 (VOLUME) ~ near IC body
#   pin 10/15 (VDD) ~ near IC body
#   pin 13 (SE/BTL) ~ near IC body

moves = [
    # CS4344 decoupling — under/next to U2
    ('C2', 28.5, 22.0, 0, 'B.Cu'),     # 0.1uF VA HF, south of U2 pin 9
    ('C3', 30.0, 22.5, 0, 'B.Cu'),     # 1uF VA bulk
    ('C4', 33.0, 21.0, 90, 'B.Cu'),    # 10uF FILT+ pin 6 (east of U2)
    ('C5', 33.0, 16.5, 90, 'B.Cu'),    # 0.1uF VQ HF pin 5 (east-north)
    ('C6', 33.0, 14.0, 90, 'B.Cu'),    # 3.3uF VQ popguard

    # APA2068 decoupling — keep near U3 (already pretty close)
    # C9, C10, C12, C15, R1, R2, R7, R8 are near U3 — minor nudges

    # SD card decoupling — already near J7
    # C18, C19 OK; R11-R13 OK

    # Boost FB divider — keep close to U4 (pin 1 is FB)
    # R9, R10 already close
]

for ref, x, y, rot, layer in moves:
    fp = b.FindFootprintByReference(ref)
    if fp is None:
        print(f"  WARN: {ref} not found")
        continue
    fp.SetPosition(pcbnew.VECTOR2I(nm(x), nm(y)))
    fp.SetOrientationDegrees(rot)
    target_layer = pcbnew.B_Cu if layer == 'B.Cu' else pcbnew.F_Cu
    if fp.GetLayer() != target_layer:
        try:
            fp.SetLayerAndFlip(target_layer)
        except AttributeError:
            fp.Flip(fp.GetPosition(), False)
    print(f"  Moved {ref} -> ({x}, {y}) rot={rot} {layer}")

pcbnew.SaveBoard(BOARD, b)
print("Saved.")
