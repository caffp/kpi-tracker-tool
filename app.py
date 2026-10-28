from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import altair as alt

from processing import OUTPUT_COLUMNS, summarize_routes


st.set_page_config(page_title="KPI Tracker Helper", page_icon="🚚", layout="centered")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Serif+Display&display=swap');

    :root {
        --ink: #29231f;
        --muted: #82776e;
        --orange: #e66c32;
        --orange-dark: #b94a20;
        --line: #eadfd6;
        --paper: #fffaf6;
    }
    html, body, [data-testid="stAppViewContainer"] {
        background: var(--paper);
        color: var(--ink);
        font-family: 'DM Sans', sans-serif;
    }
    [data-testid="stHeader"], [data-testid="stToolbar"], footer { display: none; }
    .block-container {
        max-width: 760px;
        padding: 1.15rem 1.25rem 1rem;
    }
    .brand {
        display: flex;
        align-items: center;
        gap: 10px;
        color: var(--ink);
        font-size: 13px;
        font-weight: 700;
        letter-spacing: .02em;
        margin-bottom: 2.2rem;
    }
    .brand-mark {
        display: grid;
        place-items: center;
        width: 28px;
        height: 28px;
        border-radius: 8px;
        background: var(--orange);
        color: white;
        font-size: 15px;
    }
    .intro { margin-bottom: 1.25rem; }
    .eyebrow {
        color: var(--orange-dark);
        font-size: 11px;
        font-weight: 700;
        letter-spacing: .11em;
        text-transform: uppercase;
        margin-bottom: 7px;
    }
    .intro h1 {
        color: var(--ink);
        font-family: 'DM Serif Display', Georgia, serif;
        font-size: 34px;
        font-weight: 400;
        line-height: 1.08;
        margin: 0 0 8px;
    }
    .intro p {
        color: var(--muted);
        font-size: 14px;
        margin: 0;
    }
    [data-testid="stDownloadButton"] button {
        min-height: 42px;
        border: 0;
        border-radius: 7px;
        background: var(--orange);
        color: white;
        font-family: 'DM Sans', sans-serif;
        font-weight: 700;
    }
    [data-testid="stDownloadButton"] button:hover {
        background: var(--orange-dark);
        color: white;
    }
    [data-testid="stAlert"] { padding: .6rem .8rem; }
    @media (max-width: 600px) {
        .block-container { padding: .8rem .9rem; }
        .brand { margin-bottom: 1.25rem; }
        .intro h1 { font-size: 30px; }
        .intro { margin-bottom: .85rem; }
    }
    @media (max-height: 700px) {
        .brand { margin-bottom: 1.25rem; }
        .intro { margin-bottom: .8rem; }
    }
    </style>
    <div class="brand"><span class="brand-mark">🚚</span> HONK HONK, feed me data!</div>
      <div class="eyebrow"><i>(seriously, please feed him)</i></div>
    </div>
    """,
    unsafe_allow_html=True,
)

component = components.declare_component(
    "csv_dropzone", path=str(Path(__file__).parent / "components" / "csv_dropzone")
)
uploaded = component(key="csv_dropzone", default=None)

if uploaded and uploaded.get("csv"):
    try:
        frame = pd.read_csv(io.StringIO(uploaded["csv"]))
        required_columns = {
            "routestart": "RouteStart",
            "scop": "SCOP",
            "locationkey": "LocationKey",
            "requirements": "Requirements",
        }
        columns_by_casefold = {str(column).strip().casefold(): column for column in frame.columns}
        missing_columns = [
            name for key, name in required_columns.items() if key not in columns_by_casefold
        ]
        if missing_columns:
            missing = ", ".join(missing_columns)
            st.error(f"Missing required column(s): {missing}")
        else:
            frame = frame.rename(
                columns={
                    columns_by_casefold[key]: name
                    for key, name in required_columns.items()
                    if columns_by_casefold[key] != name
                }
            )
            summary, excluded_count, invalid_date_count = summarize_routes(frame)
            total_stops = summary[["Appliance", "STH/BOX", "Revisits"]].sum().sum()
            total_revisits = summary["Revisits"].sum()
            st.markdown(
                f"<div style='margin: .9rem 0 .4rem; color:#51463e; font-size:14px'>"
                f"<strong>{total_stops:,.0f}</strong> stops, including "
                f"<strong>{total_revisits:,.0f}</strong> revisits"
                f"<span style='color:#82776e'> &nbsp;·&nbsp; {len(summary):,} days"
                f" &nbsp;·&nbsp; {excluded_count:,} pickup rows excluded</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if invalid_date_count:
                st.warning(f"Skipped {invalid_date_count:,} row(s) with an unreadable RouteStart date.")

            table_tab, chart_tab = st.tabs(["Daily totals", "Chart"])
            with table_tab:
                st.dataframe(
                    summary,
                    hide_index=True,
                    use_container_width=True,
                    height=min(100 + len(summary) * 35, 360),
                )
                st.download_button(
                    "Download daily totals",
                    data=summary.to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"{Path(uploaded.get('name') or 'routes.csv').stem}_daily_totals.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with chart_tab:
                if summary.empty:
                    st.info("No valid route dates to chart.")
                else:
                    chart_data = summary.melt(
                        id_vars="Date", var_name="Delivery type", value_name="Count"
                    )
                    delivery_types = ["Appliance", "STH/BOX", "Revisits"]
                    chart = (
                        alt.Chart(chart_data)
                        .mark_bar()
                        .encode(
                            x=alt.X(
                                "Date:O",
                                sort=summary["Date"].tolist(),
                                title=None,
                                axis=alt.Axis(labelAngle=-35),
                            ),
                            xOffset=alt.XOffset("Delivery type:N", sort=delivery_types),
                            y=alt.Y("Count:Q", title="Stops"),
                            color=alt.Color(
                                "Delivery type:N",
                                sort=delivery_types,
                                scale=alt.Scale(
                                    domain=delivery_types,
                                    range=["#e66c32", "#287c75", "#52443d"],
                                ),
                                legend=alt.Legend(orient="top", title=None),
                            ),
                            tooltip=["Date:O", "Delivery type:N", "Count:Q"],
                        )
                        .properties(height=240)
                    )
                    st.altair_chart(chart, use_container_width=True)
    except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as error:
        st.error(f"Could not read this CSV: {error}")