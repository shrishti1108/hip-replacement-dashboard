"""Patient Demographics and Outcome Trends — Streamlit Dashboard.

Ported from dashboard.html / data.json. Same chart set, same visual language,
native Streamlit controls. Run locally:

    streamlit run app.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).parent
CSV = ROOT / "cleaned_hip_replacement_data.csv"

PALETTE = ["#2a9ad9", "#ff8a1f", "#e45c5c", "#2ec4a7",
           "#c47be0", "#ffd45e", "#8fb9ff", "#f48fb1",
           "#b5d99c", "#f6a56b", "#9ca8c4", "#6bd1ff"]

SEV_RISK_COLORS = {
    "Minor":    "#2ec4a7",
    "Moderate": "#2a9ad9",
    "Major":    "#ff8a1f",
    "Extreme":  "#e45c5c",
}

ORDERED_AGE = ["0 to 17", "18 to 29", "30 to 49", "50 to 69", "70 or older"]
ORDERED_SEV = ["Minor", "Moderate", "Major", "Extreme"]
ORDERED_RISK = ORDERED_SEV


# ------------------------------------------------------------------ #
# Data
# ------------------------------------------------------------------ #
@st.cache_data(show_spinner="Loading data…")
def load_data() -> pd.DataFrame:
    df = pd.read_csv(CSV, low_memory=False)

    df["facility_name"] = df["facility_name"].str.title()
    df["gender"] = df["gender"].map({"f": "Female", "m": "Male"})
    df["race"] = df["race"].str.title()
    df["ethnicity"] = df["ethnicity"].str.title()
    df["patient_disposition"] = df["patient_disposition"].str.title()
    df["apr_severity_of_illness_description"] = df["apr_severity_of_illness_description"].str.title()
    df["apr_risk_of_mortality"] = df["apr_risk_of_mortality"].str.title()

    return df


# ------------------------------------------------------------------ #
# Layout helpers
# ------------------------------------------------------------------ #
def inject_css() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
              radial-gradient(1200px 600px at 20% -10%, rgba(42,154,217,0.18), transparent 60%),
              radial-gradient(900px 500px at 110% 10%, rgba(255,138,31,0.12), transparent 60%),
              linear-gradient(180deg, #081629 0%, #0b1b33 40%, #0a1a30 100%);
        }
        header[data-testid="stHeader"] { display: none !important; }
        div[data-testid="stToolbar"] { display: none !important; }
        div[data-testid="stDecoration"] { display: none !important; }
        .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 1500px; }

        /* Header bar */
        .hipbanner {
            background: linear-gradient(90deg, #c94f0b 0%, #ff8a1f 50%, #c94f0b 100%);
            color: #fff7e6;
            font-family: Georgia, "Times New Roman", serif;
            font-weight: 700;
            letter-spacing: 1.5px;
            font-size: 22px;
            text-align: center;
            padding: 14px 18px;
            border-radius: 6px;
            box-shadow: 0 6px 18px rgba(0,0,0,0.35);
            text-transform: uppercase;
            margin-bottom: 14px;
        }

        /* KPI card */
        .kpi {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.09);
            border-radius: 6px;
            padding: 12px 14px;
            text-align: center;
        }
        .kpi .label {
            font-size: 10px;
            letter-spacing: 1.5px;
            color: #c7d2e0;
            text-transform: uppercase;
            font-weight: 600;
        }
        .kpi .value {
            font-size: 26px;
            font-weight: 700;
            color: #fff;
            margin-top: 4px;
            font-variant-numeric: tabular-nums;
        }

        /* Chart card wrapper */
        .card-title {
            font-family: Georgia, serif;
            font-size: 14px;
            letter-spacing: 2px;
            text-transform: uppercase;
            color: #fff;
            text-align: center;
            font-weight: 600;
            border-bottom: 1px solid rgba(255,255,255,0.09);
            padding-bottom: 6px;
            margin: 8px 0 8px;
        }

        /* Gender/Race table */
        .crosstab table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            color: #c7d2e0;
        }
        .crosstab th {
            background: #0f2547;
            color: #ffb454;
            text-align: left;
            padding: 6px 8px;
            font-weight: 600;
            letter-spacing: 0.5px;
            border-bottom: 1px solid rgba(255,255,255,0.09);
        }
        .crosstab td {
            padding: 5px 8px;
            border-bottom: 1px dashed rgba(255,255,255,0.06);
        }
        .crosstab td.num { text-align: right; color: #fff; font-variant-numeric: tabular-nums; }

        /* Tighter multiselect */
        div[data-baseweb="select"] > div { background: #0a2140; }
        .stMultiSelect label, .stSelectbox label { color: #ffb454 !important; font-size: 11px; letter-spacing: 1.5px; text-transform: uppercase; font-weight: 600; }
        /* Let multi-select chips wrap & scroll so nothing gets clipped */
        .stMultiSelect div[data-baseweb="select"] > div:first-child {
            max-height: 110px;
            overflow-y: auto;
            flex-wrap: wrap;
        }
        .stMultiSelect [data-baseweb="tag"] {
            background-color: #ff8a1f !important;
        }

        footer { visibility: hidden; }
        #MainMenu { visibility: hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def kpi(col, label: str, value: str) -> None:
    col.markdown(
        f"""<div class="kpi"><div class="label">{label}</div>
        <div class="value">{value}</div></div>""",
        unsafe_allow_html=True,
    )


def card_title(text: str) -> None:
    st.markdown(f'<div class="card-title">{text}</div>', unsafe_allow_html=True)


def fmt_num(n: float) -> str:
    if n >= 1e6:
        return f"{n/1e6:.2f}M"
    if n >= 1e3:
        return f"{n/1e3:.1f}K"
    return f"{n:,.0f}"


def fmt_money(n: float) -> str:
    return "$" + fmt_num(n)


# ------------------------------------------------------------------ #
# Plotly defaults
# ------------------------------------------------------------------ #
def apply_dark(fig: go.Figure, height: int = 300) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#c7d2e0", family='Inter, "Segoe UI", sans-serif', size=11),
        margin=dict(l=10, r=10, t=10, b=60),
        height=height,
        legend=dict(
            orientation="h",
            yanchor="top", y=-0.18,
            xanchor="center", x=0.5,
            bgcolor="rgba(0,0,0,0)",
            title_text="",
        ),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.06)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)", zeroline=False)
    return fig


# ------------------------------------------------------------------ #
# Page
# ------------------------------------------------------------------ #
st.set_page_config(
    page_title="Patient Demographics & Outcomes — Hip Replacement",
    page_icon="🏥",
    layout="wide",
)
inject_css()

st.markdown(
    '<div class="hipbanner">Patient Demographics and Outcome Trends Dashboard</div>',
    unsafe_allow_html=True,
)

df = load_data()

# ---------------- Filters ----------------
f1, f2, f3, f4, f5, f6 = st.columns(6)
with f1:
    age_sel = st.multiselect("Age Group", ORDERED_AGE, default=ORDERED_AGE)
with f2:
    gen_sel = st.multiselect("Gender", ["Female", "Male"], default=["Female", "Male"])
with f3:
    sev_sel = st.multiselect("Severity", ORDERED_SEV, default=ORDERED_SEV)
with f4:
    risk_sel = st.multiselect("Risk of Mortality", ORDERED_RISK, default=ORDERED_RISK)
with f5:
    race_opts = sorted(df["race"].dropna().unique().tolist())
    race_sel = st.multiselect("Race", race_opts, default=race_opts)
with f6:
    hosp_opts = ["All"] + sorted(df["facility_name"].dropna().unique().tolist())
    hosp_pick = st.selectbox("Hospital", hosp_opts, index=0)

# Apply filters
mask = (
    df["age_group"].isin(age_sel)
    & df["gender"].isin(gen_sel)
    & df["apr_severity_of_illness_description"].isin(sev_sel)
    & df["apr_risk_of_mortality"].isin(risk_sel)
    & df["race"].isin(race_sel)
)
if hosp_pick != "All":
    mask &= df["facility_name"] == hosp_pick
fdf = df[mask]

# ---------------- KPIs ----------------
k1, k2, k3, k4, k5, k6 = st.columns(6)
n = len(fdf)
avg_los = fdf["length_of_stay"].mean() if n else 0
avg_cost = fdf["total_costs"].mean() if n else 0
avg_chg = fdf["total_charges"].mean() if n else 0
sum_cost = fdf["total_costs"].sum() if n else 0
hosps = fdf["facility_name"].nunique()

kpi(k1, "Discharges", fmt_num(n))
kpi(k2, "Avg Length of Stay", f"{avg_los:.2f}")
kpi(k3, "Avg Total Cost", fmt_money(avg_cost))
kpi(k4, "Avg Total Charges", fmt_money(avg_chg))
kpi(k5, "Total Cost (Sum)", fmt_money(sum_cost))
kpi(k6, "Hospitals Covered", str(hosps))

if n == 0:
    st.warning("No records match the current filters. Try widening them.")
    st.stop()

# ---------------- Row 1: LOS / Severity vs Mortality / Disposition ----------------
c1, c2, c3 = st.columns(3)

with c1:
    card_title("LOS by Age Group")
    agg = (
        fdf.groupby(["age_group", "apr_severity_of_illness_description"])["length_of_stay"]
        .mean().reset_index()
    )
    agg["age_group"] = pd.Categorical(agg["age_group"], categories=ORDERED_AGE, ordered=True)
    agg["apr_severity_of_illness_description"] = pd.Categorical(
        agg["apr_severity_of_illness_description"], categories=ORDERED_SEV, ordered=True
    )
    agg = agg.sort_values(["age_group", "apr_severity_of_illness_description"])
    fig = px.bar(
        agg, x="age_group", y="length_of_stay",
        color="apr_severity_of_illness_description",
        color_discrete_map=SEV_RISK_COLORS,
        category_orders={"age_group": ORDERED_AGE,
                         "apr_severity_of_illness_description": ORDERED_SEV},
        labels={"length_of_stay": "Avg LOS (days)",
                "age_group": "Age Group",
                "apr_severity_of_illness_description": ""},
    )
    fig.update_layout(barmode="stack")
    st.plotly_chart(apply_dark(fig), use_container_width=True, config={"displayModeBar": False})

with c2:
    card_title("Severity vs Mortality Risk")
    cross = (
        fdf.groupby(["apr_severity_of_illness_description", "apr_risk_of_mortality"])
        .size().reset_index(name="count")
    )
    fig = px.bar(
        cross, x="apr_severity_of_illness_description", y="count",
        color="apr_risk_of_mortality",
        color_discrete_map=SEV_RISK_COLORS,
        category_orders={"apr_severity_of_illness_description": ORDERED_SEV,
                         "apr_risk_of_mortality": ORDERED_RISK},
        barmode="group",
        labels={"count": "Discharges",
                "apr_severity_of_illness_description": "Severity",
                "apr_risk_of_mortality": ""},
    )
    st.plotly_chart(apply_dark(fig), use_container_width=True, config={"displayModeBar": False})

with c3:
    card_title("Patient Disposition")
    disp = fdf["patient_disposition"].value_counts()
    top = disp.head(5)
    other = disp.iloc[5:].sum()
    if other > 0:
        top = pd.concat([top, pd.Series({"Other": other})])
    total = top.sum()
    pct = (top / total * 100)
    # Only show label text for slices >= 3%; small slices get legend only.
    text = [f"{p:.1f}%" if p >= 3 else "" for p in pct]
    fig = go.Figure(
        go.Pie(
            labels=top.index.tolist(),
            values=top.values.tolist(),
            hole=0.55,
            marker=dict(colors=PALETTE[: len(top)], line=dict(color="#0b1b33", width=2)),
            text=text,
            textinfo="text",
            textposition="inside",
            insidetextorientation="horizontal",
            sort=False,
            hovertemplate="%{label}<br>%{value:,} (%{percent})<extra></extra>",
        )
    )
    fig = apply_dark(fig)
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=90),
        legend=dict(
            orientation="h",
            yanchor="top", y=-0.05,
            xanchor="center", x=0.5,
            font=dict(size=10),
            bgcolor="rgba(0,0,0,0)",
            title_text="",
        ),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ---------------- Row 2: Heatmap + Top Hospitals ----------------
c4, c5 = st.columns([5, 7])

with c4:
    card_title("Mortality Risk Heatmap (Age × Risk)")
    cross = (
        fdf.groupby(["age_group", "apr_risk_of_mortality"])
        .size().reset_index(name="count")
    )
    pivot = cross.pivot(index="apr_risk_of_mortality", columns="age_group", values="count").fillna(0)
    pivot = pivot.reindex(index=ORDERED_RISK, columns=ORDERED_AGE)
    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale=[[0, "#0f2547"], [0.25, "#2a9ad9"], [0.6, "#ff8a1f"], [1, "#e45c5c"]],
            hovertemplate="Age %{x}<br>Risk %{y}<br>%{z:,} discharges<extra></extra>",
            colorbar=dict(title="", thickness=12, len=0.8),
        )
    )
    fig.update_xaxes(title="Age Group")
    fig.update_yaxes(title="Risk of Mortality")
    st.plotly_chart(apply_dark(fig, height=300), use_container_width=True, config={"displayModeBar": False})

with c5:
    card_title("Top 10 Hospitals by Avg Total Cost")
    hosp = (
        fdf.groupby("facility_name")
        .agg(avg_cost=("total_costs", "mean"), count=("total_costs", "size"))
        .query("count >= 20")
        .sort_values("avg_cost", ascending=False)
        .head(10)
        .reset_index()
    )
    if hosp.empty:
        st.info("Not enough data at the current filter level.")
    else:
        hosp["short"] = hosp["facility_name"].apply(lambda s: s if len(s) < 38 else s[:35] + "…")
        fig = px.bar(
            hosp.sort_values("avg_cost"),
            x="avg_cost", y="short", orientation="h",
            color="short",
            color_discrete_sequence=PALETTE,
            labels={"avg_cost": "Avg Total Cost ($)", "short": ""},
        )
        fig.update_layout(showlegend=False)
        fig.update_xaxes(tickprefix="$", tickformat=",")
        st.plotly_chart(apply_dark(fig, height=300), use_container_width=True, config={"displayModeBar": False})

# ---------------- Row 3: Cross-tab + Top Age by Cost ----------------
c6, c7 = st.columns(2)

with c6:
    card_title("Avg Total Cost by Gender & Race")
    pivot = (
        fdf.groupby(["race", "gender"])["total_costs"].mean().unstack("gender")
    )
    overall = fdf.groupby("race")["total_costs"].mean()
    pivot["Overall"] = overall
    cols = [c for c in ["Female", "Male", "Overall"] if c in pivot.columns]
    pivot = pivot[cols]

    html = ['<div class="crosstab"><table><thead><tr><th>Race</th>']
    html += [f'<th style="text-align:right">{c}</th>' for c in pivot.columns]
    html.append("</tr></thead><tbody>")
    for race, row in pivot.iterrows():
        html.append(f"<tr><td>{race}</td>")
        for c in pivot.columns:
            v = row[c]
            cell = fmt_money(v) if pd.notna(v) else "—"
            strong_open, strong_close = ("<strong>", "</strong>") if c == "Overall" else ("", "")
            html.append(f'<td class="num">{strong_open}{cell}{strong_close}</td>')
        html.append("</tr>")
    html.append("</tbody></table></div>")
    st.markdown("".join(html), unsafe_allow_html=True)

with c7:
    card_title("Top 5 Age Groups by Avg Cost")
    ag = (
        fdf.groupby("age_group")["total_costs"].mean()
        .sort_values(ascending=False).head(5).reset_index()
    )
    ag = ag.sort_values("total_costs")
    fig = px.bar(
        ag, x="total_costs", y="age_group", orientation="h",
        color="age_group", color_discrete_sequence=PALETTE,
        labels={"total_costs": "Avg Total Cost ($)", "age_group": ""},
    )
    fig.update_layout(showlegend=False)
    fig.update_xaxes(tickprefix="$", tickformat=",")
    st.plotly_chart(apply_dark(fig, height=260), use_container_width=True, config={"displayModeBar": False})

st.caption(f"Source: cleaned_hip_replacement_data.csv · {len(df):,} records total · {n:,} after filters")
