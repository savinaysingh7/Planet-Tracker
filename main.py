import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser
import numpy as np
from datetime import datetime, timedelta, UTC
import threading
import time
import json
from planet_plot import PlanetPlot
from planet_data import planet_data  # Import the singleton instance directly
from planet_calculations import (ts, sun, EPHEMERIS_START, EPHEMERIS_END, parse_date_time,
                                 calculate_orbit, get_heliocentric_positions, get_orbital_elements,
                                 planet_dict, calculate_events)

def create_tooltip(widget, text):
    """Create a tooltip for a widget."""
    tooltip = tk.Toplevel(widget)
    tooltip.wm_overrideredirect(True)
    tooltip.wm_geometry(f"+{widget.winfo_rootx()+20}+{widget.winfo_rooty()+20}")
    label = tk.Label(tooltip, text=text, background="#ffffe0", relief="solid", borderwidth=1)
    label.pack()
    tooltip.withdraw()
    
    def show(event): tooltip.deiconify()
    def hide(event): tooltip.withdraw()
    
    widget.bind("<Enter>", show)
    widget.bind("<Leave>", hide)

def run_planet_tracker():
    global planet_api_data
    planet_api_data = planet_data.fetch_all_planet_data()  # Use the instance method directly
    
    root = tk.Tk()
    root.title("Planet Tracker: Galactic Nexus")
    root.geometry("1400x1000")
    root.resizable(True, True)
    root.configure(bg="#0a0a1a")

    style = ttk.Style()
    themes = {
        "dark": {"bg": "#1f2a44", "fg": "#00ffea", "root_bg": "#0a0a1a"},
        "light": {"bg": "#f0f0f0", "fg": "#000000", "root_bg": "#ffffff"}
    }
    current_theme = "dark"

    # Define a custom style for the right inner frame
    style.configure("RightInner.TFrame", background=themes[current_theme]["bg"])

    def apply_theme(theme):
        nonlocal current_theme
        current_theme = theme
        t = themes[theme]
        # Update styles for ttk widgets
        style.configure("TFrame", background=t["bg"], relief="raised")
        style.configure("TLabel", background=t["bg"], foreground=t["fg"], font=("Arial", 12))
        style.configure("TCheckbutton", background=t["bg"], foreground=t["fg"])
        style.configure("TButton", background=t["bg"], foreground=t["fg"])
        # Update the custom style for the right inner frame
        style.configure("RightInner.TFrame", background=t["bg"])
        # Update root and other tk widgets
        root.configure(bg=t["root_bg"])
        content_frame.configure(bg=t["root_bg"])
        title_label.configure(bg=t["root_bg"], fg=t["fg"])
        preview_frame.configure(bg=t["root_bg"])
        # Update the canvas background (tk.Canvas supports bg directly)
        right_canvas.configure(bg=t["bg"])
        # Update styles for all ttk widgets in the right inner frame
        for widget in right_inner_frame.winfo_children():
            if isinstance(widget, (ttk.Label, ttk.Checkbutton, ttk.Button, ttk.Frame)):
                widget.configure(style=widget.winfo_class())
        update_preview()

    content_frame = tk.Frame(root, bg=themes[current_theme]["root_bg"])
    content_frame.pack(fill="both", expand=True)

    content_frame.grid_rowconfigure(0, weight=0)
    content_frame.grid_rowconfigure(1, weight=1)
    content_frame.grid_columnconfigure(0, weight=1)
    content_frame.grid_columnconfigure(1, weight=3)
    content_frame.grid_columnconfigure(2, weight=1)

    title_label = tk.Label(content_frame, text="Planet Tracker: Galactic Nexus",
                           font=("Arial", 24, "bold"), bg=themes[current_theme]["root_bg"],
                           fg=themes[current_theme]["fg"])
    title_label.grid(row=0, column=0, columnspan=3, pady=20, sticky="ew")

    # Left panel (planet selection)
    left_panel = ttk.Frame(content_frame, style="TFrame")
    left_panel.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
    ttk.Label(left_panel, text="Selected Planets", font=("Arial", 18, "bold")).pack(pady=15)
    selected_planets = {planet: tk.BooleanVar(value=True) for planet in planet_data.get_all_planet_names()}
    planet_colors = {planet: planet_data.get_planet_color(planet) for planet in planet_data.get_all_planet_names()}
    for planet, var in selected_planets.items():
        frame = ttk.Frame(left_panel)
        frame.pack(anchor="w", pady=5, padx=15)
        cb = ttk.Checkbutton(frame, text=planet, variable=var)
        cb.pack(side="left")
        create_tooltip(cb, f"Toggle visibility of {planet}\nShows {planet} in the 3D plot.")
        def set_color(p=planet):
            color = colorchooser.askcolor(title=f"Choose color for {p}", initialcolor=planet_colors[p])[1]
            if color:
                planet_colors[p] = color
                update_preview()
        ttk.Button(frame, text="Color", command=set_color).pack(side="left")

    # Right panel with scrollbar
    right_panel = ttk.Frame(content_frame, style="TFrame")
    right_panel.grid(row=1, column=2, sticky="nsew", padx=20, pady=20)

    # Create a Canvas and Scrollbar for the right panel
    right_canvas = tk.Canvas(right_panel, bg=themes[current_theme]["bg"], highlightthickness=0)
    scrollbar = ttk.Scrollbar(right_panel, orient="vertical", command=right_canvas.yview)
    right_inner_frame = ttk.Frame(right_canvas, style="RightInner.TFrame")

    # Configure the canvas to scroll with the inner frame
    right_inner_frame.bind(
        "<Configure>",
        lambda e: right_canvas.configure(scrollregion=right_canvas.bbox("all"))
    )
    right_canvas.configure(yscrollcommand=scrollbar.set)

    # Pack the canvas and scrollbar
    scrollbar.pack(side="right", fill="y")
    right_canvas.pack(side="left", fill="both", expand=True)
    right_canvas.create_window((0, 0), window=right_inner_frame, anchor="nw")

    # Add widgets to the inner frame
    ttk.Label(right_inner_frame, text="Controls", font=("Arial", 14, "bold")).pack(pady=10)

    # Time slider
    ttk.Label(right_inner_frame, text="Time Navigation", font=("Arial", 14, "bold")).pack(pady=5)
    time_var = tk.DoubleVar(value=ts.now().tt)
    time_slider = ttk.Scale(right_inner_frame, from_=ts.from_datetime(EPHEMERIS_START).tt,
                            to_=ts.from_datetime(EPHEMERIS_END).tt, variable=time_var,
                            orient=tk.HORIZONTAL, length=300)
    time_slider.pack(pady=5)
    create_tooltip(time_slider, "Slide to navigate time\nRanges from 1899 to 2053")
    time_display = tk.StringVar(value=ts.now().utc_strftime('%Y-%m-%d %H:%M UTC'))
    ttk.Label(right_inner_frame, textvariable=time_display, font=("Arial", 10)).pack(pady=5)

    ttk.Separator(right_inner_frame, orient="horizontal").pack(fill="x", pady=10)

    animate_var = tk.BooleanVar(value=False)
    real_time_var = tk.BooleanVar(value=False)
    animate_cb = ttk.Checkbutton(right_inner_frame, text="Engage Warp Animation", variable=animate_var)
    animate_cb.pack(pady=5)
    create_tooltip(animate_cb, "Start/stop animation\nMoves planets along their orbits over time.")
    ttk.Checkbutton(right_inner_frame, text="Real-Time Mode", variable=real_time_var).pack(pady=5)
    create_tooltip(animate_cb, "Toggle real-time mode\nShows current positions based on UTC time.")
    ttk.Label(right_inner_frame, text="Warp Speed (ms):").pack()
    speed_var = tk.DoubleVar(value=100)
    speed_slider = ttk.Scale(right_inner_frame, from_=20, to=300, orient=tk.HORIZONTAL,
                             variable=speed_var, length=200)
    speed_slider.pack(pady=5)
    create_tooltip(speed_slider, "Adjust animation speed\nLower values = faster updates (ms per frame).")
    ttk.Separator(right_inner_frame, orient="horizontal").pack(fill="x", pady=10)

    ttk.Label(right_inner_frame, text="Custom Orbit Range", font=("Arial", 14, "bold")).pack(pady=5)
    orbit_start_var = tk.StringVar(value="2025-08-15")
    ttk.Label(right_inner_frame, text="Start Date (YYYY-MM-DD):").pack()
    orbit_start_entry = ttk.Entry(right_inner_frame, textvariable=orbit_start_var, width=15)
    orbit_start_entry.pack(pady=5)
    orbit_end_var = tk.StringVar(value="2026-08-15")
    ttk.Label(right_inner_frame, text="End Date (YYYY-MM-DD):").pack()
    orbit_end_entry = ttk.Entry(right_inner_frame, textvariable=orbit_end_var, width=15)
    orbit_end_entry.pack(pady=5)
    ttk.Separator(right_inner_frame, orient="horizontal").pack(fill="x", pady=10)

    ttk.Label(right_inner_frame, text="Planet Size Zoom", font=("Arial", 14, "bold")).pack(pady=5)
    zoom_var = tk.DoubleVar(value=1.0)
    zoom_slider = ttk.Scale(right_inner_frame, from_=0.5, to=2.0, orient=tk.HORIZONTAL,
                            variable=zoom_var, length=200)
    zoom_slider.pack(pady=5)
    create_tooltip(zoom_slider, "Adjust planet sizes\nScales the visual size of planets in the plot.")
    ttk.Separator(right_inner_frame, orient="horizontal").pack(fill="x", pady=10)

    ttk.Label(right_inner_frame, text="View Angle", font=("Arial", 14, "bold")).pack(pady=5)
    elev_var = tk.DoubleVar(value=20)
    ttk.Label(right_inner_frame, text="Elevation:").pack()
    ttk.Scale(right_inner_frame, from_=-90, to=90, variable=elev_var, orient=tk.HORIZONTAL).pack(pady=5)
    azim_var = tk.DoubleVar(value=30)
    ttk.Label(right_inner_frame, text="Azimuth:").pack()
    ttk.Scale(right_inner_frame, from_=-180, to=180, variable=azim_var, orient=tk.HORIZONTAL).pack(pady=5)
    ttk.Separator(right_inner_frame, orient="horizontal").pack(fill="x", pady=10)

    ttk.Label(right_inner_frame, text="Theme", font=("Arial", 14, "bold")).pack(pady=5)
    theme_var = tk.StringVar(value="dark")
    theme_menu = ttk.OptionMenu(right_inner_frame, theme_var, "dark", "dark", "light",
                                command=lambda value: apply_theme(value))
    theme_menu.pack(pady=5)
    create_tooltip(theme_menu, "Switch themes\nChoose between dark and light UI styles.")
    ttk.Separator(right_inner_frame, orient="horizontal").pack(fill="x", pady=10)

    update_btn = ttk.Button(right_inner_frame, text="Update Plot", command=lambda: update_preview())
    update_btn.pack(pady=5)
    export_plot_btn = ttk.Button(right_inner_frame, text="Export Plot",
                                 command=lambda: export_plot(plot.fig))
    export_plot_btn.pack(pady=5)
    create_tooltip(export_plot_btn, "Save plot\nExports the current 3D view as an HTML file.")
    export_data_btn = ttk.Button(right_inner_frame, text="Export Orbit Data",
                                 command=lambda: export_orbit_data(orbit_positions_dict))
    export_data_btn.pack(pady=5)
    create_tooltip(export_data_btn, "Save orbit data\nExports planet positions to a CSV file.")
    ttk.Button(right_inner_frame, text="Save Settings", command=lambda: save_settings()).pack(pady=5)
    ttk.Button(right_inner_frame, text="Load Settings", command=lambda: load_settings()).pack(pady=5)
    status_var = tk.StringVar(value="Ready")
    status_label = ttk.Label(right_inner_frame, textvariable=status_var, font=("Arial", 12, "italic"))
    status_label.pack(pady=10)

    info_frame = ttk.Frame(right_inner_frame, style="TFrame")
    info_frame.pack(pady=10, fill="x")
    ttk.Label(info_frame, text="Planet Info", font=("Arial", 14, "bold")).pack()
    info_var = tk.StringVar(value="Select a planet from the plot")
    info_label = ttk.Label(info_frame, textvariable=info_var, font=("Arial", 10), wraplength=200)
    info_label.pack(pady=5)

    # Preview panel (center)
    preview_frame = tk.Frame(content_frame, bg=themes[current_theme]["root_bg"])
    preview_frame.grid(row=1, column=1, sticky="nsew", padx=20, pady=20)
    
    plot = PlanetPlot(preview_frame, planet_data, on_pick_callback=lambda name: update_info(name, plot))

    animating = False
    animation_t = None
    orbit_positions_dict = {}
    animation_thread = None

    def update_info(name, plot_instance):
        info = planet_data.get_planet_info(name)
        t = ts.tt(jd=time_var.get()) if not real_time_var.get() else ts.now()
        elements = get_orbital_elements(name, t)
        if info:
            info_var.set(f"{name}\nMass: {info['mass']} kg\nTemp: {info['temperature']} K\n"
                         f"Distance: {info['distance']} M km\nOrbit: {info['orbital_period']} days\n"
                         f"Semi-Major Axis: {elements['semi_major_axis']:.2f} AU\nEcc: {elements['eccentricity']:.3f}")
        else:
            info_var.set(f"{name}\nNo API data available")
        print(f"Updated info for {name}")

    def export_plot(fig):
        file_path = filedialog.asksaveasfilename(defaultextension=".html",
                                                filetypes=[("HTML files", "*.html"), ("All files", "*.*")])
        if file_path:
            fig.write_html(file_path)
            status_var.set(f"Plot exported to {file_path}")

    def export_orbit_data(orbit_data):
        file_path = filedialog.asksaveasfilename(defaultextension=".csv",
                                                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if file_path:
            with open(file_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Planet", "X (AU)", "Y (AU)", "Z (AU)"])
                for name, positions in orbit_data.items():
                    for x, y, z in positions.T:
                        writer.writerow([name, x, y, z])
            status_var.set(f"Orbit data exported to {file_path}")

    def save_settings():
        settings = {
            "planets": {p: v.get() for p, v in selected_planets.items()},
            "colors": planet_colors,
            "time_jd": time_var.get(),
            "zoom": zoom_var.get(),
            "elev": elev_var.get(),
            "azim": azim_var.get()
        }
        file_path = filedialog.asksaveasfilename(defaultextension=".json",
                                                filetypes=[("JSON files", "*.json")])
        if file_path:
            with open(file_path, 'w') as f:
                json.dump(settings, f)
            status_var.set(f"Settings saved to {file_path}")

    def load_settings():
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            with open(file_path, 'r') as f:
                settings = json.load(f)
            for p, v in settings["planets"].items():
                selected_planets[p].set(v)
            planet_colors.update(settings["colors"])
            time_var.set(settings["time_jd"])
            zoom_var.set(settings["zoom"])
            elev_var.set(settings["elev"])
            azim_var.set(settings["azim"])
            update_preview()
            status_var.set(f"Settings loaded from {file_path}")

    def animate_loop():
        nonlocal animation_t
        while animate_var.get():
            if real_time_var.get():
                update_preview()
            else:
                if animation_t is None:
                    animation_t = ts.tt(jd=time_var.get())
                next_dt = animation_t.utc_datetime() + timedelta(days=1)
                if next_dt > EPHEMERIS_END:
                    animate_var.set(False)
                    status_var.set("Animation stopped: Reached ephemeris limit")
                    break
                animation_t = ts.from_datetime(next_dt)
                update_preview()
            time.sleep(speed_var.get() / 1000)

    def start_animation():
        nonlocal animation_thread
        if animate_var.get() and animation_thread is None:
            animation_thread = threading.Thread(target=animate_loop, daemon=True)
            animation_thread.start()
        elif not animate_var.get() and animation_thread is not None:
            animation_thread = None

    animate_cb.config(command=start_animation)

    def update_preview(custom_t=None):
        nonlocal animation_t
        active_planets = [p for p, v in selected_planets.items() if v.get()]
        if not active_planets:
            status_var.set("No planets selected")
            plot.update_plot({}, {}, ts.now(), active_planets, zoom_var.get(), elev_var.get(), azim_var.get(), planet_colors)
            return

        try:
            if real_time_var.get():
                t = ts.now()
            elif custom_t:
                t = custom_t
            elif animate_var.get() and animation_t is not None:
                t = animation_t
            else:
                t = ts.tt(jd=time_var.get())
            time_display.set(t.utc_strftime('%Y-%m-%d %H:%M UTC'))
        except ValueError as e:
            status_var.set(str(e))
            return

        try:
            t_start_custom = parse_date_time(orbit_start_var.get(), "00:00")
            t_end_custom = parse_date_time(orbit_end_var.get(), "23:59")
            if t_start_custom is None or t_end_custom is None:
                raise ValueError("Invalid orbit range dates")
        except ValueError as e:
            status_var.set(str(e))
            return

        print(f"Active planets: {active_planets}")
        print(f"Orbit range: {t_start_custom.utc_strftime('%Y-%m-%d')} to {t_end_custom.utc_strftime('%Y-%m-%d')}")

        if not animate_var.get():
            global orbit_positions_dict
            orbit_positions_dict = {}
            for name in active_planets:
                orbit = calculate_orbit(name, t_start_custom.tt, t_end_custom.tt)
                if orbit.size > 0 and not np.all(orbit == 0):
                    orbit_positions_dict[name] = orbit
                    print(f"Orbit calculated for {name}: shape={orbit.shape}")
                else:
                    print(f"Failed to calculate orbit for {name}")

        positions = get_heliocentric_positions(active_planets, t)
        events = calculate_events(t)
        if events:
            status_var.set(f"Updated at {t.utc_strftime('%Y-%m-%d %H:%M UTC')}. Events: {[(p, e) for p, e in events]}")
        else:
            status_var.set(f"Updated at {t.utc_strftime('%Y-%m-%d %H:%M UTC')}. No events detected.")

        plot.update_plot(positions, orbit_positions_dict, t, active_planets, zoom_var.get(), elev_var.get(), azim_var.get(), planet_colors)

    # Bind slider to update preview
    time_slider.bind("<B1-Motion>", lambda e: update_preview(ts.tt(jd=time_var.get())))

    # Enable mouse wheel scrolling for the canvas
    def _on_mousewheel(event):
        right_canvas.yview_scroll(-1 * (event.delta // 120), "units")

    right_canvas.bind_all("<MouseWheel>", _on_mousewheel)  # For Windows
    right_canvas.bind_all("<Button-4>", lambda e: right_canvas.yview_scroll(-1, "units"))  # For Linux (scroll up)
    right_canvas.bind_all("<Button-5>", lambda e: right_canvas.yview_scroll(1, "units"))  # For Linux (scroll down)

    apply_theme("dark")
    update_preview()
    root.mainloop()

if __name__ == "__main__":
    run_planet_tracker()