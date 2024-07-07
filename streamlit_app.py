import altair as alt
import pandas as pd
import streamlit as st
import pydeck as pdk
import plotly.express as px
import folium
from folium.plugins import Draw
from folium import Popup
from streamlit_folium import st_folium
import geopandas as gpd

# Remove redundant import
# import plotly.express as px
# import glob

# Initialize Streamlit app layout
st.set_page_config(page_title="UFN", page_icon="🌎", layout="wide")
st.title("Utah Geological Survey-Utah Flux Network")

ufn_url = "https://geology.utah.gov/utah-flux-network"
st.write(f"[The Utah Flux Network]({ufn_url})")

param_select = {
    'Air Temperature': [['TA_1_1_1', 'TA_1_4_1', 'TA_1_2_1', 'TA_1_3_1', 'T_SONIC'], "Temperature (°C)", "Temperature Sensor"],
    'Soil Temperature': [['TS_1_1_1', 'TS_1_2_1', 'TS_3_1_1'], "Temperature (°C)", "Temperature Sensor"],
    'Relative Humidity': [['RH_1_1_1', 'RH_1_2_1', 'RH_1_3_1'], "Relative Humidity (%)", "RH Sensor"],
    'Energy Components': [['LE', 'H', 'G', 'NETRAD'], 'Energy (W/m²)', 'Energy Component']
}

@st.cache_data
def load_data():
    df = pd.read_parquet('data/all_data.parquet')
    df.reset_index(inplace=True)
    df.replace(-9999, None, inplace=True)
    return df

@st.cache_data
def filter_station_data(data, selected_site, sel_variables):
    plotparam = [parm for parm in sel_variables if parm in data.columns]
    df = data.set_index(['datetime_start'])
    df = df[df['station'] == selected_site][plotparam]
    return df, plotparam

@st.cache_data
def resample_three_hours(df):
    return df.resample('3h').mean()

@st.cache_resource
def create_violin_plot(data_df, param='Air Temperature'):
    stat_temp = data_df.reset_index().melt(id_vars=['datetime_start'])
    fig = px.violin(stat_temp, y="value", x="variable", box=True, hover_data=stat_temp.columns,
                    labels={"value": param_select[param][1], "variable": param_select[param][2]},
                    title=param)
    return fig

@st.cache_resource
def create_energy_balance_plot(df, selected_months):
    df_energy = df[['G', 'LE', 'NETRAD', 'H']].dropna()
    df_energy['Rn - G'] = df_energy['NETRAD'] - df_energy['G']
    df_energy['LE + H'] = df_energy['H'] + df_energy['LE']
    ebal = df_energy[df_energy.index.month_name().isin(selected_months)]
    ebal = ebal[ebal.index.hour.isin(range(6, 21))]
    fig = px.scatter(ebal, y="LE + H", x="Rn - G", trendline="ols")
    return fig

# Load data and station information
data = load_data()
stations_file_path = 'data/stations.geojson'
sites = gpd.read_file(stations_file_path)
sitelist = list(sites['Site ID'].values)

def create_map(sites):
    m = folium.Map(location=[sites.centroid.y.mean(), sites.centroid.x.mean()], zoom_start=6)
    folium.GeoJson(sites, marker=folium.Marker(icon=folium.Icon(icon='star')), 
                   popup=folium.GeoJsonPopup(fields=["Site ID"])).add_to(m)
    return m

def get_site_name(map_data):
    if map_data['last_object_clicked']:
        lat = map_data['last_object_clicked']['lat']
        site = sites[sites.geometry.y == lat]['Site ID'].values[0]
        return site
    return None

# Create a Folium map and display it in the sidebar
st.sidebar.header("Map")
folium_map = create_map(sites)
with st.sidebar:
    map_data = st_folium(folium_map, width=300, height=500)

amfluxurl = "https://ameriflux.lbl.gov/sites/siteinfo/"
clicked_site = get_site_name(map_data)
selected_site = clicked_site if clicked_site else 'US-UTB'

selected_site = st.selectbox("Select a site:", options=sitelist, index=sitelist.index(selected_site))

if selected_site:
    site_info = sites[sites['Site ID'] == selected_site]
    if not site_info.empty:
        snm = site_info['Name'].values[0]
        st.subheader(f"[{selected_site}: {snm}]({amfluxurl}{selected_site})")
    else:
        st.write("No additional information available for this site.")
    vio_parm = st.selectbox("Parameter", param_select.keys(), index=0)
else:
    vio_param = 'Air Temperature'

col1, col2 = st.columns(2)

with col1:
    if selected_site in data['station'].unique():
        sel_variables = param_select[vio_parm][0]
        data_df, plotparam = filter_station_data(data, selected_site, sel_variables)
        df3 = resample_three_hours(data_df)
        fig = px.line(df3, x=df3.index, y=plotparam, title=f"{vio_parm} at {selected_site}")
        st.plotly_chart(fig)

with col2:
    if selected_site in data['station'].unique():
        molist = list(data_df.index.month_name().unique())
        fig = create_violin_plot(data_df, vio_parm)
        st.plotly_chart(fig)
    else:
        st.write("Select a point on the map to view data")
        molist = data['datetime_start'].dt.month_name().unique()

cont = st.container()
allvals = st.checkbox("Select All", key=23)
sel_opts = cont.multiselect("Select one or more options:", molist, molist if allvals else [], key=54)

ebal_data, _ = filter_station_data(data, selected_site, ['LE', 'H', 'G', 'NETRAD'])
fig3 = create_energy_balance_plot(ebal_data, sel_opts)
st.plotly_chart(fig3)