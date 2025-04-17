import plotly.graph_objects as go
import numpy as np
from datetime import datetime, UTC
from skyfield.timelib import Time # For type hinting
from typing import Dict, List, Optional, Tuple, Callable # Added typing
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

import logging

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
        self.master = master
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
        """Updates and displays a static 3D plot."""
        # --- Plot Generation Logic (Same as previous version, assumed correct) ---
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
        # Display
        try: config = {'displaylogo': False, 'modeBarButtonsToRemove': ['sendDataToCloud']}; self.fig.show(config=config); logger.info("Static plot displayed.")
        except Exception as e: logger.error(f"Failed to show static plot: {e}", exc_info=True)


    # --- Animation Method ---
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
        """Creates and displays a precomputed animated 3D plot."""
        logger.info(f"Creating animation: {len(times)} frames, {frame_duration_ms}ms/frame, planets: {active_planets}")
        if status_callback: status_callback("Validating animation inputs...")

        if not positions_list or not times or len(positions_list) != len(times):
            logger.error("Animation input error: positions_list and times mismatch or empty.")
            if status_callback: status_callback("Animation failed: Input data length mismatch.")
            return
        if not active_planets: logger.warning("No active planets selected for animation.")

        colors_to_use = planet_colors if planet_colors is not None else {}
        self.fig = go.Figure()
        initial_positions = positions_list[0]
        base_size, jupiter_radius_km, radius_scale_factor = 5.0, 69911.0, 15.0 / 69911.0

        # --- Add Initial Planet Traces ---
        if status_callback: status_callback("Adding initial animation traces...")
        planet_trace_indices = []
        initially_added_planets = []
        trace_counter = 0
        for name in active_planets:
            if (name in initial_positions and isinstance(initial_positions[name], np.ndarray) and initial_positions[name].shape == (3,)):
                 pos = initial_positions[name]; radius_km = self.planet_data.get_planet_radius(name)
                 marker_size = max(3.0*zoom, min((base_size*zoom)+(radius_km*radius_scale_factor*zoom), 50.0*zoom))
                 color = colors_to_use.get(name, self.planet_data.get_planet_color(name))
                 # Keep hover text simple for animation performance
                 hover_text = f"<b>{name}</b>"
                 self.fig.add_trace(go.Scatter3d(
                      x=[pos[0]], y=[pos[1]], z=[pos[2]], mode='markers+text',
                      marker=dict(size=marker_size, color=color, symbol='circle', line=dict(width=0.5, color='DarkSlateGrey')),
                      text=[name], textfont=dict(size=10, color=color), textposition="top center",
                      name=name, customdata=[name], hoverinfo="text", hovertext=hover_text,
                      hovertemplate = hover_text + '<extra></extra>'
                  ))
                 planet_trace_indices.append(trace_counter); initially_added_planets.append(name); trace_counter += 1
            else: logger.warning(f"Excluding planet '{name}' from animation: Missing/invalid initial position.")
        if not planet_trace_indices: logger.warning("No valid planet traces added for animation.")

        # --- Add Static Traces (Sun and Orbits) ---
        if status_callback: status_callback("Adding static orbits and Sun...")
        sun_size = max(5.0, 20.0 * zoom)
        self.fig.add_trace(go.Scatter3d(x=[0],y=[0],z=[0],mode='markers',marker=dict(size=sun_size, color='yellow', opacity=0.9),name='Sun',hoverinfo='name')); trace_counter += 1
        self.fig.add_trace(go.Scatter3d(x=[0],y=[0],z=[0],mode='markers',marker=dict(size=sun_size * 2, color='yellow', opacity=0.15),name='Sun Glow',showlegend=False,hoverinfo='skip')); trace_counter += 1
        max_orbit_radius = 0.0
        for name in active_planets:
             if (name in orbit_positions and isinstance(orbit_positions[name], np.ndarray) and
                 orbit_positions[name].ndim == 2 and orbit_positions[name].shape[0] == 3 and orbit_positions[name].shape[1] > 1):
                 orbit_pos = orbit_positions[name]; color = colors_to_use.get(name, self.planet_data.get_planet_color(name))
                 self.fig.add_trace(go.Scatter3d(x=orbit_pos[0,:],y=orbit_pos[1,:],z=orbit_pos[2,:],mode='lines',line=dict(color=color,width=1.5),name=f"{name} Orbit",opacity=0.6,hoverinfo='skip')); trace_counter += 1
                 try: max_orbit_radius = max(max_orbit_radius, np.max(np.linalg.norm(orbit_pos, axis=0)))
                 except ValueError: logger.warning(f"Could not calculate max radius for static orbit of {name}.")
             else: logger.debug(f"No static orbit data for {name} in animation.")

        # --- Define Animation Frames ---
        if status_callback: status_callback("Generating animation frames...")
        frames = []; num_frames = len(times); max_abs_val_anim = 0.0
        for frame_idx in range(num_frames):
            current_positions = positions_list[frame_idx]; current_time = times[frame_idx]
            frame_data = [] # Data for THIS frame
            for name in initially_added_planets: # IMPORTANT: Iterate in the same order traces were added
                if (name in current_positions and isinstance(current_positions[name], np.ndarray) and current_positions[name].shape == (3,)):
                     pos = current_positions[name]
                     # Only update position data in frames. Marker size, text, color are from initial trace.
                     frame_data.append(go.Scatter3d(x=[pos[0]], y=[pos[1]], z=[pos[2]]))
                     max_abs_val_anim = max(max_abs_val_anim, np.max(np.abs(pos)))
                else:
                     # Data missing for this planet in this frame, add None to keep alignment
                     logger.warning(f"Data for planet '{name}' missing/invalid in frame {frame_idx}. Using None position.")
                     frame_data.append(go.Scatter3d(x=[None], y=[None], z=[None])) # Add placeholder

            # Create the frame object
            frame_name = current_time.utc_strftime('%Y-%m-%d %H:%M')
            frames.append(go.Frame(data=frame_data, name=frame_name, traces=planet_trace_indices))

            # Update status periodically
            if status_callback and (frame_idx == 0 or (frame_idx + 1) % max(1, num_frames // 20) == 0 or frame_idx == num_frames - 1):
                 status_callback(f"Generating animation frames... {frame_idx + 1}/{num_frames}")

        self.fig.frames = frames
        logger.info(f"Generated {len(frames)} animation frames.")

        # --- Animation Layout and Controls ---
        if status_callback: status_callback("Configuring animation layout...")
        grid_size = max(max_orbit_radius, max_abs_val_anim, 1.5) * 1.1
        logger.info(f"Animation dynamic axis range set: {grid_size:.2f} AU")
        elev_rad, azim_rad = np.radians(elev), np.radians(azim); cam_dist = max(2.0, grid_size * 2.5)
        cam_x, cam_y, cam_z = (cam_dist*np.cos(elev_rad)*np.cos(azim_rad), cam_dist*np.cos(elev_rad)*np.sin(azim_rad), cam_dist*np.sin(elev_rad))
        axis_config = dict(range=[-grid_size,grid_size],showgrid=False,zeroline=False,showbackground=True,backgroundcolor="#101020",showticklabels=True,tickfont=dict(color='#a0a0b0',size=9),title=dict(font=dict(color='#c0c0d0',size=10)))

        # Buttons - Use redraw=True as a potential fix for rendering updates reliably
        play_button = dict(label="Play", method="animate", args=[None, {"frame": {"duration": frame_duration_ms, "redraw": True}, "mode": "immediate", "fromcurrent": True, "transition": {"duration": 0}}])
        pause_button = dict(label="Pause", method="animate", args=[[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate", "transition": {"duration": 0}}]) # Pause can keep redraw False
        # Slider steps - Use redraw=True here too
        slider_steps = [dict(method="animate", args=[[f.name], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate", "transition": {"duration": 0}}], label=f.name.split(" ")[0]) for f in self.fig.frames]

        self.fig.update_layout(
             title=dict(text=f"Planetary Motion: {times[0].utc_strftime('%Y-%m-%d')} to {times[-1].utc_strftime('%Y-%m-%d')}", font=dict(color="#e0e0ff",size=16),x=0.5,xanchor='center'),
             scene=dict(xaxis_title="X (AU)",yaxis_title="Y (AU)",zaxis_title="Z (AU)",xaxis=axis_config,yaxis=axis_config,zaxis=axis_config,camera=dict(eye=dict(x=cam_x,y=cam_y,z=cam_z),up=dict(x=0,y=0,z=1)),aspectmode='cube'),
             legend=dict(x=0.01,y=0.99,bgcolor='rgba(30,30,50,0.6)',bordercolor='#505060',font=dict(color='#e0e0ff')),
             margin=dict(l=10,r=10,t=40,b=40), paper_bgcolor="#0a0a1a", plot_bgcolor="#0a0a1a",
             updatemenus=[dict(type="buttons",direction="left",buttons=[play_button,pause_button],pad={"r":10,"t":70},showactive=True,x=0.1,xanchor="right",y=0,yanchor="top")],
             sliders=[dict(active=0,steps=slider_steps,x=0.15,y=0.01,len=0.85,pad={"t":10,"b":10},currentvalue={"font":{"size":12,"color":"#00ffea"},"prefix":"Date: ","visible":True,"xanchor":"left"},transition={"duration":0})]
         )

        # --- Display Animation ---
        if status_callback: status_callback("Displaying animation...")
        try:
            config = {'displaylogo': False, 'modeBarButtonsToRemove': ['sendDataToCloud']}
            self.fig.show(config=config)
            logger.info("Animation display initiated successfully.")
            if status_callback: status_callback("Animation ready.")
        except Exception as e:
             logger.error(f"Failed to show animation: {e}", exc_info=True)
             if status_callback: status_callback(f"Animation display failed: {e}")


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
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s [%(name)s] - %(message)s')
    module_logger = logging.getLogger(__name__)
    module_logger.info("--- Testing PlanetPlot Module (Standalone) ---")
    # --- Prerequisite Checks ---
    planet_data_available = 'planet_data_instance' in locals() and isinstance(planet_data_instance, PlanetData)
    calculations_available = False
    try: from planet_calculations import ts, parse_date_time, get_heliocentric_positions, calculate_orbit, calculate_events; calculations_available = True
    except ImportError: module_logger.error("-> Prerequisite Error: Cannot import from 'planet_calculations'.")
    except Exception as e: module_logger.error(f"-> Prerequisite Error during import from 'planet_calculations': {e}", exc_info=True)
    # --- Run Tests if Ready ---
    if planet_data_available and calculations_available:
        # --- Static Plot Test ---
        module_logger.info("\n--- Static Plot Test ---")
        try:
            t_static = parse_date_time("2025-12-25","00:00"); static_planets=["Mercury","Venus","Earth","Moon","Mars","Jupiter"]
            module_logger.info(f"Calculating data for static plot at {t_static.utc_iso()}...")
            static_positions=get_heliocentric_positions(static_planets,t_static)
            t_orbit_start=ts.tt(jd=t_static.tt - 182); t_orbit_end=ts.tt(jd=t_static.tt + 182)
            static_orbit_positions={p:calculate_orbit(p, t_orbit_start.tt, t_orbit_end.tt, num_points=180) for p in static_planets if p in planet_data_instance.get_all_planet_names()}
            static_events=calculate_events(t_static); module_logger.info(f"Approx events: {static_events or 'None'}")
            plotter = PlanetPlot(None, planet_data_instance); module_logger.info("Generating static plot...")
            plotter.update_plot(positions=static_positions,orbit_positions=static_orbit_positions,current_time=t_static,active_planets=static_planets,events=static_events,zoom=1.2,elev=25,azim=45)
        except Exception as e: module_logger.error(f"Static plot test error:", exc_info=True)
        # --- Animation Test ---
        module_logger.info("\n--- Animation Test ---")
        try:
            t_anim_start=parse_date_time("2024-01-01"); t_anim_end=parse_date_time("2024-03-01"); anim_planets=["Mercury","Venus","Earth","Moon","Mars"]
            num_frames=60; times_anim=ts.linspace(t_anim_start, t_anim_end, num_frames); module_logger.info(f"Generating {num_frames} frames for animation...")
            positions_anim_list = [get_heliocentric_positions(anim_planets, t_frame) for t_frame in times_anim]
            module_logger.info("Calculating orbits for animation background..."); t_orb_anim_start = t_anim_start; t_orb_anim_end = ts.tt(jd=t_anim_start.tt+90) # Shorter orbit for anim test
            anim_orbit_positions={p:calculate_orbit(p,t_orb_anim_start.tt,t_orb_anim_end.tt,num_points=180) for p in anim_planets if p in planet_data_instance.get_all_planet_names()}
            module_logger.info("Generating animation plot...")
            if 'plotter' not in locals(): plotter = PlanetPlot(None, planet_data_instance)
            status_update=lambda msg: module_logger.info(f"    [Anim Status] {msg}")
            plotter.create_animation(positions_list=positions_anim_list,times=times_anim,orbit_positions=anim_orbit_positions,active_planets=anim_planets,frame_duration_ms=60,zoom=1.0,elev=30,azim=-30,status_callback=status_update)
        except Exception as e: module_logger.error(f"Animation test error:", exc_info=True)
    else: module_logger.warning("Cannot run plot tests due to missing prerequisites.")
    module_logger.info("\n--- PlanetPlot Testing Complete ---")

# --- END OF FULL CORRECTED FILE planet_plot.py ---