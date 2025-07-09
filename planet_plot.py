import plotly.graph_objects as go
import numpy as np
from datetime import datetime, UTC
from skyfield.timelib import Time # For type hinting
from typing import Dict, List, Optional, Tuple, Callable
import logging
import os
import webbrowser
from tkinter import messagebox
import tkinter as tk

# Ensure PlanetData can be imported
try:
    from planet_data import PlanetData, planet_data as planet_data_instance
    if planet_data_instance is None:
        raise ImportError("planet_data instance not initialized")
except ImportError:
    import logging as temp_logging
    temp_logging.basicConfig(level=temp_logging.CRITICAL)
    temp_logging.critical("CRITICAL ERROR: planet_data.py not found or cannot be imported. Plotting requires PlanetData.")
    import sys
    sys.exit("Fatal Error: Missing planet_data.py dependency")

logger = logging.getLogger(__name__)

class PlanetPlot:
    """
    Manages 3D plotting of planetary positions and orbits using Plotly.
    Supports static plots, pre-computed animations, and event markers.
    """

    def __init__(self, master, planet_data: PlanetData, on_pick_callback: Optional[Callable[[str], None]] = None):
        """Initializes the PlanetPlot class."""
        if not isinstance(planet_data, PlanetData):
             msg = "Initialization failed: planet_data must be an instance of PlanetData class."
             logger.critical(msg)
             raise TypeError(msg)
        self.planet_data = planet_data
        self.on_pick_callback = on_pick_callback
        self.fig: go.Figure = go.Figure()
        self.master = master # Store reference to the Tkinter root for messageboxes
        logger.info("PlanetPlot initialized successfully.")

    def update_plot(self,
                    positions: Dict[str, np.ndarray],
                    orbit_positions: Dict[str, np.ndarray],
                    current_time: Time,
                    active_planets: List[str],
                    events: List[Tuple[str, str]] = [],
                    zoom: float = 1.0,
                    elev: float = 20.0,
                    azim: float = 30.0,
                    planet_colors: Optional[Dict[str, str]] = None):
        """Updates a static 3D plot, saves it, and attempts to open it in a browser."""
        if not isinstance(current_time, Time):
            logger.error("Invalid current_time object passed to update_plot. Expected skyfield.timelib.Time.")
            return

        logger.info(f"Updating static plot for time {current_time.utc_iso()} with planets: {active_planets}")
        colors_to_use = planet_colors if planet_colors is not None else {}
        self.fig = go.Figure()
        events_dict = {name: event_type for name, event_type in events}

        # Sun
        sun_size = max(5.0, 20.0 * zoom)
        self.fig.add_trace(go.Scatter3d(x=[0],y=[0],z=[0],mode='markers',marker=dict(size=sun_size, color='yellow', opacity=0.9),name='Sun',hoverinfo='name'))
        self.fig.add_trace(go.Scatter3d(x=[0],y=[0],z=[0],mode='markers',marker=dict(size=sun_size * 2, color='yellow', opacity=0.15),name='Sun Glow',showlegend=False,hoverinfo='skip'))

        # Orbits
        max_orbit_radius = 0.0
        for name in active_planets:
             if (name in orbit_positions and isinstance(orbit_positions[name], np.ndarray) and
                 orbit_positions[name].ndim == 2 and orbit_positions[name].shape[0] == 3 and orbit_positions[name].shape[1] > 1):
                  orbit_pos = orbit_positions[name]; color = colors_to_use.get(name, self.planet_data.get_planet_color(name))
                  self.fig.add_trace(go.Scatter3d(x=orbit_pos[0,:],y=orbit_pos[1,:],z=orbit_pos[2,:],mode='lines',line=dict(color=color, width=1.5),name=f"{name} Orbit",opacity=0.6,hoverinfo='skip'))
                  try: max_orbit_radius = max(max_orbit_radius, np.max(np.linalg.norm(orbit_pos, axis=0)))
                  except ValueError: logger.warning(f"Could not calculate max radius for {name}'s orbit.")
             else:
                 if name in active_planets: logger.warning(f"No valid static orbit data for active planet: {name}")
        
        # Planets
        max_planet_radius = 0.0; base_size = 5.0; jupiter_radius_km = 69911.0; radius_scale_factor = 15.0 / jupiter_radius_km
        for name in active_planets:
             if (name in positions and isinstance(positions[name], np.ndarray) and positions[name].shape == (3,)):
                  pos = positions[name]; x, y, z = pos; current_dist = np.linalg.norm(pos); max_planet_radius = max(max_planet_radius, current_dist)
                  radius_km = self.planet_data.get_planet_radius(name); marker_size = max(3.0*zoom, min((base_size*zoom)+(radius_km*radius_scale_factor*zoom), 50.0*zoom))
                  color = colors_to_use.get(name, self.planet_data.get_planet_color(name)); event_type = events_dict.get(name); symbol="circle"; event_text = ""
                  if event_type: symbol_map={"Opposition":"star", "Inferior Conjunction":"diamond-tall", "Superior Conjunction":"cross"}; symbol=symbol_map.get(event_type, "circle-open"); event_text=f"<br><b>{event_type}!</b>"
                  hover_text = f"<b>{name}</b><br>Pos: ({x:.3f}, {y:.3f}, {z:.3f}) AU<br>Dist: {current_dist:.3f} AU<br>Radius: {radius_km:,.0f} km{event_text}"
                  self.fig.add_trace(go.Scatter3d(x=[x],y=[y],z=[z],mode='markers+text',marker=dict(size=marker_size,color=color,symbol=symbol,opacity=0.95,line=dict(width=0.5,color='DarkSlateGrey')),text=[name],textfont=dict(size=10,color=color),textposition="top center",name=name,customdata=[name],hoverinfo="text",hovertext=hover_text,hovertemplate = hover_text + '<extra></extra>'))
             else:
                  if name in active_planets: logger.warning(f"No valid position data for active planet: {name}")

        # Layout
        grid_size = max(max_orbit_radius, max_planet_radius, 1.5) * 1.1; elev_rad, azim_rad = np.radians(elev), np.radians(azim); cam_dist = max(2.0, grid_size * 2.5)
        cam_x,cam_y,cam_z=(cam_dist*np.cos(elev_rad)*np.cos(azim_rad), cam_dist*np.cos(elev_rad)*np.sin(azim_rad), cam_dist*np.sin(elev_rad))
        axis_config = dict(range=[-grid_size,grid_size],showgrid=False,zeroline=False,showbackground=True,backgroundcolor="#101020",showticklabels=True,tickfont=dict(color='#a0a0b0',size=9),title=dict(font=dict(color='#c0c0d0',size=10)))
        self.fig.update_layout(title=dict(text=f"Solar System View - {current_time.utc_strftime('%Y-%m-%d %H:%M UTC')}",font=dict(color="#e0e0ff", size=16),x=0.5,xanchor='center'),scene=dict(xaxis_title="X (AU)",yaxis_title="Y (AU)",zaxis_title="Z (AU)",xaxis=axis_config,yaxis=axis_config,zaxis=axis_config,camera=dict(eye=dict(x=cam_x,y=cam_y,z=cam_z),up=dict(x=0,y=0,z=1),center=dict(x=0,y=0,z=0)),aspectmode='cube'),legend=dict(x=0.01,y=0.99,bgcolor='rgba(30,30,50,0.6)',bordercolor='#505060',font=dict(color='#e0e0ff')),margin=dict(l=10,r=10,t=40,b=10),paper_bgcolor="#0a0a1a",plot_bgcolor="#0a0a1a")
        
        # --- ROBUST BROWSER LAUNCH LOGIC (REPLACES OLD `fig.show()`) ---
        plot_file_path = "solar_system_plot.html"
        logger.info(f"Saving static plot to '{plot_file_path}'...")
        try:
            self.fig.write_html(
                file=plot_file_path,
                config={'displaylogo': False, 'modeBarButtonsToRemove': ['sendDataToCloud']},
                include_plotlyjs='cdn'
            )
            logger.info("Plot saved. Attempting to open in browser...")

            file_url = 'file://' + os.path.abspath(plot_file_path)
            webbrowser.open(file_url, new=2)
            logger.info(f"Browser launch command issued for: {file_url}")
        except Exception as e:
            logger.error(f"Failed to save or automatically open static plot: {e}", exc_info=True)
            if self.master and self.master.winfo_exists():
                messagebox.showwarning(
                    "Browser Warning",
                    f"Could not automatically open the web browser.\n\n"
                    f"The plot has been saved as:\n{os.path.abspath(plot_file_path)}\n\n"
                    f"Please open this file manually.",
                    parent=self.master
                )

    def create_animation(self,
                         positions_list: List[Dict[str, np.ndarray]],
                         times: List[Time],
                         orbit_positions: Dict[str, np.ndarray],
                         active_planets: List[str],
                         frame_duration_ms: int,
                         zoom: float = 1.0,
                         elev: float = 20.0,
                         azim: float = 30.0,
                         planet_colors: Optional[Dict[str, str]] = None,
                         status_callback: Optional[Callable[[str], None]] = None):
        """Creates an animated plot, saves it, and attempts to open it in a browser."""
        # [This part is identical to your original correct code]
        logger.info(f"Creating animation: {len(times)} frames, {frame_duration_ms}ms/frame, planets: {active_planets}")
        if status_callback: status_callback("Validating animation inputs...")
        if not positions_list or not times or len(positions_list) != len(times):
            logger.error("Animation input error: positions_list and times mismatch or empty.")
            if status_callback: status_callback("Animation failed: Input data length mismatch.")
            return
        colors_to_use = planet_colors if planet_colors is not None else {}
        self.fig = go.Figure()
        initial_positions = positions_list[0]
        base_size, jupiter_radius_km, radius_scale_factor = 5.0, 69911.0, 15.0 / 69911.0

        if status_callback: status_callback("Adding initial animation traces...")
        planet_trace_indices = []
        initially_added_planets = []
        trace_counter = 0
        for name in active_planets:
            if (name in initial_positions and isinstance(initial_positions[name], np.ndarray) and initial_positions[name].shape == (3,)):
                 pos = initial_positions[name]; radius_km = self.planet_data.get_planet_radius(name)
                 marker_size = max(3.0*zoom, min((base_size*zoom)+(radius_km*radius_scale_factor*zoom), 50.0*zoom))
                 color = colors_to_use.get(name, self.planet_data.get_planet_color(name))
                 hover_text = f"<b>{name}</b>"
                 self.fig.add_trace(go.Scatter3d(
                      x=[pos[0]], y=[pos[1]], z=[pos[2]], mode='markers+text',
                      marker=dict(size=marker_size, color=color, symbol='circle', line=dict(width=0.5, color='DarkSlateGrey')),
                      text=[name], textfont=dict(size=10, color=color), textposition="top center",
                      name=name, customdata=[name], hoverinfo="text", hovertext=hover_text,
                      hovertemplate = hover_text + '<extra></extra>'
                  ))
                 planet_trace_indices.append(trace_counter); initially_added_planets.append(name); trace_counter += 1

        if status_callback: status_callback("Adding static orbits and Sun...")
        sun_size = max(5.0, 20.0 * zoom)
        self.fig.add_trace(go.Scatter3d(x=[0],y=[0],z=[0],mode='markers',marker=dict(size=sun_size, color='yellow', opacity=0.9),name='Sun',hoverinfo='name')); trace_counter += 1
        self.fig.add_trace(go.Scatter3d(x=[0],y=[0],z=[0],mode='markers',marker=dict(size=sun_size * 2, color='yellow', opacity=0.15),name='Sun Glow',showlegend=False,hoverinfo='skip')); trace_counter += 1
        max_orbit_radius = 0.0
        for name in active_planets:
             if (name in orbit_positions and isinstance(orbit_positions[name], np.ndarray) and orbit_positions[name].ndim == 2):
                 orbit_pos = orbit_positions[name]; color = colors_to_use.get(name, self.planet_data.get_planet_color(name))
                 self.fig.add_trace(go.Scatter3d(x=orbit_pos[0,:],y=orbit_pos[1,:],z=orbit_pos[2,:],mode='lines',line=dict(color=color,width=1.5),name=f"{name} Orbit",opacity=0.6,hoverinfo='skip')); trace_counter += 1
                 try: max_orbit_radius = max(max_orbit_radius, np.max(np.linalg.norm(orbit_pos, axis=0)))
                 except ValueError: logger.warning(f"Could not calculate max radius for static orbit of {name}.")

        if status_callback: status_callback("Generating animation frames...")
        frames = []; num_frames = len(times); max_abs_val_anim = 0.0
        for frame_idx in range(num_frames):
            current_positions = positions_list[frame_idx]; current_time = times[frame_idx]
            frame_data = [go.Scatter3d(x=[current_positions.get(name, [None])[0]], y=[current_positions.get(name, [None])[1]], z=[current_positions.get(name, [None])[2]]) for name in initially_added_planets]
            frame_name = current_time.utc_strftime('%Y-%m-%d %H:%M')
            frames.append(go.Frame(data=frame_data, name=frame_name, traces=planet_trace_indices))
            if status_callback and (frame_idx+1)%max(1,num_frames//20)==0: status_callback(f"Generating animation frames... {frame_idx + 1}/{num_frames}")

        self.fig.frames = frames
        logger.info(f"Generated {len(frames)} animation frames.")
        
        # [Layout code is identical to your original correct code]
        if status_callback: status_callback("Configuring animation layout...")
        grid_size = max(max_orbit_radius, max_abs_val_anim, 1.5) * 1.1
        elev_rad, azim_rad = np.radians(elev), np.radians(azim); cam_dist = max(2.0, grid_size * 2.5)
        cam_x, cam_y, cam_z = (cam_dist*np.cos(elev_rad)*np.cos(azim_rad), cam_dist*np.cos(elev_rad)*np.sin(azim_rad), cam_dist*np.sin(elev_rad))
        axis_config = dict(range=[-grid_size,grid_size],showgrid=False,zeroline=False,showbackground=True,backgroundcolor="#101020",showticklabels=True,tickfont=dict(color='#a0a0b0',size=9),title=dict(font=dict(color='#c0c0d0',size=10)))
        play_button = dict(label="Play", method="animate", args=[None, {"frame": {"duration": frame_duration_ms, "redraw": True}, "mode": "immediate", "fromcurrent": True, "transition": {"duration": 0}}])
        pause_button = dict(label="Pause", method="animate", args=[[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate", "transition": {"duration": 0}}])
        slider_steps = [dict(method="animate", args=[[f.name], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate", "transition": {"duration": 0}}], label=f.name.split(" ")[0]) for f in self.fig.frames]
        self.fig.update_layout(
             title=dict(text=f"Planetary Motion: {times[0].utc_strftime('%Y-%m-%d')} to {times[-1].utc_strftime('%Y-%m-%d')}", font=dict(color="#e0e0ff",size=16),x=0.5,xanchor='center'),
             scene=dict(xaxis_title="X (AU)",yaxis_title="Y (AU)",zaxis_title="Z (AU)",xaxis=axis_config,yaxis=axis_config,zaxis=axis_config,camera=dict(eye=dict(x=cam_x,y=cam_y,z=cam_z),up=dict(x=0,y=0,z=1)),aspectmode='cube'),
             legend=dict(x=0.01,y=0.99,bgcolor='rgba(30,30,50,0.6)',bordercolor='#505060',font=dict(color='#e0e0ff')),
             margin=dict(l=10,r=10,t=40,b=40), paper_bgcolor="#0a0a1a", plot_bgcolor="#0a0a1a",
             updatemenus=[dict(type="buttons",direction="left",buttons=[play_button,pause_button],pad={"r":10,"t":70},showactive=True,x=0.1,xanchor="right",y=0,yanchor="top")],
             sliders=[dict(active=0,steps=slider_steps,x=0.15,y=0.01,len=0.85,pad={"t":10,"b":10},currentvalue={"font":{"size":12,"color":"#00ffea"},"prefix":"Date: ","visible":True,"xanchor":"left"},transition={"duration":0})]
         )
        
        # --- ROBUST BROWSER LAUNCH LOGIC (FOR ANIMATION) ---
        animation_file_path = "solar_system_animation.html"
        if status_callback: status_callback("Saving animation file...")
        logger.info(f"Saving animation to '{animation_file_path}'...")
        try:
            self.fig.write_html(
                file=animation_file_path,
                config={'displaylogo': False, 'modeBarButtonsToRemove': ['sendDataToCloud']},
                include_plotlyjs='cdn'
            )
            logger.info("Animation saved. Attempting to open in browser...")

            file_url = 'file://' + os.path.abspath(animation_file_path)
            webbrowser.open(file_url, new=2)
            logger.info(f"Browser launch command issued for: {file_url}")
            if status_callback: status_callback("Animation ready in browser.")

        except Exception as e:
            logger.error(f"Failed to save or automatically open animation: {e}", exc_info=True)
            if status_callback: status_callback("Animation display failed.")
            if self.master and self.master.winfo_exists():
                messagebox.showwarning(
                    "Browser Warning",
                    f"Could not automatically open the web browser for the animation.\n\n"
                    f"The animation has been saved as:\n{os.path.abspath(animation_file_path)}\n\n"
                    f"Please open this file manually.",
                    parent=self.master
                )

    def _on_pick(self, trace, points, state):
        """Internal callback handler for Plotly click events (requires integration)."""
        if self.on_pick_callback and points and points.point_inds:
            point_index = points.point_inds[0]
            if (hasattr(trace, 'customdata') and isinstance(trace.customdata, (list, tuple)) and len(trace.customdata) > point_index):
                name = trace.customdata[point_index]; logger.info(f"Plot element '{name}' clicked.")
                try: self.on_pick_callback(name)
                except Exception as e: logger.error(f"Error executing on_pick_callback: {e}", exc_info=True)
            else: logger.warning(f"Clicked element lacks customdata for callback.")


# --- Standalone Test Block ---
if __name__ == "__main__":
    # This block remains unchanged and is excellent for testing.
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s [%(name)s] - %(message)s')
    module_logger = logging.getLogger(__name__)
    module_logger.info("--- Testing PlanetPlot Module (Standalone) ---")
    planet_data_available = 'planet_data_instance' in locals() and isinstance(planet_data_instance, PlanetData)
    calculations_available = False
    try: from planet_calculations import ts, parse_date_time, get_heliocentric_positions, calculate_orbit, calculate_events; calculations_available = True
    except ImportError: module_logger.error("-> Prerequisite Error: Cannot import from 'planet_calculations'.")
    except Exception as e: module_logger.error(f"-> Prerequisite Error during import from 'planet_calculations': {e}", exc_info=True)
    
    if planet_data_available and calculations_available:
        # Create a dummy Tkinter root for the messagebox parent
        root_test = tk.Tk()
        root_test.withdraw() 
        plotter = PlanetPlot(root_test, planet_data_instance)

        # Static Plot Test
        module_logger.info("\n--- Static Plot Test ---")
        try:
            t_static = parse_date_time("2025-12-25","00:00"); static_planets=["Mercury","Venus","Earth","Moon","Mars","Jupiter"]
            static_positions=get_heliocentric_positions(static_planets,t_static)
            t_orbit_start=ts.tt(jd=t_static.tt - 182); t_orbit_end=ts.tt(jd=t_static.tt + 182)
            static_orbit_positions={p:calculate_orbit(p, t_orbit_start.tt, t_orbit_end.tt, num_points=180) for p in static_planets if p in planet_data_instance.get_all_planet_names()}
            static_events=calculate_events(t_static)
            module_logger.info("Generating static plot...")
            plotter.update_plot(positions=static_positions,orbit_positions=static_orbit_positions,current_time=t_static,active_planets=static_planets,events=static_events,zoom=1.2,elev=25,azim=45)
        except Exception as e: module_logger.error(f"Static plot test error:", exc_info=True)
        
        # Animation Test
        module_logger.info("\n--- Animation Test ---")
        try:
            t_anim_start=parse_date_time("2024-01-01"); t_anim_end=parse_date_time("2024-03-01"); anim_planets=["Mercury","Venus","Earth","Moon","Mars"]
            num_frames=60; times_anim=ts.linspace(t_anim_start, t_anim_end, num_frames)
            positions_anim_list = [get_heliocentric_positions(anim_planets, t_frame) for t_frame in times_anim]
            t_orb_anim_start = t_anim_start; t_orb_anim_end = ts.tt(jd=t_anim_start.tt+90)
            anim_orbit_positions={p:calculate_orbit(p,t_orb_anim_start.tt,t_orb_anim_end.tt,num_points=180) for p in anim_planets}
            module_logger.info("Generating animation plot...")
            status_update=lambda msg: module_logger.info(f"    [Anim Status] {msg}")
            plotter.create_animation(positions_list=positions_anim_list,times=times_anim,orbit_positions=anim_orbit_positions,active_planets=anim_planets,frame_duration_ms=60,zoom=1.0,elev=30,azim=-30,status_callback=status_update)
        except Exception as e: module_logger.error(f"Animation test error:", exc_info=True)
        
        module_logger.info("--- To see plots, open the generated .html files in your browser. ---")
        # In standalone mode, plots are generated but we can't block with a mainloop.
        # So we can just destroy the dummy root window.
        root_test.destroy()
    else: 
        module_logger.warning("Cannot run plot tests due to missing prerequisites.")

    module_logger.info("\n--- PlanetPlot Testing Complete ---")