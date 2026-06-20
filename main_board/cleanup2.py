#!/usr/bin/env python3
"""
Round 2 cleanup:
1. Remove all 42x32 outline remnants — keep only the 50x42 outline
2. Set U3 EP pad (pin 17) to GND net (fixes APA2068 EP grounding properly)
3. Remove my extra GND vias under U3 EP (they're now redundant once EP is GND)
4. Move all component reference text to F.Fab/B.Fab (kills silk_overlap explosion)
5. Re-fill zones, save
"""
import pcbnew

BOARD = '/Users/ppisljar/Sonatino/kicad_project/esp32audio/esp32audio.kicad_pcb'
b = pcbnew.LoadBoard(BOARD)
def mm(x): return x/1_000_000.0

stats = {
    'outline_42x32_removed': 0,
    'outline_kept': 0,
    'ep_pad_fixed': False,
    'ep_extra_vias_removed': 0,
    'fp_refs_moved_to_fab': 0,
    'fp_values_hidden': 0,
}

# ============================================================
# 0. Silk cleanup FIRST (before Remove() invalidates iterators)
# ============================================================
F_Fab_ = pcbnew.F_Fab
B_Fab_ = pcbnew.B_Fab
F_Silk_ = pcbnew.F_SilkS
B_Silk_ = pcbnew.B_SilkS
for fp in b.GetFootprints():
    layer = fp.GetLayer()
    fab_layer = F_Fab_ if layer == pcbnew.F_Cu else B_Fab_
    ref = fp.Reference()
    if ref.GetLayer() in (F_Silk_, B_Silk_):
        ref.SetLayer(fab_layer)
        stats['fp_refs_moved_to_fab'] += 1
    val = fp.Value()
    if val.IsVisible():
        val.SetVisible(False)
        stats['fp_values_hidden'] += 1

# ============================================================
# 1. Strip 42x32 outline remnants
# ============================================================
# The 50x42 outline has corners at 1.5, 48.5, 40.5
# The 42x32 outline has corners at 1, 41, 31
# Any segment touching coords 31, 32, 41 (and not 50, 42, 40.5) is 42x32

OLD_COORDS = {31.0, 32.0, 41.0}
NEW_COORDS = {0.0, 1.5, 48.5, 50.0, 40.5, 42.0}

def is_42x32_segment(d):
    """True if this drawing belongs to the dead 42x32 outline."""
    s = (mm(d.GetStart().x), mm(d.GetStart().y))
    e = (mm(d.GetEnd().x), mm(d.GetEnd().y))
    coords = {round(c, 2) for c in (s[0], s[1], e[0], e[1])}
    # If it touches an OLD coord and NO NEW-only coord -> it's the dead outline
    touches_old = bool(coords & OLD_COORDS)
    touches_only_new = coords.issubset(NEW_COORDS | {1.0})  # 1.0 is a corner radius pt for 50x42 arcs
    return touches_old and not touches_only_new

# Also remove arcs not on the 50x42 corner positions
NEW_CORNERS = [(1.5, 0), (48.5, 0), (50, 1.5), (50, 40.5),
               (48.5, 42), (1.5, 42), (0, 40.5), (0, 1.5)]

def is_new_arc(d):
    s = (round(mm(d.GetStart().x), 2), round(mm(d.GetStart().y), 2))
    e = (round(mm(d.GetEnd().x), 2), round(mm(d.GetEnd().y), 2))
    # Both endpoints should be on NEW corner positions
    for ep in (s, e):
        if not any(abs(ep[0]-cx) < 0.05 and abs(ep[1]-cy) < 0.05 for cx,cy in NEW_CORNERS):
            return False
    return True

# Also: detect the segment (0,1)->(0,31) which has BOTH endpoints in NEW_COORDS|{1.0}
# but is part of the 42x32 outline. Distinguish by: if endpoint coord = 31, it's old.
# The 50x42 west edge is (0,1.5)->(0,40.5), not (0,1)->(0,31).

to_remove = []
for d in b.GetDrawings():
    if d.GetLayerName() != 'Edge.Cuts':
        continue
    s = (round(mm(d.GetStart().x), 2), round(mm(d.GetStart().y), 2))
    e = (round(mm(d.GetEnd().x), 2), round(mm(d.GetEnd().y), 2))
    shape = d.GetShape()
    SHAPE_ARC = pcbnew.SHAPE_T_ARC

    # Determine if this segment is on the 50x42 outline
    keep = False
    if shape == SHAPE_ARC:
        keep = is_new_arc(d)
    else:
        # Segment: must lie on 50x42 perimeter
        # West edge: x=0, y from 1.5 to 40.5
        if s[0] == 0 and e[0] == 0:
            keep = (min(s[1], e[1]) >= 1.5 - 0.05) and (max(s[1], e[1]) <= 40.5 + 0.05)
        # East edge: x=50, y from 1.5 to 40.5
        elif abs(s[0] - 50) < 0.05 and abs(e[0] - 50) < 0.05:
            keep = (min(s[1], e[1]) >= 1.5 - 0.05) and (max(s[1], e[1]) <= 40.5 + 0.05)
        # North edge: y=0, x from 1.5 to 48.5
        elif s[1] == 0 and e[1] == 0:
            keep = (min(s[0], e[0]) >= 1.5 - 0.05) and (max(s[0], e[0]) <= 48.5 + 0.05)
        # South edge: y=42, x from 1.5 to 48.5
        elif abs(s[1] - 42) < 0.05 and abs(e[1] - 42) < 0.05:
            keep = (min(s[0], e[0]) >= 1.5 - 0.05) and (max(s[0], e[0]) <= 48.5 + 0.05)

    if not keep:
        to_remove.append((d, s, e))
    else:
        stats['outline_kept'] += 1

for d, s, e in to_remove:
    print(f"Remove outline: {s} -> {e}")
    b.Remove(d)
    stats['outline_42x32_removed'] += 1

# ============================================================
# 2. Set U3 EP pad (pin 17 — the SMD rectangular thermal pad) to GND
# ============================================================
u3 = b.FindFootprintByReference('U3')
if u3:
    gnd_net = b.FindNet('GND')
    if gnd_net is None:
        # Create it
        gnd_net = pcbnew.NETINFO_ITEM(b, 'GND')
        b.Add(gnd_net)
    for pad in u3.Pads():
        # Look for the EP SMD pad (large rect, pin 17)
        if pad.GetNumber() == '17' and pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
            sz = pad.GetSize()
            if sz.x > 1_000_000:  # > 1mm
                print(f"Setting U3 pad 17 EP to GND: pos=({mm(pad.GetPosition().x):.2f},{mm(pad.GetPosition().y):.2f})")
                pad.SetNet(gnd_net)
                stats['ep_pad_fixed'] = True
        # Also set the 6 NPTH thermal vias (through_hole pad type, small) to GND
        elif pad.GetNumber() == '17' and pad.GetAttribute() in (pcbnew.PAD_ATTRIB_NPTH, pcbnew.PAD_ATTRIB_PTH):
            sz = pad.GetSize()
            if sz.x < 1_000_000:  # the small thermal stitches
                # Change to PTH so they actually plate to GND
                pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
                pad.SetNet(gnd_net)
                # Also make sure the layer set includes the copper layers
                ls = pcbnew.LSET()
                ls.AddLayer(pcbnew.F_Cu)
                ls.AddLayer(pcbnew.B_Cu)
                # Keep mask layers too
                ls.AddLayer(pcbnew.F_Mask)
                ls.AddLayer(pcbnew.B_Mask)
                pad.SetLayerSet(ls)

    # Now remove my added GND vias that are co-located with the EP thermal stitches
    ep_locs = [(28.8, 29.5), (30, 29.5), (31.2, 29.5),
               (28.8, 30.5), (30, 30.5), (31.2, 30.5)]
    for track in list(b.GetTracks()):
        if track.GetClass() != 'PCB_VIA':
            continue
        x, y = round(mm(track.GetPosition().x), 2), round(mm(track.GetPosition().y), 2)
        if (x, y) in [(round(ex, 2), round(ey, 2)) for ex, ey in ep_locs]:
            net = track.GetNetname()
            print(f"Remove redundant GND via @ ({x},{y}) net={net}")
            b.Remove(track)
            stats['ep_extra_vias_removed'] += 1

# ============================================================
# 3. Hide footprint Reference (move to F.Fab) and Value (hide) text
#    — kills 199 silk_overlap violations
# ============================================================
F_Fab = pcbnew.F_Fab
B_Fab = pcbnew.B_Fab
F_Silk = pcbnew.F_SilkS
B_Silk = pcbnew.B_SilkS

# (silk cleanup moved to step 0 above)

# ============================================================
# 4. Re-fill and save
# ============================================================
filler = pcbnew.ZONE_FILLER(b)
filler.Fill(list(b.Zones()))
pcbnew.SaveBoard(BOARD, b)

print("\n=== Summary ===")
for k, v in stats.items():
    print(f"  {k}: {v}")
print(f"  Outline drawings remaining: {sum(1 for d in b.GetDrawings() if d.GetLayerName()=='Edge.Cuts')}")
print(f"  Total vias remaining: {sum(1 for t in b.GetTracks() if t.GetClass()=='PCB_VIA')}")
