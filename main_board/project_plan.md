# esp32audio — CS4344 version, build plan

**Goal:** Small audio board. XIAO ESP32-S3 streams I²S → CS4344 stereo DAC → APA2068 stereo class-D amp.

**Outputs:**
- 2× speaker connectors (stereo, JST PH-2, BTL drive)
- 1× 3.5 mm stereo headphone jack with auto-detect (APA2068 SE/BTL mode toggle)

**Inputs:**
- USB-C on the XIAO (development)
- External `V+/GND` JST PH-2 (5 V wall adapter)
- Li-ion battery on screw terminal → XIAO BAT+ → TPS61023 boost → 5 V rail

**v1 scope:** CS4344 only. PCM5101A deferred to a separate v2 project.

**v1.1 additions** (this revision):
- **microSD card** on SPI (CS, MOSI, MISO, SCK). 4 pins from XIAO D1–D4. No CD switch (firmware polls).
- **0402 passives** for all standard R/C (replacing 0603/0805 where possible). Saves ~40 mm² board area.
- J6 breakout reduced from D0–D6 to D0, D5, D6 (D1–D4 reassigned to SD card).

---

## Final design decisions (all locked in)

| Topic | Decision | Notes |
|---|---|---|
| DAC | CS4344 only (v1) | PCM5101A deferred |
| Amp | APA2068 in BTL stereo, SE switch via headphone jack | |
| MCU module | Seeed XIAO ESP32-S3, **SMD castellated mount** | BAT+ pad needs SMD electrical contact |
| Speakers | Stereo, 2× JST PH-2 (J2 = L, J3 = R) | |
| Headphone | 3.5 mm TRS w/ switched detect (J1) | e.g. PJ-320A |
| External 5 V in | JST PH-2 (J4), parallel with USB VBUS | "USB ⊕ V+, one at a time" |
| Battery | 2-pos screw terminal (J5) → XIAO BAT+ | XIAO's onboard charger handles management |
| Battery → 5 V | TPS61023 boost (U4), BAT+ → Vout via D1 Schottky to 5 V rail | enables headphone audio on battery |
| GPIO breakout | J6 = **1×10 SIL** pin header (D0–D6, GND, +3V3, +5V) | |
| Diode-OR USB/V+ | No (mutually exclusive) | USB + battery is the only "both-at-once" case, handled by D1 |
| MUTE / SHUTDOWN | Tied directly to +5V (always enabled) | Mute = stop I²S in firmware |
| VOLUME | Fixed +14 dB via R7=100k / R8=10k divider on VOLUME pin | Volume controlled in software (DAC level) |
| SE/BTL | 100 k pull-up + 100 k series to jack-switch contact → GND | Verified vs datasheet VIH=4V, VIL=3V |
| CS4344 VA | 3.3 V from XIAO 3V3 pin | XIAO LDO is clean enough for ~100 dB SNR |

---

## Block diagram

```
                                         ┌──────────────────────────────────────┐
   USB-C  ──► XIAO 5V pin ──┬─────────────┤                                      │
                            │             │     +5V rail                         │
                            │             │   ┌──────────────► APA2068 VDD (10,15)
                            │             │   │
   J4 V+ JST ───────────────┘             │   ├─── decoupling C9, C10, C11
                                          │   ├─── R1 → SE/BTL
                                          │   ├─── R7 → VOLUME divider
                                          │   ├─── APA2068 ~MUTE, ~SHUTDOWN tied here
                                          │   │
   J5 BAT screw ── BAT+ ──► XIAO BAT+ ──► U4 TPS61023 ──L1──► VOUT ──► D1 Schottky
                                          (boost VIN)            (SS14)

                                          XIAO 3V3 pin ──► +3V3 rail ──► CS4344 VA (9)
                                                                          + C2, C3 decoupling

                                          XIAO D7  ──► CS4344 SCLK (2)   I2S_BCLK
                                          XIAO D8  ──► CS4344 LRCK (3)   I2S_LRCK
                                          XIAO D9  ──► CS4344 SDIN (1)   I2S_DOUT
                                          XIAO D10 ──► CS4344 MCLK (4)   I2S_MCLK

                                          XIAO D0..D6 → J6 breakout (+3V3, +5V, GND also on J6)

   CS4344 AOUTL (7) ── C7 3.3µ → APA2068 LIN- (6)
   CS4344 AOUTR (10)── C8 3.3µ → APA2068 RIN- (3)
   CS4344 VQ (5)  ────── C5 0.1µ, C6 3.3µ → GND
   CS4344 FILT+ (6) ──── C4 10µ → GND

   APA2068 LOUT- (9)  ──┬─► J2 (L spkr) pin 1
                        └─ C13 220µ ─► J1 Tip (HP L) ── R3 1k → GND
   APA2068 LOUT+ (11) ──► J2 (L spkr) pin 2
   APA2068 ROUT- (16) ──┬─► J3 (R spkr) pin 1
                        └─ C14 220µ ─► J1 Ring (HP R) ── R4 1k → GND
   APA2068 ROUT+ (14) ──► J3 (R spkr) pin 2

   APA2068 SE/BTL (13) ── R1 100k ▲ +5V
                       ── R2 100k ── J1 SW → GND
   APA2068 BYPASS (4)  ── C12 2.2µ → GND
   APA2068 VOLUME (7)  ── R7 100k ▲ +5V, R8 10k ▼ GND, + C15 0.1µ → GND   (0.45 V → +14 dB)
   APA2068 VOLMAX (8)  ── GND
   APA2068 ~MUTE (1)   ── +5V
   APA2068 ~SHUTDOWN(2)── +5V
   APA2068 EP (17)     ── GND
```

---

## Power tree

| Net | Sourced by | Sinks |
|---|---|---|
| `+5V` | XIAO 5V pin (USB VBUS) **OR** J4 V+ JST **OR** TPS61023 VOUT via D1 (when on battery) | APA2068 VDD (10, 15), APA2068 ~MUTE (1), APA2068 ~SHUTDOWN (2), R1 (SE/BTL pull-up), R7 (VOLUME top), C9, C10, C11, C17 (boost output cap), J6 pin 10 |
| `+3V3` | XIAO 3V3 pin (XIAO internal LDO) | CS4344 VA (9), C2, C3, J6 pin 9 |
| `BAT+` | J5 screw terminal pin 1 ↔ XIAO BAT+ | TPS61023 VIN, C16 (boost input cap) |
| `GND` | XIAO GND pin | Every return |

Notes:
- USB-C → XIAO 5V pin directly drives the +5V rail (no Schottky drop) → APA2068 sees full 5 V on USB.
- On battery only (USB unplugged): TPS61023 boost output goes through D1 Schottky (≈0.3 V drop) → +5V rail sits at ≈4.7 V → APA2068 still in spec (min 4.5 V).
- USB plugged in + battery present: USB holds +5V rail at 5 V; boost output sees its cathode at 5 V → reverse-biases D1 → boost backs off to light-load mode (~30 µA from battery). XIAO charger tops up the battery.

---

## XIAO ESP32-S3 (U?) pin assignment

(Reference designator will be assigned during schematic capture.)

| Pin | Name | Function | Net |
|----:|------|----------|-----|
|  1  | D0/GPIO1   | breakout | `D0` → J6 pin 1 |
|  2  | D1/GPIO2   | Free breakout GPIO | `D1_NET` → J6 pin 2 |
|  18 | GPIO42 (bottom pad) | SD card CS | `SD_CS` → J7 (microSD), R11 pull-up |
|  3  | D2/GPIO3   | SD card SCK | `SD_SCK` → J7 (microSD) |
|  4  | D3/GPIO4   | SD card MOSI | `SD_MOSI` → J7 (microSD) |
|  5  | D4/GPIO5   | SD card MISO | `SD_MISO` → J7 (microSD) |
|  6  | D5/GPIO6   | breakout (SCL-capable) | `D5` → J6 pin 2 |
|  7  | D6/GPIO43  | breakout (UART0 TX)    | `D6` → J6 pin 3 |
|  8  | D7/GPIO44  | I²S BCLK   | `I2S_BCLK` → CS4344 pin 2 |
|  9  | D8/GPIO7   | I²S LRCK   | `I2S_LRCK` → CS4344 pin 3 |
| 10  | D9/GPIO8   | I²S DOUT   | `I2S_DOUT` → CS4344 pin 1 |
| 11  | D10/GPIO9  | I²S MCLK   | `I2S_MCLK` → CS4344 pin 4 |
| 12  | 3V3        | power out  | `+3V3` |
| 13  | GND        | gnd return | `GND` |
| 14  | 5V         | USB VBUS   | `+5V` |
| 15  | BAT+       | Li-ion I/O | `BAT+` |

---

## CS4344 (U2) — 10-pin MSOP, VA = 3.3 V

| # | Name | Net | Component |
|--:|------|-----|-----------|
|  1 | SDIN     | `I2S_DOUT` |  |
|  2 | DEM/SCLK | `I2S_BCLK` |  |
|  3 | LRCK     | `I2S_LRCK` |  |
|  4 | MCLK     | `I2S_MCLK` |  |
|  5 | VQ       | `VQ_NET`   | C5 0.1 µF + C6 3.3 µF → GND |
|  6 | FILT+    | `FILT_NET` | C4 10 µF → GND |
|  7 | AOUTL    | `AOUTL_AC` | + side of C7 3.3 µF → APA2068 pin 6 |
|  8 | GND      | `GND`      |  |
|  9 | VA       | `+3V3`     | C2 0.1 µF + C3 1 µF → GND |
| 10 | AOUTR    | `AOUTR_AC` | + side of C8 3.3 µF → APA2068 pin 3 |

DC-block cap polarity: `+` on CS4344 side.

---

## APA2068 (U3) — SOP-16-P with EP

| # | Name | Net | Component |
|--:|------|-----|-----------|
|  1 | ~MUTE      | `+5V`       | tied directly (always on) |
|  2 | ~SHUTDOWN  | `+5V`       | tied directly (always on) |
|  3 | RIN-       | `AOUTR_AC`  | from CS4344 via C8 |
|  4 | BYPASS     | `BYPASS_C`  | C12 2.2 µF → GND |
|  5 | GND        | `GND`       |  |
|  6 | LIN-       | `AOUTL_AC`  | from CS4344 via C7 |
|  7 | VOLUME     | `VOLUME_C`  | R7 100k → +5V; R8 10k → GND; C15 0.1 µF → GND |
|  8 | VOLMAX     | `GND`       | clamp disabled |
|  9 | LOUT-      | `SPK_L_NEG` | J2 pin 1; C13 (+) 220 µF → J1 Tip |
| 10 | VDD        | `+5V`       | C9 0.1 µF + C11 100 µF → GND |
| 11 | LOUT+      | `SPK_L_POS` | J2 pin 2 |
| 12 | GND        | `GND`       |  |
| 13 | SE/~BTL    | `SE_BTL`    | R1 100k → +5V; R2 100k → J1 SW |
| 14 | ROUT+      | `SPK_R_POS` | J3 pin 2 |
| 15 | VDD        | `+5V`       | C10 0.1 µF → GND |
| 16 | ROUT-      | `SPK_R_NEG` | J3 pin 1; C14 (+) 220 µF → J1 Ring |
| 17 | EP         | `GND`       | thermal pad + 6 vias |

---

## TPS61023 boost block (U4)

| # | Name | Net | Component |
|--:|------|-----|-----------|
|  1 | FB     | `FB_NET`     | R9 (top) to VOUT, R10 (bottom) to GND  → sets 5 V output (see below) |
|  2 | EN     | `BAT+`       | tied to VIN → boost always on |
|  3 | VIN    | `BAT+`       | C16 10 µF → GND |
|  4 | GND    | `GND`        |  |
|  5 | SW     | `BOOST_SW`   | L1 (4.7 µH) between SW and VOUT |
|  6 | VOUT   | `BOOST_OUT`  | C17 22 µF → GND; through D1 (SS14) → `+5V` rail |

**Feedback divider:** TPS61023 VFB = 0.6 V. For 5 V output: VOUT/VFB = 8.33 → R9/R10 = 7.33. Standard values: **R9 = 365 kΩ (or 360 kΩ), R10 = 49.9 kΩ**, giving 5.0 V; or R9 = 100 kΩ, R10 = 13.7 kΩ.

**Schottky D1:** SS14 (1 A, 40 V) or PMEG2010AEH. Drop ~0.3 V at 1 A. Cathode = +5V rail, anode = BOOST_OUT.

---

## Headphone jack J1

3.5 mm stereo TRS jack with switched detect contact (PJ-320A or equivalent).

| Contact | Net | Notes |
|---|---|---|
| Tip (L)        | `HP_L`       | + of C13 → APA2068 LOUT-; R3 1 kΩ → GND |
| Ring (R)       | `HP_R`       | + of C14 → APA2068 ROUT-; R4 1 kΩ → GND |
| Sleeve         | `GND`        |  |
| Switch         | `J1_SW`      | one end → GND; other → R2 → SE_BTL |

---

## Speaker connectors

| Connector | Pin 1 | Pin 2 |
|---|---|---|
| **J2** L speaker — JST PH-2 | `SPK_L_NEG` (APA2068 LOUT-) | `SPK_L_POS` (APA2068 LOUT+) |
| **J3** R speaker — JST PH-2 | `SPK_R_NEG` (APA2068 ROUT-) | `SPK_R_POS` (APA2068 ROUT+) |

---

## Power input + breakout

| Connector | Style | Pinout |
|---|---|---|
| **J4** V+ external | JST PH-2 | 1=`+5V`, 2=`GND` |
| **J5** Battery | JST PH-2 vertical (same footprint as J4) | 1=`BAT+`, 2=`GND` |
| **J6** GPIO breakout | 1×6 SIL pin header, 2.54 mm | 1=`D0`, 2=`D1_NET`, 3=`D6`, 4=`GND`, 5=`+3V3`, 6=`D5` (SD_CS moved to GPIO42 bottom pad — no jumper needed, D1 is a free breakout GPIO) |
| **J7** microSD card | Push-push microSD socket (e.g. Hirose DM3D-SF) | 8-pin SD: 1=`SD_CS` (DAT3), 2=`SD_MOSI` (CMD), 3=`GND`, 4=`+3V3`, 5=`SD_SCK` (CLK), 6=`GND`, 7=`SD_MISO` (DAT0), 8=NC (DAT1), 9=NC (DAT2) |

---

## Final BOM

### Active

| Ref | Part | Package | Library |
|---|---|---|---|
| U? | XIAO ESP32-S3 | XIAO SMD castellated | `New_Library:XIAO_ESP32-S3_SMD` |
| U2 | CS4344 | MSOP-10 (3×3 mm, 0.5 mm pitch) | `Audio:CS4344` (stock KiCad) |
| U3 | APA2068 | SOP-16-P with EP | `New_Library:SOP-16-P_3.9x9.9mm_P1.27mm_EP2.18x4.12mm` |
| U4 | TPS61023DRLR | SOT-563 (6-pin) | `New_Library:TPS61023DRLR` |

### Passives

| Ref | Value | Package | Purpose |
|---|---|---|---|
| C2 | 0.1 µF | **0402 X7R** | CS4344 VA HF |
| C3 | 1 µF | **0402 X7R** | CS4344 VA bulk |
| C4 | 10 µF | 0805 X5R | CS4344 FILT+ (size kept — 10 µF in 0402 is rare) |
| C5 | 0.1 µF | **0402 X7R** | CS4344 VQ HF |
| C6 | 3.3 µF | **0603 X5R** | CS4344 VQ popguard (down from 0805) |
| C7 | 3.3 µF | 0805 X5R | CS4344 AOUTL DC-block (audio path — keep 0805) |
| C8 | 3.3 µF | 0805 X5R | CS4344 AOUTR DC-block (audio path — keep 0805) |
| C9 | 0.1 µF | **0402 X7R** | APA2068 VDD HF (pin 10) |
| C10 | 0.1 µF | **0402 X7R** | APA2068 VDD HF (pin 15) |
| C11 | 100 µF | electrolytic 6.3 mm | APA2068 VDD bulk |
| C12 | 2.2 µF | **0603 X5R** | APA2068 BYPASS (down from 0805) |
| C13 | 220 µF | electrolytic 6.3 mm | Headphone L AC |
| C14 | 220 µF | electrolytic 6.3 mm | Headphone R AC |
| C15 | 0.1 µF | **0402 X7R** | VOLUME divider filter |
| C16 | 10 µF | 0805 X5R | Boost VIN |
| C17 | 22 µF | 0805 X5R | Boost VOUT |
| C18 | 0.1 µF | **0402 X7R** | SD card VDD decoupling (new) |
| C19 | 10 µF | 0805 X5R | SD card VDD bulk (new) |
| L1 | 4.7 µH | SMD power, 1.5 A+ | TPS61023 inductor |
| D1 | SS14 (1 A 40 V Schottky) | SMA / SOD-123FL | Boost output OR'ing diode |
| R1 | 100 kΩ | **0402** | SE/BTL pull-up |
| R2 | 100 kΩ | **0402** | SE/BTL series to jack SW |
| R3 | 1 kΩ | 0603 | HP L load reference (audio path) |
| R4 | 1 kΩ | 0603 | HP R load reference (audio path) |
| R7 | 100 kΩ | **0402** | VOLUME divider top |
| R8 | 10 kΩ | **0402** | VOLUME divider bottom |
| R9 | 365 kΩ | **0402** (1%) | Boost FB top |
| R10 | 49.9 kΩ | **0402** (1%) | Boost FB bottom |
| R11 | 10 kΩ | **0402** | SD_CS pull-up (new) |
| R12 | 10 kΩ | **0402** | SD_MOSI pull-up (new — keeps line defined when CS deasserted) |
| R13 | 10 kΩ | **0402** | SD_MISO pull-up (new) |
| ~~R14~~ | — | — | (removed — SD_CS moved to dedicated GPIO42) |
| ~~R15~~ | — | — | (removed — SD_CS moved to dedicated GPIO42) |

### Connectors

| Ref | Part |
|---|---|
| J1 | 3.5 mm stereo TRS jack with switch — PJ-320A or equivalent |
| J2 | JST PH-2 (B2B-PH-K-S or equivalent) — L speaker |
| J3 | JST PH-2 — R speaker |
| J4 | JST PH-2 — V+ external |
| J5 | JST PH-2 (B2B-PH-K-S or equivalent) — battery (was screw terminal in v1, now matches J4) |
| J6 | 1×10 male pin header, 2.54 mm pitch — GPIO breakout |

**Total:** 4 ICs + XIAO module + 6 connectors + 1 inductor + 1 diode + 16 caps + 8 resistors = **37 placements**.

---

## Net list summary

| Net | Members |
|---|---|
| `+5V` | XIAO 5V pin, J4 pin 1, D1 cathode, APA2068 pins 1/2/10/15, R1, R7, C9, C10, C11, C17, J6 pin 10 |
| `+3V3` | XIAO 3V3 pin, CS4344 pin 9, C2, C3, J6 pin 9 |
| `GND` | every return + J6 pin 8 + APA2068 EP + sleeves + screws |
| `BAT+` | XIAO BAT+ pin, J5 pin 1, U4 pin 2 (EN), U4 pin 3 (VIN), C16 |
| `BOOST_SW` | U4 pin 5, L1 (one terminal) |
| `BOOST_OUT` | U4 pin 6, L1 (other terminal), C17, D1 anode, R9 (top) |
| `FB_NET` | U4 pin 1, R9 (bottom), R10 (top) |
| `I2S_BCLK` | XIAO D7, CS4344 pin 2 |
| `I2S_LRCK` | XIAO D8, CS4344 pin 3 |
| `I2S_DOUT` | XIAO D9, CS4344 pin 1 |
| `I2S_MCLK` | XIAO D10, CS4344 pin 4 |
| `VQ_NET` | CS4344 pin 5, C5, C6 |
| `FILT_NET` | CS4344 pin 6, C4 |
| `AOUTL_AC` | CS4344 pin 7 → C7+ → C7– → APA2068 pin 6 |
| `AOUTR_AC` | CS4344 pin 10 → C8+ → C8– → APA2068 pin 3 |
| `BYPASS_C` | APA2068 pin 4, C12 |
| `VOLUME_C` | APA2068 pin 7, R7, R8, C15 |
| `SE_BTL` | APA2068 pin 13, R1, R2 |
| `J1_SW` | J1 switch contact, R2 (other side) |
| `SPK_L_NEG` | APA2068 pin 9, J2 pin 1, C13 (+) |
| `SPK_L_POS` | APA2068 pin 11, J2 pin 2 |
| `SPK_R_NEG` | APA2068 pin 16, J3 pin 1, C14 (+) |
| `SPK_R_POS` | APA2068 pin 14, J3 pin 2 |
| `HP_L` | C13 (–), J1 Tip, R3 |
| `HP_R` | C14 (–), J1 Ring, R4 |
| `D0` | XIAO pin 1 → J6 pin 1 |
| `D5` | XIAO pin 6 → J6 pin 2 |
| `D6` | XIAO pin 7 → J6 pin 3 |
| `SD_CS` | XIAO pin 2 (D1) → J7 pin 1, R11 (pull-up to +3V3) |
| `SD_SCK` | XIAO pin 3 (D2) → J7 pin 5 |
| `SD_MOSI` | XIAO pin 4 (D3) → J7 pin 2, R12 (pull-up to +3V3) |
| `SD_MISO` | XIAO pin 5 (D4) → J7 pin 7, R13 (pull-up to +3V3) |
