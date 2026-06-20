#!/usr/bin/env python3
"""
Force-reload U1's footprint from the New_Library file.
KiCad's UI "Update Footprints from Library" thinks U1 is already current
(same nickname:name), but the in-PCB copy has only 15 pads while the
library file has 24. Forcibly swap the footprint, preserving:
- position, rotation, layer (top/bottom)
- value, reference
- net assignments for pads 1-15 (16-24 will inherit whatever the
  schematic netlist sync writes next time you Update PCB from Schematic)
"""
import os, sys
import pcbnew

BOARD = '/Users/ppisljar/Sonatino/kicad_project/esp32audio/esp32audio.kicad_pcb'
LIB_DIR = '/Users/ppisljar/Sonatino/kicad_project/New_Library.pretty'
LIB_NICK = 'New_Library'
FP_NAME = 'XIAO_ESP32-S3_SMD'
REF = 'U1'

b = pcbnew.LoadBoard(BOARD)
io = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP)

fp = b.FindFootprintByReference(REF)
if fp is None:
    print(f"ERROR: {REF} not found on board"); sys.exit(2)

pos = pcbnew.VECTOR2I(fp.GetPosition().x, fp.GetPosition().y)
rot = fp.GetOrientation()
on_bottom = (fp.GetLayer() == pcbnew.B_Cu)
value = fp.GetValue()

# Snapshot existing pad-net assignments by pad number
pad_nets = {}
for pad in fp.Pads():
    n = pad.GetNumber()
    if n:
        pad_nets[n] = pad.GetNetname()
print(f"Snapshotted {len(pad_nets)} pad nets: {sorted(pad_nets.keys(), key=lambda x: int(x) if x.isdigit() else 99)}")

# Load fresh from library file
new_fp = io.FootprintLoad(LIB_DIR, FP_NAME)
if new_fp is None:
    print(f"ERROR: FootprintLoad({LIB_DIR}, {FP_NAME}) returned None"); sys.exit(2)

new_pads = [pad.GetNumber() for pad in new_fp.Pads()]
print(f"Library footprint has {len(new_pads)} pads: {sorted(set(new_pads), key=lambda x: int(x) if x.isdigit() else 99)}")

b.Remove(fp)
new_fp.SetReference(REF)
new_fp.SetValue(value)
new_fp.SetFPID(pcbnew.LIB_ID(LIB_NICK, FP_NAME))
b.Add(new_fp)
new_fp.SetPosition(pos)
if on_bottom:
    try:
        new_fp.SetLayerAndFlip(pcbnew.B_Cu)
    except AttributeError:
        new_fp.Flip(pos, False)
new_fp.SetOrientation(rot)

# Restore net assignments for pads that existed before
restored = 0
for pad in new_fp.Pads():
    n = pad.GetNumber()
    if n in pad_nets and pad_nets[n]:
        net_obj = b.FindNet(pad_nets[n])
        if net_obj:
            pad.SetNet(net_obj)
            restored += 1
print(f"Restored {restored} pad-net assignments")

pcbnew.SaveBoard(BOARD, b)
print(f"Saved. New pad count on {REF}: {len(new_pads)}")
