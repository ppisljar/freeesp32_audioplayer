#!/usr/bin/env python3
"""Iterative footprint sync: process ONE swap, save, exit. Caller loops until clean."""
import re
import pcbnew
import os
import sys

BOARD = '/Users/ppisljar/Sonatino/kicad_project/esp32audio/esp32audio.kicad_pcb'
SCH = '/Users/ppisljar/Sonatino/kicad_project/esp32audio/esp32audio.kicad_sch'

LIB_PATHS = [
    '/Users/ppisljar/Sonatino/kicad_project/New_Library.pretty',
    '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints',
]

def find_library(nick):
    for base in LIB_PATHS:
        if base.endswith('.pretty') and os.path.basename(base) == f'{nick}.pretty':
            return base
        cand = os.path.join(base, f'{nick}.pretty')
        if os.path.isdir(cand):
            return cand
    return None

with open(SCH) as f:
    sch = f.read()
sch_footprints = {}
sym_blocks = re.findall(r'\(symbol\s+\(lib_id[^)]+\)(.*?)\(instances', sch, re.DOTALL)
for body in sym_blocks:
    ref_m = re.search(r'\(property "Reference" "([^"]+)"', body)
    fp_m = re.search(r'\(property "Footprint" "([^"]*)"', body)
    if ref_m and fp_m and fp_m.group(1).strip():
        sch_footprints[ref_m.group(1).strip()] = fp_m.group(1).strip()

b = pcbnew.LoadBoard(BOARD)
io = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP)

# Find first swap needed
target = None
for fp in b.GetFootprints():
    ref = fp.GetReference()
    fpid = fp.GetFPID()
    current = f"{fpid.GetLibNickname()}:{fpid.GetLibItemName()}"
    expected = sch_footprints.get(ref)
    if expected and current != expected:
        target = (ref, current, expected)
        break

if target is None:
    print("DONE: all footprints match schematic")
    sys.exit(0)

ref, cur, exp = target
print(f"Updating {ref}: {cur} -> {exp}")

fp = b.FindFootprintByReference(ref)
pos = pcbnew.VECTOR2I(fp.GetPosition().x, fp.GetPosition().y)
rot = fp.GetOrientation()
on_bottom = (fp.GetLayer() == pcbnew.B_Cu)
value = fp.GetValue()
pad_nets = {}
for pad in fp.Pads():
    n = pad.GetNumber()
    if n:
        pad_nets[n] = pad.GetNetname()

lib_nick, fp_name = exp.split(':', 1)
lib_dir = find_library(lib_nick)
if not lib_dir:
    print(f"ERROR: library {lib_nick} not found")
    sys.exit(2)

new_fp = io.FootprintLoad(lib_dir, fp_name)
if new_fp is None:
    print(f"ERROR: FootprintLoad returned None")
    sys.exit(2)

b.Remove(fp)
new_fp.SetReference(ref)
new_fp.SetValue(value)
# Set FPID with explicit library nickname
new_fpid = pcbnew.LIB_ID(lib_nick, fp_name)
new_fp.SetFPID(new_fpid)
b.Add(new_fp)  # Add to board FIRST, then position/orient/flip
new_fp.SetPosition(pos)
if on_bottom:
    # Use SetLayerAndFlip instead of Flip
    try:
        new_fp.SetLayerAndFlip(pcbnew.B_Cu)
    except AttributeError:
        # Fall back to Flip with explicit position
        new_fp.Flip(pos, False)
new_fp.SetOrientation(rot)
# Restore net assignments
for pad in new_fp.Pads():
    n = pad.GetNumber()
    if n in pad_nets and pad_nets[n]:
        net_obj = b.FindNet(pad_nets[n])
        if net_obj:
            pad.SetNet(net_obj)
print(f"OK")
pcbnew.SaveBoard(BOARD, b)
sys.exit(1)  # exit code 1 = "did one, more to do, call me again"
