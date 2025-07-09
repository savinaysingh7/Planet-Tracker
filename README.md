````markdown
# Planet Tracker

**Interactive 3D Solar System Visualization**

---

## 📖 Overview

**Planet Tracker** is a Python desktop application that simulates and visualizes the solar system in real time.  
- Computes planetary and lunar positions using NASA/JPL DE421 ephemeris via [Skyfield](https://rhodesmill.org/skyfield/).  
- Renders interactive 3D plots with [Plotly](https://plotly.com/python/).  
- Provides a Tkinter-based GUI for time controls, orbit visualization, and AI‑assisted queries (via Groq).  
- Fetches planetary metadata from the OpenData Solar System API with caching and fallbacks.

---

## 🚀 Features

- **3D Visualization**  
  - Sun, Mercury…Neptune, and Moon, with color‑coded markers, labels, and orbits.  
- **Accurate Ephemeris Calculations**  
  - On‑the‑fly position computations for any date/time within 1900–2050.  
- **Orbit Path Generator**  
  - Plot full heliocentric trajectories over a user‑defined date range.  
- **Time Controls**  
  - Slider for stepping through time, real‑time mode, and animation export (HTML).  
- **Event Detection**  
  - Automatic search for upcoming conjunctions and oppositions.  
- **Planet Info Panel**  
  - Mass, radius, orbital period, gravity, average temperature, etc., fetched & cached.  
- **AI Assistant (Optional)**  
  - Chat interface powered by Groq LLM to answer questions about planets or app usage.  
- **Customization & Export**  
  - Light/dark themes, planet color picker, save/load settings (JSON), export plot (HTML) and data (CSV).  
- **Robust Logging & Error Handling**  
  - Detailed logs, graceful fallbacks for missing dependencies or network issues.

---

## 🛠️ Prerequisites

- **Python 3.8+**  
- Required Python packages (see **Installation**).  
- **Ephemeris file**: `de421.bsp` (download from NASA/JPL).  
- (Optional) **Groq API Key** for AI assistant.

---

## ⚙️ Installation

1. **Clone the repository**  
   ```bash
   git clone https://github.com/yourusername/planet-tracker.git
   cd planet-tracker
````

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

   > **`requirements.txt`** should include:
   >
   > ```
   > skyfield
   > plotly
   > requests
   > groq           # if using AI assistant
   > ```
   >
   > *(Tkinter is included with most Python distributions.)*

3. **Download Ephemeris**
   Place `de421.bsp` in the project root (same folder as `main.py`).

4. **(Optional) Configure Groq API Key**

   ```bash
   export GROQ_API_KEY="your_groq_api_key_here"
   ```

   Or set in your environment so the app can enable AI chat features.

---

## ▶️ Usage

Run the main application script:

```bash
python main.py
```

* **Left Panel**

  * Select/deselect celestial bodies
  * Pick marker colors

* **Right Panel** (Tabs)

  1. **Time & Orbits**

     * Enter start/end dates (YYYY‑MM‑DD)
     * Click **“Update Plot”** to generate 3D view or **“Animate”** for time‑lapse
  2. **View & Animation**

     * Adjust zoom, camera elevation & azimuth
     * Toggle real‑time mode or manual slider
     * Export HTML animation
  3. **Settings & Export**

     * Switch light/dark theme
     * Save/load app settings (JSON)
     * Export orbit data (CSV)
  4. **Info & Events**

     * View planet metadata
     * Search upcoming conjunctions/oppositions
     * Chat with AI assistant (if enabled)

---

## 🗂️ Project Structure

```
planet-tracker/
├── de421.bsp                   # JPL ephemeris file
├── main.py                     # Application entry point & GUI
├── planet_calculations.py      # Skyfield ephemeris & orbit math
├── planet_data.py              # Fetch/cache Solar System metadata
├── planet_plot.py              # Plotly 3D plotting & animation
├── requirements.txt            # Python dependencies
└── README.md                   # This documentation
```

---

## 📝 Configuration

| Variable            | Description                                    | Default / Example        |
| ------------------- | ---------------------------------------------- | ------------------------ |
| `GROQ_API_KEY`      | API key for Groq LLM chat assistant            | *(not set)*              |
| `LOG_LEVEL`         | Logging verbosity (`DEBUG`, `INFO`, `WARNING`) | `INFO`                   |
| `planet_data_cache` | JSON file name for caching API metadata        | `planet_data_cache.json` |

---

## 🛡️ Troubleshooting

* **Missing ephemeris file**
  The app will exit with an error if `de421.bsp` is not found.
* **Network/API failures**
  Fallback data is used if the OpenData API is unavailable.
* **Groq import or key issues**
  Chat assistant is disabled if the `groq` package/key is missing.

Logs are written to the console—adjust `LOG_LEVEL` for more detail.

---

## 🎓 Educational Value

Planet Tracker combines scientific accuracy with engaging visualization. It’s ideal for:

* Astronomy students learning celestial mechanics
* Educators demonstrating orbital dynamics
* Hobbyists planning observation sessions
* Developers exploring ephemeris computations and 3D plotting

---

## 📄 License

This project is released under the MIT License. See `LICENSE` for details.

---

*Happy stargazing!* 🌌

```
```
