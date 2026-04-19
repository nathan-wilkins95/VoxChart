# voxchart_roi/scripts/analysis.py
# Core data generation — builds all ROI DataFrames

import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from config import *

def build_roi_table():
    records = []
    for nurses in UNIT_SIZES:
        for label, saved in SAVINGS_SCENARIOS.items():
            ot_hours_saved   = (saved / 60) * SHIFTS_PER_MONTH * nurses
            monthly_savings  = ot_hours_saved * OT_RATE
            annual_savings   = monthly_savings * 12
            annual_cost      = VOXCHART_COST_MONTH * 12
            net_annual_roi   = annual_savings - annual_cost
            records.append({
                "Nurses":               nurses,
                "Scenario":             label,
                "Min Saved/Shift":      saved,
                "OT Hrs Saved/Mo":      round(ot_hours_saved, 1),
                "Monthly OT Savings":   round(monthly_savings),
                "Annual OT Savings":    round(annual_savings),
                "Annual VoxChart Cost": annual_cost,
                "Net Annual ROI":       round(net_annual_roi),
            })
    return pd.DataFrame(records)

def build_breakeven_table():
    records = []
    for label, saved in SAVINGS_SCENARIOS.items():
        annual_savings_per_nurse = (saved / 60) * SHIFTS_PER_MONTH * 12 * OT_RATE
        breakeven = (VOXCHART_COST_MONTH * 12) / annual_savings_per_nurse
        records.append({"Scenario": label, "Breakeven Nurses": round(breakeven, 1)})
    return pd.DataFrame(records)

def build_retention_table():
    records = []
    for n in range(1, 8):
        records.append({
            "RNs Retained":     n,
            "Turnover Savings": n * RN_REPLACEMENT_COST,
            "VoxChart Annual":  VOXCHART_COST_MONTH * 12,
        })
    return pd.DataFrame(records)

def build_5yr_projection(nurses=20, scenario="Moderate (25 min)"):
    saved = SAVINGS_SCENARIOS[scenario]
    annual_ot  = (saved / 60) * SHIFTS_PER_MONTH * nurses * 12 * OT_RATE
    annual_ret = RNS_RETAINED_PER_YR * RN_REPLACEMENT_COST
    annual_cost = VOXCHART_COST_MONTH * 12
    records = []
    for yr in range(1, PROJECTION_YEARS + 1):
        records.append({
            "Year":            yr,
            "Cumulative ROI":  round((annual_ot + annual_ret - annual_cost) * yr),
            "Annual Net":      round(annual_ot + annual_ret - annual_cost),
        })
    return pd.DataFrame(records)

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    build_roi_table().to_csv("data/roi_table.csv", index=False)
    build_breakeven_table().to_csv("data/breakeven.csv", index=False)
    build_retention_table().to_csv("data/retention.csv", index=False)
    build_5yr_projection().to_csv("data/projection_5yr.csv", index=False)
    print("Data files written to data/")
