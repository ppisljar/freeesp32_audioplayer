#!/usr/bin/env python3
"""Rip up all PCB_TRACK and PCB_VIA. Keep zones, footprints, drawings."""
import pcbnew
BOARD = '/Users/ppisljar/Sonatino/kicad_project/esp32audio/esp32audio.kicad_pcb'
b = pcbnew.LoadBoard(BOARD)
tracks = [t for t in b.GetTracks()]
n_tracks = n_vias = 0
for t in tracks:
    c = t.GetClass()
    if c == 'PCB_TRACK':
        b.Remove(t); n_tracks += 1
    elif c == 'PCB_VIA':
        b.Remove(t); n_vias += 1
pcbnew.SaveBoard(BOARD, b)
print(f"Ripped {n_tracks} tracks, {n_vias} vias")
