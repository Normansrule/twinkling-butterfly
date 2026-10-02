/*
 * Twinkling Butterfly - firmware
 * ------------------------------
 * Board : custom ESP32-C3FH4, 6 x WS2812B on GPIO4, 2 x LIR2032 in parallel
 * Build : Arduino IDE, esp32 core, board "ESP32C3 Dev Module"
 * Flash : over the onboard FT231XS COM port. Auto-reset works, no buttons.
 *
 * The power budget is the whole design here.  Two LIR2032 cells give about
 * 80 mAh and will sag badly above roughly 60 mA, so the firmware keeps the
 * average draw near 12 mA:
 *
 *   - global brightness capped at MAX_BRIGHTNESS (~10 %)
 *   - never more than MAX_LIT pixels above zero at once
 *   - light sleep between frames instead of delay(), which parks the CPU
 *   - deep sleep after AUTO_OFF_HOURS so a forgotten ornament does not
 *     deep-discharge the cells
 *
 * The pixels run straight off the switched battery rail (3.0-4.2 V), not off
 * the 3.3 V regulator.  Below ~3.5 V the blue and green dice inside a WS2812B
 * dim faster than the red one, so colours drift warm as the cells empty.  At
 * this brightness it reads as candlelight rather than as a fault.
 */

#include <Adafruit_NeoPixel.h>
#include <esp_sleep.h>
#include <esp_random.h>

// ---------------------------------------------------------------- hardware
constexpr uint8_t  LED_PIN        = 4;      // GPIO4 -> 470 ohm -> D1 DIN
constexpr uint16_t NUM_PIXELS     = 6;

// ------------------------------------------------------------ power budget
constexpr uint8_t  MAX_BRIGHTNESS = 25;     // of 255; ~10 %
constexpr uint8_t  MAX_LIT        = 3;      // pixels allowed above zero
constexpr uint32_t FRAME_US       = 33000;  // ~30 fps
constexpr uint32_t AUTO_OFF_HOURS = 8;

// ------------------------------------------------------------- twinkle feel
constexpr uint16_t FADE_IN_MIN    = 400;    // ms
constexpr uint16_t FADE_IN_MAX    = 1600;
constexpr uint16_t HOLD_MIN       = 120;
constexpr uint16_t HOLD_MAX       = 900;
constexpr uint16_t FADE_OUT_MIN   = 600;
constexpr uint16_t FADE_OUT_MAX   = 2200;
constexpr uint16_t REST_MIN       = 300;    // dark time before a pixel may relight
constexpr uint16_t REST_MAX       = 4000;

Adafruit_NeoPixel strip(NUM_PIXELS, LED_PIN, NEO_GRB + NEO_KHZ800);

// Warm candle-ish hues, as (r,g,b) at full scale. Kept away from pure blue:
// blue costs the most current and fades first as the cells discharge.
struct Hue { uint8_t r, g, b; };
constexpr Hue PALETTE[] = {
  {255, 180,  70},   // amber
  {255, 120,  40},   // ember
  {255, 220, 150},   // warm white
  {200, 160, 255},   // faint violet
  {120, 255, 190},   // mint
};
constexpr uint8_t PALETTE_N = sizeof(PALETTE) / sizeof(PALETTE[0]);

// gamma 2.2, so a linear fade looks linear to the eye
uint8_t gamma8(uint8_t v) {
  static const uint8_t T[32] = {
      0,  0,  1,  2,  4,  6,  9, 12, 16, 20, 25, 30, 36, 42, 49, 56,
     64, 72, 81, 90,100,110,121,132,144,156,169,182,196,210,225,255};
  uint8_t i = v >> 3, f = v & 7;
  uint16_t a = T[i], b = (i < 31) ? T[i + 1] : 255;
  return a + ((b - a) * f) / 8;
}

enum Phase : uint8_t { REST, FADE_IN, HOLD, FADE_OUT };

struct Pixel {
  Phase    phase    = REST;
  uint32_t t_start  = 0;
  uint32_t t_len    = 0;
  Hue      hue      = PALETTE[0];
  uint8_t  level    = 0;      // 0..255 before gamma
} px[NUM_PIXELS];

uint32_t rnd(uint32_t lo, uint32_t hi) {      // inclusive-exclusive
  return lo + (esp_random() % (hi - lo));
}

uint8_t litCount() {
  uint8_t n = 0;
  for (auto &p : px) if (p.phase != REST) n++;
  return n;
}

void startPixel(Pixel &p, uint32_t now) {
  p.phase   = FADE_IN;
  p.t_start = now;
  p.t_len   = rnd(FADE_IN_MIN, FADE_IN_MAX);
  p.hue     = PALETTE[esp_random() % PALETTE_N];
}

void advance(Pixel &p, uint32_t now) {
  uint32_t dt = now - p.t_start;
  switch (p.phase) {
    case REST:
      p.level = 0;
      if (dt >= p.t_len && litCount() < MAX_LIT) startPixel(p, now);
      break;
    case FADE_IN:
      p.level = (dt >= p.t_len) ? 255 : (uint8_t)((dt * 255) / p.t_len);
      if (dt >= p.t_len) { p.phase = HOLD; p.t_start = now; p.t_len = rnd(HOLD_MIN, HOLD_MAX); }
      break;
    case HOLD:
      p.level = 255;
      if (dt >= p.t_len) { p.phase = FADE_OUT; p.t_start = now; p.t_len = rnd(FADE_OUT_MIN, FADE_OUT_MAX); }
      break;
    case FADE_OUT:
      p.level = (dt >= p.t_len) ? 0 : (uint8_t)(255 - (dt * 255) / p.t_len);
      if (dt >= p.t_len) { p.phase = REST; p.t_start = now; p.t_len = rnd(REST_MIN, REST_MAX); }
      break;
  }
}

void setup() {
  strip.begin();
  strip.setBrightness(MAX_BRIGHTNESS);
  strip.clear();
  strip.show();

  uint32_t now = millis();
  for (uint16_t i = 0; i < NUM_PIXELS; i++) {
    px[i].phase   = REST;
    px[i].t_start = now;
    px[i].t_len   = rnd(0, REST_MAX);     // stagger so they do not pulse in step
  }

  // Wake the CPU from light sleep on the frame timer alone.
  esp_sleep_enable_timer_wakeup(FRAME_US);
}

void loop() {
  static uint32_t started = millis();
  uint32_t now = millis();

  if ((now - started) >= AUTO_OFF_HOURS * 3600UL * 1000UL) {
    strip.clear();
    strip.show();
    delay(10);
    esp_deep_sleep_start();              // only a power cycle on SW1 wakes it
  }

  for (uint16_t i = 0; i < NUM_PIXELS; i++) {
    advance(px[i], now);
    uint8_t  g = gamma8(px[i].level);
    const Hue &h = px[i].hue;
    strip.setPixelColor(i,
        (uint8_t)((h.r * g) / 255),
        (uint8_t)((h.g * g) / 255),
        (uint8_t)((h.b * g) / 255));
  }
  strip.show();

  // Park the CPU until the next frame. Far cheaper than delay(), which keeps
  // the core clocked the whole time.
  esp_light_sleep_start();
}
