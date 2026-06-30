import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# ────────────────────────────────────────────────────────────────
# PART 1 — SYNTHETIC AIS DATA
# Mimics real AIS feed format from AISHub / MarineTraffic
# ────────────────────────────────────────────────────────────────

def generate_ais_data():
    """
    Generate synthetic AIS position history for a fleet of vessels.
    Includes normal vessels and shadow fleet vessels that go dark.
    """
    print("Generating synthetic AIS dataset...")

    vessels = [
        # (mmsi, name,              behavior)
        ("123456789", "PACIFIC STAR",    "normal"),
        ("234567890", "OCEAN PIONEER",   "normal"),
        ("345678901", "GULF TRADER",     "gap_suspicious"),   # goes dark mid-voyage
        ("456789012", "EASTERN PROMISE", "gap_suspicious"),   # goes dark near sanctioned port
        ("567890123", "SEA SHADOW",      "dark_vessel"),      # long dark period + spoofing
        ("678901234", "ARCTIC WIND",     "normal"),
        ("789012345", "PHANTOM MARINER", "dark_vessel"),      # disappears completely
    ]

    records = []
    base_time = datetime(2026, 6, 1, 0, 0, 0)

    for mmsi, name, behavior in vessels:
        # Each vessel gets 30 days of position history
        # Normal AIS: broadcast every 10 minutes
        interval_minutes = 10
        total_minutes = 30 * 24 * 60  # 30 days

        lat = np.random.uniform(20, 40)   # Starting latitude
        lon = np.random.uniform(40, 70)   # Starting longitude (Persian Gulf region)
        speed = np.random.uniform(8, 14)  # Knots

        t = 0
        dark_start = None
        dark_end = None

        # Define dark periods based on behavior
        if behavior == "gap_suspicious":
            # Goes dark for 18-36 hours mid-voyage
            dark_start = np.random.randint(5000, 15000)
            dark_end = dark_start + np.random.randint(1080, 2160)
        elif behavior == "dark_vessel":
            # Goes dark for 3-7 days
            dark_start = np.random.randint(3000, 8000)
            dark_end = dark_start + np.random.randint(4320, 10080)

        while t < total_minutes:
            # Check if in dark period
            in_dark = dark_start and dark_end and dark_start <= t <= dark_end

            if not in_dark:
                # Add position noise (GPS + transmission jitter)
                noise_lat = np.random.normal(0, 0.01)
                noise_lon = np.random.normal(0, 0.01)

                # Move vessel along heading
                heading = np.random.uniform(0, 360)
                speed_knots = speed + np.random.normal(0, 0.5)
                dist_per_interval = speed_knots * (interval_minutes / 60) / 60

                lat += dist_per_interval * np.cos(np.radians(heading)) + noise_lat
                lon += dist_per_interval * np.sin(np.radians(heading)) + noise_lon

                records.append({
                    "mmsi": mmsi,
                    "vessel_name": name,
                    "timestamp": base_time + timedelta(minutes=t),
                    "latitude": round(lat, 5),
                    "longitude": round(lon, 5),
                    "speed_knots": round(max(0, speed_knots), 1),
                    "heading": round(heading, 1),
                    "behavior": behavior,
                })

            t += interval_minutes

    df = pd.DataFrame(records)
    df = df.sort_values(["mmsi", "timestamp"]).reset_index(drop=True)
    print(f"✓ Generated {len(df)} AIS position records")
    print(f"  Vessels: {df['mmsi'].nunique()}")
    print(f"  Date range: {df['timestamp'].min()} → {df['timestamp'].max()}")
    return df

# ────────────────────────────────────────────────────────────────
# PART 2 — GAP DETECTION
# ────────────────────────────────────────────────────────────────

def detect_ais_gaps(df, gap_threshold_hours=6):
    """
    Detect suspicious AIS gaps for each vessel.

    A gap is flagged when a vessel stops transmitting for longer
    than gap_threshold_hours. Normal gaps: port calls, equipment
    issues. Suspicious gaps: deliberate AIS switch-off.

    Args:
        df: AIS position dataframe
        gap_threshold_hours: Minimum gap duration to flag

    Returns:
        gaps_df: DataFrame of all detected gaps with risk assessment
    """
    print(f"\nAnalyzing AIS gaps (threshold: {gap_threshold_hours}h)...")
    gaps = []

    for mmsi, group in df.groupby("mmsi"):
        group = group.sort_values("timestamp")
        vessel_name = group["vessel_name"].iloc[0]
        timestamps = group["timestamp"].tolist()

        for i in range(1, len(timestamps)):
            gap_duration = (timestamps[i] - timestamps[i-1]).total_seconds() / 3600

            if gap_duration >= gap_threshold_hours:
                # Position before and after gap
                pos_before = group.iloc[i-1]
                pos_after = group.iloc[i]

                # Distance jumped during gap (suspicious if large)
                lat_diff = abs(pos_after["latitude"] - pos_before["latitude"])
                lon_diff = abs(pos_after["longitude"] - pos_before["longitude"])
                position_jump_deg = np.sqrt(lat_diff**2 + lon_diff**2)

                # Risk scoring
                risk_score = 0

                # Long gaps are more suspicious
                if gap_duration > 72:
                    risk_score += 40
                elif gap_duration > 24:
                    risk_score += 25
                elif gap_duration > 12:
                    risk_score += 15
                else:
                    risk_score += 5

                # Large position jumps during gap suggest
                # vessel moved without broadcasting
                if position_jump_deg > 5:
                    risk_score += 30
                elif position_jump_deg > 2:
                    risk_score += 15
                elif position_jump_deg > 0.5:
                    risk_score += 5

                # Risk tier
                if risk_score >= 50:
                    risk_tier = "CRITICAL"
                elif risk_score >= 30:
                    risk_tier = "HIGH"
                elif risk_score >= 15:
                    risk_tier = "MEDIUM"
                else:
                    risk_tier = "LOW"

                gaps.append({
                    "mmsi": mmsi,
                    "vessel_name": vessel_name,
                    "gap_start": pos_before["timestamp"],
                    "gap_end": pos_after["timestamp"],
                    "gap_duration_hours": round(gap_duration, 1),
                    "lat_before": pos_before["latitude"],
                    "lon_before": pos_before["longitude"],
                    "lat_after": pos_after["latitude"],
                    "lon_after": pos_after["longitude"],
                    "position_jump_deg": round(position_jump_deg, 3),
                    "risk_score": risk_score,
                    "risk_tier": risk_tier,
                })

    gaps_df = pd.DataFrame(gaps)
    gaps_df = gaps_df.sort_values("risk_score", ascending=False).reset_index(drop=True)

    print(f"✓ Found {len(gaps_df)} AIS gaps above threshold")
    return gaps_df

# ────────────────────────────────────────────────────────────────
# PART 3 — SPOOFING DETECTION
# ────────────────────────────────────────────────────────────────

def detect_spoofing(df):
    """
    Detect AIS spoofing — vessels broadcasting false positions.

    Key indicators:
    - Impossible speed between two positions (faster than physically possible)
    - Teleportation (large position jump in short time)
    - Speed reported as 0 but position changes significantly
    """
    print("\nRunning spoofing detection...")
    spoof_flags = []
    max_speed_knots = 35  # Fastest commercial vessels ~30kts

    for mmsi, group in df.groupby("mmsi"):
        group = group.sort_values("timestamp").reset_index(drop=True)
        vessel_name = group["vessel_name"].iloc[0]

        for i in range(1, len(group)):
            prev = group.iloc[i-1]
            curr = group.iloc[i]

            time_diff_hours = (
                curr["timestamp"] - prev["timestamp"]
            ).total_seconds() / 3600

            if time_diff_hours <= 0:
                continue

            # Calculate implied speed from position change
            lat_diff = curr["latitude"] - prev["latitude"]
            lon_diff = curr["longitude"] - prev["longitude"]
            dist_deg = np.sqrt(lat_diff**2 + lon_diff**2)
            dist_nm = dist_deg * 60  # approximate nautical miles
            implied_speed = dist_nm / time_diff_hours

            if implied_speed > max_speed_knots:
                spoof_flags.append({
                    "mmsi": mmsi,
                    "vessel_name": vessel_name,
                    "timestamp": curr["timestamp"],
                    "implied_speed_knots": round(implied_speed, 1),
                    "reported_speed_knots": curr["speed_knots"],
                    "flag": "IMPOSSIBLE_SPEED",
                    "severity": "HIGH" if implied_speed > 100 else "MEDIUM",
                })

    spoof_df = pd.DataFrame(spoof_flags) if spoof_flags else pd.DataFrame()
    print(f"✓ Spoofing flags: {len(spoof_df)}")
    return spoof_df

# ────────────────────────────────────────────────────────────────
# PART 4 — VISUALIZE AND SAVE
# ────────────────────────────────────────────────────────────────

def visualize_gaps(gaps_df):
    """Bar chart of gap durations by vessel colored by risk tier."""
    colors = {
        "CRITICAL": "#FF4444",
        "HIGH": "#FF8800",
        "MEDIUM": "#FFB800",
        "LOW": "#00FFB2",
    }

    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor('#0A0E14')
    ax.set_facecolor('#0A0E14')

    for i, row in gaps_df.iterrows():
        color = colors.get(row["risk_tier"], "#888888")
        ax.barh(
            f"{row['vessel_name']}\n{row['gap_start'].strftime('%m/%d %H:%M')}",
            row["gap_duration_hours"],
            color=color,
            alpha=0.85,
            edgecolor='none',
        )
        ax.text(
            row["gap_duration_hours"] + 0.5,
            i,
            f"{row['risk_tier']} ({row['risk_score']})",
            color=color,
            va='center',
            fontsize=8,
        )

    ax.set_xlabel("Gap Duration (hours)", color='#8AAABB')
    ax.set_title("AIS Dark Periods — Risk Assessment", color='white', fontsize=13)
    ax.tick_params(colors='#8AAABB')
    for spine in ax.spines.values():
        spine.set_edgecolor('#1A3040')

    # Legend
    for tier, color in colors.items():
        ax.barh([], [], color=color, label=tier)
    ax.legend(loc='lower right', facecolor='#0A1520',
              labelcolor='white', edgecolor='#1A3040')

    plt.tight_layout()
    output_path = os.path.join("outputs", "ais_gaps.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='#0A0E14')
    plt.close()
    print(f"✓ Visualization saved to {output_path}")

def save_results(gaps_df, spoof_df):
    """Save gap and spoofing results to JSON."""
    output = {
        "generated": datetime.now().isoformat(),
        "ais_gaps": gaps_df.to_dict(orient="records") if len(gaps_df) else [],
        "spoofing_flags": spoof_df.to_dict(orient="records") if len(spoof_df) else [],
    }
    # Convert timestamps to strings
    for gap in output["ais_gaps"]:
        gap["gap_start"] = str(gap["gap_start"])
        gap["gap_end"] = str(gap["gap_end"])
    for flag in output["spoofing_flags"]:
        flag["timestamp"] = str(flag["timestamp"])

    path = os.path.join("outputs", "ais_analysis.json")
    with open(path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"✓ Results saved to {path}")

# ────────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Generate AIS data
    df = generate_ais_data()

    # Detect gaps
    gaps_df = detect_ais_gaps(df, gap_threshold_hours=6)

    # Print gap summary
    print("\n── AIS GAP SUMMARY ───────────────────────")
    for _, row in gaps_df.iterrows():
        print(f"  [{row['risk_tier']:8s}] {row['vessel_name']:20s} | "
              f"Dark: {row['gap_duration_hours']:6.1f}h | "
              f"Jump: {row['position_jump_deg']:.2f}° | "
              f"Score: {row['risk_score']}")

    # Detect spoofing
    spoof_df = detect_spoofing(df)

    # Save and visualize
    visualize_gaps(gaps_df)
    save_results(gaps_df, spoof_df)

    print("\n── STAGE 3 COMPLETE ──────────────────────")
    print("  CFAR vessel detection  ✓")
    print("  AIS gap analysis       ✓")
    print("  Spoofing detection     ✓")