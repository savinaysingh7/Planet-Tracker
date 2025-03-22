import tkinter as tk
from tkinter import ttk, messagebox
from planet_data import fetch_all_planet_data, PLANETS
from planet_calculations import get_heliographic_position, get_positions_over_time
from planet_plot import plot_planetary_positions
from astropy.time import Time

def run_planet_tracker():
    root = tk.Tk()
    root.title("Planet Tracker")
    root.geometry("400x300")

    selected_planets = {planet: tk.BooleanVar(value=True) for planet in PLANETS}
    plot_3d_var = tk.BooleanVar(value=False)
    animate_var = tk.BooleanVar(value=False)

    tk.Label(root, text="Select Planets to Track:").pack(pady=5)
    for planet, var in selected_planets.items():
        tk.Checkbutton(root, text=planet.capitalize(), variable=var).pack(anchor="w")

    tk.Checkbutton(root, text="3D Plot", variable=plot_3d_var).pack(pady=5)
    tk.Checkbutton(root, text="Animate (30 days)", variable=animate_var).pack(pady=5)

    def start_tracking():
        active_planets = [p for p, v in selected_planets.items() if v.get()]
        if not active_planets:
            messagebox.showwarning("Warning", "Please select at least one planet!")
            return
        
        data_dict = fetch_all_planet_data(active_planets)
        positions = {}
        distances = {}
        
        if animate_var.get():
            start_date = Time.now()
            for planet in active_planets:
                time_positions = get_positions_over_time(planet, start_date)
                positions[planet] = (time_positions[0][0], time_positions[0][1])  # lon, lat
                distances[planet] = time_positions[0][2]  # dist
                data_dict[planet] = data_dict[planet] or {}
                data_dict[planet]['time_positions'] = time_positions
        else:
            for planet in active_planets:
                lon, lat, distance = get_heliographic_position(planet)
                positions[planet] = (lon, lat)
                distances[planet] = distance

        print("\nPlanet Data:")
        for planet in active_planets:
            period = data_dict[planet].get('period', 'N/A') if data_dict[planet] else 'N/A'
            print(f"{planet.capitalize():<8} | Distance: {distances[planet]:.2f} AU | "
                  f"Period: {period:<6} days | Lat: {positions[planet][1]:>6.2f}° | "
                  f"Lon: {positions[planet][0]:>6.2f}°")
        
        plot_planetary_positions(positions, distances, data_dict, plot_3d_var.get(), animate_var.get())
        root.destroy()

    tk.Button(root, text="Track Planets", command=start_tracking).pack(pady=10)
    root.mainloop()

if __name__ == "__main__":
    run_planet_tracker()