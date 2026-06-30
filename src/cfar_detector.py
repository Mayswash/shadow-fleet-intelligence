import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from scipy import ndimage

# ── Reproducibility ──────────────────────────────────────────────
np.random.seed(42)

# ────────────────────────────────────────────────────────────────
# PART 1 — SYNTHETIC SAR SCENE
# Mimics real Sentinel-1 GRD statistics over open ocean
# ────────────────────────────────────────────────────────────────

def generate_sar_scene(rows=512, cols=512):
    """
    Generate a synthetic SAR image with realistic ocean clutter
    and embedded vessel signatures.

    In real SAR:
    - Ocean backscatter follows a Gamma distribution
    - Vessels appear as bright point targets 10-30dB above background
    - Speckle noise is multiplicative (we model this with Gamma)
    """
    print("Generating synthetic SAR scene...")

    # Ocean clutter — Gamma distributed (standard SAR ocean model)
    # shape=1 gives Rayleigh-like distribution matching real ocean
    clutter = np.random.gamma(shape=1.0, scale=0.3, size=(rows, cols))

    # Add spatial variation — rougher sea state in some areas
    # (real ocean has variable wind-driven roughness)
    sea_state = ndimage.gaussian_filter(
        np.random.random((rows, cols)), sigma=50
    ) * 0.4
    ocean = clutter + sea_state

    # Embed synthetic vessels — bright point targets
    # Real vessels: 10-30dB above ocean background
    # We use intensity ratio of ~20x above local mean
    vessels = [
        # (row, col, intensity, size_pixels, label)
        (120, 180, 8.0,  4, "Tanker A"),
        (200, 300, 6.5,  3, "Tanker B"),
        (310, 150, 7.2,  4, "Cargo A"),
        (380, 400, 5.8,  3, "Vessel D"),
        (450, 250, 9.1,  5, "Large Tanker"),
        # Dark vessel — no AIS, positioned away from shipping lanes
        (90,  420, 7.5,  3, "DARK VESSEL"),
    ]

    scene = ocean.copy()
    ground_truth = []

    for row, col, intensity, size, label in vessels:
        # Gaussian point spread function (SAR impulse response)
        for dr in range(-size, size+1):
            for dc in range(-size, size+1):
                r, c = row+dr, col+dc
                if 0 <= r < rows and 0 <= c < cols:
                    dist = np.sqrt(dr**2 + dc**2)
                    scene[r, c] += intensity * np.exp(-dist**2 / (size/2)**2)
        ground_truth.append((row, col, label))

    print(f"✓ Scene generated: {rows}x{cols} pixels")
    print(f"  Ocean mean backscatter: {ocean.mean():.3f}")
    print(f"  {len(vessels)} vessels embedded")
    return scene, ground_truth

# ────────────────────────────────────────────────────────────────
# PART 2 — CFAR DETECTOR
# ────────────────────────────────────────────────────────────────

def cfar_detector(image, guard_cells=2, training_cells=8, pfa=1e-4):
    """
    Cell-Averaging CFAR (CA-CFAR) detector.

    For each pixel (the Cell Under Test / CUT):
    1. Define a guard window around it (excluded from background estimate)
    2. Define a larger training window (used to estimate background)
    3. Compute adaptive threshold = mean(training cells) * threshold_factor
    4. Flag CUT as detection if it exceeds the threshold

    Args:
        image:          2D numpy array of SAR backscatter values
        guard_cells:    Half-width of guard window (excluded from training)
        training_cells: Half-width of training window
        pfa:            Desired probability of false alarm (1e-4 = 1 in 10,000)

    Returns:
        detections: Binary mask where 1 = detected target
        threshold_map: Adaptive threshold at each pixel
    """
    print("\nRunning CFAR detection...")
    rows, cols = image.shape
    detections = np.zeros((rows, cols), dtype=np.uint8)
    threshold_map = np.zeros((rows, cols))

    # Number of training cells in 2D window
    total_window = (2*(guard_cells + training_cells) + 1)**2
    guard_window = (2*guard_cells + 1)**2
    n_training = total_window - guard_window

    # Threshold scaling factor derived from desired Pfa
    # For CA-CFAR: alpha = n_training * (Pfa^(-1/n_training) - 1)
    alpha = n_training * (pfa**(-1.0/n_training) - 1)

    margin = guard_cells + training_cells

    for r in range(margin, rows - margin):
        for c in range(margin, cols - margin):
            # Extract training window (excluding guard cells)
            outer = image[
                r-margin : r+margin+1,
                c-margin : c+margin+1
            ]
            inner = image[
                r-guard_cells : r+guard_cells+1,
                c-guard_cells : c+guard_cells+1
            ]

            # Background estimate from training cells only
            training_sum = outer.sum() - inner.sum()
            background_mean = training_sum / n_training

            # Adaptive threshold
            threshold = alpha * background_mean
            threshold_map[r, c] = threshold

            # Detection decision
            if image[r, c] > threshold:
                detections[r, c] = 1

    print(f"✓ CFAR complete")
    print(f"  Threshold factor (alpha): {alpha:.2f}")
    print(f"  Raw detections: {detections.sum()} pixels")
    return detections, threshold_map

def cluster_detections(detections, min_size=3):
    """
    Group nearby detection pixels into individual vessel candidates.
    A single vessel spans multiple pixels — we cluster them into one detection.
    """
    labeled, n_clusters = ndimage.label(detections)
    vessels = []

    for i in range(1, n_clusters + 1):
        cluster = np.where(labeled == i)
        size = len(cluster[0])
        if size >= min_size:
            # Centroid of cluster
            row = int(np.mean(cluster[0]))
            col = int(np.mean(cluster[1]))
            # Peak intensity within cluster
            peak = image_global[cluster].max()
            vessels.append({
                "row": row,
                "col": col,
                "size_px": size,
                "peak_intensity": round(float(peak), 3),
                "vessel_id": f"SAR-{i:03d}",
            })

    print(f"  Clustered into {len(vessels)} vessel candidates")
    return vessels

# ────────────────────────────────────────────────────────────────
# PART 3 — VISUALIZE AND SAVE RESULTS
# ────────────────────────────────────────────────────────────────

def visualize_results(scene, detections, vessels, ground_truth):
    """Generate a 3-panel visualization of the detection results."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.patch.set_facecolor('#0A0E14')

    # Panel 1 — Raw SAR scene
    ax1 = axes[0]
    ax1.imshow(scene, cmap='gray', vmin=0, vmax=2)
    ax1.set_title('SAR Scene (Port of LA)', color='white', fontsize=12)
    ax1.set_facecolor('#0A0E14')
    ax1.tick_params(colors='gray')
    for spine in ax1.spines.values():
        spine.set_edgecolor('#1A3040')

    # Panel 2 — CFAR detections overlaid
    ax2 = axes[1]
    ax2.imshow(scene, cmap='gray', vmin=0, vmax=2)
    # Overlay detections in red
    det_overlay = np.zeros((*scene.shape, 4))
    det_overlay[detections == 1] = [1, 0.2, 0.2, 0.8]
    ax2.imshow(det_overlay)
    ax2.set_title('CFAR Detections', color='white', fontsize=12)
    ax2.set_facecolor('#0A0E14')
    ax2.tick_params(colors='gray')
    for spine in ax2.spines.values():
        spine.set_edgecolor('#1A3040')

    # Panel 3 — Clustered vessel candidates
    ax3 = axes[2]
    ax3.imshow(scene, cmap='gray', vmin=0, vmax=2)
    colors = {
        "DARK VESSEL": "#FF4444",
        "default": "#00FFB2",
    }
    for v in vessels:
        color = colors["default"]
        label = ""
        # Check if near a ground truth dark vessel
        for gt_row, gt_col, gt_label in ground_truth:
            if abs(v["row"] - gt_row) < 15 and abs(v["col"] - gt_col) < 15:
                if "DARK" in gt_label:
                    color = colors["DARK VESSEL"]
                    label = "DARK"
        size = max(v["size_px"] * 2, 12)
        rect = patches.Rectangle(
            (v["col"] - size//2, v["row"] - size//2),
            size, size,
            linewidth=1.5, edgecolor=color, facecolor='none'
        )
        ax3.add_patch(rect)
        if label:
            ax3.text(
                v["col"], v["row"] - size//2 - 3,
                label, color=color, fontsize=7,
                ha='center', fontweight='bold'
            )

    ax3.set_title('Vessel Candidates', color='white', fontsize=12)
    ax3.set_facecolor('#0A0E14')
    ax3.tick_params(colors='gray')
    for spine in ax3.spines.values():
        spine.set_edgecolor('#1A3040')

    plt.tight_layout()
    output_path = os.path.join("outputs", "cfar_detection.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='#0A0E14')
    plt.close()
    print(f"\n✓ Visualization saved to {output_path}")
    return output_path

# ────────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────────

image_global = None

if __name__ == "__main__":
    # Generate scene
    scene, ground_truth = generate_sar_scene()
    image_global = scene

    # Run CFAR
    detections, threshold_map = cfar_detector(
        scene,
        guard_cells=2,
        training_cells=8,
        pfa=1e-4
    )

    # Cluster into vessel candidates
    vessels = cluster_detections(detections)

    # Print results
    print("\n── DETECTED VESSELS ──────────────────────")
    for v in vessels:
        print(f"  {v['vessel_id']} | Row:{v['row']:4d} Col:{v['col']:4d} | "
              f"Peak:{v['peak_intensity']:.3f} | Size:{v['size_px']}px")

    # Visualize
    visualize_results(scene, detections, vessels, ground_truth)

    print("\n── GROUND TRUTH CHECK ────────────────────")
    for gt_row, gt_col, gt_label in ground_truth:
        found = any(
            abs(v["row"] - gt_row) < 15 and abs(v["col"] - gt_col) < 15
            for v in vessels
        )
        status = "✓ DETECTED" if found else "✗ MISSED"
        print(f"  {status} | {gt_label} at ({gt_row},{gt_col})")