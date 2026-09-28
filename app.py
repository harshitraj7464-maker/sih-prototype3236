import streamlit as st
import pandas as pd
import sqlite3
import base64
from folium import Map, Marker, Popup, TileLayer
from folium.plugins import HeatMap, MarkerCluster
from streamlit_folium import st_folium

# --- 1. LOCAL DATA ENGINE & PERSISTENCE CONFIGURATION ---
DB_FILE = "sih26001_production.db"

def initialize_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS disaster_incidents 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      latitude REAL, longitude REAL, risk_level TEXT, 
                      description TEXT, file_name TEXT, file_type TEXT, 
                      base64_data TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

initialize_database()

# --- 2. INTERACTIVE MEMORY BINDING (STREAMLIT SESSION STATE) ---
if "form_lat" not in st.session_state:
    st.session_state["form_lat"] = 20.5937
if "form_lon" not in st.session_state:
    st.session_state["form_lon"] = 78.9629

# --- 3. FRONTEND GRAPHICAL USER INTERFACE ---
st.set_page_config(layout="wide", page_title="SIH26001 - Terrain Risk Analytics")
st.markdown("## 🛰️ SIH26001 High-Resolution Terrain & Media Mapping System")

# Application control sidebar
st.sidebar.header("📶 System Control Network")
offline_mode = st.sidebar.checkbox("🔌 Force Offline Operational Mode", value=False)

st.sidebar.markdown("---")
st.sidebar.header("📥 Log Terrain Risk Asset")

# Media Data Collector Form
with st.sidebar.form("incident_logger_form", clear_on_submit=False):
    # Bind coordinates dynamically to Session State trackers
    input_lat = st.number_input("Latitude Coords", value=st.session_state["form_lat"], format="%.4f")
    input_lon = st.number_input("Longitude Coords", value=st.session_state["form_lon"], format="%.4f")
    
    risk_tier = st.selectbox("Assessed Risk Tier", ["Low Risk Zone", "Medium Risk Alert", "Critical / High Hazard"])
    incident_desc = st.text_area("Field Assessment Remarks")
    
    # Advanced Media Ingestion Engine
    uploaded_file = st.file_uploader("Upload Risk Media (Drone Footage / Images)", type=["png", "jpg", "jpeg", "mp4"])
    
    submit_report = st.form_submit_button("Commit Entry to Ledger")
    
    if submit_report:
        file_name, file_type, encoded_binary = "None", "None", ""
        
        if uploaded_file is not None:
            file_name = uploaded_file.name
            file_type = uploaded_file.type
            # Convert raw file upload into clean base64 data string for absolute database portability
            file_bytes = uploaded_file.read()
            encoded_binary = base64.b64encode(file_bytes).decode("utf-8")
            
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO disaster_incidents 
                          (latitude, longitude, risk_level, description, file_name, file_type, base64_data) 
                          VALUES (?, ?, ?, ?, ?, ?, ?)""", 
                       (input_lat, input_lon, risk_tier, incident_desc, file_name, file_type, encoded_binary))
        conn.commit()
        conn.close()
        st.sidebar.success(f"✓ Operational entry successfully synchronized.")

# --- 4. DATA LOADER & GEOSPATIAL MAP ENGINE ---
conn = sqlite3.connect(DB_FILE)
df_records = pd.read_sql_query("SELECT * FROM disaster_incidents", conn)
conn.close()

# Base Map Selection Engine
if offline_mode:
    # Offline fallback relies on absolute local disk map directories
    map_layer_tiles = 'http://localhost:8080/styles/terrain/{z}/{x}/{y}.png'
    map_attribution = "Local Micro-Tile Grid Server"
else:
    # High-Definition Esri World Terrain Server
    map_layer_tiles = 'https://arcgisonline.com{z}/{x}/{y}'
    map_attribution = "Esri World Terrain Infrastructure"

# Render core terrain asset canvas
risk_map = Map(location=[st.session_state["form_lat"], st.session_state["form_lon"]], 
               zoom_start=6, tiles=map_layer_tiles, attr=map_attribution)

# Overlay high-contrast topographical hillshade for precise terrain tracking
if not offline_mode:
    TileLayer(
        tiles='https://arcgisonline.com{z}/{x}/{y}',
        name="Topographical Hillshade Reference",
        attr="Esri Elevation Group",
        opacity=0.4,
        overlay=True
    ).add_to(risk_map)

# Compute and draw the geometric risk heatmap weights
if not df_records.empty:
    tier_weight_matrix = {"Low Risk Zone": 0.3, "Medium Risk Alert": 0.6, "Critical / High Hazard": 1.0}
    compiled_heatmap_data = [
        [row['latitude'], row['longitude'], tier_weight_matrix.get(row['risk_level'], 0.5)] 
        for _, row in df_records.iterrows()
    ]
    HeatMap(compiled_heatmap_data, radius=25, blur=12, min_opacity=0.5).add_to(risk_map)

    # Interactive Marker Clustering with nested media decoding popup routines
    marker_cluster_group = MarkerCluster(name="Field Reports Ledger").add_to(risk_map)
    for _, row in df_records.iterrows():
        embedded_media_tag = ""
        
        # Decode base64 stream directly back to raw binary data inside HTML popups
        if row['base64_data'] != "":
            if "video" in row['file_type']:
                embedded_media_tag = f"<br/><video width='220' controls><source src='data:{row['file_type']};base64,{row['base64_data']}' type='{row['file_type']}'></video>"
            else:
                embedded_media_tag = f"<br/><img src='data:{row['file_type']};base64,{row['base64_data']}' width='220' style='border-radius:4px;'/>"
        
        popup_markup = f"""
        <div style='font-family:Segoe UI, sans-serif; font-size:12px; width:230px;'>
            <b style='color:#d9534f;'>🚨 {row['risk_level']}</b><br/>
            <span style='color:#777;'>📍 {row['latitude']:.4f}, {row['longitude']:.4f}</span><br/>
            <p style='margin:5px 0;'>{row['description']}</p>
            {embedded_media_tag}
        </div>
        """
        Marker(
            location=[row['latitude'], row['longitude']],
            popup=Popup(popup_markup, max_width=260),
            tooltip=f"Click for Topo Risk Analysis"
        ).add_to(marker_cluster_group)

# --- 5. GRID INTERFACE LAYOUT SYSTEM ---
column_left, column_right = st.columns([2, 1])

with column_left:
    st.subheader("🗺️ Dynamic Terrain Mapping & Risk Interface")
    # Capture map clicks to automate user actions
    map_interaction_bridge = st_folium(risk_map, width="100%", height=600, key="terrain_map")
    
    # Read spatial event signals to trigger programmatic ui changes
    if map_interaction_bridge and map_interaction_bridge.get("last_clicked"):
        lat_click = map_interaction_bridge["last_clicked"]["lat"]
        lon_click = map_interaction_bridge["last_clicked"]["lng"]
        
        if lat_click != st.session_state["form_lat"] or lon_click != st.session_state["form_lon"]:
            st.session_state["form_lat"] = lat_click
            st.session_state["form_lon"] = lon_click
            st.rerun()

with column_right:
    st.subheader("📊 Field Information Feed")
    
    # Clean UI Data Inspection Tabs
    tab_overview, tab_media_gallery = st.tabs(["📋 Data Logs", "🖼️ Incident Media Feed"])
    
    with tab_overview:
        st.metric("Total Monitored Areas", len(df_records))
        if not df_records.empty:
            st.dataframe(
                df_records[['id', 'risk_level', 'file_name', 'timestamp']], 
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.info("No geospatial active records stored.")
            
    with tab_media_gallery:
        if not df_records.empty:
            for _, entry in df_records.iterrows():
                if entry['base64_data'] != "":
                    st.write(f"**Record ID {entry['id']}:** {entry['risk_level']}")
                    decoded_bytes = base64.b64decode(entry['base64_data'])
                    if "video" in entry['file_type']:
                        st.video(decoded_bytes, format=entry['file_type'])
                    else:
                        st.image(decoded_bytes, caption=entry['file_name'], use_container_width=True)
                    st.markdown("---")
        else:
            st.info("Gallery view empty.")
