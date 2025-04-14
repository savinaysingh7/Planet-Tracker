# --- START OF FILE main.py ---

import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser, scrolledtext
import numpy as np
from datetime import datetime, timedelta, UTC
import threading
import json
import random
import os
from planet_plot import PlanetPlot
from planet_data import planet_data  # Singleton instance
from planet_calculations import (
    ts, sun, EPHEMERIS_START, EPHEMERIS_END, parse_date_time,
    calculate_orbit, get_heliocentric_positions, get_orbital_elements,
    planet_dict, calculate_events, find_next_events
)

# --- Groq Integration ---
try:
    from groq import Groq, APIError
except ImportError:
    print("WARNING: 'groq' library not found. LLM features disabled.")
    print("Install it using: pip install groq")
    Groq = None
    APIError = None

# --- Tooltip Function ---
def create_tooltip(widget, text):
    """Create a tooltip for a widget."""
    tooltip = tk.Toplevel(widget)
    tooltip.wm_overrideredirect(True)
    # Position tooltip below and slightly to the right of the widget center
    widget.update_idletasks() # Ensure widget dimensions are known
    x = widget.winfo_rootx() + widget.winfo_width() // 2
    y = widget.winfo_rooty() + widget.winfo_height() + 5
    tooltip.wm_geometry(f"+{x}+{y}")

    label = tk.Label(tooltip, text=text, background="#ffffe0", relief="solid", borderwidth=1, justify=tk.LEFT)
    label.pack()
    tooltip.withdraw()

    # Debounce tooltip display/hide
    enter_id = None
    leave_id = None

    def show_tooltip(event):
        nonlocal enter_id, leave_id
        if leave_id:
            tooltip.after_cancel(leave_id)
            leave_id = None
        # Delay showing slightly
        enter_id = tooltip.after(500, tooltip.deiconify)

    def hide_tooltip(event):
        nonlocal enter_id, leave_id
        if enter_id:
            tooltip.after_cancel(enter_id)
            enter_id = None
        # Delay hiding slightly
        leave_id = tooltip.after(100, tooltip.withdraw)

    # Function to handle entering the tooltip itself to keep it visible
    def tooltip_enter(event):
        nonlocal leave_id
        if leave_id:
            tooltip.after_cancel(leave_id)
            leave_id = None

    # Function to handle leaving the tooltip
    def tooltip_leave(event):
        hide_tooltip(event) # Trigger the normal hide mechanism

    # Make sure the widget exists before binding
    if widget is not None and widget.winfo_exists():
        widget.bind("<Enter>", show_tooltip, add='+')
        widget.bind("<Leave>", hide_tooltip, add='+')
        # Allow keeping tooltip open if mouse moves onto it
        tooltip.bind("<Enter>", tooltip_enter, add='+')
        tooltip.bind("<Leave>", tooltip_leave, add='+')


# --- Main Application ---
def run_planet_tracker():
    """Main function to run the Planet Tracker GUI application."""
    root = tk.Tk()
    root.title("Planet Tracker: Galactic Nexus (LLM Enhanced)")
    root.geometry("1400x1000")
    root.minsize(1200, 800)
    root.resizable(True, True)
    root.configure(bg="#0a0a1a")

    # --- Groq Client Setup ---
    # !!! SECURITY WARNING: Hardcoded Key !!!
    groq_api_key = "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" # Exposed!
    groq_client = None
    llm_enabled = False
    if Groq and groq_api_key:
        try:
            if groq_api_key:
                groq_client = Groq(api_key=groq_api_key)
                llm_enabled = True
                print("Groq client initialized successfully.")
            else: print("WARNING: Hardcoded Groq API Key is empty. LLM disabled.")
        except Exception as e:
            print(f"Error initializing Groq client: {e}")
            messagebox.showerror("LLM Init Error", f"Failed to initialize Groq: {e}\nLLM disabled.")
    # ... (Else conditions remain) ...

    # --- Style and Theme setup ---
    style = ttk.Style()
    # style.theme_use('clam')

    themes = {
        "dark": {"bg": "#2e3f5b", "fg": "#00ffea", "root_bg": "#0a0a1a",
                 "text_bg": "#1e2a3f", "text_fg": "#e0e0ff",
                 "entry_bg": "#1e2a3f", "entry_fg": "#e0e0ff",
                 "btn_bg": "#3a5075", "btn_fg": "#ffffff",
                 "accent": "#00ffea"},
        "light": {"bg": "#e0e0e0", "fg": "#000000", "root_bg": "#ffffff",
                  "text_bg": "#ffffff", "text_fg": "#000000",
                  "entry_bg": "#fdfdfd", "entry_fg": "#000000",
                  "btn_bg": "#d0d0d0", "btn_fg": "#000000",
                  "accent": "#005f5f"}
    }
    current_theme = "dark"

    style.configure("TNotebook", background=themes[current_theme]["root_bg"])
    style.configure("TNotebook.Tab", background=themes[current_theme]["bg"], foreground=themes[current_theme]["fg"], padding=[10, 5])
    style.map("TNotebook.Tab", background=[("selected", themes[current_theme]["accent"])], foreground=[("selected", themes['dark']['btn_fg'])])
    style.configure("Status.TLabel", font=("Arial", 10, "italic"))
    style.configure("Header.TLabel", font=("Arial", 14, "bold"))
    style.configure("ColorSwatch.TLabel", borderwidth=1, relief="solid")

    color_swatches = {} # Needs to be defined before apply_theme uses it

    def apply_theme(theme):
        # ... (Implementation as before, ensure color_swatches dict exists before iterating) ...
        nonlocal current_theme
        current_theme = theme
        t = themes[theme]
        root.configure(bg=t["root_bg"])
        content_frame.configure(bg=t["root_bg"])
        title_label.configure(bg=t["root_bg"], fg=t["accent"]) # Use accent for title

        # Apply general styles
        style.configure("TFrame", background=t["bg"], relief="flat") # Use flat relief?
        style.configure("TLabel", background=t["bg"], foreground=t["fg"], font=("Arial", 10))
        style.configure("TCheckbutton", background=t["bg"], foreground=t["fg"], font=("Arial", 10))
        style.configure("TButton", background=t["btn_bg"], foreground=t["btn_fg"], font=("Arial", 10, "bold"), padding=5)
        style.map("TButton", background=[('active', t["accent"])]) # Button hover/active color
        style.configure("TEntry", fieldbackground=t["entry_bg"], foreground=t["entry_fg"])
        style.configure("TScale", background=t["bg"])

        # Specific components
        style.configure("TNotebook", background=t["root_bg"])
        style.configure("TNotebook.Tab", background=t["bg"], foreground=t["fg"], padding=[10, 5])
        style.map("TNotebook.Tab", background=[("selected", t["accent"])], foreground=[("selected", themes['dark']['btn_fg'] if theme == 'dark' else themes['light']['btn_fg'])])
        style.configure("Status.TLabel", background=t["bg"], foreground=t["fg"])
        style.configure("Header.TLabel", background=t["bg"], foreground=t["accent"]) # Accent for headers
        style.configure("ColorSwatch.TLabel", background=t["bg"]) # Background for swatch border

        # Update specific widget instances if needed
        chat_display.configure(bg=t["text_bg"], fg=t["text_fg"])
        progress_bar.configure(style="TProgressbar") # Ensure progress bar uses default ttk style for theme

        # Update color swatches in left panel
        if color_swatches: # Ensure dict is populated before using
            for planet, swatch in color_swatches.items():
                 swatch.configure(background=planet_colors.get(planet, '#808080')) # Update background color live

        # Refresh styles of widgets in Notebook tabs
        for tab_frame in right_notebook.tabs():
             # Check if the frame actually exists
             if root.nametowidget(tab_frame).winfo_exists():
                 frame_widget = root.nametowidget(tab_frame)
                 frame_widget.configure(style="TFrame")
                 for widget in frame_widget.winfo_children():
                      if widget.winfo_exists() and isinstance(widget, (ttk.Label, ttk.Checkbutton, ttk.Button, ttk.Entry, ttk.Scale, ttk.Separator, ttk.OptionMenu, ttk.Frame)):
                           widget_class = widget.winfo_class()
                           # Apply style only if it exists for that class
                           # Note: Styling complex widgets like OptionMenu fully requires more work
                           try:
                                if style.layout(widget_class): # Check if style is defined
                                     widget.configure(style=widget_class)
                           except tk.TclError:
                                pass # Ignore if style cannot be applied

    # --- Main content frame ---
    content_frame = tk.Frame(root, bg=themes[current_theme]["root_bg"])
    content_frame.pack(fill="both", expand=True, padx=10, pady=10)
    content_frame.grid_rowconfigure(1, weight=1)
    content_frame.grid_columnconfigure(0, weight=1) # Left
    content_frame.grid_columnconfigure(1, weight=4) # Center
    content_frame.grid_columnconfigure(2, weight=2) # Right

    # --- Title ---
    title_label = tk.Label(content_frame, text="Planet Tracker: Galactic Nexus",
                           font=("Arial", 24, "bold"), bg=themes[current_theme]["root_bg"],
                           fg=themes[current_theme]["accent"])
    title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20), sticky="ew")

    # --- Left panel: Planet selection ---
    left_panel = ttk.Frame(content_frame, style="TFrame", padding=10)
    left_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
    ttk.Label(left_panel, text="Solar System Bodies", style="Header.TLabel").pack(pady=(0,15), anchor="w")
    selected_planets = {planet: tk.BooleanVar(value=True) for planet in planet_data.get_all_planet_names()}
    planet_colors = {planet: planet_data.get_planet_color(planet) for planet in planet_data.get_all_planet_names()}
    # Populate after color_swatches is defined
    for planet, var in selected_planets.items():
        p_frame = ttk.Frame(left_panel, style="TFrame")
        p_frame.pack(fill="x", pady=3)
        swatch = tk.Label(p_frame, text="", width=2, background=planet_colors[planet], relief="solid", borderwidth=1)
        swatch.pack(side="left", padx=(0, 5))
        color_swatches[planet] = swatch
        cb = ttk.Checkbutton(p_frame, text=planet, variable=var, style="TCheckbutton")
        cb.pack(side="left", expand=True, fill="x")
        create_tooltip(cb, f"Toggle visibility of {planet}")
        def create_color_handler(p, s):
            def set_color():
                initial_c = planet_colors.get(p, '#808080')
                color_info = colorchooser.askcolor(title=f"Choose color for {p}", initialcolor=initial_c)
                if color_info and color_info[1]:
                    planet_colors[p] = color_info[1]
                    s.configure(background=color_info[1])
            return set_color
        color_btn = ttk.Button(p_frame, text="🎨", width=3, command=create_color_handler(planet, swatch), style="TButton")
        color_btn.pack(side="left", padx=(5, 0))
        create_tooltip(color_btn, f"Set color for {planet}")

    # --- Right Panel with Tabs ---
    right_panel = ttk.Frame(content_frame, style="TFrame", padding=(10, 0))
    right_panel.grid(row=1, column=2, sticky="nsew", padx=(10, 0))
    right_panel.grid_rowconfigure(0, weight=1)
    right_panel.grid_rowconfigure(1, weight=0)
    right_panel.grid_columnconfigure(0, weight=1)
    right_notebook = ttk.Notebook(right_panel, style="TNotebook")
    right_notebook.grid(row=0, column=0, sticky="nsew")
    # --- Create Tab Frames ---
    tab_time_orbits = ttk.Frame(right_notebook, padding=15, style="TFrame")
    tab_view_anim = ttk.Frame(right_notebook, padding=15, style="TFrame")
    tab_settings_export = ttk.Frame(right_notebook, padding=15, style="TFrame")
    tab_info_events = ttk.Frame(right_notebook, padding=15, style="TFrame")
    right_notebook.add(tab_time_orbits, text=' Time/Orbits ')
    right_notebook.add(tab_view_anim, text=' View/Animation ')
    right_notebook.add(tab_settings_export, text=' Settings/Export ')
    right_notebook.add(tab_info_events, text=' Info/Events ')

    # --- Populate Tab 1: Time/Orbits ---
    # ... (Content as before: Time Label, Display, Slider; Orbit Range Header, Labels, Entries) ...
    ttk.Label(tab_time_orbits, text="Time Navigation", style="Header.TLabel").pack(pady=5, anchor="w")
    time_var = tk.DoubleVar(value=ts.now().tt)
    time_display = tk.StringVar(value=ts.now().utc_strftime('%Y-%m-%d %H:%M UTC'))
    ttk.Label(tab_time_orbits, textvariable=time_display, font=("Arial", 10)).pack(pady=5, anchor="w")
    time_slider = ttk.Scale(tab_time_orbits, from_=ts.from_datetime(EPHEMERIS_START).tt,
                            to_=ts.from_datetime(EPHEMERIS_END).tt, variable=time_var,
                            orient=tk.HORIZONTAL, style="TScale")
    time_slider.pack(pady=(5,15), fill="x")
    create_tooltip(time_slider, "Slide to navigate time (1899-2053)")

    ttk.Separator(tab_time_orbits, orient="horizontal").pack(fill="x", pady=15)

    ttk.Label(tab_time_orbits, text="Orbit Display Range", style="Header.TLabel").pack(pady=5, anchor="w")
    orbit_start_var = tk.StringVar(value="2025-08-15")
    ttk.Label(tab_time_orbits, text="Start Date (YYYY-MM-DD):").pack(anchor="w")
    orbit_start_entry = ttk.Entry(tab_time_orbits, textvariable=orbit_start_var, width=15, style="TEntry")
    orbit_start_entry.pack(pady=5, anchor="w")
    create_tooltip(orbit_start_entry, "Start date for orbit lines/animation.")
    orbit_end_var = tk.StringVar(value="2026-08-15")
    ttk.Label(tab_time_orbits, text="End Date (YYYY-MM-DD):").pack(anchor="w")
    orbit_end_entry = ttk.Entry(tab_time_orbits, textvariable=orbit_end_var, width=15, style="TEntry")
    orbit_end_entry.pack(pady=5, anchor="w")
    create_tooltip(orbit_end_entry, "End date for orbit lines/animation.")

    # --- Populate Tab 2: View/Animation ---
    # ... (Content as before: View Settings Header, Zoom, Elevation, Azimuth Labels+Scales+Tooltips) ...
    ttk.Label(tab_view_anim, text="Plot View Settings", style="Header.TLabel").pack(pady=5, anchor="w")
    ttk.Label(tab_view_anim, text="Planet Size Zoom:").pack(anchor="w")
    zoom_var = tk.DoubleVar(value=1.0)
    zoom_slider = ttk.Scale(tab_view_anim, from_=0.1, to=5.0, orient=tk.HORIZONTAL, variable=zoom_var, style="TScale")
    zoom_slider.pack(pady=5, fill="x")
    create_tooltip(zoom_slider, "Adjust visual size of planets in the plot")

    ttk.Label(tab_view_anim, text="Camera Elevation:").pack(pady=(10, 0), anchor="w")
    elev_var = tk.DoubleVar(value=20)
    elev_scale = ttk.Scale(tab_view_anim, from_=-90, to=90, variable=elev_var, orient=tk.HORIZONTAL, style="TScale")
    elev_scale.pack(pady=5, fill="x")
    create_tooltip(elev_scale, "Set plot camera vertical angle (-90 to 90)")

    ttk.Label(tab_view_anim, text="Camera Azimuth:").pack(anchor="w")
    azim_var = tk.DoubleVar(value=30)
    azim_scale = ttk.Scale(tab_view_anim, from_=-180, to=180, variable=azim_var, orient=tk.HORIZONTAL, style="TScale")
    azim_scale.pack(pady=5, fill="x")
    create_tooltip(azim_scale, "Set plot camera horizontal angle (-180 to 180)")

    ttk.Separator(tab_view_anim, orient="horizontal").pack(fill="x", pady=15)

    ttk.Label(tab_view_anim, text="Animation Controls", style="Header.TLabel").pack(pady=5, anchor="w")
    animate_var = tk.BooleanVar(value=False)
    real_time_var = tk.BooleanVar(value=False)

    # ** Unified Animation Trigger Logic **
    def handle_animate_toggle():
        """Handles checkbox click: starts animation task only when checked ON."""
        if animate_var.get():
            # Trigger the animation task using the helper
            # Set initial status maybe? run_long_task does this too.
            add_chat_message("Bot", f"Animation request received for {orbit_start_var.get()} to {orbit_end_var.get()}.", tag="info_tag")
            run_long_task(compute_animation_frames)
        # else: # Optionally add message when unchecked, but don't stop running task
            # set_status("Animation mode disabled.")

    animate_cb = ttk.Checkbutton(tab_view_anim, text="Generate Animation", variable=animate_var,
                                style="TCheckbutton", command=handle_animate_toggle) # Use specific handler
    animate_cb.pack(pady=5, anchor="w")
    create_tooltip(animate_cb, "CHECK to generate animation for the orbit range\n(Opens in browser, can take time)")

    real_time_cb = ttk.Checkbutton(tab_view_anim, text="Use Real-Time for Plot", variable=real_time_var, style="TCheckbutton")
    real_time_cb.pack(pady=5, anchor="w")
    create_tooltip(real_time_cb, "Use current time for 'Update Plot'\n(Overrides time slider)")

    ttk.Label(tab_view_anim, text="Animation Speed (ms/frame):").pack(pady=(10,0), anchor="w")
    speed_var = tk.DoubleVar(value=100)
    speed_slider = ttk.Scale(tab_view_anim, from_=20, to=1000, orient=tk.HORIZONTAL, variable=speed_var, style="TScale")
    speed_slider.pack(pady=5, fill="x")
    create_tooltip(speed_slider, "Adjust animation frame duration (Lower = Faster)")

    # --- Populate Tab 3: Settings/Export ---
    # ... (Content as before: Appearance Header, Theme Label+Menu; Actions Header, Button Frame with Update/Export Buttons; App Settings Header, Settings Button Frame with Save/Load) ...
    ttk.Label(tab_settings_export, text="Appearance", style="Header.TLabel").pack(pady=5, anchor="w")
    theme_var = tk.StringVar(value="dark")
    ttk.Label(tab_settings_export, text="UI Theme:").pack(anchor="w")
    theme_menu = ttk.OptionMenu(tab_settings_export, theme_var, "dark", "dark", "light",
                                command=lambda value: apply_theme(value))
    theme_menu.pack(pady=5, anchor="w")
    create_tooltip(theme_menu, "Switch UI theme (Dark/Light)")

    ttk.Separator(tab_settings_export, orient="horizontal").pack(fill="x", pady=15)

    ttk.Label(tab_settings_export, text="Actions", style="Header.TLabel").pack(pady=5, anchor="w")
    btn_frame = ttk.Frame(tab_settings_export, style="TFrame")
    btn_frame.pack(fill="x", pady=10)
    update_btn = ttk.Button(btn_frame, text="Update Static Plot", command=lambda: run_long_task(update_preview), style="TButton")
    update_btn.pack(side="top", fill="x", pady=3)
    create_tooltip(update_btn, "Generate static plot for current time/settings\n(Opens in browser)")
    export_plot_btn = ttk.Button(btn_frame, text="Export Plot HTML", command=lambda: export_plot(plot.fig), style="TButton")
    export_plot_btn.pack(side="top", fill="x", pady=3)
    create_tooltip(export_plot_btn, "Save the last generated plot as HTML")
    export_data_btn = ttk.Button(btn_frame, text="Export Orbit CSV", command=lambda: export_orbit_data(orbit_positions_dict), style="TButton")
    export_data_btn.pack(side="top", fill="x", pady=3)
    create_tooltip(export_data_btn, "Save calculated orbit positions to CSV")

    ttk.Separator(tab_settings_export, orient="horizontal").pack(fill="x", pady=15)

    ttk.Label(tab_settings_export, text="App Settings", style="Header.TLabel").pack(pady=5, anchor="w")
    settings_btn_frame = ttk.Frame(tab_settings_export, style="TFrame")
    settings_btn_frame.pack(fill="x", pady=10)
    save_btn = ttk.Button(settings_btn_frame, text="Save Settings", command=lambda: save_settings(), style="TButton")
    save_btn.pack(side="left", padx=5, expand=True)
    create_tooltip(save_btn, "Save planets, colors, time, view etc. to a JSON file.")
    load_btn = ttk.Button(settings_btn_frame, text="Load Settings", command=lambda: load_settings(), style="TButton")
    load_btn.pack(side="left", padx=5, expand=True)
    create_tooltip(load_btn, "Load settings from a previously saved JSON file.")

    # --- Populate Tab 4: Info/Events ---
    # ... (Content as before: Info Header, Label; Events Header, Button) ...
    ttk.Label(tab_info_events, text="Body Information", style="Header.TLabel").pack(pady=5, anchor="w")
    info_var = tk.StringVar(value="Ask the chatbot for info (e.g., 'info Mars').")
    info_label = ttk.Label(tab_info_events, textvariable=info_var, justify=tk.LEFT, wraplength=250, style="TLabel")
    info_label.pack(pady=5, fill="x", anchor="w")

    ttk.Separator(tab_info_events, orient="horizontal").pack(fill="x", pady=15)

    ttk.Label(tab_info_events, text="Astronomical Events", style="Header.TLabel").pack(pady=5, anchor="w")
    events_btn = ttk.Button(tab_info_events, text="Show Upcoming Events", command=lambda: threading.Thread(target=show_upcoming_events, args=(False,), daemon=True).start(), style="TButton")
    events_btn.pack(pady=10, fill="x")
    create_tooltip(events_btn, "Calculate events for selected planets (next year)\n(Shows results in message box)")


    # --- Status Bar and Progress Bar Area ---
    status_frame = ttk.Frame(right_panel, style="TFrame")
    status_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
    status_frame.grid_columnconfigure(0, weight=1)
    status_var = tk.StringVar(value="Ready")
    status_label = ttk.Label(status_frame, textvariable=status_var, style="Status.TLabel")
    status_label.grid(row=0, column=0, sticky="ew", padx=5)
    progress_bar = ttk.Progressbar(status_frame, orient=tk.HORIZONTAL, mode='indeterminate', length=100)


    # --- Center Panel: Chatbot Interface ---
    # ... (Frame, ScrolledText, Input Frame, Entry, Button - setup as before) ...
    chat_frame = ttk.Frame(content_frame, style="TFrame", padding=10)
    chat_frame.grid(row=1, column=1, sticky="nsew", padx=(10, 10))
    chat_frame.grid_rowconfigure(0, weight=1)
    chat_frame.grid_rowconfigure(1, weight=0)
    chat_frame.grid_columnconfigure(0, weight=1)

    chat_display = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, state='disabled',
                                             font=("Arial", 11), relief="solid", borderwidth=1,
                                             bg=themes[current_theme]["text_bg"],
                                             fg=themes[current_theme]["text_fg"],
                                             padx=5, pady=5)
    chat_display.grid(row=0, column=0, sticky="nsew", pady=(0, 10))

    # Define chat tags after chat_display exists
    user_fg_color = themes[current_theme].get("accent", "#a0c0ff")
    chat_display.tag_configure("user_tag", font=("Arial", 11, "bold"), foreground=user_fg_color)
    chat_display.tag_configure("bot_tag", foreground=themes[current_theme]["text_fg"])
    chat_display.tag_configure("error_tag", foreground="red")
    chat_display.tag_configure("info_tag", foreground="grey", font=("Arial", 11, "italic"))

    input_frame = ttk.Frame(chat_frame, style="TFrame")
    input_frame.grid(row=1, column=0, sticky="ew")
    input_frame.grid_columnconfigure(0, weight=1)
    chat_input = ttk.Entry(input_frame, font=("Arial", 11), style="TEntry")
    chat_input.grid(row=0, column=0, sticky="ew", ipady=4)
    send_button = ttk.Button(input_frame, text="Send", command=lambda: handle_chat_message(), style="TButton")
    send_button.grid(row=0, column=1, padx=(5, 0))


    # --- PlanetPlot (Logic only) & Data Storage ---
    plot = PlanetPlot(None, planet_data)
    orbit_positions_dict = {}


    # --- Utility Functions (Threading, Status, Progress) ---
    job_running = threading.Lock() # Controls access to long tasks

    def run_long_task(target_func, args=()):
        """Manages running a long task in a thread with lock and progress bar."""
        if not job_running.acquire(blocking=False):
            add_chat_message("Bot", "System busy. Please wait for the current operation.", tag="error_tag")
            # If task was animation trigger, uncheck the box again if busy
            if target_func == compute_animation_frames:
                 root.after(100, lambda: animate_var.set(False))
            return

        progress_bar.grid(row=0, column=1, sticky="e", padx=5)
        progress_bar.start()
        readable_name = target_func.__name__.replace('_', ' ').replace('compute ', '').capitalize()
        set_status(f"Processing: {readable_name}...")

        def task_wrapper():
            try:
                target_func(*args) # Execute the actual task function
            except Exception as e:
                print(f"Error in background task {target_func.__name__}: {e}")
                # Let the target function handle setting final error status
            finally:
                root.after(0, cleanup_task) # Always schedule cleanup

        threading.Thread(target=task_wrapper, daemon=True).start()

    def cleanup_task():
        """Hides progress bar, releases lock (called via root.after)."""
        progress_bar.stop()
        progress_bar.grid_forget()
        if job_running.locked(): job_running.release()


    def set_status(message):
        """Safely updates status label from any thread."""
        root.after(0, lambda: status_var.set(message))


    # --- Chatbot Logic ---
    def add_chat_message(sender: str, message: str, tag: str = None):
        """Adds chat message with appropriate tag."""
        def _update_display_simple():
            if not chat_display.winfo_exists(): return
            chat_display.configure(state='normal')
            prefix = "You: " if sender == "User" else "Nexus: "
            line_tag = tag or ("user_tag" if sender == "User" else "bot_tag")
            chat_display.insert(tk.END, prefix + message + "\n", (line_tag,))
            chat_display.configure(state='disabled')
            chat_display.see(tk.END)
        root.after(0, _update_display_simple)

    def get_groq_response_worker(user_message):
        """Gets LLM response. Sets final status."""
        # ... (Implementation as before, ensuring final set_status call) ...
        system_prompt = (
            "You are 'Nexus', an assistant in the 'Planet Tracker: Galactic Nexus' app..." # Keep prompt concise
        )
        final_status = "LLM Error"
        try:
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                model="llama3-8b-8192", temperature=0.7, max_tokens=300
            )
            response = chat_completion.choices[0].message.content
            add_chat_message("Bot", response)
            final_status = "Ready"
        except APIError as e:
            # ... (Error handling as before) ...
            error_body = e.body.get('error', {}) if e.body else {}
            error_message = f"LLM API Error: {e.status_code} - {error_body.get('message', 'Unknown')}"
            print(error_message)
            add_chat_message("Bot", f"API Error ({e.status_code}). Try again?", tag="error_tag")
            final_status = f"LLM Error ({e.status_code})"
        except Exception as e:
            error_message = f"LLM connection error: {e}"
            print(error_message)
            add_chat_message("Bot", "Error contacting assistant.", tag="error_tag")
        finally:
             set_status(final_status)
             # Cleanup (lock release, progress bar) is handled by the calling wrapper


    def handle_chat_message(event=None):
        """Handles user chat input, routing to local commands or LLM."""
        user_message = chat_input.get().strip()
        if not user_message: return
        add_chat_message("User", user_message)
        chat_input.delete(0, tk.END)
        command = user_message.lower().split()
        if not command: return
        local_command_handled = False
        bot_response = None
        cmd_word = command[0]

        try:
            # --- Local Commands ---
            if cmd_word == "update" and len(command) > 1 and command[1] == "plot":
                run_long_task(update_preview) # Uses task runner
                local_command_handled = True
            elif cmd_word == "animate":
                if not any(selected_planets[p].get() for p in selected_planets):
                    bot_response = "Cannot animate: No planets selected."
                else:
                    # Set the checkbox state *before* starting the task
                    animate_var.set(True)
                    # Call the same handler as the checkbox click
                    handle_animate_toggle()
                local_command_handled = True
            elif cmd_word == "info":
                # ... (Info logic as before - fast enough) ...
                 if len(command) > 1:
                     # Join arguments for multi-word planets (e.g., 'Earth Moon Barycenter' if ever added)
                     planet_name = " ".join(c.capitalize() for c in command[1:])
                     if planet_name in planet_data.get_all_planet_names():
                         info = planet_data.get_planet_info(planet_name)
                         try:
                             t = ts.tt(jd=time_var.get()) if not real_time_var.get() else ts.now()
                             elements = get_orbital_elements(planet_name, t)
                             response_lines = [f"Data for {planet_name}:"]
                             if info:
                                response_lines.extend([
                                    f"  Radius: {info.get('radius', 'N/A')}", f"  Mass: {info.get('mass', 'N/A')}",
                                    f"  Avg Temp: {info.get('temperature', 'N/A')}", f"  Gravity: {info.get('gravity', 'N/A')}",
                                    f"  Orbit Period: {info.get('orbital_period', 'N/A')}", f"  Dist (AU): {info.get('distance', 'N/A')}"
                                ])
                             response_lines.append(f"  Semi-Major Axis: {elements.get('semi_major_axis', 0.0):.2f} AU")
                             response_lines.append(f"  Eccentricity: {elements.get('eccentricity', 0.0):.3f}")
                             bot_response = "\n".join(response_lines)
                             update_info(planet_name) # Update side panel too
                         except Exception as e:
                             bot_response = f"Could not retrieve full elements for {planet_name}: {e}"
                             print(f"Error in chat info elements: {e}")
                     else:
                         bot_response = f"Unknown body '{planet_name}'. Known: {', '.join(planet_data.get_all_planet_names())}"
                 else:
                     bot_response = "Usage: info [Planet Name]"
                 local_command_handled = True
            elif cmd_word == "upcoming" and len(command) > 1 and command[1] == "events":
                add_chat_message("Bot", "Checking events...", tag="info_tag")
                # Runs in basic thread, handles its own messaging/status
                threading.Thread(target=show_upcoming_events, args=(True,), daemon=True).start()
                local_command_handled = True
            elif cmd_word in ["help", "commands"]:
                # ... (Help text as before) ...
                 bot_response = ("Available commands:\n"
                              "- info [Planet Name]\n"
                              "- update plot\n"
                              "- animate\n"
                              "- upcoming events\n"
                              "- help / commands\n"
                              "Ask general space questions too!\n"
                              "Use GUI controls for settings.")
                 local_command_handled = True
            # Add other direct commands here if needed

        except Exception as e:
            bot_response = f"Error: {e}"
            set_status(f"Command Error: {e}")
            print(f"Chat Command Error: {e}")
            local_command_handled = True # Prevent sending error to LLM

        # --- Output or Call LLM ---
        if bot_response:
            add_chat_message("Bot", bot_response) # Already handled tag setting inside logic? Default bot tag OK.
            set_status("Ready")
        elif not local_command_handled: # Route to LLM if not handled locally
            if llm_enabled:
                if not job_running.acquire(blocking=False): # Check lock for LLM call
                    add_chat_message("Bot", "Busy. Please wait.", tag="error_tag")
                else: # Acquired lock, proceed
                    set_status("LLM is thinking...")
                    add_chat_message("Bot", "Nexus is thinking...", tag="info_tag")
                    progress_bar.grid(row=0, column=1, sticky="e", padx=5) # Show progress
                    progress_bar.start()
                    # Wrapper ensures cleanup even if worker errors
                    def llm_task_wrapper():
                        try: get_groq_response_worker(user_message)
                        finally: root.after(0, cleanup_task) # Schedule cleanup
                    threading.Thread(target=llm_task_wrapper, daemon=True).start()
            else: # LLM disabled fallback
                 fallback = random.choice(["LLM offline.", "Specific commands only: 'help'."])
                 add_chat_message("Bot", fallback, tag="error_tag")
                 set_status("Ready")

    # --- Bindings ---
    chat_input.bind("<Return>", handle_chat_message)
    send_button.configure(command=handle_chat_message)
    time_slider.bind("<ButtonRelease-1>", lambda e: run_long_task(update_preview, args=(ts.tt(jd=time_var.get()),)))


    # --- Core Application Functions ---
    # Functions like update_info, export_*, save/load_settings, show_upcoming_events
    # compute_animation_frames, update_preview should all now correctly:
    # 1. Run in the correct thread (directly, basic thread, or via run_long_task).
    # 2. Update the status bar using set_status() at appropriate points.
    # 3. Add chat messages ONLY where necessary, using add_chat_message().
    # 4. Set a FINAL status message just before they finish or error out.
    # 5. NOT call cleanup_task() themselves if run via run_long_task().
    # (Code for these functions as defined in previous response, adjusted for final status setting)
    # --- Function Implementations (Mostly unchanged from previous state, ensuring correct status setting) ---

    def update_info(name):
        # ... (Implementation unchanged, doesn't need status updates) ...
        info = planet_data.get_planet_info(name)
        try:
            t = ts.tt(jd=time_var.get()) if not real_time_var.get() else ts.now()
            elements = get_orbital_elements(name, t)
            if info:
                info_text = (f"{name}\n" + "\n".join([f"  {k.replace('_',' ').capitalize()}: {v}" for k, v in info.items()])) # Dynamic info
                info_text += f"\n  Semi-Major: {elements.get('semi_major_axis', 0.0):.2f} AU\n  Ecc: {elements.get('eccentricity', 0.0):.3f}"
                info_var.set(info_text)
            else: info_var.set(f"{name}\nNo data available")
        except Exception as e: info_var.set(f"Error getting data for {name}: {e}")


    def export_plot(fig):
        # ... (Implementation unchanged, just sets final status) ...
        if not hasattr(fig, 'data') or not fig.data:
            set_status("No plot to export.")
            messagebox.showwarning("Export Plot", "Please generate plot first.")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".html", filetypes=[("HTML files", "*.html")])
        if file_path:
            try:
                fig.write_html(file_path)
                set_status("Plot exported successfully.")
            except Exception as e: set_status(f"Export failed: {e}"); messagebox.showerror("Export Error", f"{e}")


    def export_orbit_data(orbit_data):
        # ... (Implementation unchanged, just sets final status) ...
         if not orbit_data:
             set_status("No orbit data calculated.")
             messagebox.showwarning("Export Data", "Please generate plot/animation first.")
             return
         file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
         if file_path:
             try:
                 with open(file_path, 'w', newline='') as csvfile:
                    # ... (CSV writing loop) ...
                    writer = csv.writer(csvfile)
                    writer.writerow(["Planet", "Point Index", "X (AU)", "Y (AU)", "Z (AU)"])
                    for name, positions in orbit_data.items():
                         if isinstance(positions, np.ndarray) and positions.ndim == 2 and positions.shape[0] == 3:
                             for i in range(positions.shape[1]): writer.writerow([name, i, positions[0, i], positions[1, i], positions[2, i]])
                 set_status("Orbit data exported.")
             except Exception as e: set_status(f"Export failed: {e}"); messagebox.showerror("Export Error", f"{e}")


    def save_settings():
        # ... (Implementation unchanged, sets final status) ...
        settings = {"planets": {p: v.get() for p, v in selected_planets.items()}, "colors": planet_colors, **{ # Other settings
                    "time_jd": time_var.get(),"zoom": zoom_var.get(),"elev": elev_var.get(), "azim": azim_var.get(),
                    "theme": current_theme,"orbit_start": orbit_start_var.get(), "orbit_end": orbit_end_var.get(),
                    "animate": animate_var.get(), "real_time": real_time_var.get(),"speed": speed_var.get()}}
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file_path:
             try:
                 with open(file_path, 'w') as f: json.dump(settings, f, indent=4)
                 set_status("Settings saved.")
                 add_chat_message("Bot", f"Settings saved to {os.path.basename(file_path)}.", tag="info_tag")
             except Exception as e: set_status(f"Save failed: {e}"); messagebox.showerror("Save Error", f"{e}")


    def load_settings():
        # ... (Implementation unchanged, sets final status, updates swatches) ...
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
             try:
                 with open(file_path, 'r') as f: settings = json.load(f)
                 for p, v in settings.get("planets", {}).items():
                      if p in selected_planets: selected_planets[p].set(v)
                 loaded_colors = settings.get("colors", {})
                 for p, swatch in color_swatches.items(): # Update swatches too
                     if p in loaded_colors: planet_colors[p] = loaded_colors[p]
                     else: planet_colors[p] = planet_data.get_planet_color(p) # Default if missing
                     swatch.configure(background=planet_colors[p])
                 # Set other variables from settings dict
                 time_var.set(settings.get("time_jd", ts.now().tt)); zoom_var.set(settings.get("zoom", 1.0))
                 elev_var.set(settings.get("elev", 20)); azim_var.set(settings.get("azim", 30))
                 orbit_start_var.set(settings.get("orbit_start", "2025-08-15")); orbit_end_var.set(settings.get("orbit_end", "2026-08-15"))
                 animate_var.set(settings.get("animate", False)); real_time_var.set(settings.get("real_time", False))
                 speed_var.set(settings.get("speed", 100))
                 loaded_theme = settings.get("theme", "dark")
                 if loaded_theme in themes: theme_var.set(loaded_theme); apply_theme(loaded_theme)
                 set_status("Settings loaded.")
                 add_chat_message("Bot", f"Settings loaded from {os.path.basename(file_path)}.", tag="info_tag")
             except Exception as e: set_status(f"Load failed: {e}"); messagebox.showerror("Load Error", f"{e}")


    def show_upcoming_events(respond_in_chat=False):
        """Calculates events, sets status, messages appropriately."""
        # ... (Implementation mostly unchanged, ensures set_status called at end) ...
        final_status = "Event check failed"
        msg = ""
        try:
            set_status("Calculating upcoming events...") # Initial status
            active_planets = [p for p, v in selected_planets.items() if v.get()]
            if not active_planets:
                msg = "No planets selected."
                final_status = "Ready"
            else:
                # ... (calculate events) ...
                t_start = ts.now()
                t_end = ts.utc(t_start.utc_datetime().year + 1, t_start.utc_datetime().month, t_start.utc_datetime().day)
                events = find_next_events(active_planets, t_start, t_end)
                if events:
                    event_text = "\n".join([f"- {p}: {e} on {d}" for p, e, d in events])
                    msg = f"Upcoming events (next year):\n{event_text}"
                    final_status = "Events calculated."
                else:
                    msg = "No major events found in the next year."
                    final_status = "No events found."
        except Exception as e:
             msg = f"Error calculating events: {e}"
             print(f"Event calculation error: {e}")
        finally:
             set_status(final_status) # Set final status before showing message
             tag = "error_tag" if "Error" in msg else "info_tag" if msg else None
             if respond_in_chat and msg: add_chat_message("Bot", msg, tag=tag)
             elif not respond_in_chat and msg: root.after(0, lambda m=msg: messagebox.showinfo("Upcoming Events", m))


    def compute_animation_frames():
        """Computes animation (run via run_long_task). Sets final status."""
        # ... (Implementation mostly unchanged, sets final_status variable) ...
        final_status = "Animation Failed"
        try:
            set_status("Verifying animation settings...")
            active_planets = [p for p, v in selected_planets.items() if v.get()]
            if not active_planets: raise ValueError("No planets selected")
            t_start = parse_date_time(orbit_start_var.get(), "00:00"); t_end = parse_date_time(orbit_end_var.get(), "23:59")
            if t_start is None or t_end is None or t_start.tt >= t_end.tt: raise ValueError("Invalid orbit range")
            if (t_end.tt - t_start.tt) > (365.25 * 50): raise ValueError("Max 50 year animation range")

            set_status("Calculating orbits...")
            anim_orbit_positions = {}
            orbit_steps = 500
            for name in active_planets:
                 orbit = calculate_orbit(name, t_start.tt, t_end.tt, num_points=orbit_steps)
                 if orbit.size > 0 and not np.all(orbit == 0): anim_orbit_positions[name] = orbit

            set_status("Calculating frames...")
            num_frames = max(100, min(1000, int((t_end.tt - t_start.tt) * 2)))
            times = ts.linspace(t_start, t_end, num_frames)
            positions_list = [get_heliocentric_positions(active_planets, t) for t in times]

            set_status("Launching animation...")
            root.after(0, lambda pl=positions_list, tl=list(times), orb=anim_orbit_positions: plot.create_animation(
                pl, tl, orb, active_planets, speed_var.get(), zoom_var.get(), elev_var.get(), azim_var.get(), planet_colors
            ))
            add_chat_message("Bot", "Animation generated.", tag="info_tag")
            final_status = "Animation launched."
        except ValueError as e: final_status = f"Animation Error: {e}"; add_chat_message("Bot", final_status, tag="error_tag"); root.after(0, lambda: animate_var.set(False))
        except Exception as e: print(f"Anim Error: {e}"); final_status = "Animation Failed"; add_chat_message("Bot", final_status, tag="error_tag"); root.after(0, lambda: animate_var.set(False))
        finally: set_status(final_status)


    def update_preview(custom_t=None):
        """Updates static plot (run via run_long_task). Sets final status."""
        # ... (Implementation mostly unchanged, sets final_status variable) ...
        final_status = "Plot Update Failed"
        try:
            set_status("Preparing plot...")
            active_planets = [p for p, v in selected_planets.items() if v.get()]
            if not active_planets: raise ValueError("No planets selected")
            target_t = ts.now() if real_time_var.get() else (custom_t or ts.tt(jd=time_var.get()))
            root.after(0, lambda t=target_t: time_display.set(t.utc_strftime('%Y-%m-%d %H:%M UTC')))
            t_start = parse_date_time(orbit_start_var.get(), "00:00"); t_end = parse_date_time(orbit_end_var.get(), "23:59")
            if t_start is None or t_end is None or t_start.tt >= t_end.tt: raise ValueError("Invalid orbit range")

            set_status("Calculating positions...")
            positions = get_heliocentric_positions(active_planets, target_t)
            set_status("Calculating orbits...")
            current_orbit_positions = {}
            orbit_steps = 500
            for name in active_planets:
                orbit = calculate_orbit(name, t_start.tt, t_end.tt, num_points=orbit_steps)
                if orbit.size > 0 and not np.all(orbit == 0): current_orbit_positions[name] = orbit
            global orbit_positions_dict; orbit_positions_dict = current_orbit_positions.copy()
            events = calculate_events(target_t)

            set_status("Generating plot...")
            root.after(0, lambda pos=positions, orb=current_orbit_positions, t=target_t: plot.update_plot(
                pos, orb, t, active_planets, events, zoom_var.get(), elev_var.get(), azim_var.get(), planet_colors))
            event_str = f" Events: {[(p, e) for p, e in events]}" if events else ""
            final_status = f"Plot ready ({target_t.utc_strftime('%H:%M')}){event_str}"
        except ValueError as e: final_status = f"Plot Error: {e}"; add_chat_message("Bot", final_status, tag="error_tag")
        except Exception as e: print(f"Plot Error: {e}"); final_status = "Plot Update Failed"; add_chat_message("Bot", final_status, tag="error_tag")
        finally: set_status(final_status)


    # --- Initial Setup & Main Loop ---
    apply_theme("dark")
    set_status("Ready. Use controls or chat ('help').")

    # Mousewheel setup as before
    def _on_mousewheel(event):
        widget = root.winfo_containing(event.x_root, event.y_root)
        w = widget; is_over_chat = False
        while w:
            if w == chat_display: is_over_chat = True; break
            w = w.master
        if is_over_chat and chat_display.winfo_exists():
             # Simplified scroll direction check
             scroll_dir = -1 if (event.num == 4 or event.delta > 0) else 1
             chat_display.yview_scroll(scroll_dir, "units")
    root.bind_all("<MouseWheel>", _on_mousewheel)
    root.bind_all("<Button-4>", _on_mousewheel)
    root.bind_all("<Button-5>", _on_mousewheel)

    root.mainloop()


if __name__ == "__main__":
    run_planet_tracker()

# --- END OF FILE main.py ---