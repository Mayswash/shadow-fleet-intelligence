import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

def load_ais_analysis():
    path = os.path.join("outputs", "ais_analysis.json")
    with open(path, "r") as f:
        data = json.load(f)
    gaps = pd.DataFrame(data["ais_gaps"]) if data["ais_gaps"] else pd.DataFrame()
    spoofs = pd.DataFrame(data["spoofing_flags"]) if data["spoofing_flags"] else pd.DataFrame()
    print(f"✓ Loaded AIS analysis: {len(gaps)} gaps, {len(spoofs)} spoof flags")
    return gaps, spoofs

OFAC_DATABASE = {
    "345678901": {"owner": "Kaveh Shipping LLC",       "flag_state": "Panama",   "sanctioned": True,  "sanction_program": "IRAN",   "confidence": 0.85},
    "567890123": {"owner": "Arctic Star Trading",      "flag_state": "Gabon",    "sanctioned": True,  "sanction_program": "RUSSIA", "confidence": 0.92},
    "789012345": {"owner": "Eastern Pacific Holdings", "flag_state": "Cameroon", "sanctioned": False, "sanction_program": None,     "confidence": 0.78},
    "123456789": {"owner": "Pacific Shipping Co",      "flag_state": "USA",      "sanctioned": False, "sanction_program": None,     "confidence": 1.0},
    "234567890": {"owner": "Ocean Lines Ltd",          "flag_state": "Norway",   "sanctioned": False, "sanction_program": None,     "confidence": 1.0},
    "456789012": {"owner": "Gulf Maritime FZE",        "flag_state": "UAE",      "sanctioned": False, "sanction_program": None,     "confidence": 0.90},
    "678901234": {"owner": "Nordic Freight AS",        "flag_state": "Denmark",  "sanctioned": False, "sanction_program": None,     "confidence": 1.0},
}

def match_ofac(mmsi):
    return OFAC_DATABASE.get(str(mmsi), {
        "owner": "Unknown", "flag_state": "Unknown",
        "sanctioned": False, "sanction_program": None, "confidence": 0.0,
    })

def compute_shadow_scores(gaps_df, spoof_df):
    print("\nComputing Shadow Scores...")
    all_vessels = {
        "123456789": "PACIFIC STAR",
        "234567890": "OCEAN PIONEER",
        "345678901": "GULF TRADER",
        "456789012": "EASTERN PROMISE",
        "567890123": "SEA SHADOW",
        "678901234": "ARCTIC WIND",
        "789012345": "PHANTOM MARINER",
    }
    results = []
    for mmsi, name in all_vessels.items():
        score = 0
        components = {}

        vessel_gaps = gaps_df[gaps_df["mmsi"] == mmsi] if len(gaps_df) else pd.DataFrame()
        if len(vessel_gaps):
            max_gap = vessel_gaps["gap_duration_hours"].max()
            if max_gap > 120:   gap_score = 35
            elif max_gap > 48:  gap_score = 25
            elif max_gap > 24:  gap_score = 15
            elif max_gap > 6:   gap_score = 8
            else:               gap_score = 0
        else:
            max_gap = 0
            gap_score = 0
        components["ais_gap"] = gap_score
        score += gap_score

        if len(vessel_gaps):
            max_jump = vessel_gaps["position_jump_deg"].max()
            if max_jump > 10:   jump_score = 20
            elif max_jump > 5:  jump_score = 14
            elif max_jump > 2:  jump_score = 8
            else:               jump_score = 2
        else:
            max_jump = 0
            jump_score = 0
        components["position_jump"] = jump_score
        score += jump_score

        ofac = match_ofac(mmsi)
        if ofac["sanctioned"]:
            ofac_score = int(30 * ofac["confidence"])
        elif ofac["confidence"] < 0.5:
            ofac_score = 8
        else:
            ofac_score = 0
        components["ofac"] = ofac_score
        score += ofac_score

        vessel_spoofs = spoof_df[spoof_df["mmsi"] == mmsi] if len(spoof_df) else pd.DataFrame()
        spoof_score = min(15, len(vessel_spoofs) * 5) if len(vessel_spoofs) else 0
        components["spoofing"] = spoof_score
        score += spoof_score

        if score >= 80:    risk_tier, tier_color = "CRITICAL", "#FF4444"
        elif score >= 60:  risk_tier, tier_color = "HIGH",     "#FF8800"
        elif score >= 40:  risk_tier, tier_color = "MEDIUM",   "#FFB800"
        else:              risk_tier, tier_color = "LOW",       "#00FFB2"

        results.append({
            "mmsi": mmsi,
            "vessel_name": name,
            "shadow_score": score,
            "risk_tier": risk_tier,
            "tier_color": tier_color,
            "owner": ofac["owner"],
            "flag_state": ofac["flag_state"],
            "sanction_program": ofac["sanction_program"] or "None",
            "max_gap_hours": round(max_gap, 1),
            "components": components,
        })

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values("shadow_score", ascending=False).reset_index(drop=True)
    return results_df

def visualize_scores(results_df):
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.patch.set_facecolor('#060A0F')

    ax1 = axes[0]
    ax1.set_facecolor('#0A0E14')
    for i, row in results_df.iterrows():
        ax1.barh(i, 100, color='#0F1A24', height=0.7)
        ax1.barh(i, row["shadow_score"], color=row["tier_color"], height=0.7, alpha=0.9)
        ax1.text(row["shadow_score"] + 1, i, f"{row['shadow_score']}", color=row["tier_color"], va='center', fontsize=10, fontweight='bold')
        ax1.text(-1, i, row["vessel_name"], color='#C8D6E5', va='center', ha='right', fontsize=9)
    ax1.set_xlim(-1, 110)
    ax1.set_ylim(-0.5, len(results_df) - 0.5)
    ax1.set_yticks([])
    ax1.set_xlabel("Shadow Score (0-100)", color='#8AAABB', fontsize=10)
    ax1.set_title("Shadow Fleet Risk Scores", color='white', fontsize=12)
    ax1.tick_params(colors='#8AAABB')
    for spine in ax1.spines.values():
        spine.set_edgecolor('#1A3040')
    for threshold, color in [(80, "#FF4444"), (60, "#FF8800"), (40, "#FFB800")]:
        ax1.axvline(threshold, color=color, linestyle='--', alpha=0.3, linewidth=0.8)

    ax2 = axes[1]
    ax2.set_facecolor('#0A0E14')
    components = ["ais_gap", "position_jump", "ofac", "spoofing"]
    comp_colors = ["#00FFB2", "#FFB800", "#FF4444", "#B06CFF"]
    comp_labels = ["AIS Gap", "Position Jump", "OFAC Match", "Spoofing"]
    bottom = np.zeros(len(results_df))
    for comp, color, label in zip(components, comp_colors, comp_labels):
        values = results_df["components"].apply(lambda x: x[comp]).values
        ax2.barh(range(len(results_df)), values, left=bottom, color=color, alpha=0.85, label=label, height=0.7)
        bottom += values
    ax2.set_xlim(0, 110)
    ax2.set_ylim(-0.5, len(results_df) - 0.5)
    ax2.set_yticks(range(len(results_df)))
    ax2.set_yticklabels(results_df["vessel_name"], color='#C8D6E5', fontsize=9)
    ax2.set_xlabel("Score Components", color='#8AAABB', fontsize=10)
    ax2.set_title("Score Breakdown by Signal", color='white', fontsize=12)
    ax2.tick_params(colors='#8AAABB')
    for spine in ax2.spines.values():
        spine.set_edgecolor('#1A3040')
    ax2.legend(facecolor='#0A1520', labelcolor='white', edgecolor='#1A3040', fontsize=8, loc='lower right')

    plt.tight_layout()
    output_path = os.path.join("outputs", "shadow_scores.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='#060A0F')
    plt.close()
    print(f"✓ Dashboard saved to {output_path}")

def save_intelligence_output(results_df):
    output = {
        "generated": datetime.now().isoformat(),
        "product": "Shadow Fleet Intelligence Feed",
        "version": "1.0",
        "vessels": []
    }
    for _, row in results_df.iterrows():
        output["vessels"].append({
            "mmsi": row["mmsi"],
            "vessel_name": row["vessel_name"],
            "shadow_score": row["shadow_score"],
            "risk_tier": row["risk_tier"],
            "owner": row["owner"],
            "flag_state": row["flag_state"],
            "sanction_program": row["sanction_program"],
            "max_dark_period_hours": row["max_gap_hours"],
            "score_components": row["components"],
        })
    path = os.path.join("outputs", "shadow_intelligence_feed.json")
    with open(path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"✓ Intelligence feed saved to {path}")

if __name__ == "__main__":
    gaps_df, spoof_df = load_ais_analysis()
    results_df = compute_shadow_scores(gaps_df, spoof_df)

    print("\n── SHADOW SCORE RESULTS ──────────────────")
    for _, row in results_df.iterrows():
        print(f"  [{row['risk_tier']:8s}] {row['vessel_name']:20s} | Score: {row['shadow_score']:3d}/100 | Owner: {row['owner']}")

    visualize_scores(results_df)
    save_intelligence_output(results_df)

    print("\n── STAGE 4 COMPLETE ──────────────────────")
    print("  Shadow Score engine    ✓")
    print("  OFAC matching          ✓")
    print("  Intelligence feed      ✓")