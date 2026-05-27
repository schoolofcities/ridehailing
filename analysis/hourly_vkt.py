"""
Sum VKT (dist_available_routed, dist_enroute_routed, dist_ontrip_routed) by hour of day
across all of 2025, reading directly from the zip archive in chunks.

Output: hr, dist_routed, dist_en_route, dist_available
"""

import zipfile
import pandas as pd
import numpy as np

ZIP_PATH = "local_data/operating_hours_2025.zip"
COLS = ["hr", "dist_ontrip_routed", "dist_enroute_routed", "dist_available_routed"]
CHUNK_SIZE = 100_000

# Accumulator: one row per hour-of-day (0-23)
acc = np.zeros((24, 3), dtype=np.float64)  # columns: routed, en_route, available

with zipfile.ZipFile(ZIP_PATH) as zf:
    for name in sorted(zf.namelist()):
        print(f"  reading {name}...")
        with zf.open(name) as f:
            for chunk in pd.read_csv(
                f,
                usecols=COLS,
                chunksize=CHUNK_SIZE,
            ):
                chunk["hr"] = pd.to_datetime(chunk["hr"], utc=True).dt.tz_convert("America/Toronto")
                chunk = chunk[chunk["hr"].dt.year == 2025]
                hour = chunk["hr"].dt.hour
                for h in range(24):
                    mask = hour == h
                    if mask.any():
                        acc[h, 0] += chunk.loc[mask, "dist_ontrip_routed"].sum()
                        acc[h, 1] += chunk.loc[mask, "dist_enroute_routed"].sum()
                        acc[h, 2] += chunk.loc[mask, "dist_available_routed"].sum()

summary = pd.DataFrame(
    {
        "hr": [f"{h}-{h+1}" for h in range(24)],
        "dist_routed": acc[:, 0],
        "dist_en_route": acc[:, 1],
        "dist_available": acc[:, 2],
    }
)

print(summary.to_string(index=False))
summary.to_csv("local_data/hourly_vkt_2025.csv", index=False)
print("\nSaved to local_data/hourly_vkt_2025.csv")
