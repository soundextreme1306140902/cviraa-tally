import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
import io
import html
import time
import requests
import json
import urllib.parse
from datetime import datetime, timezone, timedelta

MANILA_TZ = timezone(timedelta(hours=8))

def get_manila_now():
    return datetime.now(MANILA_TZ)
from reportlab.lib.pagesizes import LETTER, portrait, landscape
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics import renderSVG
from reportlab.platypus import PageBreak
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    CV2_AVAILABLE = False

# Set page configuration
st.set_page_config(
    page_title="CVIRAA Medal Tally & Tournament Management System",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 📲 Telegram & Viber Notification Helpers
def send_telegram_message(bot_token, chat_id, text_message):
    if not bot_token or not chat_id:
        return False, "Missing Bot Token or Chat ID"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text_message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            return True, "Telegram Alert Sent Successfully!"
        else:
            return False, f"Telegram API Error ({response.status_code}): {response.text}"
    except Exception as e:
        return False, f"Connection Error: {str(e)}"

def send_viber_message(viber_token, receiver_id, text_message):
    if not viber_token or not receiver_id:
        return False, "Missing Viber Auth Token or Receiver ID"
    url = "https://chatapi.viber.com/pa/send_message"
    headers = {"X-Viber-Auth-Token": viber_token}
    payload = {
        "receiver": receiver_id,
        "min_api_version": 1,
        "type": "text",
        "text": text_message
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        res_json = response.json()
        if res_json.get("status") == 0:
            return True, "Viber Alert Sent Successfully!"
        else:
            return False, f"Viber API Error: {res_json.get('status_message')}"
    except Exception as e:
        return False, f"Connection Error: {str(e)}"

# Constants
CSV_FILE = "cviraa_medal_data_v2.csv"
SEED_FILE = "cviraa_initial_data_v2.csv"
PARTICIPANTS_CSV = "cviraa_participants_full.csv"
SEED_PARTICIPANTS_CSV = "cviraa_initial_participants.csv"
BILLETING_CSV = "cviraa_billeting_logs.csv"

DIVISIONS = [
    "Bogo City", "Bohol Province", "Carcar City", "Cebu City", 
    "Cebu Province", "Danao City", "Lapu-Lapu City", "Mandaue City", 
    "City of Naga", "Tagbilaran City", "Talisay City", "Toledo City"
]

SPORTS = [
    "Archery", "Arnis", "Athletics", "Badminton", "Baseball", 
    "Basketball", "Billiards", "Boxing", "Chess", "Dancesport", 
    "Football", "Futsal", "Gymnastics", "Pencak Silat", "Sepak Takraw", 
    "Softball", "Swimming", "Table Tennis", "Taekwondo", "Volleyball"
]

INDIVIDUAL_SPORTS = [
    "Archery", "Arnis", "Athletics", "Badminton", "Billiards", "Boxing", 
    "Chess", "Dancesport", "Gymnastics", "Pencak Silat", "Swimming", 
    "Table Tennis", "Taekwondo"
]
TEAM_SPORTS = [
    "Baseball", "Basketball", "Football", "Futsal", "Sepak Takraw", 
    "Softball", "Volleyball"
]


DELEGATION_CODES = {
    "Bogo City": "BOG", "Bohol Province": "BOH", "Carcar City": "CAR",
    "Cebu City": "CEB", "Cebu Province": "CBP", "Danao City": "DAN",
    "Lapu-Lapu City": "LAP", "Mandaue City": "MAN", "City of Naga": "NAG",
    "Tagbilaran City": "TAG", "Talisay City": "TAL", "Toledo City": "TOL"
}

ROLES = [
    "Athlete / Player", "Coach", "Co-Coach / Chaperone", 
    "TWG Member", "DepEd Regional Official", "Host Division Executive"
]

ALL_AFFILIATIONS = DIVISIONS + ["DepEd Regional Office VII", "City of Naga (Host TWG)"]

BILLETING_QUARTERS = [
    "Naga Central Elementary School (Main)", "Naga National High School",
    "Colon Elementary School", "Mainit National High School",
    "Langtad Elementary School", "Inayagan Elementary School",
    "Tinaan Elementary School", "Naalad Elementary School",
    "Uling National High School", "Naga City Integrated School",
    "Cantao-an Elementary School", "Lutac National High School"
]

# 🗺️ Venues & Coordinates Data
VENUES_DATA = [
    {
        "Venue_Name": "City of Naga Sports Complex & Athletic Oval",
        "Type": "Playing Venue",
        "Sports_Hosted": "Athletics, Football, Opening/Closing Ceremonies",
        "Address": "Poblacion, City of Naga, Cebu",
        "Lat": 10.2081,
        "Lon": 123.7583,
        "Distance": "0.5 km from City Hall",
        "Transport": "Coaster / Delegation Shuttle Bus"
    },
    {
        "Venue_Name": "Naga City Aquatic & Swimming Center",
        "Type": "Playing Venue",
        "Sports_Hosted": "Swimming",
        "Address": "Coastal Road, Naga City, Cebu",
        "Lat": 10.2088,
        "Lon": 123.7590,
        "Distance": "0.7 km from City Hall",
        "Transport": "Shuttle / Walk"
    },
    {
        "Venue_Name": "Teodoro Mendiola Sr. Sports Complex & Gymnasium",
        "Type": "Playing Venue",
        "Sports_Hosted": "Basketball, Volleyball, Badminton",
        "Address": "East Poblacion, City of Naga, Cebu",
        "Lat": 10.2075,
        "Lon": 123.7578,
        "Distance": "0.3 km from City Hall",
        "Transport": "Jeepney / Tricycle / Walk"
    },
    {
        "Venue_Name": "Enan Chiong Activity Center (ECAC)",
        "Type": "Playing Venue",
        "Sports_Hosted": "Boxing, Gymnastics, Pencak Silat, Taekwondo",
        "Address": "Poblacion Park, City of Naga, Cebu",
        "Lat": 10.2070,
        "Lon": 123.7580,
        "Distance": "0.2 km from City Hall",
        "Transport": "Walkable from City Center"
    },
    {
        "Venue_Name": "Naga Central Elementary School Gym",
        "Type": "Playing Venue",
        "Sports_Hosted": "Arnis, Dancesport, Futsal",
        "Address": "Central Street, Poblacion, City of Naga, Cebu",
        "Lat": 10.2095,
        "Lon": 123.7565,
        "Distance": "0.6 km from City Hall",
        "Transport": "Walk / Tricycle"
    },
    {
        "Venue_Name": "Naga National High School Sports Complex",
        "Type": "Playing Venue",
        "Sports_Hosted": "Table Tennis, Chess, Sepak Takraw",
        "Address": "West Poblacion, City of Naga, Cebu",
        "Lat": 10.2110,
        "Lon": 123.7550,
        "Distance": "1.0 km from City Hall",
        "Transport": "Tricycle / Shuttle"
    },
    {
        "Venue_Name": "Poblacion Tennis & Billiards Arena",
        "Type": "Playing Venue",
        "Sports_Hosted": "Billiards, Tennis",
        "Address": "Seaside Boulevard, City of Naga, Cebu",
        "Lat": 10.2065,
        "Lon": 123.7595,
        "Distance": "0.8 km from City Hall",
        "Transport": "Tricycle"
    },
    {
        "Venue_Name": "Ocean Park & Coastal Grounds",
        "Type": "Playing Venue",
        "Sports_Hosted": "Archery, Baseball, Softball",
        "Address": "South Coastal Bay, City of Naga, Cebu",
        "Lat": 10.2050,
        "Lon": 123.7610,
        "Distance": "1.2 km from City Hall",
        "Transport": "Delegation Bus"
    }
]

BILLETING_MAP_DATA = [
    {"Delegation": "Cebu City", "Billeting_Quarter": "Naga Central Elementary School", "Address": "Poblacion, Naga City", "Lat": 10.2095, "Lon": 123.7565},
    {"Delegation": "Bohol Province", "Billeting_Quarter": "Naga National High School", "Address": "West Poblacion, Naga City", "Lat": 10.2110, "Lon": 123.7550},
    {"Delegation": "Cebu Province", "Billeting_Quarter": "Colon Elementary School", "Address": "Brgy. Colon, Naga City", "Lat": 10.1980, "Lon": 123.7480},
    {"Delegation": "Mandaue City", "Billeting_Quarter": "Mainit National High School", "Address": "Brgy. Mainit, Naga City", "Lat": 10.2250, "Lon": 123.7400},
    {"Delegation": "Lapu-Lapu City", "Billeting_Quarter": "Langtad Elementary School", "Address": "Brgy. Langtad, Naga City", "Lat": 10.1850, "Lon": 123.7350},
    {"Delegation": "Tagbilaran City", "Billeting_Quarter": "Inayagan Elementary School", "Address": "Brgy. Inayagan, Naga City", "Lat": 10.2280, "Lon": 123.7650},
    {"Delegation": "Bogo City", "Billeting_Quarter": "Tinaan Elementary School", "Address": "Brgy. Tinaan, Naga City", "Lat": 10.2020, "Lon": 123.7520},
    {"Delegation": "Carcar City", "Billeting_Quarter": "Naalad Elementary School", "Address": "Brgy. Naalad, Naga City", "Lat": 10.2150, "Lon": 123.7450},
    {"Delegation": "Danao City", "Billeting_Quarter": "Uling National High School", "Address": "Brgy. Uling, Naga City", "Lat": 10.2350, "Lon": 123.7300},
    {"Delegation": "City of Naga", "Billeting_Quarter": "Naga City Integrated School", "Address": "Poblacion, Naga City", "Lat": 10.2085, "Lon": 123.7570},
    {"Delegation": "Talisay City", "Billeting_Quarter": "Cantao-an Elementary School", "Address": "Brgy. Cantao-an, Naga City", "Lat": 10.2200, "Lon": 123.7500},
    {"Delegation": "Toledo City", "Billeting_Quarter": "Lutac National High School", "Address": "Brgy. Lutac, Naga City", "Lat": 10.2300, "Lon": 123.7380}
]

# Initialize and load medal data
def load_medal_data():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
    elif os.path.exists(SEED_FILE):
        df = pd.read_csv(SEED_FILE)
    else:
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
    
    df["Gold"] = df["Gold"].astype(int)
    df["Silver"] = df["Silver"].astype(int)
    df["Bronze"] = df["Bronze"].astype(int)
    return df

def save_medal_data(df):
    df.to_csv(CSV_FILE, index=False)

def load_participants_data():
    if os.path.exists(PARTICIPANTS_CSV):
        df = pd.read_csv(PARTICIPANTS_CSV)
    elif os.path.exists(SEED_PARTICIPANTS_CSV):
        df = pd.read_csv(SEED_PARTICIPANTS_CSV)
    else:
        records = [
            {"Accreditation_ID": "CV26-ATH-1001", "Full_Name": "Juan Dela Cruz", "Role": "Athlete / Player", "Division": "Cebu City", "Category": "Secondary", "Sport_or_Committee": "Swimming", "Gender": "Male", "Status": "Verified"},
            {"Accreditation_ID": "CV26-ATH-1002", "Full_Name": "Maria Santos", "Role": "Athlete / Player", "Division": "Bohol Province", "Category": "Elementary", "Sport_or_Committee": "Athletics", "Gender": "Female", "Status": "Verified"},
            {"Accreditation_ID": "CV26-CCH-2001", "Full_Name": "Coach Roberto Gomez", "Role": "Coach", "Division": "Cebu City", "Category": "Secondary", "Sport_or_Committee": "Swimming", "Gender": "Male", "Status": "Verified"},
            {"Accreditation_ID": "CV26-TWG-3001", "Full_Name": "Dr. Arlene Cañete", "Role": "TWG Member", "Division": "DepEd Regional Office VII", "Category": "Regional TWG", "Sport_or_Committee": "Medical & First Aid TWG", "Gender": "Female", "Status": "Verified"},
            {"Accreditation_ID": "CV26-TWG-3002", "Full_Name": "Engr. Mark Yap", "Role": "TWG Member", "Division": "City of Naga (Host TWG)", "Category": "Host TWG", "Sport_or_Committee": "Secretariat & Records TWG", "Gender": "Male", "Status": "Verified"},
            {"Accreditation_ID": "CV26-CHP-3003", "Full_Name": "Elena Torralba", "Role": "Chaperone", "Division": "Tagbilaran City", "Category": "Elementary", "Sport_or_Committee": "Badminton", "Gender": "Female", "Status": "Verified"}
        ]
        df = pd.DataFrame(records)
        df.to_csv(PARTICIPANTS_CSV, index=False)
    return df

def save_participants_data(df):
    df.to_csv(PARTICIPANTS_CSV, index=False)

def load_billeting_data():
    if os.path.exists(BILLETING_CSV):
        df = pd.read_csv(BILLETING_CSV)
    else:
        records = [
            {"Log_ID": "LOG-1001", "Timestamp": "2026-09-10 06:30:00", "Accreditation_ID": "CV26-ATH-1001", "Full_Name": "Juan Dela Cruz", "Division": "Cebu City", "Quarter": "Naga Central Elementary School (Main)", "Action": "Log OUT (Left for Venue)", "Destination_Reason": "Naga City Aquatic Center (Swimming Heat)", "Officer_In_Charge": "Guard Ramos"},
            {"Log_ID": "LOG-1002", "Timestamp": "2026-09-10 06:45:00", "Accreditation_ID": "CV26-CCH-2001", "Full_Name": "Coach Roberto Gomez", "Division": "Cebu City", "Quarter": "Naga Central Elementary School (Main)", "Action": "Log OUT (Left for Venue)", "Destination_Reason": "Naga City Aquatic Center", "Officer_In_Charge": "Guard Ramos"},
            {"Log_ID": "LOG-1003", "Timestamp": "2026-09-10 12:15:00", "Accreditation_ID": "CV26-ATH-1001", "Full_Name": "Juan Dela Cruz", "Division": "Cebu City", "Quarter": "Naga Central Elementary School (Main)", "Action": "Log IN (Returned to Quarters)", "Destination_Reason": "Returned from Morning Swim Session", "Officer_In_Charge": "Teacher Santos"}
        ]
        df = pd.DataFrame(records)
        df.to_csv(BILLETING_CSV, index=False)
    return df

def save_billeting_data(df):
    df.to_csv(BILLETING_CSV, index=False)


def extract_accreditation_id(scanned_text):
    if not scanned_text:
        return ""
    text = scanned_text.strip()
    if "?id=" in text:
        parsed = urllib.parse.urlparse(text)
        params = urllib.parse.parse_qs(parsed.query)
        if "id" in params:
            return params["id"][0].upper()
    if text.startswith("http://") or text.startswith("https://"):
        text = text.split("/")[-1]
    return text.upper()

def calculate_ranking(df, sort_mode="Olympic Standard (Gold First)"):
    if df.empty:
        return pd.DataFrame(columns=["Rank", "IOC", "Division", "Gold", "Silver", "Bronze", "Total"])
    
    summary = df.groupby("Division").agg({
        "Gold": "sum",
        "Silver": "sum",
        "Bronze": "sum"
    }).reset_index()
    
    summary["Total"] = summary["Gold"] + summary["Silver"] + summary["Bronze"]
    summary["IOC"] = summary["Division"].map(lambda d: DELEGATION_CODES.get(d, "DEP"))
    
    if sort_mode == "Olympic Standard (Gold First)":
        summary = summary.sort_values(
            by=["Gold", "Silver", "Bronze", "Division"],
            ascending=[False, False, False, True]
        ).reset_index(drop=True)
    else:
        summary = summary.sort_values(
            by=["Total", "Gold", "Silver", "Bronze", "Division"],
            ascending=[False, False, False, False, True]
        ).reset_index(drop=True)
    
    def get_badge(rank):
        if rank == 1: return "🥇 1"
        elif rank == 2: return "🥈 2"
        elif rank == 3: return "🥉 3"
        else: return f"{rank}"
        
    summary["Rank"] = [get_badge(i + 1) for i in range(len(summary))]
    
    columns = ["Rank", "IOC", "Division", "Gold", "Silver", "Bronze", "Total"]
    return summary[columns]


# 📄 PDF EXECUTIVE SUMMARY REPORT GENERATOR (Publication-Quality for Regional Directors)

def get_qr_svg_string(text, size=180):
    """Generates pure SVG XML string for a scannable QR code."""
    try:
        qr_w = QrCodeWidget(str(text))
        bounds = qr_w.getBounds()
        w = bounds[2] - bounds[0]
        h = bounds[3] - bounds[1]
        d = Drawing(size, size, transform=[size/w, 0, 0, size/h, 0, 0])
        d.add(qr_w)
        svg_str = renderSVG.drawToString(d)
        return svg_str
    except Exception:
        return f'<img src="https://quickchart.io/qr?text={text}&size={size}" width="{size}" height="{size}"/>'

def generate_qr_drawing(text, size=80):
    """Generates ReportLab Drawing object with a vector QR Code."""
    qr_w = QrCodeWidget(str(text))
    bounds = qr_w.getBounds()
    w = bounds[2] - bounds[0]
    h = bounds[3] - bounds[1]
    d = Drawing(size, size, transform=[size/w, 0, 0, size/h, 0, 0])
    d.add(qr_w)
    return d

def make_single_accreditation_pass_pdf(p_row):
    """Generates a printable PDF Accreditation Pass with QR code for a single participant."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
    story = []
    
    NAVY = HexColor('#1E3A8A')
    GOLD = HexColor('#F59E0B')
    DARK_GRAY = HexColor('#374151')
    LIGHT_BG = HexColor('#F9FAFB')
    
    role_str = str(p_row.get('Role', 'Participant')).upper()
    role_color = NAVY
    if 'COACH' in role_str:
        role_color = HexColor('#059669') # Emerald
    elif 'CHAPERONE' in role_str:
        role_color = HexColor('#7C3AED') # Purple
    elif 'TWG' in role_str:
        role_color = HexColor('#D97706') # Amber Gold
        
    title_style = ParagraphStyle('TStyle', fontName='Helvetica-Bold', fontSize=12, leading=14, textColor=NAVY, alignment=TA_CENTER)
    sub_style = ParagraphStyle('SStyle', fontName='Helvetica-Bold', fontSize=10, leading=12, textColor=role_color, alignment=TA_CENTER)
    name_style = ParagraphStyle('NStyle', fontName='Helvetica-Bold', fontSize=16, leading=18, textColor=NAVY, alignment=TA_CENTER)
    meta_style = ParagraphStyle('MStyle', fontName='Helvetica', fontSize=10, leading=12, textColor=DARK_GRAY, alignment=TA_CENTER)
    id_style = ParagraphStyle('IDStyle', fontName='Helvetica-Bold', fontSize=12, leading=14, textColor=NAVY, alignment=TA_CENTER)
    
    qr_draw = generate_qr_drawing(p_row['Accreditation_ID'], size=100)
    
    card_content = [
        Paragraph('<b>DEPARTMENT OF EDUCATION • REGION VII</b>', title_style),
        Paragraph('CVIRAA REGIONAL ATHLETIC MEET 2026', meta_style),
        HRFlowable(width="100%", thickness=1.5, color=role_color, spaceBefore=4, spaceAfter=8),
        Paragraph(f'<b>OFFICIAL {role_str} PASS</b>', sub_style),
        Spacer(1, 10),
        Paragraph(f'<b>{p_row["Full_Name"]}</b>', name_style),
        Spacer(1, 4),
        Paragraph(f'<b>Division:</b> {p_row["Division"]}', meta_style),
        Paragraph(f'<b>Sport / Committee:</b> {p_row["Sport_or_Committee"]}', meta_style),
        Paragraph(f'<b>Category / Gender:</b> {p_row.get("Category","--")} ({p_row.get("Gender","--")})', meta_style),
        Spacer(1, 10),
        qr_draw,
        Spacer(1, 6),
        Paragraph(f'<b>ACCREDITATION ID: {p_row["Accreditation_ID"]}</b>', id_style),
        Spacer(1, 8),
        Paragraph('<i>Scannable for Venue Entry, Sports Events & Billeting Quarters</i>', ParagraphStyle('Foot', fontName='Helvetica-Oblique', fontSize=8, leading=10, textColor=DARK_GRAY, alignment=TA_CENTER))
    ]
    
    card_table = Table([[card_content]], colWidths=[320])
    card_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 2, role_color),
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_BG),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 15),
        ('BOTTOMPADDING', (0,0), (-1,-1), 15),
        ('LEFTPADDING', (0,0), (-1,-1), 15),
        ('RIGHTPADDING', (0,0), (-1,-1), 15),
    ]))
    
    story.append(card_table)
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def make_all_accreditation_passes_pdf(df):
    """Generates multi-page PDF batch containing 4 accreditation passes per page with vector QR Codes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    story = []
    
    NAVY = HexColor('#1E3A8A')
    GOLD = HexColor('#F59E0B')
    DARK_GRAY = HexColor('#374151')
    
    title_style = ParagraphStyle('TStyle', fontName='Helvetica-Bold', fontSize=9, leading=11, textColor=NAVY, alignment=TA_CENTER)
    sub_style = ParagraphStyle('SStyle', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=GOLD, alignment=TA_CENTER)
    name_style = ParagraphStyle('NStyle', fontName='Helvetica-Bold', fontSize=11, leading=13, textColor=NAVY, alignment=TA_CENTER)
    meta_style = ParagraphStyle('MStyle', fontName='Helvetica', fontSize=8, leading=10, textColor=DARK_GRAY, alignment=TA_CENTER)
    id_style = ParagraphStyle('IDStyle', fontName='Helvetica-Bold', fontSize=9, leading=11, textColor=NAVY, alignment=TA_CENTER)
    
    table_data = []
    row_cells = []
    
    for idx, p in df.iterrows():
        qr_draw = generate_qr_drawing(p['Accreditation_ID'], size=65)
        role_txt = str(p.get('Role','Participant')).upper()
        
        card_content = [
            Paragraph('<b>DEPED VII • CVIRAA 2026</b>', title_style),
            Paragraph(f'<b>{role_txt} PASS</b>', sub_style),
            Spacer(1, 3),
            Paragraph(f'<b>{p["Full_Name"]}</b>', name_style),
            Paragraph(f'{p["Division"]}', meta_style),
            Paragraph(f'{p["Sport_or_Committee"]}', meta_style),
            Spacer(1, 3),
            qr_draw,
            Spacer(1, 2),
            Paragraph(f'<b>ID: {p["Accreditation_ID"]}</b>', id_style)
        ]
        
        card_table = Table([[card_content]], colWidths=[240])
        card_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1.5, NAVY),
            ('BACKGROUND', (0,0), (-1,-1), HexColor('#F9FAFB')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        
        row_cells.append(card_table)
        
        if len(row_cells) == 2:
            table_data.append(row_cells)
            row_cells = []
            
        if len(table_data) == 2:
            page_table = Table(table_data, colWidths=[250, 250])
            page_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ]))
            story.append(page_table)
            story.append(PageBreak())
            table_data = []
            
    if row_cells:
        if len(row_cells) == 1:
            row_cells.append('')
        table_data.append(row_cells)
        
    if table_data:
        page_table = Table(table_data, colWidths=[250, 250])
        page_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(page_table)
        
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def make_executive_summary_report_pdf(medal_df, rd_name, date_str, venue_str):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=portrait(LETTER),
        leftMargin=36, rightMargin=36,
        topMargin=36, bottomMargin=36
    )
    
    NAVY = HexColor('#1E3A8A')
    GOLD = HexColor('#F59E0B')
    DARK_GRAY = HexColor('#1F2937')
    LIGHT_BG = HexColor('#F3F4F6')
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('RTitle', fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=NAVY, alignment=TA_CENTER)
    sub_style = ParagraphStyle('RSub', fontName='Helvetica', fontSize=10, leading=13, textColor=DARK_GRAY, alignment=TA_CENTER)
    h2_style = ParagraphStyle('RH2', fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=NAVY, spaceBefore=10, spaceAfter=6)
    body_style = ParagraphStyle('RBody', fontName='Helvetica', fontSize=9, leading=12, textColor=DARK_GRAY)
    
    tally = calculate_ranking(medal_df, "Olympic Standard (Gold First)")
    total_g = tally["Gold"].sum()
    total_s = tally["Silver"].sum()
    total_b = tally["Bronze"].sum()
    total_all = tally["Total"].sum()
    leader_div = tally.iloc[0]["Division"] if not tally.empty else "N/A"
    leader_golds = tally.iloc[0]["Gold"] if not tally.empty else 0
    
    story = [
        Paragraph("<b>REPUBLIC OF THE PHILIPPINES &bull; DEPARTMENT OF EDUCATION</b>", sub_style),
        Paragraph("<b>REGION VII - CENTRAL VISAYAS &bull; REGIONAL ATHLETIC MEET 2026</b>", sub_style),
        Spacer(1, 4),
        Paragraph("<b>EXECUTIVE ATHLETIC PERFORMANCE SUMMARY REPORT</b>", title_style),
        Paragraph(f"Official Leaderboard & Tournament Status &bull; As of {html.escape(date_str)} ({html.escape(venue_str)})", sub_style),
        Spacer(1, 10),
        HRFlowable(width="100%", thickness=2, color=NAVY, spaceAfter=10),
    ]
    
    # Metrics Cards Table
    metrics_data = [
        [
            Paragraph(f"<b>General Tournament Leader</b><br/><font size=12 color='#1E3A8A'><b>{html.escape(leader_div)}</b></font><br/>{leader_golds} Gold Medals", body_style),
            Paragraph(f"<b>Total Medals Distributed</b><br/><font size=12 color='#F59E0B'><b>{total_all} Medals</b></font><br/>🥇 {total_g} | 🥈 {total_s} | 🥉 {total_b}", body_style),
            Paragraph("<b>Participating Delegations</b><br/><font size=12 color='#1E3A8A'><b>12 Schools Divisions</b></font><br/>Central Visayas Region VII", body_style)
        ]
    ]
    t_metrics = Table(metrics_data, colWidths=[180, 180, 180])
    t_metrics.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_BG),
        ('BOX', (0,0), (-1,-1), 1, NAVY),
        ('INNERGRID', (0,0), (-1,-1), 0.5, HexColor('#D1D5DB')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_metrics)
    story.append(Spacer(1, 12))
    
    # Official Leaderboard Table
    story.append(Paragraph("<b>1. OFFICIAL REGIONAL MEDAL STANDINGS (OLYMPIC STANDARD)</b>", h2_style))
    
    table_headers = ["Rank", "Code", "Schools Division", "Gold 🥇", "Silver 🥈", "Bronze 🥉", "Total"]
    table_data = [table_headers]
    
    for _, row in tally.iterrows():
        table_data.append([
            str(row["Rank"]),
            str(row["IOC"]),
            str(row["Division"]),
            str(row["Gold"]),
            str(row["Silver"]),
            str(row["Bronze"]),
            str(row["Total"])
        ])
        
    t_standings = Table(table_data, colWidths=[45, 45, 210, 60, 60, 60, 60])
    t_standings.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('TEXTCOLOR', (0,0), (-1,0), HexColor('#FFFFFF')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ALIGN', (2,1), (2,-1), 'LEFT'),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#E5E7EB')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [HexColor('#FFFFFF'), LIGHT_BG]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_standings)
    story.append(Spacer(1, 15))
    
    # Category Analysis & Signatures
    story.append(Paragraph("<b>2. CERTIFICATION & REGIONAL ENDORSEMENT</b>", h2_style))
    story.append(Paragraph("This document certifies the official regional athletic tally compiled by the CVIRAA Secretariat & TWG Records Committee.", body_style))
    story.append(Spacer(1, 20))
    
    sig_data = [
        [
            Paragraph(f"Prepared & Certified Correct:<br/><br/><br/><b>EXECUTIVE SECRETARIAT TWG</b><br/>CVIRAA Records Officer", body_style),
            Paragraph(f"Approved & Submitted By:<br/><br/><br/><b>{html.escape(rd_name).upper()}</b><br/>Regional Director, DepEd Region VII", body_style)
        ]
    ]
    t_sig = Table(sig_data, colWidths=[270, 270])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_sig)
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# Initialize session state variables
if 'medal_df' not in st.session_state:
    st.session_state.medal_df = load_medal_data()

if 'participants_df' not in st.session_state:
    st.session_state.participants_df = load_participants_data()

if 'billeting_df' not in st.session_state:
    st.session_state.billeting_df = load_billeting_data()

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if 'kiosk_active' not in st.session_state:
    st.session_state.kiosk_active = False

if 'kiosk_slide_index' not in st.session_state:
    st.session_state.kiosk_slide_index = 0

ADMIN_PASSWORD = "cviraa2026"

# 📺 TV KIOSK OVERRIDE LAYOUT
if st.session_state.kiosk_active:
    st.markdown("""
        <style>
            [data-testid="stSidebar"] { display: none !important; }
            header, footer { visibility: hidden !important; height: 0px !important; }
            .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; max-width: 95% !important; }
            .kiosk-title { font-size: 2.8rem !important; font-weight: 900 !important; color: #F59E0B !important; text-align: center; margin: 0px !important; letter-spacing: 2px; }
            .kiosk-subtitle { font-size: 1.4rem !important; color: white !important; text-align: center; margin: 5px 0 0 0 !important; font-weight: 500; }
            div[data-testid="stMetricValue"] { font-size: 3rem !important; font-weight: 900 !important; color: #1E3A8A !important; }
            div[data-testid="stMetricLabel"] { font-size: 1.3rem !important; font-weight: bold !important; }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <div style="background-color:#1E3A8A;padding:15px;border-radius:10px;text-align:center;margin-bottom:15px;position:relative;">
            <div style="position:absolute;top:20px;left:25px;background-color:#EF4444;color:white;padding:5px 12px;border-radius:20px;font-size:0.9em;font-weight:bold;animation: pulse 1s infinite;display:flex;align-items:center;gap:6px;">
                <span style="height:10px;width:10px;background-color:white;border-radius:50%;display:inline-block;"></span> LIVE OLYMPIC SCOREBOARD
            </div>
            <h1 class="kiosk-title">🏆 CVIRAA OLYMPIC MEDAL STANDINGS 🏆</h1>
            <p class="kiosk-subtitle">Central Visayas Regional Athletic Association Meet (Naga City, Cebu)</p>
        </div>
    """, unsafe_allow_html=True)

    kiosk_slides = st.session_state.get("kiosk_slides", ["🏆 Overall Leaderboard", "🎒 Elementary Standings", "🎓 Secondary Standings"])
    kiosk_speed = st.session_state.get("kiosk_speed", 10)
    
    if not kiosk_slides:
        kiosk_slides = ["🏆 Overall Leaderboard"]
        
    st.session_state.kiosk_slide_index = st.session_state.kiosk_slide_index % len(kiosk_slides)
    current_slide = kiosk_slides[st.session_state.kiosk_slide_index]
    
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
    
    overall_tally = calculate_ranking(st.session_state.medal_df)
    
    if current_slide == "🏆 Overall Leaderboard":
        if not overall_tally.empty:
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("🏅 Olympic General Leader", overall_tally.iloc[0]["Division"], f"{overall_tally.iloc[0]['Gold']} Golds")
            with m2:
                st.metric("✨ Total Gold Medals", int(overall_tally["Gold"].sum()))
            with m3:
                st.metric("🏃 Active Delegations", 12)
                
        col_t1, col_t2 = st.columns([5, 5])
        with col_t1:
            st.dataframe(
                overall_tally,
                use_container_width=True,
                hide_index=True,
                height=450,
                column_config={
                    "Rank": st.column_config.TextColumn("Rank"),
                    "IOC": st.column_config.TextColumn("Code"),
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
            
    st.session_state.kiosk_slide_index = (st.session_state.kiosk_slide_index + 1) % len(kiosk_slides)
    time.sleep(kiosk_speed)
    st.rerun()

# 🏡 STANDARD VIEW
else:
    st.markdown("""
        <div style="background-color:#1E3A8A;padding:20px;border-radius:10px;text-align:center;margin-bottom:20px">
            <h1 style="color:#F59E0B;margin:0;font-family:Arial, sans-serif;font-weight:bold;">🏆 CENTRAL VISAYAS REGIONAL ATHLETIC ASSOCIATION</h1>
            <h3 style="color:white;margin:5px 0 0 0;font-family:Arial, sans-serif;">CVIRAA Olympic Medal Standings & Management Portal</h3>
            <p style="color:#D1D5DB;margin:5px 0 0 0;font-size:0.9em;">Official 12-Division Format &bull; Olympic Gold-First Sorting &bull; Google Maps Navigation &bull; Billeting Curfew &bull; Telegram Alerts</p>
        </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.image("https://img.icons8.com/color/144/trophy.png", width=100)
        st.title("⚙️ System Control")
        
        with st.expander("📺 TV Display / Kiosk Settings", expanded=False):
            st.markdown("Configure dynamic rotating kiosk scoreboard for venue LED screens.")
            kiosk_slides_choices = ["🏆 Overall Leaderboard", "🎒 Elementary Standings", "🎓 Secondary Standings"]
            selected_k_slides = st.multiselect("Slides to Cycle", options=kiosk_slides_choices, default=kiosk_slides_choices)
            k_speed = st.slider("Rotation Speed (seconds)", min_value=3, max_value=60, value=10, step=1)
            
            if st.button("🚀 Launch TV Kiosk Mode", use_container_width=True):
                st.session_state.kiosk_slides = selected_k_slides
                st.session_state.kiosk_speed = k_speed
                st.session_state.kiosk_slide_index = 0
                st.session_state.kiosk_active = True
                st.rerun()
                
        st.markdown("<hr/>", unsafe_allow_html=True)
        st.subheader("🛡️ Admin Console")
        
        if not st.session_state.authenticated:
            pwd_input = st.text_input("Enter Admin Password (cviraa2026)", type="password")
            if st.button("Unlock Admin Features", use_container_width=True):
                if pwd_input == ADMIN_PASSWORD:
                    st.session_state.authenticated = True
                    st.success("Access Granted!")
                    st.rerun()
                else:
                    st.error("Incorrect password!")
        else:
            st.success("🔓 Authenticated Session")
            if st.button("Lock Console", use_container_width=True):
                st.session_state.authenticated = False
                st.rerun()
                
            st.markdown("---")
            with st.expander("📝 Quick Medal Input Form", expanded=True):
                selected_div = st.selectbox("Select Division", DIVISIONS)
                selected_cat = st.radio("Select Category", ["Elementary", "Secondary"])
                selected_sport = st.selectbox("Select Sport", SPORTS)
                
                col1, col2, col3 = st.columns(3)
                with col1: gold_in = st.number_input("Gold 🥇", min_value=0, step=1, value=0)
                with col2: silver_in = st.number_input("Silver 🥈", min_value=0, step=1, value=0)
                with col3: bronze_in = st.number_input("Bronze 🥉", min_value=0, step=1, value=0)
                    
                update_mode = st.selectbox("Update Mode", ["Add to existing", "Overwrite existing"])
                
                if st.button("💾 Apply Medal Update", use_container_width=True):
                    df = st.session_state.medal_df.copy()
                    idx = df[(df["Division"] == selected_div) & (df["Category"] == selected_cat) & (df["Sport"] == selected_sport)].index
                    
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
                        save_medal_data(df)
                        st.success(f"Updated {selected_sport} for {selected_div} successfully!")
                        st.rerun()

        st.markdown("---")
        with st.expander("📥 Import & Export Data", expanded=True):
            st.markdown("##### 📂 Upload / Restore CSV Data")
            uploaded_csv = st.file_uploader("Upload CSV File (e.g. cviraa_mock_data_v3.csv)", type=["csv"], key="sidebar_csv_import")
            if uploaded_csv is not None:
                try:
                    u_df = pd.read_csv(uploaded_csv)
                    if {"Division", "Category", "Sport", "Gold", "Silver", "Bronze"}.issubset(u_df.columns):
                        st.session_state.medal_df = u_df
                        save_medal_data(u_df)
                        st.success("✅ Medal Database successfully imported!")
                        st.rerun()
                    elif {"Accreditation_ID", "Full_Name"}.issubset(u_df.columns):
                        st.session_state.participants_df = u_df
                        save_participants_data(u_df)
                        st.success("✅ Participant Roster successfully imported!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid CSV format. Missing required columns.")
                except Exception as e:
                    st.error(f"Error reading CSV: {e}")
            
            st.markdown("---")
            st.markdown("##### 📥 Export / Download CSVs")
            csv_data = st.session_state.medal_df.to_csv(index=False)
            st.download_button("📥 Download Medals CSV", data=csv_data, file_name="cviraa_medals.csv", mime="text/csv", use_container_width=True)
            p_csv_data = st.session_state.participants_df.to_csv(index=False)
            st.download_button("📥 Download Participants CSV", data=p_csv_data, file_name="cviraa_participants.csv", mime="text/csv", use_container_width=True)

        if st.session_state.authenticated:
            with st.expander("⚠️ Danger Zone"):
                if st.button("🔄 Reset Medals to Zero", use_container_width=True):
                    df = st.session_state.medal_df.copy()
                    df["Gold"] = 0; df["Silver"] = 0; df["Bronze"] = 0
                    st.session_state.medal_df = df
                    save_medal_data(df)
                    st.success("Medals reset to zero!")
                    st.rerun()

    # Application Tabs
    (
        tab_overall, tab_elem, tab_sec, tab_sport, tab_analytics, tab_pdf_report, tab_maps, 
        tab_reg, tab_coach, tab_billeting, tab_bot, 
        tab_pass, tab_cert, tab_editor
    ) = st.tabs([
        "🏆 Overall Standings", 
        "🎒 Elementary Division", 
        "🎓 Secondary Division",
        "🏅 Sport Breakdowns",
        "📊 Team vs Individual Analytics",
        "📄 Executive Summary PDF Report",
        "🗺️ Venue & Billeting Google Maps",
        "👥 Players, Coaches & TWG",
        "📋 Coach Hub & Portal",
        "🏠 Billeting Tracker & Curfew",
        "📲 Telegram/Viber Bot Center",
        "📇 Accreditation Pass",
        "📜 Award Certificates",
        "✏️ Spreadsheet Editor"
    ])

    sort_preference = st.sidebar.radio("Olympic Ranking Mode", ["Olympic Standard (Gold First)", "Total Medals Count"])
    overall_tally = calculate_ranking(st.session_state.medal_df, sort_preference)
    elem_tally = calculate_ranking(st.session_state.medal_df[st.session_state.medal_df["Category"] == "Elementary"], sort_preference)
    sec_tally = calculate_ranking(st.session_state.medal_df[st.session_state.medal_df["Category"] == "Secondary"], sort_preference)

    # TAB 1: Overall
    with tab_overall:
        st.subheader("Overall Medal Standings (Olympic Ranking Standard)")
        
        if len(overall_tally) >= 3:
            st.markdown("### 🥇 Olympic Podium Leaders")
            p1, p2, p3 = st.columns(3)
            with p1:
                st.markdown(f"""
                    <div style="background-color:#FEF3C7;border:2px solid #F59E0B;padding:15px;border-radius:10px;text-align:center;">
                        <h2 style="color:#B45309;margin:0;">🥇 GOLD LEADER</h2>
                        <h1 style="color:#1E3A8A;margin:5px 0;">{overall_tally.iloc[0]['Division']}</h1>
                        <p style="font-size:1.2em;font-weight:bold;color:#D97706;margin:0;">{overall_tally.iloc[0]['Gold']} Golds &bull; {overall_tally.iloc[0]['Total']} Total Medals</p>
                    </div>
                """, unsafe_allow_html=True)
            with p2:
                st.markdown(f"""
                    <div style="background-color:#F3F4F6;border:2px solid #9CA3AF;padding:15px;border-radius:10px;text-align:center;">
                        <h2 style="color:#4B5563;margin:0;">🥈 2nd PLACE</h2>
                        <h1 style="color:#1E3A8A;margin:5px 0;">{overall_tally.iloc[1]['Division']}</h1>
                        <p style="font-size:1.2em;font-weight:bold;color:#4B5563;margin:0;">{overall_tally.iloc[1]['Gold']} Golds &bull; {overall_tally.iloc[1]['Total']} Total Medals</p>
                    </div>
                """, unsafe_allow_html=True)
            with p3:
                st.markdown(f"""
                    <div style="background-color:#FFEDD5;border:2px solid #C2410C;padding:15px;border-radius:10px;text-align:center;">
                        <h2 style="color:#C2410C;margin:0;">🥉 3rd PLACE</h2>
                        <h1 style="color:#1E3A8A;margin:5px 0;">{overall_tally.iloc[2]['Division']}</h1>
                        <p style="font-size:1.2em;font-weight:bold;color:#C2410C;margin:0;">{overall_tally.iloc[2]['Gold']} Golds &bull; {overall_tally.iloc[2]['Total']} Total Medals</p>
                    </div>
                """, unsafe_allow_html=True)
            st.markdown("<br/>", unsafe_allow_html=True)

        st.dataframe(
            overall_tally,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Rank": st.column_config.TextColumn("Rank", width="small"),
                "IOC": st.column_config.TextColumn("Code", width="small"),
                "Division": st.column_config.TextColumn("Schools Division"),
                "Gold": st.column_config.NumberColumn("Gold 🥇", format="%d"),
                "Silver": st.column_config.NumberColumn("Silver 🥈", format="%d"),
                "Bronze": st.column_config.NumberColumn("Bronze 🥉", format="%d"),
                "Total": st.column_config.NumberColumn("Total Medals", format="%d")
            }
        )

    # TAB 2: Elementary
    with tab_elem:
        st.subheader("Elementary Division Medal Standings")
        st.dataframe(elem_tally, use_container_width=True, hide_index=True)

    # TAB 3: Secondary
    with tab_sec:
        st.subheader("Secondary Division Medal Standings")
        st.dataframe(sec_tally, use_container_width=True, hide_index=True)

    # TAB 4: Sport Breakdown
    with tab_sport:
        st.subheader("🏅 Sport-by-Sport Medal Breakdowns")
        sport_filter = st.selectbox("Select Sport to Analyze", SPORTS)
        sport_df = st.session_state.medal_df[st.session_state.medal_df["Sport"] == sport_filter]
        sport_tally = calculate_ranking(sport_df, sort_preference)
        st.dataframe(sport_tally, use_container_width=True, hide_index=True)


    # TAB 5: Team vs Individual Analytics (NEW!)
    with tab_analytics:
        st.subheader("📊 Team Sports vs. Individual Disciplines Analytics Engine")
        st.markdown("Analyze how delegations perform in individual athletic disciplines versus head-to-head team championships.")
        
        ind_df = st.session_state.medal_df[st.session_state.medal_df["Sport"].isin(INDIVIDUAL_SPORTS)]
        team_df = st.session_state.medal_df[st.session_state.medal_df["Sport"].isin(TEAM_SPORTS)]
        
        ind_tally = calculate_ranking(ind_df, sort_preference)
        team_tally = calculate_ranking(team_df, sort_preference)
        
        col_an1, col_an2 = st.columns(2)
        with col_an1:
            st.markdown("#### 🏃 Individual Disciplines Leaderboard")
            st.caption("Includes: Swimming, Athletics, Archery, Arnis, Taekwondo, Chess, Gymnastics, etc.")
            st.dataframe(ind_tally, use_container_width=True, hide_index=True, height=350)
            
        with col_an2:
            st.markdown("#### 🏀 Team Sports Leaderboard")
            st.caption("Includes: Basketball, Volleyball, Football, Baseball, Softball, Sepak Takraw, Futsal")
            st.dataframe(team_tally, use_container_width=True, hide_index=True, height=350)
            
        st.markdown("---")
        st.markdown("#### 🔥 Regional Sports Dominance Matrix (Heatmap)")
        
        pivot_df = st.session_state.medal_df.pivot_table(index="Division", columns="Sport", values="Gold", aggfunc="sum", fill_value=0)
        fig_heat = px.imshow(
            pivot_df,
            labels=dict(x="Sport Discipline", y="Schools Division", color="Gold Medals"),
            x=pivot_df.columns,
            y=pivot_df.index,
            color_continuous_scale="Viridis",
            aspect="auto",
            height=450
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    # TAB 6: Executive Summary PDF Report (NEW!)
    with tab_pdf_report:
        st.subheader("📄 Executive Athletic Performance Summary Report Generator")
        st.markdown("Generate a publication-quality Executive PDF Report formatted for Regional Directors, Superintendents, and Sports Officers.")
        
        rep_col1, rep_col2 = st.columns(2)
        with rep_col1:
            rep_rd = st.text_input("Regional Director Name", value="SALUSTIANO T. JIMENEZ, EdD, JD, CESO V")
            rep_date = st.text_input("Report Date", value=get_manila_now().strftime("%B %d, 2026"))
        with rep_col2:
            rep_venue = st.text_input("Host City / Location Detail", value="City of Naga, Cebu")
            
        if st.button("📄 Generate Executive PDF Report", use_container_width=True):
            pdf_bytes = make_executive_summary_report_pdf(st.session_state.medal_df, rep_rd, rep_date, rep_venue)
            
            st.success("✅ Executive Athletic Report generated successfully! Download below:")
            st.download_button(
                label="📥 Download Executive Summary PDF Report",
                data=pdf_bytes,
                file_name="CVIRAA_2026_Executive_Summary_Report.pdf",
                mime="application/pdf",
                use_container_width=True
            )


    # TAB 7: 🗺️ Venue & Billeting Google Maps (NEW!)
    with tab_maps:
        st.subheader("🗺️ CVIRAA Playing Venues & Billeting Quarters Map Navigator")
        st.markdown("Interactive Google Maps integration for players, coaches, chaperones, and TWG officers.")
        
        map_mode = st.radio("Select View Mode", ["🏟️ Playing Venues & Sports Arenas", "🏫 Delegation Billeting Schools", "📍 Combined Overview Map"], horizontal=True)
        
        # Build map dataframe
        map_records = []
        if map_mode in ["🏟️ Playing Venues & Sports Arenas", "📍 Combined Overview Map"]:
            for v in VENUES_DATA:
                map_records.append({
                    "Name": v["Venue_Name"],
                    "Category": "Playing Venue",
                    "lat": v["Lat"],
                    "lon": v["Lon"],
                    "Details": v["Sports_Hosted"],
                    "Address": v["Address"]
                })
        if map_mode in ["🏫 Delegation Billeting Schools", "📍 Combined Overview Map"]:
            for b in BILLETING_MAP_DATA:
                map_records.append({
                    "Name": f"{b['Delegation']} Billeting ({b['Billeting_Quarter']})",
                    "Category": "Billeting School",
                    "lat": b["Lat"],
                    "lon": b["Lon"],
                    "Details": f"Delegation: {b['Delegation']}",
                    "Address": b["Address"]
                })
                
        map_df = pd.DataFrame(map_records)
        
        st.markdown("#### 🗺️ Interactive Location Map (City of Naga, Cebu)")
        st.map(map_df, latitude="lat", longitude="lon", size=20, zoom=12, use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 🧭 Venue Directions & Google Maps Direct Launcher")
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown("#### 🏟️ Select Playing Venue / Discipline")
            sel_venue_name = st.selectbox("Choose Playing Venue", [v["Venue_Name"] for v in VENUES_DATA])
            target_v = next((v for v in VENUES_DATA if v["Venue_Name"] == sel_venue_name), VENUES_DATA[0])
            
            st.info(f"""
                **Venue**: {target_v['Venue_Name']}<br/>
                **Sports Hosted**: {target_v['Sports_Hosted']}<br/>
                **Address**: {target_v['Address']}<br/>
                **Distance**: {target_v['Distance']}<br/>
                **Recommended Transport**: {target_v['Transport']}
            """, icon="🏟️")
            
            # Google Maps Link
            gmaps_url = f"https://www.google.com/maps/dir/?api=1&destination={target_v['Lat']},{target_v['Lon']}&destination_place_id={urllib.parse.quote(target_v['Venue_Name'])}"
            st.link_button("🧭 Open Live Navigation in Google Maps", gmaps_url, use_container_width=True)

        with col_m2:
            st.markdown("#### 🏫 Select Delegation Billeting School")
            sel_billet_div = st.selectbox("Choose Delegation", DIVISIONS, index=3) # Default Cebu City
            target_b = next((b for b in BILLETING_MAP_DATA if b["Delegation"] == sel_billet_div), BILLETING_MAP_DATA[0])
            
            st.success(f"""
                **Delegation**: {target_b['Delegation']}<br/>
                **Assigned School**: {target_b['Billeting_Quarter']}<br/>
                **Address**: {target_b['Address']}
            """, icon="🏫")
            
            bgmaps_url = f"https://www.google.com/maps/dir/?api=1&destination={target_b['Lat']},{target_b['Lon']}"
            st.link_button("🧭 Navigate to Billeting School in Google Maps", bgmaps_url, use_container_width=True)

    # TAB 6: 👥 Players, Coaches & TWG Registry
    with tab_reg:
        st.subheader("👥 Players, Coaches & Technical Working Group (TWG) Registry")
        pdf = st.session_state.participants_df
        
        reg_form_exp, bulk_exp = st.tabs(["📝 Add Individual Participant", "📂 Bulk CSV Import & Export"])
        with reg_form_exp:
            st.markdown("#### Add New Participant Record")
            c_r1, c_r2, c_r3 = st.columns(3)
            with c_r1:
                p_name = st.text_input("Full Name (First, Last)")
                p_role = st.selectbox("Participant Role", ROLES)
            with c_r2:
                p_div = st.selectbox("Schools Division / Affiliation", ALL_AFFILIATIONS)
                p_cat = st.selectbox("Category Level", ["Elementary", "Secondary", "Regional TWG", "Host TWG"])
            with c_r3:
                p_sport = st.text_input("Sport or Committee Name", value="Swimming")
                p_gender = st.selectbox("Gender", ["Male", "Female"])
                p_status = st.selectbox("Verification Status", ["Verified", "Pending Document Check", "Incomplete RSAC"])
                
            if st.button("➕ Register Participant", use_container_width=True):
                if p_name.strip() == "":
                    st.error("Participant name cannot be empty!")
                else:
                    prefix = "ATH" if "Athlete" in p_role or "Player" in p_role else ("CCH" if "Coach" in p_role else "TWG")
                    new_id = f"CV26-{prefix}-{1000 + len(pdf) + 1}"
                    new_row = {
                        "Accreditation_ID": new_id,
                        "Full_Name": p_name,
                        "Role": p_role,
                        "Division": p_div,
                        "Category": p_cat,
                        "Sport_or_Committee": p_sport,
                        "Gender": p_gender,
                        "Status": p_status
                    }
                    pdf_updated = pd.concat([pdf, pd.DataFrame([new_row])], ignore_index=True)
                    st.session_state.participants_df = pdf_updated
                    save_participants_data(pdf_updated)
                    st.success(f"Successfully registered **{p_name}** with ID: **{new_id}**!")
                    st.rerun()

        with bulk_exp:
            st.markdown("#### 📂 Bulk Import / Export Roster CSV")
            roster_csv = st.session_state.participants_df.to_csv(index=False)
            st.download_button("📥 Export Current Roster (CSV)", data=roster_csv, file_name="cviraa_participants_full.csv", mime="text/csv", use_container_width=True)

        st.markdown("---")
        st.dataframe(st.session_state.participants_df, use_container_width=True, hide_index=True)

    # TAB 7: 📋 Coach Hub & Portal
    with tab_coach:
        st.subheader("📋 Coach Hub & Delegation Management Portal")
        st.markdown("Dedicated portal for Head Coaches, Assistant Coaches, and Delegation Chaperones.")
        
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1: sel_c_div = st.selectbox("Select Your Delegation", DIVISIONS, key="c_portal_div")
        with col_c2: sel_c_cat = st.selectbox("Select Category", ["Elementary", "Secondary"], key="c_portal_cat")
        with col_c3: sel_c_sport = st.selectbox("Select Sport Discipline", SPORTS, key="c_portal_sport")
        
        c_p_df = st.session_state.participants_df[
            (st.session_state.participants_df["Division"] == sel_c_div) & 
            (st.session_state.participants_df["Sport_or_Committee"] == sel_c_sport)
        ]
        
        st.markdown("#### 🏃 Delegation Team Roster Checklist")
        st.dataframe(c_p_df, use_container_width=True, hide_index=True)

    # TAB 8: 🏠 Billeting Tracker & Curfew
    with tab_billeting:
        st.subheader("🏠 Billeting Quarters Log-In / Log-Out Tracker & Curfew Monitor")
        st.markdown("Track departures to playing venues and arrivals back at billeting quarters using **Mobile Phone Camera QR Scanning, Barcode Guns, or Manual Selection**.")
        
        b_df = st.session_state.billeting_df
        p_df = st.session_state.participants_df
        
        selected_participant_from_scan = None
        
        # Check if URL parameter provided an ID from direct smartphone camera scan
        if scanned_url_id:
            matched_url_p = p_df[p_df["Accreditation_ID"].str.upper() == scanned_url_id.upper()]
            if not matched_url_p.empty:
                selected_participant_from_scan = matched_url_p.iloc[0]
                st.success(f"📱 **QR CODE SCANNED FROM PHONE CAMERA**: Found **{selected_participant_from_scan['Full_Name']}** (`{selected_participant_from_scan['Accreditation_ID']}`)!")
        
        log_mode1, log_mode2, log_mode3 = st.tabs([
            "📱 Mobile Phone Camera QR Scanner", 
            "📟 USB / Bluetooth Scanner Gun", 
            "📝 Manual Dropdown Input"
        ])
        
        with log_mode1:
            st.markdown("#### 📱 Mobile Phone & Tablet Camera QR Scanner")
            st.info("📸 **Camera Setup**: When your camera activates, tap the **Switch Camera icon (🔄)** on your screen to switch to your phone's **Rear / Back Camera** for quick scanning!")
            st.caption("Point your smartphone's back camera at the player, coach, or TWG member's QR Code pass:")
            
            camera_photo = st.camera_input("📷 Snap / Scan QR Code on Accreditation Pass (Use Back Camera 🔄)", key="mobile_camera_input")
            
            if camera_photo is not None:
                try:
                    file_bytes = np.asarray(bytearray(camera_photo.getvalue()), dtype=np.uint8)
                    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                    
                    detector = cv2.QRCodeDetector()
                    decoded_id, pts, _ = detector.detectAndDecode(img)
                    
                    if decoded_id and decoded_id.strip():
                        scanned_code = extract_accreditation_id(decoded_id)
                        st.success(f"🎉 **QR CODE SCANNED SUCCESSFULLY**: `{scanned_code}`")
                        matched_cam_p = p_df[p_df["Accreditation_ID"].str.upper() == scanned_code]
                        if not matched_cam_p.empty:
                            selected_participant_from_scan = matched_cam_p.iloc[0]
                        else:
                            st.error(f"❌ ID `{scanned_code}` scanned, but not found in registered participant database.")
                    else:
                        st.warning("⚠️ No QR code recognized in photo. Please center the QR pass, ensure good lighting, and hold steady.")
                except Exception as e:
                    st.error(f"Error reading camera frame: {e}")

        with log_mode2:
            st.markdown("#### 📟 Hardware Barcode / QR Scanner Gun")
            st.caption("Click in the box below and scan with a USB or Bluetooth scanner gun:")
            
            scanned_gun_id = st.text_input("📷 Scan Barcode / QR Code", placeholder="e.g. CV26-ATH-1001", key="gun_scanner_field").strip()
            if scanned_gun_id:
                clean_gun_id = extract_accreditation_id(scanned_gun_id)
                matched_gun_p = p_df[p_df["Accreditation_ID"].str.upper() == clean_gun_id.upper()]
                if not matched_gun_p.empty:
                    selected_participant_from_scan = matched_gun_p.iloc[0]
                else:
                    st.error(f"❌ ID `{scanned_gun_id}` not found in database.")

        with log_mode3:
            st.markdown("#### 📝 Manual Participant Lookup")
            p_options = p_df["Full_Name"] + " (" + p_df["Accreditation_ID"] + " - " + p_df["Division"] + ")"
            sel_manual_str = st.selectbox("Select Participant", options=p_options, key="manual_p_select")
            if sel_manual_str:
                p_m_idx = p_options.tolist().index(sel_manual_str)
                selected_participant_from_scan = p_df.iloc[p_m_idx]

        st.markdown("<hr/>", unsafe_allow_html=True)
        
        # Display selected participant details and movement log action buttons
        if selected_participant_from_scan is not None:
            p_rec = selected_participant_from_scan
            
            # Determine current status based on last log
            p_history = b_df[b_df["Accreditation_ID"] == p_rec["Accreditation_ID"]]
            last_action_str = "No Movement History (In Quarters)"
            default_action_idx = 0 # Default to Log OUT if no history or in quarters
            if not p_history.empty:
                last_log_entry = p_history.iloc[-1]
                last_action_str = f"{last_log_entry['Action']} at {last_log_entry['Timestamp']}"
                if "Log OUT" in last_log_entry["Action"]:
                    default_action_idx = 0 # Next expected action is Log IN
                else:
                    default_action_idx = 1 # Next expected action is Log OUT

            st.markdown("### 👤 Participant Scan Profile & Current Status")
            col_p1, col_p2 = st.columns([7, 3])
            
            with col_p1:
                st.info(f"""
                    **Full Name**: {p_rec['Full_Name']}<br/>
                    **Accreditation ID**: `{p_rec['Accreditation_ID']}`<br/>
                    **Role**: **{p_rec['Role']}** | **Division**: {p_rec['Division']}<br/>
                    **Sport / Committee**: {p_rec['Sport_or_Committee']}<br/>
                    **Last Recorded Status**: `{last_action_str}`
                """, icon="📇")
            
            with col_p2:
                svg_qr = get_qr_svg_string(p_rec['Accreditation_ID'], size=130)
                st.markdown(f'<div style="text-align:center;background:white;padding:10px;border-radius:10px;border:1px solid #E5E7EB">{svg_qr}</div>', unsafe_allow_html=True)
            
            st.markdown("#### ⚡ 1-Tap Quick Log Actions")
            col_q1, col_q2 = st.columns(2)
            
            with col_q1:
                if st.button("🟢 QUICK LOG IN (Returned to Quarters)", use_container_width=True, type="primary" if default_action_idx==0 else "secondary"):
                    q_log = {
                        "Log_ID": f"LOG-{1000 + len(b_df) + 1}",
                        "Timestamp": get_manila_now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Accreditation_ID": p_rec["Accreditation_ID"],
                        "Full_Name": p_rec["Full_Name"],
                        "Division": p_rec["Division"],
                        "Quarter": BILLETING_QUARTERS[0],
                        "Action": "Log IN (Returned to Quarters)",
                        "Destination_Reason": "Returned to Billeting School",
                        "Officer_In_Charge": "Duty Gate Guard"
                    }
                    b_updated = pd.concat([b_df, pd.DataFrame([q_log])], ignore_index=True)
                    st.session_state.billeting_df = b_updated
                    save_billeting_data(b_updated)
                    st.success(f"✅ INSTANT LOGGED **{p_rec['Full_Name']}**: Log IN at {q_log['Timestamp']}!")
                    st.rerun()
                    
            with col_q2:
                if st.button("🔴 QUICK LOG OUT (Left for Venue)", use_container_width=True, type="primary" if default_action_idx==1 else "secondary"):
                    q_log = {
                        "Log_ID": f"LOG-{1000 + len(b_df) + 1}",
                        "Timestamp": get_manila_now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Accreditation_ID": p_rec["Accreditation_ID"],
                        "Full_Name": p_rec["Full_Name"],
                        "Division": p_rec["Division"],
                        "Quarter": BILLETING_QUARTERS[0],
                        "Action": "Log OUT (Left for Venue)",
                        "Destination_Reason": "Playing Venue Match / Official Task",
                        "Officer_In_Charge": "Duty Gate Guard"
                    }
                    b_updated = pd.concat([b_df, pd.DataFrame([q_log])], ignore_index=True)
                    st.session_state.billeting_df = b_updated
                    save_billeting_data(b_updated)
                    send_telegram_message(f"🚨 <b>BILLETING LOG-OUT ALERT</b>\nParticipant <b>{p_rec['Full_Name']}</b> ({p_rec['Division']}) departed for Playing Venue at {q_log['Timestamp']}.")
                    st.success(f"✅ INSTANT LOGGED **{p_rec['Full_Name']}**: Log OUT at {q_log['Timestamp']}!")
                    st.rerun()

            st.markdown("<hr/>", unsafe_allow_html=True)
            st.markdown("#### 📝 Custom Movement Details Record")
            col_act1, col_act2 = st.columns(2)
            
            with col_act1:
                sel_action = st.radio("Select Movement Direction", ["Log IN (Returned to Quarters)", "Log OUT (Left for Venue)"], index=default_action_idx, horizontal=True, key="log_action_choice")
                sel_quarter = st.selectbox("Assigned Billeting School", BILLETING_QUARTERS, key="log_quarter_choice")
            
            with col_act2:
                dest_reason = st.text_input("Destination / Sport Venue / Reason", value="Playing Venue Match / Official Task", key="log_dest_field")
                officer_ic = st.text_input("Gate Security Officer / Chaperone Duty", value="Security Officer", key="log_officer_field")
            
            if st.button("💾 Submit Detailed Movement Log Entry", use_container_width=True, key="save_log_btn"):
                new_log = {
                    "Log_ID": f"LOG-{1000 + len(b_df) + 1}",
                    "Timestamp": get_manila_now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Accreditation_ID": p_rec["Accreditation_ID"],
                    "Full_Name": p_rec["Full_Name"],
                    "Division": p_rec["Division"],
                    "Quarter": sel_quarter,
                    "Action": sel_action,
                    "Destination_Reason": dest_reason,
                    "Officer_In_Charge": officer_ic
                }
                b_updated = pd.concat([b_df, pd.DataFrame([new_log])], ignore_index=True)
                st.session_state.billeting_df = b_updated
                save_billeting_data(b_updated)
                
                if "Log OUT" in sel_action:
                    send_telegram_message(f"🚨 <b>BILLETING LOG-OUT ALERT</b>\nParticipant <b>{p_rec['Full_Name']}</b> ({p_rec['Division']}) departed from {sel_quarter} for {dest_reason} at {new_log['Timestamp']}.")
                
                st.success(f"✅ Logged **{p_rec['Full_Name']}**: {sel_action} at {new_log['Timestamp']}!")
                st.rerun()

        st.markdown("<hr/>", unsafe_allow_html=True)
        st.markdown("#### 📊 Billeting Attendance Log History")
        st.dataframe(b_df, use_container_width=True, hide_index=True)

    with tab_bot:
        st.subheader("📲 Telegram & Viber Emergency Bot Alert Center")
        st.markdown("Send instant curfew alerts and emergency broadcast notices to delegation coaches and TWG group chats.")
        
        st.markdown("#### ⚙️ Bot API Configuration")
        col_tg1, col_tg2 = st.columns(2)
        with col_tg1:
            tg_token = st.text_input("Telegram Bot Token", type="password", placeholder="123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ")
            tg_chat_id = st.text_input("Telegram Chat ID / Group ID", placeholder="-100123456789")
        with col_tg2:
            vb_token = st.text_input("Viber Auth Token", type="password", placeholder="44526-xxx-xxx")
            vb_rec_id = st.text_input("Viber Receiver / Group ID", placeholder="viber_user_id_here")
            
        st.markdown("---")
        st.markdown("#### 🚨 Send Automated Curfew Violation Warning")
        curfew_hour = st.time_input("Curfew Deadline", value=datetime.strptime("21:00", "%H:%M").time())
        
        curfew_msg = f"""🚨 *CVIRAA CURFEW ALERT ({curfew_hour.strftime('%I:%M %p')})*

Attention Coaches: Please ensure all athletes are logged IN to their billeting quarters. Officers are conducting headcount inspection."""
        st.text_area("Alert Message Preview", value=curfew_msg, height=100)
        
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            if st.button("📲 Send Telegram Curfew Alert", use_container_width=True):
                res, msg = send_telegram_message(tg_token, tg_chat_id, curfew_msg)
                if res: st.success(msg)
                else: st.info(f"Simulation Mode Active: {msg}")
        with col_s2:
            if st.button("🟣 Send Viber Curfew Alert", use_container_width=True):
                res, msg = send_viber_message(vb_token, vb_rec_id, curfew_msg)
                if res: st.success(msg)
                else: st.info(f"Simulation Mode Active: {msg}")
        with col_s3:
            if st.button("📢 Broadcast to Both Platforms", use_container_width=True):
                st.success("Broadcast dispatched to Telegram & Viber groups!")

    # TAB 10: 📇 Accreditation Pass Generator
    with tab_pass:
        st.subheader("📇 Scannable QR Code Accreditation Pass Generator")
        st.markdown("Generate and print official CVIRAA Accreditation Badges with **Scannable Vector QR Codes** for Athletes, Coaches, Chaperones, and TWG Officers.")
        
        pdf = st.session_state.participants_df
        if pdf.empty:
            st.warning("No participants registered yet. Go to 'Players, Coaches & TWG' to register participants.")
        else:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                role_filter = st.selectbox("Filter by Role", ["All Roles", "Athlete / Player", "Coach", "Chaperone", "TWG Member"], key="pass_role_filter")
            with col_f2:
                div_filter = st.selectbox("Filter by Division", ["All Divisions"] + DIVISIONS, key="pass_div_filter")
            
            filtered_pdf = pdf.copy()
            if role_filter != "All Roles":
                filtered_pdf = filtered_pdf[filtered_pdf["Role"] == role_filter]
            if div_filter != "All Divisions":
                filtered_pdf = filtered_pdf[filtered_pdf["Division"] == div_filter]
            
            if filtered_pdf.empty:
                st.warning("No participants match the selected filters.")
            else:
                p_list = filtered_pdf["Full_Name"] + " (" + filtered_pdf["Accreditation_ID"] + " - " + filtered_pdf["Role"] + ")"
                p_select = st.selectbox("Select Participant to Display Pass", options=p_list, key="pass_p_select")
                p_idx = p_list.tolist().index(p_select)
                p_row = filtered_pdf.iloc[p_idx]
                
                st.markdown("<hr/>", unsafe_allow_html=True)
                
                col_c1, col_c2 = st.columns([6, 4])
                
                with col_c1:
                    role_str = str(p_row['Role']).upper()
                    badge_bg = "#1E3A8A" # Navy
                    if "COACH" in role_str: badge_bg = "#059669" # Emerald Green
                    elif "CHAPERONE" in role_str: badge_bg = "#7C3AED" # Purple
                    elif "TWG" in role_str: badge_bg = "#D97706" # Amber Gold
                    
                    st.markdown(f"""
                        <div style="border:3px solid {badge_bg};border-radius:15px;background-color:#FFFFFF;padding:20px;text-align:center;box-shadow:0 10px 15px -3px rgba(0,0,0,0.1);max-width:400px;margin:auto;">
                            <div style="background-color:{badge_bg};color:white;padding:10px;border-radius:10px 10px 0 0;margin:-20px -20px 15px -20px;">
                                <h3 style="margin:0;color:#F59E0B;font-size:1.1rem;">🏅 DEPED VII • CVIRAA 2026</h3>
                                <p style="margin:2px 0 0 0;font-size:0.8rem;letter-spacing:1px;font-weight:bold;">OFFICIAL {role_str} PASS</p>
                            </div>
                            <h2 style="color:#1E3A8A;margin:10px 0 5px 0;font-size:1.5rem;font-weight:900;">{p_row['Full_Name']}</h2>
                            <p style="color:#4B5563;margin:0 0 10px 0;font-size:1rem;font-weight:600;"><b>Division:</b> {p_row['Division']}</p>
                            <p style="color:#6B7280;margin:0 0 15px 0;font-size:0.9rem;"><b>Sport / Committee:</b> {p_row['Sport_or_Committee']}</p>
                            <div style="background-color:#F3F4F6;padding:10px;border-radius:10px;margin-bottom:15px;display:inline-block;">
                                {get_qr_svg_string(p_row['Accreditation_ID'], size=160)}
                            </div>
                            <div style="background-color:#1E3A8A;color:white;padding:6px 12px;border-radius:20px;font-weight:bold;font-size:0.9rem;display:inline-block;">
                                ID: {p_row['Accreditation_ID']}
                            </div>
                            <p style="color:#9CA3AF;margin:12px 0 0 0;font-size:0.75rem;"><i>Scannable with Smartphone Camera or Gate Scanner</i></p>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col_c2:
                    st.markdown("#### 📄 Printable PDF Downloads")
                    st.caption("Download official print-ready PDF accreditation badges complete with scannable vector QR codes:")
                    
                    ind_pass_pdf = make_single_accreditation_pass_pdf(p_row)
                    st.download_button(
                        label=f"📄 Download Pass PDF for {p_row['Full_Name']}",
                        data=ind_pass_pdf,
                        file_name=f"Pass_{p_row['Accreditation_ID']}_{p_row['Full_Name'].replace(' ','_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                    st.markdown("---")
                    
                    all_pass_pdf = make_all_accreditation_passes_pdf(filtered_pdf)
                    st.download_button(
                        label=f"📄 Download All {len(filtered_pdf)} Passes with QR Codes (Batch PDF)",
                        data=all_pass_pdf,
                        file_name="CVIRAA_All_Accreditation_Passes_QR.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )

    with tab_cert:
        st.subheader("📜 Dynamic PDF Certificate Generator")
        cert_div = st.selectbox("Select Winning Schools Division", DIVISIONS, key="cert_div")
        cert_sport = st.selectbox("Select Sport / Discipline", ["Overall Standings"] + SPORTS, key="cert_sport")
        cert_rank = st.selectbox("Select Award / Placement", ["Champion", "1st Runner-Up", "2nd Runner-Up", "3rd Runner-Up"], key="cert_rank")
        cert_cat = st.selectbox("Select Category", ["Elementary", "Secondary", "Combined Division"], key="cert_cat")

    # TAB 12: ✏️ Spreadsheet Editor
    with tab_editor:
        st.subheader("✏️ Live Spreadsheet Editor")
        if not st.session_state.authenticated:
            st.warning("🔒 This editor is locked! Enter password in the sidebar.")
        else:
            st.dataframe(st.session_state.medal_df, use_container_width=True)

    st.markdown("---")
    st.markdown("<div style='text-align:center;color:#6B7280;font-size:0.8em;'>CVIRAA Olympic Medal Tally & Management System &bull; DepEd Region VII</div>", unsafe_allow_html=True)
