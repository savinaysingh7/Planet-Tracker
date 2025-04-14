import plotly.graph_objects as go
import numpy as np
from datetime import datetime, UTC

try:
    from IPython.display import display
except ImportError:
    display = None

class PlanetPlot:
    """Manages 3D plotting of planetary positions and orbits with Plotly."""

    def __init__(self, master, planet_data, on_pick_callback=None):
        """
        Initialize the PlanetPlot class.

        Args:
            master: Tkinter parent widget (for future embedding).
            planet_data: PlanetData instance for colors and radii.
            on_pick_callback: Callback for planet click events (future Tkinter use).
        """
        self.planet_data = planet_data
        self.on_pick_callback = on_pick_callback
        self.fig = go.Figure()
        self.master = master

    def update_plot(self, positions, orbit_positions, current_time, active_planets, events=[], zoom=1.0, elev=20, azim=30, planet_colors=None):
        """Update static 3D plot with planet positions and orbits."""
        self.fig.data = []
        events_dict = dict(events)

        # Sun with glow
        self.fig.add_trace(go.Scatter3d(x=[0], y=[0], z=[0], mode='markers',
                                        marker=dict(size=20 * zoom, color='yellow', opacity=0.8), name='Sun'))
        self.fig.add_trace(go.Scatter3d(x=[0], y=[0], z=[0], mode='markers',
                                        marker=dict(size=40 * zoom, color='yellow', opacity=0.2), name='Sun Glow', showlegend=False))

        # Orbits
        for name in active_planets:
            if name in orbit_positions and orbit_positions[name].size > 0 and not np.all(orbit_positions[name] == 0):
                orbit_pos = orbit_positions[name]
                color = planet_colors.get(name, self.planet_data.get_planet_color(name)) if planet_colors else self.planet_data.get_planet_color(name)
                self.fig.add_trace(go.Scatter3d(x=orbit_pos[0], y=orbit_pos[1], z=orbit_pos[2], mode='lines',
                                                line=dict(color=color, width=2), name=f"{name} Orbit", opacity=0.7))

        # Planets
        max_r = max([np.linalg.norm(pos) for pos in positions.values()], default=0)
        for name, pos in positions.items():
            x, y, z = pos
            radius = self.planet_data.get_planet_radius(name)
            s = (10 + 40 * (radius / 69911)) * zoom
            color = planet_colors.get(name, self.planet_data.get_planet_color(name)) if planet_colors else self.planet_data.get_planet_color(name)
            event_type = events_dict.get(name, "")
            symbol = {"Opposition": "star", "Inferior Conjunction": "triangle-up", "Superior Conjunction": "triangle-down"}.get(event_type, "circle")
            hover_text = f"{name}<br>Radius: {radius:.0f} km<br>{event_type}<br>Click for more info" if event_type else f"{name}<br>Radius: {radius:.0f} km<br>Click for more info"
            self.fig.add_trace(go.Scatter3d(x=[x], y=[y], z=[z], mode='markers+text',
                                            marker=dict(size=s, color=color, symbol=symbol),
                                            text=[name], textposition="top center", name=name, customdata=[name],
                                            hoverinfo="text", hovertext=hover_text))

        grid_size = max_r * 1.1 if max_r > 0 else 1.0
        self.fig.update_layout(
            scene=dict(
                xaxis_title="X (AU)", yaxis_title="Y (AU)", zaxis_title="Z (AU)",
                xaxis=dict(range=[-grid_size, grid_size], showgrid=False, showbackground=False, zeroline=False, showline=True, showticklabels=True),
                yaxis=dict(range=[-grid_size, grid_size], showgrid=False, showbackground=False, zeroline=False, showline=True, showticklabels=True),
                zaxis=dict(range=[-grid_size, grid_size], showgrid=False, showbackground=False, zeroline=False, showline=True, showticklabels=True),
                camera=dict(eye=dict(x=np.cos(np.radians(azim)) * 1.5, y=np.sin(np.radians(azim)) * 1.5, z=np.sin(np.radians(elev)) * 1.5))
            ),
            title=f"Planet Positions at {current_time.utc_strftime('%Y-%m-%d %H:%M UTC')}",
            legend=dict(x=0.85, y=0.95), margin=dict(l=0, r=0, t=50, b=0),
            paper_bgcolor="#0a0a1a", plot_bgcolor="#0a0a1a", font=dict(color="#00ffea")
        )
        self.fig.show()

    def create_animation(self, positions_list, times, orbit_positions, active_planets, frame_duration, zoom, elev, azim, planet_colors, status_callback=None):
        """Create and display a precomputed animated 3D plot."""
        self.fig = go.Figure()

        # Initial planet traces
        for name in active_planets:
            pos = positions_list[0][name]
            radius = self.planet_data.get_planet_radius(name)
            s = (10 + 40 * (radius / 69911)) * zoom
            color = planet_colors.get(name, self.planet_data.get_planet_color(name)) if planet_colors else self.planet_data.get_planet_color(name)
            self.fig.add_trace(go.Scatter3d(x=[pos[0]], y=[pos[1]], z=[pos[2]], mode='markers+text',
                                            marker=dict(size=s, color=color, symbol='circle'),
                                            text=[name], textposition="top center", name=name, customdata=[name],
                                            hoverinfo="text", hovertext=f"{name}<br>Radius: {radius:.0f} km<br>Click for more info"))

        # Static traces: Sun and orbits
        self.fig.add_trace(go.Scatter3d(x=[0], y=[0], z=[0], mode='markers',
                                        marker=dict(size=20 * zoom, color='yellow', opacity=0.8), name='Sun'))
        self.fig.add_trace(go.Scatter3d(x=[0], y=[0], z=[0], mode='markers',
                                        marker=dict(size=40 * zoom, color='yellow', opacity=0.2), name='Sun Glow', showlegend=False))
        for name in active_planets:
            if name in orbit_positions:
                orbit_pos = orbit_positions[name]
                color = planet_colors.get(name, self.planet_data.get_planet_color(name)) if planet_colors else self.planet_data.get_planet_color(name)
                self.fig.add_trace(go.Scatter3d(x=orbit_pos[0], y=orbit_pos[1], z=orbit_pos[2], mode='lines',
                                                line=dict(color=color, width=2), name=f"{name} Orbit", opacity=0.7))

        # Animation frames
        frames = []
        for frame_idx, positions in enumerate(positions_list):
            frame_data = [go.Scatter3d(x=[positions[name][0]], y=[positions[name][1]], z=[positions[name][2]]) for name in active_planets]
            frame_layout = go.Layout(annotations=[dict(
                text=times[frame_idx].utc_strftime('%Y-%m-%d %H:%M UTC'),
                xref="paper", yref="paper", x=0.5, y=1.05, showarrow=False,
                font=dict(size=14, color="#00ffea")
            )])
            frames.append(go.Frame(data=frame_data, layout=frame_layout, name=str(frame_idx)))

        self.fig.frames = frames

        # Dynamic axis scaling
        all_x = [pos[0] for positions in positions_list for pos in positions.values()]
        all_y = [pos[1] for positions in positions_list for pos in positions.values()]
        all_z = [pos[2] for positions in positions_list for pos in positions.values()]
        max_r = np.max([np.abs(all_x), np.abs(all_y), np.abs(all_z)])
        grid_size = max_r * 1.1 if max_r > 0 else 1.0

        # Layout with animation controls
        self.fig.update_layout(
            scene=dict(
                xaxis_title="X (AU)", yaxis_title="Y (AU)", zaxis_title="Z (AU)",
                xaxis=dict(range=[-grid_size, grid_size], showgrid=False, showbackground=False, zeroline=False, showline=True, showticklabels=True),
                yaxis=dict(range=[-grid_size, grid_size], showgrid=False, showbackground=False, zeroline=False, showline=True, showticklabels=True),
                zaxis=dict(range=[-grid_size, grid_size], showgrid=False, showbackground=False, zeroline=False, showline=True, showticklabels=True),
                camera=dict(eye=dict(x=np.cos(np.radians(azim)) * 1.5, y=np.sin(np.radians(azim)) * 1.5, z=np.sin(np.radians(elev)) * 1.5))
            ),
            title="Planet Animation",
            legend=dict(x=0.85, y=0.95), margin=dict(l=0, r=0, t=50, b=0),
            paper_bgcolor="#0a0a1a", plot_bgcolor="#0a0a1a", font=dict(color="#00ffea"),
            updatemenus=[dict(
                type="buttons",
                buttons=[
                    dict(label="Play", method="animate", args=[None, {"frame": {"duration": frame_duration, "redraw": True}, "fromcurrent": True, "transition": {"duration": 0}}]),
                    dict(label="Pause", method="animate", args=[[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate", "transition": {"duration": 0}}])
                ],
                direction="left", pad={"r": 10, "t": 87}, showactive=False, x=0.1, xanchor="right", y=0, yanchor="top"
            )],
            sliders=[dict(
                steps=[dict(method="animate", args=[[str(k)], {"frame": {"duration": frame_duration, "redraw": True}, "mode": "immediate"}], label=str(k)) for k in range(len(positions_list))],
                active=0, x=0, y=0, len=1.0
            )],
            annotations=[dict(
                text=times[0].utc_strftime('%Y-%m-%d %H:%M UTC'),
                xref="paper", yref="paper", x=0.5, y=1.05, showarrow=False,
                font=dict(size=14, color="#00ffea")
            )]
        )

        self.fig.show()
        if status_callback:
            status_callback("Animation displayed in browser")

    def _on_pick(self, trace, points, state):
        """Handle click events (for future Tkinter embedding)."""
        if self.on_pick_callback and points.point_inds:
            name = trace.customdata[points.point_inds[0]]
            print(f"Clicked {name}")
            self.on_pick_callback(name)

if __name__ == "__main__":
    from planet_data import planet_data
    from planet_calculations import ts, parse_date_time, get_heliocentric_positions, calculate_orbit

    t = parse_date_time("2025-03-24", "12:00")
    positions = get_heliocentric_positions(["Earth", "Mars"], t)
    orbit_positions = {
        "Earth": calculate_orbit("Earth", t.tt, parse_date_time("2026-03-24", "12:00").tt),
        "Mars": calculate_orbit("Mars", t.tt, parse_date_time("2027-03-24", "12:00").tt)
    }
    def on_pick(name):
        info = planet_data.get_planet_info(name)
        print(f"Clicked {name}: {info}")

    plot = PlanetPlot(None, planet_data, on_pick)
    plot.update_plot(positions, orbit_positions, t, ["Earth", "Mars"], events=[("Mars", "Opposition")])