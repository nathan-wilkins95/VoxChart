# analysis/dashboard/app.py
# VoxChart ROI Interactive Dash Dashboard
# Run: python analysis/dashboard/app.py

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../scripts"))

from dash import Dash, dcc, html, Input, Output, callback
import plotly.express as px
import plotly.graph_objects as go
from analysis import build_roi_table, build_breakeven_table, build_retention_table, build_5yr_projection
from config import UNIT_SIZES, SAVINGS_SCENARIOS, VOXCHART_COST_MONTH, RN_REPLACEMENT_COST

app = Dash(__name__, title="VoxChart ROI Dashboard")

# ── Layout ─────────────────────────────────────────────────────
app.layout = html.Div(style={"fontFamily": "Source Sans Pro, sans-serif", "backgroundColor": "#f8fafc", "minHeight": "100vh", "padding": "0"}, children=[

    # Header
    html.Div(style={"backgroundColor": "#1B3A6B", "padding": "28px 40px", "marginBottom": "32px"}, children=[
        html.H1("Vox Medical", style={"color": "#ffffff", "margin": 0, "fontSize": "28px", "fontWeight": 600, "letterSpacing": "0.05em"}),
        html.P("ROI Cost-Efficiency Dashboard", style={"color": "#8BAEDB", "margin": "4px 0 0 0", "fontSize": "15px"}),
        html.P("Less charting. More caring.", style={"color": "#0E7C7B", "margin": "2px 0 0 0", "fontSize": "13px", "fontStyle": "italic"}),
    ]),

    # Controls
    html.Div(style={"maxWidth": "1200px", "margin": "0 auto", "padding": "0 32px"}, children=[

        html.Div(style={"backgroundColor": "#ffffff", "borderRadius": "12px", "padding": "24px 32px", "marginBottom": "28px",
                        "boxShadow": "0 1px 4px rgba(0,0,0,0.08)", "display": "flex", "gap": "40px", "flexWrap": "wrap"}, children=[

            html.Div(children=[
                html.Label("Nurses per Unit", style={"fontWeight": 600, "color": "#1B3A6B", "fontSize": "14px", "display": "block", "marginBottom": "8px"}),
                dcc.Slider(id="nurses-slider", min=10, max=50, step=10, value=20,
                           marks={n: str(n) for n in UNIT_SIZES},
                           tooltip={"placement": "bottom", "always_visible": True}),
            ], style={"flex": "1", "minWidth": "260px"}),

            html.Div(children=[
                html.Label("Savings Scenario", style={"fontWeight": 600, "color": "#1B3A6B", "fontSize": "14px", "display": "block", "marginBottom": "8px"}),
                dcc.Dropdown(id="scenario-dropdown",
                             options=[{"label": k, "value": k} for k in SAVINGS_SCENARIOS],
                             value="Moderate (25 min)", clearable=False,
                             style={"fontSize": "14px"}),
            ], style={"flex": "1", "minWidth": "220px"}),

            html.Div(children=[
                html.Label("VoxChart Monthly Cost ($)", style={"fontWeight": 600, "color": "#1B3A6B", "fontSize": "14px", "display": "block", "marginBottom": "8px"}),
                dcc.Input(id="cost-input", type="number", value=1000, min=100, max=10000, step=100,
                          style={"width": "160px", "padding": "8px 12px", "border": "1px solid #CBD5E1",
                                 "borderRadius": "6px", "fontSize": "14px"}),
            ], style={"flex": "0 0 auto"}),
        ]),

        # KPI Cards
        html.Div(id="kpi-cards", style={"display": "flex", "gap": "20px", "marginBottom": "28px", "flexWrap": "wrap"}),

        # Charts row 1
        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "20px", "marginBottom": "20px"}, children=[
            html.Div(style={"backgroundColor": "#fff", "borderRadius": "12px", "padding": "20px", "boxShadow": "0 1px 4px rgba(0,0,0,0.08)"}, children=[
                html.H3("Net Annual ROI by Unit Size", style={"color": "#1B3A6B", "fontSize": "15px", "margin": "0 0 16px 0", "fontWeight": 600}),
                dcc.Graph(id="chart-roi", config={"displayModeBar": False}),
            ]),
            html.Div(style={"backgroundColor": "#fff", "borderRadius": "12px", "padding": "20px", "boxShadow": "0 1px 4px rgba(0,0,0,0.08)"}, children=[
                html.H3("Monthly Savings vs Subscription Cost", style={"color": "#1B3A6B", "fontSize": "15px", "margin": "0 0 16px 0", "fontWeight": 600}),
                dcc.Graph(id="chart-savings", config={"displayModeBar": False}),
            ]),
        ]),

        # Charts row 2
        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "20px", "marginBottom": "20px"}, children=[
            html.Div(style={"backgroundColor": "#fff", "borderRadius": "12px", "padding": "20px", "boxShadow": "0 1px 4px rgba(0,0,0,0.08)"}, children=[
                html.H3("Nurses Needed to Break Even", style={"color": "#1B3A6B", "fontSize": "15px", "margin": "0 0 16px 0", "fontWeight": 600}),
                dcc.Graph(id="chart-breakeven", config={"displayModeBar": False}),
            ]),
            html.Div(style={"backgroundColor": "#fff", "borderRadius": "12px", "padding": "20px", "boxShadow": "0 1px 4px rgba(0,0,0,0.08)"}, children=[
                html.H3("Nurse Retention Savings vs Annual Cost", style={"color": "#1B3A6B", "fontSize": "15px", "margin": "0 0 16px 0", "fontWeight": 600}),
                dcc.Graph(id="chart-retention", config={"displayModeBar": False}),
            ]),
        ]),

        # Chart row 3
        html.Div(style={"backgroundColor": "#fff", "borderRadius": "12px", "padding": "20px", "boxShadow": "0 1px 4px rgba(0,0,0,0.08)", "marginBottom": "40px"}, children=[
            html.H3("5-Year Cumulative Net ROI Projection", style={"color": "#1B3A6B", "fontSize": "15px", "margin": "0 0 16px 0", "fontWeight": 600}),
            dcc.Graph(id="chart-5yr", config={"displayModeBar": False}),
        ]),

        # Footer
        html.Div(style={"textAlign": "center", "padding": "20px 0 40px", "color": "#94A3B8", "fontSize": "13px"}, children=[
            html.P("Vox Medical · Less charting. More caring."),
            html.P("Data sources: AACN (2023), ImmersyveHealth (2025), KLAS Research (2025), Palojoki et al. (2022)"),
        ]),
    ]),
])

# ── Callbacks ─────────────────────────────────────────────────────
@callback(
    Output("kpi-cards", "children"),
    Output("chart-roi", "figure"),
    Output("chart-savings", "figure"),
    Output("chart-breakeven", "figure"),
    Output("chart-retention", "figure"),
    Output("chart-5yr", "figure"),
    Input("nurses-slider", "value"),
    Input("scenario-dropdown", "value"),
    Input("cost-input", "value"),
)
def update_all(nurses, scenario, monthly_cost):
    if not monthly_cost:
        monthly_cost = 1000
    annual_cost = monthly_cost * 12

    saved = SAVINGS_SCENARIOS[scenario]
    ot_hr_saved = (saved / 60) * 20 * nurses
    monthly_ot  = ot_hr_saved * 54
    annual_ot   = monthly_ot * 12
    net_roi     = annual_ot - annual_cost
    retention   = 1 * RN_REPLACEMENT_COST
    five_yr     = (annual_ot + retention - annual_cost) * 5

    def kpi_card(title, value, color="#1B3A6B"):
        return html.Div(style={"backgroundColor": "#fff", "borderRadius": "12px", "padding": "20px 28px",
                               "boxShadow": "0 1px 4px rgba(0,0,0,0.08)", "flex": "1", "minWidth": "180px",
                               "borderTop": f"4px solid {color}"}, children=[
            html.P(title, style={"color": "#64748B", "fontSize": "13px", "margin": "0 0 6px 0", "fontWeight": 600}),
            html.P(value, style={"color": color, "fontSize": "26px", "fontWeight": 700, "margin": 0}),
        ])

    cards = [
        kpi_card("Annual OT Savings",    f"${annual_ot:,.0f}",   "#0E7C7B"),
        kpi_card("Net Annual ROI",        f"${net_roi:,.0f}",     "#1B3A6B"),
        kpi_card("ROI Multiple",          f"{net_roi/annual_cost:.1f}×", "#2563EB"),
        kpi_card("5-Year Cumulative ROI", f"${five_yr:,.0f}",    "#7C3AED"),
    ]

    scenarios = list(SAVINGS_SCENARIOS.keys())

    # Chart 1
    df = build_roi_table()
    df_s = df[df["Scenario"] == scenario]
    fig1 = px.bar(df_s, x="Nurses", y="Net Annual ROI", color_discrete_sequence=["#1B3A6B"],
                  labels={"Nurses": "Nurses/Unit", "Net Annual ROI": "Net ROI ($)"})
    fig1.update_layout(margin=dict(t=10, b=40, l=40, r=10), plot_bgcolor="#f8fafc", paper_bgcolor="#fff", height=280)
    fig1.update_traces(cliponaxis=False)

    # Chart 2
    savings_vals = [(SAVINGS_SCENARIOS[s]/60)*20*20*54 for s in scenarios]
    fig2 = go.Figure()
    fig2.add_bar(x=scenarios, y=savings_vals, name="Monthly OT Savings", marker_color="#0E7C7B")
    fig2.add_bar(x=scenarios, y=[monthly_cost]*3, name="VoxChart Monthly Cost", marker_color="#1B3A6B")
    fig2.update_layout(barmode="group", margin=dict(t=10, b=60, l=40, r=10),
                       plot_bgcolor="#f8fafc", paper_bgcolor="#fff", height=280,
                       legend=dict(orientation="h", y=-0.3))
    fig2.update_yaxes(title_text="$/Month")

    # Chart 3
    be_vals = [annual_cost / ((SAVINGS_SCENARIOS[s]/60)*20*12*54) for s in scenarios]
    fig3 = go.Figure(go.Bar(x=scenarios, y=be_vals, text=[f"{v:.1f}" for v in be_vals],
                             textposition="outside", marker_color=["#1B3A6B","#0E7C7B","#2563EB"]))
    fig3.update_layout(margin=dict(t=20, b=40, l=40, r=10), plot_bgcolor="#f8fafc", paper_bgcolor="#fff", height=280)
    fig3.update_yaxes(title_text="# Nurses")
    fig3.update_traces(cliponaxis=False)

    # Chart 4
    rns = list(range(1, 8))
    fig4 = go.Figure()
    fig4.add_scatter(x=rns, y=[n*RN_REPLACEMENT_COST for n in rns], mode="lines+markers",
                     name="Turnover Savings", fill="tozeroy", line=dict(color="#0E7C7B", width=2))
    fig4.add_scatter(x=rns, y=[annual_cost]*7, mode="lines", name="VoxChart Annual",
                     line=dict(dash="dash", color="#1B3A6B", width=2))
    fig4.update_layout(margin=dict(t=10, b=60, l=40, r=10), plot_bgcolor="#f8fafc", paper_bgcolor="#fff",
                       height=280, legend=dict(orientation="h", y=-0.3))
    fig4.update_yaxes(title_text="Savings ($)")
    fig4.update_xaxes(title_text="RNs Retained")

    # Chart 5
    annual_net = annual_ot + retention - annual_cost
    years = list(range(1, 6))
    fig5 = go.Figure()
    fig5.add_scatter(x=years, y=[annual_net*yr for yr in years], mode="lines+markers",
                     fill="tozeroy", line=dict(color="#1B3A6B", width=3),
                     marker=dict(size=8, color="#0E7C7B"))
    fig5.update_layout(margin=dict(t=10, b=40, l=60, r=10), plot_bgcolor="#f8fafc", paper_bgcolor="#fff", height=300)
    fig5.update_yaxes(title_text="Cumul. ROI ($)")
    fig5.update_xaxes(title_text="Year", dtick=1)

    return cards, fig1, fig2, fig3, fig4, fig5


if __name__ == "__main__":
    app.run(debug=True, port=8050)
