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

# from sqlalchemy import create_engine
# import postgresql
# import psycopg2

# engine = create_engine(f"postgresql+psycopg2://{user}:{pw}@{ip}:5432/groundwater")

# Show the page title and description.
# Initialize Streamlit app layout

st.set_page_config(page_title="Station Map", page_icon="🌎")
st.title("Utah Geological Survey")

st.sidebar.markdown('''
# Sections
- [Utah Flux Network Stations](#utah-flux-network-stations)
- [Data View](#data-view)
''', unsafe_allow_html=True)

st.header('Utah Flux Network Stations')

ufn_url = "https://geology.utah.gov/utah-flux-network"
st.write(f"[The Utah Flux Network]({ufn_url})")

# Load the station data
stations_file_path = 'data/AmeriFlux-sites.csv'
stations_df = pd.read_csv(stations_file_path)

# Prepare the station data for Pydeck
stations_df['Site'] = stations_df['Site ID']

# Define a function to create the popup HTML
def create_popup_html(row):
    return f"""
    <b>Site ID:</b> {row['Site ID']}<br>
    <b>Name:</b> {row['Name']}<br>
    """

# Create a Folium map
m = folium.Map(location=[stations_df['latitude'].mean(), 
                         stations_df['longitude'].mean()], 
               zoom_start=6)

# Add markers to the map
for _, row in stations_df.iterrows():
    popup_html = create_popup_html(row)
    folium.Marker(
        location=[row['latitude'], row['longitude']],
        popup=Popup(popup_html, max_width=200),
        tooltip=row['Site ID']
    ).add_to(m)

output = st_folium(m, width="100%", height=350,
                   returned_objects=["last_object_clicked_tooltip"])

st.header('Data View')
# Handle navigation to the detailed station page
selected_site = output['last_object_clicked_tooltip']

amfluxurl = "https://ameriflux.lbl.gov/sites/siteinfo/"

container = {}
all = {}
selected_options = {}
stat_temp = {}
tdf = {}
fig1 = {}

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

def make_violin(param='Air Temperature'):
    

    container[param] = st.container()
    all[param] = st.checkbox("Select all", key=21)
    
    if all[param]:
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

    fig1[param] = px.violin(stat_temp[param], y="value", x="variable", 
                        box=True, hover_data=stat_temp[param].columns,
                        labels = {"value": param_select[param][1],
                                "variable":param_select[param][2] 
                                },
                                title=param
                        )
    st.plotly_chart(fig1[param])


if selected_site:
    datafile = f'data/{selected_site}_amfluxeddy.csv'

    # Display additional information
    site_info = stations_df[stations_df['Site ID'] == selected_site]
    if not site_info.empty:
        snm = site_info['Name'].values[0]
        st.subheader(f"[{selected_site}: {snm}]({amfluxurl}{selected_site})")
    else:
        st.write("No additional information available for this site.")

    if os.path.exists(datafile):  
        # Load the time series data
        data_file_path = f'data/{selected_site}_amfluxeddy.csv'
        data_df = pd.read_csv(data_file_path, parse_dates=['datetime_start'])
        molist = list(data_df['datetime_start'].dt.month_name().unique())
        
        # Filter data for the selected site
        #site_data = data_df[data_df['station'] == selected_site]

        tsparam = st.selectbox("Timeseries Parameter",
                               data_df.columns, index=3
                               )
        
        # Plot the timeseries data
        fig = px.line(data_df, x='datetime_start', y=tsparam , 
                      title=f"{tsparam} Levels at {selected_site}")
        st.plotly_chart(fig)

        vio_parm = st.selectbox("Parameter",
                               param_select.keys(), index=0
                               )
        make_violin(vio_parm)



        cont = st.container()
        allvals = st.checkbox("Select All", key=23)
    
        if allvals:
            sel_opts = cont.multiselect("Select one or more options:",
            molist,molist, key=54)
        else:
            sel_opts =  cont.multiselect("Select one or more options:",
            molist, key=54)


        df_energy =  data_df[['datetime_start','G','LE','NETRAD','H']].dropna()
        df_energy['Rn - G'] = df_energy['NETRAD'] - df_energy['G']
        df_energy['LE + H'] = df_energy['H'] + df_energy['LE']
        ebal = df_energy[df_energy['datetime_start'].dt.month_name().isin(sel_opts)]
        fig3 = px.scatter(ebal, x="LE + H", y="Rn - G", trendline="ols")
        st.plotly_chart(fig3)

    else:
        st.write("Select a point on the map to view data")
