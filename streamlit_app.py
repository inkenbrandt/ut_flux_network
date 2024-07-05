import altair as alt
import pandas as pd
import streamlit as st
import pydeck as pdk
import plotly.express as px
import folium
from folium.plugins import Draw
from folium import Popup
from streamlit_folium import st_folium
import os
import plotly.express as px
import glob
import geopandas as gpd
# from sqlalchemy import create_engine
# import postgresql
# import psycopg2

# engine = create_engine(f"postgresql+psycopg2://{user}:{pw}@{ip}:5432/groundwater")

# Show the page title and description.
# Initialize Streamlit app layout
param_select = {'Air Temperature':[['TA_1_1_1','TA_1_4_1','TA_1_2_1','TA_1_3_1','T_SONIC',],
                                "Temperature (°C)","Temperature Sensor",
                                ],
                'Soil Temperature':[['TS_1_1_1','TS_1_2_1','TS_3_1_1',],
                                    "Temperature (°C)","Temperature Sensor",
                                    ],
                'Relative Humidity':[['RH_1_1_1','RH_1_2_1','RH_1_3_1',],
                                    "Relative Humidity (%)","RH Sensor",
                                    ],
                'Energy Components':[['LE','H','G'],'Energy (W/m²)',
                                    'Energy Component',
                                    ]                   
                }

@st.cache_data
def stat_data():
    df = pd.read_parquet('data/all_data.parquet')
    df.reset_index(inplace=True)
    df.replace(-9999, None, inplace=True)
    return df

st.set_page_config(page_title="UFN", page_icon="🌎",
                   layout="wide")
st.title("Utah Geological Survey-Utah Flux Network")

ufn_url = "https://geology.utah.gov/utah-flux-network"
st.write(f"[The Utah Flux Network]({ufn_url})")

# Load the station data
stations_file_path = 'data/stations.geojson'
sites = gpd.read_file(stations_file_path)
sitelist = list(sites['Site ID'].values)
data = stat_data()

# Function to create a Folium map with markers
def create_map(sts):
    m = folium.Map(location=[sts.centroid.y.mean(),
                        sts.centroid.x.mean()],
            zoom_start=6)
    folium.GeoJson(sts,
                   marker=folium.Marker(icon=folium.Icon(icon='star')),
                   popup=folium.GeoJsonPopup(fields=["Site ID"])).add_to(m)
    return m

# Function to get the site name from map click
def get_site_name(map_data):
    if map_data['last_object_clicked']:
        lat = map_data['last_object_clicked']['lat']
        site = sites[sites.geometry.y==lat]['Site ID'].values[0]
        return site
    return None

# Create a Folium map and display it in the sidebar
st.sidebar.header("Map")
folium_map = create_map(sites)
# "with" notation
with st.sidebar:
    map_data = st_folium(folium_map, width=300, height=500)

amfluxurl = "https://ameriflux.lbl.gov/sites/siteinfo/"
# Update dropdown based on map click
clicked_site = get_site_name(map_data)
if clicked_site:
    st.write(f"You selected {clicked_site} from the map")
    selected_site = clicked_site
    selsite = clicked_site
else:
    selsite = 'US-UTB'

selected_site = st.selectbox("Select a site:", 
                                options=sitelist,
                                index = sitelist.index(selsite)
                                )

if selected_site:
    # Display additional information
    site_info = sites[sites['Site ID'] == selected_site]
    if not site_info.empty:
        snm = site_info['Name'].values[0]
        st.subheader(f"[{selected_site}: {snm}]({amfluxurl}{selected_site})")
    else:
        st.write("No additional information available for this site.")
    vio_parm = st.selectbox("Parameter",
            param_select.keys(), index=0
            )
else:
    vio_param = "Air Temperature"
col1, col2 = st.columns(2)

with col1:
    # Main page dropdown

    if selected_site:
        # Display additional information

        if selected_site in data.station.unique():  

            data_df = data[data['station']==selected_site]
            molist = list(data_df['datetime_start'].dt.month_name().unique())
            
            # Filter data for the selected site
            #site_data = data_df[data_df['station'] == selected_site]

            # Plot the timeseries data
            fig = px.line(data_df, x='datetime_start', y=param_select[vio_parm][0] , 
                        title=f"{vio_parm} at {selected_site}")
            st.plotly_chart(fig)



with col2:
    # Handle navigation to the detailed station page
     
    if selected_site:
        data = stat_data()
        # Display additional information

        if selected_site in data.station.unique():  

            molist = list(data_df['datetime_start'].dt.month_name().unique())
            
            container = {}
            allp = {}
            selected_options = {}
            stat_temp = {}
            tdf = {}
            fig1 = {}

            @st.cache_resource
            def voi(stat_temp,param):
                fig = px.violin(stat_temp[param], y="value", x="variable", 
                                    box=True, hover_data=stat_temp[param].columns,
                                    labels = {"value": param_select[param][1],
                                            "variable":param_select[param][2] 
                                            },
                                            title=param
                                    )
                return fig

            def make_violin(param='Air Temperature'):
                
                container[param] = st.container()
                allp[param] = st.checkbox("Select all", key=21)
                
                if allp[param]:
                    selected_options[param] = container[param].multiselect("Select one or more options:",
                        molist,molist)
                else:
                    selected_options[param] =  container[param].multiselect("Select one or more options:",
                        molist)

                tdf[param] = data_df[data_df['datetime_start'].dt.month_name().isin(selected_options[param])]
                cols = []
                for col in param_select[param][0]:
                    if col in tdf[param].columns:
                        cols.append(col)
                print(cols)
                stat_temp[param] = tdf[param][['datetime_start']+cols].melt(id_vars=['datetime_start'])

                fig1[param] = voi(stat_temp,param)
                st.plotly_chart(fig1[param])

            @st.cache_resource
            def ebalance(ddf, sel_opts):
                df_energy =  ddf[['datetime_start','G','LE','NETRAD','H']].dropna()
                df_energy['Rn - G'] = df_energy['NETRAD'] - df_energy['G']
                df_energy['LE + H'] = df_energy['H'] + df_energy['LE']
                ebal = df_energy[df_energy['datetime_start'].dt.month_name().isin(sel_opts)]
                ebal = ebal[ebal['datetime_start'].dt.hour.isin(range(6,21))]
                fig3 = px.scatter(ebal, y="LE + H", x="Rn - G", trendline="ols")
                return fig3

            make_violin(vio_parm)

            cont = st.container()
            allvals = st.checkbox("Select All", key=23)
        
            if allvals:
                sel_opts = cont.multiselect("Select one or more options:",
                molist,molist, key=54)
            else:
                sel_opts =  cont.multiselect("Select one or more options:",
                molist, key=54)


            fig3 = ebalance(data_df, sel_opts)
            st.plotly_chart(fig3)

        else:
            st.write("Select a point on the map to view data")
