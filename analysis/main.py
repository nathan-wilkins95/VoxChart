# voxchart_roi/main.py
# Run the full analysis pipeline

import subprocess, sys

print("=== VoxChart ROI Analysis ===")
print("Step 1: Generating data...")
subprocess.run([sys.executable, "scripts/analysis.py"], check=True)
print("Step 2: Generating charts...")
subprocess.run([sys.executable, "scripts/charts.py"], check=True)
print("Done. Check data/ and charts/ folders.")
