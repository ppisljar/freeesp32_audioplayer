#!/usr/bin/env python3
"""
v1.1 PCB setup:
1. Delete ALL Edge.Cuts drawings (clean slate)
2. Add fresh 55x42mm rounded rectangle outline
3. Rip up all PCB_TRACK and PCB_VIA (Freerouting will redo)
4. Update J6 footprint to 1x6 (sync may have left old)
5. Save
"""
import pcbnew
BOARD = '/Users/ppisljar/Sonatino/kicad_project/esp32audio/esp32audio.kicad_pcb'
b = pcbnew.LoadBoard(BOARD)

def mm_to_nm(x): return int(x * 1_000_000)

# 3. Rip up all tracks and vias FIRST (before Remove invalidates b)
tracks_to_remove = [t for t in b.GetTracks()]
ripped = {'tracks': 0, 'vias': 0}
for t in tracks_to_remove:
    cls = t.GetClass()
    if cls == 'PCB_TRACK':
        b.Remove(t)
        ripped['tracks'] += 1
    elif cls == 'PCB_VIA':
        b.Remove(t)
        ripped['vias'] += 1
print(f"Ripped {ripped['tracks']} tracks, {ripped['vias']} vias")

# 1. Delete ALL Edge.Cuts drawings
drawings_to_remove = [d for d in b.GetDrawings() if d.GetLayerName() == 'Edge.Cuts']
for d in drawings_to_remove:
    b.Remove(d)
print(f"Removed {len(drawings_to_remove)} old Edge.Cuts drawings")

# 2. Add fresh 55x42mm rounded rectangle outline
# Use 4 line segments + 4 arcs for rounded corners
W, H, R = 55.0, 42.0, 1.5

def add_seg(x1, y1, x2, y2):
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(mm_to_nm(x1), mm_to_nm(y1)))
    s.SetEnd(pcbnew.VECTOR2I(mm_to_nm(x2), mm_to_nm(y2)))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(mm_to_nm(0.1))
    b.Add(s)

def add_arc(cx, cy, start_angle_deg, end_angle_deg):
    """Add a 90-degree arc with radius R centered at (cx, cy)"""
    import math
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_ARC)
    sa = math.radians(start_angle_deg)
    ea = math.radians(end_angle_deg)
    ma = (sa + ea) / 2
    start = pcbnew.VECTOR2I(mm_to_nm(cx + R*math.cos(sa)), mm_to_nm(cy + R*math.sin(sa)))
    mid = pcbnew.VECTOR2I(mm_to_nm(cx + R*math.cos(ma)), mm_to_nm(cy + R*math.sin(ma)))
    end = pcbnew.VECTOR2I(mm_to_nm(cx + R*math.cos(ea)), mm_to_nm(cy + R*math.sin(ea)))
    s.SetArcGeometry(start, mid, end)
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(mm_to_nm(0.1))
    b.Add(s)

# 4 straight edges
add_seg(R, 0, W-R, 0)           # north
add_seg(W, R, W, H-R)           # east
add_seg(W-R, H, R, H)           # south
add_seg(0, H-R, 0, R)           # west

# 4 rounded corners
add_arc(R, R, 180, 270)         # NW corner
add_arc(W-R, R, 270, 360)       # NE corner
add_arc(W-R, H-R, 0, 90)        # SE corner
add_arc(R, H-R, 90, 180)        # SW corner

print(f"Added new 55x42mm outline (8 segments)")

# 4. Save
pcbnew.SaveBoard(BOARD, b)
print("Saved.")
