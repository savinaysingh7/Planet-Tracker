import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from matplotlib.backends.backend_pdf import PdfPages

def plot_planetary_positions(positions, distances, data_dict, plot_3d=False):
    if plot_3d:
        from mpl_toolkits.mplot3d import Axes3D
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        for planet, (lon, lat) in positions.items():
            x = distances[planet] * np.cos(np.deg2rad(lat)) * np.cos(np.deg2rad(lon))
            y = distances[planet] * np.cos(np.deg2rad(lat)) * np.sin(np.deg2rad(lon))
            z = distances[planet] * np.sin(np.deg2rad(lat))
            ax.scatter(x, y, z, label=planet.capitalize(), s=100)
        ax.set_xlabel("X (AU)")
        ax.set_ylabel("Y (AU)")
        ax.set_zlabel("Z (AU)")
    else:
        fig, ax = plt.subplots(figsize=(12, 10), subplot_kw={'projection': 'polar'})
        colors = plt.cm.tab10(np.linspace(0, 1, len(positions)))
        for (planet, (lon, lat)), color in zip(positions.items(), colors):
            theta = np.deg2rad(lon)
            r = abs(lat) + 90
            size = min(max(np.log(distances[planet] + 1) * 20, 20), 200)
            ax.plot(theta, r, 'o', label=f"{planet.capitalize()} ({distances[planet]:.2f} AU)", 
                    color=color, markersize=size, alpha=0.7)
            ax.text(theta, r, planet.capitalize(), fontsize=10, ha='center', va='bottom', 
                    bbox=dict(facecolor='white', alpha=0.5, edgecolor='none'))
        ax.set_ylim(0, 180)
        ax.set_yticks(range(0, 181, 30))
        ax.set_yticklabels([f"{i-90}°" for i in range(0, 181, 30)])
        ax.set_xticks(np.linspace(0, 2*np.pi, 12, endpoint=False))
        ax.set_xticklabels([f"{int(i)}°" for i in np.linspace(0, 360, 12, endpoint=False)])
        ax.grid(True, linestyle='--', alpha=0.5)

    ax.set_title(f"Planetary Positions - {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}", 
                 pad=20, fontsize=14)
    ax.legend(loc='upper right', bbox_to_anchor=(1.15, 1.1), fontsize=10)
    
    if input("Save plot as PDF? (y/n): ").lower() == 'y':
        with PdfPages(f'planetary_positions_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf') as pdf:
            pdf.savefig(fig)
        print("Plot saved as PDF")
    
    plt.tight_layout()
    plt.show()