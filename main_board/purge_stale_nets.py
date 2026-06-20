#!/usr/bin/env python3
"""
Remove stale nets (D1_NET..D4_NET) left over from before the SD swap.
Also removes any tracks/vias still on those nets.
"""
import pcbnew
BOARD = '/Users/ppisljar/Sonatino/kicad_project/esp32audio/esp32audio.kicad_pcb'
b = pcbnew.LoadBoard(BOARD)

STALE = {'D1_NET', 'D2_NET', 'D3_NET', 'D4_NET'}

# First: rip tracks/vias on stale nets
tracks_to_remove = []
for t in b.GetTracks():
    if t.GetNetname() in STALE:
        tracks_to_remove.append(t)
print(f"Tracks/vias on stale nets: {len(tracks_to_remove)}")
for t in tracks_to_remove:
    b.Remove(t)

# Look up nets by name and clear stale ones (set net code to 0 on any pads still referencing)
netinfo = b.GetNetInfo()
stale_codes = []
for n in STALE:
    net = b.FindNet(n)
    if net:
        stale_codes.append(net.GetNetCode())
        print(f"Found stale net: {n} (code {net.GetNetCode()})")

# Clear stale net assignments from pads (set to unconnected net 0)
for fp in b.GetFootprints():
    for pad in fp.Pads():
        if pad.GetNetname() in STALE:
            pad.SetNetCode(0)
            print(f"  Cleared pad {fp.GetReference()}.{pad.GetNumber()} (was on {pad.GetNetname()})")

# Remove the net definitions
removed_nets = 0
for n in list(STALE):
    net = b.FindNet(n)
    if net:
        netinfo.RemoveNet(net)
        removed_nets += 1
print(f"Removed {removed_nets} stale net definitions")

pcbnew.SaveBoard(BOARD, b)
print("Saved.")
