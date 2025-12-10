import streamlit as st
import google.generativeai as genai
import streamlit.components.v1 as components
import time
import os
import tempfile
import gc
import io
from PIL import Image
import requests
import subprocess
import sys

# --- LIBRARY IMPORTS WITH GRACEFUL FALLBACK ---
PDF_AVAILABLE = True
DOCX_AVAILABLE = True
GDOWN_AVAILABLE = True

try:
    import PyPDF2
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document
except ImportError:
    DOCX_AVAILABLE = False

try:
    import gdown
except ImportError:
    GDOWN_AVAILABLE = False

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Ultimate AI Studio",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- SESSION STATE INITIALIZATION ---
def init_session_state():
    """Initialize all session state variables at app start"""
    defaults = {
        'video_queue': [],
        'processing_active': False,
        'current_index': 0,
        'run_translate': False,
        'run_rewrite': False,
        'style_text': "",
        'api_configured': False,
        'custom_prompt': "",
        'generated_images': [],
        'ai_news_cache': None,
        'ai_news_timestamp': None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- MATRIX RAIN BACKGROUND CSS ---
st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');
    
    /* Matrix Rain Container */
    .matrix-bg {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: -1;
        overflow: hidden;
        background: linear-gradient(180deg, #0a0a0f 0%, #0d1117 50%, #0a0f0a 100%);
    }
    
    /* Matrix Rain Columns - CSS Only Animation */
    .matrix-column {
        position: absolute;
        top: -100%;
        font-family: 'Share Tech Mono', monospace;
        font-size: 14px;
        line-height: 1.2;
        color: #0f0;
        text-shadow: 0 0 8px #0f0, 0 0 20px #0f0;
        animation: matrix-fall linear infinite;
        opacity: 0.7;
        white-space: nowrap;
        writing-mode: vertical-rl;
        text-orientation: upright;
    }
    
    @keyframes matrix-fall {
        0% { transform: translateY(-100%); opacity: 1; }
        75% { opacity: 0.7; }
        100% { transform: translateY(200vh); opacity: 0; }
    }
    
    .matrix-column:nth-child(1) { left: 2%; animation-duration: 8s; animation-delay: 0s; font-size: 12px; }
    .matrix-column:nth-child(2) { left: 6%; animation-duration: 12s; animation-delay: 1s; font-size: 10px; opacity: 0.5; }
    .matrix-column:nth-child(3) { left: 10%; animation-duration: 9s; animation-delay: 2s; font-size: 14px; }
    .matrix-column:nth-child(4) { left: 14%; animation-duration: 15s; animation-delay: 0.5s; font-size: 11px; opacity: 0.4; }
    .matrix-column:nth-child(5) { left: 18%; animation-duration: 10s; animation-delay: 3s; font-size: 13px; }
    .matrix-column:nth-child(6) { left: 22%; animation-duration: 11s; animation-delay: 1.5s; font-size: 10px; opacity: 0.6; }
    .matrix-column:nth-child(7) { left: 26%; animation-duration: 14s; animation-delay: 2.5s; font-size: 12px; }
    .matrix-column:nth-child(8) { left: 30%; animation-duration: 8s; animation-delay: 0.8s; font-size: 15px; opacity: 0.5; }
    .matrix-column:nth-child(9) { left: 34%; animation-duration: 13s; animation-delay: 4s; font-size: 11px; }
    .matrix-column:nth-child(10) { left: 38%; animation-duration: 9s; animation-delay: 1.2s; font-size: 13px; opacity: 0.4; }
    .matrix-column:nth-child(11) { left: 42%; animation-duration: 16s; animation-delay: 3.5s; font-size: 10px; }
    .matrix-column:nth-child(12) { left: 46%; animation-duration: 10s; animation-delay: 0.3s; font-size: 14px; opacity: 0.6; }
    .matrix-column:nth-child(13) { left: 50%; animation-duration: 12s; animation-delay: 2.8s; font-size: 12px; }
    .matrix-column:nth-child(14) { left: 54%; animation-duration: 8s; animation-delay: 1.8s; font-size: 11px; opacity: 0.5; }
    .matrix-column:nth-child(15) { left: 58%; animation-duration: 14s; animation-delay: 4.5s; font-size: 13px; }
    .matrix-column:nth-child(16) { left: 62%; animation-duration: 11s; animation-delay: 0.6s; font-size: 10px; opacity: 0.4; }
    .matrix-column:nth-child(17) { left: 66%; animation-duration: 9s; animation-delay: 3.2s; font-size: 15px; }
    .matrix-column:nth-child(18) { left: 70%; animation-duration: 15s; animation-delay: 2.2s; font-size: 12px; opacity: 0.6; }
    .matrix-column:nth-child(19) { left: 74%; animation-duration: 10s; animation-delay: 1.4s; font-size: 11px; }
    .matrix-column:nth-child(20) { left: 78%; animation-duration: 13s; animation-delay: 5s; font-size: 14px; opacity: 0.5; }
    .matrix-column:nth-child(21) { left: 82%; animation-duration: 8s; animation-delay: 0.9s; font-size: 10px; }
    .matrix-column:nth-child(22) { left: 86%; animation-duration: 12s; animation-delay: 3.8s; font-size: 13px; opacity: 0.4; }
    .matrix-column:nth-child(23) { left: 90%; animation-duration: 11s; animation-delay: 2.6s; font-size: 12px; }
    .matrix-column:nth-child(24) { left: 94%; animation-duration: 9s; animation-delay: 1.1s; font-size: 11px; opacity: 0.6; }
    .matrix-column:nth-child(25) { left: 98%; animation-duration: 14s; animation-delay: 4.2s; font-size: 10px; }
    
    .stApp {
        background: transparent !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(10, 15, 20, 0.85);
        z-index: -1;
        pointer-events: none;
    }
    
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Main Container - Max Width 1800px */
    .main .block-container {
        max-width: 1800px !important;
        padding: 2rem 2rem !important;
    }
    
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        background: linear-gradient(145deg, rgba(0, 40, 20, 0.85), rgba(10, 30, 15, 0.9)) !important;
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 2px solid rgba(0, 255, 100, 0.25) !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 24px rgba(0, 255, 100, 0.15), 0 0 0 1px rgba(0, 255, 100, 0.1), inset 0 1px 0 rgba(0, 255, 100, 0.1);
        padding: 1.5rem;
    }
    
    .stTextInput input, .stTextArea textarea {
        background: rgba(0, 20, 10, 0.7) !important;
        color: #00ff66 !important;
        border: 2px solid rgba(0, 255, 100, 0.3) !important;
        border-radius: 10px !important;
        padding: 12px 16px !important;
        font-size: 14px !important;
        font-family: 'Share Tech Mono', monospace !important;
        transition: all 0.3s ease;
    }
    
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: rgba(0, 255, 100, 0.7) !important;
        box-shadow: 0 0 0 3px rgba(0, 255, 100, 0.15), 0 0 20px rgba(0, 255, 100, 0.2) !important;
    }
    
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {
        color: rgba(0, 255, 100, 0.4) !important;
    }
    
    .stSelectbox div[data-baseweb="select"] > div {
        background: rgba(0, 20, 10, 0.7) !important;
        border: 2px solid rgba(0, 255, 100, 0.3) !important;
        border-radius: 10px !important;
        color: #00ff66 !important;
    }
    
    .stSelectbox div[data-baseweb="select"] > div:hover {
        border-color: rgba(0, 255, 100, 0.5) !important;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, rgba(0, 200, 80, 0.9) 0%, rgba(0, 150, 60, 0.9) 100%);
        color: #000 !important;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 1.5rem;
        font-weight: 700;
        font-size: 14px;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 255, 100, 0.3), 0 0 30px rgba(0, 255, 100, 0.1);
        text-transform: uppercase;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 25px rgba(0, 255, 100, 0.5), 0 0 40px rgba(0, 255, 100, 0.2);
        background: linear-gradient(135deg, rgba(0, 255, 100, 1) 0%, rgba(0, 200, 80, 1) 100%);
    }
    
    .stDownloadButton > button {
        background: linear-gradient(135deg, rgba(0, 180, 255, 0.9) 0%, rgba(0, 120, 200, 0.9) 100%) !important;
        box-shadow: 0 4px 15px rgba(0, 180, 255, 0.3);
        color: #000 !important;
    }
    
    .stDownloadButton > button:hover {
        box-shadow: 0 6px 25px rgba(0, 180, 255, 0.5);
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(0, 40, 20, 0.6);
        padding: 8px;
        border-radius: 12px;
        border: 1px solid rgba(0, 255, 100, 0.2);
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        color: rgba(0, 255, 100, 0.7);
        border: 1px solid transparent;
        padding: 10px 20px;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        color: rgba(0, 255, 100, 0.95);
        background: rgba(0, 255, 100, 0.1);
        border: 1px solid rgba(0, 255, 100, 0.3);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(0, 200, 80, 0.9) 0%, rgba(0, 150, 60, 0.9) 100%) !important;
        color: #000 !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(0, 255, 100, 0.4), 0 0 20px rgba(0, 255, 100, 0.2);
        font-weight: 700;
    }
    
    [data-testid="stFileUploader"] {
        background: rgba(0, 40, 20, 0.4);
        border-radius: 12px;
        padding: 16px;
        border: 2px dashed rgba(0, 255, 100, 0.4) !important;
        transition: all 0.3s ease;
    }
    
    [data-testid="stFileUploader"]:hover {
        border-color: rgba(0, 255, 100, 0.7) !important;
        background: rgba(0, 255, 100, 0.05);
        box-shadow: 0 0 30px rgba(0, 255, 100, 0.1);
    }
    
    h1 {
        color: #00ff66 !important;
        font-weight: 700 !important;
        font-size: 2rem !important;
        letter-spacing: -0.5px;
        text-shadow: 0 0 10px rgba(0, 255, 100, 0.5), 0 0 30px rgba(0, 255, 100, 0.3);
    }
    
    h2, h3 {
        color: #00ff66 !important;
        font-weight: 600 !important;
        text-shadow: 0 0 8px rgba(0, 255, 100, 0.3);
    }
    
    p, label, .stMarkdown {
        color: rgba(0, 255, 100, 0.85) !important;
    }
    
    .queue-item {
        background: rgba(0, 40, 20, 0.5);
        border: 2px solid rgba(0, 255, 100, 0.2);
        border-radius: 10px;
        padding: 12px 16px;
        margin: 8px 0;
        transition: all 0.3s ease;
        font-family: 'Share Tech Mono', monospace;
    }
    
    .queue-item:hover {
        background: rgba(0, 255, 100, 0.05);
        border-color: rgba(0, 255, 100, 0.4);
        box-shadow: 0 0 20px rgba(0, 255, 100, 0.1);
    }
    
    .queue-item.processing {
        background: rgba(0, 255, 100, 0.1);
        border: 2px solid rgba(0, 255, 100, 0.5);
        animation: pulse-glow 2s infinite;
    }
    
    @keyframes pulse-glow {
        0%, 100% { box-shadow: 0 0 5px rgba(0, 255, 100, 0.3); }
        50% { box-shadow: 0 0 20px rgba(0, 255, 100, 0.6); }
    }
    
    .queue-item.completed {
        background: rgba(0, 180, 255, 0.1);
        border: 2px solid rgba(0, 180, 255, 0.5);
    }
    
    .queue-item.failed {
        background: rgba(255, 50, 50, 0.1);
        border: 2px solid rgba(255, 50, 50, 0.5);
    }
    
    .stAlert { border-radius: 10px !important; }
    
    .stProgress > div > div {
        background: linear-gradient(90deg, #00ff66, #00cc55, #00ff66) !important;
        background-size: 200% 100%;
        animation: progress-glow 2s linear infinite;
        border-radius: 10px;
        box-shadow: 0 0 10px rgba(0, 255, 100, 0.5);
    }
    
    @keyframes progress-glow {
        0% { background-position: 0% 50%; }
        100% { background-position: 200% 50%; }
    }
    
    .stRadio > div { gap: 12px; }
    .stRadio label { color: rgba(0, 255, 100, 0.85) !important; }
    
    [data-testid="stMetricValue"] {
        color: #00ff66 !important;
        font-weight: 700 !important;
        font-family: 'Share Tech Mono', monospace !important;
        text-shadow: 0 0 10px rgba(0, 255, 100, 0.5);
    }
    
    [data-testid="stMetricLabel"] { color: rgba(0, 255, 100, 0.6) !important; }
    
    .streamlit-expanderHeader {
        background: rgba(0, 40, 20, 0.5) !important;
        border-radius: 10px !important;
        color: #00ff66 !important;
    }
    
    .main-title { text-align: center; padding: 1rem 0 0.5rem 0; }
    
    .main-title h1 {
        background: linear-gradient(135deg, #00ff66, #00ffaa, #00ff66);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.8rem !important;
        margin-bottom: 0.25rem;
        animation: title-glow 3s ease-in-out infinite;
        text-shadow: none;
    }
    
    @keyframes title-glow {
        0%, 100% { filter: drop-shadow(0 0 10px rgba(0, 255, 100, 0.5)); }
        50% { filter: drop-shadow(0 0 20px rgba(0, 255, 100, 0.8)); }
    }
    
    .main-title p {
        color: rgba(0, 255, 100, 0.5) !important;
        font-size: 1rem;
        font-family: 'Share Tech Mono', monospace;
        letter-spacing: 2px;
    }
    
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(0, 255, 100, 0.3), transparent);
        margin: 1.5rem 0;
    }
    
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: rgba(0, 20, 10, 0.5); border-radius: 10px; }
    ::-webkit-scrollbar-thumb { background: rgba(0, 255, 100, 0.4); border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(0, 255, 100, 0.6); }
    
    ::selection { background: rgba(0, 255, 100, 0.3); color: #00ff66; }
    
    /* News Card Styling */
    .news-card {
        background: rgba(0, 40, 20, 0.6);
        border: 1px solid rgba(0, 255, 100, 0.2);
        border-radius: 12px;
        padding: 16px;
        margin: 10px 0;
        transition: all 0.3s ease;
    }
    
    .news-card:hover {
        border-color: rgba(0, 255, 100, 0.5);
        box-shadow: 0 0 20px rgba(0, 255, 100, 0.1);
    }
    
    .news-card h4 {
        color: #00ff66 !important;
        margin-bottom: 8px;
    }
    
    .news-card p {
        color: rgba(0, 255, 100, 0.7) !important;
        font-size: 0.9rem;
    }
    
    .news-card .source {
        color: rgba(0, 180, 255, 0.8) !important;
        font-size: 0.8rem;
    }
</style>

<!-- Matrix Rain Background HTML -->
<div class="matrix-bg">
    <div class="matrix-column">ア イ ウ エ オ カ キ ク ケ コ 0 1 0 1 サ シ ス セ ソ</div>
    <div class="matrix-column">1 0 1 タ チ ツ テ ト ナ ニ ヌ ネ ノ 0 1 0 ハ ヒ フ</div>
    <div class="matrix-column">マ ミ ム メ モ 0 1 1 0 ヤ ユ ヨ ラ リ ル レ ロ ワ</div>
    <div class="matrix-column">0 1 0 1 0 ア カ サ タ ナ ハ マ ヤ ラ ワ 1 0 1 0 1</div>
    <div class="matrix-column">キ シ チ ニ ヒ ミ リ 0 1 0 ク ス ツ ヌ フ ム ル</div>
    <div class="matrix-column">1 1 0 0 1 ケ セ テ ネ ヘ メ レ 0 0 1 1 0 コ ソ ト</div>
    <div class="matrix-column">ノ ホ モ ヨ ロ 1 0 1 ア イ ウ エ オ 0 1 0 1 0 1</div>
    <div class="matrix-column">0 カ キ ク 1 ケ コ 0 サ シ 1 ス セ 0 ソ タ 1 チ ツ</div>
    <div class="matrix-column">テ ト 0 1 ナ ニ ヌ ネ ノ 1 0 ハ ヒ フ ヘ ホ 0 1 0</div>
    <div class="matrix-column">1 マ ミ ム メ モ 0 ヤ ユ ヨ 1 ラ リ ル レ ロ 0 1 ワ</div>
    <div class="matrix-column">ア 0 イ 1 ウ 0 エ 1 オ 0 カ 1 キ 0 ク 1 ケ 0 コ 1</div>
    <div class="matrix-column">サ シ ス 0 1 0 セ ソ タ 1 0 1 チ ツ テ 0 1 0 ト ナ</div>
    <div class="matrix-column">1 0 ニ ヌ ネ 1 0 ノ ハ ヒ 1 0 フ ヘ ホ 1 0 マ ミ ム</div>
    <div class="matrix-column">メ モ 1 0 1 ヤ ユ ヨ 0 1 0 ラ リ ル 1 0 1 レ ロ ワ</div>
    <div class="matrix-column">0 1 ア イ 0 1 ウ エ 0 1 オ カ 0 1 キ ク 0 1 ケ コ</div>
    <div class="matrix-column">サ 0 シ 1 ス 0 セ 1 ソ 0 タ 1 チ 0 ツ 1 テ 0 ト 1</div>
    <div class="matrix-column">1 1 0 0 1 1 0 0 ナ ニ ヌ ネ ノ ハ ヒ フ ヘ ホ 0 0</div>
    <div class="matrix-column">マ ミ ム メ 0 1 モ ヤ ユ 1 0 ヨ ラ リ 0 1 ル レ ロ</div>
    <div class="matrix-column">0 ワ 1 ア 0 イ 1 ウ 0 エ 1 オ 0 カ 1 キ 0 ク 1 ケ</div>
    <div class="matrix-column">コ サ 0 1 0 シ ス セ 1 0 1 ソ タ チ 0 1 0 ツ テ ト</div>
    <div class="matrix-column">1 0 1 0 1 ナ ニ ヌ ネ ノ 0 1 0 1 0 ハ ヒ フ ヘ ホ</div>
    <div class="matrix-column">マ 1 ミ 0 ム 1 メ 0 モ 1 ヤ 0 ユ 1 ヨ 0 ラ 1 リ 0</div>
    <div class="matrix-column">ル レ ロ 0 0 1 1 ワ ア イ 1 1 0 0 ウ エ オ カ キ ク</div>
    <div class="matrix-column">0 1 1 0 ケ コ サ シ 1 0 0 1 ス セ ソ タ 0 1 1 0</div>
    <div class="matrix-column">チ ツ 0 テ ト 1 ナ ニ 0 ヌ ネ 1 ノ ハ 0 ヒ フ 1 ヘ ホ</div>
</div>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---

def force_memory_cleanup():
    """Force garbage collection and memory cleanup"""
    gc.collect()
    # Clear any large objects from session state that are no longer needed
    if 'temp_data' in st.session_state:
        del st.session_state['temp_data']

def extract_file_id_from_url(url):
    """Extract Google Drive file ID from various URL formats"""
    try:
        if 'drive.google.com' in url:
            if '/file/d/' in url:
                file_id = url.split('/file/d/')[1].split('/')[0].split('?')[0]
                return file_id
            elif 'id=' in url:
                file_id = url.split('id=')[1].split('&')[0]
                return file_id
        return None
    except Exception:
        return None

def download_video_from_url_gdown(url, progress_placeholder=None):
    """Download video from Google Drive URL using gdown library"""
    try:
        file_id = extract_file_id_from_url(url)
        if not file_id:
            return None, "Invalid Google Drive URL format"
        
        if progress_placeholder:
            progress_placeholder.info("📥 Downloading from Google Drive...")
        
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        tmp_path = tmp_file.name
        tmp_file.close()
        
        gdrive_url = f"https://drive.google.com/uc?id={file_id}"
        
        if GDOWN_AVAILABLE:
            output = gdown.download(gdrive_url, tmp_path, quiet=False, fuzzy=True)
            if output is None:
                return None, "gdown download failed. Check if file is shared publicly."
        else:
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "gdown", gdrive_url, "-O", tmp_path, "--fuzzy"],
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                if result.returncode != 0:
                    return None, f"Download failed: {result.stderr}"
            except subprocess.TimeoutExpired:
                return None, "Download timed out (10 minutes)"
            except FileNotFoundError:
                return None, "gdown not installed. Add 'gdown' to requirements.txt"
        
        if not os.path.exists(tmp_path):
            return None, "Download failed - file not created"
        
        file_size = os.path.getsize(tmp_path)
        if file_size < 1000:
            with open(tmp_path, 'rb') as f:
                content = f.read(500)
                if b'<!DOCTYPE' in content or b'<html' in content:
                    os.remove(tmp_path)
                    return None, "Google Drive returned error page. Ensure file is shared as 'Anyone with the link'."
            os.remove(tmp_path)
            return None, "Downloaded file is too small - likely an error"
        
        if progress_placeholder:
            size_mb = file_size / (1024 * 1024)
            progress_placeholder.success(f"✅ Downloaded: {size_mb:.1f} MB")
        
        return tmp_path, None
        
    except Exception as e:
        return None, f"Download error: {str(e)}"

def download_video_from_url(url, progress_placeholder=None):
    """Smart download using gdown"""
    if GDOWN_AVAILABLE:
        return download_video_from_url_gdown(url, progress_placeholder)
    else:
        return None, "gdown library not available. Please add 'gdown' to requirements.txt"

def save_uploaded_file_chunked(uploaded_file, progress_placeholder=None):
    """Save uploaded file in chunks"""
    try:
        file_ext = uploaded_file.name.split('.')[-1] if '.' in uploaded_file.name else 'mp4'
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}")
        tmp_path = tmp_file.name
        
        uploaded_file.seek(0, 2)
        file_size = uploaded_file.tell()
        uploaded_file.seek(0)
        
        if progress_placeholder:
            progress_placeholder.info(f"💾 Saving file ({file_size / (1024*1024):.1f} MB)...")
        
        chunk_size = 10 * 1024 * 1024
        written = 0
        
        progress_bar = st.progress(0)
        
        while True:
            chunk = uploaded_file.read(chunk_size)
            if not chunk:
                break
            tmp_file.write(chunk)
            written += len(chunk)
            progress_bar.progress(min(written / file_size, 1.0))
        
        tmp_file.close()
        progress_bar.empty()
        
        if progress_placeholder:
            progress_placeholder.success(f"✅ File saved: {written / (1024*1024):.1f} MB")
        
        return tmp_path, None
        
    except Exception as e:
        return None, f"Error saving file: {str(e)}"

def upload_to_gemini(file_path, mime_type=None, progress_placeholder=None):
    """Upload file to Gemini with status updates"""
    try:
        if progress_placeholder:
            file_size = os.path.getsize(file_path)
            size_mb = file_size / (1024 * 1024)
            progress_placeholder.info(f"📤 Uploading to Gemini ({size_mb:.1f} MB)...")
        
        file = genai.upload_file(file_path, mime_type=mime_type)
        
        wait_count = 0
        while file.state.name == "PROCESSING":
            wait_count += 1
            if progress_placeholder:
                progress_placeholder.info(f"⏳ Gemini processing... ({wait_count * 2}s)")
            time.sleep(2)
            file = genai.get_file(file.name)
            
            if wait_count > 300:
                return None
        
        if file.state.name == "FAILED":
            return None
        
        if progress_placeholder:
            progress_placeholder.success("✅ Upload complete!")
        
        return file
    except Exception as e:
        if progress_placeholder:
            progress_placeholder.error(f"❌ Upload Error: {e}")
        return None

def read_file_content(uploaded_file):
    """Reads content from txt, pdf, or docx files"""
    try:
        file_type = uploaded_file.type
        
        if file_type == "text/plain":
            return uploaded_file.getvalue().decode("utf-8")
        
        elif file_type == "application/pdf":
            if not PDF_AVAILABLE:
                st.error("⚠️ PyPDF2 not installed.")
                return None
            reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.getvalue()))
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            return text
        
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            if not DOCX_AVAILABLE:
                st.error("⚠️ python-docx not installed.")
                return None
            doc = Document(io.BytesIO(uploaded_file.getvalue()))
            text = "\n".join([para.text for para in doc.paragraphs])
            return text
        else:
            st.warning(f"⚠️ Unsupported file type: {file_type}")
            return None
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return None

def cleanup_temp_file(file_path):
    """Safely remove temporary file"""
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

def get_response_text_safe(response):
    """Safely extract text from Gemini response with proper error handling"""
    try:
        # Check if response has candidates
        if not response:
            return None, "No response received from Gemini"
        
        if not response.candidates:
            # Check for prompt feedback (content blocked)
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                block_reason = getattr(response.prompt_feedback, 'block_reason', 'Unknown')
                return None, f"Content blocked by Gemini: {block_reason}"
            return None, "Empty response from Gemini (no candidates)"
        
        candidate = response.candidates[0]
        
        # Check finish reason
        if hasattr(candidate, 'finish_reason'):
            finish_reason = str(candidate.finish_reason)
            if 'SAFETY' in finish_reason:
                return None, "Content blocked due to safety filters"
            if 'RECITATION' in finish_reason:
                return None, "Content blocked due to recitation policy"
        
        # Check if content exists
        if not hasattr(candidate, 'content') or not candidate.content:
            return None, "Response has no content"
        
        # Check if parts exist
        if not hasattr(candidate.content, 'parts') or not candidate.content.parts:
            return None, "Response content has no parts"
        
        # Extract text from parts
        text_parts = []
        for part in candidate.content.parts:
            if hasattr(part, 'text') and part.text:
                text_parts.append(part.text)
        
        if not text_parts:
            return None, "No text found in response parts"
        
        return "\n".join(text_parts), None
        
    except Exception as e:
        return None, f"Error extracting response: {str(e)}"

def call_gemini_api(model, content, timeout=600):
    """Call Gemini API with retry logic and proper error handling"""
    max_retries = 3
    base_delay = 10  # Increased base delay for rate limiting
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(content, request_options={"timeout": timeout})
            
            # Use safe extraction
            text, error = get_response_text_safe(response)
            if error:
                if attempt < max_retries - 1:
                    st.warning(f"⚠️ {error}. Retrying...")
                    time.sleep(base_delay)
                    continue
                return None, error
            
            return response, None
            
        except Exception as e:
            error_str = str(e).lower()
            
            if 'rate' in error_str or 'quota' in error_str or '429' in error_str or 'resource' in error_str:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    st.warning(f"⏳ Rate limited. Waiting {delay}s... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    return None, f"Rate limit exceeded after {max_retries} retries. Please wait a few minutes."
            else:
                return None, str(e)
    
    return None, "Max retries exceeded"

def process_video_from_path(file_path, video_name, vision_model_name, writer_model_name, style_text="", custom_prompt="", status_placeholder=None):
    """Process video from local file path with proper error handling"""
    gemini_file = None
    try:
        if status_placeholder:
            status_placeholder.info("📤 Step 1/3: Uploading video to Gemini...")
        
        gemini_file = upload_to_gemini(file_path, progress_placeholder=status_placeholder)
        if not gemini_file:
            return None, "Failed to upload to Gemini"
        
        if status_placeholder:
            status_placeholder.info("👀 Step 2/3: AI analyzing video...")
        
        vision_model = genai.GenerativeModel(vision_model_name)
        vision_prompt = """
        Watch this video carefully. 
        Generate a highly detailed, chronological scene-by-scene description.
        Include All the dialogue in the movie, visual details, emotions, and actions.
        No creative writing yet, just facts.
        """
        
        vision_response, error = call_gemini_api(vision_model, [gemini_file, vision_prompt], timeout=600)
        if error:
            return None, f"Vision analysis failed: {error}"
        
        video_description, error = get_response_text_safe(vision_response)
        if error:
            return None, f"Failed to get vision response: {error}"
        
        # Add delay between API calls to avoid rate limiting
        time.sleep(5)
        
        if status_placeholder:
            status_placeholder.info("✍️ Step 3/3: Writing Burmese recap script...")
        
        custom_instructions = ""
        if custom_prompt:
            custom_instructions = f"\n\n**CUSTOM INSTRUCTIONS:**\n{custom_prompt}\n"
        
        writer_model = genai.GenerativeModel(writer_model_name)
        writer_prompt = f"""
        You are a professional Burmese Movie Recap Scriptwriter.
        Turn this description into an engaging **Burmese Movie Recap Script**.
        
        **INPUT DATA:**
        {video_description}
        
        {style_text}
        {custom_instructions}
        
        **INSTRUCTIONS:**
        1. Write in 100% Burmese.
        2. Use a storytelling tone.
        3. Cover the whole story.
        4. Do not summarize too much; keep details.
        5. Scene-by-scene. 
        6. Full narration.                         
        """
        
        final_response, error = call_gemini_api(writer_model, writer_prompt, timeout=600)
        if error:
            return None, f"Script writing failed: {error}"
        
        final_text, error = get_response_text_safe(final_response)
        if error:
            return None, f"Failed to get script: {error}"
        
        return final_text, None
        
    except Exception as e:
        return None, str(e)
    
    finally:
        if gemini_file:
            try: 
                genai.delete_file(gemini_file.name)
            except Exception: 
                pass
        force_memory_cleanup()

def process_video_from_url(url, video_name, vision_model_name, writer_model_name, style_text="", custom_prompt="", status_placeholder=None):
    """Process video from URL with memory cleanup"""
    tmp_path = None
    try:
        if status_placeholder:
            status_placeholder.info("📥 Downloading from Google Drive...")
        
        tmp_path, error = download_video_from_url(url, status_placeholder)
        
        if error or not tmp_path:
            return None, error or "Download failed"
        
        if status_placeholder:
            status_placeholder.success("✅ Download complete!")
        
        script, error = process_video_from_path(tmp_path, video_name, vision_model_name, writer_model_name, style_text, custom_prompt, status_placeholder)
        return script, error
        
    except Exception as e:
        return None, str(e)
    
    finally:
        cleanup_temp_file(tmp_path)
        force_memory_cleanup()

# --- MAIN TITLE ---
st.markdown("""
<div class="main-title">
    <h1>✨ Ultimate AI Studio</h1>
    <p>// YOUR ALL-IN-ONE CREATIVE DASHBOARD //</p>
</div>
""", unsafe_allow_html=True)

# --- LIBRARY STATUS CHECK ---
missing_libs = []
if not PDF_AVAILABLE:
    missing_libs.append("PyPDF2")
if not DOCX_AVAILABLE:
    missing_libs.append("python-docx")
if not GDOWN_AVAILABLE:
    missing_libs.append("gdown")

if missing_libs:
    st.warning(f"⚠️ Optional libraries missing: {', '.join(missing_libs)}. Add to requirements.txt.")

# --- TOP CONTROL BAR ---
with st.container(border=True):
    col_api, col_vision, col_writer = st.columns([2, 1, 1])
    
    with col_api:
        api_key = st.text_input("🔑 Google API Key", type="password", placeholder="Paste your API key here...", label_visibility="collapsed")
    
    with col_vision:
        vision_model_name = st.selectbox(
            "Vision Model",
            [
                "models/gemini-2.5-flash",
                "models/gemini-2.5-pro",
                "models/gemini-3-pro-preview",
                "gemini-1.5-flash",
                "gemini-1.5-pro",
                "gemini-2.0-flash-exp",
            ],
            index=0,
            help="Model for video analysis",
            label_visibility="collapsed"
        )
    
    with col_writer:
        writer_model_name = st.selectbox(
            "Writer Model",
            [
                "gemini-1.5-flash",
                "gemini-2.0-flash-exp",
                "models/gemini-2.5-flash",
                "models/gemini-3-pro-preview",
                "gemini-1.5-pro",
                "models/gemini-2.5-pro",
            ],
            index=0,
            help="Model for script writing",
            label_visibility="collapsed"
        )
    
    if api_key:
        try:
            genai.configure(api_key=api_key)
        except Exception:
            pass

# --- TABS ---
st.write("") 
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎬 Movie Recap", "🌍 Translator", "🎨 Thumbnail AI", "✍️ Script Rewriter", "📰 AI News"])

# ==========================================
# TAB 1: MOVIE RECAP
# ==========================================
with tab1:
    st.write("")
    col_left, col_right = st.columns([1, 1], gap="medium")

    with col_left:
        with st.container(border=True):
            st.subheader("📂 Add Videos to Queue")
            
            upload_method = st.radio(
                "Choose Input Method:",
                ["📁 Upload Files (Local)", "🔗 Google Drive Links"],
                horizontal=True
            )
            
            st.markdown("---")
            
            if upload_method == "📁 Upload Files (Local)":
                # WARNING for large files
                st.warning("⚠️ **200MB Limit:** Files over 200MB will fail. Use Google Drive links for large files.")
                
                st.info("📌 Upload videos (max 200MB per file)")
                
                uploaded_videos = st.file_uploader(
                    "Select Video Files",
                    type=["mp4", "mkv", "mov"],
                    accept_multiple_files=True,
                    key="file_uploader"
                )
                
                if st.button("➕ Add Files to Queue", use_container_width=True):
                    if not uploaded_videos:
                        st.warning("Please select video files!")
                    else:
                        available_slots = 10 - len(st.session_state['video_queue'])
                        if available_slots <= 0:
                            st.error("Queue is full! Maximum 10 videos.")
                        else:
                            files_to_add = uploaded_videos[:available_slots]
                            added_count = 0
                            
                            for video in files_to_add:
                                try:
                                    # Check file size
                                    video.seek(0, 2)
                                    file_size = video.tell()
                                    video.seek(0)
                                    
                                    if file_size > 200 * 1024 * 1024:  # 200MB
                                        st.error(f"❌ {video.name} is too large ({file_size/(1024*1024):.0f}MB). Use Google Drive for files >200MB.")
                                        continue
                                    
                                    status_msg = st.empty()
                                    status_msg.info(f"💾 Saving {video.name}...")
                                    
                                    tmp_path, error = save_uploaded_file_chunked(video, status_msg)
                                    
                                    if error:
                                        st.error(f"Failed to save {video.name}: {error}")
                                        continue
                                    
                                    st.session_state['video_queue'].append({
                                        'name': video.name,
                                        'source_type': 'file',
                                        'file_path': tmp_path,
                                        'url': None,
                                        'status': 'waiting',
                                        'script': None,
                                        'error': None
                                    })
                                    added_count += 1
                                    status_msg.empty()
                                    
                                except Exception as e:
                                    st.error(f"Failed to add {video.name}: {e}")
                            
                            if added_count > 0:
                                st.success(f"✅ Added {added_count} file(s) to queue!")
                            
                            force_memory_cleanup()
                            st.rerun()
            
            else:
                st.success("✅ **Recommended for large files (1GB+)** - Uses gdown for reliable downloads")
                st.info("📌 Paste Google Drive links (Max 10)")
                st.markdown("""
                <small style='opacity: 0.7;'>
                💡 Make sure files are shared as "Anyone with link can view"
                </small>
                """, unsafe_allow_html=True)
                
                links_input = st.text_area(
                    "Video Links (One per line)",
                    height=200,
                    placeholder="https://drive.google.com/file/d/XXX/view\nhttps://drive.google.com/file/d/YYY/view",
                    key="links_input"
                )
                
                if st.button("➕ Add Links to Queue", use_container_width=True):
                    if not links_input.strip():
                        st.warning("Please paste video links!")
                    else:
                        raw_links = [link.strip() for link in links_input.split('\n') if link.strip()]
                        available_slots = 10 - len(st.session_state['video_queue'])
                        
                        if available_slots <= 0:
                            st.error("Queue is full! Maximum 10 videos.")
                        else:
                            links_to_add = raw_links[:available_slots]
                            valid_count = 0
                            
                            for idx, link in enumerate(links_to_add):
                                if 'drive.google.com' not in link:
                                    st.warning(f"⚠️ Skipping invalid link: {link[:50]}...")
                                    continue
                                
                                file_id = extract_file_id_from_url(link)
                                if not file_id:
                                    st.warning(f"⚠️ Could not extract file ID from: {link[:50]}...")
                                    continue
                                
                                st.session_state['video_queue'].append({
                                    'name': f"Video_{len(st.session_state['video_queue']) + 1}",
                                    'source_type': 'url',
                                    'file_path': None,
                                    'url': link,
                                    'status': 'waiting',
                                    'script': None,
                                    'error': None
                                })
                                valid_count += 1
                            
                            if valid_count > 0:
                                st.success(f"✅ Added {valid_count} link(s) to queue!")
                            st.rerun()
            
            st.markdown("---")
            st.markdown("**⚙️ Settings**")
            
            # Show selected models
            st.caption(f"🔬 Vision: {vision_model_name.split('/')[-1]} | ✍️ Writer: {writer_model_name.split('/')[-1]}")
            
            with st.expander("📝 Custom Instructions (Optional)", expanded=False):
                custom_prompt = st.text_area(
                    "Add your custom instructions here:",
                    value=st.session_state.get('custom_prompt', ''),
                    height=100,
                    placeholder="Example: Focus on romantic scenes, Include character names...",
                    key="custom_prompt_input"
                )
                if custom_prompt:
                    st.session_state['custom_prompt'] = custom_prompt
                    st.caption("✅ Custom instructions will be added")
            
            style_file = st.file_uploader("📄 Writing Style Reference (Optional)", type=["txt", "pdf", "docx"], key="style_uploader")
            
            if style_file:
                extracted_style = read_file_content(style_file)
                if extracted_style:
                    style_text = f"\n\n**WRITING STYLE REFERENCE:**\n{extracted_style[:5000]}\n"
                    st.session_state['style_text'] = style_text
                    st.caption(f"✅ Style loaded: {style_file.name}")
            
            st.markdown("---")
            
            col_start, col_clear = st.columns(2)
            
            with col_start:
                start_disabled = len(st.session_state['video_queue']) == 0 or st.session_state['processing_active']
                if st.button("🚀 Start Processing", use_container_width=True, disabled=start_disabled):
                    if not api_key:
                        st.error("Please enter API Key above.")
                    else:
                        st.session_state['processing_active'] = True
                        st.session_state['current_index'] = 0
                        st.rerun()
            
            with col_clear:
                if st.button("🗑️ Clear Queue", use_container_width=True, disabled=len(st.session_state['video_queue']) == 0):
                    for item in st.session_state['video_queue']:
                        cleanup_temp_file(item.get('file_path'))
                    
                    st.session_state['video_queue'] = []
                    st.session_state['processing_active'] = False
                    st.session_state['current_index'] = 0
                    force_memory_cleanup()
                    st.success("Queue cleared!")
                    st.rerun()

    with col_right:
        with st.container(border=True):
            st.subheader("📋 Processing Queue")
            
            if len(st.session_state['video_queue']) == 0:
                st.info("💡 Queue is empty. Add videos using files or links.")
                st.markdown("""
                **Two Ways to Add Videos:**
                
                **Method 1: Upload Files** 📁
                - For files under 200MB only
                - Larger files will fail (Streamlit limit)
                
                **Method 2: Google Drive Links** 🔗 ✅ Recommended
                - Upload videos to Google Drive first
                - Share → "Anyone with link can view"
                - Supports large files (1GB+)
                """)
            else:
                total = len(st.session_state['video_queue'])
                completed = sum(1 for v in st.session_state['video_queue'] if v['status'] == 'completed')
                failed = sum(1 for v in st.session_state['video_queue'] if v['status'] == 'failed')
                waiting = sum(1 for v in st.session_state['video_queue'] if v['status'] == 'waiting')
                
                col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                with col_stat1:
                    st.metric("Total", total)
                with col_stat2:
                    st.metric("Completed", completed)
                with col_stat3:
                    st.metric("Failed", failed)
                with col_stat4:
                    st.metric("Waiting", waiting)
                
                st.progress(completed / total if total > 0 else 0)
                
                st.markdown("---")
                
                for idx, item in enumerate(st.session_state['video_queue']):
                    status_emoji = {
                        'waiting': '⏳',
                        'processing': '🔄',
                        'completed': '✅',
                        'failed': '❌'
                    }
                    
                    source_icon = '📁' if item['source_type'] == 'file' else '🔗'
                    css_class = item['status']
                    
                    st.markdown(f"""
                    <div class='queue-item {css_class}'>
                        <strong>{status_emoji[item['status']]} {source_icon} {idx + 1}. {item['name']}</strong>
                        <br><small>Status: {item['status'].upper()}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if item['status'] == 'completed' and item['script']:
                        filename = f"{item['name'].rsplit('.', 1)[0]}_recap.txt"
                        st.download_button(
                            f"📥 Download Script #{idx + 1}",
                            item['script'],
                            file_name=filename,
                            key=f"download_{idx}"
                        )
                    
                    if item['status'] == 'failed' and item['error']:
                        st.error(f"Error: {item['error'][:300]}")
        
        if st.session_state['processing_active']:
            current_idx = st.session_state['current_index']
            
            if current_idx < len(st.session_state['video_queue']):
                current_item = st.session_state['video_queue'][current_idx]
                
                if current_item['status'] == 'waiting':
                    st.session_state['video_queue'][current_idx]['status'] = 'processing'
                    
                    with st.container(border=True):
                        st.markdown(f"### 🔄 Processing: {current_item['name']}")
                        
                        status_placeholder = st.empty()
                        style_text = st.session_state.get('style_text', "")
                        custom_prompt = st.session_state.get('custom_prompt', "")
                        
                        if current_item['source_type'] == 'file':
                            script, error = process_video_from_path(
                                current_item['file_path'],
                                current_item['name'],
                                vision_model_name,
                                writer_model_name,
                                style_text,
                                custom_prompt,
                                status_placeholder
                            )
                            cleanup_temp_file(current_item['file_path'])
                        
                        else:
                            script, error = process_video_from_url(
                                current_item['url'],
                                current_item['name'],
                                vision_model_name,
                                writer_model_name,
                                style_text,
                                custom_prompt,
                                status_placeholder
                            )
                        
                        if script:
                            st.session_state['video_queue'][current_idx]['status'] = 'completed'
                            st.session_state['video_queue'][current_idx]['script'] = script
                            status_placeholder.success(f"✅ Completed: {current_item['name']}")
                            
                            filename = f"{current_item['name'].rsplit('.', 1)[0]}_recap.txt"
                            st.download_button(
                                "📥 Download Now",
                                script,
                                file_name=filename,
                                key=f"auto_dl_{current_idx}"
                            )
                        else:
                            st.session_state['video_queue'][current_idx]['status'] = 'failed'
                            st.session_state['video_queue'][current_idx]['error'] = error
                            status_placeholder.error(f"❌ Failed: {current_item['name']}")
                        
                        # Add delay between videos to avoid rate limiting
                        st.info("⏳ Waiting 10 seconds before next video (rate limit protection)...")
                        time.sleep(10)
                        
                        st.session_state['current_index'] += 1
                        force_memory_cleanup()
                        st.rerun()
            
            else:
                completed_count = sum(1 for v in st.session_state['video_queue'] if v['status'] == 'completed')
                failed_count = sum(1 for v in st.session_state['video_queue'] if v['status'] == 'failed')
                
                st.success(f"🎉 All videos processed! ✅ {completed_count} completed, ❌ {failed_count} failed")
                st.balloons()
                st.session_state['processing_active'] = False

# ==========================================
# TAB 2: TRANSLATOR
# ==========================================
with tab2:
    st.write("")
    c1, c2 = st.columns([1, 1], gap="medium")
    
    with c1:
        with st.container(border=True):
            st.subheader("📄 Upload Media")
            uploaded_file = st.file_uploader("File (.mp3, .mp4, .txt, .srt)", type=["mp3", "mp4", "txt", "srt"], key="translator_uploader")
            if st.button("🚀 Translate Now", use_container_width=True):
                if not api_key:
                    st.error("⚠️ Please enter API Key first!")
                elif not uploaded_file:
                    st.warning("⚠️ Please upload a file first!")
                else:
                    st.session_state['run_translate'] = True

    with c2:
        if st.session_state.get('run_translate') and uploaded_file and api_key:
            with st.container(border=True):
                st.subheader("📝 Output")
                try:
                    file_ext = uploaded_file.name.split('.')[-1].lower()
                    if file_ext in ['txt', 'srt']:
                        with st.spinner("📝 Translating text..."):
                            text_content = uploaded_file.getvalue().decode("utf-8")
                            model = genai.GenerativeModel(writer_model_name)
                            res, error = call_gemini_api(model, f"Translate to **Burmese**. Return ONLY translated text.\nInput:\n{text_content}")
                            if res and not error:
                                text, _ = get_response_text_safe(res)
                                if text:
                                    st.text_area("Result", text, height=300)
                                    st.download_button("📥 Download", text, file_name=f"trans_{uploaded_file.name}")
                            else:
                                st.error(f"Translation failed: {error}")
                    else:
                        with st.spinner("🎧 Listening & Translating..."):
                            tmp_path, error = save_uploaded_file_chunked(uploaded_file)
                            if error:
                                st.error(f"Error: {error}")
                            else:
                                gemini_file = upload_to_gemini(tmp_path)
                                if gemini_file:
                                    model = genai.GenerativeModel(writer_model_name)
                                    res, error = call_gemini_api(model, [gemini_file, "Generate full transcript in **Burmese**."], timeout=600)
                                    if res and not error:
                                        text, _ = get_response_text_safe(res)
                                        if text:
                                            st.text_area("Transcript", text, height=300)
                                            st.download_button("📥 Download", text, file_name=f"{uploaded_file.name}_trans.txt")
                                    else:
                                        st.error(f"Transcription failed: {error}")
                                    try: 
                                        genai.delete_file(gemini_file.name)
                                    except: 
                                        pass
                                cleanup_temp_file(tmp_path)
                            force_memory_cleanup()
                            
                except Exception as e: 
                    st.error(f"Error: {e}")
                st.session_state['run_translate'] = False
        else:
            with st.container(border=True):
                st.info("💡 Upload a file and click 'Translate Now' to start.")

# ==========================================
# TAB 3: THUMBNAIL AI
# ==========================================
with tab3:
    st.write("")
    
    col_thumb_left, col_thumb_right = st.columns([1, 1], gap="medium")
    
    with col_thumb_left:
        with st.container(border=True):
            st.subheader("🎨 AI Thumbnail Generator")
            st.markdown("<p style='opacity: 0.7;'>Gemini API နဲ့ Image Generate လုပ်ပါ</p>", unsafe_allow_html=True)
            
            st.markdown("**🖼️ Reference Image (Optional):**")
            ref_image = st.file_uploader(
                "Upload reference image",
                type=["png", "jpg", "jpeg", "webp"],
                key="thumb_ref_image"
            )
            
            if ref_image:
                col_img_preview, _ = st.columns([1, 2])
                with col_img_preview:
                    st.image(ref_image, caption="Reference", width=150)
            
            st.markdown("---")
            
            st.markdown("**📝 Quick Templates:**")
            prompt_templates = {
                "✍️ Custom Prompt": "",
                "🎬 Movie Recap Thumbnail": "Create a dramatic YouTube movie recap thumbnail, 1280x720 pixels, with cinematic dark color grading, showing dramatic scene with emotional expressions, bold eye-catching title text, professional high contrast style",
                "😱 Shocking/Dramatic Style": "Create a YouTube thumbnail with shocked surprised expression style, bright red and yellow accent colors, large bold text with outline, arrow pointing to key element, exaggerated expressions, 1280x720 pixels",
                "🎭 Before/After Comparison": "Create a before and after comparison YouTube thumbnail, split screen design with clear dividing line, contrasting colors for each side, bold BEFORE and AFTER labels, 1280x720 pixels",
                "🔥 Top 10 List Style": "Create a Top 10 list style YouTube thumbnail, large number prominently displayed, grid collage of related images, bright energetic colors, bold sans-serif title, 1280x720 pixels",
            }
            
            selected_template = st.selectbox(
                "Template ရွေးပါ:",
                list(prompt_templates.keys()),
                key="thumb_template"
            )
            
            default_prompt = prompt_templates[selected_template]
            user_prompt = st.text_area(
                "🖼️ Image Prompt:",
                value=default_prompt,
                height=150,
                placeholder="Describe the thumbnail you want to generate...",
                key="thumb_prompt_input"
            )
            
            st.markdown("**⚙️ Customization:**")
            col_opt1, col_opt2 = st.columns(2)
            
            with col_opt1:
                add_text = st.text_input(
                    "Text on Image:",
                    placeholder="e.g., EP.1, PART 2",
                    key="thumb_text"
                )
            
            with col_opt2:
                num_images = st.selectbox(
                    "Number of Images:",
                    [1, 2, 3, 4],
                    index=0,
                    key="thumb_num"
                )
            
            style_options = st.multiselect(
                "Style Modifiers:",
                ["Cinematic", "Dramatic Lighting", "High Contrast", "Vibrant Colors", "Dark Mood", "Professional", "YouTube Style", "4K Quality"],
                default=["YouTube Style", "High Contrast"],
                key="thumb_styles"
            )
            
            st.markdown("---")
            st.success("🎯 Using Gemini 3 Pro - မြန်မာဘာသာ caption ထည့်ရေးပေးနိုင်တယ်။")
            
            generate_clicked = st.button("🚀 Generate Thumbnail", use_container_width=True)
    
    with col_thumb_right:
        with st.container(border=True):
            st.subheader("🖼️ Generated Images")
            
            if generate_clicked:
                if not api_key:
                    st.error("⚠️ Please enter API Key first!")
                elif not user_prompt.strip():
                    st.warning("⚠️ Please enter a prompt!")
                else:
                    st.session_state['generated_images'] = []
                    
                    final_prompt = user_prompt.strip()
                    if add_text:
                        final_prompt += f", with bold text overlay showing '{add_text}'"
                    if style_options:
                        final_prompt += f", style: {', '.join(style_options)}"
                    final_prompt += ", high quality, detailed, sharp focus"
                    
                    st.info("🎨 Using Gemini 3 Pro...")
                    st.markdown(f"**Prompt:** {final_prompt[:200]}...")
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    generated_images = []
                    
                    try:
                        image_model = genai.GenerativeModel("models/gemini-3-pro-image-preview")
                        
                        for i in range(num_images):
                            try:
                                status_text.info(f"🔄 Generating image {i+1}/{num_images}...")
                                progress_bar.progress((i) / num_images)
                                
                                generation_prompt = f"Generate an image: {final_prompt}"
                                
                                if ref_image:
                                    ref_image.seek(0)
                                    ref_img = Image.open(ref_image)
                                    response = image_model.generate_content(
                                        [generation_prompt, ref_img],
                                        request_options={"timeout": 180}
                                    )
                                else:
                                    response = image_model.generate_content(
                                        generation_prompt,
                                        request_options={"timeout": 180}
                                    )
                                
                                image_found = False
                                if response.candidates:
                                    for part in response.candidates[0].content.parts:
                                        if hasattr(part, 'inline_data') and part.inline_data:
                                            generated_images.append({
                                                'data': part.inline_data.data,
                                                'mime_type': part.inline_data.mime_type,
                                                'index': i + 1
                                            })
                                            image_found = True
                                            status_text.success(f"✅ Image {i+1} generated!")
                                            break
                                
                                if not image_found:
                                    status_text.warning(f"⚠️ Image {i+1}: No image generated.")
                                
                                if i < num_images - 1:
                                    time.sleep(2)
                                    
                            except Exception as e:
                                status_text.error(f"⚠️ Image {i+1} failed: {str(e)[:150]}")
                                continue
                        
                        progress_bar.progress(1.0)
                        st.session_state['generated_images'] = generated_images
                        
                        if generated_images:
                            status_text.success(f"🎉 Done! Generated {len(generated_images)}/{num_images} image(s)")
                        else:
                            status_text.error("❌ No images were generated.")
                    
                    except Exception as e:
                        st.error(f"❌ Generation Error: {e}")
            
            if st.session_state['generated_images']:
                st.markdown("---")
                for idx, img_data in enumerate(st.session_state['generated_images']):
                    st.markdown(f"**Image {img_data['index']}:**")
                    st.image(img_data['data'], use_container_width=True)
                    
                    file_ext = "png" if "png" in img_data.get('mime_type', 'png') else "jpg"
                    st.download_button(
                        f"📥 Download Image {img_data['index']}",
                        img_data['data'],
                        file_name=f"thumbnail_{idx+1}.{file_ext}",
                        mime=img_data.get('mime_type', 'image/png'),
                        key=f"dl_thumb_{idx}_{time.time()}"
                    )
                    st.markdown("---")
                
                if st.button("🗑️ Clear All Images", use_container_width=True, key="clear_thumb"):
                    st.session_state['generated_images'] = []
                    st.rerun()
            
            elif not generate_clicked:
                st.info("💡 Enter a prompt and click 'Generate Thumbnail' to create images.")

# ==========================================
# TAB 4: SCRIPT REWRITER
# ==========================================
with tab4:
    st.write("")
    col_re_1, col_re_2 = st.columns([1, 1], gap="medium")
    
    with col_re_1:
        with st.container(border=True):
            st.subheader("✍️ Style & Source")
            
            rewrite_style_file = st.file_uploader("1. Upload Writing Style", type=["txt", "pdf", "docx"], key="rewrite_style_uploader")
            original_script = st.text_area("2. Paste Original Script Here", height=300, placeholder="Paste the script you want to rewrite...")
            
            if st.button("✨ Rewrite Script", use_container_width=True):
                if not api_key:
                    st.error("⚠️ API Key Missing!")
                elif not original_script:
                    st.warning("⚠️ Please paste the original script.")
                else:
                    st.session_state['run_rewrite'] = True

    with col_re_2:
        if st.session_state.get('run_rewrite'):
            with st.container(border=True):
                st.subheader("📝 Rewritten Output")
                
                try:
                    style_content_rewrite = "Standard Professional Tone"
                    
                    if rewrite_style_file:
                        with st.spinner("📖 Reading Style File..."):
                            extracted_text = read_file_content(rewrite_style_file)
                            if extracted_text:
                                style_content_rewrite = extracted_text
                                st.success(f"✅ Loaded style from {rewrite_style_file.name}")

                    with st.spinner("🤖 Rewriting..."):
                        rewrite_model = genai.GenerativeModel(writer_model_name)
                        
                        rewrite_prompt = f"""
                        You are an expert Script Editor.
                        
                        **TASK:** Rewrite the ORIGINAL SCRIPT using the TARGET WRITING STYLE.
                        
                        **RULES:**
                        1. NO SUMMARIZATION - keep all details
                        2. 100% CONTENT PRESERVATION
                        3. MATCH STYLE strictly
                        4. OUTPUT: Burmese (Myanmar)
                        
                        **TARGET STYLE:**
                        {style_content_rewrite[:5000]} 
                        
                        **ORIGINAL SCRIPT:**
                        {original_script}
                        """
                        
                        rewrite_response, error = call_gemini_api(rewrite_model, rewrite_prompt)
                        
                        if rewrite_response and not error:
                            text, _ = get_response_text_safe(rewrite_response)
                            if text:
                                st.success("✅ Rewrite Complete!")
                                st.text_area("Result", text, height=500)
                                st.download_button("📥 Download", text, file_name="rewritten_script.txt")
                            else:
                                st.error("❌ Failed to extract rewritten text.")
                        else:
                            st.error(f"❌ Rewrite failed: {error}")
                        
                except Exception as e:
                    st.error(f"Error: {e}")
                
                st.session_state['run_rewrite'] = False
        else:
            with st.container(border=True):
                st.info("💡 Paste a script and upload a style to rewrite.")

# ==========================================
# TAB 5: AI NEWS
# ==========================================
with tab5:
    st.write("")
    
    with st.container(border=True):
        st.subheader("📰 AI News - နောက်ဆုံးရ AI သတင်းများ")
        st.markdown("နာမည်ကြီး AI Companies များရဲ့ နောက်ဆုံးရ သတင်းများကို Gemini နဲ့ ရှာဖွေပြသပေးပါတယ်။")
        
        col_news_btn, col_news_status = st.columns([1, 2])
        
        with col_news_btn:
            fetch_news = st.button("🔄 Refresh AI News", use_container_width=True)
        
        with col_news_status:
            # Show cache status
            if st.session_state.get('ai_news_timestamp'):
                st.caption(f"Last updated: {st.session_state['ai_news_timestamp']}")
        
        st.markdown("---")
        
        if fetch_news:
            if not api_key:
                st.error("⚠️ Please enter API Key first!")
            else:
                with st.spinner("🔍 Fetching latest AI news..."):
                    try:
                        news_model = genai.GenerativeModel(writer_model_name)
                        
                        news_prompt = """
                        You are an AI news reporter. Please provide the latest news and updates about major AI companies and their products.
                        
                        Cover these companies/products:
                        1. OpenAI (ChatGPT, GPT-4, GPT-5, Sora)
                        2. Google (Gemini, Bard, DeepMind)
                        3. Anthropic (Claude)
                        4. Meta (Llama, AI features)
                        5. Microsoft (Copilot, Azure AI)
                        6. Stability AI (Stable Diffusion)
                        7. Midjourney
                        8. Other notable AI news
                        
                        For each company, provide:
                        - Latest product updates or releases
                        - New features announced
                        - Important news or changes
                        - Pricing changes if any
                        
                        Format: Use clear headers for each company. Keep it concise but informative.
                        Write in English.
                        Include approximate dates if known.
                        """
                        
                        response, error = call_gemini_api(news_model, news_prompt, timeout=120)
                        
                        if response and not error:
                            news_text, _ = get_response_text_safe(response)
                            if news_text:
                                st.session_state['ai_news_cache'] = news_text
                                st.session_state['ai_news_timestamp'] = time.strftime("%Y-%m-%d %H:%M:%S")
                                st.success("✅ News updated!")
                            else:
                                st.error("Failed to get news content")
                        else:
                            st.error(f"Failed to fetch news: {error}")
                            
                    except Exception as e:
                        st.error(f"Error fetching news: {e}")
        
        # Display cached news
        if st.session_state.get('ai_news_cache'):
            st.markdown(st.session_state['ai_news_cache'])
        else:
            st.info("👆 Click 'Refresh AI News' to fetch the latest AI news and updates.")
            
            # Show placeholder content
            st.markdown("""
            **📌 Covered AI Companies:**
            
            - 🤖 **OpenAI** - ChatGPT, GPT-4, GPT-5, Sora
            - 🔷 **Google** - Gemini, DeepMind
            - 🟠 **Anthropic** - Claude
            - 🔵 **Meta** - Llama, AI features
            - 🟦 **Microsoft** - Copilot, Azure AI
            - 🎨 **Stability AI** - Stable Diffusion
            - 🖼️ **Midjourney**
            - 📰 **Other AI News**
            """)

# --- FOOTER ---
st.markdown("""
<div style='text-align: center; margin-top: 3rem; padding: 1.5rem 0; border-top: 1px solid rgba(0, 255, 100, 0.1);'>
    <p style='color: rgba(0, 255, 100, 0.4) !important; font-size: 0.85rem; margin: 0; font-family: "Share Tech Mono", monospace; letter-spacing: 1px;'>
        ✨ ULTIMATE AI STUDIO • POWERED BY GOOGLE GEMINI • ENTER THE MATRIX
    </p>
</div>
""", unsafe_allow_html=True)



