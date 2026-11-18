import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from services.databricks_data import EnergyData, DataAccessError

st.set_page_config(page_title="Energy 360 | Enterprise Energy Management", page_icon="⚡", layout="wide")

# ------------------------- Styling -------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"]{font-family:Inter,Arial,sans-serif}
.stApp{background:#F5F8FB;color:#18324B}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#123C5D,#0F304B)}
[data-testid="stSidebar"] *{color:#F4F8FC}
.block-container{padding-top:1.5rem;padding-bottom:2.5rem;max-width:1600px}
h1,h2,h3{color:#183B59;letter-spacing:-.35px}
div[data-testid="stMetric"]{background:#fff;border:1px solid #E5EDF4;padding:15px 17px;border-radius:13px;box-shadow:0 3px 12px rgba(22,55,82,.035)}
div[data-testid="stMetricLabel"]{color:#718399;font-size:.82rem;font-weight:650}
div[data-testid="stMetricValue"]{color:#173A59;font-size:1.6rem;font-weight:800}
.panel{background:#fff;border:1px solid #E5EDF4;border-radius:13px;padding:14px 17px;margin-bottom:14px}
div[data-testid="stDataFrame"]{border:1px solid #E5EDF4;border-radius:10px}
.small-note{font-size:.78rem;color:#8293A5}
</style>
""", unsafe_allow_html=True)

CATALOG = os.getenv("ENERGY360_CATALOG", "energy")
SCHEMA = os.getenv("ENERGY360_SCHEMA", "energy")

PAGES = [
    "Executive Dashboard", "Energy Generation", "Transmission & Distribution",
    "Energy Consumption", "Asset Management", "Forecasting & Analytics",
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

def fmt_num(v, digits=1):
    return "—" if v is None or pd.isna(v) else f"{v:,.{digits}f}"

def fmt_usd(v):
    return "—" if v is None or pd.isna(v) else f"${v:,.0f}"

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
    st.dataframe(df.head(limit), use_container_width=True, hide_index=True)
    st.download_button(
        f"Download {title} CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f"energy360_{title.lower().replace(' ','_')}.csv",
        mime="text/csv",
        key=f"download_{title.replace(' ','_')}",
    )

def filters():
    try:
        min_d, max_d = date_bounds()
    except Exception:
        min_d, max_d = None, None
    with st.sidebar:
        st.markdown("## ⚡ ENERGY 360")
        st.caption("ENTERPRISE ENERGY MANAGEMENT")
        st.divider()
        page = st.radio("NAVIGATION", PAGES, label_visibility="collapsed")
        st.divider()
        st.markdown("### Dashboard filters")
        if min_d and max_d:
            date_range = st.date_input("Date range", value=(min_d, max_d), min_value=min_d, max_value=max_d)
            if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
                start_d, end_d = date_range
            else:
                start_d, end_d = min_d, max_d
        else:
            start_d, end_d = None, None
            st.caption("Date dimension bounds unavailable.")
        try:
            states = data_client().state_names()
        except Exception:
            states = []
        state_options = ["All US"] + states
        selected_state = st.selectbox("State", state_options)
        st.divider()
        st.caption(f"Catalog: {CATALOG}")
        st.caption(f"Schema: {SCHEMA}")
        if st.button("↻ Refresh data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    return page, start_d, end_d, selected_state

def render_dashboard(start_d, end_d, state):
    page_heading("Energy Overview", "United States generation, consumption, grid, asset and sustainability performance.")
    data = get_dashboard_data(start_d, end_d, state)
    gen, cons, grid, plants, emissions, costs = (data[k] for k in ["generation","consumption","grid","capacity","emissions","costs"])

    generated = float(gen["generation_mwh"].sum()) if not gen.empty else None
    consumed = float(cons["consumption_mwh"].sum()) if not cons.empty else None
    availability = float(grid["gridavailabilitypct"].mean()) if not grid.empty else None
    capacity = float(plants["installedcapacitymw"].sum()) if not plants.empty else None
    co2 = float(emissions["emissions_tco2e"].sum()) if not emissions.empty else None
    cost = float(costs["totalcost_inr"].sum()) if not costs.empty else None

    metric_row([
        ("Energy Generated", f"{generated/1000:,.2f} GWh" if generated is not None else "—", "SUM(fact_generation.generation_mwh) / 1,000"),
        ("Energy Consumed", f"{consumed/1000:,.2f} GWh" if consumed is not None else "—", "SUM(fact_consumption.consumption_mwh) / 1,000"),
        ("Grid Availability", f"{availability:,.2f}%" if availability is not None else "—", "Average gridavailabilitypct"),
    ])
    metric_row([
        ("Installed Capacity", f"{capacity/1000:,.2f} GW" if capacity is not None else "—", "SUM(dim_power_plant.installedcapacitymw) / 1,000"),
        ("Carbon Emissions", f"{co2:,.2f} tCO₂e" if co2 is not None else "—", "SUM(fact_carbon_emissions.emissions_tco2e)"),
        ("Energy Cost", fmt_usd(cost), "SUM(fact_energy_cost.totalcost_inr)"),
    ])

    st.divider()
    c1,c2 = st.columns([1.5,1])
    with c1:
        st.subheader("Generation vs consumption")
        trend = data["trend"]
        if not trend.empty:
            long = trend.melt(id_vars="date", value_vars=["generation_mwh","consumption_mwh"], var_name="metric", value_name="mwh")
            long["metric"] = long["metric"].map({"generation_mwh":"Generation","consumption_mwh":"Consumption"})
            fig = px.line(long, x="date", y="mwh", color="metric", markers=True,
                          color_discrete_map={"Generation":"#1976D2","Consumption":"#25A55B"})
            fig.update_layout(height=340, margin=dict(l=5,r=5,t=15,b=5), plot_bgcolor="white", paper_bgcolor="white", legend_title="")
            st.plotly_chart(fig,use_container_width=True)
        else:
            st.info("No generation/consumption trend rows for this filter.")
    with c2:
        st.subheader("Generation by energy source")
        by_source = data["by_source"]
        if not by_source.empty:
            fig = px.pie(by_source,names="energysource",values="generation_mwh",hole=.62,
                         color_discrete_sequence=["#1976D2","#25A55B","#53B6D8","#F3B53F","#8A8FE8"])
            fig.update_layout(height=340,margin=dict(l=5,r=5,t=15,b=5),legend_title="")
            st.plotly_chart(fig,use_container_width=True)
        else:
            st.info("No source-wise generation data available.")

    c3,c4 = st.columns([1,1])
    with c3:
        st.subheader("State-wise generation")
        states = data["by_state"]
        if not states.empty and {"latitude","longitude"}.issubset(states.columns):
            fig = px.scatter_geo(states,lat="latitude",lon="longitude",size="generation_mwh",
                                 color="generation_mwh",hover_name="statename",
                                 hover_data={"generation_mwh":":,.0f","latitude":False,"longitude":False},
                                 scope="usa",color_continuous_scale=["#BFE7D0","#1976D2"])
            fig.update_geos(fitbounds="locations",visible=False,showland=True,landcolor="#F2F7FB",
                            showcountries=True,countrycolor="#CBD8E5",showocean=True,oceancolor="#FFFFFF")
            fig.update_layout(height=360,margin=dict(l=0,r=0,t=0,b=0),paper_bgcolor="white")
            st.plotly_chart(fig,use_container_width=True)
        else:
            st.info("State map requires coordinates in dim_state and matching state keys in generation.")
    with c4:
        st.subheader("Grid performance by state")
        if not data["grid_by_state"].empty:
            fig = px.bar(data["grid_by_state"],x="statename",y="gridavailabilitypct",
                         color="gridavailabilitypct",color_continuous_scale=["#F3B53F","#25A55B"])
            fig.update_layout(height=360,margin=dict(l=5,r=5,t=10,b=5),xaxis_title="",yaxis_title="Availability (%)",coloraxis_showscale=False)
            st.plotly_chart(fig,use_container_width=True)
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
        fig=px.bar(agg,x="energysource",y="generation_mwh",color="energysource",title="Generation by source")
        st.plotly_chart(fig,use_container_width=True)
    with b:
        trend=df.groupby("date",as_index=False)[["generation_mwh","targetgeneration_mwh"]].sum()
        fig=px.line(trend,x="date",y=["generation_mwh","targetgeneration_mwh"],markers=True,title="Actual vs target")
        st.plotly_chart(fig,use_container_width=True)
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
        st.plotly_chart(px.pie(sector,names="consumersector",values="consumption_mwh",hole=.55,title="Consumption by sector"),use_container_width=True)
    with b:
        trend=df.groupby("date",as_index=False)["consumption_mwh"].sum()
        st.plotly_chart(px.line(trend,x="date",y="consumption_mwh",markers=True,title="Consumption trend"),use_container_width=True)
    show_df(df,"Consumption detail")

def render_grid(start_d,end_d,state):
    page_heading("Transmission & Distribution","Grid availability, transmission losses, outages, SAIDI and peak load factor.")
    df=get_grid_data(start_d,end_d,state)
    if df.empty:
        st.info("No grid records for the selected filters."); return
    metric_row([("Grid Availability",f"{df.gridavailabilitypct.mean():.2f}%",None),
                ("Transmission Loss",f"{df.transmissionlosspct.mean():.2f}%",None),
                ("Outages",f"{df.outagecount.sum():,.0f}",None),
                ("SAIDI",f"{df.saidi_hours.mean():.2f} hours",None)])
    a,b=st.columns(2)
    with a:
        st.plotly_chart(px.line(df.groupby("date",as_index=False)["gridavailabilitypct"].mean(),x="date",y="gridavailabilitypct",markers=True,title="Grid availability trend"),use_container_width=True)
    with b:
        st.plotly_chart(px.bar(df.groupby("statename",as_index=False)["transmissionlosspct"].mean(),x="statename",y="transmissionlosspct",title="Average transmission loss by state"),use_container_width=True)
    show_df(df,"Grid performance detail")

def render_assets(start_d,end_d,state):
    page_heading("Asset Management","Asset availability, health score, downtime, maintenance and operational status.")
    df=get_asset_data(start_d,end_d,state)
    if df.empty:
        st.info("No asset performance records for the selected filters."); return
    metric_row([("Average Availability",f"{df.availabilitypct.mean():.2f}%",None),
                ("Average Health Score",f"{df.assethealthscore.mean():.2f}",None),
                ("Downtime",f"{df.downtimehours.sum():,.1f} hours",None),
                ("Maintenance Events",f"{df.maintenanceevents.sum():,.0f}",None)])
    a,b=st.columns(2)
    with a:
        st.plotly_chart(px.bar(df.groupby("assetname",as_index=False)["assethealthscore"].mean(),x="assetname",y="assethealthscore",color="assethealthscore",title="Asset health score"),use_container_width=True)
    with b:
        status=df.groupby("operationalstatus",as_index=False).size()
        st.plotly_chart(px.pie(status,names="operationalstatus",values="size",hole=.55,title="Operational status"),use_container_width=True)
    show_df(df,"Asset performance detail")

def render_sustainability(start_d,end_d,state):
    page_heading("Sustainability","Carbon emissions, emission factors and carbon reduction targets.")
    df=get_sustainability_data(start_d,end_d,state)
    if df.empty:
        st.info("No carbon emissions records for the selected filters."); return
    metric_row([("Emissions",f"{df.emissions_tco2e.sum():,.2f} tCO₂e",None),
                ("Energy Generated",f"{df.energygenerated_mwh.sum():,.2f} MWh",None),
                ("Avg Emission Factor",f"{df.emissionfactor_tco2e_per_mwh.mean():.4f} tCO₂e/MWh",None),
                ("Carbon Reduction Target",f"{df.carbonreductiontargetpct.mean():.2f}%",None)])
    a,b=st.columns(2)
    with a:
        st.plotly_chart(px.bar(df.groupby("energysource",as_index=False)["emissions_tco2e"].sum(),x="energysource",y="emissions_tco2e",color="energysource",title="Emissions by energy source"),use_container_width=True)
    with b:
        trend=df.groupby("date",as_index=False)["emissions_tco2e"].sum()
        st.plotly_chart(px.line(trend,x="date",y="emissions_tco2e",markers=True,title="Emissions trend"),use_container_width=True)
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
        st.plotly_chart(px.bar(df.groupby("energysource",as_index=False)["totalcost_inr"].sum(),x="energysource",y="totalcost_inr",color="energysource",title="Cost by source"),use_container_width=True)
    with b:
        st.plotly_chart(px.line(df.groupby("date",as_index=False)[["totalcost_inr","revenue_inr"]].sum(),x="date",y=["totalcost_inr","revenue_inr"],markers=True,title="Cost vs revenue"),use_container_width=True)
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
        st.plotly_chart(fig,use_container_width=True)
    show_df(df,"State-wise energy summary")

def render_forecasting(start_d,end_d,state):
    page_heading("Forecasting & Analytics","Forecast-ready actual energy trends using your current source tables.")
    st.info("Your supplied schema does not include a forecast fact table or prediction columns. This page currently displays historical actuals; a Databricks ML forecast can be added when you approve a forecast table/model.")
    df=get_generation_data(start_d,end_d,state)
    if not df.empty:
        trend=df.groupby("date",as_index=False)["generation_mwh"].sum()
        st.plotly_chart(px.line(trend,x="date",y="generation_mwh",markers=True,title="Historical generation (actuals only)"),use_container_width=True)
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
    page,start_d,end_d,state=filters()
    if page=="Executive Dashboard": render_dashboard(start_d,end_d,state)
    elif page=="Energy Generation": render_generation(start_d,end_d,state)
    elif page=="Transmission & Distribution": render_grid(start_d,end_d,state)
    elif page=="Energy Consumption": render_consumption(start_d,end_d,state)
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
