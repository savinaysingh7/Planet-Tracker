# --- START OF FULL CORRECTED FILE main.py ---

import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser, scrolledtext
import numpy as np
from datetime import datetime, timedelta, UTC
import threading
import json
from typing import Optional, Callable # Added Callable for type hinting
import random
import os
import logging
import sys # Import sys for fallback exit/ephemeris error handling

# --- Logging Setup ---
# Setup logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) - Basic config here, can be customized
# Read level from environment variable, default to INFO
log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
numeric_level = getattr(logging, log_level_name, logging.INFO) # Fallback to INFO if level invalid
# Format includes timestamp, level, thread name, and message
log_format = '%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s'
# Configure root logger - affects all loggers unless they specify otherwise
logging.basicConfig(level=numeric_level, format=log_format)
# Get logger specifically for this application module
logger = logging.getLogger(__name__)
logger.info(f"Logging level set to: {log_level_name}")


# --- Attempt to Import Custom Modules ---
# Encapsulate imports that might fail due to missing files or init errors
try:
    from planet_plot import PlanetPlot
    from planet_data import planet_data # Singleton instance (already initialized or None)
    # Ensure planet_data initialized successfully
    if planet_data is None:
         # Logged within planet_data, raise here to prevent proceeding if it's critical
         raise ImportError("PlanetData failed to initialize. Cannot proceed.")

    from skyfield.timelib import Time # Specific import for type hints and usage

    # FIX: Added 'earth', 'ephem_start_jd', 'ephem_end_jd' to the import list here
    from planet_calculations import (
        ts, sun, earth, ephem_start_jd, ephem_end_jd, # Ensure ephem bounds are imported
        EPHEMERIS_START, EPHEMERIS_END, parse_date_time,
        calculate_orbit, get_heliocentric_positions, get_orbital_elements,
        calculate_events, find_next_events
    )
    # Check if calculations module loaded its critical components
    # FIX: Added checks for ephem bounds
    if ts is None or sun is None or earth is None or ephem_start_jd is None or ephem_end_jd is None:
         missing = [name for name, var in {'ts':ts, 'sun':sun, 'earth':earth, 'ephem_start_jd':ephem_start_jd, 'ephem_end_jd':ephem_end_jd}.items() if var is None]
         raise ImportError(f"Core components from planet_calculations failed to load: {', '.join(missing)}")

except ImportError as e:
     logger.critical(f"Failed to import core dependency: {e}. Application cannot start.", exc_info=True)
     # Try showing a Tkinter error message if possible, otherwise exit
     try:
         root_fallback = tk.Tk(); root_fallback.withdraw()
         messagebox.showerror("Initialization Error", f"Missing or failed core component:\n{e}\n\nCheck logs and dependencies.", parent=root_fallback)
         root_fallback.destroy()
     except Exception: pass # Ignore if Tkinter itself fails here
     sys.exit(f"Core Import Error: {e}")
except SystemExit as e:
     # Catch SystemExit if raised by planet_calculations during ephemeris load failure
     logger.critical(f"Caught SystemExit during initialization: {e}")
     try:
         root_fallback = tk.Tk(); root_fallback.withdraw()
         messagebox.showerror("Initialization Error", f"Ephemeris loading failed:\n{e}\n\nPlease check the ephemeris file and logs.", parent=root_fallback)
         root_fallback.destroy()
     except Exception: pass
     sys.exit(f"Initialization Error: {e}") # Re-exit after showing message
except Exception as e:
     # Catch any other unexpected error during initial imports/setup
     logger.critical(f"Unexpected error during initial imports: {e}", exc_info=True)
     try:
         root_fallback = tk.Tk(); root_fallback.withdraw()
         messagebox.showerror("Critical Startup Error", f"An unexpected error occurred during startup:\n{e}\n\nCheck logs.", parent=root_fallback)
         root_fallback.destroy()
     except Exception: pass
     sys.exit(f"Unexpected Startup Error: {e}")


# --- Groq Integration ---
# Placed after core imports to ensure logging is likely set up
LLM_ENABLED = False
try:
    from groq import Groq, APIError
    logger.info("Python 'groq' library found.")
    # Attempt initialization later inside PlanetTrackerApp.__init__ after config/API key loaded
except ImportError:
    logger.warning("'groq' library not found. LLM features will be disabled.")
    logger.info("Install it using: pip install groq")
    Groq = None
    APIError = None


# --- Tooltip Function (Improved Safety Checks) ---
def create_tooltip(widget, text):
    """Create a tooltip for a given widget with improved safety."""
    # Basic validation of the widget itself
    if not isinstance(widget, tk.Widget) or not widget.winfo_exists():
        logger.warning(f"Cannot create tooltip for invalid or destroyed widget: {widget}")
        return None

    try:
        tooltip = tk.Toplevel(widget)
        tooltip.wm_overrideredirect(True) # No window decorations
    except Exception as e:
        # Handle cases where widget might be destroyed before Toplevel created
        logger.error(f"Failed to create Toplevel for tooltip (widget might be destroyed): {e}")
        return None

    # Store reference to prevent garbage collection issues in callbacks
    tooltip.widget_ref = widget

    label = tk.Label(tooltip, text=text, background="#ffffe0", relief="solid", borderwidth=1, justify=tk.LEFT, wraplength=300)
    label.pack(ipadx=2, ipady=2)
    tooltip.withdraw() # Start hidden

    # Debounce mechanism variables
    enter_id = None
    leave_id = None
    widget_hover = False
    tooltip_hover = False

    # Improved positioning logic (needs widget dimensions)
    def position_tooltip():
         # Check widget and tooltip exist before accessing geometry
         if not widget or not widget.winfo_exists() or not tooltip or not tooltip.winfo_exists():
             return
         widget.update_idletasks() # Ensure widget geometry is up-to-date
         # Get geometry relative to the screen
         x = widget.winfo_rootx() + widget.winfo_width() // 2
         y = widget.winfo_rooty() + widget.winfo_height() + 5 # Below widget
         screen_width = widget.winfo_screenwidth(); screen_height = widget.winfo_screenheight()
         tooltip.update_idletasks() # Ensure tooltip size is known
         tip_width = tooltip.winfo_width(); tip_height = tooltip.winfo_height()

         # Adjust x to keep tooltip on screen
         if x + tip_width > screen_width: x = screen_width - tip_width - 5
         if x < 0: x = 5
         # Adjust y (try above if below goes off screen)
         if y + tip_height > screen_height: y = widget.winfo_rooty() - tip_height - 5
         if y < 0: y = 5
         tooltip.wm_geometry(f"+{x}+{y}")

    # Enhanced scheduler/canceller with existence checks
    def schedule(action: Callable, delay_ms: int):
         if tooltip and tooltip.winfo_exists():
              try: return tooltip.after(delay_ms, action)
              except Exception as e: logger.warning(f"Tooltip 'after' scheduling error: {e}")
         return None
    def cancel_schedule(schedule_id):
        if schedule_id and tooltip and tooltip.winfo_exists():
            try: tooltip.after_cancel(schedule_id)
            except Exception as e: logger.warning(f"Tooltip 'after_cancel' error: {e}")

    # Debounced show/hide logic
    def show_tooltip_debounced():
        nonlocal enter_id; enter_id = None
        # Double check hover state and widget existence before showing
        if (widget_hover or tooltip_hover) and tooltip and tooltip.winfo_exists() and widget and widget.winfo_exists():
             position_tooltip()
             try: tooltip.deiconify()
             except Exception as e: logger.warning(f"Error deiconifying tooltip: {e}")

    def hide_tooltip_debounced():
        nonlocal leave_id; leave_id = None
        if not widget_hover and not tooltip_hover and tooltip and tooltip.winfo_exists():
             try: tooltip.withdraw()
             except Exception as e: logger.warning(f"Error withdrawing tooltip: {e}")

    # Event handlers
    def on_enter(event):
        nonlocal enter_id, leave_id, widget_hover
        widget_hover = True
        cancel_schedule(leave_id); leave_id = None
        if not enter_id and tooltip and tooltip.winfo_exists() and tooltip.state() == 'withdrawn':
             enter_id = schedule(show_tooltip_debounced, 700)
    def on_leave(event):
        nonlocal enter_id, leave_id, widget_hover
        widget_hover = False
        cancel_schedule(enter_id); enter_id = None
        if not leave_id: leave_id = schedule(hide_tooltip_debounced, 200)
    def on_tooltip_enter(event):
        nonlocal leave_id, tooltip_hover
        tooltip_hover = True
        cancel_schedule(leave_id); leave_id = None
    def on_tooltip_leave(event):
         nonlocal leave_id, tooltip_hover
         tooltip_hover = False
         if not leave_id: leave_id = schedule(hide_tooltip_debounced, 200)

    # Widget Destroy callback to clean up the tooltip
    # Use lambda to capture the current tooltip reference
    def on_widget_destroy(event, t=tooltip):
         # logger.debug(f"Widget {event.widget} destroyed, cleaning up tooltip {t}")
         if t and t.winfo_exists(): t.destroy()

    # Bind events carefully, checking widget existence again
    if widget and widget.winfo_exists():
        try:
            widget.bind("<Enter>", on_enter, add='+')
            widget.bind("<Leave>", on_leave, add='+')
            tooltip.bind("<Enter>", on_tooltip_enter, add='+')
            tooltip.bind("<Leave>", on_tooltip_leave, add='+')
            # Ensure tooltip is destroyed if parent widget is destroyed
            widget.bind("<Destroy>", on_widget_destroy, add='+')
        except tk.TclError as e:
             logger.warning(f"Could not bind tooltip events for {widget}: {e}. Cleaning up tooltip.")
             if tooltip and tooltip.winfo_exists(): tooltip.destroy()
             return None
    else:
        # If widget somehow became invalid between start and now
        logger.warning("Tooltip target widget became invalid before bindings could be set.")
        if tooltip and tooltip.winfo_exists(): tooltip.destroy()
        return None

    return tooltip # Return the tooltip object for potential external management


# --- Main Application Class ---
class PlanetTrackerApp:
    """Main application class for the Planet Tracker."""

    def __init__(self, root):
        self.root = root
        self.groq_client = None
        self.llm_enabled = LLM_ENABLED # Initial value from global scope
        self.job_running_lock = threading.Lock()
        self.current_theme = "dark"
        self.orbit_positions_dict = {}
        self.plot = None
        self.selected_planets = {}
        self.planet_colors = {}
        self.color_swatches = {}

        # --- Initialize GUI Variables ---
        # Ensure initial types/values match expected widget usage
        self.time_var = tk.DoubleVar(value=ts.now().tt) # Default to current time JD
        self.time_display = tk.StringVar(value="Initializing...") # Set properly later
        self.orbit_start_var = tk.StringVar(value="2025-01-01") # Sensible default
        self.orbit_end_var = tk.StringVar(value="2026-01-01")   # Sensible default
        self.zoom_var = tk.DoubleVar(value=1.0)
        self.elev_var = tk.DoubleVar(value=25.0)
        self.azim_var = tk.DoubleVar(value=45.0)
        self.animate_var = tk.BooleanVar(value=False)
        self.real_time_var = tk.BooleanVar(value=False)
        self.speed_var = tk.DoubleVar(value=50.0) # Animation speed (ms)
        self.theme_var = tk.StringVar(value=self.current_theme)
        self.status_var = tk.StringVar(value="Initializing application...")
        self.info_var = tk.StringVar(value="Select body or use chat for info...") # Panel in Tab 4

        # --- Placeholder Widget References (assigned in _create_widgets) ---
        self.content_frame = None
        self.title_label = None
        self.chat_display = None
        self.chat_input = None
        self.progress_bar = None
        self.right_notebook = None
        self.time_slider = None # Reference for slider bindings
        self.style = None
        self.themes = {} # Populated in _initialize_app

        logger.info("Starting Planet Tracker Application...")
        self._initialize_app_core() # Setup non-widget components (LLM, styles, plot)
        self._create_widgets()      # Build GUI elements
        self._apply_theme(self.current_theme) # Apply theme after widgets exist
        self._post_init_setup()     # Final steps (bindings, initial state updates)
        self.set_status("Ready. Use GUI controls or chat ('help').")
        logger.info("Application GUI initialized and ready.")

    def _initialize_app_core(self):
        """Initialize non-GUI components like styles, theme data, LLM client, and plot."""
        logger.info("Initializing application core components...")
        self.root.title("Planet Tracker: Galactic Nexus (LLM Enhanced)")
        self.root.geometry("1400x1000")
        self.root.minsize(1200, 800) # Minimum practical size
        # Register the close window handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # --- Style and Theme Definition ---
        self.style = ttk.Style()
        try:
            # 'clam', 'alt', 'default', 'classic' are common - 'clam' often looks good
            self.style.theme_use('clam')
            logger.debug("Using 'clam' ttk theme.")
        except tk.TclError:
            logger.warning(f"Failed to set 'clam' theme (may not be available on this system: {sys.platform}), using default ttk theme.")
            # Use default theme if clam fails
            default_theme = self.style.theme_use()
            logger.info(f"Using default ttk theme: '{default_theme}'")


        # Theme definitions (using V2 colors)
        self.themes = {
            "dark": {"bg": "#2e3f5b", "fg": "#e0e0ff", "root_bg": "#0a0a1a", # Main fg brighter
                     "text_bg": "#1e2a3f", "text_fg": "#e0e0ff",
                     "entry_bg": "#1e2a3f", "entry_fg": "#e0e0ff", "entry_insert": "#e0e0ff",
                     "btn_bg": "#3a5075", "btn_fg": "#ffffff",
                     "accent": "#00ffea", "accent_fg": "#000000", # Bright cyan accent
                     "hdr_fg": "#90e0ef", "stat_fg": "#a0b0c0", # Lighter header, subdued status
                     "plot_bg": "#0a0a1a", "plot_fg": "#e0e0ff", # For potential embedded plot elements
                     "prog_trough": "#202030", "prog_bar": "#00ffea"}, # Progress bar colors

            "light": {"bg": "#e8e8e8", "fg": "#000000", "root_bg": "#ffffff",
                      "text_bg": "#ffffff", "text_fg": "#000000",
                      "entry_bg": "#fdfdfd", "entry_fg": "#000000", "entry_insert": "#000000",
                      "btn_bg": "#d0d0d0", "btn_fg": "#000000",
                      "accent": "#007f7f", "accent_fg": "#ffffff", # Dark cyan accent
                      "hdr_fg": "#004f4f", "stat_fg": "#505050",
                      "plot_bg": "#ffffff", "plot_fg": "#000000",
                      "prog_trough": "#d0d0d0", "prog_bar": "#007f7f"}
        }

        # Base style configuration (applied more specifically in _apply_theme)
        self.style.configure("TNotebook", tabmargins=[2, 5, 2, 0])
        self.style.configure("TNotebook.Tab", padding=[10, 5], font=("Arial", 10))
        self.style.configure("Status.TLabel", font=("Arial", 9, "italic")) # Style for status bar label
        self.style.configure("Header.TLabel", font=("Arial", 12, "bold"))  # Style for section headers
        # Define named style for progress bar
        self.style.configure("custom.Horizontal.TProgressbar", thickness=10)

        # --- Groq Client Setup ---
        global LLM_ENABLED # Allow modification of global flag
        groq_api_key = os.getenv("GROQ_API_KEY")
        # Provide a clear placeholder if no key is intended
        hardcoded_default_key = "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" # Set to None explicitly, or replace "gsk_..." with your placeholder/actual default ONLY FOR LOCAL TESTING

        if not groq_api_key and hardcoded_default_key:
             groq_api_key = hardcoded_default_key
             logger.warning("Using hardcoded default Groq API Key. "
                            "Set the GROQ_API_KEY environment variable for better security and management.")
        elif not groq_api_key:
            logger.warning("Groq API Key not found in GROQ_API_KEY environment variable or hardcoded default. LLM disabled.")
            # Ensure groq_api_key is None if no key was found
            groq_api_key = None

        # Initialize client only if library exists and a key was found
        if Groq and groq_api_key:
            logger.info("Attempting to initialize Groq client...")
            try:
                self.groq_client = Groq(api_key=groq_api_key)
                # Quick check: list available models to verify key/connection
                models_list = self.groq_client.models.list()
                if models_list.data:
                    logger.info(f"Groq client initialized successfully. Available models include: {models_list.data[0].id}")
                    LLM_ENABLED = True # Update global flag
                else:
                     logger.warning("Groq client initialized, but failed to retrieve model list. Check API key permissions.")
                     LLM_ENABLED = False # Treat as disabled if models cannot be listed
            except APIError as e:
                logger.error(f"Groq API Error during initialization: {e.status_code} - {getattr(e, 'body', 'No body details')}")
                messagebox.showerror("LLM Initialization Error", f"Failed to initialize Groq API (Error {e.status_code}).\nCheck your API key and connection.\nLLM features disabled.", parent=self.root)
                LLM_ENABLED = False
            except Exception as e:
                logger.error(f"Unexpected error initializing Groq client: {e}", exc_info=True)
                messagebox.showerror("LLM Initialization Error", f"Unexpected error initializing Groq:\n{e}\nLLM features disabled.", parent=self.root)
                LLM_ENABLED = False
        elif not Groq:
             # Already logged warning about library missing
             LLM_ENABLED = False
        elif not groq_api_key:
            # Already logged warning about missing key
             LLM_ENABLED = False

        self.llm_enabled = LLM_ENABLED # Set instance variable based on final status

        # --- Initialize PlanetPlot ---
        try:
             # Check if planet_data is valid before passing
             if planet_data is None:
                  raise RuntimeError("PlanetData global instance is None.")
             self.plot = PlanetPlot(self.root, planet_data) # Pass the initialized singleton
             logger.info("PlanetPlot instance created.")
        except Exception as e:
            logger.critical(f"Failed to initialize PlanetPlot: {e}", exc_info=True)
            messagebox.showerror("Initialization Error", f"Could not initialize the plotting component:\n{e}", parent=self.root)
            # This is critical, application can't function without the plot module
            self.root.destroy()
            sys.exit("Fatal: PlanetPlot initialization failed.")

    def _apply_theme(self, theme_name: str):
        """Applies the selected theme settings to GUI widgets."""
        if theme_name not in self.themes:
            logger.warning(f"Theme '{theme_name}' not found. Using current theme '{self.current_theme}'.")
            return
        if not self.style:
             logger.error("Cannot apply theme: ttk.Style object not initialized.")
             return

        logger.info(f"Applying theme: {theme_name}")
        self.current_theme = theme_name
        t = self.themes[theme_name] # Get theme colors/settings dictionary

        try: # Wrap in try-except as widgets might not exist during initial call or shutdown
            # Apply theme to root window and main content frame
            if self.root and self.root.winfo_exists(): self.root.configure(bg=t["root_bg"])
            if self.content_frame and self.content_frame.winfo_exists(): self.content_frame.configure(bg=t["root_bg"])
            if self.title_label and self.title_label.winfo_exists(): self.title_label.configure(bg=t["root_bg"], fg=t["hdr_fg"])

            # --- Configure ttk Widget Styles ---
            self.style.configure("TFrame", background=t["bg"])
            self.style.configure("TLabel", background=t["bg"], foreground=t["fg"], font=("Arial", 10))
            self.style.configure("TCheckbutton", background=t["bg"], foreground=t["fg"], font=("Arial", 10))
            # Indicator color can make checkboxes match theme better
            # self.style.map("TCheckbutton", indicatorcolor=[('selected', t["accent"]), ('!selected', t['fg'])])

            self.style.configure("TButton", background=t["btn_bg"], foreground=t["btn_fg"], font=("Arial", 10, "bold"), padding=5, borderwidth=1)
            # Map button states for visual feedback
            self.style.map("TButton",
                        background=[('active', t["accent"]), ('pressed', '!disabled', t["accent"]), ('disabled', t['stat_fg'])],
                        foreground=[('active', t['accent_fg']), ('pressed', '!disabled', t['accent_fg']), ('disabled', t['fg'])])

            self.style.configure("TEntry", fieldbackground=t["entry_bg"], foreground=t["entry_fg"], insertcolor=t["entry_insert"])
            # Styling TScale is notoriously platform-dependent; basic background might work
            self.style.configure("TScale", background=t["bg"])
            self.style.map("TScale", troughcolor=[('!disabled', t['prog_trough'])], background=[('!disabled', t['btn_bg'])])

            # Configure specific named styles used in the app
            self.style.configure("TNotebook", background=t["root_bg"]) # Background of area behind tabs
            self.style.configure("TNotebook.Tab", background=t["bg"], foreground=t["fg"], padding=[10, 5])
            self.style.map("TNotebook.Tab", background=[("selected", t["accent"])], foreground=[("selected", t['accent_fg'])])

            self.style.configure("Status.TLabel", background=t["bg"], foreground=t["stat_fg"], font=("Arial", 9, "italic"))
            self.style.configure("Header.TLabel", background=t["bg"], foreground=t["hdr_fg"], font=("Arial", 12, "bold"))
            self.style.configure("ColorSwatch.TLabel", background=t["bg"]) # Standard tk Label, handled below

            # Configure progress bar style
            self.style.configure("custom.Horizontal.TProgressbar", troughcolor=t['prog_trough'], background=t['prog_bar'])
            if self.progress_bar and self.progress_bar.winfo_exists():
                self.progress_bar.configure(style="custom.Horizontal.TProgressbar")


            # --- Configure Standard Tk Widgets (non-ttk) ---
            # ScrolledText (Chat Display) needs direct configuration
            if self.chat_display and self.chat_display.winfo_exists():
                self.chat_display.configure(
                    bg=t["text_bg"], fg=t["text_fg"],
                    insertbackground=t["entry_insert"], # Cursor color
                    selectbackground=t["accent"],      # Selection background color
                    selectforeground=t["accent_fg"]     # Selection text color
                )
                # Update chat tag colors to match theme
                user_fg = t.get("hdr_fg", "#a0c0ff") # User messages distinct color
                self.chat_display.tag_configure("user_tag", foreground=user_fg)
                self.chat_display.tag_configure("bot_tag", foreground=t["text_fg"])
                self.chat_display.tag_configure("info_tag", foreground=t["stat_fg"])
                # error_tag foreground remains hardcoded red - usually appropriate

            # Color swatches (tk.Label)
            if self.color_swatches:
                 for planet, swatch in self.color_swatches.items():
                     if swatch and swatch.winfo_exists():
                         current_color = self.planet_colors.get(planet, '#808080') # Use stored color
                         swatch.configure(background=current_color)


            # --- Refresh Widget Styles within Notebook Tabs ---
            # Required for theme changes to affect existing widgets in inactive tabs
            if self.right_notebook and self.right_notebook.winfo_exists():
                self.root.update_idletasks() # Ensure geometry is calculated before iterating
                for tab_id_widget in self.right_notebook.tabs(): # Iterate through widget names of tabs
                    try:
                        frame_widget = self.root.nametowidget(tab_id_widget)

                        if frame_widget and frame_widget.winfo_exists():
                             frame_widget.configure(style="TFrame") # Update tab frame style
                             # Recursively update children widgets
                             for widget in frame_widget.winfo_children():
                                 if widget.winfo_exists():
                                     try: # Apply style based on widget class, ignore errors for non-ttk widgets
                                         style_name = widget.winfo_class()
                                         if style_name.startswith("T"): # Basic check for ttk widget
                                             widget.configure(style=style_name)
                                         elif isinstance(widget, tk.Label) and style_name == "Label":
                                             # Handle specific tk Labels if needed, e.g., headers/status within tabs
                                             # Check if it uses a named style like Header or Status
                                             if widget.winfo_name() == "header_label": # Hypothetical check by name if needed
                                                 widget.configure(style="Header.TLabel") # Re-apply named style
                                             elif widget.cget("style") in ["Header.TLabel", "Status.TLabel"]:
                                                  pass # Already handled by named styles
                                             else:
                                                 # Apply base tk Label theming (this part might need refinement)
                                                 widget.configure(bg=t['bg'], fg=t['fg']) # Basic colors
                                     except tk.TclError: pass # Ignore style errors for tk or complex widgets
                    except (tk.TclError, KeyError) as e: # Catch errors finding/configuring widget
                         logger.debug(f"Error processing tab {tab_id_widget} during theme apply: {e}")
                    except Exception as e: logger.error(f"Error reapplying theme to widgets in tab {tab_id_widget}: {e}", exc_info=False)

            logger.debug(f"Theme '{theme_name}' applied successfully.")

        except Exception as e:
             # Catch errors during theme application (e.g., if a widget reference is invalid)
             logger.error(f"Error occurred during theme application for '{theme_name}': {e}", exc_info=True)


    def _create_widgets(self):
        """Creates and lays out all GUI widgets."""
        logger.debug("Creating widgets...")

        # --- Main Content Frame ---
        self.content_frame = tk.Frame(self.root) # Use standard Frame for root container
        # Apply background color from theme in _apply_theme
        self.content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        # Configure grid weights for responsiveness
        self.content_frame.grid_rowconfigure(1, weight=1)    # Content row expands vertically
        self.content_frame.grid_columnconfigure(0, weight=1, minsize=200) # Left Panel
        self.content_frame.grid_columnconfigure(1, weight=4, minsize=400) # Center Panel (Plot/Chat)
        self.content_frame.grid_columnconfigure(2, weight=2, minsize=300) # Right Panel (Controls)

        # --- Title ---
        self.title_label = tk.Label(self.content_frame, text="Planet Tracker: Galactic Nexus", font=("Arial", 24, "bold"))
        # Theme colors applied in _apply_theme
        self.title_label.grid(row=0, column=0, columnspan=3, pady=(0, 15), sticky="ew")

        # --- Left Panel: Planet Selection ---
        left_panel = ttk.Frame(self.content_frame, style="TFrame", padding=10)
        left_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        ttk.Label(left_panel, text="Celestial Bodies", style="Header.TLabel").pack(pady=(0,10), anchor="w")

        # Populate from PlanetData singleton
        # Ensure planet_data is valid before using
        if planet_data is None:
            logger.critical("Cannot create planet list: PlanetData instance is not available.")
            ttk.Label(left_panel, text="Error: Planet data unavailable.", foreground="red").pack()
            # Application might be unusable, but let GUI load to show the error at least
            all_body_names = []
        else:
            all_body_names = planet_data.get_all_planet_names()

        self.selected_planets = {planet: tk.BooleanVar(value=True) for planet in all_body_names}
        self.planet_colors = {planet: planet_data.get_planet_color(planet) for planet in all_body_names} if planet_data else {}
        self.color_swatches = {} # Initialize empty dict for swatches

        # Scrollable frame for planet list (using basic Frame + potential future Scrollbar)
        # TODO: Add a ttk.Scrollbar if the list becomes very long
        planet_list_container = ttk.Frame(left_panel)
        planet_list_container.pack(fill="both", expand=True)

        for planet, var in self.selected_planets.items():
            p_frame = ttk.Frame(planet_list_container, style="TFrame") # Frame for each planet row
            p_frame.pack(fill="x", pady=2)

            # Swatch (use standard tk Label for simple colored square)
            swatch = tk.Label(p_frame, text="", width=2, relief="solid", borderwidth=1)
            swatch.configure(background=self.planet_colors.get(planet, "#808080")) # Use .get() with fallback
            swatch.pack(side="left", padx=(0, 5))
            self.color_swatches[planet] = swatch # Store reference to the swatch widget

            # Checkbox
            cb = ttk.Checkbutton(p_frame, text=planet, variable=var, style="TCheckbutton")
            cb.pack(side="left", expand=True, fill="x", padx=(0, 5))
            create_tooltip(cb, f"Toggle visibility of {planet}")

            # Color Picker Button Logic (using closure to capture planet name and swatch)
            def _create_color_handler(p_name, swatch_widget):
                def _set_color():
                    initial_color = self.planet_colors.get(p_name, '#808080') # Current color as initial
                    # Use colorchooser from tkinter
                    try:
                         # Provide root window as parent for modal behavior
                         result = colorchooser.askcolor(parent=self.root, title=f"Choose color for {p_name}", initialcolor=initial_color)
                         chosen_color_info = result if result and result[1] else None # askcolor returns (rgb_tuple, hex_string) or None

                         if chosen_color_info:
                              chosen_hex = chosen_color_info[1] # Get the hex string (#RRGGBB)
                              self.planet_colors[p_name] = chosen_hex
                              if swatch_widget.winfo_exists(): swatch_widget.configure(background=chosen_hex)
                              logger.info(f"Color updated for {p_name}: {chosen_hex}")
                              # Potentially trigger plot update if desired, or wait for explicit update
                              # self._run_long_task(self._update_preview)
                    except tk.TclError as e:
                         # Handles cases like window manager issues or dialog being closed abruptly
                         logger.error(f"TclError opening color chooser for {p_name}: {e}", exc_info=True)
                         if self.root and self.root.winfo_exists(): # Show error if main window still exists
                             messagebox.showerror("Color Chooser Error", f"Could not open color chooser for {p_name}.\n({e})", parent=self.root)
                    except Exception as e: # Catch any other unexpected error
                         logger.error(f"Unexpected error during color selection for {p_name}: {e}", exc_info=True)
                         if self.root and self.root.winfo_exists():
                             messagebox.showerror("Error", f"An unexpected error occurred during color selection for {p_name}.", parent=self.root)

                return _set_color

            color_handler = _create_color_handler(planet, swatch)
            color_btn = ttk.Button(p_frame, text="Set", width=4, command=color_handler, style="TButton")
            color_btn.pack(side="right") # Align to the right of the row
            create_tooltip(color_btn, f"Choose display color for {planet}")

        # --- Right Panel: Controls & Info (Tabs) ---
        right_panel = ttk.Frame(self.content_frame, style="TFrame", padding=(5, 0))
        right_panel.grid(row=1, column=2, sticky="nsew", padx=(5, 0))
        right_panel.grid_rowconfigure(0, weight=1) # Notebook area expands
        right_panel.grid_rowconfigure(1, weight=0) # Status bar fixed height
        right_panel.grid_columnconfigure(0, weight=1)

        # Notebook for organizing controls
        self.right_notebook = ttk.Notebook(right_panel, style="TNotebook")
        self.right_notebook.grid(row=0, column=0, sticky="nsew", pady=(0,5))

        # Create frames for each tab
        self.tab_time_orbits = ttk.Frame(self.right_notebook, padding=15, style="TFrame")
        self.tab_view_anim = ttk.Frame(self.right_notebook, padding=15, style="TFrame")
        self.tab_settings_export = ttk.Frame(self.right_notebook, padding=15, style="TFrame")
        self.tab_info_events = ttk.Frame(self.right_notebook, padding=15, style="TFrame")

        # Add tabs to the notebook
        self.right_notebook.add(self.tab_time_orbits, text=' Time / Orbits ')
        self.right_notebook.add(self.tab_view_anim, text=' View / Animation ')
        self.right_notebook.add(self.tab_settings_export, text=' Settings / Export ')
        self.right_notebook.add(self.tab_info_events, text=' Info / Events ')

        # --- Populate Tab 1: Time & Orbit Range ---
        ttk.Label(self.tab_time_orbits, text="Time Navigation", style="Header.TLabel").pack(pady=(0, 5), anchor="w")
        # Set initial time display based on variable value (will be accurate JD from calculations module)
        try: self.time_display.set(ts.tt(jd=self.time_var.get()).utc_strftime('%Y-%m-%d %H:%M UTC'))
        except Exception as e: logger.error(f"Failed to set initial time display value: {e}"); self.time_display.set("Error")
        ttk.Label(self.tab_time_orbits, textvariable=self.time_display, font=("Arial", 10)).pack(pady=(0, 5), anchor="w")

        # Time Slider - Determine bounds from ephemeris safely
        try:
            # Use the IMPORTED ephemeris bounds now
            t_slider_start_obj = ts.tt(jd=ephem_start_jd) # Use actual ephem bounds
            t_slider_end_obj = ts.tt(jd=ephem_end_jd)
            slider_start_yr = t_slider_start_obj.utc_datetime().year
            slider_end_yr = t_slider_end_obj.utc_datetime().year
            tooltip_text = f"Slide to navigate time\n({slider_start_yr} – {slider_end_yr})"
            slider_min = ephem_start_jd
            slider_max = ephem_end_jd
        except Exception as e:
            # Should not happen now if imports worked, but keep fallback
            logger.error(f"Could not determine slider range from imported ephemeris bounds: {e}", exc_info=True)
            slider_min = ts.from_datetime(EPHEMERIS_START).tt
            slider_max = ts.from_datetime(EPHEMERIS_END).tt
            tooltip_text = f"Slide to navigate time\n({EPHEMERIS_START.year} – {EPHEMERIS_END.year})"

        # Add handler to update the time display label WHILE sliding
        def _update_time_display_from_slider(value):
             if self.real_time_var.get(): return
             if self.root and self.root.winfo_exists():
                 self.root.after(0, self._update_time_label_only, float(value))

        # Create the slider
        self.time_slider = ttk.Scale(self.tab_time_orbits, from_=slider_min, to=slider_max,
                                     variable=self.time_var, orient=tk.HORIZONTAL,
                                     style="TScale", length=250,
                                     command=_update_time_display_from_slider)
        self.time_slider.pack(pady=(5, 15), fill="x")
        create_tooltip(self.time_slider, tooltip_text)

        # Binding: Trigger the *heavy* plot update only on slider release
        self.time_slider.bind("<ButtonRelease-1>", self._on_time_slider_release)

        # --- Orbit Display Range Section ---
        ttk.Separator(self.tab_time_orbits, orient="horizontal").pack(fill="x", pady=15)
        ttk.Label(self.tab_time_orbits, text="Orbit Display Range", style="Header.TLabel").pack(pady=5, anchor="w")

        ttk.Label(self.tab_time_orbits, text="Start Date (YYYY-MM-DD):").pack(anchor="w")
        orbit_start_entry = ttk.Entry(self.tab_time_orbits, textvariable=self.orbit_start_var, width=15, style="TEntry")
        orbit_start_entry.pack(pady=(0,5), anchor="w")
        create_tooltip(orbit_start_entry, "Start date for calculating and displaying orbit lines (inclusive).")

        ttk.Label(self.tab_time_orbits, text="End Date (YYYY-MM-DD):").pack(anchor="w")
        orbit_end_entry = ttk.Entry(self.tab_time_orbits, textvariable=self.orbit_end_var, width=15, style="TEntry")
        orbit_end_entry.pack(pady=(0,5), anchor="w")
        create_tooltip(orbit_end_entry, "End date for calculating and displaying orbit lines (inclusive).")

        # --- Populate Tab 2: View & Animation ---
        ttk.Label(self.tab_view_anim, text="Plot View Settings", style="Header.TLabel").pack(pady=(0, 5), anchor="w")

        ttk.Label(self.tab_view_anim, text="Planet Size Zoom:").pack(anchor="w")
        zoom_slider = ttk.Scale(self.tab_view_anim, from_=0.1, to=5.0, orient=tk.HORIZONTAL, variable=self.zoom_var, style="TScale", length=200)
        zoom_slider.pack(pady=(0, 5), fill="x")
        create_tooltip(zoom_slider, "Adjust visual size multiplier for planets (markers).")

        ttk.Label(self.tab_view_anim, text="Camera Elevation (-90° to 90°):").pack(pady=(10, 0), anchor="w")
        elev_scale = ttk.Scale(self.tab_view_anim, from_=-90, to=90, variable=self.elev_var, orient=tk.HORIZONTAL, style="TScale", length=200)
        elev_scale.pack(pady=(0, 5), fill="x")
        create_tooltip(elev_scale, "Set plot camera vertical viewing angle (degrees from XY plane).")

        ttk.Label(self.tab_view_anim, text="Camera Azimuth (-180° to 180°):").pack(anchor="w")
        azim_scale = ttk.Scale(self.tab_view_anim, from_=-180, to=180, variable=self.azim_var, orient=tk.HORIZONTAL, style="TScale", length=200)
        azim_scale.pack(pady=(0, 5), fill="x")
        create_tooltip(azim_scale, "Set plot camera horizontal rotation angle (degrees around Z axis).")

        ttk.Separator(self.tab_view_anim, orient="horizontal").pack(fill="x", pady=15)
        ttk.Label(self.tab_view_anim, text="Animation & Time Mode", style="Header.TLabel").pack(pady=(0, 5), anchor="w")

        # Command links to handler methods
        animate_cb = ttk.Checkbutton(self.tab_view_anim, text="Generate Animation", variable=self.animate_var,
                                style="TCheckbutton", command=self._handle_animate_toggle)
        animate_cb.pack(pady=(5,0), anchor="w")
        create_tooltip(animate_cb, "Check to generate an animation of the Orbit Display Range.\n(Opens in browser, may take time to calculate)")

        real_time_cb = ttk.Checkbutton(self.tab_view_anim, text="Use Real-Time for Plot Updates",
                                       variable=self.real_time_var, style="TCheckbutton", command=self._toggle_real_time_mode)
        real_time_cb.pack(pady=(0,5), anchor="w")
        create_tooltip(real_time_cb, "Check to use current system time for 'Update Static Plot'.\n(Overrides time slider when checked)")

        ttk.Label(self.tab_view_anim, text="Animation Speed (ms/frame):").pack(pady=(5,0), anchor="w")
        speed_slider = ttk.Scale(self.tab_view_anim, from_=10, to=500, orient=tk.HORIZONTAL, variable=self.speed_var, style="TScale", length=200)
        speed_slider.pack(pady=(0, 5), fill="x")
        create_tooltip(speed_slider, "Adjust animation playback frame duration (Lower = Faster). Affects generation process.")

        # --- Populate Tab 3: Settings & Export ---
        ttk.Label(self.tab_settings_export, text="Appearance", style="Header.TLabel").pack(pady=(0, 5), anchor="w")
        ttk.Label(self.tab_settings_export, text="UI Theme:").pack(anchor="w")
        theme_menu = ttk.OptionMenu(self.tab_settings_export, self.theme_var, self.current_theme,
                                    *list(self.themes.keys()), # Use themes defined in init
                                    command=self._apply_theme, style="TButton") # Style as button or TCombobox? Using TButton style here
        theme_menu.pack(pady=(0, 15), anchor="w")
        create_tooltip(theme_menu, "Switch UI color theme (Dark/Light).")

        ttk.Separator(self.tab_settings_export, orient="horizontal").pack(fill="x", pady=15)
        ttk.Label(self.tab_settings_export, text="Plot Actions", style="Header.TLabel").pack(pady=5, anchor="w")
        plot_btn_frame = ttk.Frame(self.tab_settings_export, style="TFrame")
        plot_btn_frame.pack(fill="x", pady=5)

        update_btn = ttk.Button(plot_btn_frame, text="Update Static Plot", command=self._trigger_plot_update, style="TButton")
        update_btn.pack(side="top", fill="x", pady=3)
        create_tooltip(update_btn, "Generate static plot for the current time/settings.\n(Uses slider time unless Real-Time is checked).\n(Opens in browser)")

        export_plot_btn = ttk.Button(plot_btn_frame, text="Export Plot as HTML", command=self._export_plot, style="TButton")
        export_plot_btn.pack(side="top", fill="x", pady=3)
        create_tooltip(export_plot_btn, "Save the *last generated* plot as an HTML file.")

        export_data_btn = ttk.Button(plot_btn_frame, text="Export Orbit Data as CSV", command=self._export_orbit_data, style="TButton")
        export_data_btn.pack(side="top", fill="x", pady=3)
        create_tooltip(export_data_btn, "Save calculated orbit positions from the last plot update to a CSV file.")

        ttk.Separator(self.tab_settings_export, orient="horizontal").pack(fill="x", pady=15)
        ttk.Label(self.tab_settings_export, text="Application Settings", style="Header.TLabel").pack(pady=5, anchor="w")
        settings_btn_frame = ttk.Frame(self.tab_settings_export, style="TFrame")
        settings_btn_frame.pack(fill="x", pady=5)

        save_btn = ttk.Button(settings_btn_frame, text="Save Settings", command=self._save_settings, style="TButton")
        save_btn.pack(side="left", padx=(0,5), expand=True, fill='x')
        create_tooltip(save_btn, "Save current planets, colors, time, view settings etc. to a JSON file.")

        load_btn = ttk.Button(settings_btn_frame, text="Load Settings", command=self._load_settings, style="TButton")
        load_btn.pack(side="left", padx=(5,0), expand=True, fill='x')
        create_tooltip(load_btn, "Load settings from a previously saved JSON file.")

        # --- Populate Tab 4: Info & Events ---
        ttk.Label(self.tab_info_events, text="Body Information", style="Header.TLabel").pack(pady=(0, 5), anchor="w")
        # Wraplength ensures text wraps within the tab width
        info_label_widget = ttk.Label(self.tab_info_events, textvariable=self.info_var, justify=tk.LEFT, wraplength=280, style="TLabel", font=("Arial", 9)) # Slightly smaller font
        info_label_widget.pack(pady=(0,15), fill="x", anchor="w")

        ttk.Separator(self.tab_info_events, orient="horizontal").pack(fill="x", pady=15)
        ttk.Label(self.tab_info_events, text="Astronomical Events", style="Header.TLabel").pack(pady=5, anchor="w")

        # Run event calculation in a thread to avoid blocking GUI
        # Lambda ensures current state of `respond_in_chat=False` is captured
        events_btn = ttk.Button(self.tab_info_events, text="Show Upcoming Events (Next Year)",
                               command=lambda: threading.Thread(target=self._show_upcoming_events, args=(False,), daemon=True).start(),
                               style="TButton")
        events_btn.pack(pady=10, fill="x")
        create_tooltip(events_btn, "Calculate major conjunctions/oppositions for selected planets within the next year.\n(Shows results in a popup message box)")


        # --- Status Bar & Progress Bar Area (Bottom of Right Panel) ---
        status_frame = ttk.Frame(right_panel, style="TFrame")
        status_frame.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        status_frame.grid_columnconfigure(0, weight=1) # Status label expands
        status_frame.grid_columnconfigure(1, weight=0) # Progress bar fixed width

        status_label = ttk.Label(status_frame, textvariable=self.status_var, style="Status.TLabel", anchor="w")
        status_label.grid(row=0, column=0, sticky="ew", padx=(5, 0))

        # Progress bar - Initially hidden, shown during long tasks
        self.progress_bar = ttk.Progressbar(status_frame, orient=tk.HORIZONTAL, mode='indeterminate', length=100, style="custom.Horizontal.TProgressbar")
        # Gridded/ungridded dynamically by _run_long_task / _cleanup_task


        # --- Center Panel: Chatbot Interface ---
        chat_frame = ttk.Frame(self.content_frame, style="TFrame", padding=10)
        chat_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 5))
        chat_frame.grid_rowconfigure(0, weight=1) # Chat display expands vertically
        chat_frame.grid_rowconfigure(1, weight=0) # Input area fixed height
        chat_frame.grid_columnconfigure(0, weight=1) # Display expands horizontally

        # Use ScrolledText widget for automatic scrollbars
        self.chat_display = scrolledtext.ScrolledText(
             chat_frame, wrap=tk.WORD, state='disabled', # Start disabled, enable to add text
             font=("Arial", 10), relief="solid", borderwidth=1, padx=5, pady=5,
             # Background/foreground set by _apply_theme
        )
        self.chat_display.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

        # Define text tags for styling messages (colors applied by theme)
        self.chat_display.tag_configure("user_tag", font=("Arial", 10, "bold")) # Bold for user input
        self.chat_display.tag_configure("bot_tag") # Default style for bot
        self.chat_display.tag_configure("error_tag", foreground="red") # Red for errors
        self.chat_display.tag_configure("info_tag", font=("Arial", 10, "italic")) # Italic for info messages

        # Input Frame for Entry and Send Button
        input_frame = ttk.Frame(chat_frame, style="TFrame")
        input_frame.grid(row=1, column=0, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1) # Entry expands
        input_frame.grid_columnconfigure(1, weight=0) # Button fixed width

        self.chat_input = ttk.Entry(input_frame, font=("Arial", 11), style="TEntry")
        self.chat_input.grid(row=0, column=0, sticky="ew", padx=(0,5), ipady=3) # Internal padding
        # Bind Enter key to send message function
        self.chat_input.bind("<Return>", self._handle_chat_message)

        send_button = ttk.Button(input_frame, text="Send", command=self._handle_chat_message, style="TButton")
        send_button.grid(row=0, column=1) # Automatically aligns right due to previous column weight

        logger.debug("Widget creation complete.")

    def _post_init_setup(self):
        """Perform setup tasks after all widgets are created and theme applied."""
        logger.debug("Running post-initialization setup...")
        # Update initial time display label accurately based on loaded variable
        self._update_time_label_only(self.time_var.get())

        # Add initial greeting or instruction to chat
        self.add_chat_message("Nexus", "Welcome to Galactic Nexus! Type 'help' for commands or ask questions.", tag="info_tag")

        # Ensure status bar is correctly initialized
        self.set_status("Ready.")

        # Set focus to chat input initially for convenience
        if self.chat_input and self.chat_input.winfo_exists():
            self.chat_input.focus_set()
        logger.debug("Post-initialization setup complete.")


    # --- Utility Functions (Threading, Status, Progress, GUI Updates) ---

    def _run_long_task(self, target_func: Callable, args: tuple = ()):
        """Manages running a potentially long task in a background thread with GUI feedback."""
        if not self.job_running_lock.acquire(blocking=False):
            # If lock is already held, inform user and prevent starting new task
            self.add_chat_message("Nexus", "System busy processing another request. Please wait.", tag="error_tag")
            task_name = target_func.__name__.replace('_', ' ').title()
            logger.warning(f"Task '{task_name}' blocked: Another task is already running.")
            # Specific handling for animation toggle failure
            if target_func == self._compute_animation_frames and self.root.winfo_exists():
                 self.root.after(100, lambda: self.animate_var.set(False)) # Untick the box
            return # Do not start the new task

        # Show and start the progress bar
        if self.progress_bar and self.progress_bar.winfo_exists():
             try:
                 self.progress_bar.grid(row=0, column=1, sticky="e", padx=5) # Place it
                 self.progress_bar.start(10) # Start indeterminate animation
             except tk.TclError as e: logger.warning(f"Error starting progress bar: {e}")
        else: logger.warning("Progress bar widget not available for task start.")

        # Provide immediate feedback on what's starting
        readable_name = target_func.__name__.replace('_', ' ').replace('compute ', '').replace('update ', '').replace('get ', '').capitalize()
        if readable_name.startswith('Show'): readable_name = readable_name.split(' ')[1] # e.g. Upcoming events
        if readable_name.endswith(' preview'): readable_name = readable_name.replace(' preview', ' plot')
        self.set_status(f"Processing: {readable_name}...")
        logger.info(f"Starting background task: {target_func.__name__} with args: {args if args else '()'}")

        # --- Worker Thread Definition ---
        def task_wrapper():
            final_status = "Task Completed" # Default status
            task_start_time = datetime.now()
            try:
                # Execute the target function
                result = target_func(*args)
                # Optionally use result to set final status if function returns string
                if isinstance(result, str): final_status = result
                logger.info(f"Background task {target_func.__name__} finished successfully in {(datetime.now() - task_start_time).total_seconds():.2f}s.")
            except Exception as e:
                logger.error(f"Error in background task {target_func.__name__}: {e}", exc_info=True)
                final_status = f"Error during {readable_name}: Check logs."
                # Show error in chat (via main thread)
                if self.root and self.root.winfo_exists():
                     self.add_chat_message("Nexus", f"Error processing '{readable_name}'. Please check logs.", tag="error_tag")
                # Specific cleanup for failed animation toggle
                if target_func == self._compute_animation_frames and self.root and self.root.winfo_exists():
                    self.root.after(100, lambda: self.animate_var.set(False)) # Untick the box on failure
            finally:
                # --- Cleanup (always run) ---
                # Schedule GUI cleanup (stop progress bar, set status) on main thread
                if self.root and self.root.winfo_exists():
                     # Pass final status message to the cleanup function
                     self.root.after(0, self._cleanup_task, final_status)
                # Always release the lock, even if root is destroyed
                # (needs try-except in case thread finished after lock already released, e.g. by shutdown)
                try:
                    if self.job_running_lock.locked():
                        self.job_running_lock.release()
                        # logger.debug(f"Job lock released by task {target_func.__name__}")
                except threading.ThreadError as te:
                    # This can happen if lock was already released (e.g., multiple finally blocks, shutdown race)
                    logger.warning(f"Ignoring ThreadError on lock release (task: {target_func.__name__}): {te}")
                # Log task completion time from background thread
                task_end_time = datetime.now()
                duration = (task_end_time - task_start_time).total_seconds()
                logger.debug(f"Task wrapper for {target_func.__name__} finished in {duration:.2f}s. Final status to be set: '{final_status}'")
        # --- End Worker Thread Definition ---

        # Create and start the daemon thread
        thread = threading.Thread(target=task_wrapper, daemon=True)
        # Use a descriptive thread name for logging/debugging
        thread.name = f"Task-{readable_name.split(' ')[0]}"[:15] # Max thread name length often limited
        thread.start()


    def _cleanup_task(self, final_status: str):
        """Hides progress bar, sets final status message. Called via root.after from task thread."""
        # Check widget existence before manipulating GUI elements
        if self.progress_bar and self.progress_bar.winfo_exists():
            if self.progress_bar.winfo_ismapped(): # Check if it's currently visible
                try:
                    self.progress_bar.stop()
                    self.progress_bar.grid_forget() # Hide it
                except tk.TclError as e: logger.warning(f"Error stopping/hiding progress bar: {e}")
        else: logger.debug("Progress bar doesn't exist or was destroyed before cleanup.")

        # Set the final status message provided by the task
        self.set_status(final_status)
        logger.info(f"Task cleanup complete. Final status: '{final_status}'")


    def set_status(self, message: str):
        """Safely updates the status bar label from any thread using root.after."""
        # Schedule the update on the main thread to avoid Tkinter errors
        if self.root and self.root.winfo_exists() and self.status_var:
             # Use default args in lambda to capture current message value
             self.root.after(0, lambda msg=message: self.status_var.set(msg))


    def _update_time_label_only(self, slider_jd_value: float):
        """Updates only the time display label, e.g., during slider movement."""
        try:
            current_t = ts.tt(jd=slider_jd_value)
            time_str = current_t.utc_strftime('%Y-%m-%d %H:%M UTC')
            prefix = "(Real-Time) " if self.real_time_var.get() else ""
            # Check widget existence before setting
            if self.time_display and self.root.winfo_exists():
                self.time_display.set(f"{prefix}{time_str}")
        except Exception as e:
            logger.error(f"Error updating time display label: {e}")
            if self.time_display: self.time_display.set("Error updating time")


    def _on_time_slider_release(self, event=None):
         """Callback when the time slider is released - triggers plot update."""
         if not self.real_time_var.get(): # Only trigger update if not in real-time mode
              logger.debug(f"Time slider released at value {self.time_var.get():.4f}. Triggering plot update.")
              self._trigger_plot_update()
         else:
              logger.debug("Time slider released, but ignored because Real-Time mode is active.")

    def _trigger_plot_update(self):
         """Initiates the static plot update via the background task runner."""
         logger.info("Update Static Plot button clicked or triggered.")
         # Get current time value (respecting real-time mode if active)
         # Check time var exists before getting value
         if not hasattr(self, 'time_var') or self.time_var is None:
              logger.error("Cannot trigger plot update: time_var is not initialized.")
              return
         target_time = ts.now() if self.real_time_var.get() else ts.tt(jd=self.time_var.get())
         # Run the update function in the background thread
         self._run_long_task(self._update_preview, args=(target_time,))


    # --- Mousewheel Scroll Handling (for Chat mainly) ---
    def _on_mousewheel(self, event):
        """Handles mouse wheel scrolling, primarily for the chat display."""
        if not self.root or not self.root.winfo_exists(): return # Exit if root is gone

        try:
            # Identify the widget directly under the mouse cursor
            x, y = event.x_root, event.y_root
            widget_under_cursor = self.root.winfo_containing(x, y)
            if widget_under_cursor is None: return

            # Check if the cursor is over the chat display or its children/scrollbar
            target_widget = None
            current_widget = widget_under_cursor
            while current_widget:
                if current_widget == self.chat_display:
                    target_widget = self.chat_display
                    break
                try:
                    # Check if widget is part of the ScrolledText complex (like the scrollbar)
                    # This is heuristic, might need refinement based on exact widget structure
                    if isinstance(current_widget, (ttk.Scrollbar, tk.Scrollbar)) and hasattr(current_widget.master, 'yview'):
                         if current_widget.master == self.chat_display:
                              target_widget = self.chat_display
                              break
                    current_widget = current_widget.master
                except Exception: # Catch potential errors accessing master
                    break # Stop traversal if error occurs

            # If scroll target is the chat display, perform scroll
            if target_widget == self.chat_display and target_widget.winfo_exists():
                if hasattr(target_widget, 'yview_scroll'):
                    # Determine scroll direction (platform differences)
                    scroll_dir = 0
                    if event.num == 4 or event.delta > 0: scroll_dir = -1 # Scroll Up
                    elif event.num == 5 or event.delta < 0: scroll_dir = 1  # Scroll Down

                    if scroll_dir != 0:
                        target_widget.yview_scroll(scroll_dir, "units")
                        return "break" # Prevent event from propagating further
            # Else: could add logic here for other scrollable widgets if needed

        except tk.TclError as e:
             # Can happen if widget is destroyed during event processing
             logger.debug(f"TclError during mousewheel event (widget likely destroyed): {e}")
        except Exception as e:
             logger.warning(f"Unexpected error during mousewheel event processing: {e}", exc_info=False) # Log general errors less verbosely


    # --- Chatbot Logic ---
    def add_chat_message(self, sender: str, message: str, tag: Optional[str] = None):
        """Adds a formatted message to the chat display (thread-safe)."""
        if not self.chat_display or not self.chat_display.winfo_exists():
            logger.warning("Chat display not available, cannot add message.")
            return

        def _update_chat_on_main_thread():
            # Double-check widget existence inside the scheduled call
            if not self.chat_display or not self.chat_display.winfo_exists(): return

            current_state = self.chat_display.cget('state') # Remember current state
            try:
                 self.chat_display.configure(state='normal') # Enable editing
                 # Determine prefix and tag based on sender
                 prefix = "You: " if sender == "User" else "Nexus: "
                 # Use provided tag or default based on sender
                 line_tag = tag if tag else ("user_tag" if sender == "User" else "bot_tag")

                 # Insert the message with prefix, ensuring newline separation
                 # Strip message just in case, add double newline for visual spacing
                 full_message = prefix + message.strip() + "\n\n"
                 self.chat_display.insert(tk.END, full_message, (line_tag,)) # Apply tag

                 # Scroll to the end to show the latest message
                 self.chat_display.see(tk.END)

            except tk.TclError as e:
                 # Catch error if widget gets destroyed between check and configure/insert
                 logger.error(f"TclError updating chat display (widget likely destroyed): {e}")
            except Exception as e:
                 logger.error(f"Unexpected error adding chat message: {e}", exc_info=True)
            finally:
                 # IMPORTANT: Always restore original state, even if errors occurred
                 # Check existence one last time before configure
                 if self.chat_display and self.chat_display.winfo_exists():
                     try: self.chat_display.configure(state=current_state)
                     except tk.TclError: pass # Ignore if destroyed right before final configure

        # Schedule the GUI update to run on the main Tkinter thread
        if self.root and self.root.winfo_exists():
             self.root.after(0, _update_chat_on_main_thread)
        else:
             logger.warning("Root window doesn't exist, cannot schedule chat update.")


    def _get_groq_response_worker(self, user_message: str) -> str:
        """Worker function to get LLM response. Runs in background thread via _run_long_task. Returns final status string."""
        if not self.llm_enabled or not self.groq_client:
            self.add_chat_message("Nexus", "LLM assistant is currently disabled.", tag="error_tag")
            logger.warning("Attempted LLM query while LLM is disabled or client uninitialized.")
            return "LLM Disabled" # Status message for _cleanup_task

        # Prepare system prompt for context
        system_prompt = (
            "You are Nexus, a concise astronomical assistant within the 'Planet Tracker: Galactic Nexus' GUI application. "
            "Focus on astronomy facts, planet data (like size, mass, distance), celestial events, and space concepts relevant to the solar system visualization context. "
            "Keep answers factual and brief. Use clear, simple language. "
            "Avoid code examples, excessive formatting (like lists unless necessary), apologies, or conversational fillers. "
            "If information is unavailable or outside your scope, state that directly (e.g., 'Data not available'). "
            "The user controls the application's time and view settings via the GUI, so you don't need to manipulate these."
        )
        logger.info(f"Sending query to Groq: '{user_message[:60]}...'")
        final_status = "LLM Error" # Default error status

        try:
            chat_completion = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                # Choose a suitable model available via Groq (check their documentation)
                # llama3-8b-8192 is generally fast and capable for this task
                model="llama3-8b-8192",
                temperature=0.6, # Adjust creativity (lower is more factual)
                max_tokens=300,  # Limit response length
                # top_p=0.9,       # Alternative sampling parameter
                # stop=None,       # Sequences to stop generation (e.g., ["\n"])
            )
            # Extract response and add to chat display (via main thread)
            response = chat_completion.choices[0].message.content.strip()
            self.add_chat_message("Nexus", response) # Will be scheduled on main thread
            final_status = "Ready" # Success status
            logger.info(f"Received Groq response ({len(response)} chars).")

        except APIError as e:
            # Handle specific Groq API errors (rate limits, auth errors, etc.)
            error_body = getattr(e, 'body', {})
            error_message = f"Groq API Error: {e.status_code} - {error_body.get('error', {}).get('message', 'Unknown API error details')}"
            logger.error(error_message)
            self.add_chat_message("Nexus", f"API error ({e.status_code}). Please check connection or API key and try again later.", tag="error_tag")
            final_status = f"LLM API Error ({e.status_code})" # Status reflects error
        except Exception as e:
            # Handle other potential errors (network issues, unexpected responses)
            logger.error(f"LLM connection/processing error: {e}", exc_info=True)
            self.add_chat_message("Nexus", "Sorry, there was an error contacting the assistant.", tag="error_tag")
            final_status = "LLM Connection Error"

        return final_status # Return status string for the _cleanup_task


    def _handle_chat_message(self, event=None):
        """Handles user input from the chat entry, routing to local commands or LLM."""
        if not self.chat_input or not self.chat_input.winfo_exists(): return
        user_message = self.chat_input.get().strip()
        if not user_message: return # Ignore empty input

        # Add user message to display and clear input field immediately
        self.add_chat_message("User", user_message)
        self.chat_input.delete(0, tk.END)

        # Parse command and arguments (simple split)
        command_parts = user_message.lower().split()
        cmd_word = command_parts[0] if command_parts else ""
        args = command_parts[1:]

        local_command_handled = False
        sync_response = None # Response generated synchronously (for simple local commands)

        # --- Local Command Processor ---
        try:
            if cmd_word == "help" or cmd_word == "commands":
                sync_response = (
                    "Available Commands:\n"
                    "- `help` / `commands`: Show this help message.\n"
                    "- `info [Planet Name]`: Show data for a celestial body.\n"
                    "- `update plot`: Update the static plot to the current time.\n"
                    "- `animate`: Generate an animation (uses orbit range).\n"
                    "- `upcoming events`: Show predicted events for the next year.\n"
                    "- `clear`: Clear this chat display.\n"
                    "Ask general astronomy questions to contact the Nexus AI (if enabled)."
                )
                local_command_handled = True

            elif cmd_word == "info" and args:
                 # Ensure planet_data is available
                 if planet_data is None:
                      sync_response = "Error: Planet data module not initialized."
                      local_command_handled = True
                 else:
                     # Attempt to find matching planet name (case-insensitive)
                     query = " ".join(args).strip()
                     match = next((p for p in planet_data.get_all_planet_names() if query.lower() == p.lower()), None)
                     if match:
                         # Get formatted info string
                         info_lines = [f"--- {match} ---"]
                         info_dict = planet_data.get_planet_info(match)
                         if info_dict: info_lines.extend([f"{k}: {v}" for k, v in info_dict.items()])
                         else: info_lines.append("Basic data unavailable.")

                         # Get orbital elements at current time
                         try:
                             current_t = ts.now() if self.real_time_var.get() else ts.tt(jd=self.time_var.get())
                             elements = get_orbital_elements(match, current_t)
                             if elements and (elements['semi_major_axis'] != 0.0 or elements['eccentricity'] != 0.0):
                                 info_lines.append("--- Current Orbital Elements ---")
                                 info_lines.append(f"Semi-Major Axis: {elements.get('semi_major_axis', 0.0):.4f} AU")
                                 info_lines.append(f"Eccentricity: {elements.get('eccentricity', 0.0):.5f}")
                             elif elements: # If elements were calculated but were zero/default
                                 info_lines.append("(Orbital elements calculation returned default values)")

                         except Exception as e_el: logger.warning(f"Could not get orbital elements for {match} via chat command: {e_el}")

                         sync_response = "\n".join(info_lines)
                         self._update_info_panel(match) # Also update the Info tab display
                     else:
                         known_bodies = planet_data.get_all_planet_names() if planet_data else []
                         sync_response = f"Sorry, I don't have data for '{query}'. Known bodies: {', '.join(known_bodies)}"
                     local_command_handled = True

            elif cmd_word == "update" and "plot" in args:
                self.add_chat_message("Nexus", "Requesting static plot update...", tag="info_tag")
                self._trigger_plot_update() # Uses task runner
                local_command_handled = True

            elif cmd_word == "animate":
                 self.add_chat_message("Nexus", f"Requesting animation generation ({self.orbit_start_var.get()} to {self.orbit_end_var.get()})...", tag="info_tag")
                 # Ensure checkbox is checked before calling handler (consistent UI)
                 if self.root.winfo_exists() and not self.animate_var.get():
                     self.animate_var.set(True)
                 self._handle_animate_toggle() # Calls _run_long_task internally
                 local_command_handled = True

            elif cmd_word == "upcoming" and "events" in args:
                 self.add_chat_message("Nexus", "Calculating upcoming events for selected planets (next year)...", tag="info_tag")
                 # Run calculation in thread, respond in chat
                 threading.Thread(target=self._show_upcoming_events, args=(True,), daemon=True).start()
                 local_command_handled = True

            elif cmd_word == "clear":
                if self.chat_display and self.chat_display.winfo_exists():
                     self.chat_display.configure(state='normal')
                     self.chat_display.delete('1.0', tk.END)
                     self.chat_display.configure(state='disabled')
                     # Optionally add a 'Chat cleared' message
                     self.add_chat_message("Nexus", "Chat display cleared.", tag="info_tag")
                local_command_handled = True

            # Add other local commands here if needed...

        except Exception as e:
             logger.error(f"Error processing local chat command '{cmd_word}': {e}", exc_info=True)
             sync_response = f"Internal error processing command '{cmd_word}'. Check logs."
             self.set_status(f"Command Error: {e}")
             local_command_handled = True # Treat error as handled locally

        # --- Output Response or Query LLM ---
        if sync_response:
            self.add_chat_message("Nexus", sync_response) # Add synchronous response
            self.set_status("Ready") # Reset status after local command handled
        elif not local_command_handled:
            if self.llm_enabled:
                # Offload LLM query to background task
                self.add_chat_message("Nexus", "Thinking...", tag="info_tag") # Indicate pending response
                self._run_long_task(self._get_groq_response_worker, args=(user_message,))
            else:
                 # LLM is disabled, provide fallback response
                 fallback = random.choice([
                     "My advanced cognitive functions are offline. Try `help` for local commands.",
                     "I cannot access external knowledge networks currently.",
                     "LLM features disabled. See `help`."])
                 self.add_chat_message("Nexus", fallback, tag="error_tag")
                 self.set_status("LLM Disabled")


    # --- Core Application Functions / Event Handlers ---

    def _update_info_panel(self, body_name: str):
        """Updates the 'Info/Events' tab's information display panel."""
        if not body_name or planet_data is None: # Ensure name and data module are valid
            logger.warning(f"Cannot update info panel for '{body_name}' (Invalid name or PlanetData not ready).")
            if self.info_var: self.info_var.set(f"Info unavailable for {body_name}.")
            return

        logger.debug(f"Updating info panel display for: {body_name}")

        info_lines = []
        info_dict = planet_data.get_planet_info(body_name)

        if info_dict:
            info_lines = [f"--- {body_name} ---"] + [f"{k}: {v}" for k, v in info_dict.items() if v != "N/A"]
        else:
            info_lines = [f"--- {body_name} ---", "Detailed data not available."]

        # Add current orbital elements
        try:
            current_t = ts.now() if self.real_time_var.get() else ts.tt(jd=self.time_var.get())
            elements = get_orbital_elements(body_name, current_t)
            # Only add elements section if calculation likely succeeded
            if elements and (elements['semi_major_axis'] != 0.0 or elements['eccentricity'] != 0.0):
                info_lines.append("--- Orbital Elements (Now) ---")
                info_lines.append(f"Semi-Major Axis: {elements['semi_major_axis']:.4f} AU")
                info_lines.append(f"Eccentricity: {elements['eccentricity']:.5f}")
        except Exception as e:
            logger.warning(f"Could not get orbital elements for info panel update ({body_name}): {e}")
            info_lines.append("\n(Could not retrieve current orbital elements)")

        # Safely update the Tkinter variable via main thread schedule
        final_text = "\n".join(info_lines)
        if self.root and self.root.winfo_exists() and self.info_var:
            self.root.after(0, lambda text=final_text: self.info_var.set(text))


    def _export_plot(self):
        """Exports the last generated plot figure as an HTML file."""
        if not self.plot or not hasattr(self.plot, 'fig') or not self.plot.fig or not self.plot.fig.data:
            msg = "No plot has been generated yet to export."
            self.set_status(msg)
            if self.root.winfo_exists(): messagebox.showwarning("Export Plot", msg, parent=self.root)
            logger.warning("Export plot called but no figure data exists.")
            return

        # Ask user for save location
        file_path = filedialog.asksaveasfilename(
             parent=self.root,
             title="Save Plot as HTML",
             defaultextension=".html",
             filetypes=[("HTML files", "*.html"), ("All files", "*.*")]
        )
        if not file_path:
            self.set_status("Plot export cancelled."); return

        self.set_status("Exporting plot to HTML..."); logger.info(f"Exporting plot to {file_path}")
        try:
            # Use CDN for Plotly.js to keep file size smaller
            self.plot.fig.write_html(file_path, include_plotlyjs='cdn')
            self.set_status("Plot exported successfully.")
            self.add_chat_message("Nexus", f"Static plot exported to {os.path.basename(file_path)}", tag="info_tag")
        except Exception as e:
            logger.error(f"Failed to export plot to HTML: {e}", exc_info=True)
            error_msg = f"Failed to export plot:\n{e}"
            self.set_status(f"Export failed: {e}")
            if self.root.winfo_exists(): messagebox.showerror("Export Error", error_msg, parent=self.root)


    def _export_orbit_data(self):
        """Exports the currently stored calculated orbit data to a CSV file."""
        if not self.orbit_positions_dict:
            msg = "No orbit data calculated yet. Please generate a plot or animation first."
            self.set_status(msg)
            if self.root.winfo_exists(): messagebox.showwarning("Export Orbit Data", msg, parent=self.root)
            logger.warning("Export orbit data called but orbit_positions_dict is empty.")
            return

        file_path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save Orbit Data as CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not file_path:
            self.set_status("Orbit data export cancelled."); return

        self.set_status("Exporting orbit data..."); logger.info(f"Exporting orbit data for {list(self.orbit_positions_dict.keys())} to {file_path}")
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                # Write header row
                writer.writerow(["Planet", "Point_Index", "X_AU", "Y_AU", "Z_AU"])
                # Write data rows
                point_count = 0
                for name, positions_array in self.orbit_positions_dict.items():
                     # Validate array shape before iterating
                     if isinstance(positions_array, np.ndarray) and positions_array.ndim == 2 and positions_array.shape[0] == 3:
                         num_points = positions_array.shape[1]
                         for i in range(num_points):
                              # Write row: Planet Name, Index, X, Y, Z
                              writer.writerow([name, i, positions_array[0, i], positions_array[1, i], positions_array[2, i]])
                              point_count += 1
                     else: logger.warning(f"Skipping invalid orbit data shape for {name} during CSV export: {type(positions_array)}")
            logger.info(f"Successfully exported {point_count} orbit data points.")
            self.set_status("Orbit data exported successfully.")
            self.add_chat_message("Nexus", f"Orbit data exported to {os.path.basename(file_path)}", tag="info_tag")
        except IOError as e:
            logger.error(f"IOError exporting orbit data to CSV: {e}", exc_info=True)
            error_msg = f"Failed to write orbit data file:\n{e}"
            self.set_status(f"Export failed: {e}")
            if self.root.winfo_exists(): messagebox.showerror("Export Error", error_msg, parent=self.root)
        except Exception as e:
             logger.error(f"Unexpected error exporting orbit data to CSV: {e}", exc_info=True)
             error_msg = f"An unexpected error occurred during CSV export:\n{e}"
             self.set_status(f"Export failed: {e}")
             if self.root.winfo_exists(): messagebox.showerror("Export Error", error_msg, parent=self.root)


    def _save_settings(self):
        """Saves current application settings (planets, colors, view, time) to a JSON file."""
        settings = {
            "app_version": "1.1", # Version number for future compatibility checks
            "theme": self.current_theme,
            "planets_selected": {p: var.get() for p, var in self.selected_planets.items()},
            "planet_colors": self.planet_colors,
            "time_jd": self.time_var.get(),
            "orbit_start_date": self.orbit_start_var.get(),
            "orbit_end_date": self.orbit_end_var.get(),
            "view_zoom": self.zoom_var.get(),
            "view_elevation": self.elev_var.get(),
            "view_azimuth": self.azim_var.get(),
            "real_time_mode": self.real_time_var.get(),
            "animation_speed_ms": self.speed_var.get(),
            # Add any other relevant settings here
        }

        file_path = filedialog.asksaveasfilename(
             parent=self.root,
             title="Save Application Settings",
             defaultextension=".json",
             filetypes=[("JSON settings", "*.json"), ("All files", "*.*")]
        )
        if not file_path:
            self.set_status("Save settings cancelled."); return

        self.set_status("Saving settings..."); logger.info(f"Saving settings to {file_path}")
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4) # Use indent for readability
            self.set_status("Settings saved successfully.")
            self.add_chat_message("Nexus", f"Settings saved to {os.path.basename(file_path)}.", tag="info_tag")
        except IOError as e:
            logger.error(f"IOError saving settings to JSON: {e}", exc_info=True)
            error_msg = f"Failed to save settings file:\n{e}"
            self.set_status(f"Save failed: {e}")
            if self.root.winfo_exists(): messagebox.showerror("Save Error", error_msg, parent=self.root)
        except TypeError as e: # Handle non-serializable data if any crept in
             logger.error(f"TypeError saving settings (data not serializable?): {e}", exc_info=True)
             error_msg = f"Failed to save settings due to data type error:\n{e}"
             self.set_status(f"Save failed: {e}")
             if self.root.winfo_exists(): messagebox.showerror("Save Error", error_msg, parent=self.root)
        except Exception as e:
             logger.error(f"Unexpected error saving settings: {e}", exc_info=True)
             error_msg = f"An unexpected error occurred while saving settings:\n{e}"
             self.set_status(f"Save failed: {e}")
             if self.root.winfo_exists(): messagebox.showerror("Save Error", error_msg, parent=self.root)


    def _load_settings(self):
        """Loads application settings from a JSON file and updates the GUI."""
        file_path = filedialog.askopenfilename(
             parent=self.root,
             title="Load Application Settings",
             filetypes=[("JSON settings", "*.json"), ("All files", "*.*")]
        )
        if not file_path:
            self.set_status("Load settings cancelled."); return

        self.set_status("Loading settings..."); logger.info(f"Loading settings from {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)

            # --- Apply Loaded Settings (with defaults/fallbacks) ---
            # Theme
            loaded_theme = settings.get("theme", self.current_theme) # Default to current if missing
            if loaded_theme in self.themes:
                 # Must set theme_var *and* call apply_theme
                 self.theme_var.set(loaded_theme)
                 self._apply_theme(loaded_theme) # Apply immediately
            else: logger.warning(f"Loaded theme '{loaded_theme}' not recognized, keeping current.")

            # Planet Selection & Colors
            loaded_selection = settings.get("planets_selected", {})
            loaded_colors = settings.get("planet_colors", {})
            self.planet_colors = loaded_colors.copy() # Update internal color dictionary
            for p, var in self.selected_planets.items():
                 # Update checkbox state
                 var.set(loaded_selection.get(p, True)) # Default to selected if missing in file
                 # Update color swatch visually
                 if p in self.color_swatches and self.color_swatches[p].winfo_exists():
                     # Ensure the internal color dict has a fallback if missing from file
                     if planet_data: # Check planet_data is available
                          color_val = self.planet_colors.get(p, planet_data.get_planet_color(p))
                     else: color_val = '#808080' # Ultimate fallback color
                     self.planet_colors[p] = color_val # Make sure internal dict matches what's shown
                     self.color_swatches[p].configure(background=color_val)

            # Time & Orbit Range
            self.time_var.set(settings.get("time_jd", ts.now().tt)) # Default to now if missing
            self.orbit_start_var.set(settings.get("orbit_start_date", "2025-01-01"))
            self.orbit_end_var.set(settings.get("orbit_end_date", "2026-01-01"))
            # Update time display label immediately after loading time_var
            self._update_time_label_only(self.time_var.get())

            # View Settings
            self.zoom_var.set(settings.get("view_zoom", 1.0))
            self.elev_var.set(settings.get("view_elevation", 25.0))
            self.azim_var.set(settings.get("view_azimuth", 45.0))

            # Modes
            self.real_time_var.set(settings.get("real_time_mode", False))
            # Immediately update UI elements affected by real-time mode change
            self._toggle_real_time_mode() # Updates label and potentially behavior

            # Animation Speed
            self.speed_var.set(settings.get("animation_speed_ms", 50.0))

            # Add other settings here...

            logger.info("Settings loaded and applied successfully.")
            self.set_status("Settings loaded successfully.")
            self.add_chat_message("Nexus", f"Settings loaded from {os.path.basename(file_path)}.", tag="info_tag")

            # Optional: Trigger a plot update automatically after loading settings?
            # self._trigger_plot_update()

        except FileNotFoundError:
             logger.error(f"Load settings failed: File not found at {file_path}")
             error_msg = f"Could not find settings file:\n{file_path}"
             self.set_status("Load failed: File not found.")
             if self.root.winfo_exists(): messagebox.showerror("Load Error", error_msg, parent=self.root)
        except json.JSONDecodeError as e:
             logger.error(f"Load settings failed: Invalid JSON format in {file_path}: {e}", exc_info=True)
             error_msg = f"Could not parse settings file (invalid JSON):\n{os.path.basename(file_path)}\nError: {e}"
             self.set_status("Load failed: Invalid file format.")
             if self.root.winfo_exists(): messagebox.showerror("Load Error", error_msg, parent=self.root)
        except Exception as e:
             logger.error(f"Unexpected error loading settings from {file_path}: {e}", exc_info=True)
             error_msg = f"An unexpected error occurred while loading settings:\n{e}"
             self.set_status(f"Load failed: {e}")
             if self.root.winfo_exists(): messagebox.showerror("Load Error", error_msg, parent=self.root)


    def _show_upcoming_events(self, respond_in_chat: bool = False):
        """Calculates and displays upcoming events (runs in basic thread)."""
        # This function primarily orchestrates; calculation done in planet_calculations
        task_name = "Upcoming event calculation"
        logger.info(f"Starting {task_name} (respond_in_chat={respond_in_chat})...")
        final_status = "Ready"; event_msg = ""; event_level = "info"; event_title = "Upcoming Events"

        try:
            if respond_in_chat: self.set_status("Calculating upcoming events...") # Only set status if chat response needed
            # Get list of currently selected planets from GUI
            active_planets = [p for p, var in self.selected_planets.items() if var.get() and p not in ["Earth", "Moon"]] # Exclude Earth/Moon

            if not active_planets:
                event_msg, final_status, event_level = "No relevant planets selected.", "Select planets first", "warning"
            else:
                # Define time range: now to 1 year from now, respecting ephemeris bounds
                t_start_search = ts.now()
                t_end_search_dt_unclamped = datetime.now(UTC) + timedelta(days=365)
                # Ensure ephem_end_jd is accessible
                if 'ephem_end_jd' not in globals(): # Check if imported
                    raise RuntimeError("Ephemeris end JD not available for clamping.")
                # Clamp end date to ephemeris limits
                ephem_end_dt = ts.tt(jd=ephem_end_jd).utc_datetime()
                t_end_search_dt_clamped = min(t_end_search_dt_unclamped, ephem_end_dt - timedelta(microseconds=1)) # Clamp slightly before end bound
                t_end_search = ts.from_datetime(t_end_search_dt_clamped)

                logger.info(f"Searching for events ({active_planets}) between {t_start_search.utc_iso()} and {t_end_search.utc_iso()}")

                # Call the calculation function (assumed to be thread-safe internally or using Skyfield correctly)
                events_found = find_next_events(active_planets, t_start_search, t_end_search)

                if events_found:
                    event_lines = [f"- {p}: {e} on {d.split(' ')[0]}" for p,e,d in events_found] # Show only date for brevity
                    event_msg = "Upcoming Events (Next Year):\n" + "\n".join(event_lines)
                    final_status = f"{len(events_found)} events found."
                    logger.info(f"Found {len(events_found)} upcoming events.")
                else:
                    event_msg = "No major conjunctions or oppositions found for selected planets in the next year."
                    final_status = "No upcoming events found."
                    logger.info("No upcoming events found in the search range.")
                event_level = "info"

        except ValueError as e: # Catch potential errors from find_next_events (e.g., time range issues)
             logger.error(f"Error during event calculation: {e}", exc_info=True)
             event_msg = f"Could not calculate events.\nError: {e}"
             final_status = "Event calculation error"
             event_level = "error"
             event_title = "Event Calculation Error"
        except Exception as e:
             logger.error(f"Unexpected error calculating events: {e}", exc_info=True)
             event_msg = f"An unexpected error occurred during event calculation.\nError: {e}"
             final_status = "Event calculation error"
             event_level = "error"
             event_title = "Event Calculation Error"
        finally:
             # Update GUI based on response mode
             self.set_status(final_status) # Update status bar regardless of mode
             if self.root and self.root.winfo_exists():
                 tag_map = {"info": "info_tag", "warning": "info_tag", "error": "error_tag"}
                 icon_map = {"info": messagebox.INFO, "warning": messagebox.WARNING, "error": messagebox.ERROR}

                 if respond_in_chat:
                     # Schedule adding message to chat display
                     self.root.after(0, lambda msg=event_msg, tag=tag_map.get(event_level, "bot_tag"): self.add_chat_message("Nexus", msg, tag=tag))
                 else:
                     # Schedule showing message box
                     self.root.after(0, lambda msg=event_msg, title=event_title, icon=icon_map.get(event_level, messagebox.INFO):
                                    messagebox.showinfo(title, msg, icon=icon, parent=self.root))


    def _handle_animate_toggle(self):
        """Handles the 'Generate Animation' checkbox toggle."""
        if self.animate_var.get():
            # Only trigger computation if checkbox becomes checked
            logger.info("Animation checkbox checked, initiating animation computation...")
            # The task runner will handle setting status, progress, and potential errors
            # It will also untick the box via callback if the task fails internally
            self._run_long_task(self._compute_animation_frames)
        else:
             # If checkbox is unchecked *manually*, just log it.
             # We don't attempt to cancel a potentially running animation task.
             logger.info("Animation checkbox unchecked manually.")
             # Optional: Set status? Probably not needed unless we implement cancellation.
             # self.set_status("Animation cancelled by user (if running, it will complete).")


    def _toggle_real_time_mode(self):
        """Updates time display and behavior when 'Use Real-Time' checkbox changes."""
        is_real_time = self.real_time_var.get()
        logger.info(f"Real-time mode toggled {'ON' if is_real_time else 'OFF'}.")

        if is_real_time:
            # Use current system time
            try:
                now_t = ts.now()
                now_str = now_t.utc_strftime('%Y-%m-%d %H:%M UTC')
                display_text = f"(Real-Time) {now_str}"
                self.time_var.set(now_t.tt) # Update underlying variable as well? Maybe not needed.
                status_msg = "Real-time mode enabled. Using current time for updates."
            except Exception as e:
                logger.error(f"Failed to get current time for real-time mode: {e}")
                display_text = "Error getting real-time"
                status_msg = "Error enabling real-time mode."
            if self.time_slider and self.time_slider.winfo_exists():
                self.time_slider.configure(state='disabled') # Disable slider
        else:
            # Use time from the slider
            try:
                slider_jd = self.time_var.get()
                slider_time = ts.tt(jd=slider_jd)
                display_text = slider_time.utc_strftime('%Y-%m-%d %H:%M UTC')
                status_msg = "Real-time mode disabled. Using time slider value."
            except Exception as e:
                logger.error(f"Error getting time from slider value: {e}")
                display_text = "Set Time from Slider"
                status_msg = "Error setting time from slider."
            if self.time_slider and self.time_slider.winfo_exists():
                self.time_slider.configure(state='normal') # Enable slider

        # Update the display label (always happens on main thread via variable)
        if self.time_display: self.time_display.set(display_text)
        self.set_status(status_msg)

    def _compute_animation_frames(self) -> str:
        """Computes data needed for animation (runs in background thread). Returns status string."""
        task_name = "Animation frame computation"
        logger.info(f"Starting {task_name}...")
        start_compute_time = datetime.now()
        final_status = "Animation Failed" # Default status
        try:
            if not self.plot: raise RuntimeError("PlanetPlot instance is not available.")
            self.set_status("Verifying animation settings...") # Intermediate status update

            active_planets = [p for p, v in self.selected_planets.items() if v.get()]
            if not active_planets: raise ValueError("No planets selected for animation.")

            t_start_str, t_end_str = self.orbit_start_var.get(), self.orbit_end_var.get()
            # Use parse_date_time for consistent validation and error handling
            try:
                t_start = parse_date_time(t_start_str, "00:00")
                t_end = parse_date_time(t_end_str, "23:59") # Include full end day
            except ValueError as e: raise ValueError(f"Invalid orbit range date format: {e}") # Re-raise with context

            if t_start.tt >= t_end.tt: raise ValueError("Animation start date must be before end date.")

            # Limit animation duration to prevent excessive calculation time/memory usage
            max_anim_days = 365.25 * 5 # Limit to ~5 years
            duration_days = t_end.tt - t_start.tt
            if duration_days > max_anim_days:
                # Clamp end time if duration exceeds limit
                t_end_clamped = ts.tt(jd=t_start.tt + max_anim_days)
                clamped_end_str = t_end_clamped.utc_strftime('%Y-%m-%d')
                logger.warning(f"Animation duration ({duration_days:.0f} days) exceeds limit ({max_anim_days:.0f} days). Clamped end date to {clamped_end_str}.")
                # Update GUI variable (via main thread) and message user
                if self.root.winfo_exists():
                     self.root.after(0, lambda s=clamped_end_str: self.orbit_end_var.set(s))
                     self.add_chat_message("Nexus", f"Animation duration limited to {max_anim_days:.0f} days. End date adjusted.", tag="info_tag")
                t_end = t_end_clamped # Use clamped end time for calculations
                duration_days = t_end.tt - t_start.tt # Update duration

            self.set_status("Calculating orbits for animation...")
            orbit_steps_anim = max(100, min(730, int(duration_days * 2))) # More steps for smoother animation orbits
            anim_orbit_positions = {}
            for name in active_planets:
                 orbit_data = calculate_orbit(name, t_start.tt, t_end.tt, num_points=orbit_steps_anim)
                 if orbit_data.size > 0: # Check if calculation succeeded
                      anim_orbit_positions[name] = orbit_data
                 else: logger.warning(f"Failed to calculate animation orbit for {name}.")

            self.set_status("Calculating animation frame positions...")
            # Determine number of frames (balance between smoothness and calculation time)
            # Target around 1-2 frames per day, capped at reasonable max (e.g., 1000-1500 frames)
            num_frames = max(50, min(1500, int(duration_days * 1.5)))
            logger.info(f"Generating {num_frames} animation frames for {duration_days:.1f} day period.")
            times_anim = ts.linspace(t_start, t_end, num_frames)
            positions_list = [] # List to hold position dict for each frame

            for i, t in enumerate(times_anim):
                # Calculate positions for all active planets at this time step
                frame_positions = get_heliocentric_positions(active_planets, t)
                positions_list.append(frame_positions) # Add dict to the list
                # Update progress status periodically
                if (i+1) % max(1, num_frames // 20) == 0: # ~20 status updates during calc
                     self.set_status(f"Calculating animation frames ({i+1}/{num_frames})...")

            # Check if positions list was populated
            if not positions_list: raise RuntimeError("Failed to calculate any animation frame positions.")

            compute_duration = (datetime.now() - start_compute_time).total_seconds()
            logger.info(f"Frame position calculation took {compute_duration:.2f} seconds.")
            self.set_status("Launching animation plot...") # Status before potentially blocking plot call

            # --- Prepare arguments for the plot call ---
            # Pass necessary data; ensure copies are made if needed (e.g., planet_colors)
            anim_args = (
                positions_list, times_anim, anim_orbit_positions, active_planets,
                int(self.speed_var.get()), self.zoom_var.get(), self.elev_var.get(),
                self.azim_var.get(), self.planet_colors.copy(), # Pass a copy of colors
                self.set_status # Pass status callback for use by plot method if needed
            )

            # --- Schedule Plotly plot generation/display on the main thread ---
            # Plotly interactions with browsers are often best done from the main thread
            if self.root and self.root.winfo_exists():
                # Ensure plot object exists before calling its method
                if self.plot:
                    self.root.after(0, self.plot.create_animation, *anim_args)
                    final_status = "Animation launched (check browser)." # Success status message
                else:
                    final_status = "Animation calculated but Plot object invalid."
                    logger.error(final_status)
            else:
                 final_status = "Animation calculated but cannot display (window closed)."

        except ValueError as e: # Catch configuration or date range errors
            logger.error(f"Animation setup error: {e}")
            final_status = f"Animation Error: {e}" # Set status bar message
            if self.root and self.root.winfo_exists(): self.add_chat_message("Nexus", final_status, tag="error_tag")
            # Ensure checkbox is unticked on error - Schedule on main thread
            if self.root and self.root.winfo_exists(): self.root.after(100, lambda: self.animate_var.set(False))

        except Exception as e: # Catch unexpected calculation or plotting errors
            logger.error(f"Unexpected error during animation computation: {e}", exc_info=True)
            final_status = "Animation Failed: Check logs." # Set status bar message
            if self.root and self.root.winfo_exists(): self.add_chat_message("Nexus", final_status, tag="error_tag")
            # Ensure checkbox is unticked on error - Schedule on main thread
            if self.root and self.root.winfo_exists(): self.root.after(100, lambda: self.animate_var.set(False))


        # This final_status is returned to _run_long_task's finally block
        return final_status

    def _update_preview(self, target_t: Optional[Time] = None) -> str:
        """Updates the static plot view (run via _run_long_task). Returns status string."""
        task_name = "Static plot update"
        logger.info(f"Starting {task_name}...")
        final_status = "Plot Update Failed" # Default status
        try:
            if not self.plot: raise RuntimeError("PlanetPlot instance is not available.")
            self.set_status("Verifying plot settings...") # Intermediate status

            active_planets = [p for p, v in self.selected_planets.items() if v.get()]
            if not active_planets: raise ValueError("No planets selected for plot.")

            # Determine the target time for the plot
            if target_t is None: # If not passed directly (e.g., from slider release)
                 target_t = ts.now() if self.real_time_var.get() else ts.tt(jd=self.time_var.get())
            if not isinstance(target_t, Time): raise ValueError("Invalid time specified for plot.")

            # Update time display label via main thread immediately
            # Use the determined target_t for accuracy
            if self.root.winfo_exists(): self.root.after(0, self._update_time_label_only, target_t.tt)

            # Get/Validate Orbit Range, clamp if needed
            t_start_str, t_end_str = self.orbit_start_var.get(), self.orbit_end_var.get()
            try:
                t_start_orbit = parse_date_time(t_start_str, "00:00")
                t_end_orbit = parse_date_time(t_end_str, "23:59")
            except ValueError as e: raise ValueError(f"Invalid orbit range date format: {e}") # Re-raise with context
            if t_start_orbit.tt >= t_end_orbit.tt: raise ValueError("Orbit start date must be before end date.")

            # Optional: Limit orbit duration displayed in static plot to prevent excessive calculation
            max_orbit_plot_days = 365.25 * 20 # Max ~20 years of orbit trace
            orbit_duration_days = t_end_orbit.tt - t_start_orbit.tt
            if orbit_duration_days > max_orbit_plot_days:
                 t_end_orbit_clamped = ts.tt(jd=t_start_orbit.tt + max_orbit_plot_days)
                 clamped_end_str = t_end_orbit_clamped.utc_strftime('%Y-%m-%d')
                 logger.warning(f"Static plot orbit range ({orbit_duration_days:.0f} days) exceeds display limit ({max_orbit_plot_days:.0f} days). Clamped end date to {clamped_end_str}.")
                 if self.root.winfo_exists():
                      self.root.after(0, lambda s=clamped_end_str: self.orbit_end_var.set(s))
                      self.add_chat_message("Nexus", f"Orbit range limited to {max_orbit_plot_days:.0f} days for display.", tag="info_tag")
                 t_end_orbit = t_end_orbit_clamped # Use clamped time for calculation
                 orbit_duration_days = t_end_orbit.tt - t_start_orbit.tt # Update duration


            self.set_status("Calculating current positions...")
            positions_now = get_heliocentric_positions(active_planets, target_t)
            if not positions_now:
                # Check if any active planets were expected to have positions
                if any(p not in ["Moon"] for p in active_planets): # Ignore if only Moon failed? Check logic
                     logger.error("Failed to calculate positions for one or more selected planets.")
                     raise ValueError("Failed to calculate required planet positions.")
                else:
                    # Allow to proceed if *only* Moon failed and others weren't requested/selected? Risky.
                    logger.warning("Position calculation failed, potentially only for the Moon.")
                    # Ensure positions_now is an empty dict if it was None or similar
                    positions_now = {}


            self.set_status("Calculating orbits for display...")
            # Recalculate orbits based on potentially clamped range and store them
            # More points for smoother static orbits if range is short
            orbit_steps_plot = max(100, min(1000, int(orbit_duration_days * 1.5)))
            current_orbit_positions = {}
            for name in active_planets:
                orbit_data = calculate_orbit(name, t_start_orbit.tt, t_end_orbit.tt, num_points=orbit_steps_plot)
                if orbit_data.size > 0:
                    current_orbit_positions[name] = orbit_data
                else: logger.warning(f"Failed to calculate display orbit for {name}.")
            self.orbit_positions_dict = current_orbit_positions.copy() # Update stored orbits for export

            # Calculate approximate events at this specific time
            current_events = calculate_events(target_t) # Uses geometric check

            self.set_status("Generating plot...")
            # --- Prepare arguments for plot call ---
            plot_args = (
                 positions_now, self.orbit_positions_dict, target_t, active_planets, current_events,
                 self.zoom_var.get(), self.elev_var.get(), self.azim_var.get(),
                 self.planet_colors.copy() # Pass a copy of colors
            )
            # Schedule plot generation/display on the main thread
            if self.root and self.root.winfo_exists():
                if self.plot:
                     self.root.after(0, self.plot.update_plot, *plot_args)
                     event_str = f" (Events: {len(current_events)})" if current_events else ""
                     final_status = f"Static plot launched{event_str}."
                else:
                    final_status = "Plot calculated but Plot object invalid."
                    logger.error(final_status)
            else:
                 final_status = "Plot calculated but cannot display (window closed)."

        except ValueError as e: # Catch config/calculation value errors
            logger.error(f"Static plot update failed: {e}", exc_info=False) # Log concise error
            final_status = f"Plot Error: {e}";
            if self.root and self.root.winfo_exists(): self.add_chat_message("Nexus", final_status, tag="error_tag")
        except Exception as e: # Catch unexpected errors
            logger.error(f"Unexpected error during static plot update: {e}", exc_info=True)
            final_status = "Plot Update Failed: Check logs.";
            if self.root and self.root.winfo_exists(): self.add_chat_message("Nexus", final_status, tag="error_tag")

        return final_status # Return status for the task runner


    def _on_closing(self):
        """Handles the window close event."""
        logger.info("Close button clicked. Initiating shutdown.")
        # Optional: Add confirmation dialog
        # if messagebox.askokcancel("Quit", "Do you want to quit Galactic Nexus?", parent=self.root):
        #     logger.info("User confirmed quit.")
        # else:
        #     logger.info("User cancelled quit.")
        #     return # Abort closing if user cancels

        # Perform cleanup (e.g., stop threads? save state? close files?)
        # Daemon threads should exit automatically, but explicit cleanup is safer if needed.

        # Attempt to release the task lock if held (might be locked if task hangs)
        if self.job_running_lock.locked():
             logger.warning("Attempting to release job lock during shutdown...")
             try: self.job_running_lock.release()
             except threading.ThreadError as e: logger.warning(f"Error releasing lock on shutdown: {e}")
             except Exception as e: logger.error(f"Unexpected error releasing lock on shutdown: {e}")

        logger.info("Destroying main window.")
        # Check root exists before destroying
        if self.root and self.root.winfo_exists():
            self.root.destroy() # Close the tkinter window
        logger.info("Application shutdown sequence complete.")
        # Application will exit after mainloop finishes post-destroy

# --- Main Execution ---
if __name__ == "__main__":
    try:
        # Initialize Tkinter root BEFORE creating the app instance
        main_root = tk.Tk()
        # Hide the default window initially? Might prevent brief flash.
        # main_root.withdraw()
        # Pass root to the application constructor
        app = PlanetTrackerApp(main_root)
        # If init succeeded, make window visible and start main loop
        # main_root.deiconify() # Show after setup
        main_root.mainloop()
        # Exit code should be 0 if mainloop exits normally after destroy()
        logger.info("Application exited normally.")
        sys.exit(0)
    except SystemExit as e:
         # Catch SystemExit from initialization failures (e.g., ephemeris, plot module)
         print(f"\nApplication Exit: {e}", file=sys.stderr)
         # No need for message box here, it should have been shown during init failure handling
         sys.exit(1) # Indicate error exit code
    except Exception as e:
        # Catch any other unexpected critical errors during app creation or mainloop startup
        import traceback
        print("\n--- UNHANDLED CRITICAL ERROR ---", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        print("---------------------------------", file=sys.stderr)
        # Log critical error if possible (logging might not be configured if error is very early)
        try: logging.critical("Unhandled exception during application startup!", exc_info=True)
        except NameError: pass # logger might not exist
        # Try showing a final fallback message box if Tkinter is available
        try:
            root_fallback = tk.Tk(); root_fallback.withdraw()
            messagebox.showerror("Critical Error", f"A critical error occurred:\n{e}\nPlease check console output.", parent=root_fallback)
            root_fallback.destroy()
        except Exception: pass # Ignore errors if Tkinter itself failed
        sys.exit(f"Application terminated due to critical error: {e}") # Ensure exit with error code

# --- END OF FULL CORRECTED FILE main.py ---