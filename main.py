import tkinter as tk
from tkinter import ttk, messagebox
from planet_data import fetch_all_planet_data, PLANETS
from planet_calculations import get_heliographic_position
from planet_plot import plot_planetary_positions

def run_planet_tracker():
    root = tk.Tk()
    root.title("Planet Tracker")
    root.geometry("400x300")

    selected_planets = {planet: tk.BooleanVar(value=True) for planet in PLANETS}
    plot_3d_var = tk.BooleanVar(value=False)

    tk.Label(root, text="Select Planets to Track:").pack(pady=5)
    for planet, var in selected_planets.items():
        tk.Checkbutton(root, text=planet.capitalize(), variable=var).pack(anchor="w")

    tk.Checkbutton(root, text="3D Plot", variable=plot_3d_var).pack(pady=5)

    def start_tracking():
        active_planets = [p for p, v in selected_planets.items() if v.get()]
        if not active_planets:
            messagebox.showwarning("Warning", "Please select at least one planet!")
            return
        
        data_dict = fetch_all_planet_data(active_planets)
        positions = {}
        distances = {}
        
        for planet in active_planets:
            lon, lat, distance = get_heliographic_position(planet)
            positions[planet] = (lon, lat)
            distances[planet] = distance
            period = data_dict[planet].get('period', 'N/A') if data_dict[planet] else 'N/A'
            print(f"{planet.capitalize():<8} | Distance: {distance:.2f} AU | "
                  f"Period: {period} days | Lat: {lat:>6.2f}° | Lon: {lon:>6.2f}°")
        
        plot_planetary_positions(positions, distances, data_dict, plot_3d_var.get())
        root.destroy()

    tk.Button(root, text="Track Planets", command=start_tracking).pack(pady=10)
    root.mainloop()

if __name__ == "__main__":
    run_planet_tracker()