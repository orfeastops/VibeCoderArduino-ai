# VibeCoder 🔌

**Program any microcontroller by just describing what you want.**

No Arduino IDE. No looking up pin numbers. No library hunting.  
Just connect your board, type what you want it to do, and VibeCoder handles everything.

```
[VibeCoder] ➜ blink the onboard LED every 500ms and print "hello" to serial

🤖 Thinking (llama-3.3-70b-versatile)...

✅ Compiled successfully
✅ Upload successful! Hardware is live.
📊 Wiring diagram → ~/wiring_diagram.html
💾 Project saved to history
```

---

## What it does

- **Detects your board automatically** — plugs in, gets identified (36+ boards supported)
- **Generates complete Arduino code** via AI — no placeholders, no TODOs
- **Checks for dangerous pins** — warns you before using boot-strapping or reserved pins
- **Compiles and uploads** with the correct method for your board (avrdude / esptool / UF2 / DFU / bossac)
- **Auto-fixes compile errors** — if the first attempt fails, asks AI to fix and retries
- **Generates a wiring diagram** — visual HTML file showing every connection
- **Saves every project** to history — never lose working code again
- **Works on Linux, Windows, macOS**

---

## Supported Boards

| Family | Boards |
|--------|--------|
| **Arduino AVR** | Uno, Nano, Mega 2560, Leonardo, Micro |
| **Arduino ARM** | Due, MKR1000, Zero |
| **ESP** | ESP8266 NodeMCU, ESP32 DevKit, ESP32-S2, ESP32-C3 |
| **Raspberry Pi** | Pico, Pico W |
| **STM32** | Blue Pill, Black Pill |
| **Teensy** | 4.1, 4.0, 3.2 |
| **Adafruit** | Feather M0, Feather nRF52840 |
| **BBC** | micro:bit |
| **Unknown boards** | AI identifies from USB VID/PID and fetches pin rules dynamically |

> Board database auto-updates from GitHub every 24h. New board? Just add it to `boards.json`.

---

## AI Backends

Choose your preferred AI on first run — or switch any time with `setup`:

| Backend | Cost | Speed | Notes |
|---------|------|-------|-------|
| **Groq** | Free | ~150 tok/s | Recommended. No credit card needed. |
| **OpenRouter** | Free tier | ~80 tok/s | Free models available |
| **Mistral AI** | Free | ~60 tok/s | 1B tokens/month free |
| **DeepSeek** | Cheap | ~80 tok/s | Via Custom API |
| **Anthropic Claude** | Paid | ~100 tok/s | Best code quality |
| **OpenAI** | Paid | ~80 tok/s | GPT-4o and friends |
| **Ollama** | Free | ~5-150 tok/s | Fully offline, no internet needed |
| **Any OpenAI-compatible API** | Varies | Varies | Together, Fireworks, NVIDIA, custom... |

---

## Quick Start

### 1. Install dependencies

**Linux / macOS:**
```bash
pip3 install requests pyserial prompt_toolkit
```

**Windows:**
```cmd
pip install requests pyserial prompt_toolkit
```

### 2. Install arduino-cli

**Linux / macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
```

**Windows:**  
Download from [arduino.github.io/arduino-cli](https://arduino.github.io/arduino-cli/latest/installation/)

### 3. Get a free API key (recommended)

Go to [console.groq.com](https://console.groq.com/keys) → sign up → create API key.  
No credit card required.

### 4. Run VibeCoder

```bash
python3 vibecoder.py        # Linux / macOS
python vibecoder.py         # Windows
```

First run will ask you to choose your AI backend and paste your API key.  
Config is saved to `~/.vibecoder_config.json` — you only do this once.

---

## Usage

```
[VibeCoder] ➜ <describe your project in plain English>
```

### Example prompts

```
make the LED on D1 blink 3 times when I press a button on D2
```
```
read temperature from DHT22 sensor and send it over serial every 5 seconds
```
```
control a servo motor with a potentiometer
```
```
connect to WiFi and send a GET request to api.example.com every minute
```

### Commands

| Command | What it does |
|---------|-------------|
| `history` | Show all saved projects |
| `load 3` | Reload project #3 from history |
| `load dht22` | Search history by keyword |
| `redeploy` | Re-upload the last sketch |
| `update` | Force refresh board database from GitHub |
| `setup` | Change AI backend or model |
| `exit` | Quit |

---

## Project History

Every successful upload is automatically saved to `~/.vibecoder_history/`:

```
~/.vibecoder_history/
├── index.json
├── 20260305_143200_blink_led/
│   ├── sketch.ino      ← the Arduino code
│   ├── wiring.json     ← connection table
│   └── meta.json       ← board, timestamp, task
└── 20260305_151000_dht22_sensor/
    ├── sketch.ino
    ├── wiring.json
    └── meta.json
```

---

## Pin Safety System

VibeCoder knows which pins are dangerous on each board and warns you before using them:

```
⚠️  WARNING: Pin D4 is reserved on NodeMCU ESP8266!
   Reason    : GPIO2 must be HIGH at boot + onboard LED
   Safe alt  : D2
   Risk      : May cause boot issues or programming failures
   Replace D4 → D2? [Y/n]:
```

You decide — VibeCoder educates, not dictates.

---

## Adding a New Board

Edit `boards.json` and add an entry to `usb_fingerprints` and `pin_rules`.  
Pull requests welcome!

```json
{
  "vid": "2341",
  "pid": "0043",
  "chip": "",
  "fqbn": "arduino:avr:uno",
  "name": "Arduino Uno R3",
  "upload_speed": 115200,
  "upload_method": "avrdude"
}
```

---

## Requirements

- Python 3.10+
- arduino-cli
- `requests`, `pyserial`, `prompt_toolkit`
- An AI API key (Groq free tier recommended) **or** Ollama for offline use

---

## License

MIT — free to use, modify, and distribute.

---

## Contributing

Issues and PRs welcome. Especially:
- New board entries in `boards.json`
- Upload method fixes for specific boards
- Testing on Windows / macOS

---

*Built with Python + arduino-cli + your favorite LLM.*  
*Tested on Linux. Should work on Windows and macOS.*
