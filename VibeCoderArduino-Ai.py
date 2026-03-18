#!/usr/bin/env python3
"""
VibeCoder v6.1 — Universal AI Hardware Agent
=============================================
Cross-platform: Linux, Windows, macOS
Auto-updating board database from GitHub

Usage:
  Linux/macOS : python3 vibecoder.py
  Windows     : python vibecoder.py
"""

import os, sys, json, time, re, subprocess, requests, webbrowser, platform

# ── Platform Detection ────────────────────────────────────────────────────────
IS_WINDOWS = platform.system() == "Windows"
IS_MAC     = platform.system() == "Darwin"
IS_LINUX   = platform.system() == "Linux"

# ── Paths ─────────────────────────────────────────────────────────────────────
HOME          = os.path.expanduser("~")
SKETCH_DIR    = os.path.join(HOME, "vibe_sketch")
DIAGRAM_FILE  = os.path.join(HOME, "wiring_diagram.html")
CONFIG_FILE   = os.path.join(HOME, ".vibecoder_config.json")
AVR_BAUDS     = [57600, 115200, 38400, 19200, 9600]

# ── Online board database ─────────────────────────────────────────────────────
BOARDS_DB_URL  = "https://raw.githubusercontent.com/YOUR_USERNAME/vibecoder/main/boards.json"
BOARDS_DB_FILE = os.path.join(HOME, ".vibecoder_boards.json")
BOARDS_DB_TTL  = 86400  # Re-download every 24 hours

# Project history
HISTORY_DIR    = os.path.join(HOME, ".vibecoder_history")
HISTORY_INDEX  = os.path.join(HISTORY_DIR, "index.json")

# ── AI Backend Configuration ──────────────────────────────────────────────────
AI_BACKENDS = {
    "groq": {
        "name":     "Groq (free, ~150 tokens/sec)",
        "url":      "https://api.groq.com/openai/v1/chat/completions",
        "model":    "llama-3.3-70b-versatile",
        "models":   ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
        "key_url":  "https://console.groq.com/keys",
        "free":     True,
        "needs_key": True,
    },
    "openrouter": {
        "name":     "OpenRouter (free tier available)",
        "url":      "https://openrouter.ai/api/v1/chat/completions",
        "model":    "qwen/qwen-2.5-coder-32b-instruct:free",
        "models":   ["qwen/qwen-2.5-coder-32b-instruct:free",
                     "google/gemini-2.0-flash-exp:free",
                     "meta-llama/llama-3.3-70b-instruct:free"],
        "key_url":  "https://openrouter.ai/keys",
        "free":     True,
        "needs_key": True,
    },
    "anthropic": {
        "name":     "Anthropic Claude (paid, best quality)",
        "url":      "https://api.anthropic.com/v1/messages",
        "model":    "claude-haiku-4-5",
        "models":   ["claude-haiku-4-5", "claude-sonnet-4-5"],
        "key_url":  "https://console.anthropic.com/",
        "free":     False,
        "needs_key": True,
    },
    "openai": {
        "name":     "OpenAI (paid)",
        "url":      "https://api.openai.com/v1/chat/completions",
        "model":    "gpt-4o-mini",
        "models":   ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
        "key_url":  "https://platform.openai.com/api-keys",
        "free":     False,
        "needs_key": True,
    },
    "mistral": {
        "name":     "Mistral AI (free, 1B tokens/month)",
        "url":      "https://api.mistral.ai/v1/chat/completions",
        "model":    "mistral-small-latest",
        "models":   ["mistral-small-latest", "open-mistral-7b"],
        "key_url":  "https://console.mistral.ai/",
        "free":     True,
        "needs_key": True,
    },
    "ollama": {
        "name":     "Ollama (local, offline, no internet needed)",
        "url":      "http://localhost:11434/api/chat",
        "model":    "qwen2.5-coder:3b",
        "models":   ["qwen2.5-coder:7b", "qwen2.5-coder:3b", "llama3:8b"],
        "key_url":  "",
        "free":     True,
        "needs_key": False,
    },
    "custom": {
        "name":     "Custom API (DeepSeek, Together, Cohere, any OpenAI-compatible)",
        "url":      "",
        "model":    "",
        "models":   [],
        "key_url":  "",
        "free":     None,
        "needs_key": True,
    },
}

KNOWN_CUSTOM_APIS = {
    "deepseek":   ("https://api.deepseek.com/v1/chat/completions",         "deepseek-coder",                          "https://platform.deepseek.com"),
    "together":   ("https://api.together.xyz/v1/chat/completions",         "Qwen/Qwen2.5-Coder-32B-Instruct",         "https://api.together.ai"),
    "cohere":     ("https://api.cohere.ai/v1/chat",                        "command-r-plus",                          "https://dashboard.cohere.com"),
    "fireworks":  ("https://api.fireworks.ai/inference/v1/chat/completions","accounts/fireworks/models/qwen2p5-coder-32b-instruct", "https://fireworks.ai"),
    "nvidia":     ("https://integrate.api.nvidia.com/v1/chat/completions",  "qwen/qwen2.5-coder-32b-instruct",         "https://build.nvidia.com"),
    "ollama":     ("http://localhost:11434/v1/chat/completions",            "qwen2.5-coder:7b",                        "local"),
}

AI_CFG: dict = {}

# ── Smart input with arrow keys, history ─────────────────────────────────────
try:
    from prompt_toolkit import prompt as _pt_prompt
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.styles import Style
    _pt_style   = Style.from_dict({"prompt": "ansigreen bold"})
    _pt_history = InMemoryHistory()
    _HAS_PT     = True
except ImportError:
    _HAS_PT = False
    try:
        import readline
        readline.parse_and_bind("tab: complete")
    except ImportError:
        pass

def smart_input(prompt_text: str) -> str:
    if _HAS_PT:
        try:
            return _pt_prompt(prompt_text, history=_pt_history,
                              auto_suggest=AutoSuggestFromHistory(),
                              style=_pt_style).strip()
        except (KeyboardInterrupt, EOFError):
            raise
        except Exception:
            pass
    return input(prompt_text).strip()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 0 - AI Backend Setup
# ══════════════════════════════════════════════════════════════════════════════

def _save_config(cfg: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def _load_config() -> dict:
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def setup_ai_backend(force: bool = False) -> dict:
    saved = _load_config()
    if saved.get("backend") and not force:
        b    = saved["backend"]
        info = AI_BACKENDS.get(b, {})
        print(f"   AI Backend : {info.get('name', b)}")
        print(f"   Model      : {saved.get('model','?')}")
        return saved

    print("\n" + "="*60)
    print("  VibeCoder - AI Backend Setup")
    print("="*60)
    print("\nChoose your AI backend:")
    print("(Recommended: Groq — free, fast, no credit card needed)\n")
    backends = list(AI_BACKENDS.items())
    for i, (key, info) in enumerate(backends, 1):
        free_tag = "FREE" if info["free"] else "paid"
        print(f"  {i}. {info['name']}  [{free_tag}]")
    print()
    while True:
        pick = smart_input("Your choice (1-5): ")
        if pick.isdigit() and 1 <= int(pick) <= len(backends):
            backend_key, backend_info = backends[int(pick)-1]
            break
        print("   Enter a number 1-5.")

    cfg = {"backend": backend_key, "model": backend_info["model"], "api_key": ""}

    if backend_key == "custom":
        print("\n  Known providers (or enter your own):")
        known = list(KNOWN_CUSTOM_APIS.items())
        for i, (name, (url, model, key_url)) in enumerate(known, 1):
            print(f"    {i}. {name:<12} {url[:45]}")
        print(f"    {len(known)+1}. Enter custom URL manually")

        pick = smart_input("  Choose provider (Enter for manual): ").strip()
        if pick.isdigit() and 1 <= int(pick) <= len(known):
            pname, (url, model, key_url) = known[int(pick)-1]
            cfg["url"]   = url
            cfg["model"] = model
            print(f"\n  API key for {pname}: {key_url}")
        elif pick.isdigit() and int(pick) == len(known)+1 or not pick:
            cfg["url"]   = smart_input("  API endpoint URL: ").strip()
            cfg["model"] = smart_input("  Model name: ").strip()
            key_url      = ""
        else:
            hits = [(n,v) for n,v in known if pick.lower() in n.lower()]
            if hits:
                pname, (url, model, key_url) = hits[0]
                cfg["url"]   = url
                cfg["model"] = model
                print(f"  Selected: {pname}")
            else:
                cfg["url"]   = smart_input("  API endpoint URL: ").strip()
                cfg["model"] = smart_input("  Model name: ").strip()

        override = smart_input(f"  Model [{cfg['model']}] (Enter to keep): ").strip()
        if override:
            cfg["model"] = override

        key = smart_input("  API key (Enter to skip): ").strip()
        cfg["api_key"] = key
        cfg["api_format"] = "anthropic" if "anthropic.com" in cfg.get("url","") else "openai"

        _save_config(cfg)
        print(f"\n  Saved! Custom API: {cfg['url']}")
        print(f"  Model: {cfg['model']}\n")
        return cfg

    if backend_info["needs_key"]:
        if backend_info.get("key_url"):
            print(f"\n  Get API key at: {backend_info['key_url']}")
        key = smart_input("  Paste your API key (Enter to skip): ").strip()
        if key:
            cfg["api_key"] = key
        elif backend_key != "ollama":
            print("  ⚠️  No API key entered.")
            print("  You can add it later by typing 'setup' inside VibeCoder.")
            print("  Without a key, this backend will not work.")

    models = backend_info["models"]
    if len(models) > 1:
        print("\n  Available models:")
        for i, m in enumerate(models, 1):
            tag = " <- recommended" if i == 1 else ""
            print(f"    {i}. {m}{tag}")
        pick = smart_input("  Choose model (Enter for default): ").strip()
        if pick.isdigit() and 1 <= int(pick) <= len(models):
            cfg["model"] = models[int(pick)-1]

    _save_config(cfg)
    print(f"\n  Saved! Backend: {AI_BACKENDS[cfg['backend']]['name']}")
    print(f"  Model: {cfg['model']}\n")
    return cfg


def ai_ask(messages: list, timeout: int = 300) -> str | None:
    backend = AI_CFG.get("backend", "groq")
    model   = AI_CFG.get("model",   "qwen2.5-coder:3b")
    key     = AI_CFG.get("api_key", "")
    info    = AI_BACKENDS.get(backend, list(AI_BACKENDS.values())[0])

    if backend == "custom":
        url        = AI_CFG.get("url", "")
        api_format = AI_CFG.get("api_format", "openai")
    else:
        url        = info["url"]
        api_format = "anthropic" if backend == "anthropic" else \
                     "ollama"    if backend == "ollama"    else "openai"

    try:
        if api_format == "anthropic":
            system = next((m["content"] for m in messages if m["role"]=="system"), "")
            msgs   = [m for m in messages if m["role"] != "system"]
            resp   = requests.post(url,
                headers={"x-api-key":key,"anthropic-version":"2023-06-01",
                         "content-type":"application/json"},
                json={"model":model,"max_tokens":2048,"temperature":0.2,"system":system,"messages":msgs},
                timeout=timeout)
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]

        elif api_format == "ollama":
            resp = requests.post(url,
                json={"model":model,"messages":messages,"stream":False},
                timeout=timeout)
            resp.raise_for_status()
            return resp.json()["message"]["content"]

        else:
            headers = {"Authorization":f"Bearer {key}","Content-Type":"application/json"}
            if backend == "openrouter":
                headers["HTTP-Referer"] = "https://github.com/vibecoder"
                headers["X-Title"]      = "VibeCoder"
            resp = requests.post(url, headers=headers,
                json={"model":model,"messages":messages,
                      "max_tokens":2048,"temperature":0.2},
                timeout=timeout)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    except requests.exceptions.ConnectionError:
        if backend == "ollama":
            print("\n  Cannot reach Ollama.")
            print("  Make sure Ollama is running: ollama serve")
            print("  Or switch to a cloud API: type 'setup'")
        else:
            print(f"\n  Cannot reach {info['name']}. Check internet connection.")
            print("  Type 'setup' to switch to a different backend.")
    except requests.exceptions.Timeout:
        if backend == "ollama":
            print("\n  Timeout. Ollama is slow on CPU.")
            print("  Try a smaller model: ollama pull qwen2.5-coder:3b")
            print("  Or switch to a fast free API: type 'setup' → choose Groq")
        else:
            print("\n  Timeout. Check your internet connection.")
            print("  Type 'setup' to switch to a different backend.")
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else 0
        if code == 401:   print("\n  Invalid API key. Type 'setup' to update.")
        elif code == 429: print("\n  Rate limit hit. Wait or type 'setup' to switch.")
        else:             print(f"\n  HTTP {code}: {e}")
    except Exception as e:
        print(f"\n  AI error: {e}")
    return None


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Board Database (Online + Local Fallback)
# ══════════════════════════════════════════════════════════════════════════════

_DB: dict = {}

def _load_builtin_db() -> dict:
    return {
        "_meta": {"version": "builtin"},
        "usb_fingerprints": [
            {"vid":"1a86","pid":"7523","chip":"ch34","fqbn":"arduino:avr:uno",           "name":"Arduino Uno (CH340)",       "upload_speed":57600,  "upload_method":"avrdude"},
            {"vid":"1a86","pid":"7523","chip":"ch34","fqbn":"arduino:avr:nano",          "name":"Arduino Nano (CH340)",      "upload_speed":57600,  "upload_method":"avrdude"},
            {"vid":"1a86","pid":"7523","chip":"ch34","fqbn":"esp8266:esp8266:nodemcuv2", "name":"NodeMCU ESP8266 (CH340)",   "upload_speed":921600, "upload_method":"esptool"},
            {"vid":"1a86","pid":"7523","chip":"ch34","fqbn":"esp32:esp32:esp32",         "name":"ESP32 DevKit (CH340)",      "upload_speed":921600, "upload_method":"esptool"},
            {"vid":"1a86","pid":"55d4","chip":"ch910","fqbn":"esp32:esp32:esp32",        "name":"ESP32 DevKit (CH9102)",     "upload_speed":921600, "upload_method":"esptool"},
            {"vid":"10c4","pid":"ea60","chip":"cp210","fqbn":"esp8266:esp8266:nodemcuv2","name":"NodeMCU ESP8266 (CP2102)",  "upload_speed":921600, "upload_method":"esptool"},
            {"vid":"10c4","pid":"ea60","chip":"cp210","fqbn":"esp32:esp32:esp32",        "name":"ESP32 DevKit (CP2102)",     "upload_speed":921600, "upload_method":"esptool"},
            {"vid":"0403","pid":"6001","chip":"ftdi", "fqbn":"arduino:avr:uno",          "name":"Arduino Uno (FTDI)",        "upload_speed":115200, "upload_method":"avrdude"},
            {"vid":"2341","pid":"0043","chip":"",     "fqbn":"arduino:avr:uno",          "name":"Arduino Uno R3",            "upload_speed":115200, "upload_method":"avrdude"},
            {"vid":"2341","pid":"0036","chip":"",     "fqbn":"arduino:avr:nano",         "name":"Arduino Nano",              "upload_speed":57600,  "upload_method":"avrdude"},
            {"vid":"2341","pid":"0010","chip":"",     "fqbn":"arduino:avr:mega2560",     "name":"Arduino Mega 2560",         "upload_speed":115200, "upload_method":"avrdude"},
            {"vid":"2e8a","pid":"0003","chip":"",     "fqbn":"rp2040:rp2040:rpipico",    "name":"Raspberry Pi Pico",         "upload_speed":None,   "upload_method":"uf2"},
            {"vid":"2e8a","pid":"000a","chip":"",     "fqbn":"rp2040:rp2040:rpipicow",   "name":"Raspberry Pi Pico W",       "upload_speed":None,   "upload_method":"uf2"},
        ],
        "pin_rules": {},
        "manual_selection_boards": [
            {"fqbn":"arduino:avr:uno",           "name":"Arduino Uno",         "upload_speed":115200, "upload_method":"avrdude"},
            {"fqbn":"arduino:avr:nano",          "name":"Arduino Nano",        "upload_speed":57600,  "upload_method":"avrdude"},
            {"fqbn":"arduino:avr:mega2560",      "name":"Arduino Mega 2560",   "upload_speed":115200, "upload_method":"avrdude"},
            {"fqbn":"esp8266:esp8266:nodemcuv2", "name":"NodeMCU ESP8266",     "upload_speed":921600, "upload_method":"esptool"},
            {"fqbn":"esp32:esp32:esp32",         "name":"ESP32 DevKit",        "upload_speed":921600, "upload_method":"esptool"},
            {"fqbn":"rp2040:rp2040:rpipico",     "name":"Raspberry Pi Pico",   "upload_speed":None,   "upload_method":"uf2"},
        ]
    }

def load_db() -> dict:
    global _DB

    if os.path.exists(BOARDS_DB_FILE):
        age = time.time() - os.path.getmtime(BOARDS_DB_FILE)
        if age < BOARDS_DB_TTL:
            try:
                with open(BOARDS_DB_FILE) as f:
                    _DB = json.load(f)
                    v = _DB.get("_meta",{}).get("version","?")
                    print(f"   📋 Board database v{v} (cached)")
                    return _DB
            except Exception:
                pass

    try:
        print("   🌐 Checking for board database updates...")
        resp = requests.get(BOARDS_DB_URL, timeout=10)
        if resp.status_code == 200:
            _DB = resp.json()
            with open(BOARDS_DB_FILE, "w") as f:
                json.dump(_DB, f, indent=2)
            v = _DB.get("_meta",{}).get("version","?")
            print(f"   ✅ Board database v{v} updated from GitHub")
            return _DB
    except Exception:
        pass

    if os.path.exists(BOARDS_DB_FILE):
        try:
            with open(BOARDS_DB_FILE) as f:
                _DB = json.load(f)
                print(f"   📋 Board database loaded (offline mode)")
                return _DB
        except Exception:
            pass

    print("   📋 Using built-in board database (offline)")
    _DB = _load_builtin_db()
    return _DB

def get_pin_rules(fqbn: str, board_name: str = "") -> dict:
    rules_db = _DB.get("pin_rules", {})

    for key, rules in rules_db.items():
        if key in fqbn or fqbn in key:
            norm = {}
            for pin, val in rules.get("reserved", {}).items():
                if isinstance(val, list) and len(val) >= 2:
                    norm[pin] = (val[0], val[1])
                else:
                    norm[pin] = (str(val), "")
            r = dict(rules)
            r["reserved"] = norm
            return r

    if fqbn in _pin_rules_cache:
        return _pin_rules_cache[fqbn]

    print(f"   🤖 Fetching pin rules for {board_name or fqbn}...")
    try:
        text = ai_ask([{"role":"user","content":(
                f"For {board_name} (FQBN: {fqbn}), list reserved/unsafe GPIO pins "
                "that must not be used for external components, and safe pins. "
                'Reply ONLY with JSON: {"reserved":{"PIN":["reason","alternative"]},'
                '"safe":["pin1",...],"analog":["pin1",...],"note":"voltage/current info","code_fixes":{}}'
            )}], timeout=60)
        if not text: raise ValueError("no response")
        s, e = text.find("{"), text.rfind("}") + 1
        data = json.loads(text[s:e])
        norm = {}
        for pin, val in data.get("reserved", {}).items():
            if isinstance(val, list) and len(val) >= 2:
                norm[pin] = (val[0], val[1])
            else:
                norm[pin] = (str(val), data.get("safe",[""])[0])
        data["reserved"] = norm
        data.setdefault("code_fixes", {})
        _pin_rules_cache[fqbn] = data
        print(f"   ✅ Got pin rules for {board_name or fqbn}")
        return data
    except Exception:
        return {"reserved":{}, "safe":[], "analog":[], "note":"", "code_fixes":{}}

_pin_rules_cache: dict = {}


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Cross-Platform Port Detection
# ══════════════════════════════════════════════════════════════════════════════

def list_serial_ports() -> list[str]:
    if IS_WINDOWS:
        try:
            from serial.tools import list_ports
            return [p.device for p in list_ports.comports()]
        except ImportError:
            ports = []
            for i in range(1, 20):
                port = f"COM{i}"
                try:
                    import serial
                    s = serial.Serial(port)
                    s.close()
                    ports.append(port)
                except Exception:
                    pass
            return ports
    elif IS_MAC:
        import glob
        return (glob.glob("/dev/tty.usbserial*") +
                glob.glob("/dev/tty.usbmodem*") +
                glob.glob("/dev/cu.usbserial*"))
    else:
        ports = []
        for p in [f"/dev/ttyUSB{i}" for i in range(8)] + \
                 [f"/dev/ttyACM{i}" for i in range(8)]:
            if os.path.exists(p):
                ports.append(p)
        return ports

def _usb_ids(port: str) -> tuple:
    if IS_WINDOWS:
        try:
            from serial.tools import list_ports
            for p in list_ports.comports():
                if p.device == port and p.vid and p.pid:
                    return (f"{p.vid:04x}", f"{p.pid:04x}")
        except Exception:
            pass
        return ("", "")
    elif IS_MAC:
        try:
            r = subprocess.run(["system_profiler","SPUSBDataType"],
                               capture_output=True, text=True, timeout=5)
            vid = pid = ""
            for line in r.stdout.splitlines():
                if "Vendor ID:" in line:
                    vid = line.split("0x")[-1].strip()[:4].lower()
                if "Product ID:" in line:
                    pid = line.split("0x")[-1].strip()[:4].lower()
            return (vid, pid)
        except Exception:
            return ("", "")
    else:
        try:
            name = os.path.basename(port)
            path = os.path.realpath(f"/sys/class/tty/{name}/device")
            for _ in range(6):
                path = os.path.dirname(path)
                v = os.path.join(path, "idVendor")
                if os.path.exists(v):
                    return (open(v).read().strip().lower(),
                            open(os.path.join(path,"idProduct")).read().strip().lower())
        except Exception:
            pass
        return ("", "")

def _chip_from_dmesg(port: str) -> str:
    if not IS_LINUX: return ""
    try:
        name = os.path.basename(port)
        out  = subprocess.run(["dmesg"], capture_output=True, text=True, timeout=5).stdout
        for line in reversed(out.splitlines()):
            if name in line:
                for kw in ("ch341","ch340","ch9102","cp210","ftdi","cdc_acm","rp2040"):
                    if kw in line.lower():
                        return kw
    except Exception:
        pass
    return ""

def _ensure_serial_permissions(port: str):
    if not IS_LINUX: return
    try:
        import grp, pwd
        dialout = grp.getgrnam("dialout")
        user    = pwd.getpwuid(os.getuid()).pw_name
        if user not in dialout.gr_mem and os.environ.get("VIBECODER_REEXEC") != "1":
            print(f"   🔑 Adding {user} to dialout group...")
            subprocess.run(["sudo","usermod","-aG","dialout",user], capture_output=True)
            os.environ["VIBECODER_REEXEC"] = "1"
            os.execvpe("sg", ["sg","dialout","-c",
                               f"python3 {' '.join(sys.argv)}"], os.environ)
    except Exception:
        pass

def _fingerprint(port: str) -> list[dict]:
    vid, pid = _usb_ids(port)
    chip     = _chip_from_dmesg(port)
    print(f"   🔬 USB {vid or '?'}:{pid or '?'}  chip: {chip or 'unknown'}")

    matches, seen = [], set()
    for row in _DB.get("usb_fingerprints", []):
        score = 0
        if vid and pid and vid == row["vid"] and pid == row["pid"]: score += 10
        elif vid and vid == row["vid"]:                              score += 4
        if row.get("chip") and chip and row["chip"] in chip:         score += 3
        if score >= 3 and row["fqbn"] not in seen:
            seen.add(row["fqbn"])
            matches.append({**row, "score": score})
    return sorted(matches, key=lambda x: -x["score"])

def _manual_select(port: str, candidates: list[dict]) -> dict:
    manual = _DB.get("manual_selection_boards", [])
    seen, options = set(), []
    for o in candidates + manual:
        if o["fqbn"] not in seen:
            seen.add(o["fqbn"])
            options.append(o)

    print(f"\n   Select your board (number or type to search):")
    for i, o in enumerate(options, 1):
        print(f"      {i:2}. {o['name']}")

    while True:
        pick = smart_input("   Your choice: ").lower()
        if pick.isdigit() and 1 <= int(pick) <= len(options):
            chosen = options[int(pick)-1]
            print(f"   ✔  {chosen['name']}")
            return chosen
        hits = [o for o in options
                if pick in o["name"].lower() or pick in o["fqbn"].lower()]
        if len(hits) == 1:
            print(f"   ✔  {hits[0]['name']}")
            return hits[0]
        elif len(hits) > 1:
            print("   Multiple matches:")
            for i, h in enumerate(hits, 1):
                print(f"      {i}. {h['name']}")
        else:
            if "raspberry" in pick and "pico" not in pick:
                print("   ℹ️  The standard Raspberry Pi runs Linux and cannot be")
                print("      programmed with Arduino. Did you mean 'Raspberry Pi Pico'?")
            else:
                print(f"   No match for '{pick}'. Try a number or different keyword.")

def detect_board() -> dict:
    print("\n🔍 Scanning for connected boards...")

    try:
        r = subprocess.run(
            ["arduino-cli","board","list","--format","json"],
            capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            data    = json.loads(r.stdout)
            entries = data.get("detected_ports", data) if isinstance(data,dict) else data
            if not isinstance(entries, list): entries = []
            for entry in entries:
                p    = entry.get("port",{})
                port = p.get("address","") if isinstance(p,dict) else str(p)
                if not port: continue
                boards = entry.get("matching_boards", entry.get("boards",[]))
                if boards and boards[0].get("fqbn","") not in ("","unknown"):
                    fqbn = boards[0]["fqbn"]
                    name = boards[0].get("name", fqbn)
                    print(f"   ✅ Identified: {name}")
                    for row in _DB.get("usb_fingerprints",[]):
                        if row["fqbn"] == fqbn:
                            return {"port":port,"fqbn":fqbn,"name":name,
                                    "upload_speed":row["upload_speed"],
                                    "upload_method":row["upload_method"]}
                    return {"port":port,"fqbn":fqbn,"name":name,
                            "upload_speed":None,"upload_method":"arduino-cli"}
                elif port:
                    print(f"   🔍 Port {port} found, fingerprinting...")
                    candidates = _fingerprint(port)
                    if len(candidates) == 1:
                        c = candidates[0]; c["port"] = port
                        print(f"   ✅ Identified: {c['name']}")
                        return c
                    print(f"   ⚠️  Multiple boards match this USB chip.")
                    chosen = _manual_select(port, candidates)
                    chosen["port"] = port
                    return chosen
    except Exception:
        pass

    ports = list_serial_ports()
    if ports:
        port       = ports[0]
        candidates = _fingerprint(port)
        if len(candidates) == 1:
            c = candidates[0]; c["port"] = port
            print(f"   ✅ Identified: {c['name']}")
            return c
        if candidates:
            print(f"   ⚠️  Multiple boards match.")
        chosen = _manual_select(port, candidates)
        chosen["port"] = port
        return chosen

    print("   ⚠️  No board found. Make sure it's plugged in.")
    chosen = _manual_select("unknown", [])
    chosen["port"] = None
    return chosen


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Core Installation
# ══════════════════════════════════════════════════════════════════════════════

def ensure_core(fqbn: str):
    parts = fqbn.split(":")
    if len(parts) < 2: return
    platform_id = f"{parts[0]}:{parts[1]}"
    r = subprocess.run(["arduino-cli","core","list"], capture_output=True, text=True)
    if platform_id in r.stdout: return
    print(f"\n📦 Installing core '{platform_id}' (first time only)...")
    url = _DB.get("_meta",{}).get("board_manager_urls",{}).get(parts[0])
    if url:
        subprocess.run(["arduino-cli","config","init","--overwrite"], capture_output=True)
        subprocess.run(["arduino-cli","config","add",
                        "board_manager.additional_urls", url], capture_output=True)
    subprocess.run(["arduino-cli","core","update-index"], capture_output=True)
    r = subprocess.run(["arduino-cli","core","install", platform_id])
    print(f"   {'✅' if r.returncode==0 else '⚠️ '} Core '{platform_id}' "
          f"{'installed' if r.returncode==0 else 'install may have failed'}.\n")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — AI Code Generation
# ══════════════════════════════════════════════════════════════════════════════

class AIAgent:
    def __init__(self, board: dict):
        self.board    = board
        self.messages = [{"role":"system","content": self._build_prompt()}]

    def _build_prompt(self) -> str:
        fqbn  = self.board["fqbn"]
        name  = self.board["name"]
        rules = get_pin_rules(fqbn, name)

        safe_pins     = ", ".join(rules.get("safe",[])[:15]) or "standard GPIO pins"
        reserved_text = "\n".join(
            f"  - {pin}: {reason} → use {alt} instead"
            for pin, (reason, alt) in rules.get("reserved",{}).items()
        ) or "  None"

        if "esp8266" in fqbn:
            naming = "D-prefix: D1, D2, D5, D6, D7  (NOT GPIO numbers)"
        elif "esp32" in fqbn:
            naming = "GPIO numbers: GPIO4, GPIO5, GPIO13..."
        elif "avr" in fqbn:
            naming = "Plain integers: 2, 3, 13  (NOT D2, D13)"
        elif "rp2040" in fqbn:
            naming = "GP prefix: GP0, GP1, GP2..."
        else:
            naming = "Labels as printed on the board silkscreen"

        return f"""You are an expert embedded engineer programming the {name} ({fqbn}).

## OUTPUT FORMAT — always follow exactly:
1. Complete Arduino C++ sketch in ```cpp ... ``` block.
   No placeholders, no TODOs — fully working code only.

2. Wiring table:
WIRING_START
Component | Component Pin | Board Label | Notes
LED | Anode (+) | D1 | Through 220Ω resistor
WIRING_END

## PIN NAMING for {name}:
{naming}

## SAFE PINS (use these):
{safe_pins}

## RESERVED PINS — NEVER use for components:
{reserved_text}

## BOARD NOTE:
{rules.get('note','')}

## RULES:
- Use ONLY safe pins
- {'Use #include <ESP8266WiFi.h>' if 'esp8266' in fqbn else 'Use #include <WiFi.h>' if 'esp32' in fqbn else 'No WiFi on this board'}
- 2 sentence explanation max — code and wiring table are the priority
"""

    def ask(self, prompt: str) -> str | None:
        self.messages.append({"role":"user","content":prompt})
        text = ai_ask(self.messages)
        if text:
            self.messages.append({"role":"assistant","content":text})
        return text


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Code Sanitization
# ══════════════════════════════════════════════════════════════════════════════

def extract_code(text: str) -> str:
    for marker in ("```cpp","```arduino","```c","```"):
        if marker in text:
            return text.split(marker)[1].split("```")[0].strip()
    return text.strip()

def sanitize_code(code: str, board: dict) -> str:
    fqbn  = board["fqbn"]
    rules = get_pin_rules(fqbn, board.get("name",""))

    for wrong, correct in rules.get("code_fixes",{}).items():
        code = code.replace(wrong, correct)
    for h in ["#include <WiFi.h>","#include <ESP8266WiFi.h>"]:
        if h in code and "WiFi." not in code.replace(h,""):
            code = code.replace(h, "")

    if "avr" in fqbn:
        code = re.sub(r'\bD(\d+)\b', r'\1', code)
    if "esp32" in fqbn and "esp8266" not in fqbn:
        code = re.sub(r'\bD(\d+)\b', r'\1', code)

    for bad_pin, (reason, good_pin) in rules.get("reserved",{}).items():
        fp = rf'((?:digitalWrite|digitalRead|pinMode|analogWrite|analogRead)\s*\(\s*){re.escape(bad_pin)}(\s*[,)])'
        ap = rf'((?:=|#define\s+\w+)\s*){re.escape(bad_pin)}\b'
        if re.search(fp, code) or re.search(ap, code):
            print(f"\n   ⚠️  WARNING: Pin {bad_pin} is reserved!")
            print(f"      Reason : {reason}")
            print(f"      Safe alternative: {good_pin}")
            print(f"      Risk   : May cause boot issues or programming failures")
            choice = smart_input(f"      Replace {bad_pin} → {good_pin}? [Y/n]: ").lower()
            if choice != "n":
                code = re.sub(fp, rf'\g<1>{good_pin}\2', code)
                code = re.sub(ap, rf'\g<1>{good_pin}',   code)
                print(f"      ✅ Replaced {bad_pin} → {good_pin}")
            else:
                print(f"      ⚡ Keeping {bad_pin} — proceed with caution.")

    write_pins = re.findall(r'digitalWrite\s*\(\s*(\w+)\s*,', code)
    read_pins  = re.findall(r'digitalRead\s*\(\s*(\w+)\s*\)', code)
    all_pins   = list(dict.fromkeys(write_pins + read_pins))
    setup_m    = re.search(r'void\s+setup\s*\(\s*\)\s*\{([^}]*)\}', code, re.DOTALL)
    if setup_m and all_pins:
        body, adds = setup_m.group(1), []
        for pin in all_pins:
            if f"pinMode({pin}" not in body:
                d = "OUTPUT" if pin in write_pins else "INPUT"
                adds.append(f"  pinMode({pin}, {d});")
        if adds:
            nb = body.rstrip() + "\n" + "\n".join(adds) + "\n"
            code = code[:setup_m.start(1)] + nb + code[setup_m.end(1):]
    return code


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Compile with AI Auto-Fix
# ══════════════════════════════════════════════════════════════════════════════

def auto_install_libraries(code: str):
    includes = re.findall(r'#include\s*[<"]([^>"]+)[>"]', code)

    builtin = {
        "Arduino.h","Wire.h","SPI.h","EEPROM.h","Servo.h",
        "SoftwareSerial.h","LiquidCrystal.h","SD.h","Stepper.h",
        "WiFi.h","WiFiClient.h","WiFiServer.h","WebServer.h",
        "ESP8266WiFi.h","ESP8266WebServer.h","HTTPClient.h",
        "BluetoothSerial.h","BLEDevice.h","Preferences.h",
        "FS.h","SPIFFS.h","LittleFS.h","Update.h",
        "math.h","string.h","stdlib.h","stdio.h",
    }

    lib_map = {
        "DHT.h":              "DHT sensor library",
        "DHT_U.h":            "DHT sensor library",
        "Adafruit_Sensor.h":  "Adafruit Unified Sensor",
        "Adafruit_BMP280.h":  "Adafruit BMP280 Library",
        "Adafruit_BME280.h":  "Adafruit BME280 Library",
        "Adafruit_MPU6050.h": "Adafruit MPU6050",
        "Adafruit_GFX.h":     "Adafruit GFX Library",
        "Adafruit_SSD1306.h": "Adafruit SSD1306",
        "Adafruit_ILI9341.h": "Adafruit ILI9341",
        "Adafruit_NeoPixel.h":"Adafruit NeoPixel",
        "LiquidCrystal_I2C.h":"LiquidCrystal I2C",
        "FastLED.h":          "FastLED",
        "IRremote.h":         "IRremote",
        "IRremoteESP8266.h":  "IRremote",
        "PubSubClient.h":     "PubSubClient",
        "ArduinoJson.h":      "ArduinoJson",
        "RTClib.h":           "RTClib",
        "OneWire.h":          "OneWire",
        "DallasTemperature.h":"DallasTemperature",
        "Ultrasonic.h":       "Ultrasonic",
        "NewPing.h":          "NewPing",
        "Keypad.h":           "Keypad",
        "TM1637Display.h":    "TM1637",
        "MAX30105.h":         "SparkFun MAX3010x Pulse and Proximity Sensor Library",
        "MPU6050.h":          "MPU6050",
        "HX711.h":            "HX711",
        "Stepper.h":          "Stepper",
        "AccelStepper.h":     "AccelStepper",
        "ESP32Servo.h":       "ESP32Servo",
        "ESPAsyncWebServer.h":"ESPAsyncWebServer-esphome",
        "AsyncTCP.h":         "AsyncTCP",
        "MQTT.h":             "MQTT",
        "Ticker.h":           "Ticker",
    }

    to_install = []
    for inc in includes:
        if inc in builtin: continue
        lib_name = lib_map.get(inc)
        if lib_name:
            to_install.append((inc, lib_name))

    if not to_install:
        return

    print(f"\n   📚 Found {len(to_install)} library/ies to install:")
    for inc, lib in to_install:
        print(f"      {inc} → {lib}")

    r = subprocess.run(["arduino-cli","lib","list"],
                       capture_output=True, text=True)
    installed = r.stdout.lower()

    for inc, lib in to_install:
        if lib.lower() in installed:
            print(f"      ✅ {lib} already installed")
            continue
        print(f"      📦 Installing {lib}...", end="", flush=True)
        r = subprocess.run(
            ["arduino-cli","lib","install", lib],
            capture_output=True, text=True
        )
        if r.returncode == 0:
            print(" ✅")
        else:
            search = subprocess.run(
                ["arduino-cli","lib","search", inc.replace(".h",""),"--format","json"],
                capture_output=True, text=True
            )
            try:
                results = json.loads(search.stdout)
                libs    = results.get("libraries", results) if isinstance(results,dict) else results
                if libs:
                    best = libs[0].get("name","") if isinstance(libs[0],dict) else ""
                    if best:
                        r2 = subprocess.run(
                            ["arduino-cli","lib","install", best],
                            capture_output=True, text=True
                        )
                        print(f" {'✅' if r2.returncode==0 else '⚠️ failed'}")
                    else:
                        print(" ⚠️ not found")
                else:
                    print(" ⚠️ not found in registry")
            except Exception:
                print(" ⚠️ install failed")


def compile_sketch(fqbn: str) -> tuple:
    build_dir = os.path.join(SKETCH_DIR, "build")
    os.makedirs(build_dir, exist_ok=True)
    r = subprocess.run(
        ["arduino-cli","compile","--fqbn",fqbn,"--output-dir",build_dir, SKETCH_DIR],
        capture_output=True, text=True)
    return r.returncode == 0, r.stderr + r.stdout

def compile_with_autofix(code: str, board: dict) -> bool:
    fqbn = board["fqbn"]
    hints = {
        "esp8266": "Use #include <ESP8266WiFi.h>, D-prefix pins (D1,D2,D5,D6,D7), 3.3V.",
        "esp32":   "Use #include <WiFi.h>, GPIO numbers, 3.3V.",
        "avr":     "Plain pin numbers (13 not D13), 5V logic.",
        "rp2040":  "GP prefix (GP0,GP1...), 3.3V, Arduino-Pico framework.",
    }
    hint    = next((v for k,v in hints.items() if k in fqbn), f"Board: {board['name']}")
    current = code

    auto_install_libraries(current)

    for attempt in range(3):
        os.makedirs(SKETCH_DIR, exist_ok=True)
        sketch_file = os.path.join(SKETCH_DIR, os.path.basename(SKETCH_DIR)+".ino")
        with open(sketch_file,"w") as f: f.write(current)

        ok, output = compile_sketch(fqbn)
        for line in output.splitlines():
            if any(k in line for k in ("Sketch uses","Global variables","error:","warning:")):
                print(f"   {line.strip()}")
        if ok:
            if attempt > 0: print(f"   ✅ Fixed on attempt {attempt+1}")
            return True

        errors = [l.strip() for l in output.splitlines() if "error:" in l.lower()][:6]
        if not errors: break
        print(f"   🔧 [{attempt+1}/3] AI fixing {len(errors)} error(s)...")
        try:
            fixed = ai_ask([{"role":"user","content":(
                f"Fix this Arduino code for {board['name']} ({fqbn}).\n"
                f"Errors:\n" + "\n".join(errors) +
                f"\nRules: {hint}\n"
                f"Code:\n```cpp\n{current}\n```\n"
                "Return ONLY fixed code in ```cpp block."
            )}], timeout=120)
            fixed = extract_code(fixed) if fixed else None
            if fixed and fixed != current: current = fixed
            else: break
        except Exception: break

    print("❌ Compilation failed after all attempts.")
    return False


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — Universal Upload
# ══════════════════════════════════════════════════════════════════════════════

def _dtr_reset(port: str):
    try:
        import serial
        with serial.Serial(port, 115200, timeout=0.5) as s:
            s.dtr = False; time.sleep(0.1)
            s.dtr = True;  time.sleep(0.1)
            s.dtr = False; time.sleep(0.25)
    except Exception:
        if IS_LINUX:
            try:
                subprocess.run(["stty","-F",port,"hupcl"], capture_output=True)
                time.sleep(0.3)
            except Exception: pass

def _find_file(root: str, exts: list, exclude: list=[]) -> str:
    for r, _, files in os.walk(root):
        for f in sorted(files):
            if any(f.endswith(e) for e in exts):
                if not any(x in f.lower() for x in exclude):
                    return os.path.join(r, f)
    return ""

def _find_avrdude() -> tuple:
    roots = [os.path.join(HOME,".arduino15","packages","arduino","tools","avrdude")]
    if IS_LINUX:
        roots.append("/root/.arduino15/packages/arduino/tools/avrdude")
    avrdude = conf = ""
    for base in roots:
        if not os.path.exists(base): continue
        for r, _, files in os.walk(base):
            exe = "avrdude.exe" if IS_WINDOWS else "avrdude"
            if exe in files and not avrdude:
                avrdude = os.path.join(r, exe)
            if "avrdude.conf" in files and not conf:
                conf = os.path.join(r, "avrdude.conf")
    return avrdude or "avrdude", conf or "/etc/avrdude.conf"

def _upload_avrdude(port: str, fqbn: str, baud: int) -> tuple:
    hex_file = _find_file(os.path.join(SKETCH_DIR,"build"), [".hex"], ["bootloader"])
    if not hex_file: return False, "No .hex file found"
    mcu = "atmega2560" if "mega" in fqbn else "atmega328p"
    avrdude, conf = _find_avrdude()
    _dtr_reset(port)
    time.sleep(0.15)
    r = subprocess.run([avrdude,"-C",conf,"-p",mcu,"-c","arduino",
                        "-P",port,"-b",str(baud),"-D",f"-Uflash:w:{hex_file}:i"],
                       capture_output=True, text=True)
    return r.returncode == 0, r.stderr + r.stdout

def _upload_esptool(port: str, fqbn: str) -> tuple:
    chip  = "esp8266" if "esp8266" in fqbn else "esp32"
    build = os.path.join(SKETCH_DIR, "build")
    bin_file = ""
    for root, _, files in os.walk(build):
        if chip == "esp8266" and "esp32" in root and "esp8266" not in root: continue
        if chip == "esp32"   and "esp8266" in root: continue
        for f in sorted(files):
            if f.endswith(".bin") and not any(x in f.lower() for x in
               ["bootloader","partition","boot_app","merged"]):
                bin_file = os.path.join(root, f); break
        if bin_file: break
    if not bin_file:
        return _upload_arduino_cli(port, fqbn, False)
    if subprocess.run(["python3","-m","esptool","version"],
                      capture_output=True).returncode != 0:
        print("   📦 Installing esptool...")
        subprocess.run(["pip","install","esptool","--break-system-packages","-q"],
                       capture_output=True)
    r = subprocess.run([
        sys.executable,"-m","esptool",
        "--chip",chip,"--port",port,"--baud","921600",
        "--before","default_reset","--after","hard_reset",
        "write_flash","--flash_mode","dio",
        "0x10000" if chip=="esp32" else "0x0", bin_file
    ], capture_output=True, text=True)
    return r.returncode == 0, r.stderr + r.stdout

def _upload_arduino_cli(port: str, fqbn: str, use_sudo: bool) -> tuple:
    cmd = []
    if use_sudo and IS_LINUX: cmd = ["sudo"]
    cmd += ["arduino-cli","upload","-p",port,"--fqbn",fqbn, SKETCH_DIR]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0, r.stderr + r.stdout

def _upload_uf2(port: str, fqbn: str) -> tuple:
    uf2 = _find_file(os.path.join(SKETCH_DIR,"build"), [".uf2"])
    if not uf2: return False, "No .uf2 file — put board in BOOTSEL mode and retry"
    mounts = []
    if IS_WINDOWS:
        for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
            m = f"{letter}:\\"
            if os.path.exists(m) and os.path.exists(os.path.join(m,"INFO_UF2.TXT")):
                mounts.append(m)
    elif IS_MAC:
        import glob
        mounts = glob.glob("/Volumes/RPI-RP2*")
    else:
        import glob
        mounts = (glob.glob("/media/*/RPI-RP2*") +
                  glob.glob("/run/media/*/RPI-RP2*") +
                  glob.glob("/media/RPI-RP2*"))
    if mounts:
        import shutil
        shutil.copy2(uf2, mounts[0])
        return True, "UF2 copied"
    return False, ("Board not in BOOTSEL mode. Hold BOOTSEL while plugging USB, "
                   "then type 'redeploy'.")

def _upload_dfu(port: str, fqbn: str) -> tuple:
    bin_file = _find_file(os.path.join(SKETCH_DIR,"build"), [".bin"])
    if not bin_file: return False, "No .bin file"
    r = subprocess.run(["dfu-util","-a","0","--dfuse-address","0x08000000",
                        "-D",bin_file], capture_output=True, text=True)
    return r.returncode == 0, r.stderr + r.stdout

def _upload_bossac(port: str, fqbn: str) -> tuple:
    ok, err = _upload_arduino_cli(port, fqbn, False)
    if ok: return ok, err
    bin_file = _find_file(os.path.join(SKETCH_DIR,"build"), [".bin"])
    if not bin_file: return False, "No .bin file"
    r = subprocess.run(["bossac","-p",os.path.basename(port),"-e","-w","-v","-b",bin_file],
                       capture_output=True, text=True)
    return r.returncode == 0, r.stderr + r.stdout

def upload(board: dict) -> bool:
    port   = board.get("port","")
    fqbn   = board["fqbn"]
    method = board.get("upload_method","arduino-cli")
    hint   = board.get("upload_speed")

    if method == "avrdude":
        bauds = ([hint] if hint else []) + [b for b in AVR_BAUDS if b != hint]
        strategies = [("avrdude",b) for b in bauds if b]
        strategies += [("arduino-cli",None),("arduino-cli-sudo",None)]
    elif method == "esptool":
        strategies = [("esptool",None),("arduino-cli",None),("arduino-cli-sudo",None)]
    elif method == "uf2":
        strategies = [("uf2",None)]
    elif method == "dfu":
        strategies = [("dfu",None),("arduino-cli",None)]
    elif method == "bossac":
        strategies = [("bossac",None),("arduino-cli",None)]
    else:
        strategies = [("arduino-cli",None),("arduino-cli-sudo",None)]

    print(f"\n🚀 Uploading to {board['name']} on {port}...")

    for i, (strat, baud) in enumerate(strategies):
        if port and not os.path.exists(port) and not IS_WINDOWS:
            ports = list_serial_ports()
            if ports:
                print(f"   🔌 Port changed → {ports[0]}")
                board["port"] = ports[0]; port = ports[0]

        label = strat + (f" @{baud}" if baud else "")
        print(f"   [{i+1}/{len(strategies)}] {label}... ", end="", flush=True)

        if   strat == "avrdude":          ok, err = _upload_avrdude(port, fqbn, baud)
        elif strat == "esptool":          ok, err = _upload_esptool(port, fqbn)
        elif strat == "uf2":              ok, err = _upload_uf2(port, fqbn)
        elif strat == "dfu":              ok, err = _upload_dfu(port, fqbn)
        elif strat == "bossac":           ok, err = _upload_bossac(port, fqbn)
        elif strat == "arduino-cli-sudo": ok, err = _upload_arduino_cli(port, fqbn, True)
        else:                             ok, err = _upload_arduino_cli(port, fqbn, False)

        if ok:
            print("✅")
            print("✅ Upload successful! Hardware is live.\n")
            return True

        if "this chip is esp8266" in err.lower() and "esp32" in fqbn:
            print("✗\n   🔧 Auto-correcting ESP32→ESP8266...")
            board.update({"fqbn":"esp8266:esp8266:nodemcuv2",
                          "name":"NodeMCU ESP8266","upload_method":"esptool"})
            ensure_core(board["fqbn"])
            return False
        if "this chip is esp32" in err.lower() and "esp8266" in fqbn:
            print("✗\n   🔧 Auto-correcting ESP8266→ESP32...")
            board.update({"fqbn":"esp32:esp32:esp32",
                          "name":"ESP32 DevKit","upload_method":"esptool"})
            ensure_core(board["fqbn"])
            return False

        err_line = next((l.strip() for l in err.splitlines()
                         if any(k in l.lower() for k in
                                ("error","fatal","unable","denied","not in sync","no such"))), "")
        print(f"✗  ({err_line[:70]})" if err_line else "✗")

    print("\n❌ Upload failed. Diagnosing...")
    _diagnose(board)
    return False

def _diagnose(board: dict):
    port, issues = board.get("port",""), []
    if IS_WINDOWS:
        ports = list_serial_ports()
        if not ports:
            issues.append("No COM port found. Check Device Manager → Ports.")
        else:
            issues.append(f"Available ports: {', '.join(ports)} — try 'redeploy'")
            board["port"] = ports[0]
    else:
        if not port or not os.path.exists(port):
            found = list_serial_ports()
            if found:
                issues.append(f"Port changed → {found[0]} — type 'redeploy'")
                board["port"] = found[0]
            else:
                issues.append("No serial port. Is the board plugged in?")
        else:
            r = subprocess.run(["test","-w",port], capture_output=True)
            if r.returncode != 0:
                issues.append(f"No permission on {port} → sudo usermod -aG dialout $USER")

    method = board.get("upload_method","")
    if method == "uf2":
        issues.append("Hold BOOTSEL while plugging USB, then type 'redeploy'")
    if method == "dfu":
        issues.append("Set BOOT0=HIGH, press RESET for DFU mode, then type 'redeploy'")

    for issue in (issues or ["Try a different USB cable or port"]):
        print(f"   ⚠️  {issue}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — Wiring Diagram
# ══════════════════════════════════════════════════════════════════════════════

def parse_wiring(text: str) -> list[dict]:
    rows, inside = [], False
    for line in text.splitlines():
        if "WIRING_START" in line: inside = True; continue
        if "WIRING_END"   in line: break
        if inside and "|" in line and "---" not in line and "Component" not in line:
            p = [x.strip() for x in line.split("|") if x.strip()]
            if len(p) >= 3:
                rows.append({"component":p[0],"comp_pin":p[1],
                             "board_pin":p[2],"notes":p[3] if len(p)>3 else ""})
    return rows

_diagram_server = None
_diagram_port   = 7890

def _start_diagram_server():
    global _diagram_server
    if _diagram_server:
        return

    import http.server, threading, socketserver

    class _Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/" or self.path == "/index.html":
                self.path = "/" + os.path.basename(DIAGRAM_FILE)
            if self.path.endswith(".html"):
                try:
                    with open(DIAGRAM_FILE, "rb") as f:
                        content = f.read()
                    inject = b"""<script>
                        let lastMod = null;
                        setInterval(async () => {
                            const r = await fetch('/ping?' + Date.now());
                            const mod = r.headers.get('X-Last-Modified');
                            if (lastMod && mod !== lastMod) location.reload();
                            lastMod = mod;
                        }, 2000);
                    </script>"""
                    content = content.replace(b"</body>", inject + b"</body>")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)
                except Exception:
                    super().do_GET()
            elif self.path.startswith("/ping"):
                try:
                    mtime = str(os.path.getmtime(DIAGRAM_FILE))
                except Exception:
                    mtime = "0"
                self.send_response(200)
                self.send_header("X-Last-Modified", mtime)
                self.end_headers()
            else:
                super().do_GET()

        def log_message(self, *args): pass

    os.chdir(os.path.dirname(DIAGRAM_FILE) or HOME)
    try:
        server = socketserver.TCPServer(("127.0.0.1", _diagram_port), _Handler)
        server.allow_reuse_address = True
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        _diagram_server = server
    except OSError:
        pass


def generate_diagram(board: dict, rows: list[dict], task: str):
    colors = ["#00ff88","#ff6b6b","#ffd93d","#6bcbff","#c084fc","#fb923c","#34d399"]
    trs = ""
    for i, r in enumerate(rows):
        c = colors[i % len(colors)]
        trs += (f'<tr><td><span class="cb">{r["component"]}</span></td>'
                f'<td><span class="pb cp">{r["comp_pin"]}</span></td>'
                f'<td class="arr">──▶</td>'
                f'<td><span class="pb bp" style="border-color:{c};color:{c}">{r["board_pin"]}</span></td>'
                f'<td class="nt">{r["notes"]}</td></tr>')
    warn = ('<div class="wb">⚠️ <span>3.3V logic only — do NOT connect 5V signals to GPIO</span></div>'
            if any(x in board["fqbn"] for x in ("esp","rp2040","samd","sam")) else "")

    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>Wiring — {board['name']}</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Space+Grotesk:wght@400;600;700&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0a0e1a;color:#e2e8f0;font-family:'Space Grotesk',sans-serif;min-height:100vh;padding:40px 20px}}
body::before{{content:'';position:fixed;inset:0;background-image:linear-gradient(rgba(0,255,136,.03) 1px,transparent 1px),linear-gradient(90deg,rgba(0,255,136,.03) 1px,transparent 1px);background-size:40px 40px;pointer-events:none;z-index:0}}
.w{{max-width:900px;margin:0 auto;position:relative;z-index:1}}
header{{margin-bottom:40px;border-left:3px solid #00ff88;padding-left:20px}}
.lbl{{font-family:'JetBrains Mono',monospace;font-size:11px;color:#00ff88;letter-spacing:3px;text-transform:uppercase;margin-bottom:8px}}
h1{{font-size:26px;font-weight:700;color:#fff}}
.tag{{display:inline-block;margin-top:12px;background:rgba(0,255,136,.1);border:1px solid rgba(0,255,136,.3);color:#00ff88;font-family:'JetBrains Mono',monospace;font-size:12px;padding:4px 12px;border-radius:4px}}
.card{{background:#111827;border:1px solid #1f2d45;border-radius:12px;overflow:hidden;margin-bottom:24px}}
.ch{{padding:16px 24px;border-bottom:1px solid #1f2d45;display:flex;align-items:center;gap:10px}}
.dot{{width:8px;height:8px;border-radius:50%;background:#00ff88;box-shadow:0 0 8px #00ff88;animation:pulse 2s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
.ct{{font-weight:600;font-size:14px}}
table{{width:100%;border-collapse:collapse}}
th{{font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#64748b;padding:12px 24px;text-align:left;border-bottom:1px solid #1f2d45}}
td{{padding:14px 24px;border-bottom:1px solid rgba(31,45,69,.5);font-size:14px;vertical-align:middle}}
tr:last-child td{{border-bottom:none}}tr:hover td{{background:rgba(255,255,255,.02)}}
.cb{{background:rgba(255,255,255,.05);border:1px solid #1f2d45;padding:3px 10px;border-radius:4px;font-weight:600}}
.pb{{font-family:'JetBrains Mono',monospace;font-size:12px;padding:3px 10px;border-radius:4px;border:1px solid;display:inline-block}}
.cp{{border-color:#64748b;color:#e2e8f0}}.bp{{font-weight:700}}.arr{{color:#64748b;font-family:'JetBrains Mono',monospace}}.nt{{color:#64748b;font-size:12px;font-style:italic}}
.wb{{background:rgba(251,146,60,.08);border:1px solid rgba(251,146,60,.3);border-radius:8px;padding:14px 20px;font-size:13px;color:#fb923c;display:flex;gap:10px}}
footer{{margin-top:40px;text-align:center;color:#64748b;font-size:12px;font-family:'JetBrains Mono',monospace}}
</style></head><body><div class="w">
<header><div class="lbl">VibeCoder v6.1 — Wiring Diagram</div>
<h1>{task}</h1><div class="tag">🔌 {board['name']}</div></header>
<div class="card"><div class="ch"><div class="dot"></div><span class="ct">Connection Guide</span></div>
<table><thead><tr><th>Component</th><th>Pin</th><th></th><th>Board</th><th>Notes</th></tr></thead>
<tbody>{trs}</tbody></table></div>{warn}
<footer>VibeCoder v6.1 · {board['name']} · {time.strftime('%Y-%m-%d %H:%M')}</footer>
</div></body></html>"""

    with open(DIAGRAM_FILE, "w") as f:
        f.write(html)

    _start_diagram_server()
    url = f"http://127.0.0.1:{_diagram_port}/"

    if not getattr(generate_diagram, "_opened", False):
        try:
            webbrowser.open(url)
            generate_diagram._opened = True
            print(f"   📊 Wiring diagram → {url}  (auto-updates on redeploy)")
        except Exception:
            print(f"   📊 Open in browser: {url}")
    else:
        print(f"   📊 Wiring diagram updated (live reload)")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8b — Project History
# ══════════════════════════════════════════════════════════════════════════════

def _load_index() -> list:
    try:
        with open(HISTORY_INDEX) as f:
            return json.load(f)
    except Exception:
        return []

def _save_index(index: list):
    os.makedirs(HISTORY_DIR, exist_ok=True)
    with open(HISTORY_INDEX, "w") as f:
        json.dump(index, f, indent=2)

def save_project(task: str, code: str, wiring_rows: list, board: dict):
    os.makedirs(HISTORY_DIR, exist_ok=True)
    ts       = time.strftime("%Y%m%d_%H%M%S")
    safe     = re.sub(r"[^\w\s-]", "", task.lower())[:40].strip().replace(" ","_")
    proj_id  = f"{ts}_{safe}"
    proj_dir = os.path.join(HISTORY_DIR, proj_id)
    os.makedirs(proj_dir, exist_ok=True)
    with open(os.path.join(proj_dir, "sketch.ino"), "w") as f:
        f.write(code)
    with open(os.path.join(proj_dir, "wiring.json"), "w") as f:
        json.dump(wiring_rows, f, indent=2)
    meta = {
        "id":         proj_id,
        "task":       task,
        "board":      board.get("name",""),
        "fqbn":       board.get("fqbn",""),
        "timestamp":  time.strftime("%Y-%m-%d %H:%M:%S"),
        "code_lines": len(code.splitlines()),
    }
    with open(os.path.join(proj_dir, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    index = _load_index()
    index.append(meta)
    _save_index(index)
    print(f"   Project saved: {proj_id}")
    return proj_dir

def show_history():
    index = _load_index()
    if not index:
        print("\n   No projects saved yet.")
        return
    recent = list(reversed(index))[:20]
    sep = "-" * 72
    print("\n" + sep)
    print(f"  {'#':<4} {'Date':<20} {'Board':<22} Task")
    print(sep)
    for i, p in enumerate(recent, 1):
        ts  = p.get("timestamp","")[:19]
        brd = p.get("board","")[:20]
        tsk = p.get("task","")[:28]
        print(f"  {i:<4} {ts:<20} {brd:<22} {tsk}")
    print(sep)
    print(f"  {len(index)} total projects saved in {HISTORY_DIR}\n")

def load_project(pick: str) -> dict | None:
    index = _load_index()
    if not index:
        print("   No history yet.")
        return None
    recent = list(reversed(index))[:20]
    if pick.isdigit() and 1 <= int(pick) <= len(recent):
        meta = recent[int(pick)-1]
    else:
        hits = [p for p in index if pick.lower() in p.get("task","").lower()]
        if not hits:
            print(f"   No project matching '{pick}'.")
            return None
        meta = hits[-1]
    proj_dir = os.path.join(HISTORY_DIR, meta["id"])
    try:
        code   = open(os.path.join(proj_dir, "sketch.ino")).read()
        wiring = json.load(open(os.path.join(proj_dir, "wiring.json")))
        print(f"   Loaded: {meta['task']} ({meta['timestamp']})")
        return {"meta": meta, "code": code, "wiring": wiring}
    except Exception as e:
        print(f"   Could not load: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8c — Serial Monitor
# ══════════════════════════════════════════════════════════════════════════════

def serial_monitor(port: str, baud: int = 115200):
    try:
        import serial
        import serial.tools.list_ports
        import threading
    except ImportError:
        print("   Installing pyserial...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyserial", "-q"])
        import serial
        import threading

    if not port or not os.path.exists(port) and not IS_WINDOWS:
        ports = list_serial_ports()
        if not ports:
            print("   No serial port found. Is your board connected?")
            return
        port = ports[0]
        print(f"   Using port: {port}")

    bauds_to_try = [baud, 115200, 9600, 57600, 38400, 4800]

    ser = None
    for b in bauds_to_try:
        try:
            ser = serial.Serial(port, b, timeout=0.1)
            print(f"\n   Serial Monitor — {port} @ {b} baud")
            print("   Press Ctrl+C to exit. Type messages and press Enter to send.")
            print("   " + "─"*50)
            break
        except Exception:
            ser = None
            continue

    if not ser:
        print(f"   Could not open {port}. Try a different baud rate.")
        return

    stop_flag = threading.Event()

    def _reader():
        buf = b""
        while not stop_flag.is_set():
            try:
                chunk = ser.read(64)
                if chunk:
                    buf += chunk
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        text = line.decode("utf-8", errors="replace").rstrip()
                        if text:
                            print(f"\r   \033[36m{text}\033[0m")
            except Exception:
                break

    reader_thread = threading.Thread(target=_reader, daemon=True)
    reader_thread.start()

    try:
        while True:
            msg = smart_input("")
            if msg:
                try:
                    ser.write((msg + "\n").encode("utf-8"))
                except Exception:
                    print("   Write error — board may have disconnected.")
                    break
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        stop_flag.set()
        reader_thread.join(timeout=1)
        try:
            ser.close()
        except Exception:
            pass
        print("\n   Serial monitor closed.")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — Deploy Pipeline
# ══════════════════════════════════════════════════════════════════════════════

def deploy(response: str, board: dict, task: str):
    code = extract_code(response)
    code = sanitize_code(code, board)

    os.makedirs(SKETCH_DIR, exist_ok=True)
    sketch_file = os.path.join(SKETCH_DIR, os.path.basename(SKETCH_DIR)+".ino")
    with open(sketch_file,"w") as f: f.write(code)
    print(f"\n💾 Sketch saved → {sketch_file}")

    rows = parse_wiring(response)
    if rows: generate_diagram(board, rows, task)
    else:    print("⚠️  No wiring table in AI response.")

    print(f"\n🔨 Compiling for {board['name']}...")
    if not compile_with_autofix(code, board):
        return

    ok = upload(board)
    if not ok and board.get("fqbn") not in (board.get("_orig_fqbn",""), ""):
        print(f"\n Recompiling for corrected board: {board['name']}...")
        code = sanitize_code(code, board)
        with open(sketch_file,"w") as f: f.write(code)
        if compile_with_autofix(code, board):
            ok = upload(board)

    if ok:
        save_project(task, code, rows, board)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — Startup & Main
# ══════════════════════════════════════════════════════════════════════════════

def _ensure_deps():
    deps = {"requests": "requests", "serial": "pyserial"}
    if not _HAS_PT:
        deps["prompt_toolkit"] = "prompt_toolkit"

    missing = []
    for mod, pkg in deps.items():
        try: __import__(mod)
        except ImportError: missing.append(pkg)

    if missing:
        print(f"   📦 Installing: {', '.join(missing)}...")
        flags = ["--break-system-packages"] if IS_LINUX or IS_MAC else []
        subprocess.run([sys.executable,"-m","pip","install","-q"] + flags + missing)
        print("   ✅ Done. Restart if you see import errors.")


def _install_arduino_cli_windows():
    """
    Install arduino-cli on Windows.
    Strategy:
      1. winget  (Windows 10 1709+ — most reliable)
      2. GitHub Releases ZIP (manual download + extract)
      3. Print manual instructions and exit
    """
    # ── Strategy 1: winget ───────────────────────────────────────────────────
    print("   Trying winget...")
    try:
        r = subprocess.run(
            ["winget", "install", "--id", "Arduino.ArduinoCLI",
             "--accept-source-agreements", "--accept-package-agreements",
             "--silent"],
            timeout=120
        )
        if r.returncode == 0:
            # winget installs to %LOCALAPPDATA%\Microsoft\WinGet\Packages\ or
            # C:\Program Files\Arduino CLI — refresh PATH in this process
            _refresh_windows_path()
            # Verify
            v = subprocess.run(["arduino-cli", "version"],
                               capture_output=True, text=True)
            if v.returncode == 0:
                print(f"   ✅ arduino-cli installed via winget: {v.stdout.strip()}")
                return True
    except FileNotFoundError:
        print("   winget not available (Windows < 1709 or App Installer missing).")
    except subprocess.TimeoutExpired:
        print("   winget timed out.")
    except Exception as e:
        print(f"   winget failed: {e}")

    # ── Strategy 2: GitHub Releases ZIP ─────────────────────────────────────
    print("   Trying GitHub Releases download...")
    try:
        import urllib.request, zipfile, io

        # Fetch latest release metadata
        api_url  = "https://api.github.com/repos/arduino/arduino-cli/releases/latest"
        req      = urllib.request.Request(api_url,
                       headers={"User-Agent": "VibeCoder/6.1"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            release = json.loads(resp.read().decode())

        # Find the Windows 64-bit ZIP asset
        asset_url = ""
        for asset in release.get("assets", []):
            name = asset["name"].lower()
            if "windows" in name and "64bit" in name and name.endswith(".zip"):
                asset_url = asset["browser_download_url"]
                break

        if not asset_url:
            raise RuntimeError("No Windows 64-bit ZIP found in latest release.")

        print(f"   Downloading {asset_url.split('/')[-1]} ...")
        with urllib.request.urlopen(asset_url, timeout=120) as resp:
            zip_data = resp.read()

        # Extract arduino-cli.exe to %LOCALAPPDATA%\Programs\arduino-cli\
        install_dir = os.path.join(os.environ.get("LOCALAPPDATA", HOME),
                                   "Programs", "arduino-cli")
        os.makedirs(install_dir, exist_ok=True)

        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            for member in zf.namelist():
                if member.lower().endswith("arduino-cli.exe"):
                    zf.extract(member, install_dir)
                    # Flatten: move to install_dir root if in a subdirectory
                    extracted = os.path.join(install_dir, member)
                    dest      = os.path.join(install_dir, "arduino-cli.exe")
                    if extracted != dest:
                        import shutil
                        shutil.move(extracted, dest)
                    break

        exe = os.path.join(install_dir, "arduino-cli.exe")
        if not os.path.exists(exe):
            raise RuntimeError("arduino-cli.exe not found after extraction.")

        # Add to PATH for this session
        os.environ["PATH"] = install_dir + os.pathsep + os.environ.get("PATH","")

        # Persist to user PATH via registry (best-effort)
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE)
            current_path, _ = winreg.QueryValueEx(key, "PATH")
            if install_dir not in current_path:
                winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ,
                                  current_path + os.pathsep + install_dir)
            winreg.CloseKey(key)
            print(f"   ✅ Added {install_dir} to user PATH (restart terminal to take effect).")
        except Exception:
            print(f"   ℹ️  Add to PATH manually: {install_dir}")

        # Verify
        v = subprocess.run([exe, "version"], capture_output=True, text=True)
        if v.returncode == 0:
            print(f"   ✅ arduino-cli installed via ZIP: {v.stdout.strip()}")
            return True

        raise RuntimeError("Installed but verification failed.")

    except Exception as e:
        print(f"   GitHub download failed: {e}")

    # ── Strategy 3: Manual instructions ─────────────────────────────────────
    print("\n   ❌ Automatic install failed.")
    print("   Please install arduino-cli manually:")
    print()
    print("   Option A — winget (run in PowerShell):")
    print("     winget install --id Arduino.ArduinoCLI")
    print()
    print("   Option B — Download ZIP:")
    print("     https://github.com/arduino/arduino-cli/releases/latest")
    print("     → arduino-cli_*_Windows_64bit.zip")
    print("     Extract arduino-cli.exe to a folder in your PATH")
    print()
    print("   Option C — Chocolatey:")
    print("     choco install arduino-cli")
    print()
    print("   After installing, restart this script.")
    return False


def _refresh_windows_path():
    """Re-read PATH from registry so newly installed tools are found."""
    if not IS_WINDOWS:
        return
    try:
        import winreg
        # System PATH
        sys_key  = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                  r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")
        sys_path, _ = winreg.QueryValueEx(sys_key, "PATH")
        winreg.CloseKey(sys_key)
        # User PATH
        usr_key  = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment")
        try:
            usr_path, _ = winreg.QueryValueEx(usr_key, "PATH")
        except FileNotFoundError:
            usr_path = ""
        winreg.CloseKey(usr_key)

        combined = sys_path + os.pathsep + usr_path
        os.environ["PATH"] = combined + os.pathsep + os.environ.get("PATH","")
    except Exception:
        pass


def ensure_arduino_cli():
    """Check and auto-install arduino-cli if missing — cross-platform."""

    # ── Already installed? ───────────────────────────────────────────────────
    try:
        r = subprocess.run(["arduino-cli", "version"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return  # All good
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass

    # On Windows, refresh PATH first — winget may have installed it already
    if IS_WINDOWS:
        _refresh_windows_path()
        try:
            r = subprocess.run(["arduino-cli", "version"],
                               capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return
        except Exception:
            pass

    print("\n   arduino-cli not found. Auto-installing...")

    # ── Windows ──────────────────────────────────────────────────────────────
    if IS_WINDOWS:
        ok = _install_arduino_cli_windows()
        if not ok:
            sys.exit(1)

    # ── macOS ─────────────────────────────────────────────────────────────────
    elif IS_MAC:
        try:
            # Prefer Homebrew if available
            brew = subprocess.run(["brew", "version"], capture_output=True)
            if brew.returncode == 0:
                print("   Installing via Homebrew...")
                subprocess.run(["brew", "install", "arduino-cli"], check=True)
            else:
                raise FileNotFoundError("brew not found")
        except Exception:
            # Fallback: official install script
            try:
                print("   Installing via official script...")
                cmd = ("curl -fsSL "
                       "https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh"
                       " | sh")
                subprocess.run(["sh", "-c", cmd], check=True)
                for candidate in [os.path.join(HOME, "bin"), "/usr/local/bin"]:
                    if os.path.exists(os.path.join(candidate, "arduino-cli")):
                        os.environ["PATH"] += os.pathsep + candidate
                        break
            except Exception as e:
                print(f"   ❌ Auto-install failed: {e}")
                print("   Install manually: https://arduino.github.io/arduino-cli/")
                sys.exit(1)

    # ── Linux ─────────────────────────────────────────────────────────────────
    else:
        try:
            print("   Installing via official script...")
            cmd = ("curl -fsSL "
                   "https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh"
                   " | sh")
            subprocess.run(["sh", "-c", cmd], check=True)
            for candidate in [
                os.path.join(HOME, "bin"),
                os.path.join(os.getcwd(), "bin"),
                "/usr/local/bin",
            ]:
                if os.path.exists(os.path.join(candidate, "arduino-cli")):
                    os.environ["PATH"] += os.pathsep + candidate
                    break
        except Exception as e:
            print(f"   ❌ Auto-install failed: {e}")
            print("   Install manually: https://arduino.github.io/arduino-cli/")
            sys.exit(1)

    # ── Final verification ────────────────────────────────────────────────────
    try:
        r = subprocess.run(["arduino-cli", "version"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            print(f"   ✅ arduino-cli ready: {r.stdout.strip()}")
            subprocess.run(["arduino-cli", "config", "init"], capture_output=True)
        else:
            raise RuntimeError("version check failed")
    except Exception:
        print("   ❌ arduino-cli not found after install.")
        print("   Please restart your terminal and try again.")
        sys.exit(1)


def main(cli_port=None, cli_board=None, cli_baud=None,
         cli_monitor=False, cli_setup=False):
    print("=" * 60)
    print("  VibeCoder v6.1 - Universal AI Hardware Agent")
    print(f"  Platform: {platform.system()}")
    print("=" * 60)

    _ensure_deps()
    load_db()

    global AI_CFG
    AI_CFG = setup_ai_backend(force=cli_setup)

    if cli_board and cli_port:
        board = {**cli_board, "port": cli_port}
        if cli_baud: board["upload_speed"] = cli_baud
        print(f"\n✔  Board  : {board['name']} (from --board flag)")
        print(f"   Port   : {board['port']} (from --port flag)")
    else:
        board = detect_board()
        if cli_port:  board["port"]         = cli_port
        if cli_baud:  board["upload_speed"] = cli_baud
    if not board.get("port"):
        print("\n⚠️  No board detected. Plug in your board and restart.")
        return

    if IS_LINUX:
        _ensure_serial_permissions(board["port"])

    print(f"\n✔  Board  : {board['name']}")
    print(f"   FQBN   : {board['fqbn']}")
    print(f"   Port   : {board['port']}")
    print(f"   Upload : {board.get('upload_method','arduino-cli')}")

    ensure_core(board["fqbn"])

    if cli_monitor:
        serial_monitor(board.get("port",""))
        return

    ai            = AIAgent(board)
    last_response = None

    print("\n" + "─"*60)
    print("Describe what you want your hardware to do.")
    print("Commands: 'exit' | 'redeploy' | 'monitor [baud]' | 'history' | 'load <n>' | 'update' | 'setup'")
    print("─"*60)

    while True:
        try:
            user_input = smart_input("\n[VibeCoder] ➜ ")
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye! 👋"); break

        if not user_input: continue
        if user_input.lower() in ("exit","quit","q"):
            print("Goodbye! 👋"); break

        if user_input.lower() == "redeploy":
            if last_response: deploy(last_response, board, "redeploy")
            else: print("Nothing to redeploy.")
            continue

        if user_input.lower() == "update":
            if os.path.exists(BOARDS_DB_FILE):
                os.remove(BOARDS_DB_FILE)
            load_db()
            continue

        if user_input.lower() == "setup":
            AI_CFG = setup_ai_backend(force=True)
            continue

        if user_input.lower() in ("history", "h"):
            show_history()
            continue

        if user_input.lower().startswith("load "):
            pick = user_input[5:].strip()
            proj = load_project(pick)
            if proj:
                last_response = proj["code"]
                generate_diagram(board, proj["wiring"], proj["meta"]["task"])
                choice = smart_input("   Re-upload this project? [Y/n]: ").lower()
                if choice != "n":
                    deploy(proj["code"], board, proj["meta"]["task"])
            continue

        if user_input.lower().startswith("monitor"):
            parts = user_input.split()
            baud  = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 115200
            serial_monitor(board.get("port",""), baud)
            continue

        print(f"\n🤖 Thinking ({AI_CFG.get('model','AI')})...\n")
        response = ai.ask(user_input)
        if not response: continue

        print("─"*60)
        print(response)
        print("─"*60)

        last_response = response
        deploy(response, board, user_input)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="VibeCoder — Program any microcontroller with plain English",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python vibecoder.py
  python vibecoder.py --board esp32 --port COM3
  python vibecoder.py --port /dev/ttyUSB0 --baud 115200
  python vibecoder.py --monitor
  python vibecoder.py --setup
        """
    )
    parser.add_argument("--port",    type=str, help="Serial port (e.g. COM3 or /dev/ttyUSB0)")
    parser.add_argument("--board",   type=str, help="Board FQBN or short name (e.g. esp32, uno, nano)")
    parser.add_argument("--baud",    type=int, help="Upload baud rate (default: auto)")
    parser.add_argument("--monitor", action="store_true", help="Open serial monitor immediately")
    parser.add_argument("--setup",   action="store_true", help="Run AI backend setup wizard")
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    args = parser.parse_args()

    if args.version:
        print("VibeCoder v6.1 — Universal AI Hardware Agent")
        print("github.com/YOUR_USERNAME/vibecoder")
        sys.exit(0)

    ensure_arduino_cli()

    try:
        board_shortcuts = {
            "uno":     {"fqbn":"arduino:avr:uno",           "name":"Arduino Uno",         "upload_speed":115200, "upload_method":"avrdude"},
            "nano":    {"fqbn":"arduino:avr:nano",          "name":"Arduino Nano",        "upload_speed":57600,  "upload_method":"avrdude"},
            "mega":    {"fqbn":"arduino:avr:mega2560",      "name":"Arduino Mega 2560",   "upload_speed":115200, "upload_method":"avrdude"},
            "esp32":   {"fqbn":"esp32:esp32:esp32",         "name":"ESP32 DevKit",        "upload_speed":921600, "upload_method":"esptool"},
            "esp8266": {"fqbn":"esp8266:esp8266:nodemcuv2", "name":"NodeMCU ESP8266",     "upload_speed":921600, "upload_method":"esptool"},
            "nodemcu": {"fqbn":"esp8266:esp8266:nodemcuv2", "name":"NodeMCU ESP8266",     "upload_speed":921600, "upload_method":"esptool"},
            "pico":    {"fqbn":"rp2040:rp2040:rpipico",     "name":"Raspberry Pi Pico",   "upload_speed":None,   "upload_method":"uf2"},
            "picow":   {"fqbn":"rp2040:rp2040:rpipicow",    "name":"Raspberry Pi Pico W", "upload_speed":None,   "upload_method":"uf2"},
            "leonardo":{"fqbn":"arduino:avr:leonardo",      "name":"Arduino Leonardo",    "upload_speed":None,   "upload_method":"arduino-cli"},
            "due":     {"fqbn":"arduino:sam:arduino_due_x", "name":"Arduino Due",         "upload_speed":None,   "upload_method":"bossac"},
        }

        main(
            cli_port    = args.port,
            cli_board   = board_shortcuts.get(args.board.lower(), None) if args.board else None,
            cli_baud    = args.baud,
            cli_monitor = args.monitor,
            cli_setup   = args.setup,
        )
    except KeyboardInterrupt:
        print("\n   Goodbye! 👋")
        sys.exit(0)
