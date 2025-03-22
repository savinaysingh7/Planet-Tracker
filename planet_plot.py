import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.animation import FuncAnimation

def plot_planetary_positions(positions, distances, data_dict, plot_3d=False, animate=False):
    """Create a polar or 3D plot of planetary positions, with optional animation."""
    fig, ax = plt.subplots(figsize=(12, 10), subplot_kw={'projection': 'polar'})
    colors = plt.cm.tab10(np.linspace(0, 1, len(positions)))

    scatters = {}
    for planet, pos in positions.items():
        lon, lat = pos[0], pos[1]
        theta = np.deg2rad(lon)
        r = abs(lat) + 90
        size = min(max(np.log(distances[planet] + 1) * 20, 20), 200)
        scat = ax.scatter(theta, r, label=f"{planet.capitalize()} ({distances[planet]:.2f} AU)", 
                          color=colors[list(positions.keys()).index(planet)], s=size, alpha=0.7)
        ax.text(theta, r, planet.capitalize(), fontsize=10, ha='center', va='bottom', 
                bbox=dict(facecolor='white', alpha=0.5, edgecolor='none'))
        scatters[planet] = scat

    ax.set_ylim(0, 180)
    ax.set_yticks(range(0, 181, 30))
    ax.set_yticklabels([f"{i-90}°" for i in range(0, 181, 30)])
    ax.set_xticks(np.linspace(0, 2*np.pi, 12, endpoint=False))
    ax.set_xticklabels([f"{int(i)}°" for i in np.linspace(0, 360, 12, endpoint=False)])
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.legend(loc='upper right', bbox_to_anchor=(1.15, 1.1), fontsize=10)

    if animate:
        time_positions = {planet: data_dict[planet]['time_positions'] for planet in positions}
        def update(frame):
            for planet, scat in scatters.items():
                lon, lat, _ = time_positions[planet][frame]
                theta = np.deg2rad(lon)
                r = abs(lat) + 90
                scat.set_offsets([theta, r])
            ax.set_title(f"Planetary Positions - Day {frame+1}/30", pad=20, fontsize=14)
            return list(scatters.values())

        ani = FuncAnimation(fig, update, frames=len(time_positions[next(iter(positions))]), 
                           interval=100, blit=True)
    else:
        ax.set_title(f"Planetary Positions - {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}", 
                     pad=20, fontsize=14)

    if input("Save plot as PDF? (y/n): ").lower() == 'y':
        with PdfPages(f'planetary_positions_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf') as pdf:
            pdf.savefig(fig)
        print("Plot saved as PDF")
    
    plt.tight_layout()
    plt.show()