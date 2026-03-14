# 🌌 Planet Tracker: Galactic Nexus

![Python Version](https://img.shields.io/badge/python-3.x-blue.svg)
![GUI Toolkit](https://img.shields.io/badge/GUI-Tkinter-lightgray.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 📖 Description

**Planet Tracker: Galactic Nexus** is an advanced, beautifully tailored Python desktop application designed for astronomy enthusiasts, students, and educators. It accurately orchestrates the simulation, calculation, and visualization of planetary positions, orbital paths, and astronomical events within our Solar System. 

Powered by real astronomical ephemeris data (NASA JPL DE421) and the high-precision `skyfield` library, the app transcends basic planetary tracking. It integrates rich 3D interactive plotting, offline planetary metadata, orbital animations, and an AI-driven chat assistant to answer your cosmic inquiries.

---

## ✨ Key Features

- 🎯 **High-Precision Ephemeris:** Computes highly accurate heliocentric positions for planets and geocentric positions for the Moon using NASA JPL’s DE421 planetary ephemeris.
- 🪐 **Interactive 3D Orbit Visualization:** Generates stunning, interactive 3D plots of celestial bodies and their orbital paths using `plotly` (featuring smooth zooming, panning, and camera rotation).
- 🎬 **Orbital Animations:** Generate smooth, time-lapsed interactive animations of planetary motion over a specified date range with adjustable playback speeds.
- 📅 **Advanced Time Navigation:** Navigate seamlessly through time using an interactive slider, define precise start and end dates, or use a live "Real-Time" tracking mode.
- 🔭 **Astronomical Event Detection:** Automatically scans and calculates upcoming major astronomical events (e.g., Superior/Inferior Conjunctions, Oppositions) relative to Earth.
- 🧠 **Smart AI Assistant:** Features an integrated chat interface powered by the `groq` LLM framework. Ask complex astronomy questions directly within the application.
- 📊 **Dynamic Planet Metadata:** Fetches rich planetary physical parameters (mass, temperature, radius, gravity, density) from the *L'OpenData du Système solaire API* and caches them for offline use.
- 🎨 **Deep UI Customization:** Personalize the application with Dark and Light mode GUI themes, assign custom hex colors to planets, and effortlessly save/load your configurations.
- 📥 **Export Capabilities:** Export robust 3D plots as standalone, interactive HTML files, or capture raw orbital positioning data as CSV spreadsheets.

---

## 🛠️ Tech Stack

- **Core Python 3.x:** Primary language driving logic and GUI.
- **Tkinter:** Standard toolkit utilized for building the native desktop interface.
- **Skyfield:** Elegant astronomical computation library mimicking high-precision physics.
- **Plotly & NumPy:** Employed to generate 3D spatial visualizations and perform fast matrix math on vectors.
- **Requests:** Handling REST API connections for fetching external planetary metadata.
- **Groq API:** Fast Large Language Model API utilized for the built-in astronomy chat assistant.
- **NASA JPL DE421:** Standard binary planetary ephemeris database.

---

## 📂 Folder Structure

```text
Planet-Tracker/
├── main.py                  # Tkinter UI, LLM Chat interaction, Theming configuration.
├── planet_calculations.py   # Core physics engine: Skyfield integration, orbits, and events.
├── planet_data.py           # Data interface: API requests, caching, and planet metadata.
├── planet_plot.py           # Presentation layer: Plotly 3D scatter and animation rendering.
├── planet_data_cache.json   # (Auto-generated) Local cache of OpenData system parameters.
├── de421.bsp                # (Required) NASA JPL Ephemeris binary file. 
├── requirements.txt         # Pip package dependencies.
└── README.md                # Project documentation.
```

---

## 🚀 Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/your-username/Planet-Tracker.git
cd Planet-Tracker
```

### 2. Set up a virtual environment (Recommended)
Isolate your installation dependencies:
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Download the Ephemeris File (Required)
The application requires the `de421.bsp` ephemeris file to parse locations. 
If the application cannot download it automatically, download it manually and place it in the project root directory:
[Download DE421 from NASA NAIF](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de421.bsp)

### 5. Setup AI Assistant (Optional)
To enable the integrated LLM Chatbot, configure a Groq API key in your environment variables:
```bash
# On Windows:
set GROQ_API_KEY="your-groq-api-key"

# On macOS/Linux:
export GROQ_API_KEY="your-groq-api-key"
```

---

## 🎮 Usage Example

Launch the master file from your console:
```bash
python main.py
```

### Basic Workflow
1. **Select Celestial Bodies:** Choose which planets (e.g., Earth, Venus, Mars) you want to visualize from the left panel. Customize their visual colors using the "Set" button.
2. **Scrub Through Time:** Navigate to the **Time / Orbits** tab on the right. Modify the "Time Navigation" slider to change the current epoch, or set an overarching interval in the "Orbit Display Range".
3. **Generate Visualizations:** Move to the **Settings / Export** tab and click **Update Static Plot**. Your default browser will instantly launch the generated interactive 3D Solar System map.
4. **Interact with AI:** Ask the chatbot in the center panel queries like, "What is a Superior Conjunction?" or "How long is a year on Mars?"

---

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details. Let the cosmic tracking commence!
