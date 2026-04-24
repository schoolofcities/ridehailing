"""
Estimates the number and % of trips < 5km using trips_2025.zip.

Since the data is aggregated (trips_total + distance_avg per origin/destination/hour),
we treat rows where distance_avg < 5 as "short trip" rows and sum their trips_total.
This assumes trips within each group are roughly uniform around the average — ballpark only.
"""

import zipfile
import pandas as pd

ZIP_PATH = "data/trips_2025.zip"
DISTANCE_THRESHOLD_KM = 5


def main():
    dfs = []
    with zipfile.ZipFile(ZIP_PATH) as z:
        for name in sorted(z.namelist()):
            if name.endswith(".csv"):
                with z.open(name) as f:
                    df = pd.read_csv(f, usecols=["trips_total", "distance_avg"])
                    dfs.append(df)

    data = pd.concat(dfs, ignore_index=True)
    data = data.dropna(subset=["trips_total", "distance_avg"])
    data["trips_total"] = data["trips_total"].astype(int)

    total_trips = data["trips_total"].sum()
    short_mask = data["distance_avg"] < DISTANCE_THRESHOLD_KM
    short_trips = data.loc[short_mask, "trips_total"].sum()
    pct = short_trips / total_trips * 100

    print(f"Total trips (all distances): {total_trips:,}")
    print(f"Trips in groups where avg distance < {DISTANCE_THRESHOLD_KM}km: {short_trips:,}")
    print(f"Percentage: {pct:.1f}%")
    print()
    print("Note: rows with distance_avg >= 5km may still contain some trips < 5km")
    print("(and vice versa) — this is a group-average approximation.")


if __name__ == "__main__":
    main()
