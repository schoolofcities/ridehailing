"""
Sum VKT and time-on-app by hour of day across all of 2025.

Outputs:
  local_data/hourly_vkt_2025.csv   — dist_routed, dist_en_route, dist_available
  local_data/hourly_time_2025.csv  — time_ontrip, time_enroute, time_available (minutes)
"""

import zipfile
import pandas as pd
import numpy as np

ZIP_PATH = "local_data/operating_hours_2025.zip"
COLS = [
    "hr",
    "dist_ontrip_routed", "dist_enroute_routed", "dist_available_routed",
    "time_ontrip", "time_enroute", "time_available",
]
CHUNK_SIZE = 100_000

# Accumulators: one row per hour-of-day (0-23)
dist_acc = np.zeros((24, 3), dtype=np.float64)  # routed, en_route, available
time_acc = np.zeros((24, 3), dtype=np.float64)  # ontrip, enroute, available

with zipfile.ZipFile(ZIP_PATH) as zf:
    for name in sorted(zf.namelist()):
        print(f"  reading {name}...")
        with zf.open(name) as f:
            for chunk in pd.read_csv(f, usecols=COLS, chunksize=CHUNK_SIZE):
                chunk["hr"] = pd.to_datetime(chunk["hr"], utc=True).dt.tz_convert("America/Toronto")
                chunk = chunk[chunk["hr"].dt.year == 2025]
                hour = chunk["hr"].dt.hour
                for h in range(24):
                    mask = hour == h
                    if mask.any():
                        dist_acc[h, 0] += chunk.loc[mask, "dist_ontrip_routed"].sum()
                        dist_acc[h, 1] += chunk.loc[mask, "dist_enroute_routed"].sum()
                        dist_acc[h, 2] += chunk.loc[mask, "dist_available_routed"].sum()
                        time_acc[h, 0] += chunk.loc[mask, "time_ontrip"].sum()
                        time_acc[h, 1] += chunk.loc[mask, "time_enroute"].sum()
                        time_acc[h, 2] += chunk.loc[mask, "time_available"].sum()

hrs = [f"{h}-{h+1}" for h in range(24)]

dist_summary = pd.DataFrame({
    "hr": hrs,
    "dist_routed":    dist_acc[:, 0],
    "dist_en_route":  dist_acc[:, 1],
    "dist_available": dist_acc[:, 2],
})
dist_summary.to_csv("local_data/hourly_vkt_2025.csv", index=False)
print(dist_summary.to_string(index=False))
print("\nSaved to local_data/hourly_vkt_2025.csv")

time_summary = pd.DataFrame({
    "hr": hrs,
    "time_ontrip":   time_acc[:, 0],
    "time_enroute":  time_acc[:, 1],
    "time_available": time_acc[:, 2],
})
time_summary.to_csv("local_data/hourly_time_2025.csv", index=False)
print(time_summary.to_string(index=False))
print("\nSaved to local_data/hourly_time_2025.csv")
