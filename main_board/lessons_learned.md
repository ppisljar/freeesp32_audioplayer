# esp32audio v1 — lessons learned

What went well, what went wrong, what to do differently next time.
Captured during the v1 build so v2 (and any other KiCad-via-MCP project)
benefits.

---

## 1. Schematic phase

### What worked

- **Build plan in markdown before touching KiCad.** The 300-line plan
  (`project_plan.md`) made the schematic step almost mechanical — every
  decision (DAC choice, mount style, dividers, fb resistors, jack pinout)
  was already locked. Net list, BOM, and pin tables in the plan mapped
  1:1 to MCP calls.
- **Custom symbols already existed** (XIAO, APA2068, TPS61023 in
  `New_Library`). Saved an hour vs. authoring them.
- **`snap_to_grid` after placement.** Off-grid components produce
  unconnected-pin ERC noise. Running `snap_to_grid` with all elements
  before wiring fixed a lot of issues in one call.

### What didn't

- **PWR_FLAG on a rail that already has `power_out`** triggers an ERC
  error (two power-out pins shorted). XIAO 3V3 pin is `power_out`, so
  adding a PWR_FLAG on +3V3 was wrong. Only add PWR_FLAG on nets whose
  source is a `power_in` pin (like XIAO 5V / BAT+).
- **Hidden EP pin on APA2068**: pin 17 (EP) is hidden in the symbol.
  `batch_connect` silently skipped it. The schematic appeared clean
  but the EP wasn't grounded at the PCB level — fixed only during PCB
  cleanup by setting the EP pad's net directly via pcbnew.
- **Symbol pin names vs footprint pad names mismatch**:
  `AudioJack3_Switch` symbol uses pins `T/R/S/TN/RN/SN`. No stock
  KiCad footprint has matching pad names — they use `T/S/R1/R2/R1N`
  etc. The schematic looks right, the PCB connects via different pad
  names. **Always verify symbol pin names == footprint pad names
  before sync.** Use `list_symbol_pins` and `get_footprint_info` to
  cross-check.

### Rule for v2

> Before sync_schematic_to_board, for every component verify that
> `symbol.pin_name` set == `footprint.pad_name` set. Mismatch =
> unconnected pads.

---

## 2. PCB placement phase

### What worked

- **`check_courtyard_overlaps` with `include_boundary=True`** caught
  90% of placement problems early. Run it after every batch of moves.
- **Two-sided component placement** worked — XIAO on top, ICs on
  bottom (under XIAO), small passives on bottom. The 50×42mm board
  fits 36 footprints comfortably.
- **`add_board_outline` with rounded_rectangle** is the right
  primitive (KiCad UI's outline tool is finicky).

### What didn't

- **`add_board_outline` called multiple times stacks outlines** —
  doesn't replace. Caused `invalid_outline ×5` + `copper_edge_clearance
  ×77` DRC violations. Three boards (42×32 + 50×42 + 50×42) all on
  Edge.Cuts at once.

  **Fix in v2**: Before changing board outline, programmatically
  remove all existing Edge.Cuts drawings first (no MCP tool for this
  — needs pcbnew script).

- **Courtyards include silkscreen/USB-C overhang**. XIAO bbox is
  20.9×26.1mm but the body is only 21×17.5mm. The `overlap` check
  flags things that are physically fine (top vs bottom, courtyard
  fluff). **Treat overlaps as a starting point for visual check, not
  a strict failure list.**

- **Auto-save races between MCP and pcbnew scripts**: writing the
  board via Python while MCP has it open → "auto-save refused, disk
  changed externally". Always reload via `open_project` after a
  Python script writes the board.

### Rule for v2

> When working with custom Python scripts that write `.kicad_pcb`,
> always:
> 1. Save / close the board in MCP (or accept the auto-save warning)
> 2. Run the Python script
> 3. `open_project` to reload the MCP's view of the board
> 4. Then continue MCP edits

---

## 3. Routing phase

### What worked

- **Manual `route_pad_to_pad` for the critical 10–15 nets**
  (boost loop, audio chain, GND vias for EP). Fast, precise, no
  surprises.
- **Freerouting via `java -jar freerouting.jar -de in.dsn -do out.ses`**
  routed 47/57 nets in 1 minute and eliminated all 35 tracks-crossing
  errors. The MCP's `import_ses` then loaded results cleanly.
- **`add_gnd_stitching_vias` strategy combo** (`grid + around_refs +
  in_zones`) placed 92 stitching vias with collision checking.

### What didn't

- **Manual routing AFTER Freerouting created crossings** that
  Freerouting had avoided. Order matters: run Freerouting LAST, then
  only touch up if needed. Or: rip up everything, re-run Freerouting
  with the new constraints.

- **`route_pad_to_pad` doesn't avoid existing traces**. It draws a
  fresh Manhattan path. If the path crosses other traces, you get
  shorts. There's no "interactive router" equivalent in the MCP.

- **`add_gnd_stitching_vias` with 4mm spacing in a tiny board** added
  92 vias and made the bottom pour MORE fragmented (16 islands vs the
  original 10). The pour breaks around each via cluster. **Smaller
  boards need fewer stitches, not more.** For a 50×42mm board, 20–40
  stitching vias is plenty; 92 is over-engineering.

- **Edge-clearance violations from stitching vias near board edge**.
  The tool's `edgeMargin=0.5mm` parameter wasn't tight enough vs the
  DRC's 0.5mm edge clearance — vias at 0.65mm from edge with 0.3mm
  radius leave 0.35mm to edge, below 0.5mm. **Set edgeMargin to >=
  required_clearance + via_radius** (so 0.5 + 0.3 = 0.8mm minimum).

### Rule for v2

> Routing order:
> 1. Set design rules and net classes first (NOT after routing)
> 2. Run Freerouting once on full unrouted board
> 3. Manually patch unrouted nets if any
> 4. Add stitching vias LAST, in small dose (20–30 for board < 2500 mm²)
> 5. Re-run DRC; only then iterate

---

## 4. MCP tooling

### Strengths

- Add primitives (place, route, copper pour, via): excellent
- Inspection (component list, pads, overlaps, DRC): excellent
- Analyzer integration (schematic, PCB, EMC, cross): excellent —
  catches issues no naive DRC pass would
- Batch operations (`batch_add_components`, `batch_connect`): saved
  hundreds of single-shot calls

### Gaps that bit us

| Need | Workaround |
|---|---|
| Delete graphic items (Edge.Cuts lines) | pcbnew Python script |
| Delete vias by criteria (edge dist, dup) | pcbnew Python script |
| Set pad net assignment (e.g. EP to GND) | pcbnew Python script |
| Move silk text (refs to F.Fab to declutter) | pcbnew Python script |
| Push-and-shove router | Use Freerouting via Java |
| Connection-aware re-route | Rip up + Freerouting |
| Add net classes | Edit `.kicad_pro` directly |

**Pattern**: when MCP doesn't expose a primitive, **pcbnew (KiCad's
Python module) does**. The bundled Python interpreter at
`/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3`
has `pcbnew` import-able with full SWIG bindings.

### Rule for v2

> When MCP runs out of primitives, write a 30-line pcbnew Python
> script. Don't try to brute-force it via 50 MCP calls.

---

## 5. Freerouting setup

### Install in 3 minutes

```bash
brew install openjdk
mkdir -p ~/.kicad-mcp
curl -L -o ~/.kicad-mcp/freerouting.jar \
  "https://github.com/freerouting/freerouting/releases/download/v2.2.4/freerouting-2.2.4.jar"
```

### Run

```bash
cd <project>
/opt/homebrew/opt/openjdk/bin/java -jar ~/.kicad-mcp/freerouting.jar \
    -de board.dsn -do board.ses -mp 200 -us global
```

`-mp N` = max passes (200 = thorough), `-us global` = global optimisation.

### Gotchas

- The MCP `check_freerouting` tool looks at `/usr/bin/java` only.
  Without `sudo ln -sfn` to symlink the JDK into
  `/Library/Java/JavaVirtualMachines/`, the MCP autoroute won't see
  Java. Workaround: run Freerouting from Python with the explicit
  brewed Java path.
- Freerouting needs the board fully exported (no in-progress traces)
  for best results. Always rip-up first if you re-run.

---

## 6. Design choices we'd revisit

| Decision | What we'd change |
|---|---|
| 0603 / 0805 passives | Consider 0402 for digital decoupling — saves ~25–30 mm² total |
| PJ-320 audio jack symbol | Use a symbol whose pin names match a stock footprint (or author a custom symbol/footprint pair upfront) |
| 92 GND stitching vias | 25–35 is plenty for a 50×42mm board; more fragments the pour |
| 0.5mm edge clearance | Keep. PCBWay's 0.3mm min is too aggressive for hand-assembly boards |
| 50×42mm board | Could shrink to ~45×38mm with 0402 passives, but at the cost of routing density and hand assembly |
| Manual routing after Freerouting | Don't. Always rip-up first if iterating |

---

## 7. Workflow that worked

For v2 (or any new MCP-based KiCad project):

```
1. PLAN
   - Write project_plan.md with all design decisions, BOM, net list
   - Write pcb_plan.md with floor plan, top/bottom assignments, DRC

2. SCHEMATIC
   - kicad_sch_edit skill
   - Verify all symbol pin names against footprint pad names BEFORE sync
   - Skip PWR_FLAG on nets that have a power_out pin
   - Annotate, snap to grid, run ERC

3. PCB SETUP
   - Set design rules ONCE (for target fab, e.g. PCBWay)
   - Write .kicad_dru with net-class rules
   - sync_schematic_to_board
   - Place components per pcb_plan.md
   - Verify with check_courtyard_overlaps

4. ROUTE
   - Export DSN -> Freerouting -> import SES
   - Manually patch any unrouted nets
   - Add 20-30 GND stitching vias (NOT 100)
   - Refill zones, run DRC

5. CLEANUP (pcbnew Python script)
   - Set EP pads to GND
   - Move ref text to F.Fab, hide values
   - Remove edge-clearance vias

6. VALIDATE
   - kicad-happy skill: schematic + pcb + cross + EMC
   - Fix HIGH findings (real blockers, not heuristic noise)
   - Document false positives (VM-001 5V/3.3V on I2S etc.)

7. SHIP
   - Export gerbers + drill + CPL + BOM
   - Order from PCBWay (or fab of choice)
```

Total expected hours: ~6–8 for a board this size if you don't have
to iterate the schematic.
