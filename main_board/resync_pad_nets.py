#!/usr/bin/env python3
"""
Parse schematic for ref.pin -> net mapping, fix PCB pad-to-net assignments
that the MCP sync didn't propagate.
"""
import re
import pcbnew

BOARD = '/Users/ppisljar/Sonatino/kicad_project/esp32audio/esp32audio.kicad_pcb'
SCH = '/Users/ppisljar/Sonatino/kicad_project/esp32audio/esp32audio.kicad_sch'

# === Parse schematic ===
# A net is defined by labels on a wire net. We extract from the netlist style.
# Easier: parse all (symbol ...) blocks with (instances ...) to get refs and pin nets.
# Easier still: read net labels and trace, but complex. Use simpler approach:
# Parse the .net file if available, or use the kicad-cli to export netlist.
# Fallback: extract from schematic by parsing each symbol's pins and connected wires.

# Easiest: use kicad-cli to export netlist
import subprocess, os, tempfile, json
netlist_path = tempfile.NamedTemporaryFile(suffix='.net', delete=False).name
subprocess.run([
    '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli',
    'sch', 'export', 'netlist', '--format', 'kicadsexpr',
    '-o', netlist_path, SCH
], check=True, capture_output=True)
print(f"Netlist exported to {netlist_path}")

netlist = open(netlist_path).read()

# Parse netlist. Format:
# (net
#     (code "26")
#     (name "/SD_CS")
#     (node (ref "U1") (pin "2") ...)
# )
sch_pin_nets = {}
# Split on `(net\n` to get each net's block
chunks = re.split(r'(?m)^\t\t\(net\b', netlist)
for chunk in chunks[1:]:
    # find name and stop before next net/footprint section
    name_m = re.search(r'\(name\s+"([^"]*)"\)', chunk)
    if not name_m: continue
    net_name = name_m.group(1).lstrip('/')  # remove leading /
    # Find all nodes in this chunk (until the chunk ends or next (net starts)
    for node_m in re.finditer(r'\(node\s+\(ref\s+"([^"]+)"\)\s+\(pin\s+"([^"]+)"\)', chunk):
        ref, pin = node_m.group(1), node_m.group(2)
        sch_pin_nets[(ref, pin)] = net_name

print(f"Parsed {len(sch_pin_nets)} pin-net assignments from schematic")

# === Compare with PCB ===
b = pcbnew.LoadBoard(BOARD)
changes = []
for fp in b.GetFootprints():
    ref = fp.GetReference()
    for pad in fp.Pads():
        num = pad.GetNumber()
        if not num:
            continue
        sch_net = sch_pin_nets.get((ref, num))
        pcb_net = pad.GetNetname()
        if sch_net is None:
            continue  # NC pin in schematic
        # Normalize: schematic uses unnamed-net /xxx -> PCB shows "" or no name
        if sch_net.startswith('/') or sch_net == '':
            sch_net = ''
        if pcb_net != sch_net and sch_net != '':
            changes.append((ref, num, pcb_net, sch_net))

print(f"\nMismatches found: {len(changes)}")
for ref, pin, pcb_n, sch_n in changes:
    print(f"  {ref}.{pin}: PCB={pcb_n!r} -> SCH={sch_n!r}")

# === Apply fixes ===
fixed = 0
for ref, pin, pcb_n, sch_n in changes:
    fp = b.FindFootprintByReference(ref)
    if not fp:
        continue
    target_net = b.FindNet(sch_n)
    if not target_net:
        # Add new net
        print(f"  Adding new net '{sch_n}'")
        new_net = pcbnew.NETINFO_ITEM(b, sch_n)
        b.Add(new_net)
        target_net = b.FindNet(sch_n)
    if not target_net:
        print(f"  FAILED to find/create net {sch_n} for {ref}.{pin}")
        continue
    for pad in fp.Pads():
        if pad.GetNumber() == pin:
            pad.SetNet(target_net)
            fixed += 1
            break

print(f"\nFixed {fixed} pad-net assignments")

# Also rip up tracks/vias on stale D1_NET..D4_NET
STALE = {'D1_NET', 'D2_NET', 'D3_NET', 'D4_NET'}
removed_tracks = 0
for t in list(b.GetTracks()):
    if t.GetNetname() in STALE:
        b.Remove(t)
        removed_tracks += 1
print(f"Removed {removed_tracks} stale tracks/vias")

pcbnew.SaveBoard(BOARD, b)
print("Saved.")
