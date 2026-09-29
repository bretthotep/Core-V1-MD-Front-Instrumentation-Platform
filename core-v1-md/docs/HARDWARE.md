# Hardware notes (planning)

> The target hardware is **not yet chosen**. This document records requirements,
> candidate approaches and open questions. Nothing here is final.

## Host

- **Case:** Thermaltake Core V1 (Mini-ITX cube). The front fascia covers a 200 mm intake fan.
- **PC:** custom gaming / development build (Windows).

## Display strip

| Requirement | Notes |
|---|---|
| Technology | AMOLED/OLED preferred: true black, high contrast, EL-like glow |
| Form factor | Narrow vertical bar; simulator placeholder 240 × 1000 (~1:4) |
| Interface | SPI/QSPI or MIPI-DSI via a bridge, or a USB display controller |
| Pixel format | RGB565 assumed (`display.oled_display.to_rgb565`) |
| Brightness | Software-controllable; dim at night |
| Burn-in | Mostly-black UI + optional pixel-shift orbit (`FutureOledDisplay.pixel_shift`) |

Open questions:

- Exact module and resolution – the layout engine adapts to any size (`--width/--height`
  in the simulator), so this can be decided late.
- Whether frames are driven directly from the PC (USB display) or streamed via the ESP32.
- Achievable frame rate over the chosen link (240 × 1000 × 16 bpp ≈ 480 KB/frame).

## Controller

- **ESP32**-class MCU mounted behind the fascia, outside the fan's swept area.
- USB CDC serial to the PC for input events (see `hardware/esp32.py` for the draft protocol).
- Optional: frame buffer streaming to the display.

## Jog wheel

- Detented rotary encoder with integrated push switch.
- Optional dedicated HOME key.
- Gesture classification (press / double / long) happens on the host
  (`hardware.jog.PressGestureDetector`) so timing can be tuned without reflashing.

## Cooling & airflow constraints

- Nothing inside the 200 mm fan's intake path.
- Display strip and controller must be thinner than the fascia's existing clearance.
- Flat/flex cabling routed along existing front-I/O paths.
- Sub-watt power budget; no additional heat source near intake.
