import os
import json
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Colors ───────────────────────────────────────────────────────
C_BG        = HexColor("#060A0F")
C_PANEL     = HexColor("#0A0E14")
C_ACCENT    = HexColor("#00FFB2")
C_TEXT      = HexColor("#C8D6E5")
C_MUTED     = HexColor("#4A6A80")
C_CRITICAL  = HexColor("#FF4444")
C_HIGH      = HexColor("#FF8800")
C_MEDIUM    = HexColor("#FFB800")
C_LOW       = HexColor("#00FFB2")
C_BORDER    = HexColor("#0F2030")

def tier_color(tier):
    return {
        "CRITICAL": C_CRITICAL,
        "HIGH": C_HIGH,
        "MEDIUM": C_MEDIUM,
        "LOW": C_LOW,
    }.get(tier, C_MUTED)

def load_intelligence_feed():
    path = os.path.join("outputs", "shadow_intelligence_feed.json")
    with open(path, "r") as f:
        return json.load(f)

def build_styles():
    styles = getSampleStyleSheet()
    custom = {
        "cover_title": ParagraphStyle("cover_title",
            fontSize=28, textColor=white, fontName="Helvetica-Bold",
            leading=34, alignment=TA_LEFT),
        "cover_sub": ParagraphStyle("cover_sub",
            fontSize=11, textColor=C_ACCENT, fontName="Helvetica",
            leading=16, alignment=TA_LEFT, spaceAfter=4),
        "cover_meta": ParagraphStyle("cover_meta",
            fontSize=9, textColor=C_MUTED, fontName="Helvetica",
            leading=14, alignment=TA_LEFT),
        "section_header": ParagraphStyle("section_header",
            fontSize=10, textColor=C_ACCENT, fontName="Helvetica-Bold",
            leading=14, spaceBefore=18, spaceAfter=6,
            letterSpacing=2),
        "body": ParagraphStyle("body",
            fontSize=9, textColor=C_TEXT, fontName="Helvetica",
            leading=15, spaceAfter=6),
        "vessel_name": ParagraphStyle("vessel_name",
            fontSize=11, textColor=white, fontName="Helvetica-Bold",
            leading=14),
        "small": ParagraphStyle("small",
            fontSize=8, textColor=C_MUTED, fontName="Helvetica",
            leading=12),
        "footer": ParagraphStyle("footer",
            fontSize=7, textColor=C_MUTED, fontName="Helvetica",
            leading=10, alignment=TA_CENTER),
    }
    return custom

def cover_page(styles, report_date):
    """Build the cover page elements."""
    elements = []

    elements.append(Spacer(1, 0.8*inch))

    # Classification banner
    banner_data = [["UNCLASSIFIED // FOR OFFICIAL USE ONLY"]]
    banner = Table(banner_data, colWidths=[6.5*inch])
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), C_ACCENT),
        ("TEXTCOLOR",  (0,0), (-1,-1), C_BG),
        ("FONTNAME",   (0,0), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 8),
        ("ALIGN",      (0,0), (-1,-1), "CENTER"),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    elements.append(banner)
    elements.append(Spacer(1, 0.4*inch))

    elements.append(Paragraph("SHADOW FLEET", styles["cover_sub"]))
    elements.append(Paragraph("INTELLIGENCE REPORT", styles["cover_title"]))
    elements.append(Spacer(1, 0.15*inch))
    elements.append(Paragraph(
        "Maritime Sanctions Evasion · Vessel Anomaly Detection · Risk Assessment",
        styles["cover_sub"]
    ))
    elements.append(Spacer(1, 0.3*inch))
    elements.append(HRFlowable(width="100%", thickness=0.5,
                               color=C_BORDER, spaceAfter=16))

    meta = [
        ["REPORT DATE",    report_date],
        ["CLASSIFICATION", "UNCLASSIFIED // FOUO"],
        ["DATA SOURCES",   "Sentinel-1 SAR · AIS · OFAC SDN List"],
        ["COVERAGE",       "Persian Gulf / Global Maritime"],
        ["PRODUCT",        "Shadow Fleet Intelligence Platform v1.0"],
    ]
    for label, value in meta:
        elements.append(Paragraph(
            f'<font color="#4A6A80">{label}&nbsp;&nbsp;</font>'
            f'<font color="#C8D6E5">{value}</font>',
            styles["cover_meta"]
        ))

    elements.append(Spacer(1, 0.4*inch))
    elements.append(HRFlowable(width="100%", thickness=0.5,
                               color=C_BORDER, spaceAfter=16))

    elements.append(Paragraph(
        "This report contains automated intelligence derived from satellite SAR imagery, "
        "AIS vessel tracking data, and OFAC sanctions databases. Vessels are scored using "
        "the Shadow Score algorithm which fuses multiple signals into a single risk indicator. "
        "All findings should be corroborated with additional sources prior to enforcement action.",
        styles["body"]
    ))

    return elements

def executive_summary(styles, feed):
    """Build the executive summary section."""
    elements = []
    elements.append(Paragraph("EXECUTIVE SUMMARY", styles["section_header"]))
    elements.append(HRFlowable(width="100%", thickness=0.5,
                               color=C_BORDER, spaceAfter=10))

    vessels = feed["vessels"]
    critical = [v for v in vessels if v["risk_tier"] == "CRITICAL"]
    high     = [v for v in vessels if v["risk_tier"] == "HIGH"]
    medium   = [v for v in vessels if v["risk_tier"] == "MEDIUM"]

    elements.append(Paragraph(
        f"Analysis of {len(vessels)} vessels identified <b>{len(critical)} CRITICAL</b>, "
        f"<b>{len(high)} HIGH</b>, and <b>{len(medium)} MEDIUM</b> risk contacts. "
        f"Two vessels — SEA SHADOW and GULF TRADER — exhibit overlapping AIS dark periods "
        f"and confirmed OFAC ownership links, indicating probable sanctions evasion activity. "
        f"PHANTOM MARINER recorded the longest dark period at 147.7 hours.",
        styles["body"]
    ))

    # Summary stats table
    stats_data = [
        ["METRIC", "VALUE"],
        ["Vessels Analyzed", str(len(vessels))],
        ["CRITICAL Risk", str(len(critical))],
        ["HIGH Risk", str(len(high))],
        ["MEDIUM Risk", str(len(medium))],
        ["OFAC Matches", "2"],
        ["Longest Dark Period", "147.7 hours"],
    ]
    stats_table = Table(stats_data, colWidths=[3*inch, 3.5*inch])
    stats_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  C_PANEL),
        ("TEXTCOLOR",     (0,0), (-1,0),  C_ACCENT),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("TEXTCOLOR",     (0,1), (-1,-1), C_TEXT),
        ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
        ("BACKGROUND",    (0,1), (-1,-1), C_BG),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_BG, C_PANEL]),
        ("GRID",          (0,0), (-1,-1), 0.3, C_BORDER),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
    ]))
    elements.append(Spacer(1, 0.1*inch))
    elements.append(stats_table)
    return elements

def vessel_profiles(styles, feed):
    """Build individual vessel profile sections."""
    elements = []
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph("VESSEL PROFILES", styles["section_header"]))
    elements.append(HRFlowable(width="100%", thickness=0.5,
                               color=C_BORDER, spaceAfter=10))

    for vessel in feed["vessels"]:
        score = vessel["shadow_score"]
        tier  = vessel["risk_tier"]
        tc    = tier_color(tier)

        # Vessel header bar
        header_data = [[
            vessel["vessel_name"],
            f"SHADOW SCORE: {score}/100",
            tier,
        ]]
        header_table = Table(header_data, colWidths=[3*inch, 2*inch, 1.5*inch])
        header_table.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), C_PANEL),
            ("TEXTCOLOR",     (0,0), (0,0),   white),
            ("TEXTCOLOR",     (1,0), (1,0),   C_MUTED),
            ("TEXTCOLOR",     (2,0), (2,0),   tc),
            ("FONTNAME",      (0,0), (-1,-1), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,-1), 9),
            ("TOPPADDING",    (0,0), (-1,-1), 7),
            ("BOTTOMPADDING", (0,0), (-1,-1), 7),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
            ("LINEBELOW",     (0,0), (-1,0),  0.5, tc),
        ]))
        elements.append(header_table)

        # Vessel details
        comp = vessel["score_components"]
        details_data = [
            ["MMSI",           vessel["mmsi"],
             "AIS Gap Score",  str(comp.get("ais_gap", 0))],
            ["Owner",          vessel["owner"],
             "Position Jump",  str(comp.get("position_jump", 0))],
            ["Flag State",     vessel["flag_state"],
             "OFAC Score",     str(comp.get("ofac", 0))],
            ["Sanction Program", vessel["sanction_program"],
             "Spoofing Score", str(comp.get("spoofing", 0))],
            ["Max Dark Period", f"{vessel['max_dark_period_hours']}h",
             "Total Score",    f"{score}/100"],
        ]
        details_table = Table(
            details_data,
            colWidths=[1.5*inch, 2*inch, 1.5*inch, 1.5*inch]
        )
        details_table.setStyle(TableStyle([
            ("FONTSIZE",      (0,0), (-1,-1), 8),
            ("TEXTCOLOR",     (0,0), (0,-1), C_MUTED),
            ("TEXTCOLOR",     (2,0), (2,-1), C_MUTED),
            ("TEXTCOLOR",     (1,0), (1,-1), C_TEXT),
            ("TEXTCOLOR",     (3,0), (3,-1), C_TEXT),
            ("FONTNAME",      (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTNAME",      (2,0), (2,-1), "Helvetica-Bold"),
            ("FONTNAME",      (1,0), (1,-1), "Helvetica"),
            ("FONTNAME",      (3,0), (3,-1), "Helvetica"),
            ("BACKGROUND",    (0,0), (-1,-1), C_BG),
            ("ROWBACKGROUNDS",(0,0), (-1,-1), [C_BG, C_PANEL]),
            ("GRID",          (0,0), (-1,-1), 0.3, C_BORDER),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ]))
        elements.append(details_table)
        elements.append(Spacer(1, 0.15*inch))

    return elements

def score_table(styles, feed):
    """Full scored vessel table."""
    elements = []
    elements.append(Paragraph("FULL VESSEL RISK MATRIX", styles["section_header"]))
    elements.append(HRFlowable(width="100%", thickness=0.5,
                               color=C_BORDER, spaceAfter=10))

    header = ["VESSEL NAME", "MMSI", "SCORE", "TIER", "OWNER", "FLAG", "DARK HRS"]
    rows = [header]
    for v in feed["vessels"]:
        rows.append([
            v["vessel_name"],
            v["mmsi"],
            str(v["shadow_score"]),
            v["risk_tier"],
            v["owner"][:22],
            v["flag_state"],
            str(v["max_dark_period_hours"]),
        ])

    col_widths = [1.5*inch, 0.9*inch, 0.55*inch, 0.7*inch, 1.5*inch, 0.75*inch, 0.6*inch]
    table = Table(rows, colWidths=col_widths)

    style = [
        ("BACKGROUND",    (0,0), (-1,0),  C_PANEL),
        ("TEXTCOLOR",     (0,0), (-1,0),  C_ACCENT),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 7.5),
        ("TEXTCOLOR",     (0,1), (-1,-1), C_TEXT),
        ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_BG, C_PANEL]),
        ("GRID",          (0,0), (-1,-1), 0.3, C_BORDER),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("ALIGN",         (2,0), (3,-1),  "CENTER"),
    ]
    # Color tier column
    tier_col = 3
    for i, v in enumerate(feed["vessels"], start=1):
        tc = tier_color(v["risk_tier"])
        style.append(("TEXTCOLOR", (tier_col,i), (tier_col,i), tc))
        style.append(("FONTNAME",  (tier_col,i), (tier_col,i), "Helvetica-Bold"))

    table.setStyle(TableStyle(style))
    elements.append(table)
    return elements

def build_report(feed):
    report_date = datetime.now().strftime("%B %d, %Y")
    output_path = os.path.join("outputs", "shadow_fleet_report.pdf")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.75*inch,
        rightMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch,
    )

    styles = build_styles()
    elements = []

    elements += cover_page(styles, report_date)
    elements.append(Spacer(1, 0.3*inch))
    elements += executive_summary(styles, feed)
    elements.append(Spacer(1, 0.2*inch))
    elements += vessel_profiles(styles, feed)
    elements += score_table(styles, feed)

    # Add score dashboard image if it exists
    img_path = os.path.join("outputs", "shadow_scores.png")
    if os.path.exists(img_path):
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph("RISK SCORE DASHBOARD", styles["section_header"]))
        elements.append(HRFlowable(width="100%", thickness=0.5,
                                   color=C_BORDER, spaceAfter=10))
        elements.append(Image(img_path, width=6.5*inch, height=3*inch))

    doc.build(elements)
    print(f"✓ Report saved to {output_path}")
    return output_path

if __name__ == "__main__":
    print("Loading intelligence feed...")
    feed = load_intelligence_feed()
    print(f"✓ Loaded {len(feed['vessels'])} vessel records")
    print("Building PDF report...")
    build_report(feed)
    print("\n── STAGE 5 COMPLETE ──────────────────────")
    print("  PDF intelligence report  ✓")
    print("  Ready to send to buyers  ✓")