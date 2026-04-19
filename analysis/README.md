# VoxChart ROI Analysis

A Python-based data analysis project modeling the cost efficiency and ROI of
**VoxChart (Vox Medical)** — a voice-powered nursing documentation tool.

## Project Structure

```
voxchart_roi/
├── main.py                  # Run full pipeline
├── requirements.txt         # Python dependencies
├── scripts/
│   ├── config.py            # All assumptions (edit here)
│   ├── analysis.py          # Data generation
│   └── charts.py            # Plotly chart generation
├── notebooks/
│   └── voxchart_roi.ipynb   # Interactive Jupyter notebook
├── data/                    # Generated CSV files
└── charts/                  # Generated PNG charts
```

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run full analysis
python main.py

# 3. Or open the Jupyter notebook
jupyter lab notebooks/voxchart_roi.ipynb
```

## Key Assumptions

All assumptions live in `scripts/config.py` and can be adjusted:

| Parameter | Default | Source |
|---|---|---|
| RN overtime rate | $54/hr | NSI Nursing Solutions |
| RN replacement cost | $61,110 | ImmersyveHealth (2025) |
| VoxChart unit cost | $1,000/mo | Vox Medical pricing |
| Shifts per month | 20 | Standard nursing schedule |
| Time saved per shift | 15–35 min | AACN / KLAS Research |

## Output

Running `main.py` produces:

- `data/roi_table.csv` — Full ROI table across unit sizes and scenarios
- `data/breakeven.csv` — Nurses needed to break even per scenario
- `data/retention.csv` — Turnover savings by nurses retained
- `data/projection_5yr.csv` — 5-year cumulative ROI projection
- `charts/01_net_roi.png` — Net Annual ROI by unit size
- `charts/02_savings_vs_cost.png` — Monthly savings vs cost
- `charts/03_breakeven.png` — Breakeven nurses per unit
- `charts/04_retention.png` — Retention savings vs annual cost
- `charts/05_5yr_roi.png` — 5-year cumulative ROI

## References

- AACN (2023). Nursing documentation burden: A critical problem to solve.
- ImmersyveHealth (2025). The soaring cost of nurse turnover in 2025.
- KLAS Research (2025). Reducing nursing documentation burden.
- Palojoki et al. (2022). Documentation burden in nursing and clinician burnout. PMC.

---
*Less charting. More caring. — Vox Medical*
