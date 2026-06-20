# freeesp32_audioplayer

Open-source ESP32 audio playback board designed primarily as the hardware
platform for [**`freeesp32_ave`**](https://github.com/ppisljar/freeesp32_ave) —
audio-visual entrainment (AVE) firmware.

This repository contains the full **KiCad** project: schematic, PCB layout,
design rules, 3D models, datasheets, and helper scripts.

## Board features

- **MCU module**: Seeed Studio **XIAO ESP32-S3** (Wi-Fi + BLE)
- **Headphone output**: Cirrus Logic **CS4344** stereo I²S DAC
- **Speaker output**: **APA2068** Class-D power amplifier
- **Storage**: microSD card slot for offline audio and timeline files
- **LED outputs**: configurable headers — works with NeoPixel (WS2812),
  DotStar (APA102), or direct PWM strips (the firmware picks the backend)

## Repository layout

```
main_board/
├── esp32audio.kicad_sch    # schematic
├── esp32audio.kicad_pcb    # PCB layout
├── esp32audio.kicad_pro    # KiCad project
├── 3dmodels/               # STEP models for enclosure design
├── datasheets/             # IC datasheets and reference schematics
├── analysis/               # generated reports (regenerable from source)
├── outputs/                # gerbers, drill files, BOM
└── *.py                    # helper scripts (netlist sync, freerouting…)
```

## Related projects

| Repo | Role |
|---|---|
| [`freeesp32_audioplayer`](https://github.com/ppisljar/freeesp32_audioplayer) | **This repo** — open hardware (KiCad) |
| [`freeesp32_ave`](https://github.com/ppisljar/freeesp32_ave) | AVE firmware that runs on this board |
| [`freeesp32_ave_generator`](https://github.com/ppisljar/freeesp32_ave_generator) | Web editor that generates session timelines for the firmware |

## Status

Hardware design in active development. See `main_board/project_plan.md` and
`main_board/lessons_learned.md` for design notes.

## License

TBD — open hardware license to be chosen (e.g. CERN-OHL-S 2.0).
