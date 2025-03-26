import plotly.graph_objects as go
import numpy as np
from datetime import datetime, UTC

class PlanetPlot:
    """Class to manage 3D plotting of planetary positions and orbits with Plotly."""

    def __init__(self, master, planet_data, on_pick_callback=None):
        """
        Initialize the PlanetPlot class.
        
        Args:
            master: Tkinter parent widget (for future embedding).
            planet_data: Object providing planet colors and radii.
            on_pick_callback: Function to call when a planet is clicked.
        """
        self.planet_data = planet_data
        self.on_pick_callback = on_pick_callback
        self.fig = go.Figure()
        self.master = master
        # Note: Currently displays in browser; Tkinter embedding will be added later
        self.canvas = None

    def update_plot(self, positions, orbit_positions, current_time, active_planets, zoom=1.0, elev=20, azim=30, planet_colors=None):
        """
        Update the 3D plot with planet positions and orbits using Plotly.
        
        Args:
            positions: Dict of planet names to current positions (x, y, z in AU).
            orbit_positions: Dict of planet names to orbit coordinates (x, y, z arrays).
            current_time: Skyfield Time object for the current timestamp.
            active_planets: List of planet names to display.
            zoom: Scaling factor for planet sizes.
            elev: Elevation angle for 3D view (degrees).
            azim: Azimuth angle for 3D view (degrees).
            planet_colors: Dict of planet names to custom colors.
        """
        self.fig.data = []  # Clear previous traces

        # Plot Sun with glow effect
        self.fig.add_trace(go.Scatter3d(
            x=[0], y=[0], z=[0], mode='markers',
            marker=dict(size=20 * zoom, color='yellow', opacity=0.8),
            name='Sun'
        ))
        self.fig.add_trace(go.Scatter3d(
            x=[0], y=[0], z=[0], mode='markers',
            marker=dict(size=40 * zoom, color='yellow', opacity=0.2),
            name='Sun Glow', showlegend=False
        ))

        # Plot orbits
        for name in active_planets:
            if name in orbit_positions and orbit_positions[name].size > 0:
                orbit_pos = orbit_positions[name]
                color = planet_colors.get(name, self.planet_data.get_planet_color(name)) if planet_colors else self.planet_data.get_planet_color(name)
                self.fig.add_trace(go.Scatter3d(
                    x=orbit_pos[0], y=orbit_pos[1], z=orbit_pos[2], mode='lines',
                    line=dict(color=color, width=2),
                    name=f"{name} Orbit", opacity=0.7
                ))
                print(f"Plotted orbit for {name}: shape={orbit_pos.shape}")
            else:
                print(f"No orbit data for {name}")

        # Plot planets with scaled sizes
        max_r = 0
        for name, pos in positions.items():
            x, y, z = pos
            r = np.linalg.norm(pos)
            max_r = max(max_r, r)
            radius = self.planet_data.get_planet_radius(name)
            s = (10 + 40 * (radius / 69911)) * zoom  # Scale size relative to Jupiter
            color = planet_colors.get(name, self.planet_data.get_planet_color(name)) if planet_colors else self.planet_data.get_planet_color(name)
            self.fig.add_trace(go.Scatter3d(
                x=[x], y=[y], z=[z], mode='markers+text',
                marker=dict(size=s, color=color),
                text=[name], textposition="top center",
                name=name, customdata=[name],
                hoverinfo="text", hovertext=f"{name}<br>Click for info"
            ))

        # Add ecliptic plane
        grid_size = max_r * 1.1
        xx, yy = np.meshgrid(np.linspace(-grid_size, grid_size, 10), np.linspace(-grid_size, grid_size, 10))
        zz = np.zeros_like(xx)
        self.fig.add_trace(go.Surface(
            x=xx, y=yy, z=zz, colorscale=[[0, 'gray'], [1, 'gray']], opacity=0.1, showscale=False
        ))

        # Update layout with dynamic view and styling
        self.fig.update_layout(
            scene=dict(
                xaxis_title="X (AU)", yaxis_title="Y (AU)", zaxis_title="Z (AU)",
                xaxis=dict(range=[-grid_size, grid_size]),
                yaxis=dict(range=[-grid_size, grid_size]),
                zaxis=dict(range=[-grid_size, grid_size]),
                camera=dict(eye=dict(
                    x=np.cos(np.radians(azim)) * 1.5,
                    y=np.sin(np.radians(azim)) * 1.5,
                    z=np.sin(np.radians(elev)) * 1.5
                ))
            ),
            title=f"Planet Positions at {current_time.utc_strftime('%Y-%m-%d %H:%M UTC')}",
            legend=dict(x=0.85, y=0.95),
            margin=dict(l=0, r=0, t=50, b=0),
            paper_bgcolor="#0a0a1a", plot_bgcolor="#0a0a1a",
            font=dict(color="#00ffea")
        )

        # Add note for Moon scaling
        if "Moon" in active_planets:
            self.fig.add_trace(go.Scatter3d(
                x=[0], y=[0], z=[0], mode='text',
                text=["Note: Moon position scaled 1000x"], textposition="bottom center",
                showlegend=True, name="Moon Note"
            ))

        # Display in browser (Tkinter embedding to be added in next update)
        self.fig.show()
        # TODO: Implement click event handling when embedded in Tkinter

    def _on_pick(self, trace, points, state):
        """Handle click events (to be used when embedded in Tkinter)."""
        if self.on_pick_callback and points.point_inds:
            name = trace.customdata[points.point_inds[0]]
            print(f"Clicked {name}")
            self.on_pick_callback(name)


if __name__ == "__main__":
    # Test the class standalone
    from planet_data import fetch_all_planet_data, get_planet_info, planet_dict
    from planet_calculations import parse_date_time, get_heliocentric_positions, calculate_orbit

    # Mock planet_data object for testing
    class MockPlanetData:
        def get_planet_color(self, name): return planet_dict[name]["color"]
        def get_planet_radius(self, name): return planet_dict[name]["radius"]

    api_data = fetch_all_planet_data()
    t = parse_date_time("2025-03-24", "12:00")
    positions = get_heliocentric_positions(["Earth", "Mars"], t)
    orbit_positions = {
        "Earth": calculate_orbit("Earth", t, parse_date_time("2026-03-24", "12:00")),
        "Mars": calculate_orbit("Mars", t, parse_date_time("2027-03-24", "12:00"))
    }

    def on_pick(name):
        info = get_planet_info(name, api_data)
        print(f"Clicked {name}: {info}")

    plot = PlanetPlot(None, MockPlanetData(), on_pick)
    plot.update_plot(positions, orbit_positions, t, ["Earth", "Mars"], planet_colors=planet_dict)