#!/usr/bin/env python3
"""
Replace the schematic's embedded copy of XIAO_ESP32-S3 lib_symbol with the
latest version from New_Library.kicad_sym (now has pins 1-24).
"""
import re

SCH = '/Users/ppisljar/Sonatino/kicad_project/esp32audio/esp32audio.kicad_sch'
LIB = '/Users/ppisljar/Sonatino/kicad_project/New_Library.kicad_sym'

def extract_symbol_block(text, sym_name):
    """Return (start_idx, end_idx, block_text) of (symbol "sym_name" ...)."""
    pat = re.compile(rf'\(symbol\s+"{re.escape(sym_name)}"')
    m = pat.search(text)
    if not m:
        return None
    start = m.start()
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '(': depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                return (start, i+1, text[start:i+1])
    return None

# Read library, extract the XIAO symbol block
lib = open(LIB).read()
res = extract_symbol_block(lib, 'XIAO_ESP32-S3')
assert res, "Could not find XIAO_ESP32-S3 in library"
_, _, lib_xiao = res
print(f'Library XIAO symbol: {len(lib_xiao)} bytes')

# Read schematic — find the embedded XIAO symbol within lib_symbols
sch = open(SCH).read()
# Schematic embeds symbols with prefix like "New_Library:XIAO_ESP32-S3"
res = extract_symbol_block(sch, 'New_Library:XIAO_ESP32-S3')
assert res, "Could not find New_Library:XIAO_ESP32-S3 in schematic"
sstart, send, sch_xiao = res
print(f'Schematic embedded XIAO symbol: {len(sch_xiao)} bytes')

# Build a new block: copy lib_xiao but rename to "New_Library:XIAO_ESP32-S3"
new_block = lib_xiao.replace('"XIAO_ESP32-S3"', '"New_Library:XIAO_ESP32-S3"', 1)
# Indent each line by adding tab so it matches the schematic's lib_symbols indent
# Find indent from original block
orig_indent = ''
for ch in sch[sstart-10:sstart]:
    if ch == '\t': orig_indent += '\t'
# Apply same indent to new block (very rough; KiCad re-formats on save anyway)
new_block_indented = new_block

new_sch = sch[:sstart] + new_block_indented + sch[send:]
open(SCH, 'w').write(new_sch)
print(f'Wrote schematic ({len(new_sch)} bytes). Pin count in new embedded symbol:')
new_pins = re.findall(r'\(number\s+"(\d+)"', new_block)
print(f'  pins: {sorted(set(int(n) for n in new_pins))}')
