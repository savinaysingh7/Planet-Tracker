# 🌌 Planet Tracker: 3D Solar System Visualizer

**Planet Tracker** is a Python-based desktop application that simulates and visualizes planetary positions and orbits in the Solar System using real ephemeris data. Featuring an interactive GUI, 3D Plotly visualizations, AI-powered chat assistant, and educational tools, it’s designed for learners, astronomy enthusiasts, and hobbyists.


---

## 🚀 Features

- 🎯 **Accurate Ephemeris Calculations**  
  Uses NASA JPL’s DE421 ephemeris (via Skyfield) to compute precise heliocentric positions.

- 🪐 **3D Orbit Visualization**  
  Interactive 3D plots of planets and their orbits using Plotly. Includes zoom, pan, rotation, and hover tooltips.

- 📅 **Date & Time Control**  
  Navigate through past or future positions using a date slider or manually defined time range.

- 🛰️ **Event Detection**  
  Automatically find upcoming oppositions, conjunctions, and key astronomical alignments.

- 💬 **AI Assistant (Optional)**  
  Integrated chat assistant powered by Groq LLM to answer astronomy-related queries.

- 🎨 **Customization**  
  Change themes (dark/light), assign custom colors to planets, and control view angles.

- 📤 **Export Options**  
  Save the generated orbit plots as standalone HTML or export planetary data as CSV.

- 🧠 **Offline Planet Metadata**  
  Fetches planetary characteristics from OpenData API and caches locally for offline use.

---

## 🛠️ Technologies Used

- **Python 3.x**
- **Tkinter** – GUI framework
- **Skyfield** – Ephemeris-based astronomical calculations
- **Plotly** – 3D visualization
- **Requests** – API integration
- **Groq (optional)** – AI chat assistant integration

---

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/planet-tracker.git
   cd planet-tracker
   ```

2. **Create and activate a virtual environment** (optional but recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Linux/Mac
   venv\Scripts\activate     # On Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Download Ephemeris File**
   Ensure `de421.bsp` is placed in the root directory:
   ```python
   from skyfield.api import load
   load('de421.bsp')
   ```
   Or download manually from:  
   [https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/)

5. **(Optional) Set Groq API Key for AI Assistant**
   ```bash
   export GROQ_API_KEY="your-api-key"     # Linux/Mac
   set GROQ_API_KEY="your-api-key"        # Windows
   ```

---

## ▶️ Running the Application

```bash
python main.py
```

Upon launching:

- Select celestial bodies from the left panel
- Choose orbit date range and viewing settings
- Click "Update Plot" to generate a 3D visualization
- Access planetary info and upcoming events from the Info tab
- Use the chat box to ask astronomy questions (if AI is enabled)

---

## 📂 Project Structure

```
planet-tracker/
├── main.py                   # GUI entry point
├── planet_calculations.py   # Orbit & event computations using Skyfield
├── planet_data.py           # Fetch & cache metadata from OpenData API
├── planet_plot.py           # 3D plotting logic using Plotly
├── de421.bsp                # JPL Ephemeris file (download separately)
├── requirements.txt         # Required Python libraries
├── README.md                # This file
└── exports/                 # Folder for generated plots and CSVs
```

---

## ⚙️ Configuration Tips

- **Change theme:** via the Settings tab (light/dark)
- **Adjust camera:** modify zoom, elevation, azimuth
- **Save settings:** export and import user preferences via JSON
- **Logging:** enabled by default (`LOG_LEVEL=INFO`), changeable via environment variable

---

## 🧪 Example Use Cases

- Visualize the position of planets on your birthday
- Detect next Mars–Sun opposition for observation planning
- Export planetary orbits for school/college presentations
- Ask "What is Jupiter’s gravity?" in the chat window

---

## 💡 Contributions

Contributions are welcome!

1. Fork the repo
2. Create a new branch: `git checkout -b feature-name`
3. Commit changes: `git commit -m "Add feature"`
4. Push and open a Pull Request

---


## 🙌 Acknowledgements

- JPL / NASA for the DE421 Ephemeris
- Skyfield Team for the astronomical computation library
- Plotly for 3D visualization tools
- [Le Systeme Solaire API](https://api.le-systeme-solaire.net/) for planetary data
- Groq for LLM integration

---

## 🌠 Happy Exploring!

