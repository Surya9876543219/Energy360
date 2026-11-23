import os
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from services.databricks_data import EnergyData, DataAccessError

st.set_page_config(page_title="Energy 360 | Enterprise Energy Management", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# ------------------------- Styling -------------------------
st.markdown("""
<style>

/* Keep the native Streamlit sidebar toggle available as a floating control.
   The header overlays the page instead of reserving vertical space. */
header[data-testid="stHeader"],[data-testid="stHeader"]{
 display:flex!important;visibility:visible!important;opacity:1!important;
 position:fixed!important;top:0!important;left:0!important;right:0!important;
 width:100%!important;height:2.75rem!important;min-height:2.75rem!important;
 padding:0!important;margin:0!important;background:transparent!important;
 border:0!important;box-shadow:none!important;overflow:visible!important;
 z-index:100000!important;pointer-events:none!important
}
[data-testid="stHeader"] [data-testid="stToolbar"]{
 display:flex!important;visibility:visible!important;opacity:1!important;
 height:2.75rem!important;min-height:2.75rem!important;
 pointer-events:auto!important;background:transparent!important
}
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarExpandButton"],
[data-testid="stSidebarCollapsedControl"]{
 display:flex!important;visibility:visible!important;opacity:1!important;
 pointer-events:auto!important;position:relative!important;z-index:100002!important
}
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarExpandButton"] button,
[data-testid="stSidebarCollapsedControl"] button{
 display:flex!important;visibility:visible!important;opacity:1!important;
 pointer-events:auto!important;color:#173A59!important;background:#FFFFFF!important;
 border:1px solid #DCE6EF!important;border-radius:7px!important
}
[data-testid="stAppViewContainer"] .main{padding-top:0!important;margin-top:0!important}
section[data-testid="stMain"]{padding-top:0!important}

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"]{font-family:Inter,Arial,sans-serif}
.stApp{background:#F4F7FB;color:#17324D}
.block-container{padding-top:0!important;padding-bottom:2rem;max-width:none!important;width:100%!important;margin-left:0!important;margin-right:0!important;box-sizing:border-box}
[data-testid="stMainBlockContainer"],.stMainBlockContainer,section[data-testid="stMain"] .block-container{width:100%!important;max-width:none!important;margin-left:0!important;margin-right:0!important;padding-left:clamp(1rem,2vw,2rem)!important;padding-right:clamp(1rem,2vw,2rem)!important;box-sizing:border-box!important}
[data-testid="stMain"]{min-width:0!important}
[data-testid="stAppViewContainer"]{width:100%!important}

[data-testid="stSidebar"]{background:linear-gradient(180deg,#031D36 0%,#0B2D4B 55%,#123C5D 100%);border-right:1px solid #D7E2EC}
[data-testid="stSidebar"]>div{padding-top:1rem}
[data-testid="stSidebar"] *{color:#F4F8FC}
.sidebar-brand{padding:8px 0 20px;border-bottom:1px solid rgba(255,255,255,.25);margin-bottom:18px}
.sidebar-brand-name{font-size:1.48rem;font-weight:850;letter-spacing:-.7px;color:#FFFFFF}
.sidebar-brand-name span{color:#22C5D5}
.sidebar-brand-sub{font-size:.78rem;color:#C4D3E0;margin-top:4px}
.sidebar-section{font-size:.72rem;font-weight:800;letter-spacing:.9px;color:#B7C9D9;margin:17px 0 8px}
[data-testid="stSidebar"] .stButton>button{width:100%;text-align:left;justify-content:flex-start;background:transparent;color:#F4F8FC;border:1px solid transparent;border-radius:8px;padding:.52rem .68rem;font-size:.88rem;font-weight:600}
[data-testid="stSidebar"] .stButton>button:hover{background:rgba(255,255,255,.12);border-color:rgba(255,255,255,.18);color:#FFFFFF}
[data-testid="stSidebar"] .stButton>button[kind="primary"]{background:linear-gradient(90deg,#0AA6BD,#0794B5);border-color:#27C3D4;color:#FFFFFF}

.utility-item{font-size:1rem;color:#173A59;font-weight:700}
.utility-avatar{background:#0DB7C8;color:#FFFFFF;border-radius:50%;width:30px;height:30px;display:flex;align-items:center;justify-content:center;font-size:.75rem;font-weight:800}
.hero-banner{position:relative;overflow:hidden;background:linear-gradient(90deg,rgba(4,35,65,.98) 0%,rgba(7,49,83,.94) 48%,rgba(8,57,85,.45) 100%),linear-gradient(135deg,#123C5D,#0A2946);padding:22px 26px 22px 28px;margin:0 -1rem 10px;min-height:132px;display:flex;align-items:center;border-left:5px solid #17C2D2}
.hero-banner:after{content:"";position:absolute;inset:0 0 0 42%;background-image:linear-gradient(90deg,rgba(5,35,66,.10),rgba(5,35,66,.04)),url("https://www.acer.europa.eu/sites/default/files/2024-03/ELE_KD_0.jpg");background-size:cover;background-position:center 54%;pointer-events:none}
.hero-banner{min-height:118px;padding:18px 24px;margin:0 calc(-1 * clamp(1rem,2vw,2rem)) 10px;border-left:5px solid #17C2D2;border-radius:0}
.hero-content{max-width:62%;text-shadow:0 1px 2px rgba(0,0,0,.12)}
/* Let Streamlit control sidebar width so the main panel can reclaim space when collapsed. */
[data-testid="stSidebar"] [data-testid="stSidebarContent"]{background:transparent}

@media(max-width:900px){.hero-banner:after{left:30%;opacity:.55}.hero-content{max-width:80%}.hero-title{font-size:1.45rem}.hero-subtitle{font-size:.78rem}}
.hero-content{position:relative;z-index:1}
.hero-title{color:#FFFFFF;font-size:2.05rem;font-weight:850;letter-spacing:-.8px;line-height:1.15}
.hero-subtitle{color:#E1EDF5;font-size:.92rem;margin-top:7px}
.filter-bar{background:#FFFFFF;border:1px solid #DCE6EF;border-radius:13px;padding:10px 14px;margin:0 0 17px;box-shadow:0 2px 10px rgba(22,55,82,.035)}
.filter-heading{font-weight:800;color:#183B59;font-size:.95rem;padding-top:7px}
div[data-testid="stMetric"]{background:#FFFFFF;border:1px solid #DCE6EF;padding:14px 16px;border-radius:13px;box-shadow:0 3px 12px rgba(22,55,82,.045)}
.metric-card{background:#FFFFFF;border:1px solid #DCE6EF;border-radius:13px;padding:13px 12px;min-height:91px;box-shadow:0 3px 12px rgba(22,55,82,.045);display:flex;align-items:center;gap:11px}
.metric-icon{width:46px;height:46px;min-width:46px;border-radius:11px;display:flex;align-items:center;justify-content:center;font-size:1.45rem;background:var(--icon-bg);color:var(--accent)}
.metric-label{font-size:.78rem;color:#526A80;font-weight:650;margin-bottom:4px}
.metric-value{font-size:1.34rem;line-height:1.25;color:#173A59;font-weight:850;white-space:nowrap}
.chart-panel{background:#FFFFFF;border:1px solid #DCE6EF;border-radius:13px;padding:13px 16px 8px;box-shadow:0 3px 12px rgba(22,55,82,.04);height:100%}
.chart-title{font-size:1.12rem;color:#183B59;font-weight:800;padding-bottom:10px;border-bottom:1px solid #E3EBF2;margin-bottom:8px}
h1,h2,h3{color:#183B59;letter-spacing:-.35px}
div[data-testid="stDataFrame"]{border:1px solid #E5EDF4;border-radius:10px}
@media(max-width:1050px){.metric-value{font-size:1.08rem}.hero-title{font-size:1.6rem}.hero-banner:after{width:42%}}
</style>
""", unsafe_allow_html=True)

CATALOG = os.getenv("ENERGY360_CATALOG", "energy")
SCHEMA = os.getenv("ENERGY360_SCHEMA", "energy")

PAGES = [
    "Executive Dashboard", "Energy Generation", "Transmission & Distribution",
    "Energy Consumption", "Property Energy Management", "Asset Management", "Forecasting & Analytics",
    "Sustainability", "Energy Cost & Trading", "Geographical Analysis",
    "Reports & Insights",
]

@st.cache_resource(show_spinner=False)
def data_client():
    return EnergyData(CATALOG, SCHEMA)

@st.cache_data(ttl=180, show_spinner=False)
def table_list():
    return data_client().list_tables()

@st.cache_data(ttl=180, show_spinner=False)
def date_bounds():
    return data_client().date_bounds()

@st.cache_data(ttl=180, show_spinner=False)
def get_dashboard_data(start_date, end_date, state):
    return data_client().dashboard_data(start_date, end_date, state)

@st.cache_data(ttl=180, show_spinner=False)
def get_generation_data(start_date, end_date, state):
    return data_client().generation_data(start_date, end_date, state)

@st.cache_data(ttl=180, show_spinner=False)
def get_consumption_data(start_date, end_date, state):
    return data_client().consumption_data(start_date, end_date, state)

@st.cache_data(ttl=180, show_spinner=False)
def get_grid_data(start_date, end_date, state):
    return data_client().grid_data(start_date, end_date, state)

@st.cache_data(ttl=180, show_spinner=False)
def get_asset_data(start_date, end_date, state):
    return data_client().asset_data(start_date, end_date, state)

@st.cache_data(ttl=180, show_spinner=False)
def get_sustainability_data(start_date, end_date, state):
    return data_client().sustainability_data(start_date, end_date, state)

@st.cache_data(ttl=180, show_spinner=False)
def get_cost_data(start_date, end_date, state):
    return data_client().cost_data(start_date, end_date, state)

@st.cache_data(ttl=180, show_spinner=False)
def get_state_data(start_date, end_date):
    return data_client().state_data(start_date, end_date)


@st.cache_data(ttl=180, show_spinner=False)
def get_property_list():
    return data_client().property_list()

@st.cache_data(ttl=180, show_spinner=False)
def get_property_energy(property_id):
    return data_client().property_energy_data(property_id)

@st.cache_data(ttl=180, show_spinner=False)
def get_property_meters(property_id):
    return data_client().property_meter_data(property_id)

@st.cache_data(ttl=180, show_spinner=False)
def get_property_accounts(property_id):
    return data_client().property_account_data(property_id)

@st.cache_data(ttl=180, show_spinner=False)
def get_property_vendors(property_id):
    return data_client().property_vendor_data(property_id)

@st.cache_data(ttl=180, show_spinner=False)
def get_property_rates(property_id):
    return data_client().property_rate_data(property_id)

@st.cache_data(ttl=180, show_spinner=False)
def get_property_contracts(property_id):
    return data_client().property_contract_data(property_id)

@st.cache_data(ttl=180, show_spinner=False)
def get_property_meter_contracts(property_id):
    return data_client().property_meter_contract_data(property_id)

@st.cache_data(ttl=180, show_spinner=False)
def get_property_bills(property_id):
    return data_client().property_bill_data(property_id)

@st.cache_data(ttl=180, show_spinner=False)
def get_property_procurement(property_id):
    return data_client().property_procurement_data(property_id)

def fmt_k(v, digits=2):
    """Display values >= 1,000 in thousands (K), with two decimals."""
    if v is None or pd.isna(v):
        return "—"
    number = float(v)
    return f"{number / 1000:,.{digits}f}K" if abs(number) >= 1000 else f"{number:,.{digits}f}"

def fmt_num(v, digits=2):
    return fmt_k(v, digits)

def fmt_usd(v):
    if v is None or pd.isna(v):
        return "—"
    number = float(v)
    amount = f"{number / 1000:,.2f}K" if abs(number) >= 1000 else f"{number:,.2f}"
    return "$" + amount

def page_heading(title, subtitle):
    st.title(title)
    st.caption(subtitle)

def metric_row(items):
    cols = st.columns(len(items))
    for col, (label, value, help_text) in zip(cols, items):
        with col:
            st.metric(label, value, help=help_text)

def show_df(df, title, limit=500):
    st.subheader(title)
    if df is None or df.empty:
        st.info("No records match the selected filters.")
        return
    number_formats = {col: fmt_k for col in df.select_dtypes(include=["number"]).columns if col.lower() != "datekey"}
    st.dataframe(df.head(limit).style.format(number_formats, na_rep="—"), use_container_width=True, hide_index=True)
    st.download_button(
        f"Download {title} CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f"energy360_{title.lower().replace(' ','_')}.csv",
        mime="text/csv",
        key=f"download_{title.replace(' ','_')}",
    )

def _choose_page(page_name):
    st.session_state["active_energy_page"] = page_name

def filters():
    groups = [
        ("OVERVIEW", ["Executive Dashboard"]),
        ("OPERATIONS", ["Energy Generation", "Transmission & Distribution", "Energy Consumption", "Property Energy Management", "Asset Management", "Forecasting & Analytics"]),
        ("SUSTAINABILITY & MARKETS", ["Sustainability", "Energy Cost & Trading"]),
        ("INSIGHTS", ["Geographical Analysis", "Reports & Insights"]),
    ]
    if "active_energy_page" not in st.session_state:
        st.session_state["active_energy_page"] = "Executive Dashboard"

    with st.sidebar:
        st.markdown("""
        <div class="sidebar-brand">
          <div class="sidebar-brand-name">⚡ ENERGY <span>360</span></div>
          <div class="sidebar-brand-sub">Enterprise Energy Analytics</div>
        </div>
        """, unsafe_allow_html=True)
        for group_name, pages in groups:
            st.markdown(f'<div class="sidebar-section">{group_name}</div>', unsafe_allow_html=True)
            for page_name in pages:
                icon = {
                    "Executive Dashboard":"◉", "Energy Generation":"▥",
                    "Transmission & Distribution":"⚡", "Energy Consumption":"♧",
                    "Property Energy Management":"⌂", "Asset Management":"⚙", "Forecasting & Analytics":"⌁",
                    "Sustainability":"❧", "Energy Cost & Trading":"▤",
                    "Geographical Analysis":"⌖", "Reports & Insights":"▣",
                }.get(page_name, "•")
                st.button(
                    f"{icon}   {page_name}",
                    key=f"nav_{page_name}",
                    type="primary" if st.session_state["active_energy_page"] == page_name else "secondary",
                    on_click=_choose_page,
                    args=(page_name,),
                )
        st.divider()
        st.caption(f"Catalog: {CATALOG}")
        st.caption(f"Schema: {SCHEMA}")
    return st.session_state["active_energy_page"]

def render_utility_bar():
    st.markdown("""
    <div class="utility-bar">
      <span class="utility-item">♧</span>
      <span class="utility-item">ⓘ</span>
      <span class="utility-avatar">PB</span>
      <span class="utility-item">⌄</span>
    </div>
    """, unsafe_allow_html=True)

def render_hero(page):
    page_subtitles = {
        "Executive Dashboard": "United States energy generation, consumption, grid, asset and sustainability performance.",
        "Energy Generation": "Monitor power generation, plant output and energy-source performance across the United States.",
        "Transmission & Distribution": "Track grid performance, transmission reliability and distribution availability across the United States.",
        "Energy Consumption": "Analyze energy demand, consumption patterns and usage trends across the United States.",
        "Property Energy Management": "Explore property-level energy usage, meters, utility accounts, suppliers, rates, contracts and procurement.",
        "Asset Management": "Monitor energy assets, operational health, performance and maintenance indicators.",
        "Forecasting & Analytics": "Explore energy trends, historical performance and analytical insights for better planning.",
        "Sustainability": "Track carbon emissions, clean energy contribution and sustainability performance.",
        "Energy Cost & Trading": "Review energy costs, revenue and trading performance in US dollars.",
        "Geographical Analysis": "Explore energy generation and infrastructure performance across US states.",
        "Reports & Insights": "Review energy performance summaries, detailed records and business insights.",
    }
    subtitle = page_subtitles.get(page, page_subtitles["Executive Dashboard"])
    st.markdown(
        f'<div class="hero-banner"><div class="hero-content">'
        f'<div class="hero-title">{page}</div>'
        f'<div class="hero-subtitle">{subtitle}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def format_plotly_numbers(fig):
    """Display chart axes and color scales in thousands (K)."""
    def _axis_ticks(values):
        arr = np.asarray(values, dtype=float).ravel()
        arr = arr[np.isfinite(arr)]
        if arr.size == 0:
            return None, None
        low, high = float(arr.min()), float(arr.max())
        ticks = np.array([low]) if low == high else np.linspace(low, high, 5)
        labels = [
            f"{value / 1000:,.2f}K" if abs(value) >= 1000 else f"{value:,.2f}"
            for value in ticks
        ]
        return ticks.tolist(), labels

    for axis_name, attr in (("xaxis", "x"), ("yaxis", "y")):
        values = []
        for trace in fig.data:
            raw = getattr(trace, attr, None)
            if raw is not None:
                try:
                    values.extend(np.asarray(raw, dtype=float).ravel().tolist())
                except (TypeError, ValueError):
                    pass
        tickvals, ticktext = _axis_ticks(values)
        if tickvals:
            fig.update_layout(**{axis_name: dict(tickmode="array", tickvals=tickvals, ticktext=ticktext)})

    for trace in fig.data:
        if getattr(trace, "marker", None) is not None:
            try:
                raw_color = trace.marker.color
                if raw_color is not None and not isinstance(raw_color, str):
                    tickvals, ticktext = _axis_ticks(raw_color)
                    if tickvals:
                        trace.marker.colorbar = dict(tickmode="array", tickvals=tickvals, ticktext=ticktext)
            except (TypeError, ValueError, AttributeError):
                pass
        template = getattr(trace, "hovertemplate", None)
        if isinstance(template, str):
            trace.hovertemplate = template.replace("%{y}", "%{y:,.2f}").replace(
                "%{z}", "%{z:,.2f}"
            ).replace("%{marker.color}", "%{marker.color:,.2f}").replace(
                "%{value}", "%{value:,.2f}"
            )
        if getattr(trace, "type", None) == "pie":
            trace.texttemplate = "%{percent:.2%}"
    return fig
    for trace in fig.data:
        if getattr(trace, "marker", None) is not None:
            try:
                trace.marker.colorbar = dict(
                    tickformat=",.2f", exponentformat="none", showexponent="none"
                )
            except (ValueError, AttributeError):
                pass
        template = getattr(trace, "hovertemplate", None)
        if isinstance(template, str):
            template = template.replace("%{y}", "%{y:,.2f}")
            template = template.replace("%{z}", "%{z:,.2f}")
            template = template.replace("%{marker.color}", "%{marker.color:,.2f}")
            template = template.replace("%{value}", "%{value:,.2f}")
            trace.hovertemplate = template
        if getattr(trace, "type", None) == "pie":
            trace.texttemplate = "%{percent:.2%}"
    return fig


def plotly_drilldown(fig, detail_df, key, detail_title, detail_column=None):
    """Clickable Plotly selection with matching underlying rows and CSV export."""
    format_plotly_numbers(fig)
    if detail_df is None or detail_df.empty:
        st.plotly_chart(fig, use_container_width=True, key=key)
        return
    try:
        event = st.plotly_chart(fig, use_container_width=True, key=key,
                                on_select="rerun", selection_mode="points")
        points = event.selection.points if event and hasattr(event, "selection") else []
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, key=key)
        st.caption("Chart drill-through requires Streamlit 1.40 or newer.")
        return
    selected = []
    for point in points:
        custom = point.get("customdata")
        if hasattr(custom, "tolist"):
            custom = custom.tolist()
        value = custom[0] if isinstance(custom, (list, tuple)) and custom else custom
        if value is not None:
            selected.append(str(value))
    if selected and detail_column and detail_column in detail_df.columns:
        matched = detail_df[detail_df[detail_column].astype(str).isin(set(selected))]
        with st.expander(f"Drill-through: {detail_title} ({len(matched):,} records)", expanded=True):
            float_formats = {col: "{:,.2f}" for col in matched.select_dtypes(include=["number"]).columns}
            st.dataframe(matched.style.format(float_formats, na_rep="—"), use_container_width=True, hide_index=True)
            st.download_button(f"Download {detail_title} detail",
                matched.to_csv(index=False).encode("utf-8"),
                file_name=f"energy360_{key}_detail.csv", mime="text/csv",
                key=f"{key}_download")
    else:
        st.caption("Select a point, bar or chart segment to view its underlying records.")


def render_filter_bar():
    try:
        min_d, max_d = date_bounds()
    except Exception:
        min_d, max_d = None, None
    try:
        states = data_client().state_names()
    except Exception:
        states = []

    if "energy_date_range" not in st.session_state and min_d and max_d:
        st.session_state["energy_date_range"] = (min_d, max_d)
    if "energy_state_filter" not in st.session_state:
        st.session_state["energy_state_filter"] = "All US"

    st.markdown('<div class="filter-bar">', unsafe_allow_html=True)
    cols = st.columns([1.35, 1.9, 1.35, 1.45, .45])
    with cols[0]:
        st.markdown('<div class="filter-heading">⚲ &nbsp; Dashboard filters</div>', unsafe_allow_html=True)
    with cols[1]:
        st.caption("Date range")
        if min_d and max_d:
            selected_range = st.date_input(
                "Date range",
                value=st.session_state["energy_date_range"],
                min_value=min_d,
                max_value=max_d,
                label_visibility="collapsed",
                key="energy_date_picker",
            )
            if isinstance(selected_range, (tuple, list)) and len(selected_range) == 2:
                start_d, end_d = selected_range
            else:
                start_d, end_d = min_d, max_d
        else:
            start_d, end_d = None, None
            st.caption("Date range unavailable")
    with cols[2]:
        st.caption("State")
        state = st.selectbox(
            "State",
            ["All US"] + states,
            index=(["All US"] + states).index(st.session_state["energy_state_filter"])
                if st.session_state["energy_state_filter"] in (["All US"] + states) else 0,
            label_visibility="collapsed",
            key="energy_state_picker",
        )
    with cols[3]:
        st.caption("Apply filters")
        if st.button("⌕  Apply Filters", type="primary", use_container_width=True):
            st.session_state["energy_date_range"] = (start_d, end_d) if start_d and end_d else None
            st.session_state["energy_state_filter"] = state
            st.rerun()
    with cols[4]:
        st.caption(" ")
        if st.button("↻", help="Refresh data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    applied_range = st.session_state.get("energy_date_range")
    if applied_range and len(applied_range) == 2:
        start_d, end_d = applied_range
    applied_state = st.session_state.get("energy_state_filter", "All US")
    return start_d, end_d, applied_state

def render_dashboard(start_d, end_d, state):
    data = get_dashboard_data(start_d, end_d, state)
    gen, cons, grid, plants, emissions, costs = (data[k] for k in ["generation","consumption","grid","capacity","emissions","costs"])

    generated = float(gen["generation_mwh"].sum()) if not gen.empty else None
    consumed = float(cons["consumption_mwh"].sum()) if not cons.empty else None
    availability = float(grid["gridavailabilitypct"].mean()) if not grid.empty else None
    capacity = float(plants["installedcapacitymw"].sum()) if not plants.empty else None
    co2 = float(emissions["emissions_tco2e"].sum()) if not emissions.empty else None
    cost = float(costs["totalcost_inr"].sum()) if not costs.empty else None

    cards = [
        ("⚡", "Energy Generated", f"{generated/1000:,.2f} GWh" if generated is not None else "—", "#16A66A", "#E5F8EE"),
        ("♧", "Energy Consumed", f"{consumed/1000:,.2f} GWh" if consumed is not None else "—", "#1976D2", "#E6F2FF"),
        ("▱", "Grid Availability", f"{availability:,.2f}%" if availability is not None else "—", "#8B5CF6", "#F1EAFE"),
        ("⚡", "Installed Capacity", f"{capacity/1000:,.2f} GW" if capacity is not None else "—", "#E69A19", "#FFF3DD"),
        ("🍃", "Carbon Emissions", f"{co2:,.2f} tCO₂e" if co2 is not None else "—", "#20A45B", "#E7F8EC"),
        ("▤", "Energy Cost", fmt_usd(cost), "#168ACB", "#E4F5FC"),
    ]
    for row_start in (0, 3):
        card_cols = st.columns(3, gap="medium")
        for col, (icon, label, value, accent, icon_bg) in zip(card_cols, cards[row_start:row_start+3]):
            with col:
                st.markdown(
                    f'<div class="metric-card" style="--accent:{accent};--icon-bg:{icon_bg}">'
                    f'<div class="metric-icon">{icon}</div>'
                    f'<div><div class="metric-label">{label} &nbsp; ⓘ</div>'
                    f'<div class="metric-value">{value}</div></div></div>',
                    unsafe_allow_html=True,
                )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns([1.08, 1])
    with c1:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        st.markdown('<div class="chart-title">↗ &nbsp; Generation vs consumption</div>', unsafe_allow_html=True)
        trend = data["trend"]
        if not trend.empty:
            long = trend.melt(id_vars="date", value_vars=["generation_mwh","consumption_mwh"], var_name="metric", value_name="mwh")
            long["drill_date"] = long["date"].astype(str)
            long["metric"] = long["metric"].map({"generation_mwh":"Generation","consumption_mwh":"Consumption"})
            fig = px.line(
                long, x="date", y="mwh", color="metric", markers=True, custom_data=["drill_date"],
                color_discrete_map={"Generation":"#1976D2","Consumption":"#25A55B"},
            )
            fig.update_traces(line_width=2.5, marker_size=6)
            fig.update_layout(
                height=340, margin=dict(l=5,r=5,t=12,b=5), plot_bgcolor="white", paper_bgcolor="white",
                legend_title="", legend=dict(orientation="h",y=-.18,x=.25),
                hovermode="x unified",
            )
            fig.update_xaxes(showgrid=False,zeroline=False)
            fig.update_yaxes(gridcolor="#E7EEF4",zeroline=False,title="Energy (MWh)")
            drill = pd.concat([data["generation"].assign(drill_date=data["generation"]["date"].astype(str)), data["consumption"].assign(drill_date=data["consumption"]["date"].astype(str))], ignore_index=True, sort=False)
            plotly_drilldown(fig, drill, "dash_generation_consumption", "generation and consumption by date", "drill_date")
        else:
            st.info("No generation/consumption trend rows for this filter.")
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        st.markdown('<div class="chart-title">◉ &nbsp; Generation by energy source</div>', unsafe_allow_html=True)
        by_source = data["by_source"].copy()
        if not by_source.empty:
            total_source = float(by_source["generation_mwh"].sum())
            by_source["share_pct"] = (by_source["generation_mwh"] / total_source * 100) if total_source else 0
            pie_col, table_col = st.columns([.95, 1.15])
            with pie_col:
                fig = px.pie(
                    by_source,names="energysource",values="generation_mwh",hole=.58,custom_data=["energysource"],
                    color_discrete_sequence=["#1976D2","#25A55B","#F3B53F","#8A55D8","#14B8C4","#9AA8B5"],
                )
                fig.update_traces(textposition="inside",textinfo="percent",hole=.58)
                fig.update_layout(height=330,margin=dict(l=0,r=0,t=8,b=0),showlegend=False,paper_bgcolor="white")
                plotly_drilldown(fig, data["generation"], "dash_source_mix", "generation by energy source", "energysource")
            with table_col:
                display_source = by_source[["energysource","generation_mwh","share_pct"]].copy()
                display_source["generation_mwh"] = display_source["generation_mwh"].map(lambda x: f"{x/1000:,.2f}")
                display_source["share_pct"] = display_source["share_pct"].map(lambda x: f"{x:.2f}%")
                display_source.columns = ["Energy Source","Generation (GWh)","Share"]
                st.dataframe(display_source,use_container_width=True,hide_index=True,height=300)
        else:
            st.info("No source-wise generation data available.")
        st.markdown('</div>', unsafe_allow_html=True)

    c3, c4 = st.columns([1, 1])
    with c3:
        st.subheader("State-wise generation")
        states = data["by_state"]
        if not states.empty and {"latitude","longitude"}.issubset(states.columns):
            # Display generation in millions so 13,951,403.2 is shown as 13.95,
            # rather than Plotly's automatically abbreviated 13.9514032M.
            states = states.copy()
            states["generation_millions"] = states["generation_mwh"] / 1_000_000
            fig = px.scatter_geo(
                states, lat="latitude", lon="longitude", size="generation_mwh",
                color="generation_millions", hover_name="statename",
                hover_data={
                    "generation_millions":":.2f",
                    "generation_mwh":False,
                    "latitude":False,
                    "longitude":False,
                },
                custom_data=["statekey"],
                scope="usa", color_continuous_scale=["#BFE7D0","#1976D2"],
                labels={"generation_millions":"Generation (millions)"},
            )
            fig.update_traces(
                marker_colorbar=dict(
                    title="Generation (millions)",
                    tickformat=".2f",
                    exponentformat="none",
                    showexponent="none",
                )
            )
            fig.update_geos(fitbounds="locations",visible=False,showland=True,landcolor="#F2F7FB",
                            showcountries=True,countrycolor="#CBD8E5",showocean=True,oceancolor="#FFFFFF")
            fig.update_layout(height=360,margin=dict(l=0,r=0,t=0,b=0),paper_bgcolor="white")
            plotly_drilldown(fig, data["generation"], "dash_state_generation", "state generation", "statekey")
        else:
            st.info("State map requires coordinates in dim_state and matching state keys in generation.")
    with c4:
        st.subheader("Grid performance by state")
        if not data["grid_by_state"].empty:
            fig = px.bar(data["grid_by_state"],x="statename",y="gridavailabilitypct",custom_data=["statename"],
                         color="gridavailabilitypct",color_continuous_scale=["#F3B53F","#25A55B"])
            fig.update_layout(height=360,margin=dict(l=5,r=5,t=10,b=5),xaxis_title="",yaxis_title="Availability (%)",coloraxis_showscale=False)
            plotly_drilldown(fig, data["grid"], "dash_grid_state", "grid performance by state", "statename")
        else:
            st.info("No state-wise grid records available.")

    st.divider()
    show_df(data["recent_generation"],"Recent generation records",100)

def render_generation(start_d,end_d,state):
    page_heading("Energy Generation","Plant-level output, energy source mix, capacity utilization and target performance.")
    df = get_generation_data(start_d,end_d,state)
    if df.empty:
        st.info("No generation records for the selected filters."); return
    total = df["generation_mwh"].sum()
    target = df["targetgeneration_mwh"].sum()
    util = df["capacityutilizationpct"].mean()
    curtail = df["curtailment_mwh"].sum()
    metric_row([("Generated",f"{total/1000:,.2f} GWh",None),("Target",f"{target/1000:,.2f} GWh",None),
                ("Capacity Utilization",f"{util:,.2f}%",None),("Curtailment",f"{curtail:,.2f} MWh",None)])
    a,b = st.columns(2)
    with a:
        agg=df.groupby("energysource",as_index=False)["generation_mwh"].sum()
        fig=px.bar(agg,x="energysource",y="generation_mwh",color="energysource",custom_data=["energysource"],title="Generation by source")
        plotly_drilldown(fig,df,"gen_source_detail","generation by source","energysource")
    with b:
        trend=df.groupby("date",as_index=False)[["generation_mwh","targetgeneration_mwh"]].sum()
        trend["drill_date"]=trend["date"].astype(str)
        fig=px.line(trend,x="date",y=["generation_mwh","targetgeneration_mwh"],markers=True,custom_data=["drill_date"],title="Actual vs target")
        df["drill_date"]=df["date"].astype(str)
        plotly_drilldown(fig,df,"gen_actual_target","generation by date","drill_date")
    show_df(df,"Generation detail")

def render_consumption(start_d,end_d,state):
    page_heading("Energy Consumption","Analyze electricity consumption by sector, state and reporting date.")
    df=get_consumption_data(start_d,end_d,state)
    if df.empty:
        st.info("No consumption records for the selected filters."); return
    total=df["consumption_mwh"].sum()
    target=df["targetconsumption_mwh"].sum()
    peak=df["peakdemandmw"].max()
    variance=df["variancepct"].mean()
    metric_row([("Consumption",f"{total/1000:,.2f} GWh",None),("Target",f"{target/1000:,.2f} GWh",None),
                ("Peak Demand",f"{peak:,.2f} MW",None),("Average Variance",f"{variance:,.2f}%",None)])
    a,b=st.columns(2)
    with a:
        sector=df.groupby("consumersector",as_index=False)["consumption_mwh"].sum()
        fig=px.pie(sector,names="consumersector",values="consumption_mwh",hole=.55,custom_data=["consumersector"],title="Consumption by sector")
        plotly_drilldown(fig,df,"cons_sector_detail","consumption by sector","consumersector")
    with b:
        trend=df.groupby("date",as_index=False)["consumption_mwh"].sum()
        trend["drill_date"]=trend["date"].astype(str)
        fig=px.line(trend,x="date",y="consumption_mwh",markers=True,custom_data=["drill_date"],title="Consumption trend")
        df["drill_date"]=df["date"].astype(str)
        plotly_drilldown(fig,df,"cons_trend_detail","consumption by date","drill_date")
    show_df(df,"Consumption detail")

def render_grid(start_d,end_d,state):
    page_heading("Transmission & Distribution","Grid availability, transmission losses, outages, SAIDI and peak load factor.")
    df=get_grid_data(start_d,end_d,state)
    if df.empty:
        st.info("No grid records for the selected filters."); return
    metric_row([("Grid Availability",f"{df.gridavailabilitypct.mean():.2f}%",None),
                ("Transmission Loss",f"{df.transmissionlosspct.mean():.2f}%",None),
                ("Outages",f"{df.outagecount.sum():,.2f}",None),
                ("SAIDI",f"{df.saidi_hours.mean():.2f} hours",None)])
    a,b=st.columns(2)
    with a:
        trend=df.groupby("date",as_index=False)["gridavailabilitypct"].mean(); trend["drill_date"]=trend["date"].astype(str)
        fig=px.line(trend,x="date",y="gridavailabilitypct",markers=True,custom_data=["drill_date"],title="Grid availability trend")
        df["drill_date"]=df["date"].astype(str)
        plotly_drilldown(fig,df,"grid_trend_detail","grid performance by date","drill_date")
    with b:
        state_loss=df.groupby("statename",as_index=False)["transmissionlosspct"].mean()
        fig=px.bar(state_loss,x="statename",y="transmissionlosspct",custom_data=["statename"],title="Average transmission loss by state")
        plotly_drilldown(fig,df,"grid_state_detail","grid records by state","statename")
    show_df(df,"Grid performance detail")

def render_assets(start_d,end_d,state):
    page_heading("Asset Management","Asset availability, health score, downtime, maintenance and operational status.")
    df=get_asset_data(start_d,end_d,state)
    if df.empty:
        st.info("No asset performance records for the selected filters."); return
    metric_row([("Average Availability",f"{df.availabilitypct.mean():.2f}%",None),
                ("Average Health Score",f"{df.assethealthscore.mean():.2f}",None),
                ("Downtime",f"{df.downtimehours.sum():,.2f} hours",None),
                ("Maintenance Events",f"{df.maintenanceevents.sum():,.2f}",None)])
    a,b=st.columns(2)
    with a:
        asset_health=df.groupby("assetname",as_index=False)["assethealthscore"].mean()
        fig=px.bar(asset_health,x="assetname",y="assethealthscore",color="assethealthscore",custom_data=["assetname"],title="Asset health score")
        plotly_drilldown(fig,df,"asset_health_detail","asset performance","assetname")
    with b:
        status=df.groupby("operationalstatus",as_index=False).size()
        fig=px.pie(status,names="operationalstatus",values="size",hole=.55,custom_data=["operationalstatus"],title="Operational status")
        plotly_drilldown(fig,df,"asset_status_detail","asset operational status","operationalstatus")
    show_df(df,"Asset performance detail")

def render_sustainability(start_d,end_d,state):
    page_heading("Sustainability","Carbon emissions, emission factors and carbon reduction targets.")
    df=get_sustainability_data(start_d,end_d,state)
    if df.empty:
        st.info("No carbon emissions records for the selected filters."); return
    metric_row([("Emissions",f"{df.emissions_tco2e.sum():,.2f} tCO₂e",None),
                ("Energy Generated",f"{df.energygenerated_mwh.sum():,.2f} MWh",None),
                ("Avg Emission Factor",f"{df.emissionfactor_tco2e_per_mwh.mean():.2f} tCO₂e/MWh",None),
                ("Carbon Reduction Target",f"{df.carbonreductiontargetpct.mean():.2f}%",None)])
    a,b=st.columns(2)
    with a:
        em_source=df.groupby("energysource",as_index=False)["emissions_tco2e"].sum()
        fig=px.bar(em_source,x="energysource",y="emissions_tco2e",color="energysource",custom_data=["energysource"],title="Emissions by energy source")
        plotly_drilldown(fig,df,"em_source_detail","emissions by energy source","energysource")
    with b:
        trend=df.groupby("date",as_index=False)["emissions_tco2e"].sum()
        trend["drill_date"]=trend["date"].astype(str)
        fig=px.line(trend,x="date",y="emissions_tco2e",markers=True,custom_data=["drill_date"],title="Emissions trend")
        df["drill_date"]=df["date"].astype(str)
        plotly_drilldown(fig,df,"em_trend_detail","emissions by date","drill_date")
    show_df(df,"Emissions detail")

def render_costs(start_d,end_d,state):
    page_heading("Energy Cost & Trading","Energy purchases, unit costs, revenue and gross margin in US Dollars.")
    df=get_cost_data(start_d,end_d,state)
    if df.empty:
        st.info("No energy cost records for the selected filters."); return
    metric_row([("Purchased Energy",f"{df.energypurchased_mwh.sum():,.2f} MWh",None),
                ("Total Cost",fmt_usd(df.totalcost_inr.sum()),None),
                ("Revenue",fmt_usd(df.revenue_inr.sum()),None),
                ("Gross Margin",fmt_usd(df.grossmargin_inr.sum()),None)])
    a,b=st.columns(2)
    with a:
        cost_source=df.groupby("energysource",as_index=False)["totalcost_inr"].sum()
        fig=px.bar(cost_source,x="energysource",y="totalcost_inr",color="energysource",custom_data=["energysource"],title="Cost by source")
        plotly_drilldown(fig,df,"cost_source_detail","energy cost by source","energysource")
    with b:
        cost_trend=df.groupby("date",as_index=False)[["totalcost_inr","revenue_inr"]].sum(); cost_trend["drill_date"]=cost_trend["date"].astype(str)
        fig=px.line(cost_trend,x="date",y=["totalcost_inr","revenue_inr"],markers=True,custom_data=["drill_date"],title="Cost vs revenue")
        df["drill_date"]=df["date"].astype(str)
        plotly_drilldown(fig,df,"cost_trend_detail","energy cost by date","drill_date")
    show_df(df,"Energy cost detail")

def render_geography(start_d,end_d):
    page_heading("Geographical Analysis","State-level energy generation, consumption, grid and location coordinates.")
    df=get_state_data(start_d,end_d)
    if df.empty:
        st.info("No state dimension records found."); return
    if {"latitude","longitude"}.issubset(df.columns):
        fig=px.scatter_geo(df,lat="latitude",lon="longitude",hover_name="statename",
                           size="generation_mwh",color="region",scope="usa",
                           hover_data=["generation_mwh","consumption_mwh","gridavailabilitypct"])
        fig.update_geos(fitbounds="locations",visible=False,showland=True,landcolor="#F2F7FB")
        fig.update_layout(height=520,margin=dict(l=0,r=0,t=10,b=0))
        plotly_drilldown(fig,df,"geo_state_detail","state energy summary","statekey")
    show_df(df,"State-wise energy summary")

def render_forecasting(start_d,end_d,state):
    page_heading("Forecasting & Analytics","Forecast-ready actual energy trends using your current source tables.")
    st.info("Your supplied schema does not include a forecast fact table or prediction columns. This page currently displays historical actuals; a Databricks ML forecast can be added when you approve a forecast table/model.")
    df=get_generation_data(start_d,end_d,state)
    if not df.empty:
        trend=df.groupby("date",as_index=False)["generation_mwh"].sum()
        trend["drill_date"]=trend["date"].astype(str)
        fig=px.line(trend,x="date",y="generation_mwh",markers=True,custom_data=["drill_date"],title="Historical generation (actuals only)")
        df["drill_date"]=df["date"].astype(str)
        plotly_drilldown(fig,df,"forecast_actual_detail","historical generation by date","drill_date")
        show_df(df,"Generation history")

def render_reports(start_d,end_d,state):
    page_heading("Reports & Insights","Download filtered data from the Energy 360 business tables.")
    report=st.selectbox("Select report",["Generation","Consumption","Grid Performance","Asset Performance","Carbon Emissions","Energy Cost"])
    loaders={
        "Generation":get_generation_data,"Consumption":get_consumption_data,
        "Grid Performance":get_grid_data,"Asset Performance":get_asset_data,
        "Carbon Emissions":get_sustainability_data,"Energy Cost":get_cost_data
    }
    df=loaders[report](start_d,end_d,state)
    show_df(df,f"{report} report",10000)

def render_property_energy_management():
    page_heading(
        "Property Energy Management",
        "Property-level energy usage, meters, utility accounts, suppliers, rate details, contracts and procurement.",
    )
    try:
        properties = get_property_list()
    except DataAccessError as exc:
        st.error("Could not load the property master. Confirm that the property SQL script has been deployed.")
        st.code(str(exc))
        return

    if properties.empty:
        st.warning("No properties were found in dim_property.")
        return

    property_ids = properties["property_id"].astype(str).tolist()

    def property_label(pid):
        row = properties.loc[properties["property_id"].astype(str) == str(pid)].iloc[0]
        city_state = ", ".join(
            str(value) for value in [row.get("city"), row.get("state_code")]
            if pd.notna(value) and str(value).strip()
        )
        return f"{row.get('property_name', pid)} | {city_state} | {pid}"

    default_id = st.session_state.get("selected_energy_property", property_ids[0])
    if default_id not in property_ids:
        default_id = property_ids[0]
    selected_id = st.selectbox(
        "Select property", property_ids, index=property_ids.index(default_id),
        format_func=property_label, key="property_energy_selector",
    )
    st.session_state["selected_energy_property"] = selected_id
    prop = properties.loc[properties["property_id"].astype(str) == selected_id].iloc[0]

    try:
        energy = get_property_energy(selected_id)
        meters = get_property_meters(selected_id)
        accounts = get_property_accounts(selected_id)
        vendors = get_property_vendors(selected_id)
        rates = get_property_rates(selected_id)
        contracts = get_property_contracts(selected_id)
        bills = get_property_bills(selected_id)
        procurement = get_property_procurement(selected_id)
    except DataAccessError as exc:
        st.error("Could not load this property's related records.")
        st.code(str(exc))
        return

    try:
        meter_contracts = get_property_meter_contracts(selected_id)
    except DataAccessError as exc:
        meter_contracts = pd.DataFrame()
        st.warning("Meter-level contract duration is not available yet. Run the contract duration migration SQL script, then refresh the app.")
        st.caption(str(exc))

    area = prop.get("gross_area_sqft")
    area_text = f"{float(area):,.2f} gross sq. ft." if pd.notna(area) else "Area not provided"
    st.markdown(
        f"**{prop.get('property_type') or 'Property'}** · "
        f"{prop.get('address_line_1') or ''} · "
        f"{prop.get('city') or ''}, {prop.get('state_code') or ''} "
        f"{prop.get('postal_code') or ''} · {area_text}"
    )
    st.caption(
        f"Property ID: {selected_id} | Status: {prop.get('operating_status') or 'Not specified'} | "
        f"Manager: {prop.get('property_manager') or 'Not assigned'}"
    )

    total_cost = float(energy["cost_amount"].fillna(0).sum()) if not energy.empty else 0.0
    meter_count = int(meters["meter_id"].nunique()) if not meters.empty else 0
    account_count = int(accounts["utility_account_id"].nunique()) if not accounts.empty else 0
    contract_count = int(contracts["contract_id"].nunique()) if not contracts.empty else 0
    metric_row([
        ("Energy Cost", fmt_usd(total_cost), "Sum of recorded property energy costs."),
        ("Meters", f"{meter_count:,.2f}", None),
        ("Utility Accounts", f"{account_count:,.2f}", None),
        ("Supplier Contracts", f"{contract_count:,.2f}", None),
    ])

    st.subheader("Commodity consumption")
    if energy.empty:
        st.info("No energy usage records exist for this property.")
    else:
        totals = (
            energy.groupby(["commodity_name", "usage_unit"], dropna=False, as_index=False)
            .agg(total_usage=("usage_quantity", "sum"),
                 total_cost=("cost_amount", "sum"),
                 records=("property_energy_usage_id", "count"))
        )
        cols = st.columns(max(1, min(3, len(totals))))
        for col, (_, row) in zip(cols, totals.iterrows()):
            with col:
                st.metric(
                    f"{row['commodity_name']} ({row['usage_unit']})",
                    fmt_num(row["total_usage"], 2),
                    help=f"{int(row['records']):,.2f} usage records | {fmt_usd(row['total_cost'])}",
                )

        left, right = st.columns([1.35, 1])
        with left:
            st.markdown("**Monthly consumption trend**")
            commodities = totals["commodity_name"].dropna().astype(str).tolist()
            chosen = st.selectbox(
                "Commodity for trend", commodities,
                key=f"property_commodity_trend_{selected_id}",
            )
            selected_energy = energy[energy["commodity_name"] == chosen].copy()
            trend = (
                selected_energy.groupby("period_start_date", as_index=False)["usage_quantity"]
                .sum().sort_values("period_start_date")
            )
            if not trend.empty:
                unit_values = selected_energy["usage_unit"].dropna()
                unit = str(unit_values.iloc[0]) if not unit_values.empty else ""
                fig = px.line(
                    trend, x="period_start_date", y="usage_quantity", markers=True,
                    title=f"{chosen} usage ({unit})",
                )
                fig.update_traces(line_color="#0878D1", line_width=3, marker_size=7)
                fig.update_layout(
                    height=330, margin=dict(l=10, r=10, t=45, b=10),
                    paper_bgcolor="white", plot_bgcolor="white",
                )
                fig.update_yaxes(title=unit, gridcolor="#E7EEF4")
                fig.update_xaxes(title="")
                fig.update_yaxes(tickformat=",.2f")
                st.plotly_chart(format_plotly_numbers(fig), use_container_width=True, key=f"property_usage_{selected_id}")
        with right:
            st.markdown("**Energy cost by commodity**")
            cost_data = totals[["commodity_name", "total_cost"]].copy()
            fig = px.bar(cost_data, x="commodity_name", y="total_cost",
                         color="commodity_name", title="Cost (USD)")
            fig.update_layout(
                showlegend=False, height=330, margin=dict(l=10, r=10, t=45, b=10),
                paper_bgcolor="white", plot_bgcolor="white",
            )
            fig.update_yaxes(title="USD", tickprefix="$", gridcolor="#E7EEF4")
            fig.update_xaxes(title="")
            fig.update_yaxes(tickformat=",.2f")
            st.plotly_chart(format_plotly_numbers(fig), use_container_width=True, key=f"property_cost_{selected_id}")

    st.subheader("Property operations")
    tabs = st.tabs([
        "Meters & Readings", "Meter Contracts", "Utility Accounts", "Vendors",
        "Rate Details", "Property Contracts", "Bills", "Procurement",
    ])
    tab_data = [
        (meters, "Meter inventory"),
        (meter_contracts, "Meter-level contract duration"),
        (accounts, "Utility accounts"),
        (vendors, "Vendors and suppliers"),
        (rates, "Rate schedules and components"),
        (contracts, "Property-level supplier contracts"),
        (bills, "Utility bills"),
        (procurement, "Purchase orders, invoices and payments"),
    ]
    for tab, (frame, title) in zip(tabs, tab_data):
        with tab:
            if frame is None or frame.empty:
                st.info(f"No {title.lower()} records are linked to this property.")
            else:
                number_formats = {col: fmt_k for col in frame.select_dtypes(include=["number"]).columns if col.lower() != "datekey"}
                st.dataframe(frame.style.format(number_formats, na_rep="—"), use_container_width=True, hide_index=True)
                st.download_button(
                    f"Download {title} CSV",
                    frame.to_csv(index=False).encode("utf-8"),
                    file_name=f"energy360_{selected_id}_{title.lower().replace(' ', '_')}.csv",
                    mime="text/csv",
                    key=f"property_download_{selected_id}_{title.replace(' ', '_')}",
                )

    with st.expander("Property energy usage records"):
        show_df(energy, "Property energy usage", 10000)


# ------------------------- App entry -------------------------
try:
    with st.spinner("Connecting to Databricks SQL Warehouse..."):
        available=table_list()
    expected = {
        "dim_asset","dim_date","dim_energy_source","dim_power_plant","dim_state",
        "fact_asset_performance","fact_carbon_emissions","fact_consumption",
        "fact_energy_cost","fact_generation","fact_grid_performance"
    }
    missing=sorted(expected-set(available))
    if missing:
        st.warning("Expected tables not found in configured schema: "+", ".join(missing))
    page=filters()
    render_hero(page)
    # Global filter pane removed: use the full available date range and all US states.
    try:
        start_d, end_d = date_bounds()
    except Exception:
        start_d, end_d = None, None
    state = "All US"
    if page=="Executive Dashboard": render_dashboard(start_d,end_d,state)
    elif page=="Energy Generation": render_generation(start_d,end_d,state)
    elif page=="Transmission & Distribution": render_grid(start_d,end_d,state)
    elif page=="Energy Consumption": render_consumption(start_d,end_d,state)
    elif page=="Property Energy Management": render_property_energy_management()
    elif page=="Asset Management": render_assets(start_d,end_d,state)
    elif page=="Forecasting & Analytics": render_forecasting(start_d,end_d,state)
    elif page=="Sustainability": render_sustainability(start_d,end_d,state)
    elif page=="Energy Cost & Trading": render_costs(start_d,end_d,state)
    elif page=="Geographical Analysis": render_geography(start_d,end_d)
    elif page=="Reports & Insights": render_reports(start_d,end_d,state)
    with st.expander("Data source diagnostics"):
        st.write(f"Catalog: `{CATALOG}` | Schema: `{SCHEMA}`")
        st.write("Tables discovered:", ", ".join(available))
        st.caption("All measures are calculated from your existing Unity Catalog fact and dimension tables. Configure the tables with US state, plant and USD-denominated sample records.")
except DataAccessError as e:
    st.error("Could not connect to your Energy 360 data.")
    st.code(str(e))
    st.markdown("""
Check:
1. App Resources includes a SQL Warehouse.
2. App service principal has `USE CATALOG`, `USE SCHEMA`, and `SELECT` grants.
3. `ENERGY360_CATALOG` and `ENERGY360_SCHEMA` match the actual Unity Catalog location.
4. The warehouse is running and the app has permission to use it.
""")
except Exception as e:
    st.error("An unexpected application error occurred.")
    st.exception(e)
