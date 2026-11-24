import os
import html
import json
from urllib.parse import urlencode
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

/* Keep the native sidebar toggle visible without reserving a blank header row. */
header[data-testid="stHeader"], [data-testid="stHeader"] {
 display:flex!important;
 visibility:visible!important;
 opacity:1!important;
 position:fixed!important;
 top:0!important; left:0!important; right:0!important;
 width:100%!important;
 height:0!important; min-height:0!important;
 padding:0!important; margin:0!important;
 background:transparent!important;
 border:0!important; box-shadow:none!important; overflow:visible!important;
 z-index:100000!important; pointer-events:none!important;
}
[data-testid="stHeader"] [data-testid="stToolbar"] {
 display:flex!important;
 visibility:visible!important;
 opacity:1!important;
 height:0!important; min-height:0!important;
 pointer-events:none!important;
 background:transparent!important;
}
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarExpandButton"],
[data-testid="stSidebarCollapsedControl"]{
 display:flex!important;visibility:visible!important;opacity:1!important;
 pointer-events:auto!important;position:relative!important;z-index:100002!important
}
/* Minimal sidebar toggle: white arrow only, with no button tile. */
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarExpandButton"] button,
[data-testid="stSidebarCollapsedControl"] button{
 display:flex!important;
 align-items:center!important;
 justify-content:center!important;
 visibility:visible!important;
 opacity:1!important;
 pointer-events:auto!important;
 color:#FFFFFF!important;
 background:transparent!important;
 border:0!important;
 border-radius:0!important;
 box-shadow:none!important;
 padding:0.25rem!important;
 min-width:2rem!important;
 min-height:2rem!important;
}
[data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="stSidebarExpandButton"] button:hover,
[data-testid="stSidebarCollapsedControl"] button:hover,
[data-testid="stSidebarCollapseButton"] button:focus,
[data-testid="stSidebarExpandButton"] button:focus,
[data-testid="stSidebarCollapsedControl"] button:focus{
 color:#FFFFFF!important;
 background:transparent!important;
 border:0!important;
 box-shadow:none!important;
}
[data-testid="stSidebarCollapseButton"] button svg,
[data-testid="stSidebarExpandButton"] button svg,
[data-testid="stSidebarCollapsedControl"] button svg{
 color:#FFFFFF!important;
 fill:none!important;
 stroke:#FFFFFF!important;
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
.sidebar-brand{padding:2px 0 14px!important;border-bottom:0!important;margin-top:0!important;margin-bottom:12px!important}
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

/* Floating Energy 360 AI launcher stays visible while the page scrolls. */
div[class*="st-key-energy360_ai_launcher"] {
    position: fixed !important; right: 24px !important; bottom: 22px !important;
    width: auto !important; z-index: 1000500 !important; margin: 0 !important; padding: 0 !important;
}
div[class*="st-key-energy360_ai_launcher"] [data-testid="stPopover"] > button,
div[class*="st-key-energy360_ai_launcher"] button {
    background: linear-gradient(135deg,#08AFC2,#087EA5) !important;
    color: #FFFFFF !important; border: 1px solid rgba(255,255,255,.65) !important;
    border-radius: 999px !important; min-height: 48px !important;
    padding: .55rem 1rem !important; box-shadow: 0 6px 22px rgba(5,43,70,.28) !important;
    font-weight: 750 !important;
}

@media(max-width:1050px){.metric-value{font-size:1.08rem}.hero-title{font-size:1.6rem}.hero-banner:after{width:42%}}

/* Property chart section labels are bold; chart-internal titles remain regular. */
.property-chart-section-heading {
    font-weight: 800 !important;
    text-transform: none !important;
    font-size: 1rem;
    color: #183B59;
    margin: 0 0 0.75rem 0;
}
.js-plotly-plot .gtitle,
.js-plotly-plot .gtitle text,
.js-plotly-plot .gtitle tspan {
    font-weight: 400 !important;
    text-transform: none !important;
}
/* Consistent bold Pascal Case headers throughout every app page. */
h1, h2, h3, h4, h5, h6,
[data-testid="stSubheader"],
[data-testid="stMetricLabel"],
[data-testid="stDataFrame"] [role="columnheader"],
[data-testid="stTable"] th,
[data-testid="stTabs"] button[role="tab"],
[data-testid="stSidebar"] .stButton > button,
.chart-title,
.js-plotly-plot .xtitle,
.js-plotly-plot .ytitle,
.js-plotly-plot .legendtitle,
.js-plotly-plot .annotation-text {
    font-weight: 800 !important;
    text-transform: capitalize !important;
}

/* Energy360 typography system: consistent, compact and readable across pages. */
html, body, [class*="css"], .stApp {
    font-family: Inter, "Segoe UI", Arial, sans-serif !important;
    font-size: 14px !important;
    line-height: 1.5 !important;
}
.stMarkdown, .stMarkdown p, .stText, [data-testid="stText"],
[data-testid="stCaptionContainer"], .stCaption, .stAlert,
[data-testid="stAlert"] p, .stExpander p {
    font-size: 0.875rem !important;
    line-height: 1.5 !important;
}
h1, .stTitle, [data-testid="stTitle"] {
    font-size: 1.55rem !important;
    line-height: 1.25 !important;
    font-weight: 700 !important;
    letter-spacing: -0.35px !important;
}
h2, .stSubheader, [data-testid="stSubheader"] {
    font-size: 1.18rem !important;
    line-height: 1.35 !important;
    font-weight: 650 !important;
    letter-spacing: -0.2px !important;
}
h3, h4, h5, h6 {
    font-size: 1rem !important;
    line-height: 1.35 !important;
    font-weight: 650 !important;
}
.hero-title { font-size: 1.85rem !important; line-height: 1.2 !important; font-weight: 750 !important; }
.hero-subtitle { font-size: 0.88rem !important; line-height: 1.45 !important; }
.sidebar-brand-name { font-size: 1.35rem !important; }
.sidebar-brand-sub { font-size: 0.75rem !important; }
.sidebar-section { font-size: 0.68rem !important; letter-spacing: 0.8px !important; }
[data-testid="stSidebar"] .stButton > button {
    font-size: 0.84rem !important;
    line-height: 1.35 !important;
    font-weight: 550 !important;
    padding: 0.48rem 0.65rem !important;
}
label, [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p,
.stSelectbox label, .stTextInput label, .stDateInput label,
.stNumberInput label, .stRadio label, .stMultiSelect label {
    font-size: 0.82rem !important;
    line-height: 1.35 !important;
    font-weight: 600 !important;
}
input, textarea, [data-baseweb="select"] *, [data-baseweb="input"] *,
[data-testid="stDateInput"] input, [data-testid="stNumberInput"] input {
    font-size: 0.86rem !important;
}
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] button {
    font-size: 0.84rem !important;
    line-height: 1.35 !important;
    font-weight: 600 !important;
}
div[data-testid="stMetric"] { padding: 12px 14px !important; }
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p {
    font-size: 0.78rem !important;
    line-height: 1.3 !important;
    font-weight: 600 !important;
}
[data-testid="stMetricValue"], [data-testid="stMetricValue"] div {
    font-size: 1.45rem !important;
    line-height: 1.25 !important;
    font-weight: 700 !important;
}
[data-testid="stMetricDelta"], [data-testid="stMetricDelta"] div {
    font-size: 0.75rem !important;
}
.metric-label { font-size: 0.76rem !important; }
.metric-value { font-size: 1.25rem !important; }
.chart-title, .property-chart-section-heading {
    font-size: 0.98rem !important;
    line-height: 1.35 !important;
    font-weight: 650 !important;
}
[data-testid="stTabs"] button[role="tab"] {
    font-size: 0.82rem !important;
    line-height: 1.3 !important;
    font-weight: 600 !important;
    padding: 0.55rem 0.8rem !important;
}
[data-testid="stDataFrame"], [data-testid="stDataFrame"] *,
[data-testid="stTable"], [data-testid="stTable"] * {
    font-size: 0.80rem !important;
    line-height: 1.4 !important;
}
[data-testid="stDataFrame"] [role="columnheader"],
[data-testid="stTable"] th {
    font-size: 0.78rem !important;
    font-weight: 650 !important;
}
[data-testid="stCaptionContainer"] p, .stCaption {
    font-size: 0.76rem !important;
    color: #62778A !important;
}
.filter-heading { font-size: 0.88rem !important; }
.utility-item { font-size: 0.92rem !important; }
.utility-avatar { font-size: 0.72rem !important; }
.js-plotly-plot, .js-plotly-plot text {
    font-family: Inter, "Segoe UI", Arial, sans-serif !important;
}
.js-plotly-plot .xtick text, .js-plotly-plot .ytick text,
.js-plotly-plot .legendtext, .js-plotly-plot .annotation-text {
    font-size: 11px !important;
}
.js-plotly-plot .gtitle { font-size: 15px !important; font-weight: 500 !important; }
.js-plotly-plot .xtitle, .js-plotly-plot .ytitle {
    font-size: 12px !important;
    font-weight: 500 !important;
}
@media (max-width: 900px) {
    html, body, [class*="css"], .stApp { font-size: 13px !important; }
    .hero-title { font-size: 1.45rem !important; }
    h1, .stTitle, [data-testid="stTitle"] { font-size: 1.35rem !important; }
    h2, .stSubheader, [data-testid="stSubheader"] { font-size: 1.08rem !important; }
}


/* Keep the complete hero heading and subtitle inside the solid blue area. */
.hero-banner:after {
    left: 58% !important;
    right: 0 !important;
    width: auto !important;
}
.hero-content {
    max-width: 56% !important;
    flex: 0 0 56% !important;
    position: relative !important;
    z-index: 2 !important;
}
.hero-subtitle {
    display: block !important;
    width: fit-content !important;
    max-width: 100% !important;
    color: #E1EDF5 !important;
    background: transparent !important;
    border: 0 !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin-top: 7px !important;
    overflow-wrap: anywhere !important;
}
@media (max-width: 900px) {
    .hero-banner:after { left: 68% !important; right: 0 !important; width: auto !important; }
    .hero-content { max-width: 65% !important; flex-basis: 65% !important; }
}
@media (max-width: 600px) {
    .hero-banner:after { left: 72% !important; opacity: 0.45 !important; }
    .hero-content { max-width: 70% !important; flex-basis: 70% !important; }
}


/* Hide export controls throughout the app, including page-specific CSV actions. */
[data-testid="stDownloadButton"],
.stDownloadButton,
div[data-testid="stDownloadButton"] {
    display: none !important;
}
/* Remove the Streamlit status/rendering badge from the top chrome. */
[data-testid="stStatusWidget"],
[data-testid="stToolbar"] [data-testid="stStatusWidget"],
.stStatusWidget {
    display: none !important;
}


/* Sidebar arrow: crisp white icon on a transparent hit target. */
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarExpandButton"],
[data-testid="stSidebarCollapsedControl"] {
    position: fixed !important;
    top: 8px !important;
    left: calc(var(--sidebar-width, 18rem) - 42px) !important;
    z-index: 100010 !important;
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
}
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarExpandButton"] button,
[data-testid="stSidebarCollapsedControl"] button {
    width: 30px !important;
    height: 30px !important;
    min-width: 30px !important;
    min-height: 30px !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    color: #FFFFFF !important;
    background: transparent !important;
    border: 0 !important;
    border-radius: 6px !important;
    box-shadow: none !important;
    pointer-events: auto !important;
}
[data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="stSidebarExpandButton"] button:hover,
[data-testid="stSidebarCollapsedControl"] button:hover {
    background: rgba(255,255,255,0.12) !important;
    color: #FFFFFF !important;
}
[data-testid="stSidebarCollapseButton"] button svg,
[data-testid="stSidebarExpandButton"] button svg,
[data-testid="stSidebarCollapsedControl"] button svg,
[data-testid="stSidebarCollapseButton"] button svg *,
[data-testid="stSidebarExpandButton"] button svg *,
[data-testid="stSidebarCollapsedControl"] button svg * {
    color: #FFFFFF !important;
    fill: #FFFFFF !important;
    stroke: #FFFFFF !important;
    opacity: 1 !important;
}
/* Start the sidebar and hero ribbon at the same top edge. */
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
section[data-testid="stMain"] {
    padding-top: 0 !important;
    margin-top: 0 !important;
}
[data-testid="stSidebar"] {
    top: 0 !important;
}
[data-testid="stSidebar"] > div {
    padding-top: 0.45rem !important;
}
.block-container,
[data-testid="stMainBlockContainer"],
section[data-testid="stMain"] .block-container {
    padding-top: 0 !important;
    margin-top: 0 !important;
}
.hero-banner {
    margin-top: 0 !important;
}


/* Remove Streamlit's white top toolbar strip without losing the sidebar toggle. */
header[data-testid="stHeader"],
[data-testid="stHeader"] {
    height: 0 !important;
    min-height: 0 !important;
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
}
[data-testid="stToolbar"] {
    height: 0 !important;
    min-height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
    overflow: visible !important;
}
/* Do not hide toolbar children: Streamlit places the collapsed-sidebar control here. */
[data-testid="stToolbar"] > div {
    visibility: visible !important;
}
[data-testid="stToolbarActions"],
[data-testid="stStatusWidget"],
[data-testid="stDecoration"],
#MainMenu,
.stDeployButton {
    display: none !important;
}
/* Keep the sidebar control visible and fixed in both expanded and collapsed states. */
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarExpandButton"] {
    position: fixed !important;
    top: 8px !important;
    left: calc(var(--sidebar-width, 18rem) - 42px) !important;
    z-index: 100020 !important;
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
}
[data-testid="stSidebarCollapsedControl"] {
    position: fixed !important;
    top: 8px !important;
    left: 8px !important;
    z-index: 100020 !important;
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
}
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarExpandButton"] button,
[data-testid="stSidebarCollapsedControl"] button {
    width: 32px !important;
    height: 32px !important;
    min-width: 32px !important;
    min-height: 32px !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    color: #FFFFFF !important;
    background: transparent !important;
    border: 0 !important;
    border-radius: 5px !important;
    box-shadow: none !important;
    opacity: 1 !important;
    visibility: visible !important;
    pointer-events: auto !important;
}
[data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="stSidebarExpandButton"] button:hover,
[data-testid="stSidebarCollapsedControl"] button:hover {
    color: #FFFFFF !important;
    background: rgba(255,255,255,0.14) !important;
}
[data-testid="stSidebarCollapseButton"] button svg,
[data-testid="stSidebarExpandButton"] button svg,
[data-testid="stSidebarCollapsedControl"] button svg,
[data-testid="stSidebarCollapseButton"] button svg *,
[data-testid="stSidebarExpandButton"] button svg *,
[data-testid="stSidebarCollapsedControl"] button svg * {
    color: #FFFFFF !important;
    fill: #FFFFFF !important;
    stroke: #FFFFFF !important;
    opacity: 1 !important;
}


/* Crop/zoom the hero artwork so its source-image edges never appear as a frame. */
.hero-banner {
    border-top: 0 !important;
    border-right: 0 !important;
    border-bottom: 0 !important;
    outline: 0 !important;
    box-shadow: none !important;
    background-color: #082D4D !important;
}
.hero-banner:after {
    top: -10px !important;
    right: -14px !important;
    bottom: -10px !important;
    left: 58% !important;
    width: auto !important;
    background-size: cover !important;
    background-position: center 54% !important;
    transform: scale(1.07) !important;
    transform-origin: center center !important;
}
@media (max-width: 900px) {
    .hero-banner:after {
        left: 68% !important;
        right: -12px !important;
        transform: scale(1.08) !important;
    }
}
@media (max-width: 600px) {
    .hero-banner:after {
        left: 72% !important;
        right: -10px !important;
        transform: scale(1.1) !important;
    }
}
/* Eliminate any residual top gap before the banner. */
[data-testid="stMain"],
section[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
section[data-testid="stMain"] .block-container {
    padding-top: 0 !important;
    margin-top: 0 !important;
}


/* Reliable white sidebar toggle in both expanded and collapsed layouts. */
header[data-testid="stHeader"],
[data-testid="stHeader"] {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    height: 40px !important;
    min-height: 40px !important;
    overflow: visible !important;
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
    pointer-events: none !important;
    z-index: 100100 !important;
}
[data-testid="stToolbar"] {
    height: 40px !important;
    min-height: 40px !important;
    overflow: visible !important;
    background: transparent !important;
    pointer-events: none !important;
}
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarExpandButton"] {
    position: fixed !important;
    top: 6px !important;
    left: 248px !important;
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    z-index: 100200 !important;
    pointer-events: auto !important;
}
[data-testid="stSidebarCollapsedControl"] {
    position: fixed !important;
    top: 6px !important;
    left: 8px !important;
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    z-index: 100200 !important;
    pointer-events: auto !important;
}
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarExpandButton"] button,
[data-testid="stSidebarCollapsedControl"] button,
button[aria-label*="sidebar" i],
button[title*="sidebar" i] {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 32px !important;
    height: 32px !important;
    min-width: 32px !important;
    min-height: 32px !important;
    padding: 0 !important;
    color: #FFFFFF !important;
    background: rgba(3, 29, 54, 0.92) !important;
    border: 1px solid rgba(255,255,255,0.55) !important;
    border-radius: 6px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.22) !important;
    opacity: 1 !important;
    visibility: visible !important;
    pointer-events: auto !important;
}
[data-testid="stSidebarCollapseButton"] button svg,
[data-testid="stSidebarExpandButton"] button svg,
[data-testid="stSidebarCollapsedControl"] button svg,
button[aria-label*="sidebar" i] svg,
button[title*="sidebar" i] svg,
[data-testid="stSidebarCollapseButton"] button svg *,
[data-testid="stSidebarExpandButton"] button svg *,
[data-testid="stSidebarCollapsedControl"] button svg * {
    color: #FFFFFF !important;
    fill: none !important;
    stroke: #FFFFFF !important;
    opacity: 1 !important;
}


/* Final banner treatment: solid blue only, with no turbine image or image frame. */
.hero-banner {
    position: relative !important;
    overflow: hidden !important;
    background: linear-gradient(110deg, #062744 0%, #0A3558 58%, #10466B 100%) !important;
    border: 0 !important;
    outline: 0 !important;
    box-shadow: none !important;
    margin-top: 0 !important;
}
.hero-banner:after {
    content: none !important;
    display: none !important;
    background: none !important;
}
/* Remove the white Streamlit top strip and its reserved height. */
header[data-testid="stHeader"],
[data-testid="stHeader"],
[data-testid="stToolbar"] {
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
}
[data-testid="stHeader"] {
    height: 0 !important;
    min-height: 0 !important;
}
[data-testid="stToolbar"] {
    height: 0 !important;
    min-height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    overflow: visible !important;
}
/* Keep only the native sidebar toggle available above the page. */
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarExpandButton"],
[data-testid="stSidebarCollapsedControl"] {
    z-index: 100300 !important;
    visibility: visible !important;
    opacity: 1 !important;
}


/* Restore the original Energy360 hero image treatment. */
.hero-banner {
    position: relative !important;
    overflow: hidden !important;
    background: linear-gradient(90deg, rgba(4,35,65,.98) 0%, rgba(7,49,83,.94) 48%, rgba(8,57,85,.45) 100%), linear-gradient(135deg,#123C5D,#0A2946) !important;
    border-left: 5px solid #17C2D2 !important;
    border-top: 0 !important;
    border-right: 0 !important;
    border-bottom: 0 !important;
}
.hero-banner:after {
    content: "" !important;
    display: block !important;
    position: absolute !important;
    inset: 0 0 0 42% !important;
    background-image: linear-gradient(90deg,rgba(5,35,66,.10),rgba(5,35,66,.04)), url("https://www.acer.europa.eu/sites/default/files/2024-03/ELE_KD_0.jpg") !important;
    background-size: cover !important;
    background-position: center 54% !important;
    transform: none !important;
    pointer-events: none !important;
    z-index: 0 !important;
}
.hero-content { position: relative !important; z-index: 1 !important; }

/* Slim white arrow only: no border, no tile, and visible at either sidebar state. */
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarExpandButton"] {
    position: fixed !important;
    top: 7px !important;
    left: 258px !important;
    width: 24px !important;
    height: 28px !important;
    min-width: 24px !important;
    min-height: 28px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    visibility: visible !important;
    opacity: 1 !important;
    z-index: 100500 !important;
    pointer-events: auto !important;
}
[data-testid="stSidebarCollapsedControl"] {
    position: fixed !important;
    top: 7px !important;
    left: 7px !important;
    width: 24px !important;
    height: 28px !important;
    min-width: 24px !important;
    min-height: 28px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    visibility: visible !important;
    opacity: 1 !important;
    z-index: 100500 !important;
    pointer-events: auto !important;
}
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarExpandButton"] button,
[data-testid="stSidebarCollapsedControl"] button {
    width: 22px !important;
    height: 26px !important;
    min-width: 22px !important;
    min-height: 26px !important;
    padding: 0 !important;
    margin: 0 !important;
    color: #FFFFFF !important;
    background: transparent !important;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    border-radius: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    opacity: 1 !important;
    visibility: visible !important;
    pointer-events: auto !important;
}
[data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="stSidebarExpandButton"] button:hover,
[data-testid="stSidebarCollapsedControl"] button:hover,
[data-testid="stSidebarCollapseButton"] button:focus,
[data-testid="stSidebarExpandButton"] button:focus,
[data-testid="stSidebarCollapsedControl"] button:focus {
    color: #FFFFFF !important;
    background: transparent !important;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
}
[data-testid="stSidebarCollapseButton"] button svg,
[data-testid="stSidebarExpandButton"] button svg,
[data-testid="stSidebarCollapsedControl"] button svg,
[data-testid="stSidebarCollapseButton"] button svg *,
[data-testid="stSidebarExpandButton"] button svg *,
[data-testid="stSidebarCollapsedControl"] button svg * {
    color: #FFFFFF !important;
    fill: none !important;
    stroke: #FFFFFF !important;
    opacity: 1 !important;
}


/* Keep the entire hero heading and subtitle on the solid-blue side. */
.hero-banner {
    position: relative !important;
}
.hero-banner:after {
    left: 62% !important;
    right: 0 !important;
    width: auto !important;
    background-position: center center !important;
}
.hero-content {
    position: relative !important;
    z-index: 2 !important;
    width: 60% !important;
    max-width: 60% !important;
    flex: 0 0 60% !important;
}
.hero-title,
.hero-subtitle {
    display: block !important;
    max-width: 100% !important;
    overflow-wrap: anywhere !important;
    background: transparent !important;
    box-shadow: none !important;
}
.hero-subtitle {
    color: #E1EDF5 !important;
    white-space: normal !important;
}
@media (max-width: 900px) {
    .hero-banner:after { left: 68% !important; }
    .hero-content { width: 65% !important; max-width: 65% !important; flex-basis: 65% !important; }
}
@media (max-width: 600px) {
    .hero-banner:after { left: 72% !important; }
    .hero-content { width: 68% !important; max-width: 68% !important; flex-basis: 68% !important; }
}


/* Improve contrast and hierarchy for selected-property information. */
.property-detail-line {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px 8px;
    margin: 7px 0 5px !important;
    color: #29445D !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    line-height: 1.55 !important;
}
.property-detail-line .property-type {
    color: #102F4A !important;
    font-weight: 750 !important;
}
.property-meta-line {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px 18px;
    margin: 3px 0 12px !important;
    padding: 8px 11px;
    background: #E8F0F7 !important;
    border: 1px solid #C9D8E6 !important;
    border-radius: 7px;
    color: #29445D !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    line-height: 1.5 !important;
}
.property-meta-line span {
    color: #29445D !important;
}
.property-meta-line strong {
    color: #102F4A !important;
    font-weight: 750 !important;
    margin-right: 4px;
}

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

def update_contract_link(scope,link_id,contract_number,contract_name,start_date,end_date):
    return data_client().update_contract_link(scope,link_id,contract_number,contract_name,start_date,end_date)

def delete_contract_link(scope,link_id):
    return data_client().delete_contract_link(scope,link_id)

def get_contract_management_options():
    return data_client().contract_management_options()

def get_contract_management_data(property_id, scope):
    return data_client().contract_management_data(property_id, scope)

@st.cache_data(ttl=180, show_spinner=False)
def get_all_contracts():
    return data_client().all_contracts_data()


@st.cache_data(ttl=180, show_spinner=False)
def get_property_bills(property_id):
    return data_client().property_bill_data(property_id)

@st.cache_data(ttl=180, show_spinner=False)
def get_property_procurement(property_id):
    return data_client().property_procurement_data(property_id)


@st.cache_data(ttl=3600, show_spinner=False)
def get_crud_columns(entity):
    return data_client().crud_columns(entity)

@st.cache_data(ttl=120, show_spinner=False)
def get_crud_rows(entity, property_id):
    return data_client().crud_rows(entity, property_id, limit=300)

@st.cache_data(ttl=600, show_spinner=False)
def get_crud_choices(entity, column, property_id):
    return data_client().crud_choices(entity, column, property_id)

def save_crud_record(entity, values, record_id=None):
    return data_client().crud_save(entity, values, record_id)

def delete_crud_record(entity, record_id):
    return data_client().crud_delete(entity, record_id)

def clear_property_crud_cache():
    get_crud_rows.clear()
    get_crud_columns.clear()
    get_crud_choices.clear()
    get_property_meters.clear()
    get_property_accounts.clear()
    get_property_vendors.clear()
    get_property_rates.clear()
    get_property_contracts.clear()
    get_property_meter_contracts.clear()
    get_property_bills.clear()
    get_property_procurement.clear()
    get_all_contracts.clear()


@st.fragment
def render_crud_entity(entity, title, property_id):
    client = data_client()
    try:
        table, key_col = client.crud_table(entity)
        columns = get_crud_columns(entity)
        rows = get_crud_rows(entity, property_id)
    except DataAccessError as exc:
        st.error(f"Unable to load {title.lower()}: {exc}")
        return

    rels = client.CRUD_RELATIONSHIPS.get(table, {})
    editable = [c for c in columns if c["name"] not in
                (key_col, "created_at", "updated_at", "ingestion_timestamp")]
    st.markdown(f"**{title}**")
    with st.expander(f"＋ Add {title.rstrip('s')}", expanded=False):
        with st.form(f"crud_add_{entity}_{property_id}"):
            values = {}
            for col in editable:
                name, dtype = col["name"], col["type"]
                label = name.replace("_", " ").title()
                if name in rels:
                    options = [("", "— Select —")] + get_crud_choices(entity, name, property_id)
                    chosen = st.selectbox(label, options, format_func=lambda x: x[1],
                                          key=f"crud_add_{entity}_{name}_{property_id}")
                    values[name] = chosen[0] or None
                elif dtype == "boolean":
                    values[name] = st.checkbox(label, key=f"crud_add_{entity}_{name}_{property_id}")
                else:
                    values[name] = st.text_input(label, placeholder=f"Enter {label.lower()}",
                                                 key=f"crud_add_{entity}_{name}_{property_id}")
            if st.form_submit_button(f"Save New {title.rstrip('s')}", type="primary"):
                try:
                    save_crud_record(entity, values)
                    clear_property_crud_cache()
                    st.success(f"{title.rstrip('s')} created.")
                    st.rerun()
                except DataAccessError as exc:
                    st.error(f"Could not create record: {exc}")

    if rows.empty:
        st.caption(f"No {title.lower()} records found.")
        return

    # Preserve the approved compact row layout while making the full grid
    # horizontally scrollable. Each data column has a fixed readable width.
    visible = list(rows.columns)
    data_width = 132
    widths = [data_width] * len(visible) + [88, 88]
    grid_key = f"crud-native-grid-{entity}-{property_id}"
    st.markdown(f"""
    <style>
      .st-key-{grid_key} {{
        display:block !important; position:relative !important;
        width:100% !important; max-width:100% !important;
        overflow-x:auto !important; overflow-y:hidden !important;
        scrollbar-width:auto !important; padding-bottom:8px !important;
      }}
      .st-key-{grid_key} > div,
      .st-key-{grid_key} > div > [data-testid="stVerticalBlock"] {{
        width:max-content !important; min-width:100% !important;
        max-width:none !important; display:flex !important;
        flex-direction:column !important; gap:0 !important;
      }}
      .st-key-{grid_key} > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {{
        display:flex !important; flex-wrap:nowrap !important;
        align-items:center !important; justify-content:flex-start !important;
        width:max-content !important; min-width:100% !important;
        max-width:none !important; gap:0 !important;
        border-bottom:1px solid #E5EDF4 !important; padding:0 !important;
      }}
      .st-key-{grid_key} [class*="st-key-crud-grid-row-"] {{
        display:block !important;
        width:max-content !important;
        min-width:max-content !important;
        max-width:none !important;
        margin:0 !important;
        padding:0 !important;
      }}
      .st-key-{grid_key} [class*="st-key-crud-grid-row-"] [data-testid="stHorizontalBlock"] {{
        display:flex !important; flex-wrap:nowrap !important;
        width:max-content !important; min-width:max-content !important;
        gap:0 !important; align-items:stretch !important;
      }}
      .st-key-{grid_key} [class*="st-key-crud-grid-row-"] [data-testid="column"] {{
        box-sizing:border-box !important;
        flex:0 0 {data_width}px !important; width:{data_width}px !important;
        min-width:{data_width}px !important; max-width:{data_width}px !important;
        padding:8px 10px !important;
        border-left:1px solid #D9E1EA !important;
        border-top:1px solid #D9E1EA !important;
        border-bottom:1px solid #D9E1EA !important;
        background:#FFFFFF !important;
        text-align:left !important;
      }}
      .st-key-{grid_key} [class*="st-key-crud-grid-row-"] [data-testid="column"]:nth-last-child(-n+2) {{
        box-sizing:border-box !important;
        flex:0 0 88px !important; width:88px !important;
        min-width:88px !important; max-width:88px !important;
      }}
      .st-key-{grid_key} [class*="st-key-crud-grid-row-"] [data-testid="column"]:last-child {{
        border-right:1px solid #D9E1EA !important;
      }}
      .st-key-{grid_key} .crud-header-row {{ margin:0 !important; padding:0 !important; }}
      .st-key-{grid_key} .crud-header-cell {{
        box-sizing:border-box !important; display:flex !important;
        align-items:center !important; min-height:48px !important;
        padding:7px 10px !important; border-right:1px solid #E5EDF4 !important;
        font-size:13px !important; font-weight:650 !important;
        line-height:1.25 !important; white-space:normal !important;
        overflow-wrap:anywhere !important; word-break:normal !important;
      }}
      .st-key-{grid_key} .crud-header-cell span {{
        display:block !important; width:100% !important;
      }}
      .st-key-{grid_key} [data-testid="stMarkdown"],
      .st-key-{grid_key} [data-testid="stMarkdownContainer"] {{ margin:0 !important; padding:0 !important; text-align:left !important; width:100% !important; }}
      .st-key-{grid_key} [data-testid="stMarkdownContainer"] p {{ text-align:left !important;
        margin:0 !important; white-space:nowrap !important;
        overflow:hidden !important; text-overflow:ellipsis !important;
        font-size:13px !important;
      }}
      .st-key-{grid_key} [data-testid="stButton"] {{ margin:0 !important; }}
      .st-key-{grid_key} [data-testid="stButton"] button {{
        width:100% !important; min-width:68px !important;
        min-height:34px !important; padding:5px 7px !important;
        white-space:nowrap !important;
      }}
    </style>
    """, unsafe_allow_html=True)

    with st.container(key=grid_key):
        # Render headers with the exact same Streamlit column structure and
        # width ratios as each data row. This guarantees header/value alignment.
        with st.container(key=f"crud-grid-row-{entity}-{property_id}-header"):
            header = st.columns(widths, gap=0, vertical_alignment="center")
            for idx, col_name in enumerate(visible):
                with header[idx]:
                    st.markdown(
                    f'<div title="{html.escape("".join(part[:1].upper() + part[1:] for part in col_name.replace("_", " ").split()), quote=True)}" style="box-sizing:border-box;display:flex;align-items:center;width:{data_width-20}px;min-height:48px;margin:0;padding:7px 8px;border:1px solid #C9D4E0;background:#EDF2F7;text-align:left;white-space:normal;overflow-wrap:anywhere;line-height:1.2;font-weight:700;">{html.escape("".join(part[:1].upper() + part[1:] for part in col_name.replace("_", " ").split()))}</div>',
                        unsafe_allow_html=True,
                    )
            with header[-2]:
                st.markdown("")
            with header[-1]:
                st.markdown("")

        for _, record in rows.iterrows():
            record_id = str(record[key_col])
            with st.container(key=f"crud-grid-row-{entity}-{property_id}-{record_id}"):
                cells = st.columns(widths, gap=0, vertical_alignment="center")
                for idx, col_name in enumerate(visible):
                    raw_value = record.get(col_name)
                    if pd.isna(raw_value):
                        display_value = "—"
                    elif isinstance(raw_value, pd.Timestamp):
                        display_value = raw_value.strftime("%Y-%m-%d")
                    else:
                        display_value = str(raw_value)
                    with cells[idx]:
                        st.markdown(
                            f'<div title="{html.escape(display_value, quote=True)}" style="box-sizing:border-box;display:flex;align-items:center;width:{data_width-20}px;min-height:38px;margin:0;padding:7px 8px;border:1px solid #D5DEE8;background:#FFFFFF;text-align:left;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{html.escape(display_value)}</div>',
                            unsafe_allow_html=True,
                        )
                with cells[-2]:
                    if st.button("Edit", key=f"crud_edit_row_{entity}_{property_id}_{record_id}", use_container_width=True):
                        st.session_state[f"crud_active_edit_{entity}_{property_id}"] = record_id
                        st.session_state.pop(f"crud_active_delete_{entity}_{property_id}", None)
                with cells[-1]:
                    if st.button("Delete", key=f"crud_delete_row_{entity}_{property_id}_{record_id}", use_container_width=True):
                        st.session_state[f"crud_active_delete_{entity}_{property_id}"] = record_id
                        st.session_state.pop(f"crud_active_edit_{entity}_{property_id}", None)

            # When an action is selected at the far-right end, reset the horizontal
            # table viewport to the first column so the inline form is immediately visible.
            active_edit = st.session_state.get(f"crud_active_edit_{entity}_{property_id}")
            active_delete_for_row = st.session_state.get(f"crud_active_delete_{entity}_{property_id}")
            if active_edit == record_id or active_delete_for_row == record_id:
                st.components.v1.html(
                    f"""
                    <script>
                    (() => {{
                      const selector = ".st-key-{grid_key}";
                      const reset = () => {{
                        try {{
                          const frame = window.parent.document.querySelector(selector);
                          if (frame) frame.scrollTo({{left: 0, behavior: "instant"}});
                        }} catch (e) {{}}
                      }};
                      reset();
                      requestAnimationFrame(reset);
                      setTimeout(reset, 80);
                    }})();
                    </script>
                    """,
                    height=0,
                    scrolling=False,
                )
            if active_edit == record_id:
                with st.container(border=True):
                    st.markdown(
                        f'<div style="display:block;width:100%;box-sizing:border-box;padding:10px 12px;margin-bottom:10px;background:#F7F9FC;border-bottom:1px solid #DCE6EF;border-radius:6px;font-size:14px;font-weight:700;line-height:1.4;white-space:normal;overflow-wrap:anywhere;">Edit {html.escape(title.rstrip("s"))} — {html.escape(record_id)}</div>',
                        unsafe_allow_html=True,
                    )
                    with st.form(f"crud_edit_{entity}_{property_id}_{record_id}"):
                        values = {}
                        for col in editable:
                            name, dtype = col["name"], col["type"]
                            label = name.replace("_", " ").title()
                            current_value = record.get(name)
                            if name in rels:
                                options = get_crud_choices(entity, name, property_id)
                                option_ids = [x[0] for x in options]
                                current_id = str(current_value) if pd.notna(current_value) else ""
                                if current_id and current_id not in option_ids:
                                    options = [(current_id, current_id)] + options
                                options = [("", "— None —")] + options
                                idx = next((i for i, x in enumerate(options) if x[0] == current_id), 0)
                                chosen = st.selectbox(
                                    label, options, index=idx, format_func=lambda x: x[1],
                                    key=f"crud_edit_{entity}_{name}_{record_id}",
                                )
                                values[name] = chosen[0] or None
                            elif dtype == "boolean":
                                values[name] = st.checkbox(
                                    label,
                                    value=bool(current_value) if pd.notna(current_value) else False,
                                    key=f"crud_edit_{entity}_{name}_{record_id}",
                                )
                            else:
                                default = "" if pd.isna(current_value) else str(current_value)
                                values[name] = st.text_input(
                                    label, value=default,
                                    key=f"crud_edit_{entity}_{name}_{record_id}",
                                )
                        c1, c2 = st.columns(2)
                        with c1:
                            submitted = st.form_submit_button(
                                "Save Changes", type="primary", use_container_width=True
                            )
                        with c2:
                            cancel = st.form_submit_button("Cancel", use_container_width=True)
                        if submitted:
                            try:
                                save_crud_record(entity, values, record_id)
                                st.session_state.pop(f"crud_active_edit_{entity}_{property_id}", None)
                                clear_property_crud_cache()
                                st.success("Record updated.")
                                st.rerun()
                            except DataAccessError as exc:
                                st.error(f"Update blocked: {exc}")
                        elif cancel:
                            st.session_state.pop(f"crud_active_edit_{entity}_{property_id}", None)
                            st.rerun()

            active_delete = st.session_state.get(f"crud_active_delete_{entity}_{property_id}")
            if active_delete == record_id:
                with st.container(border=True):
                    st.warning(f"Delete this {title.rstrip('s')} record? This cannot be undone.")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button(
                            "Confirm Delete", key=f"crud_confirm_delete_{entity}_{record_id}",
                            type="primary", use_container_width=True,
                        ):
                            try:
                                delete_crud_record(entity, record_id)
                                st.session_state.pop(f"crud_active_delete_{entity}_{property_id}", None)
                                clear_property_crud_cache()
                                st.success("Record deleted.")
                                st.rerun()
                            except DataAccessError as exc:
                                st.error(f"Deletion blocked: {exc}")
                    with c2:
                        if st.button(
                            "Cancel", key=f"crud_cancel_delete_{entity}_{record_id}",
                            use_container_width=True,
                        ):
                            st.session_state.pop(f"crud_active_delete_{entity}_{property_id}", None)
                            st.rerun()


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
        ("OPERATIONS", ["Property Energy Management", "Energy Compliance", "Budgets / Savings", "Contract Portfolio"]),
        ("SUSTAINABILITY & MARKETS", [
            "Energy Generation", "Transmission & Distribution", "Energy Consumption",
            "Asset Management", "Forecasting & Analytics", "Sustainability",
            "Energy Cost & Trading",
        ]),
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
                    "Property Energy Management":"⌂", "Energy Compliance":"▣", "Budgets / Savings":"▤", "Contract Portfolio":"▤", "Asset Management":"⚙", "Forecasting & Analytics":"⌁",
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
        "Energy Compliance": "Track property energy, water and emissions performance against applicable building benchmarking and performance requirements.",
        "Budgets / Savings": "Compare approved property energy budgets with actual costs and monitor planned and realized savings initiatives.",
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
    """Executive portfolio view sourced only from the four property modules."""
    try:
        properties = get_property_list()
        if properties.empty:
            st.warning("No properties were found in dim_property.")
            return

        property_ids = properties["property_id"].astype(str).tolist()
        property_names = dict(zip(properties["property_id"].astype(str), properties["property_name"].astype(str)))
        labels = ["All Properties"] + property_ids
        def property_label(pid):
            if pid == "All Properties":
                return pid
            row = properties.loc[properties["property_id"].astype(str) == str(pid)].iloc[0]
            place = ", ".join(str(v) for v in [row.get("city"), row.get("state_code")]
                              if pd.notna(v) and str(v).strip())
            return f"{row.get('property_name', pid)} | {place}"

        f1, f2 = st.columns([1, 2])
        with f1:
            selected_year = st.selectbox(
                "Fiscal Year", ["All"] + list(range(pd.Timestamp.now().year, pd.Timestamp.now().year - 5, -1)),
                key="exec_fiscal_year"
            )
        with f2:
            selected_property = st.selectbox(
                "Property", labels, index=0, format_func=property_label,
                key="exec_property_filter"
            )
        selected_ids = property_ids if selected_property == "All Properties" else [selected_property]

        # Property Energy Management: collect usage at the selected property grain.
        energy_frames = []
        for pid in selected_ids:
            frame = get_property_energy(pid)
            if frame is not None and not frame.empty:
                frame = frame.copy()
                frame["property_id"] = pid
                frame["property_name"] = property_names.get(pid, pid)
                energy_frames.append(frame)
        energy = pd.concat(energy_frames, ignore_index=True) if energy_frames else pd.DataFrame()
        if not energy.empty:
            for col in ["usage_quantity", "cost_amount", "emissions_kg_co2e"]:
                energy[col] = pd.to_numeric(energy[col], errors="coerce").fillna(0)
            energy["period_start_date"] = pd.to_datetime(energy["period_start_date"], errors="coerce")
            if selected_year != "All":
                energy = energy[energy["period_start_date"].dt.year == int(selected_year)]

        # Budgets / Savings and Contract Portfolio.
        budgets = data_client().property_budget_portfolio_data()
        savings = data_client().property_savings_portfolio_data()
        contracts = get_all_contracts()
        if not budgets.empty:
            budgets = budgets[budgets["property_id"].astype(str).isin(selected_ids)].copy()
            if selected_year != "All":
                budgets = budgets[pd.to_numeric(budgets["fiscal_year"], errors="coerce") == int(selected_year)]
        if not savings.empty:
            savings = savings[savings["property_id"].astype(str).isin(selected_ids)].copy()
        if contracts is not None and not contracts.empty:
            contracts = contracts[contracts["property_name"].isin([property_names.get(pid, pid) for pid in selected_ids])].copy()

        # Energy Compliance: obligations and reports are property-specific.
        obligation_frames, report_frames = [], []
        for pid in selected_ids:
            obligations = data_client().property_compliance_obligations(pid)
            reports = data_client().property_compliance_reports(pid)
            if obligations is not None and not obligations.empty:
                obligations = obligations.copy()
                obligations["property_id"] = pid
                obligations["property_name"] = property_names.get(pid, pid)
                obligation_frames.append(obligations)
            if reports is not None and not reports.empty:
                reports = reports.copy()
                reports["property_id"] = pid
                reports["property_name"] = property_names.get(pid, pid)
                report_frames.append(reports)
        obligations = pd.concat(obligation_frames, ignore_index=True) if obligation_frames else pd.DataFrame()
        reports = pd.concat(report_frames, ignore_index=True) if report_frames else pd.DataFrame()

    except DataAccessError as exc:
        st.error("Could not load the four property modules for the Executive Dashboard.")
        st.code(str(exc))
        return

    # Portfolio KPI calculations.
    water_mask = energy["commodity_name"].astype(str).str.contains("water", case=False, na=False) if not energy.empty else pd.Series(dtype=bool)
    def usage_by_unit(frame):
        if frame.empty:
            return "No records"
        unit_col = "usage_unit" if "usage_unit" in frame.columns else None
        if not unit_col:
            return f"{len(frame):,} records"
        grouped = (frame.assign(_unit=frame[unit_col].fillna("Unit not specified").astype(str))
                   .groupby("_unit")["usage_quantity"].sum().sort_values(ascending=False))
        parts = [f"{value:,.0f} {unit}" for unit, value in grouped.head(2).items()]
        if len(grouped) > 2:
            parts.append(f"+{len(grouped)-2} more units")
        return " · ".join(parts)
    energy_usage_display = usage_by_unit(energy.loc[~water_mask] if not energy.empty else energy)
    water_usage_display = usage_by_unit(energy.loc[water_mask] if not energy.empty else energy)
    energy_cost = float(energy["cost_amount"].sum()) if not energy.empty else 0.0
    emissions_tonnes = float(energy["emissions_kg_co2e"].sum()) / 1000 if not energy.empty else 0.0
    realized_savings = float(pd.to_numeric(savings.get("realized_savings_amount", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not savings.empty else 0.0
    target_savings = float(pd.to_numeric(savings.get("target_savings_amount", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not savings.empty else 0.0
    approved_budgets = budgets[budgets["approval_status"].astype(str).str.lower().eq("approved")] if not budgets.empty else pd.DataFrame()
    approved_budget = float(pd.to_numeric(approved_budgets.get("budget_amount", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not approved_budgets.empty else 0.0
    active_property_count = len(selected_ids)

    cards = [
        ("Energy Consumption", energy_usage_display, "Non-water energy usage, shown by native commodity unit"),
        ("Water Usage", water_usage_display, "Recorded water volume, shown by native unit"),
        ("Energy Cost", fmt_usd(energy_cost), "From property energy records"),
        ("Carbon Emissions", f"{emissions_tonnes:,.2f} tCO₂e", "Converted from kg CO₂e"),
        ("Realized Savings", fmt_usd(realized_savings), f"Target: {fmt_usd(target_savings)}"),
        ("Approved Budget", fmt_usd(approved_budget), "Approved budgets only"),
    ]
    metric_row([(label, value, note) for label, value, note in cards])

    st.markdown("### Energy Performance")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Monthly Energy Consumption by Commodity**")
        if not energy.empty:
            trend = energy.dropna(subset=["period_start_date"]).copy()
            trend["Month"] = trend["period_start_date"].dt.to_period("M").dt.to_timestamp()
            trend = trend.loc[~trend["commodity_name"].astype(str).str.contains("water", case=False, na=False)]
            trend["series"] = trend["commodity_name"].fillna("Unclassified").astype(str) + " (" + trend["usage_unit"].fillna("unit").astype(str) + ")"
            trend = trend.groupby(["Month", "series"], as_index=False)["usage_quantity"].sum()
            if not trend.empty:
                fig = px.line(trend, x="Month", y="usage_quantity", color="series", markers=True,
                              labels={"usage_quantity":"Usage (commodity-specific unit)","Month":"Month","series":"Commodity / Unit"})
                fig.update_layout(height=330, margin=dict(l=8,r=8,t=20,b=8), paper_bgcolor="white", plot_bgcolor="white", legend_title_text="")
                fig.update_yaxes(gridcolor="#E7EEF4")
                fig.update_xaxes(tickformat="%b %Y")
                st.plotly_chart(fig, use_container_width=True, key="exec_energy_monthly")
            else:
                st.info("No monthly energy consumption records for the selected filters.")
        else:
            st.info("No property energy records for the selected filters.")
    with c2:
        st.markdown("**Monthly Energy Cost**")
        if not energy.empty:
            cost_trend = energy.dropna(subset=["period_start_date"]).copy()
            cost_trend["Month"] = cost_trend["period_start_date"].dt.to_period("M").dt.to_timestamp()
            cost_trend = cost_trend.groupby("Month", as_index=False)["cost_amount"].sum()
            if not cost_trend.empty:
                fig = px.line(cost_trend, x="Month", y="cost_amount", markers=True,
                              labels={"cost_amount":"Energy Cost (USD)","Month":"Month"})
                fig.update_layout(height=330, margin=dict(l=8,r=8,t=20,b=8), paper_bgcolor="white", plot_bgcolor="white")
                fig.update_yaxes(gridcolor="#E7EEF4", tickprefix="$")
                fig.update_xaxes(tickformat="%b %Y")
                st.plotly_chart(fig, use_container_width=True, key="exec_cost_monthly")
            else:
                st.info("No monthly energy cost records for the selected filters.")
        else:
            st.info("No energy cost records for the selected filters.")

    st.markdown("### Budget & Savings Performance")
    b1, b2 = st.columns(2)
    with b1:
        st.markdown("**Approved Budget vs Actual Energy Cost by Property**")
        if not approved_budgets.empty:
            budget_chart = approved_budgets.groupby("property_name", as_index=False)["budget_amount"].sum()
            if not energy.empty:
                actual_chart = energy.groupby("property_name", as_index=False)["cost_amount"].sum()
                budget_chart = budget_chart.merge(actual_chart, on="property_name", how="outer").fillna(0)
            else:
                budget_chart["cost_amount"] = 0
            long = budget_chart.melt(id_vars="property_name", value_vars=["budget_amount","cost_amount"], var_name="Measure", value_name="Amount")
            long["Measure"] = long["Measure"].map({"budget_amount":"Approved Budget","cost_amount":"Actual Energy Cost"})
            fig = px.bar(long, x="property_name", y="Amount", color="Measure", barmode="group",
                         labels={"property_name":"Property","Amount":"Amount (USD)"})
            fig.update_layout(height=330, margin=dict(l=8,r=8,t=20,b=8), paper_bgcolor="white", plot_bgcolor="white", legend_title_text="")
            fig.update_yaxes(tickprefix="$", gridcolor="#E7EEF4")
            st.plotly_chart(fig, use_container_width=True, key="exec_budget_actual")
        else:
            st.info("No approved budget records for the selected filters.")
    with b2:
        st.markdown("**Target vs Realized Savings by Property**")
        if not savings.empty:
            save_chart = savings.groupby("property_name", as_index=False)[["target_savings_amount","realized_savings_amount"]].sum()
            long = save_chart.melt(id_vars="property_name", var_name="Measure", value_name="Amount")
            long["Measure"] = long["Measure"].map({"target_savings_amount":"Target Savings","realized_savings_amount":"Realized Savings"})
            fig = px.bar(long, x="property_name", y="Amount", color="Measure", barmode="group",
                         labels={"property_name":"Property","Amount":"Savings (USD)"})
            fig.update_layout(height=330, margin=dict(l=8,r=8,t=20,b=8), paper_bgcolor="white", plot_bgcolor="white", legend_title_text="")
            fig.update_yaxes(tickprefix="$", gridcolor="#E7EEF4")
            st.plotly_chart(fig, use_container_width=True, key="exec_savings_comparison")
        else:
            st.info("No savings initiatives for the selected filters.")

    st.markdown("### Compliance Overview")
    if not obligations.empty:
        status = obligations["compliance_status"].fillna("Not Reported").astype(str).str.strip().str.lower()
        noncompliant_mask = status.str.contains(r"non[ -]?compliant|overdue|violation|failed|not compliant", regex=True)
        compliant_mask = status.isin(["compliant", "in compliance", "passed"]) & ~noncompliant_mask
        compliant_count = int(compliant_mask.sum())
        noncompliant_count = int(noncompliant_mask.sum())
        other_count = max(len(status) - compliant_count - noncompliant_count, 0)
        compliance_summary = pd.DataFrame({
            "Status": ["Compliant", "Non-Compliant / Overdue", "Other / Pending"],
            "Obligations": [compliant_count, noncompliant_count, other_count],
        })

        # Full-width KPI row avoids leaving a large unused block beside two cards.
        metric_row([
            ("Total Obligations", f"{len(obligations):,}", "All configured compliance obligations"),
            ("Compliant", f"{compliant_count:,}", "Reported compliant or passed"),
            ("Non-Compliant / Overdue", f"{noncompliant_count:,}", "Reported violations, failures or overdue items"),
            ("Other / Pending", f"{other_count:,}", "Pending or unreported status"),
        ])

        compliance_left, compliance_right = st.columns([1.15, 1.85], gap="medium")
        with compliance_left:
            st.markdown("**Reporting activity & readiness**")
            report_count = len(reports) if reports is not None else 0
            reported_obligations = (
                int(reports["obligation_id"].dropna().astype(str).nunique())
                if report_count and "obligation_id" in reports.columns else 0
            )
            due_dates = pd.to_datetime(obligations.get(
                "next_submission_due_date", pd.Series(index=obligations.index, dtype="datetime64[ns]")
            ), errors="coerce")
            configured_due_dates = int(due_dates.notna().sum())
            r1, r2, r3 = st.columns(3)
            with r1:
                st.metric("Reports on file", f"{report_count:,}")
            with r2:
                st.metric("Obligations reported", f"{reported_obligations:,} / {len(obligations):,}")
            with r3:
                st.metric("Due dates configured", f"{configured_due_dates:,} / {len(obligations):,}")

            if report_count:
                st.success("Compliance reporting records are available.")
                recent_reports = reports.copy()
                if "submission_date" in recent_reports.columns:
                    recent_reports["submission_date"] = pd.to_datetime(recent_reports["submission_date"], errors="coerce")
                    recent_reports = recent_reports.sort_values("submission_date", ascending=False, na_position="last")
                recent_cols = [c for c in ["report_status", "reporting_period_start", "reporting_period_end", "submission_date", "submission_reference"] if c in recent_reports.columns]
                recent_reports = recent_reports[recent_cols].head(5)
                for date_col in ["reporting_period_start", "reporting_period_end", "submission_date"]:
                    if date_col in recent_reports.columns:
                        recent_reports[date_col] = pd.to_datetime(recent_reports[date_col], errors="coerce").dt.strftime("%d %b %Y")
                st.dataframe(recent_reports, use_container_width=True, hide_index=True, height=190)
            else:
                st.info("No compliance reports have been recorded yet. The obligations are configured, but report submissions have not been captured.")
                st.markdown(
                    """
                    <div style="background:#FFFFFF;border:1px solid #DCE7F2;border-radius:10px;padding:14px 16px;margin-top:8px;">
                      <div style="font-weight:650;color:#123B5D;margin-bottom:9px;">Recommended next steps</div>
                      <div style="display:flex;gap:10px;align-items:flex-start;margin:7px 0;color:#42566B;">
                        <span style="color:#D69B25;font-weight:700;">1</span>
                        <span>Assign an owner to each compliance obligation</span>
                      </div>
                      <div style="display:flex;gap:10px;align-items:flex-start;margin:7px 0;color:#42566B;">
                        <span style="color:#D69B25;font-weight:700;">2</span>
                        <span>Configure reporting due dates and frequency</span>
                      </div>
                      <div style="display:flex;gap:10px;align-items:flex-start;margin:7px 0;color:#42566B;">
                        <span style="color:#D69B25;font-weight:700;">3</span>
                        <span>Record submitted reports and supporting references</span>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with compliance_right:
            st.markdown("**Obligations by status**")
            fig = px.bar(
                compliance_summary, x="Obligations", y="Status", orientation="h", color="Status",
                color_discrete_map={
                    "Compliant": "#20A46B",
                    "Non-Compliant / Overdue": "#D94B55",
                    "Other / Pending": "#D69B25",
                },
                text="Obligations",
            )
            fig.update_traces(textposition="outside", cliponaxis=False, hovertemplate="%{y}: %{x} obligations<extra></extra>")
            fig.update_layout(
                height=260, margin=dict(l=8, r=28, t=4, b=8), showlegend=False,
                paper_bgcolor="white", plot_bgcolor="white",
                xaxis_title="Number of obligations", yaxis_title="",
                bargap=0.42,
            )
            fig.update_xaxes(dtick=1, rangemode="tozero", gridcolor="#E7EEF4")
            fig.update_yaxes(categoryorder="array", categoryarray=["Other / Pending", "Non-Compliant / Overdue", "Compliant"])
            st.plotly_chart(fig, use_container_width=True, key="exec_compliance_status")
    else:
        st.info("Compliance obligations are not configured for the selected properties. Compliance status is not inferred from energy usage.")

    st.markdown("### Contract Portfolio")
    if contracts is not None and not contracts.empty:
        days = pd.to_numeric(contracts.get("days_remaining", pd.Series(dtype=float)), errors="coerce")
        active = contracts["contract_status"].astype(str).str.lower().isin(["active","approved"])
        expiring = days.between(0,90)
        contract_count = contracts["contract_id"].nunique() if "contract_id" in contracts else len(contracts)
        active_count = contracts.loc[active, "contract_id"].nunique() if "contract_id" in contracts else int(active.sum())
        expiring_count = contracts.loc[expiring, "contract_id"].nunique() if "contract_id" in contracts else int(expiring.sum())
        annual_values = pd.to_numeric(contracts.get("estimated_annual_value", pd.Series(dtype=float)), errors="coerce").fillna(0)
        annual_value = contracts.assign(_annual_value=annual_values).drop_duplicates("contract_id")["_annual_value"].sum() if "contract_id" in contracts else annual_values.sum()
        metric_row([
            ("Contracts", f"{contract_count:,}", "Distinct contracts"),
            ("Active Contracts", f"{active_count:,}", "Distinct active contracts"),
            ("Expiring in 90 Days", f"{expiring_count:,}", "Distinct contracts with 0–90 days remaining"),
            ("Estimated Annual Value", fmt_usd(annual_value), "Distinct contract values"),
        ])
        contract_view = contracts.copy()
        contract_view["days_remaining"] = pd.to_numeric(contract_view["days_remaining"], errors="coerce")
        contract_view = contract_view.sort_values("days_remaining", na_position="last")
        st.dataframe(contract_view[[c for c in ["property_name","contract_number","contract_name","supplier_name","commodity_name","contract_status","contract_end_date","days_remaining","estimated_annual_value"] if c in contract_view.columns]].head(15),
                     use_container_width=True, hide_index=True)
    else:
        st.info("No contract portfolio records are available for the selected properties.")

    st.markdown("### Management Alerts & Actions")
    alerts = []
    if not budgets.empty and not energy.empty:
        approved = budgets[budgets["approval_status"].astype(str).str.lower().eq("approved")]
        for _, row in approved.iterrows():
            actual_match = energy[energy["property_id"].astype(str) == str(row["property_id"])]
            start = pd.to_datetime(row.get("period_start_date"), errors="coerce")
            end = pd.to_datetime(row.get("period_end_date"), errors="coerce")
            if pd.notna(start) and pd.notna(end):
                actual_match = actual_match[(actual_match["period_start_date"] >= start) & (actual_match["period_start_date"] <= end)]
            actual_value = float(actual_match["cost_amount"].sum()) if not actual_match.empty else 0.0
            budget_value = float(pd.to_numeric(pd.Series([row.get("budget_amount")]), errors="coerce").fillna(0).iloc[0])
            if budget_value > 0 and actual_value > budget_value:
                alerts.append({"Priority":"High","Property":row.get("property_name"),"Alert":"Approved energy budget exceeded","Detail":f"Actual {fmt_usd(actual_value)} vs budget {fmt_usd(budget_value)}"})
    if not contracts.empty:
        expiring_contracts = contracts[pd.to_numeric(contracts["days_remaining"], errors="coerce").between(0,90)]
        for _, row in expiring_contracts.iterrows():
            alerts.append({"Priority":"Medium","Property":row.get("property_name"),"Alert":"Contract expiring within 90 days","Detail":f"{row.get('contract_number','')} – {row.get('days_remaining')} days remaining"})
    if not obligations.empty and "next_submission_due_date" in obligations:
        due = obligations.copy()
        due["next_submission_due_date"] = pd.to_datetime(due["next_submission_due_date"], errors="coerce")
        due = due[due["next_submission_due_date"].between(pd.Timestamp.today().normalize(), pd.Timestamp.today().normalize()+pd.Timedelta(days=30))]
        for _, row in due.iterrows():
            alerts.append({"Priority":"Medium","Property":row.get("property_name"),"Alert":"Compliance submission due within 30 days","Detail":f"{row.get('standard_name','')} – {row.get('next_submission_due_date').date()}"})
    if alerts:
        alert_df = pd.DataFrame(alerts)
        priority_order = pd.Categorical(alert_df["Priority"], categories=["High","Medium","Low"], ordered=True)
        alert_df = alert_df.assign(_priority=priority_order).sort_values("_priority").drop(columns="_priority")
        st.dataframe(alert_df, use_container_width=True, hide_index=True)
    else:
        st.success("No budget overruns, upcoming contract expirations or near-term compliance deadlines were identified in the selected records.")


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


def render_contract_management(property_id, meters):
    scope = st.radio(
        "Contract Level", ["Property", "Meter"], horizontal=True,
        key=f"contract_scope_{property_id}",
    )
    expiry_days = st.selectbox(
        "Show Contracts Expiring Within", [30, 60, 90], index=0,
        format_func=lambda value: f"Next {value} Days",
        key=f"contract_expiry_window_{property_id}_{scope}",
    )
    try:
        contracts = get_contract_management_data(property_id, scope)
    except DataAccessError as exc:
        st.error("Could not load contract records. Confirm that the contract tables are deployed.")
        st.code(str(exc))
        contracts = pd.DataFrame()

    if not contracts.empty:
        contracts["days_remaining"] = pd.to_numeric(contracts["days_remaining"], errors="coerce")
        expiring = contracts[contracts["days_remaining"].between(0, expiry_days, inclusive="both")].copy()
        st.markdown(f"**Contracts Expiring Within {expiry_days} Days**")
        if expiring.empty:
            st.success(f"No {scope.lower()} contracts are expiring within the next {expiry_days} days.")
        else:
            expiring = expiring.sort_values("days_remaining")
            number_formats = {col: fmt_k for col in expiring.select_dtypes(include=["number"]).columns
                              if col.lower() != "days_remaining"}
            number_formats["days_remaining"] = "{:.0f}".format
            st.dataframe(expiring.style.format(number_formats, na_rep="—"),
                         use_container_width=True, hide_index=True)

        st.markdown("**Edit or Delete Contract**")
        labels = {
            str(row["link_id"]): (
                f"{row.get('contract_number','')} | {row.get('contract_name') or 'Contract'} "
                f"| {pd.to_datetime(row['contract_start_date']).date()} to "
                f"{pd.to_datetime(row['contract_end_date']).date()}"
            )
            for _, row in contracts.iterrows()
        }
        selected_link = st.selectbox(
            "Select contract to manage", list(labels.keys()),
            format_func=lambda value: labels[value],
            key=f"manage_contract_link_{property_id}_{scope}",
        )
        selected = contracts[contracts["link_id"].astype(str) == str(selected_link)].iloc[0]
        with st.form(f"edit_contract_form_{property_id}_{scope}_{selected_link}"):
            edit_number = st.text_input("Contract Number", value=str(selected.get("contract_number") or ""))
            edit_name = st.text_input("Contract Name", value=str(selected.get("contract_name") or ""))
            date_col1, date_col2 = st.columns(2)
            with date_col1:
                edit_start = st.date_input(
                    "Contract Start Date",
                    value=pd.to_datetime(selected["contract_start_date"]).date(),
                    key=f"edit_contract_start_{property_id}_{scope}_{selected_link}",
                )
            with date_col2:
                edit_end = st.date_input(
                    "Contract End Date",
                    value=pd.to_datetime(selected["contract_end_date"]).date(),
                    key=f"edit_contract_end_{property_id}_{scope}_{selected_link}",
                )
            save_edit = st.form_submit_button("Save Contract Changes", type="primary")
            if save_edit:
                if not edit_number.strip() or not edit_name.strip():
                    st.error("Contract Number and Contract Name are required.")
                elif edit_end < edit_start:
                    st.error("Contract end date cannot be earlier than its start date.")
                else:
                    try:
                        update_contract_link(scope, selected_link, edit_number.strip(),
                                             edit_name.strip(), edit_start, edit_end)
                        st.cache_data.clear()
                        st.success("Contract updated successfully.")
                        st.rerun()
                    except DataAccessError as exc:
                        st.error("Could not update the contract.")
                        st.code(str(exc))

        with st.expander("Delete selected contract"):
            st.warning("This removes the selected property/meter contract link. The shared contract record is deleted only when no other links use it.")
            confirm_delete = st.checkbox(
                "I confirm that I want to delete this contract link.",
                key=f"confirm_delete_contract_{property_id}_{scope}_{selected_link}",
            )
            if st.button("Delete Contract", type="secondary",
                         disabled=not confirm_delete,
                         key=f"delete_contract_{property_id}_{scope}_{selected_link}"):
                try:
                    delete_contract_link(scope, selected_link)
                    st.cache_data.clear()
                    st.success("Contract link deleted successfully.")
                    st.rerun()
                except DataAccessError as exc:
                    st.error("Could not delete the contract.")
                    st.code(str(exc))
    else:
        st.info(f"No {scope.lower()} contracts are currently linked to this property.")

    st.divider()
    st.markdown("**Add Contract**")
    st.caption(f"Create a new contract and link it to this {scope.lower()}.")
    try:
        vendors, commodities = get_contract_management_options()
    except DataAccessError as exc:
        st.error("Could not load supplier and commodity options.")
        st.code(str(exc))
        return
    if vendors.empty or commodities.empty:
        st.warning("Add active suppliers and commodities before creating a contract.")
        return

    vendor_options = dict(zip(vendors["vendor_id"].astype(str), vendors["vendor_name"].astype(str)))
    commodity_options = dict(zip(commodities["commodity_id"].astype(str), commodities["commodity_name"].astype(str)))
    with st.form(f"add_contract_form_{property_id}_{scope}", clear_on_submit=True):
        contract_number = st.text_input("Contract Number")
        contract_name = st.text_input("Contract Name")
        supplier_id = st.selectbox("Supplier", list(vendor_options.keys()),
                                   format_func=lambda value: vendor_options[value])
        commodity_id = st.selectbox("Commodity", list(commodity_options.keys()),
                                     format_func=lambda value: commodity_options[value])
        meter_id = None
        if scope == "Meter":
            if meters.empty:
                st.warning("No meters are available for this property.")
            else:
                meter_options = dict(zip(
                    meters["meter_id"].astype(str),
                    meters.apply(lambda row: f"{row.get('meter_number','')} | {row.get('meter_name') or row.get('commodity_name') or ''}", axis=1)
                ))
                meter_id = st.selectbox("Meter", list(meter_options.keys()),
                                        format_func=lambda value: meter_options[value])
        start_col, end_col = st.columns(2)
        with start_col:
            start_date = st.date_input("Contract Start Date", value=pd.Timestamp.today().date())
        with end_col:
            end_date = st.date_input("Contract End Date", value=(pd.Timestamp.today() + pd.Timedelta(days=365)).date())
        currency_code = st.selectbox("Currency", ["USD", "INR", "CAD", "GBP", "EUR"], index=0)
        auto_renewal = st.checkbox("Auto Renewal")
        renewal_notice_days = st.number_input("Renewal Notice Days", min_value=0, max_value=365, value=30, step=1)
        submitted = st.form_submit_button("Add Contract", type="primary")
        if submitted:
            if not contract_number.strip() or not contract_name.strip():
                st.error("Contract Number and Contract Name are required.")
            elif end_date <= start_date:
                st.error("Contract End Date must be after Contract Start Date.")
            elif scope == "Meter" and not meter_id:
                st.error("Select a meter for this contract.")
            else:
                try:
                    data_client().create_contract_link(
                        scope, property_id, meter_id, contract_number.strip(),
                        contract_name.strip(), supplier_id, commodity_id,
                        start_date, end_date, currency_code, auto_renewal,
                        int(renewal_notice_days),
                    )
                    st.cache_data.clear()
                    st.success("Contract created and linked successfully.")
                    st.rerun()
                except DataAccessError as exc:
                    st.error("Could not create the contract.")
                    st.code(str(exc))


def render_contract_portfolio():
    page_heading(
        "Contract Portfolio",
        "Complete contract register across all properties and meters, with duration and expiry monitoring.",
    )
    try:
        contracts = get_all_contracts()
    except DataAccessError as exc:
        st.error("Unable to load the complete contract register.")
        st.code(str(exc))
        return

    if contracts.empty:
        st.info("No contracts are currently available in the contract master.")
        return

    contracts = contracts.copy()
    contracts["contract_duration_days"] = pd.to_numeric(
        contracts["contract_duration_days"], errors="coerce"
    )
    # Recalculate remaining days from the displayed contract end date so that
    # KPI counts, filters and row highlighting all use the same date basis.
    # Use the application business date (India) rather than a potentially
    # different SQL session timezone or stale cached days_remaining value.
    today = pd.Timestamp.now(tz="Asia/Kolkata").date()
    end_dates = pd.to_datetime(contracts["contract_end_date"], errors="coerce").dt.date
    contracts["days_remaining"] = end_dates.apply(
        lambda end_date: (end_date - today).days if pd.notna(end_date) else float("nan")
    )
    contract_level = st.radio(
        "Contract Type",
        ["Property", "Meter"],
        horizontal=True,
        key="contract_portfolio_level",
    )
    if "linked_to" in contracts.columns:
        if contract_level == "Property":
            contracts = contracts[contracts["linked_to"].astype(str).str.lower() == "property"].copy()
        else:
            contracts = contracts[contracts["linked_to"].astype(str).str.lower().str.startswith("meter")].copy()

    if contracts.empty:
        st.info(f"No records are available for {contract_level.lower()}.")
        return

    total = len(contracts)
    expired_or_30 = int((contracts["days_remaining"] <= 30).sum())
    expiring_31_60 = int(contracts["days_remaining"].between(31, 60).sum())
    healthy = int((contracts["days_remaining"] > 60).sum())
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Contracts", f"{total:,}")
    k2.metric("Expired / Expiring Within 30 Days", f"{expired_or_30:,}")
    k3.metric("Expiring In 31–60 Days", f"{expiring_31_60:,}")
    k4.metric("More Than 60 Days", f"{healthy:,}")

    st.markdown("**Expiry Status Legend**")
    st.markdown(
        '<span style="background:#FDE2E2;color:#991B1B;padding:5px 10px;border-radius:6px;">'
        'Red: Expired / 0–30 Days</span> &nbsp; '
        '<span style="background:#FFEDD5;color:#9A3412;padding:5px 10px;border-radius:6px;">'
        'Orange: 31–60 Days</span> &nbsp; '
        '<span style="background:#DCFCE7;color:#166534;padding:5px 10px;border-radius:6px;">'
        'Green: More Than 60 Days</span>',
        unsafe_allow_html=True,
    )

    search_col, status_col = st.columns([2, 1])
    with search_col:
        search = st.text_input("Search Contracts", placeholder="Contract, supplier or property")
    with status_col:
        expiry_filter = st.selectbox(
            "Expiry Filter",
            ["All Contracts", "Expired / 0–30 Days", "31–60 Days", "More Than 60 Days"],
        )

    filtered = contracts.copy()
    if search.strip():
        term = search.strip().lower()
        searchable = ["contract_number", "contract_name", "supplier_name",
                      "commodity_name", "property_name", "linked_to"]
        mask = pd.Series(False, index=filtered.index)
        for col in searchable:
            if col in filtered.columns:
                mask |= filtered[col].fillna("").astype(str).str.lower().str.contains(
                    term, regex=False
                )
        filtered = filtered[mask]
    if expiry_filter == "Expired / 0–30 Days":
        filtered = filtered[filtered["days_remaining"] <= 30]
    elif expiry_filter == "31–60 Days":
        filtered = filtered[filtered["days_remaining"].between(31, 60)]
    elif expiry_filter == "More Than 60 Days":
        filtered = filtered[filtered["days_remaining"] > 60]

    display_cols = [
        "property_name", "contract_number", "contract_name", "supplier_name",
        "commodity_name", "linked_to", "contract_start_date", "contract_end_date",
        "contract_duration_days", "days_remaining", "auto_renewal_flag",
        "contract_status",
    ]
    display_cols = [col for col in display_cols if col in filtered.columns]
    display = filtered[display_cols].copy()
    for col in ["contract_start_date", "contract_end_date"]:
        if col in display.columns:
            display[col] = pd.to_datetime(display[col], errors="coerce").dt.strftime("%Y-%m-%d").fillna("—")

    rename = {
        "contract_number": "Contract Number",
        "contract_name": "Contract Name",
        "supplier_name": "Supplier",
        "commodity_name": "Commodity",
        "property_name": "Property Name",
        "linked_to": "Linked To",
        "contract_start_date": "Start Date",
        "contract_end_date": "End Date",
        "contract_duration_days": "Contract Duration (Days)",
        "days_remaining": "Days Remaining",
        "auto_renewal_flag": "Auto Renewal",
        "contract_status": "Contract Status",
    }
    display = display.rename(columns=rename)

    def property_expiry_style(row):
        days = row.get("Days Remaining")
        if pd.isna(days):
            color = "background-color: #E5E7EB; color: #374151;"
        elif days <= 30:
            color = "background-color: #FDE2E2; color: #991B1B; font-weight: 700;"
        elif days <= 60:
            color = "background-color: #FFEDD5; color: #9A3412; font-weight: 700;"
        else:
            color = "background-color: #DCFCE7; color: #166534; font-weight: 700;"
        return [
            color if col == "Property Name" else ""
            for col in row.index
        ]

    st.markdown(f"**{contract_level} ({len(display):,} Records)**")
    if display.empty:
        st.info("No contracts match the selected search and expiry filter.")
    else:
        formatters = {}
        for col in ["Contract Duration (Days)", "Days Remaining"]:
            if col in display.columns:
                formatters[col] = lambda value: "—" if pd.isna(value) else f"{int(value):,}"
        styled = display.style.apply(property_expiry_style, axis=1).format(
            formatters, na_rep="—"
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)
        st.download_button(
            "Download Complete Contract List CSV",
            filtered.to_csv(index=False).encode("utf-8"),
            file_name=f"energy360_{contract_level.lower().replace(' ', '_')}.csv",
            mime="text/csv",
            key="download_contract_portfolio",
        )


def _property_page_context(page_key):
    """Use the same property master and labels as Property Energy Management."""
    properties = get_property_list()
    if properties.empty:
        st.warning("No properties were found in dim_property.")
        return None, None
    property_ids = properties["property_id"].astype(str).tolist()
    def _label(pid):
        row = properties.loc[properties["property_id"].astype(str) == str(pid)].iloc[0]
        place = ", ".join(str(v) for v in [row.get("city"), row.get("state_code")]
                          if pd.notna(v) and str(v).strip())
        return f"{row.get('property_name', pid)} | {place} | {pid}"
    default_id = st.session_state.get("selected_energy_property", property_ids[0])
    if default_id not in property_ids:
        default_id = property_ids[0]
    selected_id = st.selectbox("Select property", property_ids,
        index=property_ids.index(default_id), format_func=_label,
        key=f"{page_key}_property_selector")
    st.session_state["selected_energy_property"] = selected_id
    prop = properties.loc[properties["property_id"].astype(str) == selected_id].iloc[0]
    st.markdown(
        f'<div class="property-detail-line"><span class="property-type">{html.escape(str(prop.get("property_type") or "Property"))}</span>'
        f'<span>{html.escape(str(prop.get("address_line_1") or ""))}</span>'
        f'<span>{html.escape(str(prop.get("city") or ""))}, {html.escape(str(prop.get("state_code") or ""))} '
        f'{html.escape(str(prop.get("postal_code") or ""))}</span></div>',
        unsafe_allow_html=True)
    return selected_id, prop


def render_energy_compliance():
    try:
        property_id, prop = _property_page_context("compliance")
        if property_id is None:
            return
        energy = get_property_energy(property_id)
    except DataAccessError as exc:
        st.error("Could not load property energy data.")
        st.code(str(exc))
        return

    # All compliance visuals below are scoped to the property selected above.
    # Do not show the all-properties portfolio table on this property-level page.
    st.subheader(f"Building Performance Overview — {prop.get('property_name', property_id)}")
    area = pd.to_numeric(pd.Series([prop.get("gross_area_sqft")]), errors="coerce").iloc[0]
    frame = energy.copy()
    if not frame.empty:
        for col in ["usage_quantity", "emissions_kg_co2e", "cost_amount"]:
            frame[col] = pd.to_numeric(frame[col], errors="coerce").fillna(0)
    water_mask = frame["commodity_name"].astype(str).str.contains("water", case=False, na=False) if not frame.empty else pd.Series(dtype=bool)
    water = frame.loc[water_mask] if not frame.empty else frame
    non_water = frame.loc[~water_mask] if not frame.empty else frame
    water_total = float(water["usage_quantity"].sum()) if not water.empty else 0.0
    water_units = ", ".join(sorted(water["usage_unit"].dropna().astype(str).unique())) if not water.empty else "No water records"
    emissions = float(frame["emissions_kg_co2e"].sum()) / 1000 if not frame.empty else 0.0
    metric_row([
        ("Energy Commodities", f"{non_water['commodity_id'].nunique():,}" if not non_water.empty else "0", "Distinct non-water commodities recorded."),
        ("Water Usage", f"{water_total:,.2f}", water_units),
        ("Emissions", f"{emissions:,.2f} tCO2e", "Converted from recorded kg CO2e."),
        ("Gross Building Area", f"{float(area):,.0f} sq. ft." if pd.notna(area) else "Not provided", "From dim_property."),
    ])
    st.subheader("Energy and Water Benchmarking Data")
    if frame.empty:
        st.info("No property energy usage is available for this property.")
    else:
        by_commodity = frame.groupby(["commodity_name", "usage_unit"], dropna=False, as_index=False).agg(
            usage=("usage_quantity", "sum"), emissions_kg_co2e=("emissions_kg_co2e", "sum"),
            cost=("cost_amount", "sum"))
        st.dataframe(by_commodity, use_container_width=True, hide_index=True)
        monthly = frame.copy()
        monthly["period_start_date"] = pd.to_datetime(monthly["period_start_date"], errors="coerce")
        monthly["reporting_month"] = monthly["period_start_date"].dt.to_period("M").astype(str)
        trend = monthly.groupby(["reporting_month", "commodity_name"], as_index=False)["usage_quantity"].sum()
        if not trend.empty:
            fig = px.line(trend, x="reporting_month", y="usage_quantity", color="commodity_name",
                          markers=True, title="Monthly Property Usage by Commodity")
            fig.update_layout(height=330, paper_bgcolor="white", plot_bgcolor="white",
                              margin=dict(l=10, r=10, t=45, b=10))
            st.plotly_chart(fig, use_container_width=True, key=f"compliance_usage_{property_id}")

    st.subheader("Compliance Obligations and Reporting")
    st.caption("Configure only verified municipal, state or regional requirements. Thresholds and deadlines must come from the applicable authority.")
    try:
        obligations = data_client().property_compliance_obligations(property_id)
        reports = data_client().property_compliance_reports(property_id)
        if obligations.empty:
            st.info("No compliance obligations are configured for this property yet. Deploy the compliance SQL tables and add verified standards and property obligations.")
        else:
            st.dataframe(obligations, use_container_width=True, hide_index=True)
        if not reports.empty:
            st.markdown("**Submitted / Prepared Reports**")
            st.dataframe(reports, use_container_width=True, hide_index=True)
    except DataAccessError as exc:
        st.warning("Compliance tracking tables are not available yet. Run sql/property_compliance_and_budgeting.sql.")
        st.caption(str(exc))
    if pd.isna(area) or float(area) <= 0:
        st.warning("Gross building area is missing. Add it to dim_property before calculating area-normalized performance indicators such as EUI.")


def render_budgets_savings():
    """Budget vs actual and target vs realized savings portfolio dashboard."""
    try:
        properties = get_property_list()
        if properties.empty:
            st.warning("No properties were found in dim_property.")
            return
        property_ids = properties["property_id"].astype(str).tolist()

        def _property_label(pid):
            if pid == "ALL":
                return "All Properties"
            row = properties.loc[properties["property_id"].astype(str) == str(pid)].iloc[0]
            place = ", ".join(str(v) for v in [row.get("city"), row.get("state_code")]
                              if pd.notna(v) and str(v).strip())
            return f"{row.get('property_name', pid)} | {place} | {pid}"

        default_id = st.session_state.get("selected_energy_property", property_ids[0])
        if default_id not in property_ids:
            default_id = property_ids[0]
        selection_options = property_ids
        selected_property = st.selectbox(
            "Select property", selection_options,
            index=selection_options.index(default_id),
            format_func=_property_label, key="budget_savings_property_selector"
        )
        st.session_state["selected_energy_property"] = selected_property
        prop = properties.loc[properties["property_id"].astype(str) == selected_property].iloc[0]
        st.markdown(
            f'<div class="property-detail-line"><span class="property-type">{html.escape(str(prop.get("property_type") or "Property"))}</span>'
            f'<span>{html.escape(str(prop.get("address_line_1") or ""))}</span>'
            f'<span>{html.escape(str(prop.get("city") or ""))}, {html.escape(str(prop.get("state_code") or ""))} '
            f'{html.escape(str(prop.get("postal_code") or ""))}</span></div>',
            unsafe_allow_html=True
        )

        budgets_all = data_client().property_budget_portfolio_data()
        savings_all = data_client().property_savings_portfolio_data()
        actual_frames = []
        for pid in [selected_property]:
            actual_frame = get_property_energy(pid)
            if actual_frame is not None and not actual_frame.empty:
                actual_frame = actual_frame.copy()
                actual_frame["property_id"] = pid
                prop_row = properties.loc[properties["property_id"].astype(str) == pid].iloc[0]
                actual_frame["property_name"] = prop_row.get("property_name", pid)
                actual_frames.append(actual_frame)
        actual_all = pd.concat(actual_frames, ignore_index=True) if actual_frames else pd.DataFrame()
    except DataAccessError as exc:
        st.error("Could not load budget, savings or actual energy data.")
        st.code(str(exc))
        return

    view = st.radio(
        "Budgets / Savings", ["Budgets", "Savings"], horizontal=True,
        key="budget_savings_view"
    )
    property_filter_ids = [selected_property]

    if view == "Budgets":
        st.subheader("Budget vs Actual Energy Cost")
        st.caption("Compare approved budgets with actual energy expenditure over the same property, commodity and reporting period.")

        budget_rows = budgets_all.copy()
        if not budget_rows.empty:
            budget_rows = budget_rows[budget_rows["property_id"].astype(str).isin(property_filter_ids)].copy()
        if not budget_rows.empty:
            budget_rows["fiscal_year"] = pd.to_numeric(budget_rows["fiscal_year"], errors="coerce")
            year_options = sorted(budget_rows["fiscal_year"].dropna().astype(int).unique().tolist())
        else:
            year_options = []
        f1, f2, f3 = st.columns(3)
        with f1:
            selected_year = st.selectbox("Fiscal Year", ["All"] + year_options, key="budget_fiscal_year")
        with f2:
            selected_commodity = st.selectbox(
                "Commodity", ["All"] + (sorted(actual_all["commodity_name"].dropna().astype(str).unique().tolist())
                if not actual_all.empty and "commodity_name" in actual_all else []),
                key="budget_commodity_filter"
            )
        with f3:
            selected_status = st.selectbox(
                "Budget Status", ["All", "Approved", "Submitted", "Draft", "Rejected"],
                key="budget_status_filter"
            )

        if not budget_rows.empty:
            if selected_year != "All":
                budget_rows = budget_rows[budget_rows["fiscal_year"] == int(selected_year)]
            if selected_status != "All":
                budget_rows = budget_rows[budget_rows["approval_status"].astype(str).str.title() == selected_status]
        actual = actual_all.copy()
        if not actual.empty:
            actual["cost_amount"] = pd.to_numeric(actual["cost_amount"], errors="coerce").fillna(0)
            actual["period_start_date"] = pd.to_datetime(actual["period_start_date"], errors="coerce")
            actual["period_end_date"] = pd.to_datetime(actual["period_end_date"], errors="coerce")
            if selected_commodity != "All":
                actual = actual[actual["commodity_name"].astype(str) == selected_commodity]

        comparison_rows = []
        for _, budget in budget_rows.iterrows():
            start_date = pd.to_datetime(budget.get("period_start_date"), errors="coerce")
            end_date = pd.to_datetime(budget.get("period_end_date"), errors="coerce")
            matched = actual[actual["property_id"].astype(str) == str(budget["property_id"])] if not actual.empty else actual
            if pd.notna(start_date) and pd.notna(end_date) and not matched.empty:
                matched = matched[(matched["period_start_date"] >= start_date) & (matched["period_end_date"] <= end_date)]
            if pd.notna(budget.get("commodity_id")) and str(budget.get("commodity_id")).strip():
                matched = matched[matched["commodity_id"].astype(str) == str(budget["commodity_id"])]
            elif selected_commodity != "All" and not matched.empty:
                matched = matched[matched["commodity_name"].astype(str) == selected_commodity]
            actual_cost = float(matched["cost_amount"].sum()) if not matched.empty else 0.0
            budget_amount = float(pd.to_numeric(pd.Series([budget.get("budget_amount")]), errors="coerce").fillna(0).iloc[0])
            row = budget.to_dict()
            row.update({
                "actual_cost": actual_cost,
                "variance_amount": actual_cost - budget_amount,
                "remaining_budget": budget_amount - actual_cost,
                "utilization_pct": actual_cost / budget_amount * 100 if budget_amount > 0 else None,
            })
            comparison_rows.append(row)
        comparison = pd.DataFrame(comparison_rows)

        approved = comparison[
            comparison["approval_status"].astype(str).str.lower().eq("approved")
        ] if not comparison.empty and "approval_status" in comparison else pd.DataFrame()
        total_budget = float(pd.to_numeric(approved.get("budget_amount", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
        total_actual = float(pd.to_numeric(approved.get("actual_cost", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
        remaining = total_budget - total_actual
        utilization = total_actual / total_budget * 100 if total_budget > 0 else 0
        metric_row([
            ("Approved Budget", fmt_usd(total_budget), "Approved budgets only"),
            ("Actual Cost", fmt_usd(total_actual), "Matched reporting periods"),
            ("Remaining / (Overrun)", fmt_usd(remaining), "Negative means over budget"),
            ("Budget Utilization", f"{utilization:,.1f}%", "Actual cost / approved budget"),
        ])

        if comparison.empty:
            st.info("No budget records match the selected filters. Add a budget or change the filters.")
        else:
            st.subheader("Monthly Budget vs Actual Cost")
            # Allocate budget evenly over the months in its reporting period.
            monthly_budget_rows = []
            for _, budget_row in budget_rows.iterrows():
                start = pd.to_datetime(budget_row.get("period_start_date"), errors="coerce")
                end = pd.to_datetime(budget_row.get("period_end_date"), errors="coerce")
                amount = pd.to_numeric(pd.Series([budget_row.get("budget_amount")]), errors="coerce").fillna(0).iloc[0]
                if pd.isna(start) or pd.isna(end) or end < start:
                    continue
                months = pd.date_range(start=start.to_period("M").to_timestamp(),
                                       end=end.to_period("M").to_timestamp(), freq="MS")
                if len(months):
                    monthly_share = float(amount) / len(months)
                    monthly_budget_rows.extend({"Month": month, "Budget": monthly_share} for month in months)
            monthly_budget = (pd.DataFrame(monthly_budget_rows).groupby("Month", as_index=False)["Budget"].sum()
                              if monthly_budget_rows else pd.DataFrame(columns=["Month", "Budget"]))
            monthly_actual = pd.DataFrame(columns=["Month", "Actual Cost"])
            if not actual.empty:
                actual_trend = actual.dropna(subset=["period_start_date"]).copy()
                if not actual_trend.empty and not budget_rows.empty:
                    budget_starts = pd.to_datetime(budget_rows["period_start_date"], errors="coerce").dropna()
                    budget_ends = pd.to_datetime(budget_rows["period_end_date"], errors="coerce").dropna()
                    if not budget_starts.empty and not budget_ends.empty:
                        actual_trend = actual_trend[
                            (actual_trend["period_start_date"] >= budget_starts.min())
                            & (actual_trend["period_start_date"] <= budget_ends.max())
                        ]
                if not actual_trend.empty:
                    actual_trend["Month"] = actual_trend["period_start_date"].dt.to_period("M").dt.to_timestamp()
                    monthly_actual = actual_trend.groupby("Month", as_index=False)["cost_amount"].sum()
                    monthly_actual = monthly_actual.rename(columns={"cost_amount": "Actual Cost"})
            monthly_trend = pd.merge(monthly_budget, monthly_actual, on="Month", how="outer").fillna(0).sort_values("Month")
            if not monthly_trend.empty:
                fig = px.line(monthly_trend, x="Month", y=["Budget", "Actual Cost"], markers=True,
                              labels={"value": "Amount (USD)", "Month": "Month", "variable": "Measure"},
                              title=f"Monthly Budget vs Actual Cost — {prop.get('property_name', selected_property)}")
                fig.update_layout(height=370, paper_bgcolor="white", plot_bgcolor="white",
                                  margin=dict(l=10, r=10, t=55, b=10), legend_title_text="")
                fig.update_traces(line_width=3, marker_size=7)
                fig.update_yaxes(title="Amount (USD)", gridcolor="#E7EEF4", tickprefix="$")
                fig.update_xaxes(title="", tickformat="%b %Y")
                st.plotly_chart(format_plotly_numbers(fig), use_container_width=True, key="budget_monthly_trend")
            else:
                st.info("No monthly budget or actual-cost records are available for this property.")

            # Build a true commodity-level comparison. A budget with no
            # commodity_id covers all commodities, so allocate it across
            # commodities in proportion to their actual cost for the same
            # property and budget period. This keeps the allocated budgets
            # additive and avoids assigning the full budget to every commodity.
            commodity_rows = []
            for _, budget_row in budget_rows.iterrows():
                start_date = pd.to_datetime(budget_row.get("period_start_date"), errors="coerce")
                end_date = pd.to_datetime(budget_row.get("period_end_date"), errors="coerce")
                matched_all = actual_all.copy()
                if not matched_all.empty:
                    matched_all["cost_amount"] = pd.to_numeric(matched_all["cost_amount"], errors="coerce").fillna(0)
                    matched_all["period_start_date"] = pd.to_datetime(matched_all["period_start_date"], errors="coerce")
                    matched_all["period_end_date"] = pd.to_datetime(matched_all["period_end_date"], errors="coerce")
                    if pd.notna(start_date) and pd.notna(end_date):
                        matched_all = matched_all[
                            (matched_all["period_start_date"] >= start_date)
                            & (matched_all["period_end_date"] <= end_date)
                        ]
                budget_commodity_id = budget_row.get("commodity_id")
                if pd.notna(budget_commodity_id) and str(budget_commodity_id).strip():
                    matched_all = matched_all[
                        matched_all["commodity_id"].astype(str) == str(budget_commodity_id)
                    ] if not matched_all.empty else matched_all
                if not matched_all.empty:
                    commodity_actual = matched_all.groupby("commodity_name", dropna=False, as_index=False)["cost_amount"].sum()
                    commodity_actual["Commodity"] = commodity_actual["commodity_name"].fillna("Unclassified")
                    if selected_commodity != "All":
                        commodity_actual = commodity_actual[commodity_actual["Commodity"].astype(str) == selected_commodity]
                    total_actual_for_all_commodities = float(matched_all["cost_amount"].sum())
                    budget_amount_for_period = float(pd.to_numeric(
                        pd.Series([budget_row.get("budget_amount")]), errors="coerce"
                    ).fillna(0).iloc[0])
                    for _, commodity_row in commodity_actual.iterrows():
                        commodity_cost = float(commodity_row["cost_amount"])
                        if pd.notna(budget_commodity_id) and str(budget_commodity_id).strip():
                            allocated_budget = budget_amount_for_period
                        elif total_actual_for_all_commodities > 0:
                            allocated_budget = budget_amount_for_period * commodity_cost / total_actual_for_all_commodities
                        else:
                            allocated_budget = 0.0
                        commodity_rows.append({
                            "Commodity": str(commodity_row["Commodity"]),
                            "Budget": allocated_budget,
                            "Actual Cost": commodity_cost,
                        })
                elif pd.notna(budget_commodity_id) and str(budget_commodity_id).strip():
                    label_rows = actual_all.loc[
                        actual_all["commodity_id"].astype(str) == str(budget_commodity_id), "commodity_name"
                    ] if not actual_all.empty else pd.Series(dtype=str)
                    commodity_label = str(label_rows.iloc[0]) if not label_rows.empty else str(budget_commodity_id)
                    if selected_commodity == "All" or selected_commodity == commodity_label:
                        commodity_rows.append({
                            "Commodity": commodity_label,
                            "Budget": float(budget_row.get("budget_amount") or 0),
                            "Actual Cost": 0.0,
                        })
            commodity_df = pd.DataFrame(commodity_rows)
            if not commodity_df.empty:
                commodity_df = commodity_df.groupby("Commodity", as_index=False)[["Budget", "Actual Cost"]].sum()
                st.subheader("Budget vs Actual by Commodity")
                commodity_long = commodity_df.melt(
                    id_vars="Commodity", value_vars=["Budget", "Actual Cost"],
                    var_name="Measure", value_name="Amount"
                )
                fig = px.bar(
                    commodity_long, x="Commodity", y="Amount", color="Measure",
                    barmode="group", category_orders={"Commodity": sorted(commodity_df["Commodity"].astype(str).unique())},
                    labels={"Commodity": "Commodity", "Amount": "Amount (USD)", "Measure": "Comparison"},
                    title="Budget vs Actual Cost by Commodity",
                )
                fig.update_layout(
                    height=370, paper_bgcolor="white", plot_bgcolor="white",
                    margin=dict(l=10, r=10, t=50, b=20), legend_title_text="",
                    xaxis_title="Commodity", yaxis_title="Amount (USD)",
                )
                fig.update_yaxes(gridcolor="#E7EEF4", tickprefix="$")
                st.plotly_chart(
                    format_plotly_numbers(fig), use_container_width=True,
                    key="budget_commodity_comparison",
                )
            else:
                st.info("No commodity-level budget or actual-cost records are available for the selected filters.")

            display = comparison.copy()
            display["status"] = display["utilization_pct"].apply(
                lambda x: "Over Budget" if pd.notna(x) and x > 100 else ("Near Limit" if pd.notna(x) and x >= 90 else "Under Budget")
            )
            display = display.rename(columns={
                "property_name":"Property","budget_name":"Budget Name","fiscal_year":"Fiscal Year",
                "commodity_id":"Commodity ID","period_start_date":"Period Start Date",
                "period_end_date":"Period End Date","budget_amount":"Budget Amount",
                "actual_cost":"Actual Cost","variance_amount":"Variance",
                "remaining_budget":"Remaining Budget","utilization_pct":"Budget Utilization (%)",
                "approval_status":"Approval Status","status":"Performance Status"
            })
            preferred = ["Property","Budget Name","Fiscal Year","Commodity ID","Period Start Date","Period End Date",
                         "Budget Amount","Actual Cost","Variance","Remaining Budget","Budget Utilization (%)",
                         "Approval Status","Performance Status"]
            display = display[[c for c in preferred if c in display.columns]]
            st.subheader("Budget Comparison Details")
            st.dataframe(display, use_container_width=True, hide_index=True)
            st.download_button("Download Budget Comparison CSV", display.to_csv(index=False).encode("utf-8"),
                               file_name="energy360_budget_vs_actual.csv", mime="text/csv",
                               key="download_budget_comparison")

        with st.expander("＋ Add Budget", expanded=False):
            with st.form("add_property_budget_portfolio"):
                add_property_id = selected_property
                st.caption(_property_label(add_property_id))
                left, right = st.columns(2)
                with left:
                    budget_name = st.text_input("Budget Name")
                    fiscal_year = st.number_input("Fiscal Year", min_value=2000, max_value=2100, value=2026, step=1)
                    budget_amount = st.number_input("Budget Amount (USD)", min_value=0.0, value=0.0, step=1000.0)
                with right:
                    commodity_choices = ["All Commodities"] + (sorted(actual_all.loc[actual_all["property_id"].astype(str)==str(add_property_id),"commodity_id"].dropna().astype(str).unique().tolist()) if not actual_all.empty else [])
                    commodity_id = st.selectbox("Commodity", commodity_choices)
                    period_start = st.date_input("Period Start")
                    period_end = st.date_input("Period End")
                submitted = st.form_submit_button("Save Budget", type="primary")
                if submitted:
                    if not budget_name.strip() or period_end < period_start or budget_amount <= 0:
                        st.error("Enter a budget name, valid period and amount greater than zero.")
                    else:
                        try:
                            data_client().create_property_budget(add_property_id,budget_name,int(fiscal_year),
                                None if commodity_id=="All Commodities" else commodity_id,
                                period_start,period_end,budget_amount)
                            st.cache_data.clear()
                            st.success("Budget saved as Draft. Submit and approve it before it contributes to approved-budget KPIs.")
                            st.rerun()
                        except DataAccessError as exc:
                            st.error(str(exc))

    else:
        st.subheader("Target Savings vs Realized Savings")
        st.caption("Compare planned initiative savings with recorded realized savings. Realized values should be supported by measurement and verification.")
        initiatives = savings_all.copy()
        if not initiatives.empty:
            initiatives = initiatives[initiatives["property_id"].astype(str).isin(property_filter_ids)].copy()
        f1, f2 = st.columns(2)
        with f1:
            category_options = ["All"] + (sorted(initiatives["initiative_category"].dropna().astype(str).unique().tolist()) if not initiatives.empty else [])
            selected_category = st.selectbox("Initiative Category", category_options, key="savings_category_filter")
        with f2:
            selected_initiative_status = st.selectbox(
                "Initiative Status", ["All","Planned","In Progress","Completed","On Hold"],
                key="savings_status_filter"
            )
        if not initiatives.empty:
            if selected_category != "All":
                initiatives = initiatives[initiatives["initiative_category"].astype(str) == selected_category]
            if selected_initiative_status != "All":
                initiatives = initiatives[initiatives["initiative_status"].astype(str).str.title() == selected_initiative_status]
            for col in ["target_savings_amount","realized_savings_amount"]:
                initiatives[col] = pd.to_numeric(initiatives[col],errors="coerce").fillna(0)
            initiatives["achievement_pct"] = initiatives.apply(
                lambda row: row["realized_savings_amount"]/row["target_savings_amount"]*100
                if row["target_savings_amount"]>0 else 0,axis=1
            )
        target_total = float(initiatives["target_savings_amount"].sum()) if not initiatives.empty else 0.0
        realized_total = float(initiatives["realized_savings_amount"].sum()) if not initiatives.empty else 0.0
        opportunity = target_total-realized_total
        achievement = realized_total/target_total*100 if target_total>0 else 0
        metric_row([
            ("Target Savings",fmt_usd(target_total),"Planned initiative savings"),
            ("Realized Savings",fmt_usd(realized_total),"Recorded achieved savings"),
            ("Remaining Opportunity",fmt_usd(opportunity),"Target minus realized"),
            ("Savings Achievement",f"{achievement:,.1f}%","Realized / target savings"),
        ])
        if initiatives.empty:
            st.info("No savings initiatives match the selected filters.")
        else:
            st.subheader("Monthly Target vs Realized Savings")
            st.caption(
                "Monthly trend is phased from each initiative's cumulative target and realized amounts "
                "across its active period. It is an estimated allocation, not measured monthly savings; "
                "use monthly measurement records when available for verified reporting."
            )
            monthly_rows = []
            trend_today = pd.Timestamp.now().normalize()
            for _, initiative in initiatives.iterrows():
                start = pd.to_datetime(initiative.get("start_date"), errors="coerce")
                finish = pd.to_datetime(initiative.get("target_completion_date"), errors="coerce")
                target_amount = float(pd.to_numeric(
                    pd.Series([initiative.get("target_savings_amount")]), errors="coerce"
                ).fillna(0).iloc[0])
                realized_amount = float(pd.to_numeric(
                    pd.Series([initiative.get("realized_savings_amount")]), errors="coerce"
                ).fillna(0).iloc[0])
                if pd.isna(start):
                    continue
                start_month = start.to_period("M").to_timestamp()
                end_month = (finish.to_period("M").to_timestamp()
                             if pd.notna(finish) and finish >= start
                             else trend_today.to_period("M").to_timestamp())
                target_months = pd.date_range(start_month, end_month, freq="MS")
                if len(target_months) == 0:
                    continue
                target_per_month = target_amount / len(target_months)
                elapsed_end = min(end_month, trend_today.to_period("M").to_timestamp())
                realized_months = pd.date_range(start_month, elapsed_end, freq="MS")
                realized_per_month = realized_amount / len(realized_months) if len(realized_months) else 0.0
                for month in target_months:
                    monthly_rows.append({
                        "Month": month,
                        "Target Savings": target_per_month,
                        "Realized Savings": realized_per_month if month in realized_months else 0.0,
                    })
            if monthly_rows:
                monthly_savings = pd.DataFrame(monthly_rows).groupby("Month", as_index=False)[
                    ["Target Savings", "Realized Savings"]
                ].sum().sort_values("Month")
                fig = px.line(
                    monthly_savings, x="Month",
                    y=["Target Savings", "Realized Savings"],
                    markers=True,
                    labels={"value": "Savings (USD)", "Month": "Month", "variable": "Measure"},
                    title="Monthly Target vs Realized Savings",
                )
                fig.update_layout(
                    height=370, paper_bgcolor="white", plot_bgcolor="white",
                    margin=dict(l=10, r=10, t=50, b=15), legend_title_text="",
                )
                fig.update_traces(line_width=3, marker_size=7)
                fig.update_yaxes(title="Savings (USD)", gridcolor="#E7EEF4", tickprefix="$")
                fig.update_xaxes(title="", tickformat="%b %Y")
                st.plotly_chart(
                    format_plotly_numbers(fig), use_container_width=True,
                    key="savings_monthly_trend",
                )
                monthly_display = monthly_savings.copy()
                monthly_display["Month"] = monthly_display["Month"].dt.strftime("%b %Y")
                for amount_col in ["Target Savings", "Realized Savings"]:
                    monthly_display[amount_col] = monthly_display[amount_col].round(2)
                st.dataframe(monthly_display, use_container_width=True, hide_index=True)
                st.download_button(
                    "Download Monthly Savings Trend CSV",
                    monthly_display.to_csv(index=False).encode("utf-8"),
                    file_name="energy360_monthly_savings_trend.csv",
                    mime="text/csv",
                    key="download_monthly_savings_trend",
                )
            else:
                st.info("Monthly savings trend cannot be calculated because initiative start dates are missing.")

            st.subheader("Savings by Initiative Category")
            by_category = initiatives.groupby("initiative_category",as_index=False).agg(
                target_savings=("target_savings_amount","sum"),
                realized_savings=("realized_savings_amount","sum"))
            category_long = by_category.melt(id_vars="initiative_category",
                value_vars=["target_savings","realized_savings"],var_name="measure",value_name="amount")
            category_long["measure"] = category_long["measure"].map(
                {"target_savings":"Target Savings","realized_savings":"Realized Savings"})
            fig = px.bar(category_long,x="initiative_category",y="amount",color="measure",barmode="group",
                labels={"initiative_category":"Initiative Category","amount":"Savings (USD)","measure":"Comparison"},
                title="Target vs Realized Savings by Category")
            fig.update_layout(height=320,paper_bgcolor="white",plot_bgcolor="white",
                margin=dict(l=10,r=10,t=50,b=10),legend_title_text="")
            st.plotly_chart(fig,use_container_width=True,key="savings_category_comparison")

            st.subheader("Initiative Status Distribution")
            status_counts = initiatives.groupby("initiative_status",as_index=False).size()
            fig = px.pie(status_counts,names="initiative_status",values="size",hole=0.55,
                         title="Initiatives by Status")
            fig.update_layout(height=300,paper_bgcolor="white",margin=dict(l=10,r=10,t=45,b=10))
            st.plotly_chart(fig,use_container_width=True,key="savings_status_distribution")

            display = initiatives.rename(columns={
                "property_name":"Property","initiative_id":"Initiative ID","initiative_name":"Initiative Name",
                "initiative_category":"Category","target_savings_amount":"Target Savings",
                "realized_savings_amount":"Realized Savings","achievement_pct":"Achievement (%)",
                "initiative_status":"Status","start_date":"Start Date",
                "target_completion_date":"Target Completion Date","currency_code":"Currency"
            })
            preferred = ["Property","Initiative ID","Initiative Name","Category","Target Savings",
                         "Realized Savings","Achievement (%)","Currency","Status","Start Date","Target Completion Date"]
            display = display[[c for c in preferred if c in display.columns]]
            st.subheader("Savings Initiative Comparison")
            st.dataframe(display,use_container_width=True,hide_index=True)
            st.download_button("Download Savings Comparison CSV",display.to_csv(index=False).encode("utf-8"),
                file_name="energy360_target_vs_realized_savings.csv",mime="text/csv",
                key="download_savings_comparison")

        with st.expander("＋ Add Savings Initiative",expanded=False):
            with st.form("add_savings_initiative_portfolio"):
                add_property_id=selected_property
                st.caption(_property_label(add_property_id))
                initiative_name=st.text_input("Initiative Name")
                category=st.selectbox("Category",["Lighting","HVAC","Controls","Water","Renewables","Operations","Other"])
                target_savings=st.number_input("Target Savings (USD)",min_value=0.0,value=0.0,step=500.0)
                realized_savings=st.number_input("Realized Savings (USD)",min_value=0.0,value=0.0,step=100.0)
                status=st.selectbox("Status",["Planned","In Progress","Completed","On Hold"])
                notes=st.text_area("Notes")
                submitted=st.form_submit_button("Save Initiative",type="primary")
                if submitted:
                    if not initiative_name.strip() or target_savings<=0:
                        st.error("Enter an initiative name and a positive target savings amount.")
                    else:
                        try:
                            data_client().create_savings_initiative(add_property_id,initiative_name,category,
                                target_savings,realized_savings,status,notes)
                            st.cache_data.clear()
                            st.success("Savings initiative saved.")
                            st.rerun()
                        except DataAccessError as exc:
                            st.error(str(exc))


def render_property_energy_management():
    # The global hero banner already displays the page title and description.
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

    # Use Streamlit's native searchable dropdown so search and selection
    # happen in one control (type a property name, city, state or ID).
    selected_id = st.selectbox(
        "Select property",
        property_ids,
        index=property_ids.index(default_id),
        format_func=property_label,
        key="property_energy_selector",
    )
    st.session_state["selected_energy_property"] = selected_id
    prop = properties.loc[properties["property_id"].astype(str) == selected_id].iloc[0]

    # Load only the datasets needed for the property summary. Operational
    # tables are fetched on demand when their section is selected below.
    try:
        energy = get_property_energy(selected_id)
        meters = get_property_meters(selected_id)
        accounts = get_property_accounts(selected_id)
        contracts = get_property_contracts(selected_id)
    except DataAccessError as exc:
        st.error("Could not load this property's summary records.")
        st.code(str(exc))
        return

    area = prop.get("gross_area_sqft")
    area_text = f"{float(area):,.2f} gross sq. ft." if pd.notna(area) else "Area not provided"
    st.markdown(
        f'<div class="property-detail-line">'
        f'<span class="property-type">{prop.get("property_type") or "Property"}</span>'
        f'<span>{prop.get("address_line_1") or ""}</span>'
        f'<span>{prop.get("city") or ""}, {prop.get("state_code") or ""} '
        f'{prop.get("postal_code") or ""}</span>'
        f'<span>{area_text}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="property-meta-line">'
        f'<span><strong>Property ID</strong> {selected_id}</span>'
        f'<span><strong>Status</strong> {prop.get("operating_status") or "Not specified"}</span>'
        f'<span><strong>Manager</strong> {prop.get("property_manager") or "Not assigned"}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    total_cost = float(energy["cost_amount"].fillna(0).sum()) if not energy.empty else 0.0
    meter_count = int(meters["meter_id"].nunique()) if not meters.empty else 0
    account_count = int(accounts["utility_account_id"].nunique()) if not accounts.empty else 0
    contract_count = int(contracts["contract_id"].nunique()) if not contracts.empty else 0
    metric_row([
        ("Energy Cost", "$" + fmt_k(total_cost, 0), "Sum of recorded property energy costs."),
        ("Meters", f"{meter_count:,}", None),
        ("Utility Accounts", f"{account_count:,}", None),
        ("Supplier Contracts", f"{contract_count:,}", None),
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

        view_mode = st.radio(
            "",
            ["By commodity", "Monthly by commodity"],
            horizontal=True,
            key=f"property_chart_view_{selected_id}",
        )

        commodities = totals["commodity_name"].dropna().astype(str).tolist()
        chosen = None
        selected_energy = energy.iloc[0:0].copy()
        if view_mode == "Monthly by commodity":
            st.markdown("**Select commodity**")
            chosen = st.selectbox(
                "Select a commodity", commodities,
                key=f"property_commodity_trend_{selected_id}",
                label_visibility="collapsed",
            )
            selected_energy = energy[energy["commodity_name"] == chosen].copy()

        left, right = st.columns(2, gap="large")
        with left:
            if view_mode == "By commodity":
                st.markdown('<div class="property-chart-section-heading">Energy Usage By Commodity</div>', unsafe_allow_html=True)
                usage_data = totals[["commodity_name", "usage_unit", "total_usage"]].copy()
                usage_data["commodity_label"] = (
                    usage_data["commodity_name"].astype(str)
                    + " (" + usage_data["usage_unit"].astype(str) + ")"
                )
                fig = px.bar(
                    usage_data, x="commodity_label", y="total_usage",
                    color="commodity_name", title="Total Usage By Commodity",
                )
                fig.update_layout(
                    showlegend=False, height=360, margin=dict(l=10, r=10, t=45, b=10),
                    paper_bgcolor="white", plot_bgcolor="white",
                )
                fig.update_yaxes(title="Usage (native unit)", gridcolor="#E7EEF4")
                fig.update_xaxes(title="")
                st.plotly_chart(
                    format_plotly_numbers(fig), use_container_width=True,
                    key=f"property_usage_by_commodity_{selected_id}",
                )
            else:
                st.markdown(f"**Monthly consumption trend — {chosen}**")
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
                        height=360, margin=dict(l=10, r=10, t=45, b=10),
                        paper_bgcolor="white", plot_bgcolor="white",
                    )
                    fig.update_yaxes(title=unit, gridcolor="#E7EEF4")
                    fig.update_xaxes(title="")
                    st.plotly_chart(
                        format_plotly_numbers(fig), use_container_width=True,
                        key=f"property_usage_{selected_id}_{chosen}",
                    )
                else:
                    st.info(f"No monthly usage records are available for {chosen}.")

        with right:
            if view_mode == "By commodity":
                st.markdown('<div class="property-chart-section-heading">Energy Cost By Commodity</div>', unsafe_allow_html=True)
                cost_data = totals[["commodity_name", "total_cost"]].copy()
                fig = px.bar(
                    cost_data, x="commodity_name", y="total_cost",
                    color="commodity_name", title="Total Cost By Commodity (USD)",
                )
                fig.update_layout(
                    showlegend=False, height=360, margin=dict(l=10, r=10, t=45, b=10),
                    paper_bgcolor="white", plot_bgcolor="white",
                )
                fig.update_yaxes(title="USD", gridcolor="#E7EEF4")
                fig.update_xaxes(title="")
                st.plotly_chart(
                    format_plotly_numbers(fig), use_container_width=True,
                    key=f"property_cost_by_commodity_{selected_id}",
                )
            else:
                st.markdown(f"**Monthly energy cost — {chosen}**")
                monthly_cost = (
                    selected_energy.groupby("period_start_date", as_index=False)["cost_amount"]
                    .sum().sort_values("period_start_date")
                )
                if not monthly_cost.empty:
                    fig = px.line(
                        monthly_cost, x="period_start_date", y="cost_amount",
                        markers=True, title=f"{chosen} monthly cost (USD)",
                    )
                    fig.update_traces(line_color="#0AA6BD", line_width=3, marker_size=7)
                    fig.update_layout(
                        height=360, margin=dict(l=10, r=10, t=45, b=10),
                        paper_bgcolor="white", plot_bgcolor="white",
                    )
                    fig.update_yaxes(title="USD", gridcolor="#E7EEF4")
                    fig.update_xaxes(title="")
                    st.plotly_chart(
                        format_plotly_numbers(fig), use_container_width=True,
                        key=f"property_cost_{selected_id}_{chosen}",
                    )
                else:
                    st.info(f"No monthly cost records are available for {chosen}.")

    st.subheader("Property Operations")
    operation_sections = [
        "Meters & Readings", "Meter Contracts", "Utility Accounts", "Vendors",
        "Rate Details", "Property Contracts", "Bills", "Procurement", "Contract Management",
    ]
    active_section = st.radio("Property operations", operation_sections,
                              horizontal=True, label_visibility="collapsed",
                              key=f"property_ops_section_{selected_id}")
    if active_section == "Contract Management":
        render_contract_management(selected_id, meters)
    elif active_section == "Meters & Readings":
        render_crud_entity("meters", "Meters", selected_id)
        render_crud_entity("meter_readings", "Meter Readings", selected_id)
    elif active_section == "Meter Contracts":
        render_crud_entity("meter_contracts", "Meter Contracts", selected_id)
    elif active_section == "Utility Accounts":
        render_crud_entity("accounts", "Utility Accounts", selected_id)
    elif active_section == "Vendors":
        render_crud_entity("vendors", "Vendors", selected_id)
    elif active_section == "Rate Details":
        render_crud_entity("rate_classes", "Rate Classes", selected_id)
        render_crud_entity("rate_schedules", "Rate Schedules", selected_id)
        render_crud_entity("rate_components", "Rate Components", selected_id)
    elif active_section == "Property Contracts":
        render_crud_entity("property_contracts", "Property Contracts", selected_id)
    elif active_section == "Bills":
        render_crud_entity("bills", "Utility Bills", selected_id)
        render_crud_entity("bill_lines", "Bill Line Items", selected_id)
    elif active_section == "Procurement":
        render_crud_entity("purchase_orders", "Purchase Orders", selected_id)
        render_crud_entity("purchase_order_lines", "Purchase Order Lines", selected_id)
        render_crud_entity("vendor_invoices", "Vendor Invoices", selected_id)
        render_crud_entity("vendor_invoice_lines", "Vendor Invoice Lines", selected_id)
        render_crud_entity("vendor_payments", "Vendor Payments", selected_id)



# ------------------------- Global Energy 360 AI Assistant -------------------------
AI_PAGE_MAP = {
    "Executive Dashboard": "Executive Dashboard",
    "Property Energy Management": "Property Energy Management",
    "Energy Compliance": "Energy Compliance",
    "Budgets / Savings": "Budgets / Savings",
    "Contract Portfolio": "Contract Portfolio",
    "Energy Generation": "Energy Generation",
    "Transmission & Distribution": "Transmission & Distribution",
    "Energy Consumption": "Energy Consumption",
    "Asset Management": "Asset Management",
    "Forecasting & Analytics": "Forecasting & Analytics",
    "Sustainability": "Sustainability",
    "Energy Cost & Trading": "Energy Cost & Trading",
    "Geographical Analysis": "Geographical Analysis",
    "Reports & Insights": "Reports & Insights",
}


def _ai_frame_snapshot(frame, limit=8):
    """Keep model context compact and grounded in rows returned by SQL."""
    if frame is None:
        return {"row_count": 0, "columns": [], "sample": []}
    if not isinstance(frame, pd.DataFrame):
        return {"value": str(frame)[:1000]}
    if frame.empty:
        return {"row_count": 0, "columns": list(frame.columns), "sample": []}
    sample = json.loads(frame.head(limit).to_json(orient="records", date_format="iso"))
    return {"row_count": int(len(frame)), "columns": list(frame.columns), "sample": sample}


def _ai_safe_load(context, label, loader):
    try:
        context[label] = _ai_frame_snapshot(loader())
    except Exception as exc:
        context[label] = {"unavailable": str(exc)[:300]}


def _build_ai_page_context(page, start_d=None, end_d=None, state="All US"):
    """Fetch only the data relevant to the page the user is viewing."""
    context = {"current_page": page, "business_date": str(pd.Timestamp.now(tz="Asia/Kolkata").date())}
    try:
        properties = get_property_list()
        context["property_master"] = _ai_frame_snapshot(properties, limit=12)
    except Exception as exc:
        properties = pd.DataFrame()
        context["property_master"] = {"unavailable": str(exc)[:300]}

    selected_property = st.session_state.get("selected_energy_property")
    context["selected_property_id"] = selected_property
    if selected_property and not properties.empty:
        selected = properties[properties["property_id"].astype(str) == str(selected_property)]
        if not selected.empty:
            context["selected_property"] = json.loads(selected.head(1).to_json(orient="records", date_format="iso"))[0]

    if page == "Executive Dashboard":
        energy_parts = []
        for pid in (properties["property_id"].astype(str).tolist() if not properties.empty else []):
            try:
                part = get_property_energy(pid)
                if part is not None and not part.empty:
                    part = part.copy()
                    part["property_id"] = pid
                    energy_parts.append(part)
            except Exception:
                continue
        context["property_energy_usage_all"] = _ai_frame_snapshot(
            pd.concat(energy_parts, ignore_index=True) if energy_parts else pd.DataFrame(), limit=16
        )
        _ai_safe_load(context, "budgets_all_properties", lambda: data_client().property_budget_portfolio_data())
        _ai_safe_load(context, "savings_all_properties", lambda: data_client().property_savings_portfolio_data())
        _ai_safe_load(context, "contracts_all_properties", get_all_contracts)
        obligations, reports = [], []
        for pid in (properties["property_id"].astype(str).tolist() if not properties.empty else []):
            try:
                ob = data_client().property_compliance_obligations(pid)
                rp = data_client().property_compliance_reports(pid)
                if ob is not None and not ob.empty:
                    ob = ob.copy()
                    ob["property_id"] = pid
                    obligations.append(ob)
                if rp is not None and not rp.empty:
                    rp = rp.copy()
                    rp["property_id"] = pid
                    reports.append(rp)
            except Exception:
                continue
        context["compliance_obligations_all_properties"] = _ai_frame_snapshot(
            pd.concat(obligations, ignore_index=True) if obligations else pd.DataFrame(), limit=12
        )
        context["compliance_reports_all_properties"] = _ai_frame_snapshot(
            pd.concat(reports, ignore_index=True) if reports else pd.DataFrame(), limit=10
        )

    elif page == "Property Energy Management" and selected_property:
        for label, loader in [
            ("property_energy_usage", lambda: get_property_energy(selected_property)),
            ("meters", lambda: get_property_meters(selected_property)),
            ("utility_accounts", lambda: get_property_accounts(selected_property)),
            ("vendors", lambda: get_property_vendors(selected_property)),
            ("rates", lambda: get_property_rates(selected_property)),
            ("property_contracts", lambda: get_property_contracts(selected_property)),
            ("meter_contracts", lambda: get_property_meter_contracts(selected_property)),
            ("utility_bills", lambda: get_property_bills(selected_property)),
            ("procurement", lambda: get_property_procurement(selected_property)),
        ]:
            _ai_safe_load(context, label, loader)

    elif page == "Energy Compliance" and selected_property:
        _ai_safe_load(context, "property_energy_usage", lambda: get_property_energy(selected_property))
        _ai_safe_load(context, "compliance_obligations", lambda: data_client().property_compliance_obligations(selected_property))
        _ai_safe_load(context, "compliance_reports", lambda: data_client().property_compliance_reports(selected_property))

    elif page == "Budgets / Savings" and selected_property:
        _ai_safe_load(context, "property_energy_usage", lambda: get_property_energy(selected_property))
        try:
            budgets = data_client().property_budget_portfolio_data()
            savings = data_client().property_savings_portfolio_data()
            if not budgets.empty:
                budgets = budgets[budgets["property_id"].astype(str) == str(selected_property)]
            if not savings.empty:
                savings = savings[savings["property_id"].astype(str) == str(selected_property)]
            context["property_budgets"] = _ai_frame_snapshot(budgets)
            context["property_savings_initiatives"] = _ai_frame_snapshot(savings)
        except Exception as exc:
            context["budget_savings_unavailable"] = str(exc)[:300]

    elif page == "Contract Portfolio":
        _ai_safe_load(context, "contract_register", get_all_contracts)

    else:
        try:
            if start_d is None or end_d is None:
                start_d, end_d = date_bounds()
            if start_d is not None and end_d is not None:
                dashboard = get_dashboard_data(start_d, end_d, state)
                page_keys = {
                    "Energy Generation": ["generation", "by_source", "by_state"],
                    "Transmission & Distribution": ["grid", "grid_by_state"],
                    "Energy Consumption": ["consumption", "trend"],
                    "Asset Management": ["capacity"],
                    "Forecasting & Analytics": ["trend", "generation", "consumption"],
                    "Sustainability": ["emissions", "generation"],
                    "Energy Cost & Trading": ["costs"],
                    "Geographical Analysis": ["by_state", "grid_by_state"],
                    "Reports & Insights": ["generation", "consumption", "grid", "emissions", "costs"],
                }
                for key in page_keys.get(page, ["trend"]):
                    context[key] = _ai_frame_snapshot(dashboard.get(key), limit=10)
                context["reporting_period"] = {"start_date": str(start_d), "end_date": str(end_d), "state": state}
        except Exception as exc:
            context["operational_data_unavailable"] = str(exc)[:300]
    return context


def _ask_energy360_ai(page, question, history, start_d=None, end_d=None, state="All US"):
    """Call a Databricks Model Serving chat endpoint with the app workspace identity."""
    endpoint = (
        os.getenv("ENERGY360_AI_ENDPOINT")
        or os.getenv("DATABRICKS_CHAT_ENDPOINT")
        or os.getenv("DATABRICKS_AI_ENDPOINT")
    )
    if not endpoint:
        raise RuntimeError(
            "AI model endpoint is not configured. Add ENERGY360_AI_ENDPOINT to the Databricks App environment "
            "using the name of an enabled Databricks Model Serving chat endpoint."
        )
    from databricks.sdk import WorkspaceClient
    context = _build_ai_page_context(page, start_d, end_d, state)
    allowed_pages = list(AI_PAGE_MAP.keys())
    system_message = (
        "You are Energy 360 AI Assistant for an enterprise property energy application. "
        "Use only the supplied page context for factual figures, statuses, dates and recommendations. "
        "Never invent missing energy measurements, compliance outcomes, contract values, budgets, savings or deadlines. "
        "Say clearly when records are missing. A sample contains only a subset of rows; distinguish it from total row_count. "
        "Answer questions about the current page directly. If the question clearly belongs to a different app page, "
        "do not answer using unrelated data: set route_to to that exact page and briefly explain why. "
        "If unrelated to all pages, set route_to null and explain the supported Energy 360 topics. "
        "Return ONLY valid JSON with keys answer (string) and route_to (string or null). "
        "Allowed route_to values: " + ", ".join(allowed_pages) + ". "
        "Current page: " + page + ". Current page context JSON: " + json.dumps(context, default=str)[:18000]
    )
    messages = [{"role": "system", "content": system_message}]
    for item in history[-8:]:
        if item.get("role") in ("user", "assistant"):
            messages.append({"role": item["role"], "content": item.get("content", "")[:2500]})
    messages.append({"role": "user", "content": question[:2500]})
    response = WorkspaceClient().serving_endpoints.query(
        name=endpoint, messages=messages, max_tokens=900, temperature=0.15
    )
    payload = response.as_dict() if hasattr(response, "as_dict") else response
    if not isinstance(payload, dict):
        raise RuntimeError("The model endpoint returned an unsupported response format.")
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError("The configured endpoint returned no chat response. Confirm it is a chat-completion endpoint.")
    message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
    content = message.get("content", "") if isinstance(message, dict) else ""
    if isinstance(content, list):
        content = " ".join(str(part.get("text", "")) if isinstance(part, dict) else str(part) for part in content)
    raw = str(content).strip()
    fence = chr(96) * 3
    if raw.startswith(fence):
        raw = raw.split("\n", 1)[-1].rsplit(fence, 1)[0].strip()
    try:
        result = json.loads(raw)
    except Exception:
        result = {"answer": raw, "route_to": None}
    route = result.get("route_to")
    if route not in AI_PAGE_MAP:
        route = None
    return {"answer": str(result.get("answer", "I couldn't answer from the available records.")), "route_to": route}


def render_energy360_ai_assistant(page, start_d=None, end_d=None, state="All US"):
    """Render the same floating AI assistant on every app page."""
    if "energy360_ai_messages" not in st.session_state:
        st.session_state["energy360_ai_messages"] = []
    with st.container(key="energy360_ai_launcher"):
        with st.popover("AI Assistant", icon=":material/smart_toy:", help="Ask questions about Energy 360"):
            st.markdown("#### Energy 360 AI Assistant")
            st.caption(f"Currently viewing: {page}")
            visible_messages = st.session_state["energy360_ai_messages"][-12:]
            for idx, item in enumerate(visible_messages):
                with st.chat_message(item.get("role", "assistant")):
                    st.markdown(item.get("content", ""))
                    if item.get("role") == "assistant" and item.get("route_to") and item.get("route_to") != page:
                        target = item["route_to"]
                        st.button(
                            f"Go to {target}",
                            key=f"energy360_ai_route_{idx}_{target}",
                            on_click=_choose_page,
                            args=(target,),
                            use_container_width=True,
                        )
            with st.form("energy360_ai_chat_form", clear_on_submit=True):
                question = st.text_input("Ask a question", placeholder="e.g. Which property has the highest energy cost?")
                submitted = st.form_submit_button("Send", use_container_width=True)
            if submitted and question.strip():
                history = st.session_state["energy360_ai_messages"][-8:]
                st.session_state["energy360_ai_messages"].append({"role": "user", "content": question.strip()})
                try:
                    result = _ask_energy360_ai(page, question.strip(), history, start_d, end_d, state)
                    st.session_state["energy360_ai_messages"].append({
                        "role": "assistant", "content": result["answer"], "route_to": result["route_to"]
                    })
                    if result["route_to"] and result["route_to"] != page:
                        st.session_state["active_energy_page"] = result["route_to"]
                except Exception as exc:
                    st.session_state["energy360_ai_messages"].append({
                        "role": "assistant", "content": "I couldn't reach the AI service. " + str(exc)
                    })
                st.rerun()


# ------------------------- App entry -------------------------
try:
    # Restore the Property Operations context when a row action link is opened.
    _crud_page = st.query_params.get("crud_page", "")
    _crud_property = st.query_params.get("crud_property", "")
    _crud_section = st.query_params.get("crud_section", "")
    if _crud_page:
        st.session_state["active_energy_page"] = _crud_page
    if _crud_property:
        st.session_state["selected_energy_property"] = _crud_property
    if _crud_property and _crud_section:
        st.session_state[f"property_ops_section_{_crud_property}"] = _crud_section

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
    elif page=="Energy Compliance": render_energy_compliance()
    elif page=="Budgets / Savings": render_budgets_savings()
    elif page=="Contract Portfolio": render_contract_portfolio()
    elif page=="Asset Management": render_assets(start_d,end_d,state)
    elif page=="Forecasting & Analytics": render_forecasting(start_d,end_d,state)
    elif page=="Sustainability": render_sustainability(start_d,end_d,state)
    elif page=="Energy Cost & Trading": render_costs(start_d,end_d,state)
    elif page=="Geographical Analysis": render_geography(start_d,end_d)
    elif page=="Reports & Insights": render_reports(start_d,end_d,state)
    render_energy360_ai_assistant(page, start_d, end_d, state)
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
