#!/usr/bin/env python3
"""Cross-check PCB pad-net assignments vs schematic netlist. Report mismatches."""
import re, subprocess, tempfile, os
import pcbnew

BOARD = '/Users/ppisljar/Sonatino/kicad_project/esp32audio/esp32audio.kicad_pcb'
SCH = '/Users/ppisljar/Sonatino/kicad_project/esp32audio/esp32audio.kicad_sch'

# Export netlist
netf = tempfile.NamedTemporaryFile(suffix='.net', delete=False).name
subprocess.run([
    '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli',
    'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', netf, SCH
], check=True, capture_output=True)
net = open(netf).read()

# Parse schematic: pin -> net
sch = {}
for chunk in re.split(r'(?m)^\t\t\(net\b', net)[1:]:
    name_m = re.search(r'\(name\s+"([^"]*)"\)', chunk)
    if not name_m: continue
    nname = name_m.group(1).lstrip('/')
    for nm in re.finditer(r'\(node\s+\(ref\s+"([^"]+)"\)\s+\(pin\s+"([^"]+)"\)', chunk):
        sch[(nm.group(1), nm.group(2))] = nname

# Load PCB
b = pcbnew.LoadBoard(BOARD)

# Build pcb pin->net map (skip NPTH no-name pads)
pcb = {}
pcb_refs = set()
for fp in b.GetFootprints():
    ref = fp.GetReference()
    pcb_refs.add(ref)
    for pad in fp.Pads():
        num = pad.GetNumber()
        if not num: continue  # skip mount holes / NPTH
        pcb[(ref, num)] = pad.GetNetname()

sch_refs = {r for r,_ in sch.keys()}
print(f"Schematic refs: {len(sch_refs)}, PCB refs: {len(pcb_refs)}")
print(f"Schematic pins: {len(sch)}, PCB pads (numbered): {len(pcb)}")

# === Refs in schematic but not in PCB ===
missing_in_pcb = sch_refs - pcb_refs
if missing_in_pcb:
    print(f"\n!! Refs in schematic but NOT in PCB: {sorted(missing_in_pcb)}")

# === Refs in PCB but not in schematic ===
missing_in_sch = pcb_refs - sch_refs
if missing_in_sch:
    print(f"\n!! Refs in PCB but NOT in schematic: {sorted(missing_in_sch)}")

# === Pad/pin mismatches ===
print("\n=== MISMATCH: schematic pin exists, PCB pad missing ===")
sch_pin_missing_pcb = []
for key, sch_net in sch.items():
    if key not in pcb:
        sch_pin_missing_pcb.append((key, sch_net))
for (ref, pin), sn in sorted(sch_pin_missing_pcb):
    print(f"  {ref}.{pin}  expected net={sn!r}  -- no matching PCB pad")

print("\n=== MISMATCH: PCB pad exists, schematic pin missing or different net ===")
mismatches = []
unconnected = []
for key, pcb_net in pcb.items():
    sch_net = sch.get(key)
    if sch_net is None:
        # Pad exists on PCB but no schematic pin with that number
        if pcb_net:
            mismatches.append((key, pcb_net, '(not in schematic)'))
    elif sch_net != pcb_net:
        if pcb_net == '':
            unconnected.append((key, sch_net))
        else:
            mismatches.append((key, pcb_net, sch_net))

for (ref, pin), pn, sn in sorted(mismatches):
    print(f"  {ref}.{pin}  PCB={pn!r}  SCH={sn!r}")

print("\n=== PCB PADS WITH NO NET (orphaned) ===")
print("  (pad has number, schematic says it should be on a net, but PCB has it empty)")
for (ref, pin), sn in sorted(unconnected):
    print(f"  {ref}.{pin}  should be on net {sn!r}")

# Summary
print("\n=== SUMMARY ===")
print(f"  Refs match: {len(sch_refs & pcb_refs)} of {len(sch_refs)} schematic refs")
print(f"  Pin mismatches: {len(mismatches)}")
print(f"  Pads unconnected (should be on a net): {len(unconnected)}")
print(f"  Schematic pins missing PCB pads: {len(sch_pin_missing_pcb)}")
