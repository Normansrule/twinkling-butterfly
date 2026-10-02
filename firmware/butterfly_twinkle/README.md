# Firmware

Arduino sketch for the Twinkling Butterfly.

| | |
|---|---|
| Core | `esp32` (Espressif Arduino core) |
| Board | **ESP32C3 Dev Module** |
| Port | the FT231XS COM port that appears when you plug in USB-C |
| Upload | normal Upload button; the DTR/RTS transistors handle reset and boot mode |
| Library | `Adafruit NeoPixel` (Library Manager) |

SW1 must be **on** to flash: the ESP32 is powered from the switched battery
rail, and USB-C only supplies the charger and the bridge.

If the auto-reset ever misbehaves, GPIO18/19 are brought out to TP1/TP2 for
the native-USB flashing path.
