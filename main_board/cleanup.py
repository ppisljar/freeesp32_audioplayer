#!/usr/bin/env python3
"""
PCB cleanup script — removes the mess auto-routing left behind.
Run via KiCad's bundled Python (has pcbnew module).
"""
import sys
import pcbnew
from collections import defaultdict

BOARD = '/Users/ppisljar/Sonatino/kicad_project/esp32audio/esp32audio.kicad_pcb'

b = pcbnew.LoadBoard(BOARD)

def mm(x):
    """KiCad native nm -> mm"""
    return x / 1_000_000.0

def nm(x):
    return int(x * 1_000_000)

# Board target dimensions (the one we want)
W, H = 50.0, 42.0
EDGE_MIN = 0.5  # min copper-to-edge per PCBWay
VIA_RADIUS = 0.3  # 0.6mm via diameter / 2

stats = {
    'outline_segments_removed': 0,
    'outline_segments_kept': 0,
    'vias_removed_near_edge': 0,
    'vias_removed_duplicates': 0,
    'vias_kept': 0,
    'dangling_traces_removed': 0,
}

# ============================================================
# 1. Clean up board outline — remove anything that's not on the
#    50x42 outline (the 42x32 first attempt + duplicate 50x42)
# ============================================================
# A rectangle outline on Edge.Cuts has 4 line segments + 4 arcs (rounded corners)
# We want to keep only segments whose endpoints lie on the 50x42 box.

def on_50x42_outline(start_mm, end_mm, tol=0.1):
    """Is this segment on the 50x42 perimeter (with rounded corners)?"""
    sx, sy = start_mm
    ex, ey = end_mm
    # Endpoints should be on one of the edges OR on a corner arc
    def on_edge(x, y):
        # On west edge x=0, east x=50, north y=0, south y=42 (within bounds)
        EPS = tol
        on_west = abs(x) < EPS and 1.0 <= y <= 40.5
        on_east = abs(x - 50) < EPS and 1.0 <= y <= 40.5
        on_north = abs(y) < EPS and 1.0 <= x <= 49.0
        on_south = abs(y - 42) < EPS and 1.0 <= x <= 49.0
        # Corner arc endpoints (radius 1.5mm corners)
        corners = [(1.5, 0), (48.5, 0), (50, 1.5), (50, 40.5),
                   (48.5, 42), (1.5, 42), (0, 40.5), (0, 1.5)]
        on_corner = any(abs(x-cx) < EPS and abs(y-cy) < EPS for cx,cy in corners)
        return on_west or on_east or on_north or on_south or on_corner
    return on_edge(sx, sy) and on_edge(ex, ey)

drawings_to_remove = []
for d in list(b.GetDrawings()):
    if d.GetLayerName() != 'Edge.Cuts':
        continue
    if d.GetClass() == 'PCB_SHAPE':
        shape = d.GetShape()
        # Get start/end in mm
        start = (mm(d.GetStart().x), mm(d.GetStart().y))
        end = (mm(d.GetEnd().x), mm(d.GetEnd().y))

        # For an arc, also check mid point
        keep = False
        if shape == pcbnew.SHAPE_T_ARC:
            # Arc endpoints should be on corner positions of 50x42
            keep = on_50x42_outline(start, end, tol=0.15)
        else:
            # Line segment
            keep = on_50x42_outline(start, end, tol=0.15)

        if not keep:
            drawings_to_remove.append((d, start, end))
        else:
            stats['outline_segments_kept'] += 1

for d, start, end in drawings_to_remove:
    print(f"Removing outline segment: {start} -> {end}")
    b.Remove(d)
    stats['outline_segments_removed'] += 1

# ============================================================
# 2. Remove vias too close to board edge OR co-located
# ============================================================
seen_positions = defaultdict(list)
vias_to_remove = []

for track in list(b.GetTracks()):
    if track.GetClass() != 'PCB_VIA':
        continue
    via = track
    x, y = mm(via.GetPosition().x), mm(via.GetPosition().y)
    net = via.GetNetname()

    # Too close to edge of 50x42 board?
    edge_dist = min(x, y, W - x, H - y)
    if edge_dist < EDGE_MIN + VIA_RADIUS:
        vias_to_remove.append((via, x, y, net, f"edge dist {edge_dist:.2f}mm"))
        continue

    # Co-located with another via?
    key = (round(x, 2), round(y, 2))
    seen_positions[key].append(via)

# Mark duplicates (keep one, remove rest)
for key, vias in seen_positions.items():
    if len(vias) > 1:
        # Keep the GND-net via if any, remove the rest
        gnd_vias = [v for v in vias if v.GetNetname() == 'GND']
        if gnd_vias:
            keeper = gnd_vias[0]
            for v in vias:
                if v is not keeper:
                    vias_to_remove.append((v, key[0], key[1], v.GetNetname(), "duplicate"))
        else:
            # Keep first, remove rest
            for v in vias[1:]:
                vias_to_remove.append((v, key[0], key[1], v.GetNetname(), "duplicate"))

removed_via_keys = set()
for via, x, y, net, reason in vias_to_remove:
    if id(via) in removed_via_keys:
        continue
    print(f"Removing via @ ({x:.2f},{y:.2f}) net={net!r} -- {reason}")
    b.Remove(via)
    removed_via_keys.add(id(via))
    if 'edge' in reason:
        stats['vias_removed_near_edge'] += 1
    else:
        stats['vias_removed_duplicates'] += 1

remaining = sum(1 for t in b.GetTracks() if t.GetClass() == 'PCB_VIA')
stats['vias_kept'] = remaining

# ============================================================
# 3. Remove dangling track stubs (track endpoints with no other
#    track or pad in radius)
# ============================================================
# Build map of pad positions
pad_positions = []
for fp in b.GetFootprints():
    for pad in fp.Pads():
        p = pad.GetPosition()
        pad_positions.append((mm(p.x), mm(p.y), pad.GetNetname(), set(pad.GetLayerSet().Seq())))

# Build map of track endpoints
def track_endpoints():
    eps = []
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_TRACK':
            s = t.GetStart(); e = t.GetEnd()
            eps.append((mm(s.x), mm(s.y), t, 'start'))
            eps.append((mm(e.x), mm(e.y), t, 'end'))
    return eps

def via_positions():
    return [(mm(v.GetPosition().x), mm(v.GetPosition().y), v.GetNetname())
            for v in b.GetTracks() if v.GetClass() == 'PCB_VIA']

TOL = 0.01  # 10 microns
def has_connection(x, y, net, this_track):
    # Connected to a pad of same net?
    for px, py, pn, layers in pad_positions:
        if abs(px-x) < TOL and abs(py-y) < TOL and pn == net:
            return True
    # Connected to a via of same net?
    for vx, vy, vn in via_positions():
        if abs(vx-x) < TOL and abs(vy-y) < TOL and vn == net:
            return True
    # Connected to another track of same net?
    for ex, ey, ot, side in track_endpoints():
        if ot is this_track: continue
        if abs(ex-x) < TOL and abs(ey-y) < TOL and ot.GetNetname() == net:
            return True
    return False

dangling = []
for t in list(b.GetTracks()):
    if t.GetClass() != 'PCB_TRACK':
        continue
    s = t.GetStart(); e = t.GetEnd()
    sx, sy = mm(s.x), mm(s.y)
    ex, ey = mm(e.x), mm(e.y)
    net = t.GetNetname()
    # If neither end is connected to anything → dangling stub
    if not has_connection(sx, sy, net, t) and not has_connection(ex, ey, net, t):
        dangling.append((t, sx, sy, ex, ey, net))

for t, sx, sy, ex, ey, net in dangling:
    print(f"Removing dangling track: ({sx:.2f},{sy:.2f})->({ex:.2f},{ey:.2f}) net={net!r}")
    b.Remove(t)
    stats['dangling_traces_removed'] += 1

# ============================================================
# 4. Re-fill zones and save
# ============================================================
filler = pcbnew.ZONE_FILLER(b)
zones = list(b.Zones())
filler.Fill(zones)

pcbnew.SaveBoard(BOARD, b)

print("\n=== Summary ===")
for k, v in stats.items():
    print(f"  {k}: {v}")
print(f"  Total drawings remaining: {len(list(b.GetDrawings()))}")
print(f"  Total tracks remaining:   {sum(1 for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK')}")
print(f"  Total vias remaining:     {sum(1 for t in b.GetTracks() if t.GetClass() == 'PCB_VIA')}")
