# 🌌 Planet Tracker: Galactic Nexus

> Real-time 3D solar system simulation with AI-powered astronomy chat, built on NASA ephemeris data.

![Python Version](https://img.shields.io/badge/python-3.x-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![GUI](https://img.shields.io/badge/GUI-Tkinter-lightgray.svg)
![Ephemeris](https://img.shields.io/badge/ephemeris-NASA_JPL_DE421-orange.svg)
![Skyfield](https://img.shields.io/badge/skyfield-≥1.45-blueviolet.svg)
![Plotly](https://img.shields.io/badge/plotly-≥5.18.0-3F4F75.svg)
![LLM](https://img.shields.io/badge/LLM-Groq-FF6B35.svg)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Tech Stack](#️-tech-stack)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Variables](#environment-variables)
  - [Running the Application](#running-the-application)
- [Usage Guide](#-usage-guide)
- [Architecture](#️-architecture)
- [Module Reference](#-module-reference)
- [Tracked Celestial Bodies](#-tracked-celestial-bodies)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)
- [Acknowledgments](#-acknowledgments)

---

## 🌟 Overview

**Planet Tracker: Galactic Nexus** is a desktop astronomy application built for enthusiasts, students, and educators who want to explore our solar system with precision and interactivity. It computes real, physically accurate planetary positions using NASA JPL's DE421 ephemeris via the `skyfield` library — covering dates from ~1900 to 2050 — and renders them as interactive 3D Plotly visualizations launched directly in your browser.

Beyond visualization, the application integrates an AI chat assistant powered by Groq, live planetary metadata fetched from the *L'OpenData du Système solaire* API, full dark/light theming, astronomical event detection, time-scrubbing across 150 years of orbital data, and HTML/CSV export — all within a single Tkinter desktop window.

---

## ✨ Features

- 🔭 **NASA JPL DE421 Ephemeris Engine** — Sub-arcsecond accurate heliocentric positions for 8 planets + Moon, covering 1900–2050, computed via `skyfield` with JD-boundary clamping to prevent out-of-range errors.

- 🌙 **Correct Moon Heliocentric Positioning** — The Moon's position is computed as Earth's heliocentric vector plus the Moon's geocentric vector, placing it accurately in the solar frame rather than at Earth's position.

- 🪐 **Interactive 3D Orbital Visualization** — Plotly `Scatter3d` plots render full orbital paths and current planet positions with size-scaled markers (proportional to real planetary radii), custom camera orientation (elevation + azimuth), and zoom controls. Output saves as a standalone `.html` file and auto-launches in your default browser.

- 🎬 **Time-Lapsed Orbital Animations** — Generate frame-by-frame animations of planetary motion across a custom date range, complete with a built-in Play/Pause button and timeline slider, exported as a self-contained interactive HTML file.

- 📅 **150-Year Time Navigation** — Scrub through planetary positions from 1900 to 2050 using a real-time slider, manual date entry (`YYYY-MM-DD HH:MM:SS`), or enable **Real-Time mode** to lock the view to the current UTC moment.

- 🔭 **Astronomical Event Detection** — Detects and labels Superior Conjunctions, Inferior Conjunctions, and Oppositions using `skyfield`'s `find_minima` / `find_maxima` on apparent elongation angles. Events are marked directly on the 3D plot with distinct Plotly symbols (`star`, `diamond-tall`, `cross`).

- 🧠 **Embedded Groq AI Chat Assistant** — A scrollable chat panel inside the app lets you query an LLM about astronomy topics. The client verifies connectivity at startup by listing available models. Gracefully degrades if `GROQ_API_KEY` is absent or the library is not installed.

- 📊 **Live Planetary Metadata Panel** — Physical parameters (mass, mean radius in km, surface gravity in m/s², density in g/cm³, average temperature in °C/K, orbital period in days, semi-major axis in AU and km) fetched from [L'OpenData du Système solaire](https://api.le-systeme-solaire.net) and cached locally as `planet_data_cache.json` for offline use.

- 🎨 **Dark & Light Theming** — Full GUI theme switching between a deep-space dark mode (`#0a0a1a` background, `#00ffea` cyan accent) and a clean light mode (`#ffffff` background, `#007f7f` teal accent), applied consistently across all `ttk` and `tk` widgets.

- 🖌️ **Per-Planet Custom Colors** — Each planet has a scientifically inspired default color (e.g., Earth: `#4682B4` SteelBlue, Mars: `#CD5C5C` IndianRed, Neptune: `#4169E1` RoyalBlue). Override any color with a hex picker; choices propagate to orbit lines, planet markers, and text labels.

- 💾 **Configuration Save / Load** — Persist and reload selected planets, custom colors, date ranges, camera settings, and theme preferences to/from a JSON config file.

- 📥 **Export to HTML & CSV** — Export the current 3D plot as a standalone interactive HTML file (powered by Plotly CDN), or dump raw heliocentric orbital position data as a CSV spreadsheet for external analysis.

- 🔒 **Thread-Safe UI** — All long-running calculations (orbit computation, event search, animation generation) execute on background threads controlled by a `threading.Lock`, keeping the Tkinter main loop responsive with a `ttk.Progressbar` indicator.

- 📝 **Structured Logging** — Module-level `logging` throughout all four Python files, with log level configurable via the `LOG_LEVEL` environment variable (default: `INFO`). Each log entry includes timestamp, level, and thread name.

- ⚡ **LRU-Cached Orbit Calculations** — `calculate_orbit` is decorated with `@lru_cache(maxsize=32)`, caching the 32 most recent orbit calculations by planet name, start JD, end JD, and point count — avoiding redundant Skyfield calls during repeated renders.

---

## 🛠️ Tech Stack

| Category | Technology | Version | Purpose |
|---|---|---|---|
| Language | Python | 3.x | Core application logic |
| GUI Framework | Tkinter + ttk | stdlib | Native desktop interface (1400×1000 window) |
| Astronomy Engine | Skyfield | ≥ 1.45 | Ephemeris loading, time objects, position vectors, event search |
| Ephemeris Data | NASA JPL DE421 | — | Binary planetary/lunar position kernel (~17 MB) |
| 3D Visualization | Plotly | ≥ 5.18.0 | Interactive `Scatter3d` plots and frame animations |
| Numerical Computing | NumPy | ≥ 1.24.0 | Position vector arithmetic, array operations |
| HTTP Client | Requests | ≥ 2.31.0 | Fetching planetary metadata from L'OpenData API |
| LLM Integration | Groq | ≥ 0.3.0 | Fast inference API for the embedded astronomy assistant |
| Metadata API | L'OpenData du Système solaire | — | Physical parameters for planets and Moon |
| Data Cache | JSON (stdlib) | — | Offline persistence of API planetary data |

---

## 📁 Project Structure

```
Planet-Tracker/
├── main.py                  # Tkinter UI, LLM chat, theming, threading, config save/load
├── planet_calculations.py   # Skyfield ephemeris engine: positions, orbits, events, elements
├── planet_plot.py           # Plotly 3D rendering: static plots and frame-by-frame animations
├── planet_data.py           # L'OpenData API client, JSON caching, radius/color lookups
├── planet_data_cache.json   # Auto-generated local cache of API planetary parameters
├── de421.bsp                # NASA JPL DE421 ephemeris binary (required, ~17 MB)
├── requirements.txt         # pip dependency declarations
└── README.md                # Project documentation
```

**Generated at runtime:**

```
solar_system_plot.html       # Exported static 3D plot (opened automatically in browser)
solar_system_animation.html  # Exported animation (opened automatically in browser)
```

---

## ⚡ Quick Start

### Prerequisites

- **Python 3.8+** (3.10+ recommended for `datetime.UTC` support used in the codebase)
- **pip** package manager
- A display/desktop environment (Tkinter requires a GUI; headless environments are detected and exit cleanly)
- *(Optional)* A [Groq API key](https://console.groq.com) for AI chat features
- The `de421.bsp` ephemeris file (~17 MB) — either downloaded automatically by Skyfield or placed manually in the project root

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/savinaysingh7/Planet-Tracker.git
cd Planet-Tracker

# 2. (Recommended) Create and activate a virtual environment
python -m venv venv

# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# 3. Install all dependencies
pip install -r requirements.txt
```

### Ephemeris File

The application requires `de421.bsp` in the project root. If not already present, download it manually:

```bash
# Direct download via curl (~17 MB)
curl -O https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de421.bsp

# Or using Python
python -c "from skyfield.api import Loader; load = Loader('.'); load('de421.bsp')"
```

If the file is missing at startup, the application exits immediately with a clear `FATAL` log message.

### Environment Variables

| Variable | Description | Required | Default |
|---|---|---|---|
| `GROQ_API_KEY` | API key from [console.groq.com](https://console.groq.com) for the embedded LLM assistant | ❌ Optional | None (LLM disabled if absent) |
| `LOG_LEVEL` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | ❌ Optional | `INFO` |

```bash
# macOS / Linux
export GROQ_API_KEY="gsk_your_key_here"
export LOG_LEVEL="DEBUG"    # Optional — increase verbosity for troubleshooting

# Windows (Command Prompt)
set GROQ_API_KEY=gsk_your_key_here
set LOG_LEVEL=DEBUG
```

> **Note:** If `GROQ_API_KEY` is not set, the AI chat panel will be present in the UI but will display a disabled state. All astronomy calculation and visualization features remain fully functional without it.

### Running the Application

```bash
python main.py
```

The application initializes in this order:
1. Loads `de421.bsp` and verifies Sun, Earth, Moon bodies are present
2. Initializes `PlanetData` (loads from `planet_data_cache.json` or fetches from API)
3. Verifies Groq connectivity (if key is configured)
4. Launches the 1400×1000 Tkinter window

---

## 📖 Usage Guide

### Basic Workflow

**1. Select Celestial Bodies**
In the left panel, toggle checkboxes for any of the 9 tracked bodies (Mercury through Neptune + Moon). Click **"Set"** next to any planet name to open a hex color picker and assign a custom visualization color.

**2. Navigate Time**

- **Time Slider** (Time/Orbits tab): Drag to any Julian Date between ~1900 and ~2050. The current UTC date/time updates in real time.
- **Manual Entry**: Type a specific date (`YYYY-MM-DD`) and time (`HH:MM:SS`) into the date/time fields.
- **Real-Time Mode**: Enable the "Real-Time" checkbox to track the current UTC moment, automatically refreshing positions.
- **Orbit Display Range**: Set `Start Date` and `End Date` fields to define the arc of orbital path displayed. The app auto-clamps ranges to the loaded ephemeris bounds.

**3. Generate the 3D Plot**
Go to the **Settings/Export** tab and click **"Update Static Plot"**. The app calculates positions, orbits (up to 1,000 points for smooth curves), and any active astronomical events, then saves `solar_system_plot.html` and opens it in your default browser.

**4. Generate an Animation**
Set your desired date range and click **"Generate Animation"**. Frames are computed at regular intervals; the resulting `solar_system_animation.html` opens with Play/Pause controls and a scrubable timeline.

**5. Detect Astronomical Events**
Click **"Find Next Events"** with a search window configured. The app uses `skyfield`'s `find_minima` / `find_maxima` on apparent elongation to locate Conjunctions and Oppositions, displaying results in the chat panel and marking them on the next plot with special symbols.

**6. Explore Planetary Data**
Select any body and switch to the **Planet Info** tab to view API-sourced physical parameters: mass, radius, surface gravity, density, temperature, orbital period, and semi-major axis.

**7. Chat with the AI Assistant**
Type astronomy questions into the chat input field (e.g., *"What causes a superior conjunction?"*, *"How long is a Martian year in Earth days?"*) and press Enter or click **Send**. Responses stream into the scrollable chat panel.

**8. Export Data**
- **Export HTML**: Saves the current plot as a self-contained interactive HTML file (Plotly loaded from CDN).
- **Export CSV**: Dumps the heliocentric `(x, y, z)` orbital position arrays for all active planets to a `.csv` file.
- **Save Config / Load Config**: Persist your planet selection, colors, date ranges, zoom, elevation, azimuth, and theme to a JSON file.

### Camera Controls (in the HTML plot)

The Plotly viewer supports full 3D interaction:
- **Left-drag** — Rotate the scene
- **Right-drag / Scroll** — Zoom
- **Middle-drag** — Pan
- **Double-click** — Reset camera

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                   main.py                        │
│   PlanetTrackerApp (Tkinter 1400×1000 window)    │
│   ├── Left Panel: Planet selection + color pickers│
│   ├── Center Panel: Groq LLM chat (scrolledtext) │
│   └── Right Notebook (4 tabs):                   │
│       ├── Time / Orbits                          │
│       ├── Camera Settings                        │
│       ├── Settings / Export                      │
│       └── Planet Info                            │
│                                                  │
│   Threading: background jobs via threading.Lock  │
│   Theme: dark (#0a0a1a / #00ffea)                │
│           light (#ffffff / #007f7f)              │
└───────────┬─────────────────┬────────────────────┘
            │                 │
            ▼                 ▼
┌───────────────────┐ ┌──────────────────────────┐
│ planet_calculations│ │      planet_data.py       │
│ .py               │ │   PlanetData (singleton)  │
│                   │ │                           │
│ Skyfield engine:  │ │ L'OpenData API client     │
│ • de421.bsp load  │ │ planet_data_cache.json    │
│ • ts (timescale)  │ │ Fallback data on failure  │
│ • sun, earth, moon│ │ get_planet_info()         │
│ • planet_dict     │ │ get_planet_color()        │
│ • parse_date_time │ │ get_planet_radius()       │
│ • calculate_orbit │ └──────────────────────────┘
│   @lru_cache(32)  │
│ • get_heliocentric│          ▼
│ • get_orbital_    │ ┌──────────────────────────┐
│   elements        │ │     planet_plot.py        │
│ • calculate_events│ │     PlanetPlot            │
│ • find_next_events│ │                           │
│   (elongation)    │ │ Plotly Scatter3d:         │
└───────────────────┘ │ • Sun + glow layers       │
                      │ • Orbit path lines        │
                      │ • Size-scaled planet dots │
                      │ • Event symbol markers    │
                      │ • go.Frame animation      │
                      │ • write_html → browser    │
                      └──────────────────────────┘
```

**Data flow for a plot update:**
1. UI thread reads date/time widgets → validates against ephemeris bounds
2. Background thread calls `get_heliocentric_positions()` for active planets
3. Background thread calls `calculate_orbit()` (LRU-cached) for each body
4. Background thread calls `calculate_events()` for conjunction/opposition detection
5. Main thread calls `PlanetPlot.update_plot()` → Plotly figure → `write_html` → `webbrowser.open`

---

## 📦 Module Reference

### `planet_calculations.py`

| Export | Type | Description |
|---|---|---|
| `ts` | `Timescale` | Skyfield timescale object used for all time conversions |
| `sun`, `earth`, `moon` | `Body` | Skyfield body objects from DE421 |
| `ephem_start_jd`, `ephem_end_jd` | `float` | Buffered Julian Date bounds of the loaded ephemeris |
| `EPHEMERIS_START`, `EPHEMERIS_END` | `datetime` | App-level date range constants (1900–2050) |
| `parse_date_time(date_str, time_str)` | `→ Time` | Parses `YYYY-MM-DD` + `HH:MM[:SS]` into a validated Skyfield `Time` object |
| `calculate_orbit(name, start_jd, end_jd, num_points)` | `→ ndarray (3, N)` | LRU-cached heliocentric orbit positions in AU; Moon uses Earth+Moon vector sum |
| `get_heliocentric_positions(planets, t)` | `→ Dict[str, ndarray]` | Instantaneous heliocentric `(x,y,z)` in AU for multiple bodies at time `t` |
| `get_orbital_elements(name, t)` | `→ Dict` | Osculating Keplerian elements (SMA, eccentricity, inclination, etc.) at `t` |
| `calculate_events(t)` | `→ List[Tuple]` | Geometric conjunction/opposition check at a single instant |
| `find_next_events(planets, t_start, t_end, ...)` | `→ List[Tuple]` | Precise event search using `find_minima` / `find_maxima` on elongation angle |

### `planet_data.py`

| Export | Type | Description |
|---|---|---|
| `planet_data` | `PlanetData` | Module-level singleton, initialized on import |
| `PlanetData.get_planet_info(name)` | `→ Dict` | Formatted physical parameters with units (mass, temp, radius, gravity, etc.) |
| `PlanetData.get_planet_color(name)` | `→ str` | Hex color code for the planet (from `planet_dict` defaults) |
| `PlanetData.get_planet_radius(name)` | `→ float` | Mean radius in km; API → `planet_dict` → 1000.0 fallback chain |
| `PlanetData.get_all_planet_names()` | `→ List[str]` | Sorted list of all tracked body names |

### `planet_plot.py`

| Method | Description |
|---|---|
| `PlanetPlot.update_plot(positions, orbits, time, planets, events, zoom, elev, azim, colors)` | Renders full static 3D scene and auto-opens in browser |
| `PlanetPlot.create_animation(positions_list, times, orbits, planets, frame_duration_ms, ...)` | Builds `go.Frame` animation with Play/Pause/slider controls |

---

## 🌍 Tracked Celestial Bodies

| Body | Default Color | Mean Radius | Ephemeris Key |
|---|---|---|---|
| Mercury | `#A9A9A9` DarkGray | 2,440 km | `mercury` |
| Venus | `#FFF8DC` Cornsilk | 6,052 km | `venus` |
| Earth | `#4682B4` SteelBlue | 6,371 km | `earth` / `earth barycenter` |
| Moon | `#D3D3D3` LightGray | 1,737 km | `moon` |
| Mars | `#CD5C5C` IndianRed | 3,390 km | `mars barycenter` |
| Jupiter | `#DEB887` BurlyWood | 69,911 km | `jupiter barycenter` |
| Saturn | `#F5DEB3` Wheat | 58,232 km | `saturn barycenter` |
| Uranus | `#AFEEEE` PaleTurquoise | 25,362 km | `uranus barycenter` |
| Neptune | `#4169E1` RoyalBlue | 24,622 km | `neptune barycenter` |

All colors are fully customizable in the UI via a hex color picker.

---

## 🔧 Troubleshooting

**`FATAL: Ephemeris file 'de421.bsp' not found`**
Download the file and place it in the project root directory. See [Ephemeris File](#ephemeris-file) above.

**`Failed to import core dependency`**
Run `pip install -r requirements.txt`. If using a virtual environment, ensure it is activated before running.

**LLM chat is disabled / shows no response**
Set the `GROQ_API_KEY` environment variable and restart. Verify your key is valid at [console.groq.com](https://console.groq.com). The `groq` package must also be installed (`pip install groq`).

**`Cannot start the application in a headless environment`**
Tkinter requires a display. On Linux servers, set `DISPLAY` or run locally. The app detects headless mode (`DEBIAN_FRONTEND=noninteractive`) and exits cleanly without crashing.

**Plot opens but is blank or partial**
The browser may block `file://` access. Try opening `solar_system_plot.html` manually, or use a browser with relaxed local file policies.

**Dates outside 1900–2050 are rejected**
The DE421 ephemeris covers approximately 1899–2053; the application enforces a buffered safe range. Dates outside this window raise a `ValueError` with a clear message.

**Enable verbose logging for debugging:**
```bash
LOG_LEVEL=DEBUG python main.py
```

---

## 🤝 Contributing

```bash
# 1. Fork the repository on GitHub

# 2. Clone your fork
git clone https://github.com/your-username/Planet-Tracker.git
cd Planet-Tracker

# 3. Create a feature branch
git checkout -b feature/your-feature-name

# 4. Make your changes and test
python planet_calculations.py   # Module self-test
python planet_data.py           # Module self-test
python planet_plot.py           # Module self-test (generates test HTML)
python main.py                  # Full application test

# 5. Commit and push
git add .
git commit -m "feat: describe your change clearly"
git push origin feature/your-feature-name

# 6. Open a Pull Request on GitHub
```

**Code style conventions observed in the project:**
- Module-level `logging.getLogger(__name__)` in every file
- Type hints on all public functions (`Dict`, `List`, `Optional`, `Tuple` from `typing`)
- Docstrings with `Args:` and `Returns:` sections on all public methods
- Graceful degradation — every external dependency (API, LLM, ephemeris) has an explicit fallback path

---

## 📄 License

This project is licensed under the **MIT License**. See the `LICENSE` file for full details.

---

## 👤 Author

**Savinay Singh**
GitHub: [@savinaysingh7](https://github.com/savinaysingh7)
Repository: [github.com/savinaysingh7/Planet-Tracker](https://github.com/savinaysingh7/Planet-Tracker)

---

## 🙏 Acknowledgments

- **[NASA JPL / NAIF](https://naif.jpl.nasa.gov)** — DE421 planetary ephemeris kernel that makes high-precision calculations possible
- **[Skyfield](https://rhodesmill.org/skyfield/)** by Brandon Rhodes — elegant Python library for high-precision astronomical calculations
- **[Plotly](https://plotly.com/python/)** — interactive 3D visualization library powering the browser-rendered solar system views
- **[L'OpenData du Système solaire](https://api.le-systeme-solaire.net)** — open REST API providing rich physical parameters for solar system bodies
- **[Groq](https://groq.com)** — ultra-fast LLM inference API enabling real-time astronomy Q&A inside the application

---

*Let the cosmic tracking commence.* 🚀