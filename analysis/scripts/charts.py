# voxchart_roi/scripts/charts.py
# Generates all Plotly PNG charts

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from analysis import build_roi_table, build_breakeven_table, build_retention_table, build_5yr_projection
from config import VOXCHART_COST_MONTH, RN_REPLACEMENT_COST

OUT = "charts"
os.makedirs(OUT, exist_ok=True)

def save(fig, name, caption, desc):
    path = f"{OUT}/{name}.png"
    fig.write_image(path)
    with open(f"{path}.meta.json", "w") as f:
        json.dump({"caption": caption, "description": desc}, f)
    print(f"Saved {path}")

def chart_net_roi():
    df = build_roi_table()
    fig = px.bar(df, x="Nurses", y="Net Annual ROI", color="Scenario", barmode="group",
                 title="VoxChart Net Annual ROI by Unit Size",
                 labels={"Nurses": "Nurses/Unit", "Net Annual ROI": "Net ROI ($)"})
    fig.update_layout(legend=dict(orientation='h', yanchor='bottom', y=1.05, xanchor='center', x=0.5))
    fig.update_traces(cliponaxis=False)
    save(fig, "01_net_roi", "Net Annual ROI by unit size", "Grouped bar chart of ROI across unit sizes and savings scenarios")

def chart_savings_vs_cost():
    df = build_roi_table()
    df20 = df[df["Nurses"] == 20]
    fig = go.Figure()
    fig.add_bar(x=df20["Scenario"], y=df20["Monthly OT Savings"], name="Monthly OT Savings")
    fig.add_bar(x=df20["Scenario"], y=[VOXCHART_COST_MONTH]*3, name="VoxChart Monthly Cost")
    fig.update_layout(barmode="group", title="Monthly Savings vs Cost (20-Nurse Unit)",
                      legend=dict(orientation='h', yanchor='bottom', y=1.05, xanchor='center', x=0.5))
    fig.update_yaxes(title_text="$/Month")
    fig.update_xaxes(title_text="Scenario")
    save(fig, "02_savings_vs_cost", "Monthly OT savings vs VoxChart cost", "Grouped bar chart for 20-nurse unit")

def chart_breakeven():
    df = build_breakeven_table()
    fig = px.bar(df, x="Scenario", y="Breakeven Nurses", text="Breakeven Nurses",
                 title="Nurses Needed to Break Even on VoxChart")
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_yaxes(title_text="# Nurses")
    fig.update_xaxes(title_text="Scenario")
    save(fig, "03_breakeven", "Breakeven nurses per unit", "Bar chart of minimum nurses to cover annual VoxChart cost")

def chart_retention():
    df = build_retention_table()
    fig = go.Figure()
    fig.add_scatter(x=df["RNs Retained"], y=df["Turnover Savings"], mode="lines+markers",
                    name="Turnover Savings", fill="tozeroy")
    fig.add_scatter(x=df["RNs Retained"], y=df["VoxChart Annual"], mode="lines",
                    name="VoxChart Annual Cost", line=dict(dash="dash", width=2))
    fig.update_layout(title="Nurse Retention Savings vs VoxChart Annual Cost",
                      legend=dict(orientation='h', yanchor='bottom', y=1.05, xanchor='center', x=0.5))
    fig.update_yaxes(title_text="Savings ($)")
    fig.update_xaxes(title_text="RNs Retained")
    save(fig, "04_retention", "Retention savings vs VoxChart cost", "Line chart showing rapid ROI from nurse retention")

def chart_5yr():
    df = build_5yr_projection()
    fig = go.Figure()
    fig.add_scatter(x=df["Year"], y=df["Cumulative ROI"], mode="lines+markers", fill="tozeroy",
                    name="Cumulative Net ROI")
    fig.update_layout(title="5-Year Cumulative Net ROI (20-Nurse Unit, Moderate)")
    fig.update_yaxes(title_text="Cumul. ROI ($)")
    fig.update_xaxes(title_text="Year", dtick=1)
    save(fig, "05_5yr_roi", "5-year cumulative ROI", "Line chart of compounding net ROI over 5 years")

if __name__ == "__main__":
    chart_net_roi()
    chart_savings_vs_cost()
    chart_breakeven()
    chart_retention()
    chart_5yr()
    print("All charts generated.")
