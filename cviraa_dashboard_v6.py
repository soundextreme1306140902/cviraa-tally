import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
import io
import html
import time
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics

# Set page configuration
st.set_page_config(
    page_title="CVIRAA Medal Tally System",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
CSV_FILE = "cviraa_medal_data_v2.csv"
SEED_FILE = "cviraa_initial_data_v2.csv"

# Divisions List (Post-2026 Split - 12 active divisions)
DIVISIONS = [
    "Bogo City", "Bohol Province", "Carcar City", "Cebu City", 
    "Cebu Province", "Danao City", "Lapu-Lapu City", "Mandaue City", 
    "City of Naga", "Tagbilaran City", "Talisay City", "Toledo City"
]

# Sports List
SPORTS = [
    "Archery", "Arnis", "Athletics", "Badminton", "Baseball", 
    "Basketball", "Billiards", "Boxing", "Chess", "Dancesport", 
    "Football", "Futsal", "Gymnastics", "Pencak Silat", "Sepak Takraw", 
    "Softball", "Swimming", "Table Tennis", "Taekwondo", "Volleyball"
]

# Initialize and load data
def load_data():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
    elif os.path.exists(SEED_FILE):
        df = pd.read_csv(SEED_FILE)
    else:
        # Fallback if neither exists (480 rows)
        records = []
        for div in DIVISIONS:
            for cat in ["Elementary", "Secondary"]:
                for sport in SPORTS:
                    records.append({
                        "Division": div,
                        "Category": cat,
                        "Sport": sport,
                        "Gold": 0,
                        "Silver": 0,
                        "Bronze": 0
                    })
        df = pd.DataFrame(records)
        df.to_csv(CSV_FILE, index=False)
    
    # Data type integrity
    df["Gold"] = df["Gold"].astype(int)
    df["Silver"] = df["Silver"].astype(int)
    df["Bronze"] = df["Bronze"].astype(int)
    return df

def save_data(df):
    df.to_csv(CSV_FILE, index=False)

# Custom tie-breaker sorting and ranking logic
def calculate_ranking(df):
    if df.empty:
        return pd.DataFrame(columns=["Rank", "Division", "Gold", "Silver", "Bronze", "Total"])
    
    # Group by Division to calculate dynamic rankings based on the filtered dataset
    summary = df.groupby("Division").agg({
        "Gold": "sum",
        "Silver": "sum",
        "Bronze": "sum"
    }).reset_index()
    
    summary["Total"] = summary["Gold"] + summary["Silver"] + summary["Bronze"]
    
    # Sort: Gold desc, Silver desc, Bronze desc, then alphabetically by Division name
    summary = summary.sort_values(
        by=["Gold", "Silver", "Bronze", "Division"],
        ascending=[False, False, False, True]
    ).reset_index(drop=True)
    
    # Assign Rank
    summary["Rank"] = summary.index + 1
    
    # Reorder columns
    columns = ["Rank", "Division", "Gold", "Silver", "Bronze", "Total"]
    return summary[columns]

# Initialize session state variables
if 'medal_df' not in st.session_state:
    st.session_state.medal_df = load_data()

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if 'kiosk_active' not in st.session_state:
    st.session_state.kiosk_active = False

if 'kiosk_slide_index' not in st.session_state:
    st.session_state.kiosk_slide_index = 0

ADMIN_PASSWORD = "cviraa2026"

# 📺 TV KIOSK OVERRIDE LAYOUT
if st.session_state.kiosk_active:
    # Hide sidebar and header, add widescreen kiosk typography
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                display: none !important;
            }
            header, footer {
                visibility: hidden !important;
                height: 0px !important;
            }
            .block-container {
                padding-top: 1rem !important;
                padding-bottom: 1rem !important;
                max-width: 95% !important;
            }
            .kiosk-title {
                font-size: 2.8rem !important;
                font-weight: 900 !important;
                color: #F59E0B !important;
                text-align: center;
                margin: 0px !important;
                letter-spacing: 2px;
            }
            .kiosk-subtitle {
                font-size: 1.4rem !important;
                color: white !important;
                text-align: center;
                margin: 5px 0 0 0 !important;
                font-weight: 500;
            }
            .kiosk-slide-title {
                font-size: 2.2rem !important;
                font-weight: 800 !important;
                color: #1E3A8A !important;
                text-align: center;
                margin-top: 10px;
                margin-bottom: 15px;
            }
            /* High-contrast metrics on TV */
            div[data-testid="stMetricValue"] {
                font-size: 3rem !important;
                font-weight: 900 !important;
                color: #1E3A8A !important;
            }
            div[data-testid="stMetricLabel"] {
                font-size: 1.3rem !important;
                font-weight: bold !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # TV Kiosk Banner Header
    st.markdown("""
        <div style="background-color:#1E3A8A;padding:15px;border-radius:10px;text-align:center;margin-bottom:15px;position:relative;">
            <div style="position:absolute;top:20px;left:25px;background-color:#EF4444;color:white;padding:5px 12px;border-radius:20px;font-size:0.9em;font-weight:bold;animation: pulse 1s infinite;display:flex;align-items:center;gap:6px;">
                <span style="height:10px;width:10px;background-color:white;border-radius:50%;display:inline-block;"></span> LIVE SCOREBOARD
            </div>
            <h1 class="kiosk-title">🏆 CVIRAA MEDAL TALLY 🏆</h1>
            <p class="kiosk-subtitle">Central Visayas Regional Athletic Association Meet (Naga City, Cebu)</p>
        </div>
        <style>
            @keyframes pulse {
                0% { opacity: 0.4; }
                50% { opacity: 1; }
                100% { opacity: 0.4; }
            }
        </style>
    """, unsafe_allow_html=True)

    # Get Kiosk Configuration from Session State
    kiosk_slides = st.session_state.get("kiosk_slides", ["🏆 Overall Leaderboard", "🎒 Elementary Standings", "🎓 Secondary Standings"])
    kiosk_speed = st.session_state.get("kiosk_speed", 10)
    
    # Make sure we don't have empty slides list
    if not kiosk_slides:
        kiosk_slides = ["🏆 Overall Leaderboard"]
        
    # Cycle slides index safely
    st.session_state.kiosk_slide_index = st.session_state.kiosk_slide_index % len(kiosk_slides)
    current_slide = kiosk_slides[st.session_state.kiosk_slide_index]
    
    # Display Exit and Navigation Bar
    nav_col1, nav_col2, nav_col3 = st.columns([2, 6, 2])
    with nav_col1:
        if st.button("❌ Exit TV Mode", use_container_width=True):
            st.session_state.kiosk_active = False
            st.rerun()
    with nav_col2:
        st.markdown(f"<h3 style='text-align:center;margin:0;color:#1E3A8A;'>📺 Displaying: {current_slide}</h3>", unsafe_allow_html=True)
    with nav_col3:
        if st.button("➡️ Next Slide", use_container_width=True):
            st.session_state.kiosk_slide_index = (st.session_state.kiosk_slide_index + 1) % len(kiosk_slides)
            st.rerun()
            
    st.markdown("<hr style='margin:10px 0 20px 0;'/>", unsafe_allow_html=True)
    
    # Slide Render Router
    if current_slide == "🏆 Overall Leaderboard":
        overall_tally = calculate_ranking(st.session_state.medal_df)
        
        # Big Stats
        if not overall_tally.empty:
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("🏅 General Leader", overall_tally.iloc[0]["Division"], f"{overall_tally.iloc[0]['Gold']} Golds")
            with m2:
                st.metric("✨ Golds Awarded", int(overall_tally["Gold"].sum()))
            with m3:
                st.metric("🏃 Active delegations", 12)
                
        # Main split: wide table (left) vs plot (right)
        col_t1, col_t2 = st.columns([5, 5])
        with col_t1:
            st.dataframe(
                overall_tally,
                use_container_width=True,
                hide_index=True,
                height=450,
                column_config={
                    "Rank": st.column_config.NumberColumn("Rank", format="%d"),
                    "Division": st.column_config.TextColumn("Schools Division"),
                    "Gold": st.column_config.NumberColumn("Gold 🥇", format="%d"),
                    "Silver": st.column_config.NumberColumn("Silver 🥈", format="%d"),
                    "Bronze": st.column_config.NumberColumn("Bronze 🥉", format="%d"),
                    "Total": st.column_config.NumberColumn("Total", format="%d")
                }
            )
        with col_t2:
            fig = px.bar(
                overall_tally.sort_values("Total", ascending=True), 
                y="Division", 
                x=["Gold", "Silver", "Bronze"],
                labels={"value": "Medals", "Division": "Schools Division", "variable": "Color"},
                color_discrete_map={"Gold": "#F59E0B", "Silver": "#9CA3AF", "Bronze": "#B45309"},
                orientation="h",
                height=450
            )
            fig.update_layout(barmode="stack", margin=dict(t=10, b=10, l=10, r=10), legend_title_text="")
            st.plotly_chart(fig, use_container_width=True)
            
    elif current_slide == "🎒 Elementary Standings":
        elem_tally = calculate_ranking(st.session_state.medal_df[st.session_state.medal_df["Category"] == "Elementary"])
        
        if not elem_tally.empty:
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("🎒 Elementary Leader", elem_tally.iloc[0]["Division"], f"{elem_tally.iloc[0]['Gold']} Golds")
            with m2:
                st.metric("🏅 Elementary Golds", int(elem_tally["Gold"].sum()))
            with m3:
                st.metric("🏟️ Sub-competition", "Elementary Division")
                
        col_t1, col_t2 = st.columns([5, 5])
        with col_t1:
            st.dataframe(
                elem_tally,
                use_container_width=True,
                hide_index=True,
                height=450,
                column_config={
                    "Rank": st.column_config.NumberColumn("Rank", format="%d"),
                    "Division": st.column_config.TextColumn("Schools Division"),
                    "Gold": st.column_config.NumberColumn("Gold 🥇", format="%d"),
                    "Silver": st.column_config.NumberColumn("Silver 🥈", format="%d"),
                    "Bronze": st.column_config.NumberColumn("Bronze 🥉", format="%d"),
                    "Total": st.column_config.NumberColumn("Total", format="%d")
                }
            )
        with col_t2:
            fig = px.bar(
                elem_tally.sort_values("Total", ascending=True), 
                y="Division", 
                x=["Gold", "Silver", "Bronze"],
                color_discrete_map={"Gold": "#F59E0B", "Silver": "#9CA3AF", "Bronze": "#B45309"},
                orientation="h",
                height=450
            )
            fig.update_layout(barmode="stack", margin=dict(t=10, b=10, l=10, r=10), legend_title_text="")
            st.plotly_chart(fig, use_container_width=True)
            
    elif current_slide == "🎓 Secondary Standings":
        sec_tally = calculate_ranking(st.session_state.medal_df[st.session_state.medal_df["Category"] == "Secondary"])
        
        if not sec_tally.empty:
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("🎓 Secondary Leader", sec_tally.iloc[0]["Division"], f"{sec_tally.iloc[0]['Gold']} Golds")
            with m2:
                st.metric("🏅 Secondary Golds", int(sec_tally["Gold"].sum()))
            with m3:
                st.metric("🏟️ Sub-competition", "Secondary Division")
                
        col_t1, col_t2 = st.columns([5, 5])
        with col_t1:
            st.dataframe(
                sec_tally,
                use_container_width=True,
                hide_index=True,
                height=450,
                column_config={
                    "Rank": st.column_config.NumberColumn("Rank", format="%d"),
                    "Division": st.column_config.TextColumn("Schools Division"),
                    "Gold": st.column_config.NumberColumn("Gold 🥇", format="%d"),
                    "Silver": st.column_config.NumberColumn("Silver 🥈", format="%d"),
                    "Bronze": st.column_config.NumberColumn("Bronze 🥉", format="%d"),
                    "Total": st.column_config.NumberColumn("Total", format="%d")
                }
            )
        with col_t2:
            fig = px.bar(
                sec_tally.sort_values("Total", ascending=True), 
                y="Division", 
                x=["Gold", "Silver", "Bronze"],
                color_discrete_map={"Gold": "#F59E0B", "Silver": "#9CA3AF", "Bronze": "#B45309"},
                orientation="h",
                height=450
            )
            fig.update_layout(barmode="stack", margin=dict(t=10, b=10, l=10, r=10), legend_title_text="")
            st.plotly_chart(fig, use_container_width=True)
            
    elif "Highlights" in current_slide:
        # Extra: Sport Highlights Slide
        # Extract the sport name from the slide title (e.g. "🏊 Swimming Highlights" -> "Swimming")
        target_sport = current_slide.split()[-2] if len(current_slide.split()) >= 2 else "Swimming"
        # Quick lookup or fallback if emoji is stuck
        if "Swimming" in current_slide: target_sport = "Swimming"
        elif "Athletics" in current_slide: target_sport = "Athletics"
        elif "Chess" in current_slide: target_sport = "Chess"
        
        sport_df = st.session_state.medal_df[st.session_state.medal_df["Sport"] == target_sport]
        sport_tally = calculate_ranking(sport_df)
        
        if not sport_tally.empty and sport_tally["Total"].sum() > 0:
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric(f"🥇 {target_sport} Leader", sport_tally.iloc[0]["Division"], f"{sport_tally.iloc[0]['Gold']} Golds")
            with m2:
                st.metric("Total Medals Logged", int(sport_tally["Total"].sum()))
            with m3:
                st.metric("Featured Sport", target_sport)
                
            col_t1, col_t2 = st.columns([5, 5])
            with col_t1:
                st.dataframe(
                    sport_tally,
                    use_container_width=True,
                    hide_index=True,
                    height=450,
                    column_config={
                        "Rank": st.column_config.NumberColumn("Rank", format="%d"),
                        "Division": st.column_config.TextColumn("Schools Division"),
                        "Gold": st.column_config.NumberColumn("Gold 🥇", format="%d"),
                        "Silver": st.column_config.NumberColumn("Silver 🥈", format="%d"),
                        "Bronze": st.column_config.NumberColumn("Bronze 🥉", format="%d"),
                        "Total": st.column_config.NumberColumn("Total", format="%d")
                    }
                )
            with col_t2:
                fig = px.bar(
                    sport_tally.sort_values("Total", ascending=True), 
                    y="Division", 
                    x=["Gold", "Silver", "Bronze"],
                    color_discrete_map={"Gold": "#F59E0B", "Silver": "#9CA3AF", "Bronze": "#B45309"},
                    orientation="h",
                    height=450
                )
                fig.update_layout(barmode="stack", margin=dict(t=10, b=10, l=10, r=10), legend_title_text="")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"No medals logged yet for {target_sport}.")
            
    # Auto-cycle loop using simple time.sleep and st.rerun
    st.session_state.kiosk_slide_index = (st.session_state.kiosk_slide_index + 1) % len(kiosk_slides)
    time.sleep(kiosk_speed)
    st.rerun()

# 🏡 STANDARD BOARDROOM / MANAGER VIEW (If Kiosk is NOT active)
else:
    # Page Header
    st.markdown("""
        <div style="background-color:#1E3A8A;padding:20px;border-radius:10px;text-align:center;margin-bottom:20px">
            <h1 style="color:#F59E0B;margin:0;font-family:Arial, sans-serif;font-weight:bold;">🏆 CENTRAL VISAYAS REGIONAL ATHLETIC ASSOCIATION</h1>
            <h3 style="color:white;margin:5px 0 0 0;font-family:Arial, sans-serif;">CVIRAA Medal Tally & Monitoring System</h3>
            <p style="color:#D1D5DB;margin:5px 0 0 0;font-size:0.9em;">Official 12-Division Format &bull; Sport-by-Sport Tracking &bull; Certificate Generator &bull; TV Kiosk Mode</p>
        </div>
    """, unsafe_allow_html=True)

    # Sidebar: Management Panel
    with st.sidebar:
        st.image("https://img.icons8.com/color/144/trophy.png", width=100)
        st.title("⚙️ System Control")
        
        # TV KIOSK SETTINGS
        with st.expander("📺 TV Display / Kiosk Settings", expanded=True):
            st.markdown("Configure a dynamic rotating kiosk scoreboard for TV screens or LED walls.")
            
            # Select slides to display in cycle
            kiosk_slides_choices = [
                "🏆 Overall Leaderboard", 
                "🎒 Elementary Standings", 
                "🎓 Secondary Standings",
                "🏊 Swimming Highlights",
                "🏃 Athletics Highlights",
                "♟️ Chess Highlights"
            ]
            selected_k_slides = st.multiselect(
                "Slides to Cycle", 
                options=kiosk_slides_choices, 
                default=["🏆 Overall Leaderboard", "🎒 Elementary Standings", "🎓 Secondary Standings"]
            )
            
            k_speed = st.slider("Rotation Speed (seconds)", min_value=3, max_value=60, value=10, step=1)
            
            # Trigger Kiosk Mode
            if st.button("🚀 Launch TV Kiosk Mode", use_container_width=True):
                st.session_state.kiosk_slides = selected_k_slides
                st.session_state.kiosk_speed = k_speed
                st.session_state.kiosk_slide_index = 0
                st.session_state.kiosk_active = True
                st.rerun()
                
        st.markdown("<hr/>", unsafe_allow_html=True)
        st.subheader("🛡️ Admin Database Portal")
        
        # Authenticate admin
        if not st.session_state.authenticated:
            st.subheader("🔐 Staff Authentication")
            pwd_input = st.text_input("Enter Admin Password", type="password")
            if st.button("Unlock Admin Features", use_container_width=True):
                if pwd_input == ADMIN_PASSWORD:
                    st.session_state.authenticated = True
                    st.success("Access Granted!")
                    st.rerun()
                else:
                    st.error("Incorrect password! Access denied.")
        else:
            st.success("🔓 Authenticated Session")
            if st.button("Lock Console / Log Out", use_container_width=True):
                st.session_state.authenticated = False
                st.rerun()
                
            st.markdown("---")
            st.markdown("Use the forms below to log individual medals or manage records.")
            
            # Quick Update Form
            with st.expander("📝 Quick Medal Input Form", expanded=True):
                selected_div = st.selectbox("Select Division", DIVISIONS)
                selected_cat = st.radio("Select Category", ["Elementary", "Secondary"])
                selected_sport = st.selectbox("Select Sport", SPORTS)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    gold_in = st.number_input("Gold 🥇", min_value=0, step=1, value=0)
                with col2:
                    silver_in = st.number_input("Silver 🥈", min_value=0, step=1, value=0)
                with col3:
                    bronze_in = st.number_input("Bronze 🥉", min_value=0, step=1, value=0)
                    
                update_mode = st.selectbox("Update Mode", ["Add to existing", "Overwrite existing"])
                
                if st.button("💾 Apply Medal Update", use_container_width=True):
                    df = st.session_state.medal_df.copy()
                    idx = df[(df["Division"] == selected_div) & 
                             (df["Category"] == selected_cat) & 
                             (df["Sport"] == selected_sport)].index
                    
                    if len(idx) > 0:
                        if update_mode == "Add to existing":
                            df.loc[idx, "Gold"] += gold_in
                            df.loc[idx, "Silver"] += silver_in
                            df.loc[idx, "Bronze"] += bronze_in
                        else:
                            df.loc[idx, "Gold"] = gold_in
                            df.loc[idx, "Silver"] = silver_in
                            df.loc[idx, "Bronze"] = bronze_in
                        
                        st.session_state.medal_df = df
                        save_data(df)
                        st.success(f"Updated {selected_sport} for {selected_div} ({selected_cat}) successfully!")
                        st.rerun()

            # Bulk CSV Importer / Exporter
            with st.expander("📂 Import & Export Data"):
                st.subheader("Export Data")
                csv_data = st.session_state.medal_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download current database (CSV)",
                    data=csv_data,
                    file_name="cviraa_sport_medal_tally.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
                st.subheader("Import / Restore Data")
                uploaded_file = st.file_uploader("Upload CSV to overwrite database", type=["csv"])
                if uploaded_file is not None:
                    try:
                        uploaded_df = pd.read_csv(uploaded_file)
                        # Verify columns
                        required_cols = {"Division", "Category", "Sport", "Gold", "Silver", "Bronze"}
                        if required_cols.issubset(uploaded_df.columns):
                            st.session_state.medal_df = uploaded_df
                            save_data(uploaded_df)
                            st.success("Database restored successfully from file!")
                            st.rerun()
                        else:
                            st.error("Invalid CSV structure! Must contain columns: Division, Category, Sport, Gold, Silver, Bronze")
                    except Exception as e:
                        st.error(f"Error reading file: {e}")

            # Database Reset Section
            with st.expander("⚠️ Danger Zone"):
                st.warning("These operations cannot be undone.")
                
                if st.button("🔄 Reset All Tallies to Zero", use_container_width=True):
                    df = st.session_state.medal_df.copy()
                    df["Gold"] = 0
                    df["Silver"] = 0
                    df["Bronze"] = 0
                    st.session_state.medal_df = df
                    save_data(df)
                    st.success("All sport medals have been reset to 0!")
                    st.rerun()

    # Main Application Tabs
    tab_overall, tab_elem, tab_sec, tab_sport, tab_cert, tab_editor = st.tabs([
        "🏆 Overall Standings", 
        "🎒 Elementary Division", 
        "🎓 Secondary Division",
        "🏅 Sport-by-Sport Breakdown",
        "📜 Certificate Generator",
        "✏️ Spreadsheet Editor"
    ])

    # Process the classifications
    overall_tally = calculate_ranking(st.session_state.medal_df)
    elem_tally = calculate_ranking(st.session_state.medal_df[st.session_state.medal_df["Category"] == "Elementary"])
    sec_tally = calculate_ranking(st.session_state.medal_df[st.session_state.medal_df["Category"] == "Secondary"])

    # Tab 1: Overall Tally
    with tab_overall:
        st.subheader("Overall Medal Standings")
        
        # Top Metrics Bar
        if len(overall_tally) > 0:
            top_div = overall_tally.iloc[0]["Division"]
            top_golds = overall_tally.iloc[0]["Gold"]
            total_golds_awarded = overall_tally["Gold"].sum()
            
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Current Leader", top_div, f"{top_golds} Gold Medals")
            with m2:
                st.metric("Total Gold Medals Distributed", int(total_golds_awarded))
            with m3:
                st.metric("Active Delegations", len(overall_tally))
        
        # Display overall table
        st.dataframe(
            overall_tally,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Rank": st.column_config.NumberColumn("Rank", format="%d"),
                "Division": st.column_config.TextColumn("Schools Division"),
                "Gold": st.column_config.NumberColumn("Gold 🥇", format="%d"),
                "Silver": st.column_config.NumberColumn("Silver 🥈", format="%d"),
                "Bronze": st.column_config.NumberColumn("Bronze 🥉", format="%d"),
                "Total": st.column_config.NumberColumn("Total Medals", format="%d")
            }
        )
        
        # Visualization
        st.subheader("📊 Visualizing Overall Medal Distribution")
        fig = px.bar(
            overall_tally.sort_values("Total", ascending=True), 
            y="Division", 
            x=["Gold", "Silver", "Bronze"],
            title="Medal Distribution by Schools Division",
            labels={"value": "Medal Count", "Division": "Schools Division", "variable": "Medal Type"},
            color_discrete_map={"Gold": "#F59E0B", "Silver": "#9CA3AF", "Bronze": "#B45309"},
            orientation="h",
            height=500
        )
        fig.update_layout(barmode="stack", legend_title_text="Medal Color")
        st.plotly_chart(fig, use_container_width=True)

    # Tab 2: Elementary Division
    with tab_elem:
        st.subheader("Elementary Division Medal Standings")
        st.dataframe(
            elem_tally,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Rank": st.column_config.NumberColumn("Rank", format="%d"),
                "Division": st.column_config.TextColumn("Schools Division"),
                "Gold": st.column_config.NumberColumn("Gold 🥇", format="%d"),
                "Silver": st.column_config.NumberColumn("Silver 🥈", format="%d"),
                "Bronze": st.column_config.NumberColumn("Bronze 🥉", format="%d"),
                "Total": st.column_config.NumberColumn("Total Medals", format="%d")
            }
        )
        
        fig_elem = px.bar(
            elem_tally.sort_values("Total", ascending=True), 
            y="Division", 
            x=["Gold", "Silver", "Bronze"],
            title="Elementary Medal Distribution",
            labels={"value": "Medal Count", "Division": "Schools Division", "variable": "Medal Type"},
            color_discrete_map={"Gold": "#F59E0B", "Silver": "#9CA3AF", "Bronze": "#B45309"},
            orientation="h",
            height=400
        )
        fig_elem.update_layout(barmode="stack", legend_title_text="Medal Color")
        st.plotly_chart(fig_elem, use_container_width=True)

    # Tab 3: Secondary Division
    with tab_sec:
        st.subheader("Secondary Division Medal Standings")
        st.dataframe(
            sec_tally,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Rank": st.column_config.NumberColumn("Rank", format="%d"),
                "Division": st.column_config.TextColumn("Schools Division"),
                "Gold": st.column_config.NumberColumn("Gold 🥇", format="%d"),
                "Silver": st.column_config.NumberColumn("Silver 🥈", format="%d"),
                "Bronze": st.column_config.NumberColumn("Bronze 🥉", format="%d"),
                "Total": st.column_config.NumberColumn("Total Medals", format="%d")
            }
        )
        
        fig_sec = px.bar(
            sec_tally.sort_values("Total", ascending=True), 
            y="Division", 
            x=["Gold", "Silver", "Bronze"],
            title="Secondary Medal Distribution",
            labels={"value": "Medal Count", "Division": "Schools Division", "variable": "Medal Type"},
            color_discrete_map={"Gold": "#F59E0B", "Silver": "#9CA3AF", "Bronze": "#B45309"},
            orientation="h",
            height=400
        )
        fig_sec.update_layout(barmode="stack", legend_title_text="Medal Color")
        st.plotly_chart(fig_sec, use_container_width=True)

    # Tab 4: Sport-by-Sport Breakdown
    with tab_sport:
        st.subheader("🏅 Sport-by-Sport Medal Breakdowns")
        st.markdown("Analyze the rankings and standings for each specific athletic discipline.")
        
        col_sel_sport, col_sel_cat = st.columns(2)
        with col_sel_sport:
            sport_filter = st.selectbox("Select Sport to Analyze", SPORTS, index=SPORTS.index("Swimming") if "Swimming" in SPORTS else 0)
        with col_sel_cat:
            category_filter = st.selectbox("Select Division Category", ["All Categories", "Elementary", "Secondary"])
            
        # Filter the main dataframe
        sport_df = st.session_state.medal_df[st.session_state.medal_df["Sport"] == sport_filter]
        if category_filter != "All Categories":
            sport_df = sport_df[sport_df["Category"] == category_filter]
            
        # Calculate standings for this specific subset
        sport_tally = calculate_ranking(sport_df)
        
        if not sport_tally.empty and sport_tally["Total"].sum() > 0:
            # Highlighting the champion of this sport
            sport_champ = sport_tally.iloc[0]["Division"]
            sport_champ_gold = sport_tally.iloc[0]["Gold"]
            sport_champ_total = sport_tally.iloc[0]["Total"]
            
            st.info(f"🏆 **Sport Leader**: **{sport_champ}** is currently leading in **{sport_filter}** ({category_filter}) with **{sport_champ_gold} Gold Medals** (Total: {sport_champ_total} medals)!")
            
            # Display Podiums (Gold, Silver, Bronze top divisions)
            p_gold, p_silver, p_bronze = st.columns(3)
            with p_gold:
                g_divs = sport_tally.sort_values(by=["Gold"], ascending=False).iloc[0]["Division"] if sport_tally["Gold"].max() > 0 else "None"
                g_val = sport_tally["Gold"].max()
                st.metric("🥇 Most Gold", g_divs, f"{g_val} Golds")
            with p_silver:
                s_divs = sport_tally.sort_values(by=["Silver"], ascending=False).iloc[0]["Division"] if sport_tally["Silver"].max() > 0 else "None"
                s_val = sport_tally["Silver"].max()
                st.metric("🥈 Most Silver", s_divs, f"{s_val} Silvers")
            with p_bronze:
                b_divs = sport_tally.sort_values(by=["Bronze"], ascending=False).iloc[0]["Division"] if sport_tally["Bronze"].max() > 0 else "None"
                b_val = sport_tally["Bronze"].max()
                st.metric("🥉 Most Bronze", b_divs, f"{b_val} Bronzes")
                
            # Display the sport table
            st.dataframe(
                sport_tally,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Rank": st.column_config.NumberColumn("Rank", format="%d"),
                    "Division": st.column_config.TextColumn("Schools Division"),
                    "Gold": st.column_config.NumberColumn("Gold 🥇", format="%d"),
                    "Silver": st.column_config.NumberColumn("Silver 🥈", format="%d"),
                    "Bronze": st.column_config.NumberColumn("Bronze 🥉", format="%d"),
                    "Total": st.column_config.NumberColumn("Total Medals", format="%d")
                }
            )
            
            # Plotly chart for this sport
            fig_sport = px.bar(
                sport_tally.sort_values("Total", ascending=True), 
                y="Division", 
                x=["Gold", "Silver", "Bronze"],
                title=f"Medal Standings in {sport_filter} ({category_filter})",
                labels={"value": "Medal Count", "Division": "Schools Division", "variable": "Medal Type"},
                color_discrete_map={"Gold": "#F59E0B", "Silver": "#9CA3AF", "Bronze": "#B45309"},
                orientation="h",
                height=400
            )
            fig_sport.update_layout(barmode="stack", legend_title_text="Medal Color")
            st.plotly_chart(fig_sport, use_container_width=True)
        else:
            st.warning(f"No medals have been logged yet for {sport_filter} in {category_filter}.")

    # Tab 5: Dynamic PDF Certificate Generator
    with tab_cert:
        st.subheader("📜 Dynamic PDF Certificate Generator")
        st.markdown("Generate official, publication-quality **Certificates of Award** for winning teams instantly.")
        
        # Selection details
        c_col1, c_col2 = st.columns(2)
        with c_col1:
            cert_div = st.selectbox("Select Winning Schools Division", DIVISIONS, key="cert_div")
            cert_sport = st.selectbox("Select Sport / Discipline", ["Overall Standings"] + SPORTS, key="cert_sport")
        with c_col2:
            cert_rank = st.selectbox("Select Award / Placement", ["Champion", "1st Runner-Up", "2nd Runner-Up", "3rd Runner-Up"], key="cert_rank")
            cert_cat = st.selectbox("Select Category", ["Elementary", "Secondary", "Combined Division"], key="cert_cat")
            
        # Signatories section
        st.markdown("#### Custom Signatories & Details")
        sig_col1, sig_col2, sig_col3 = st.columns(3)
        with sig_col1:
            sig_name_1 = st.text_input("DepEd Region VII Regional Director", value="SALUSTIANO T. JIMENEZ, EdD, JD, CESO V")
            sig_role_1 = st.text_input("First Role Title", value="Regional Director, DepEd Region VII")
        with sig_col2:
            sig_name_2 = st.text_input("Host City Mayor", value="VALDEMAR M. CHIONG")
            sig_role_2 = st.text_input("Second Role Title", value="City Mayor, Naga City, Cebu (Host City)")
        with sig_col3:
            cert_date = st.text_input("Award Date / Location Detail", value="March 28, 2026 at the City of Naga, Cebu")

        def make_certificate_pdf(div, rank, sport, cat, sig1, role1, sig2, role2, date_str):
            # Setup memory buffer
            buffer = io.BytesIO()
            PAGE_SIZE = landscape(LETTER)  # 792 x 612
            PAGE_W, PAGE_H = PAGE_SIZE
            
            doc = SimpleDocTemplate(
                buffer,
                pagesize=PAGE_SIZE,
                leftMargin=54, rightMargin=54,
                topMargin=54, bottomMargin=54
            )
            
            NAVY = HexColor('#1E3A8A')
            GOLD = HexColor('#F59E0B')
            DARK_GRAY = HexColor('#1F2937')
            
            # Draw borders and signature lines in callback
            def draw_certificate_borders(canvas, doc):
                canvas.saveState()
                # Borders
                canvas.setStrokeColor(NAVY)
                canvas.setLineWidth(5)
                canvas.rect(20, 20, PAGE_W - 40, PAGE_H - 40, stroke=1, fill=0)
                
                canvas.setStrokeColor(GOLD)
                canvas.setLineWidth(1.5)
                canvas.rect(28, 28, PAGE_W - 56, PAGE_H - 56, stroke=1, fill=0)
                
                # Corner accents
                canvas.setStrokeColor(NAVY)
                canvas.setLineWidth(1)
                canvas.line(28, 50, 50, 50)
                canvas.line(50, 28, 50, 50)
                canvas.line(PAGE_W - 28, 50, PAGE_W - 50, 50)
                canvas.line(PAGE_W - 50, 28, PAGE_W - 50, 50)
                canvas.line(28, PAGE_H - 50, 50, PAGE_H - 50)
                canvas.line(50, PAGE_H - 28, 50, PAGE_H - 50)
                canvas.line(PAGE_W - 28, PAGE_H - 50, PAGE_W - 50, PAGE_H - 50)
                canvas.line(PAGE_W - 50, PAGE_H - 28, PAGE_W - 50, PAGE_H - 50)
                
                # Signatures
                canvas.setStrokeColor(DARK_GRAY)
                canvas.setLineWidth(0.75)
                canvas.line(100, 100, 310, 100)
                canvas.line(PAGE_W - 310, 100, PAGE_W - 100, 100)
                
                canvas.setFont('Times-Bold', 9)
                canvas.setFillColor(DARK_GRAY)
                canvas.drawCentredString(205, 85, html.escape(sig1).upper())
                canvas.setFont('Times-Roman', 8)
                canvas.drawCentredString(205, 72, html.escape(role1))
                
                canvas.setFont('Times-Bold', 9)
                canvas.drawCentredString(PAGE_W - 205, 85, html.escape(sig2).upper())
                canvas.setFont('Times-Roman', 8)
                canvas.drawCentredString(PAGE_W - 205, 72, html.escape(role2))
                canvas.restoreState()
                
            styles = getSampleStyleSheet()
            
            # Styles
            style_sub = ParagraphStyle('CSub', fontName='Times-Roman', fontSize=10, leading=14, textColor=DARK_GRAY, alignment=TA_CENTER)
            style_deped = ParagraphStyle('CDep', fontName='Times-Bold', fontSize=11, leading=15, textColor=NAVY, alignment=TA_CENTER)
            style_association = ParagraphStyle('CAssoc', fontName='Times-Bold', fontSize=14, leading=18, textColor=NAVY, alignment=TA_CENTER)
            style_title = ParagraphStyle('CTitle', fontName='Times-Bold', fontSize=24, leading=28, textColor=GOLD, alignment=TA_CENTER, spaceAfter=15)
            style_present = ParagraphStyle('CPres', fontName='Times-Italic', fontSize=12, leading=16, textColor=DARK_GRAY, alignment=TA_CENTER, spaceAfter=15)
            style_div = ParagraphStyle('CDiv', fontName='Times-Bold', fontSize=26, leading=30, textColor=NAVY, alignment=TA_CENTER, spaceAfter=12)
            style_achievement = ParagraphStyle('CAch', fontName='Times-Roman', fontSize=12, leading=18, textColor=DARK_GRAY, alignment=TA_CENTER)
            
            story = [
                Spacer(1, 10),
                Paragraph("Republic of the Philippines", style_sub),
                Paragraph("DEPARTMENT OF EDUCATION", style_deped),
                Paragraph("Region VII - Central Visayas", style_sub),
                Spacer(1, 15),
                Paragraph("CENTRAL VISAYAS REGIONAL ATHLETIC ASSOCIATION", style_association),
                Paragraph("CERTIFICATE OF AWARD", style_title),
                Paragraph("is proudly presented to the delegation of", style_present),
                Paragraph(html.escape(div).upper(), style_div),
            ]
            
            # Event phrase
            event_phrase = f"{cat} {sport}" if sport != "Overall Standings" else f"the {cat} General Championship"
            
            achievement_html = (
                f"for securing the rank of <b>{html.escape(rank).upper()}</b> in the "
                f"<b>{html.escape(event_phrase)}</b> competition "
                f"during the 2026 CVIRAA Sports Meet.<br/><br/>"
                f"Given this {html.escape(date_str)}, Philippines."
            )
            story.append(Paragraph(achievement_html, style_achievement))
            
            doc.build(story, onFirstPage=draw_certificate_borders)
            buffer.seek(0)
            return buffer.getvalue()

        # Generation Button
        st.markdown("<br/>", unsafe_allow_html=True)
        if st.button("🏆 Generate Official PDF Certificate", use_container_width=True):
            pdf_bytes = make_certificate_pdf(
                cert_div, cert_rank, cert_sport, cert_cat,
                sig_name_1, sig_role_1, sig_name_2, sig_role_2, cert_date
            )
            
            file_label = f"CVIRAA_Certificate_{cert_div.replace(' ', '_')}_{cert_rank.replace(' ', '_')}.pdf"
            
            st.success("✅ Certificate created successfully! Download it below:")
            st.download_button(
                label="📥 Download Certificate PDF",
                data=pdf_bytes,
                file_name=file_label,
                mime="application/pdf",
                use_container_width=True
            )

    # Tab 6: Interactive Spreadsheet Editor
    with tab_editor:
        st.subheader("✏️ Live Spreadsheet Editor")
        
        if not st.session_state.authenticated:
            st.warning("🔒 This editor is locked! Please go to the sidebar's Admin Console and enter the password to gain editing privileges.")
        else:
            st.info("Filter by Sport and Category to easily edit a clean 12-row table for that exact discipline. Changes are saved automatically when you click off a cell.")
            
            # Filters to make spreadsheet extremely compact and manageable (only 12 rows!)
            col_ed_sport, col_ed_cat = st.columns(2)
            with col_ed_sport:
                edit_sport = st.selectbox("Select Sport to Edit", SPORTS, key="ed_sport")
            with col_ed_cat:
                edit_cat = st.selectbox("Select Category to Edit", ["Elementary", "Secondary"], key="ed_cat")
                
            # Get the index subset of the data
            subset_df = st.session_state.medal_df[
                (st.session_state.medal_df["Sport"] == edit_sport) & 
                (st.session_state.medal_df["Category"] == edit_cat)
            ].copy()
            
            # Interactive dataframe editor
            edited_subset = st.data_editor(
                subset_df,
                column_config={
                    "Division": st.column_config.TextColumn("Schools Division", disabled=True),
                    "Category": st.column_config.TextColumn("Category", disabled=True),
                    "Sport": st.column_config.TextColumn("Sport", disabled=True),
                    "Gold": st.column_config.NumberColumn("Gold 🥇", min_value=0, step=1),
                    "Silver": st.column_config.NumberColumn("Silver 🥈", min_value=0, step=1),
                    "Bronze": st.column_config.NumberColumn("Bronze 🥉", min_value=0, step=1)
                },
                hide_index=True,
                num_rows="fixed",
                use_container_width=True
            )
            
            # Merge the edited subset back into the master dataframe if changes are made
            if not edited_subset.equals(subset_df):
                df_master = st.session_state.medal_df.copy()
                for idx, row in edited_subset.iterrows():
                    df_master.loc[idx, "Gold"] = row["Gold"]
                    df_master.loc[idx, "Silver"] = row["Silver"]
                    df_master.loc[idx, "Bronze"] = row["Bronze"]
                    
                st.session_state.medal_df = df_master
                save_data(df_master)
                st.success(f"Successfully saved edits for {edit_sport} ({edit_cat})! Leaderboards updated.")
                st.rerun()

    # Footer
    st.markdown("---")
    st.markdown("""
        <div style="text-align:center;color:#6B7280;font-size:0.8em;">
            CVIRAA Medal Tally System &bull; Designed for Region VII DepEd Schools Divisions &bull; Built with Streamlit & ReportLab
        </div>
    """, unsafe_allow_html=True)
