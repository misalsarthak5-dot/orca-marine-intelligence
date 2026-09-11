import urllib.request
import json
import sys
import io
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 1. Fetch Landing Centres WFS
lc_url = "https://www.incois.gov.in/geoserver/PFZ_LandingCentres/ows?service=WFS&version=1.1.0&request=GetFeature&typeName=PFZ_LandingCentres:LandingCenters_29Apr2024&outputFormat=application/json"
print("Fetching Landing Centres WFS...")
req = urllib.request.Request(lc_url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as resp:
    lc_data = json.loads(resp.read().decode())

features = lc_data.get("features", [])
print(f"Total Landing Centre features: {len(features)}")

# Inspect sample properties
states = ["MAHARASHTRA", "GOA", "KERALA", "TAMIL NADU", "TAMILNADU"]
state_samples = {s: [] for s in states}

for f in features:
    props = f.get("properties", {})
    sec = props.get("SECTOR_NAM", "").upper()
    for s in states:
        if s in sec:
            state_samples[s].append(props)

print("\n=== LANDING CENTRES DATE FIELDS AUDIT ===")
for s, samples in state_samples.items():
    print(f"\n--- State / Sector: {s} (Total features: {len(samples)}) ---")
    active_samples = [p for p in samples if p.get("STATUS") == "YES"]
    print(f"  STATUS='YES' count: {len(active_samples)}")
    if active_samples:
        for idx, p in enumerate(active_samples[:3]):
            print(f"  Sample {idx+1}: LC_NAME={p.get('LC_NAME')}, DIST_NAME={p.get('DIST_NAME')}")
            print(f"    FORECAST_D (Forecast Date): {p.get('FORECAST_D')}")
            print(f"    VALIDITY_D (Validity Date): {p.get('VALIDITY_D')}")
            print(f"    UPDATED_DA (Updated Date):  {p.get('UPDATED_DA')}")
            print(f"    FORECAST_I (Forecast Issue):{p.get('FORECAST_I')}")
            print(f"    STATUS:                     {p.get('STATUS')}")
            print(f"    BEARING/DIRECTION:          {p.get('BEARING')} / {p.get('DIRECTION')}")
            print(f"    DIST_F - DIST_T:            {p.get('DISTANCE_F')} - {p.get('DISTANCE_T')}")
            print(f"    DEPTH_FROM - DEPTH_TO:      {p.get('DEPTH_FROM')} - {p.get('DEPTH_TO')}")

# 2. Fetch PFZ Lines WFS
lines_url = "https://www.incois.gov.in/geoserver/PFZ_Automation/ows?service=WFS&version=1.1.0&request=GetFeature&typeName=PFZ_Automation:pfzlines&outputFormat=application/json"
print("\nFetching PFZ Lines WFS...")
req2 = urllib.request.Request(lines_url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req2) as resp2:
    lines_data = json.loads(resp2.read().decode())

line_features = lines_data.get("features", [])
print(f"Total PFZ Line features: {len(line_features)}")
print("\n=== PFZ LINES DATE FIELDS AUDIT ===")
for idx, f in enumerate(line_features[:10]):
    props = f.get("properties", {})
    print(f"Line {idx+1}: UID={props.get('UID')}, State_Name={props.get('State_Name')}, Year={props.get('Year')}, Julian_day={props.get('Julian_day')}, Length={props.get('Length')}, Category={props.get('Category')}")

# Analyze Year / Julian_day across all lines
years = set()
julian_days = set()
for f in line_features:
    p = f.get("properties", {})
    years.add(p.get("Year"))
    julian_days.add(p.get("Julian_day"))
print(f"\nUnique Years in PFZ Lines: {years}")
print(f"Unique Julian Days in PFZ Lines: {sorted(list(julian_days))}")

# Check UID structure
uids = [f.get("properties", {}).get("UID") for f in line_features[:10]]
print(f"Sample UIDs: {uids}")
