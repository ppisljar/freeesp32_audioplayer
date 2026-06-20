# esp32audio — PCB layout plan

Mixed-signal board with a switching boost converter and a Class-D amp.
The biggest layout risks are switching-noise coupling into the analog
audio path and inadequate return current management. Plan below is
optimised for that.

---

## 1. Board outline and stackup

| Topic | Decision |
|---|---|
| Outline target | **~42 x 32 mm** (≈ 1350 mm²), rounded 1 mm corners. Stretch goal 40 x 30. Hard ceiling 45 x 35. |
| Layer count | **2-layer**, **components on BOTH sides** to hit the size target |
| Copper weight | 1 oz (35 µm) standard |
| Substrate | FR-4, 1.6 mm |
| Top side (component-heavy) | XIAO, all 4 ICs, all connectors, the three electrolytic caps (C11, C13, C14), L1, D1 |
| Bottom side (small SMD only) | All 0603 decoupling caps, all 0603/0805 ceramics that fit, all 0603 resistors, FB divider, VOLUME divider, SE/BTL divider, FB-loop resistors |
| Stackup notes | Still 2-layer, but bottom is no longer a pure ground pour — it carries small SMDs in patches between the ground pour. Discipline: every bottom-side passive sits on a copper island connected to its corresponding top-side pin by a single via per pad. The pour fills around them. |
| Fab assumption | JLCPCB design rules (6/6 mil trace/space, 8 mil min annular, 0.3 mm min hole) |
| Assembly assumption | JLCPCB SMT both sides (extra cost vs. one side, but worth it for the area savings). Hand-solder fallback OK — all bottom parts are passives. |

Size-vs-quality reasoning: a 2-layer board with components on both
sides preserves the single-ground-pour discipline (§4) as long as
bottom-side passive islands are small and the pour stitches around
them. The audio path stays on the top layer end-to-end. The boost
island stays on the top layer end-to-end. We only lose pour
continuity in patches under decoupling caps — those patches are
< 5 mm wide and shielded by the IC body above, so they do not
disrupt audio return paths.

Switching node area, audio bandwidth, and ground-pour discipline
arguments still apply unchanged from the single-side plan.

---

## 2. Floor plan — XIAO on south edge, USB-C facing south

```
       ┌──────────────────────────────────────────────────┐
       │ [J5 BAT screw]    [J4 V+ JST]      [J1 3.5mm jack]│  NORTH edge
       │                                                  │
       │ [boost island:                     [J2 L spkr]    │  (connectors NORTH)
       │   U4,L1,C16,                                      │
       │   C17,D1]          [APA2068 U3]    [J3 R spkr]    │
       │                                                  │
       │ [J6 GPIO     [CS4344 U2]                          │
       │   breakout                                        │
       │   1x10       (audio chain in middle row)          │
       │   pin hdr]                                        │
       │                                                  │
       │      [────  XIAO ESP32-S3 (U1) ────]              │  SOUTH edge
       └────────────────↓ USB-C overhang ↓────────────────┘
                       (clear board edge south)
```

The XIAO is the size-driver. Pinning its USB-C to one edge defines
that edge; everything else fits around it.

**XIAO orientation (locked):**

- XIAO long axis runs **east-west** along the south edge of the
  board.
- USB-C connector points **south**, overhanging the board edge by
  ~1.5 mm so the USB-C plug shell clears any silkscreen / soldermask
  pile-up.
- Castellated mount: BAT+ SMD pad (bottom of XIAO module) sits on a
  matching copper land on the top layer of the board. Verify the
  XIAO_ESP32-S3_SMD footprint exposes this pad; if it does not, fix
  the .kicad_mod before placement.
- Board edge directly under the USB-C must be straight (no rounded
  corner) for ~6 mm centered on the connector — round corners
  reduce strain relief but a USB-C plug needs a flat seat.
- No tall components within 3 mm north of the XIAO body — the
  module's antenna sits on its top face and benefits from clear
  space.

Edge ownership (so cables don't fight):

| Edge | Connectors |
|---|---|
| North | J5 battery screw (left), J4 V+ JST (center), J1 headphone (right) |
| East | J2 L speaker, J3 R speaker (stacked vertically) |
| West | J6 GPIO breakout (1x10 SIL header, vertical) |
| South | XIAO U1, USB-C overhang only — no other connector |

Trade-off: J5 (battery screw) and J1 (headphone) on the same edge
means the user must route the battery wire away from the headphone
plug when the device is held normally. Acceptable — the alternative
(headphone on east, speakers on north) makes the east edge cluttered
with one BIG part and three small ones.

---

## 2a. Top vs bottom side assignment

Every part is placed on exactly one of the two sides. The board is
designed so that **everything on the bottom is a small passive** —
no ICs, no electrolytics, no connectors, no tall parts on the
bottom. This keeps assembly cheap and lets the board sit flat on a
case.

### TOP side (north view)

All ICs, the XIAO module, all connectors, all electrolytic /
through-hole / tall parts, the boost inductor and Schottky.

| Ref | Part | Reason for top |
|---|---|---|
| U1 | XIAO ESP32-S3 module | Castellated SMD; antenna up |
| U2 | CS4344 TSSOP-10 | Main IC |
| U3 | APA2068 SOP-16-EP | Main IC, EP needs top-side via field |
| U4 | TPS61023 SOT-563 | Main IC |
| L1 | 4.7 µH SMD inductor | Tall, magnetic — keep above plane |
| D1 | SS14 Schottky | Part of boost loop, keep with L1 |
| C11 | 100 µF electrolytic | Tall radial / SMD lead |
| C13 | 220 µF electrolytic (HP L) | Tall |
| C14 | 220 µF electrolytic (HP R) | Tall |
| J1–J6 | All connectors | Through-hole or large SMD |

### BOTTOM side (small SMD passives only, 0603/0805)

| Ref | Part | Goes near |
|---|---|---|
| C2 | 0.1 µF | Under CS4344, snug to pin 9 (VA) |
| C3 | 1 µF | Under CS4344, near pin 9 |
| C4 | 10 µF | Under CS4344, snug to pin 6 (FILT+) |
| C5 | 0.1 µF | Under CS4344, snug to pin 5 (VQ) |
| C6 | 3.3 µF | Under CS4344, near pin 5 |
| C7 | 3.3 µF poly | Mid-path CS4344↔APA2068 (could be on top if 0805 polarised cap is fine on top) |
| C8 | 3.3 µF poly | Mid-path CS4344↔APA2068 |
| C9 | 0.1 µF | Under APA2068, snug to pin 10 (VDD) |
| C10 | 0.1 µF | Under APA2068, snug to pin 15 (VDD) |
| C12 | 2.2 µF | Under APA2068, snug to pin 4 (BYPASS) |
| C15 | 0.1 µF | Under APA2068, snug to pin 7 (VOLUME) |
| C16 | 10 µF | Under U4, snug to pin 3 (VIN). Keep on TOP if it fits the boost-island rule (see §3.1) |
| C17 | 22 µF | Under U4, snug to pin 6 (VOUT). Same caveat |
| R1, R2 | 100k | Under APA2068, near pin 13 (SE/BTL) |
| R3, R4 | 1k | Under HP path, near J1 |
| R7, R8 | VOLUME divider | Under APA2068, near pin 7 |
| R9, R10 | FB divider | Under U4, near pin 1 (FB) |

**Caveat for C16, C17:** the boost-island rule (§3.1) requires the
input/output caps to close their current loop with U4 via the
shortest possible path. If putting C16/C17 on the bottom forces the
loop to detour through vias (adding inductance), keep them on the
top side flanking U4 instead. Decide during placement based on what
visually closes the loop tightest. The rest of the bottom-side
assignments are unconditional.

### Bottom-side ground-pour rule

The bottom layer is **mostly ground pour**, with small copper
patches for the bottom-side passive pads. Each bottom-side pad
connects to its top-side function via a single via per pad, placed
on the pad itself (via-in-pad, or tab-and-via if fab forbids
via-in-pad). The pour stitches around these patches.

Result: viewed from below, the board looks like solid copper with a
few tiny copper-and-pad islands. The audio return path under
top-side traces is preserved everywhere except those islands.

---

## 2b. Size optimization checklist

Run through this list during placement. Each item is worth 1–5 mm²
of saved area.

- [ ] **XIAO USB-C overhangs the south edge** (saves ~3 mm of board
      length compared to fully containing the connector)
- [ ] **All small passives on the bottom side** (saves the area they
      would otherwise occupy on top)
- [ ] **Decoupling caps directly under their IC pin** (zero
      additional top-side area)
- [ ] **No silkscreen reference designators on tight bottom-side
      patches** — they push pours apart; use a separate top-side ref
      legend or rely on the BOM for ref positions
- [ ] **JST PH-2 connectors share centerlines** where multiple sit
      on the same edge (J4 with J2/J3 styled the same, mounted
      flush)
- [ ] **J6 GPIO header oriented vertically along west edge** (uses
      the full west edge in one strip instead of a horizontal block
      that eats interior area)
- [ ] **APA2068 EP vias fit inside the package footprint** (no extra
      copper required beyond the EP outline)
- [ ] **Boost island fits in a 12 x 12 mm square**; if it spreads
      beyond that, re-pack
- [ ] **No "test point" pads on v1** — leave testpoints for v1.1 if
      we discover we need them. Each TP eats 2.5 mm²
- [ ] **Mounting holes deferred to v1.1** OR use M2 holes (≤ 4.5 mm
      keep-out each), placed only at two diagonal corners
- [ ] **Silkscreen kept to essentials**: pin 1 dots, polarities,
      J5/J6 labels, board name. No full pinouts on every connector.

### Realistic size budget

| Element | Area used |
|---|---|
| XIAO under-area (21 x 17.5) | 367 mm² |
| APA2068 + decoupling | ~50 mm² |
| CS4344 + decoupling | ~30 mm² |
| Boost island | ~120 mm² |
| C11, C13, C14 electrolytics | ~90 mm² |
| Connectors (J1–J6) | ~440 mm² |
| J6 header strip | ~75 mm² |
| Routing / clearance | ~200 mm² |
| **Total** | **~1372 mm²** ≈ 41 x 33 mm |

Target **42 x 32 mm** is achievable. Stretch goal **40 x 30 mm**
requires shrinking the headphone jack footprint or putting C13/C14
on the bottom (which conflicts with the electrolytic-on-top rule
unless we use ceramic instead).

### Size-saving substitutions (BOM changes, optional)

These are not in v1 BOM but listed so we can pull them in if we
overshoot the target:

| Original | Alternative | Area saved | Trade-off |
|---|---|---|---|
| C11 100 µF radial electrolytic (6.3 mm) | 22 µF ceramic 1210 X5R 10V | ~25 mm² | Lower bulk capacitance; APA2068 may dip on transients |
| C13, C14 220 µF radial electrolytic (6.3 mm) each | 100 µF ceramic 1210 X5R 10V | ~50 mm² total | High-pass corner shifts up; check ≥ 20 Hz still met with 1 kΩ R3/R4 |
| PJ-320A through-hole jack (13×14 mm) | SMD 3.5 mm jack (e.g. CUI SJ-43514) | ~80 mm² | More expensive part, harder to source |
| J5 5.08 mm screw terminal | 2.5 mm screw terminal or JST XH-2 | ~40 mm² | Smaller wire gauge |

---

## 3. Power partitioning — the single most important thing

Split the board mentally into three power domains:

1. **Battery / boost** (BAT+, BOOST_SW, BOOST_OUT, FB) — high di/dt, switching
2. **Clean +5V** (downstream of D1 / XIAO 5V pin) — feeds APA2068 VDD
3. **Clean +3V3** — feeds CS4344 VA only

These overlap on the same ground plane, but their **current loops
must not cross each other**. Plan:

### 3.1 Boost loop (highest priority)

The TPS61023 boost loop carries the largest di/dt on the board. Keep
this loop physically tiny:

```
        BAT+ ──► C16 ──► U4 pin 3 (VIN)
                          U4 pin 5 (SW) ──► L1 ──► U4 pin 6 (VOUT)
                                                    │
                                                    ├──► C17 ──► GND
                                                    └──► D1 anode → D1 cathode → +5V rail
        GND ◄────────────── U4 pin 4 (GND), C16, C17, D1 cathode return
```

**Rules:**
- C16, U4, L1, C17, D1 cluster into a < 10 x 10 mm island in the
  north-center of the board.
- L1 sits directly between U4 SW pin and U4 VOUT pin — keep the SW
  copper area small (it is the noisiest node on the board).
- C16 (input cap) ground pin and U4 GND pin **share a ground via**
  (or copper short) — do not let the input current loop close
  through the broader ground plane.
- C17 (output cap) ground pin and U4 GND pin same rule.
- D1 cathode → +5V rail leaves the boost island via a **single
  trace**, ≥ 0.6 mm wide, that crosses into the amp area.
- FB divider (R9, R10) is on a **quiet copper** — keep R9/R10 away
  from the SW node. The FB trace from U4 pin 1 to the R9/R10
  junction is < 5 mm. Run it on the side of U4 opposite to L1.
- No ground plane cut under the boost loop — solid pour underneath
  the entire island.

### 3.2 +5V rail to amp

C9, C10 (0.1 µF HF decoupling) sit **within 1 mm of APA2068 pin 10
and pin 15** respectively, with the shortest possible ground via.

C11 (100 µF bulk) within 5 mm of APA2068.

Trace from boost island to APA2068 VDD: ≥ 0.6 mm wide, kept on top
layer, routed around the audio signal area (do not run +5V across
the CS4344 analog outputs).

### 3.3 +3V3 rail

XIAO 3V3 pin → CS4344 VA pin (pin 9). Single trace, ≥ 0.3 mm,
< 25 mm long. C2 (0.1 µF) within 1 mm of CS4344 pin 9. C3 (1 µF)
within 5 mm. Do **not** share this trace with any other +3V3 sink
except J6 pin 9 (breakout).

---

## 4. Ground strategy

**Single solid ground pour on the bottom layer.** No analog/digital
split. The board is too small to gain anything from a split, and a
split done wrong is worse than no split at all.

Discipline instead of split:

- **APA2068 EP (thermal pad)** is the highest-current return on the
  board. Sew it to the ground plane with **at least 6 vias** (0.3 mm
  drill, 0.6 mm pad). The EP is also the thermal exit path — these
  vias matter for both thermal and electrical reasons.
- **CS4344 GND (pin 8)** has its own dedicated via to the bottom
  plane, placed within 1 mm of the pin.
- **C5, C6 (VQ caps), C4 (FILT+ cap), C2, C3 (VA caps)** — each
  ground pin gets its own via to the bottom plane, no daisy chains.
- **Boost island** ground vias as listed in §3.1.
- **Headphone jack sleeve (J1.S)** ground via at the connector body.
- **Speaker connector grounds**: J2 pin 1 and J3 pin 1 are NOT GND
  on this design (they are SPK_L_NEG and SPK_R_NEG — BTL output
  legs). Do not accidentally pour ground onto them.
- **J6 pin 8 (GND breakout)** — direct via to plane at the connector.

Return path check: trace the return current for the I²S signals from
CS4344 back to XIAO GND. It should follow the I²S trace on the
bottom plane uninterrupted. If you add any cuts to the bottom pour,
sanity-check return paths first.

---

## 5. Signal routing

### 5.1 I²S bus (XIAO D7–D10 → CS4344 pins 1–4)

Four signals: BCLK, LRCK, SDIN, MCLK. MCLK is the fastest
(typically 12.288 MHz for 48 kHz audio).

- Length match within ~5 mm (not critical at these speeds, but easy
  to do and good hygiene).
- Trace width 0.2 mm.
- **Do not route the I²S bus over the SW node or over L1.**
- Keep at least 1 mm separation from the boost island.
- Route on top layer, ground return on the bottom layer directly
  beneath.

### 5.2 Analog audio path — CS4344 AOUTL/R → APA2068 LIN-/RIN-

This is the most noise-sensitive path on the board. AOUTL/R are
single-ended ~1 Vpp signals.

- Total path length **< 25 mm** per channel.
- DC-block caps C7, C8 sit **between** CS4344 and APA2068 (mid-path).
- Trace width 0.25 mm.
- Route on top layer with solid ground beneath on bottom layer.
- **Keep at least 2 mm from any switching trace (SW node, I²S MCLK,
  USB DP/DM if exposed).**
- No vias on these traces — keep them on a single layer.

### 5.3 Speaker outputs (BTL, differential)

Pairs: (LOUT+, LOUT-) → J2, (ROUT+, ROUT-) → J3.

- Route as **tightly-coupled pairs** (0.25 mm trace, 0.25 mm gap)
  from APA2068 to the connector. This minimises radiated emissions
  from the PWM modulation.
- Trace width 0.4 mm minimum (current capacity for ~1 W into 4–8 Ω).
- Length: keep under 30 mm. Speaker leads outside the board do the
  EMI work, so the on-board portion should be short and parallel.
- If radiated emissions become a problem in testing, the standard
  fix is a ferrite bead + small cap LC filter at each output. Leave
  placeholder room near J2 and J3 for two 0603 footprints per
  channel (BOM-optional).

### 5.4 Headphone outputs

C13, C14 (220 µF AC-coupling) sit close to J1, **not** close to
APA2068 — the long trace is on the BTL side (which is differential
and tolerant), the short trace is on the single-ended HP side.

- C13: APA2068 LOUT- → C13 (+) → C13 (-) → J1.T (tip)
- C14: APA2068 ROUT- → C14 (+) → C14 (-) → J1.R (ring)
- R3, R4 (1 kΩ load reference) placed near J1.

### 5.5 SE/BTL detect

R1 (100k pull-up), R2 (100k series), J1.SN (sleeve switch).

- Place R1 near APA2068 pin 13.
- Place R2 mid-way between R1 and J1.
- Run R2-to-J1.SN as a quiet trace (no special width, no shielding,
  but keep it on the top layer).

### 5.6 VOLUME divider

R7 (100k), R8 (10k), C15 (0.1 µF) → APA2068 pin 7. Place all three
within 5 mm of APA2068 pin 7. The 0.45 V bias node is high-impedance
(~9 kΩ), so it is sensitive to capacitive coupling from PWM — keep
C15 close to the pin to shunt any pickup.

---

## 6. Trace width reference

| Net | Width | Reason |
|---|---|---|
| +5V (boost output → APA2068 VDD) | 0.6 mm | Peak current ~1 A |
| +5V (APA2068 → J6 pin 10 breakout) | 0.4 mm | Lower current |
| +3V3 | 0.3 mm | < 100 mA |
| BAT+ (J5 → C16 → U4) | 0.6 mm | Boost input current |
| BOOST_SW (U4 pin 5 → L1) | 0.5 mm copper region | Switching node, keep area small not skinny |
| BOOST_OUT (L1 → D1 → C17) | 0.6 mm | High di/dt |
| GND vias | 0.3 mm drill / 0.6 mm pad | Standard, low-impedance |
| Speaker outputs | 0.4 mm | Audio current |
| I²S, MCLK | 0.2 mm | Signal only |
| Audio AOUT L/R | 0.25 mm | Signal, low impedance |
| Headphone outputs (C13/C14 to jack) | 0.3 mm | < 100 mA |
| FB_NET | 0.2 mm | Sense, low impedance |
| SE_BTL, J1_SW | 0.2 mm | Logic |
| Everything else | 0.2 mm default | |

Track-to-track clearance: 0.2 mm (8 mil) minimum. Default 0.25 mm.

---

## 7. Component placement order

Place in this order so each step constrains the next:

1. **Set DRC and board outline** to the size target (42 x 32 mm
   working, 45 x 35 mm hard ceiling). Mounting holes deferred to
   v1.1.
2. **XIAO ESP32-S3 first**, locked to the south edge with USB-C
   overhanging south. This is the largest single part and dictates
   everything else.
3. **Edge connectors next** (J1, J2, J3, J4, J5, J6), placed on
   their assigned edges per §2.
4. **APA2068** — locked in the east-center area, with output pins
   (LOUT, ROUT, pins 9–16) facing east toward J2/J3.
5. **CS4344** — locked west of APA2068, I²S pins (1–4) facing west
   toward XIAO, AOUT pins (7, 10) facing east toward APA2068.
6. **TPS61023 + L1 + C16 + C17 + D1** — boost island in the
   north-west corner, between J5 and the audio chain.
7. **Flip board, place bottom-side decoupling caps directly under
   their IC pins** (C2, C3, C4, C5, C6 under CS4344; C9, C10, C12,
   C15 under APA2068). Goal: zero added top-side area for
   decoupling.
8. **Bottom-side dividers and small resistors** (R1, R2, R7, R8,
   R9, R10, R3, R4) placed near the pins they feed.
9. **Top-side audio coupling caps** (C7, C8) in their signal paths
   between CS4344 and APA2068. **Top-side electrolytics** (C11,
   C13, C14) near their ICs / connectors.
10. **Decide C16, C17 placement** (top vs bottom) by which option
    closes the boost loop tightest. Default top if in doubt.
11. **Routing pass**: power first, then audio (top side only), then
    I²S, then everything else.
12. **Pour ground**: bottom layer first as the primary plane, top
    layer as a secondary pour filling open areas. Stitch with
    ground vias every ~5 mm in quiet regions; denser around the
    boost island and APA2068 EP.

Do not move an IC after its decoupling caps are placed — re-do the
caps from scratch instead.

When a bottom-side cap conflicts with a routing channel needed on
the bottom, prefer to route on the top and keep the cap on the
bottom. Top-side routing tolerates jogs better than bottom-side
ground-pour does.

---

## 8. Polarity, orientation, silkscreen

Mark on silkscreen:

- **J5 battery**: clearly label `BAT+` and `BAT-` (this is a screw
  terminal a user wires by hand — getting it wrong destroys the
  board)
- **J4 V+ JST**: label `+5V` and `GND` with pin 1 indicator
- **J2, J3 speakers**: pin 1 = NEG, pin 2 = POS (mark + on pin 2 so
  speaker phase is obvious)
- **J6 breakout**: full pinout label `D0 D1 D2 D3 D4 D5 D6 GND 3V3 5V`
- **Electrolytic caps (C7, C8, C11, C13, C14)**: + side clearly marked
- **D1**: cathode bar visible
- **U1 XIAO**: pin 1 indicator + orientation arrow
- **U2 CS4344, U3 APA2068, U4 TPS61023**: pin 1 dots
- Board name, version, date in the corner: `esp32audio v1` /
  `2026-06` / `CS4344`

---

## 9. Thermal

APA2068 worst-case dissipation:
- 2 channels × 1 W output × (1 - efficiency). Class-D at 5 V into
  4 Ω is roughly 85% efficient → ~0.35 W total dissipation max.
- EP thermal pad with 6× 0.3 mm vias to a ≥ 100 mm² bottom-side
  copper pour handles this with margin.

TPS61023 worst-case dissipation:
- 1 A boost from 3.7 V to 5 V, ~92% efficiency → ~0.4 W internal.
- SOT-563 thermal pad on the package; rely on PCB copper around
  pins for heat spreading. Pour a ~50 mm² copper region around U4.

No active cooling needed.

---

## 10. EMC / EMI checklist before fab

- [ ] SW node copper area < 50 mm² (visually inspect the boost
      island)
- [ ] No analog audio traces cross the SW node or pass within 2 mm
      of L1
- [ ] Speaker output pairs routed as tight differential pairs
- [ ] Ground pour continuous under all signal traces — no slots,
      no large cuts
- [ ] C16/C17 ground vias share copper with U4 GND pin
- [ ] APA2068 EP has ≥ 6 ground vias
- [ ] +5V trace from boost to APA2068 does not weave through the
      audio area
- [ ] Boost feedback divider trace is on the side of U4 opposite
      to L1
- [ ] All decoupling caps within 1 mm of their IC power pin

---

## 11. DRC settings

Set in KiCad before routing:

| Constraint | Value |
|---|---|
| Minimum clearance | 0.2 mm |
| Minimum trace width | 0.15 mm |
| Default trace width | 0.25 mm |
| Minimum via diameter | 0.6 mm (pad) / 0.3 mm (drill) |
| Minimum annular ring | 0.1 mm |
| Minimum hole-to-hole | 0.5 mm |
| Edge clearance | 0.3 mm |

Net classes:

| Class | Width | Members |
|---|---|---|
| Power | 0.6 mm | +5V, BAT+, BOOST_OUT |
| Audio | 0.25 mm | AOUTL/R_RAW, AOUTL/R_AC, HP_L, HP_R |
| Speaker | 0.4 mm | SPK_L_NEG/POS, SPK_R_NEG/POS |
| I2S | 0.2 mm | I2S_BCLK, I2S_LRCK, I2S_DOUT, I2S_MCLK |
| Default | 0.25 mm | Everything else |

---

## 12. Pre-fab gates

Before sending gerbers:

1. **DRC clean** — zero errors, zero warnings (or each warning
   reviewed and justified)
2. **Visual ground-pour inspection** — pour continuous on bottom,
   no orphaned islands, all ground pins connected via thermal relief
   or solid copper
3. **Return path trace** — pick three signals (an I²S line, the
   audio AOUTL, the LOUT speaker), mentally trace return current,
   confirm uninterrupted ground beneath
4. **3D render check** — connectors at edges, USB-C clear, no
   collisions, polarised parts oriented correctly
5. **Footprint review** — every footprint matches the actual part
   (especially the custom ones: XIAO, APA2068 SOP-16-EP, TPS61023
   SOT-563). Cross-check pad sizes against datasheet recommended
   land patterns.
6. **BOM cross-check** — every reference in the schematic appears
   on the PCB and has a value, footprint, and (ideally) JLCPCB part
   number assigned.

---

## 13. Known risks / things to watch

| Risk | Mitigation |
|---|---|
| XIAO BAT+ pad orientation in footprint may be wrong | Verify against XIAO datasheet before placement; if wrong, fix the .kicad_mod |
| APA2068 cached symbol mismatch warning in ERC | Open in KiCad UI, Tools → Update Symbols from Library, re-save |
| TPS61023 symbol pin types are bidirectional, not power_in/out | Cosmetic ERC warnings; functional. Optionally tighten pin types in New_Library |
| Audio coupling via L1 fringing field into AOUTL/R traces | L1 is shielded inductor; place ≥ 5 mm from CS4344 outputs |
| Speaker cable radiation under FCC class B | Add LC output filter footprints (DNP by default), populate if needed |
| Hand-routing speaker BTL pairs may not stay tightly coupled | Use route_differential_pair tool in KiCad MCP for J2/J3 pairs |
| Ground pour leaving voids near dense BGA-like via clusters | Inspect after pour fill; manually patch with copper if needed |
| Bottom-side decoupling cap pad islands break the ground pour and degrade return paths | Keep each bottom-side pad cluster < 5 mm wide. Verify pour fills around them (no isolated copper pieces). For any spot where pour fragmentation looks bad, move that cap back to the top. |
| Bottom-side ground pour fragmented under the audio path | After routing, manually scan the bottom layer under each top-side audio trace (AOUTL/R_AC, HP_L/R). Continuous copper required. |
| XIAO USB-C plug shell hitting nearby components | 3D-render and verify ≥ 1.5 mm clearance around the USB-C body on the south edge before fab |
| Double-sided assembly cost increase (JLCPCB) | Confirmed acceptable for v1 prototype quantity. If scaling, revisit single-side layout. |
| Headphone jack J1 too close to battery screw J5 on the north edge | Maintain ≥ 10 mm horizontal gap between the two; user routes wires opposite directions |
| Audio coupling caps C7/C8 forced to the bottom (polarised SMD electrolytics) | If using polarised SMD parts, the bottom-side placement is fine. If we substitute non-polar film caps that are too tall for the bottom, move to top and accept ~5 mm² area cost. |
