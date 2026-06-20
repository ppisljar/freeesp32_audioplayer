#!/usr/bin/env python3
"""
Fix the 9 stale pad-net assignments on U1 and J6, plus rename J1 footprint
pads R1->R and R2->SN so they match the AudioJack3_Switch symbol.

Non-destructive: keeps all routing, footprints, placement.
"""
import pcbnew

BOARD = '/Users/ppisljar/Sonatino/kicad_project/esp32audio/esp32audio.kicad_pcb'
b = pcbnew.LoadBoard(BOARD)

def get_or_add_net(name):
    n = b.FindNet(name)
    if n is None:
        ni = pcbnew.NETINFO_ITEM(b, name)
        b.Add(ni)
        n = b.FindNet(name)
    return n

# Stale pad-net reassignments (per cross-check vs schematic)
PAD_NETS = [
    # XIAO SD bus
    ('U1', '2', 'SD_CS'),
    ('U1', '3', 'SD_SCK'),
    ('U1', '4', 'SD_MOSI'),
    ('U1', '5', 'SD_MISO'),
    # J6 GPIO breakout new pinout
    ('J6', '2', 'D5_NET'),
    ('J6', '3', 'D6_NET'),
    ('J6', '4', 'GND'),
    ('J6', '5', '+3V3'),
    ('J6', '6', '+5V'),
]

# J1 pad RENAMES (footprint has R1/R2 but symbol uses R/SN)
PAD_RENAMES = [
    ('J1', 'R1', 'R',  'HP_R'),
    ('J1', 'R2', 'SN', 'J1_SW'),
]

print("=== Reassigning stale pad nets ===")
fixed = 0
for ref, pin, net_name in PAD_NETS:
    fp = b.FindFootprintByReference(ref)
    if fp is None:
        print(f"  WARN: {ref} not found")
        continue
    target_net = get_or_add_net(net_name)
    for pad in fp.Pads():
        if pad.GetNumber() == pin:
            old = pad.GetNetname()
            pad.SetNet(target_net)
            print(f"  {ref}.{pin}: {old!r} -> {net_name!r}")
            fixed += 1
            break

print(f"\n=== Renaming J1 pads to match symbol ===")
renamed = 0
for ref, old_num, new_num, net_name in PAD_RENAMES:
    fp = b.FindFootprintByReference(ref)
    if fp is None: continue
    target_net = get_or_add_net(net_name)
    for pad in fp.Pads():
        if pad.GetNumber() == old_num:
            pad.SetNumber(new_num)
            pad.SetNet(target_net)
            print(f"  {ref}: pad {old_num} -> {new_num} (net {net_name})")
            renamed += 1
            break

pcbnew.SaveBoard(BOARD, b)
print(f"\nFixed {fixed} pad-net assignments, renamed {renamed} J1 pads. Saved.")
