import streamlit as st
import google.generativeai as genai
import time
import os
import tempfile
import gc
import io
import hashlib
import asyncio
from PIL import Image
import requests
import subprocess
import sys

# --- LIBRARY IMPORTS WITH GRACEFUL FALLBACK ---
PDF_AVAILABLE = True
DOCX_AVAILABLE = True
GDOWN_AVAILABLE = True
SUPABASE_AVAILABLE = True
EDGE_TTS_AVAILABLE = True

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

try:
    from supabase import create_client
except ImportError:
    SUPABASE_AVAILABLE = False

try:
    import edge_tts
except ImportError:
    EDGE_TTS_AVAILABLE = False

# --- SUPABASE CONFIGURATION ---
SUPABASE_URL = "https://ohjvgupjocgsirhwuobf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9oanZndXBqb2Nnc2lyaHd1b2JmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU5MzkwMTgsImV4cCI6MjA4MTUxNTAxOH0.oZxQZ6oksjbmEeA_m8c44dG_z5hHLwtgoJssgK2aogI"

# Initialize Supabase client
supabase = None
if SUPABASE_AVAILABLE:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        SUPABASE_AVAILABLE = False

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
        'ai_news_timestamp': None,
        'notes_list': [],
        'current_note_id': None,
        'tts_audio': None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- MATRIX RAIN BACKGROUND CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');
    
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
        box-shadow: 0 4px 24px rgba(0, 255, 100, 0.15);
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
    }
    
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: rgba(0, 255, 100, 0.7) !important;
        box-shadow: 0 0 0 3px rgba(0, 255, 100, 0.15) !important;
    }
    
    .stSelectbox div[data-baseweb="select"] > div {
        background: rgba(0, 20, 10, 0.7) !important;
        border: 2px solid rgba(0, 255, 100, 0.3) !important;
        border-radius: 10px !important;
        color: #00ff66 !important;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, rgba(0, 200, 80, 0.9) 0%, rgba(0, 150, 60, 0.9) 100%);
        color: #000 !important;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 1.5rem;
        font-weight: 700;
        font-size: 14px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 255, 100, 0.3);
        text-transform: uppercase;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 25px rgba(0, 255, 100, 0.5);
    }
    
    .stDownloadButton > button {
        background: linear-gradient(135deg, rgba(0, 180, 255, 0.9) 0%, rgba(0, 120, 200, 0.9) 100%) !important;
        color: #000 !important;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(0, 40, 20, 0.6);
        padding: 8px;
        border-radius: 12px;
        border: 1px solid rgba(0, 255, 100, 0.2);
        flex-wrap: wrap;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        color: rgba(0, 255, 100, 0.7);
        border: 1px solid transparent;
        padding: 10px 16px;
        font-weight: 500;
        font-size: 13px;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(0, 200, 80, 0.9) 0%, rgba(0, 150, 60, 0.9) 100%) !important;
        color: #000 !important;
        font-weight: 700;
    }
    
    h1 {
        color: #00ff66 !important;
        font-weight: 700 !important;
        font-size: 2rem !important;
        text-shadow: 0 0 10px rgba(0, 255, 100, 0.5);
    }
    
    h2, h3 {
        color: #00ff66 !important;
        font-weight: 600 !important;
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
        font-family: 'Share Tech Mono', monospace;
    }
    
    .queue-item.completed {
        background: rgba(0, 180, 255, 0.1);
        border-color: rgba(0, 180, 255, 0.5);
    }
    
    .queue-item.failed {
        background: rgba(255, 50, 50, 0.1);
        border-color: rgba(255, 50, 50, 0.5);
    }
    
    .note-card {
        background: rgba(0, 40, 20, 0.6);
        border: 1px solid rgba(0, 255, 100, 0.3);
        border-radius: 10px;
        padding: 12px;
        margin: 8px 0;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .note-card:hover {
        border-color: rgba(0, 255, 100, 0.6);
        box-shadow: 0 0 15px rgba(0, 255, 100, 0.2);
    }
    
    .main-title { text-align: center; padding: 1rem 0 0.5rem 0; }
    
    .main-title h1 {
        background: linear-gradient(135deg, #00ff66, #00ffaa, #00ff66);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem !important;
        animation: title-glow 3s ease-in-out infinite;
    }
    
    @keyframes title-glow {
        0%, 100% { filter: drop-shadow(0 0 10px rgba(0, 255, 100, 0.5)); }
        50% { filter: drop-shadow(0 0 20px rgba(0, 255, 100, 0.8)); }
    }
    
    .main-title p {
        color: rgba(0, 255, 100, 0.5) !important;
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
</style>

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

def get_user_hash(api_key):
    """Generate a hash from API key for user identification"""
    return hashlib.sha256(api_key.encode()).hexdigest()[:32]

def force_memory_cleanup():
    """Force garbage collection"""
    gc.collect()
    if 'temp_data' in st.session_state:
        del st.session_state['temp_data']

# --- SUPABASE NOTES FUNCTIONS ---

def get_notes(user_hash):
    """Get all notes for a user"""
    if not SUPABASE_AVAILABLE or not supabase:
        return []
    try:
        response = supabase.table('notes').select('*').eq('user_hash', user_hash).order('updated_at', desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error fetching notes: {e}")
        return []

def create_note(user_hash, title, content):
    """Create a new note"""
    if not SUPABASE_AVAILABLE or not supabase:
        return None
    try:
        response = supabase.table('notes').insert({
            'user_hash': user_hash,
            'title': title,
            'content': content
        }).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        st.error(f"Error creating note: {e}")
        return None

def update_note(note_id, title, content):
    """Update an existing note"""
    if not SUPABASE_AVAILABLE or not supabase:
        return None
    try:
        response = supabase.table('notes').update({
            'title': title,
            'content': content,
            'updated_at': 'now()'
        }).eq('id', note_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        st.error(f"Error updating note: {e}")
        return None

def delete_note(note_id):
    """Delete a note"""
    if not SUPABASE_AVAILABLE or not supabase:
        return False
    try:
        supabase.table('notes').delete().eq('id', note_id).execute()
        return True
    except Exception as e:
        st.error(f"Error deleting note: {e}")
        return False

# --- EDGE TTS FUNCTIONS ---

def get_voice_list():
    """Get available voices for Edge TTS"""
    return {
        "🇲🇲 Myanmar (Thiha)": "my-MM-ThihaNeural",
        "🇲🇲 Myanmar (Nilar)": "my-MM-NilarNeural",
        "🇺🇸 English US (Jenny)": "en-US-JennyNeural",
        "🇺🇸 English US (Guy)": "en-US-GuyNeural",
        "🇬🇧 English UK (Sonia)": "en-GB-SoniaNeural",
        "🇨🇳 Chinese (Xiaoxiao)": "zh-CN-XiaoxiaoNeural",
        "🇯🇵 Japanese (Nanami)": "ja-JP-NanamiNeural",
        "🇰🇷 Korean (SunHi)": "ko-KR-SunHiNeural",
        "🇹🇭 Thai (Premwadee)": "th-TH-PremwadeeNeural",
        "🇻🇳 Vietnamese (HoaiMy)": "vi-VN-HoaiMyNeural",
    }

async def generate_tts_async(text, voice, rate, output_path):
    """Generate TTS audio using Edge TTS"""
    rate_str = f"+{rate}%" if rate >= 0 else f"{rate}%"
    communicate = edge_tts.Communicate(text, voice, rate=rate_str)
    await communicate.save(output_path)

def generate_tts(text, voice, rate=0):
    """Wrapper for async TTS generation"""
    if not EDGE_TTS_AVAILABLE:
        return None, "Edge TTS not available"
    
    try:
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
        asyncio.run(generate_tts_async(text, voice, rate, output_path))
        return output_path, None
    except Exception as e:
        return None, str(e)

# --- VIDEO PROCESSING FUNCTIONS ---

def extract_file_id_from_url(url):
    """Extract Google Drive file ID"""
    try:
        if 'drive.google.com' in url:
            if '/file/d/' in url:
                return url.split('/file/d/')[1].split('/')[0].split('?')[0]
            elif 'id=' in url:
                return url.split('id=')[1].split('&')[0]
        return None
    except:
        return None

def download_video_from_url_gdown(url, progress_placeholder=None):
    """Download video from Google Drive"""
    try:
        file_id = extract_file_id_from_url(url)
        if not file_id:
            return None, "Invalid Google Drive URL"
        
        if progress_placeholder:
            progress_placeholder.info("📥 Downloading from Google Drive...")
        
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        tmp_path = tmp_file.name
        tmp_file.close()
        
        gdrive_url = f"https://drive.google.com/uc?id={file_id}"
        
        if GDOWN_AVAILABLE:
            output = gdown.download(gdrive_url, tmp_path, quiet=False, fuzzy=True)
            if output is None:
                return None, "Download failed. Check if file is shared publicly."
        else:
            return None, "gdown not available"
        
        if not os.path.exists(tmp_path):
            return None, "Download failed"
        
        file_size = os.path.getsize(tmp_path)
        if file_size < 1000:
            os.remove(tmp_path)
            return None, "Downloaded file too small"
        
        if progress_placeholder:
            progress_placeholder.success(f"✅ Downloaded: {file_size/(1024*1024):.1f} MB")
        
        return tmp_path, None
    except Exception as e:
        return None, str(e)

def download_video_from_url(url, progress_placeholder=None):
    """Smart download"""
    if GDOWN_AVAILABLE:
        return download_video_from_url_gdown(url, progress_placeholder)
    return None, "gdown not available"

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
            progress_placeholder.info(f"💾 Saving file ({file_size/(1024*1024):.1f} MB)...")
        
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
            progress_placeholder.success(f"✅ Saved: {written/(1024*1024):.1f} MB")
        
        return tmp_path, None
    except Exception as e:
        return None, str(e)

def upload_to_gemini(file_path, mime_type=None, progress_placeholder=None):
    """Upload to Gemini"""
    try:
        if progress_placeholder:
            file_size = os.path.getsize(file_path)
            progress_placeholder.info(f"📤 Uploading to Gemini ({file_size/(1024*1024):.1f} MB)...")
        
        file = genai.upload_file(file_path, mime_type=mime_type)
        
        wait_count = 0
        while file.state.name == "PROCESSING":
            wait_count += 1
            if progress_placeholder:
                progress_placeholder.info(f"⏳ Processing... ({wait_count * 2}s)")
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
            progress_placeholder.error(f"❌ Error: {e}")
        return None

def read_file_content(uploaded_file):
    """Read file content"""
    try:
        file_type = uploaded_file.type
        
        if file_type == "text/plain":
            return uploaded_file.getvalue().decode("utf-8")
        elif file_type == "application/pdf" and PDF_AVAILABLE:
            reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.getvalue()))
            return "\n".join([p.extract_text() or "" for p in reader.pages])
        elif "wordprocessingml" in file_type and DOCX_AVAILABLE:
            doc = Document(io.BytesIO(uploaded_file.getvalue()))
            return "\n".join([p.text for p in doc.paragraphs])
        return None
    except:
        return None

def cleanup_temp_file(file_path):
    """Remove temp file"""
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except:
            pass

def get_response_text_safe(response):
    """Safely extract text from Gemini response"""
    try:
        if not response or not response.candidates:
            return None, "Empty response"
        
        candidate = response.candidates[0]
        if not hasattr(candidate, 'content') or not candidate.content.parts:
            return None, "No content"
        
        text_parts = [p.text for p in candidate.content.parts if hasattr(p, 'text') and p.text]
        return "\n".join(text_parts) if text_parts else (None, "No text")
        
    except Exception as e:
        return None, str(e)

def call_gemini_api(model, content, timeout=600):
    """Call Gemini API with retry"""
    max_retries = 3
    base_delay = 10
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(content, request_options={"timeout": timeout})
            text, error = get_response_text_safe(response)
            if error and attempt < max_retries - 1:
                time.sleep(base_delay)
                continue
            return response, None
        except Exception as e:
            error_str = str(e).lower()
            if any(x in error_str for x in ['rate', 'quota', '429', 'resource']):
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    st.warning(f"⏳ Rate limited. Waiting {delay}s...")
                    time.sleep(delay)
                else:
                    return None, "Rate limit exceeded"
            else:
                return None, str(e)
    return None, "Max retries exceeded"

def process_video_from_path(file_path, video_name, vision_model_name, writer_model_name, style_text="", custom_prompt="", status_placeholder=None):
    """Process video"""
    gemini_file = None
    try:
        if status_placeholder:
            status_placeholder.info("📤 Step 1/3: Uploading...")
        
        gemini_file = upload_to_gemini(file_path, progress_placeholder=status_placeholder)
        if not gemini_file:
            return None, "Upload failed"
        
        if status_placeholder:
            status_placeholder.info("👀 Step 2/3: Analyzing...")
        
        vision_model = genai.GenerativeModel(vision_model_name)
        vision_prompt = """Watch this video carefully. Generate a detailed scene-by-scene description with dialogue, emotions, and actions."""
        
        vision_response, error = call_gemini_api(vision_model, [gemini_file, vision_prompt], timeout=600)
        if error:
            return None, f"Vision failed: {error}"
        
        video_description, _ = get_response_text_safe(vision_response)
        time.sleep(5)
        
        if status_placeholder:
            status_placeholder.info("✍️ Step 3/3: Writing script...")
        
        writer_model = genai.GenerativeModel(writer_model_name)
        writer_prompt = f"""You are a Burmese Movie Recap Scriptwriter.
        
**INPUT:** {video_description}
{style_text}
{f"**CUSTOM:** {custom_prompt}" if custom_prompt else ""}

**INSTRUCTIONS:** Write in 100% Burmese, storytelling tone, scene-by-scene, full details."""
        
        final_response, error = call_gemini_api(writer_model, writer_prompt, timeout=600)
        if error:
            return None, f"Writing failed: {error}"
        
        final_text, _ = get_response_text_safe(final_response)
        return final_text, None
        
    except Exception as e:
        return None, str(e)
    finally:
        if gemini_file:
            try:
                genai.delete_file(gemini_file.name)
            except:
                pass
        force_memory_cleanup()

def process_video_from_url(url, video_name, vision_model_name, writer_model_name, style_text="", custom_prompt="", status_placeholder=None):
    """Process video from URL"""
    tmp_path = None
    try:
        if status_placeholder:
            status_placeholder.info("📥 Downloading...")
        
        tmp_path, error = download_video_from_url(url, status_placeholder)
        if error:
            return None, error
        
        return process_video_from_path(tmp_path, video_name, vision_model_name, writer_model_name, style_text, custom_prompt, status_placeholder)
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

# --- LIBRARY STATUS ---
missing = []
if not PDF_AVAILABLE: missing.append("PyPDF2")
if not DOCX_AVAILABLE: missing.append("python-docx")
if not GDOWN_AVAILABLE: missing.append("gdown")
if not SUPABASE_AVAILABLE: missing.append("supabase")
if not EDGE_TTS_AVAILABLE: missing.append("edge-tts")

if missing:
    st.warning(f"⚠️ Missing: {', '.join(missing)}. Add to requirements.txt.")

# --- TOP CONTROL BAR ---
with st.container(border=True):
    col_api, col_vision, col_writer = st.columns([2, 1, 1])
    
    with col_api:
        api_key = st.text_input("🔑 Google API Key", type="password", placeholder="Paste API key...", label_visibility="collapsed")
    
    with col_vision:
        vision_model_name = st.selectbox("Vision", [
            "models/gemini-2.5-flash",
            "models/gemini-2.5-pro",
            "gemini-1.5-flash",
            "gemini-2.0-flash-exp",
        ], label_visibility="collapsed")
    
    with col_writer:
        writer_model_name = st.selectbox("Writer", [
            "gemini-1.5-flash",
            "gemini-2.0-flash-exp",
            "models/gemini-2.5-flash",
            "models/gemini-2.5-pro",
        ], label_visibility="collapsed")
    
    if api_key:
        try:
            genai.configure(api_key=api_key)
        except:
            pass

# --- TABS ---
st.write("")
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🎬 Movie Recap", 
    "🌍 Translator", 
    "🎨 Thumbnail", 
    "✍️ Rewriter", 
    "📰 AI News",
    "📝 Note Pad",
    "🔊 TTS"
])

# ==========================================
# TAB 1: MOVIE RECAP
# ==========================================
with tab1:
    col_left, col_right = st.columns([1, 1], gap="medium")

    with col_left:
        with st.container(border=True):
            st.subheader("📂 Add Videos")
            
            upload_method = st.radio("Method:", ["📁 Local Files", "🔗 Google Drive"], horizontal=True)
            st.markdown("---")
            
            if upload_method == "📁 Local Files":
                st.warning("⚠️ Max 200MB per file. Use Google Drive for larger files.")
                
                uploaded_videos = st.file_uploader("Videos", type=["mp4", "mkv", "mov"], accept_multiple_files=True, key="vid_upload")
                
                if st.button("➕ Add to Queue", use_container_width=True, key="add_files"):
                    if uploaded_videos:
                        for video in uploaded_videos[:10 - len(st.session_state['video_queue'])]:
                            video.seek(0, 2)
                            if video.tell() <= 200 * 1024 * 1024:
                                video.seek(0)
                                tmp_path, _ = save_uploaded_file_chunked(video)
                                if tmp_path:
                                    st.session_state['video_queue'].append({
                                        'name': video.name, 'source_type': 'file',
                                        'file_path': tmp_path, 'url': None,
                                        'status': 'waiting', 'script': None, 'error': None
                                    })
                        st.rerun()
            else:
                st.success("✅ Recommended for large files")
                links_input = st.text_area("Links (one per line)", height=150, key="links")
                
                if st.button("➕ Add to Queue", use_container_width=True, key="add_links"):
                    if links_input.strip():
                        for link in links_input.strip().split('\n')[:10 - len(st.session_state['video_queue'])]:
                            if 'drive.google.com' in link and extract_file_id_from_url(link):
                                st.session_state['video_queue'].append({
                                    'name': f"Video_{len(st.session_state['video_queue'])+1}",
                                    'source_type': 'url', 'file_path': None, 'url': link.strip(),
                                    'status': 'waiting', 'script': None, 'error': None
                                })
                        st.rerun()
            
            st.markdown("---")
            st.caption(f"🔬 Vision: {vision_model_name.split('/')[-1]} | ✍️ Writer: {writer_model_name.split('/')[-1]}")
            
            with st.expander("📝 Custom Instructions"):
                custom_prompt = st.text_area("Instructions:", value=st.session_state.get('custom_prompt', ''), height=80, key="custom")
                st.session_state['custom_prompt'] = custom_prompt
            
            style_file = st.file_uploader("📄 Style Reference", type=["txt", "pdf", "docx"], key="style")
            if style_file:
                content = read_file_content(style_file)
                if content:
                    st.session_state['style_text'] = f"\n**STYLE:**\n{content[:5000]}\n"
            
            st.markdown("---")
            col_start, col_clear = st.columns(2)
            
            with col_start:
                if st.button("🚀 Start", use_container_width=True, disabled=not st.session_state['video_queue'] or st.session_state['processing_active']):
                    if api_key:
                        st.session_state['processing_active'] = True
                        st.session_state['current_index'] = 0
                        st.rerun()
            
            with col_clear:
                if st.button("🗑️ Clear", use_container_width=True, disabled=not st.session_state['video_queue']):
                    for item in st.session_state['video_queue']:
                        cleanup_temp_file(item.get('file_path'))
                    st.session_state['video_queue'] = []
                    st.session_state['processing_active'] = False
                    st.rerun()

    with col_right:
        with st.container(border=True):
            st.subheader("📋 Queue")
            
            if not st.session_state['video_queue']:
                st.info("Add videos to start")
            else:
                total = len(st.session_state['video_queue'])
                completed = sum(1 for v in st.session_state['video_queue'] if v['status'] == 'completed')
                
                st.progress(completed / total if total else 0)
                st.caption(f"✅ {completed}/{total} completed")
                
                for idx, item in enumerate(st.session_state['video_queue']):
                    emoji = {'waiting': '⏳', 'processing': '🔄', 'completed': '✅', 'failed': '❌'}[item['status']]
                    st.markdown(f"**{emoji} {idx+1}. {item['name']}** - {item['status'].upper()}")
                    
                    if item['status'] == 'completed' and item['script']:
                        st.download_button(f"📥 Download #{idx+1}", item['script'], f"{item['name']}_recap.txt", key=f"dl_{idx}")
                    if item['status'] == 'failed' and item['error']:
                        st.error(item['error'][:200])
        
        if st.session_state['processing_active']:
            idx = st.session_state['current_index']
            if idx < len(st.session_state['video_queue']):
                item = st.session_state['video_queue'][idx]
                if item['status'] == 'waiting':
                    st.session_state['video_queue'][idx]['status'] = 'processing'
                    
                    with st.container(border=True):
                        st.markdown(f"### 🔄 {item['name']}")
                        status = st.empty()
                        
                        if item['source_type'] == 'file':
                            script, error = process_video_from_path(
                                item['file_path'], item['name'], vision_model_name, writer_model_name,
                                st.session_state.get('style_text', ''), st.session_state.get('custom_prompt', ''), status)
                            cleanup_temp_file(item['file_path'])
                        else:
                            script, error = process_video_from_url(
                                item['url'], item['name'], vision_model_name, writer_model_name,
                                st.session_state.get('style_text', ''), st.session_state.get('custom_prompt', ''), status)
                        
                        if script:
                            st.session_state['video_queue'][idx]['status'] = 'completed'
                            st.session_state['video_queue'][idx]['script'] = script
                            status.success("✅ Done!")
                        else:
                            st.session_state['video_queue'][idx]['status'] = 'failed'
                            st.session_state['video_queue'][idx]['error'] = error
                            status.error(f"❌ {error}")
                        
                        time.sleep(10)
                        st.session_state['current_index'] += 1
                        st.rerun()
            else:
                st.success("🎉 All done!")
                st.balloons()
                st.session_state['processing_active'] = False

# ==========================================
# TAB 2: TRANSLATOR
# ==========================================
with tab2:
    c1, c2 = st.columns([1, 1], gap="medium")
    
    with c1:
        with st.container(border=True):
            st.subheader("📄 Upload")
            uploaded_file = st.file_uploader("File", type=["mp3", "mp4", "txt", "srt"], key="trans_file")
            if st.button("🚀 Translate", use_container_width=True):
                if api_key and uploaded_file:
                    st.session_state['run_translate'] = True

    with c2:
        with st.container(border=True):
            st.subheader("📝 Output")
            if st.session_state.get('run_translate') and uploaded_file:
                try:
                    ext = uploaded_file.name.split('.')[-1].lower()
                    if ext in ['txt', 'srt']:
                        with st.spinner("Translating..."):
                            text = uploaded_file.getvalue().decode("utf-8")
                            model = genai.GenerativeModel(writer_model_name)
                            res, _ = call_gemini_api(model, f"Translate to Burmese:\n{text}")
                            if res:
                                result, _ = get_response_text_safe(res)
                                if result:
                                    st.text_area("Result", result, height=300)
                                    st.download_button("📥 Download", result, f"trans_{uploaded_file.name}")
                    else:
                        with st.spinner("Processing audio..."):
                            tmp_path, _ = save_uploaded_file_chunked(uploaded_file)
                            if tmp_path:
                                gemini_file = upload_to_gemini(tmp_path)
                                if gemini_file:
                                    model = genai.GenerativeModel(writer_model_name)
                                    res, _ = call_gemini_api(model, [gemini_file, "Transcribe to Burmese"], timeout=600)
                                    if res:
                                        result, _ = get_response_text_safe(res)
                                        if result:
                                            st.text_area("Result", result, height=300)
                                            st.download_button("📥 Download", result, f"{uploaded_file.name}_trans.txt")
                                    try:
                                        genai.delete_file(gemini_file.name)
                                    except:
                                        pass
                                cleanup_temp_file(tmp_path)
                except Exception as e:
                    st.error(str(e))
                st.session_state['run_translate'] = False
            else:
                st.info("Upload a file and click Translate")

# ==========================================
# TAB 3: THUMBNAIL
# ==========================================
with tab3:
    col_l, col_r = st.columns([1, 1], gap="medium")
    
    with col_l:
        with st.container(border=True):
            st.subheader("🎨 Generator")
            
            ref_image = st.file_uploader("Reference Image", type=["png", "jpg", "jpeg"], key="thumb_ref")
            if ref_image:
                st.image(ref_image, width=150)
            
            templates = {
                "Custom": "",
                "Movie Recap": "dramatic YouTube thumbnail, 1280x720, cinematic, emotional, bold text",
                "Shocking": "YouTube thumbnail, shocked expression, red/yellow colors, bold text, 1280x720",
            }
            
            template = st.selectbox("Template", list(templates.keys()))
            prompt = st.text_area("Prompt", value=templates[template], height=100, key="thumb_prompt")
            
            add_text = st.text_input("Text overlay", placeholder="EP.1, PART 2", key="thumb_text")
            num_images = st.selectbox("Count", [1, 2, 3, 4], key="thumb_num")
            
            generate = st.button("🚀 Generate", use_container_width=True)
    
    with col_r:
        with st.container(border=True):
            st.subheader("🖼️ Results")
            
            if generate and api_key and prompt:
                st.session_state['generated_images'] = []
                final_prompt = prompt + (f", text: '{add_text}'" if add_text else "") + ", high quality"
                
                try:
                    model = genai.GenerativeModel("models/gemini-3-pro-image-preview")
                    
                    for i in range(num_images):
                        st.info(f"Generating {i+1}/{num_images}...")
                        
                        if ref_image:
                            ref_image.seek(0)
                            img = Image.open(ref_image)
                            response = model.generate_content([f"Generate: {final_prompt}", img], request_options={"timeout": 180})
                        else:
                            response = model.generate_content(f"Generate: {final_prompt}", request_options={"timeout": 180})
                        
                        if response.candidates:
                            for part in response.candidates[0].content.parts:
                                if hasattr(part, 'inline_data') and part.inline_data:
                                    st.session_state['generated_images'].append({
                                        'data': part.inline_data.data,
                                        'mime': part.inline_data.mime_type,
                                        'idx': i + 1
                                    })
                                    break
                        time.sleep(2)
                    
                    st.success(f"Generated {len(st.session_state['generated_images'])} images")
                except Exception as e:
                    st.error(str(e))
            
            for img in st.session_state.get('generated_images', []):
                st.image(img['data'], use_container_width=True)
                st.download_button(f"📥 Download {img['idx']}", img['data'], f"thumb_{img['idx']}.png", key=f"dl_img_{img['idx']}_{time.time()}")

# ==========================================
# TAB 4: REWRITER
# ==========================================
with tab4:
    c1, c2 = st.columns([1, 1], gap="medium")
    
    with c1:
        with st.container(border=True):
            st.subheader("✍️ Input")
            style_file = st.file_uploader("Style Reference", type=["txt", "pdf", "docx"], key="rewrite_style")
            original = st.text_area("Original Script", height=300, key="original_script")
            rewrite = st.button("✨ Rewrite", use_container_width=True)

    with c2:
        with st.container(border=True):
            st.subheader("📝 Output")
            if rewrite and api_key and original:
                try:
                    style = read_file_content(style_file) if style_file else "Professional tone"
                    
                    with st.spinner("Rewriting..."):
                        model = genai.GenerativeModel(writer_model_name)
                        prompt = f"""Rewrite in TARGET STYLE. Keep all details. Output: Burmese.
                        
**STYLE:** {style[:5000]}

**ORIGINAL:** {original}"""
                        
                        res, error = call_gemini_api(model, prompt)
                        if res:
                            text, _ = get_response_text_safe(res)
                            if text:
                                st.text_area("Result", text, height=400)
                                st.download_button("📥 Download", text, "rewritten.txt")
                        else:
                            st.error(error)
                except Exception as e:
                    st.error(str(e))
            else:
                st.info("Paste script and click Rewrite")

# ==========================================
# TAB 5: AI NEWS
# ==========================================
with tab5:
    with st.container(border=True):
        st.subheader("📰 AI News")
        
        if st.button("🔄 Refresh", use_container_width=True):
            if api_key:
                with st.spinner("Fetching..."):
                    try:
                        model = genai.GenerativeModel(writer_model_name)
                        prompt = """Latest AI news about: OpenAI, Google Gemini, Anthropic Claude, Meta Llama, Microsoft Copilot, Stability AI, Midjourney.
                        
For each: product updates, new features, pricing changes. Be concise."""
                        
                        res, _ = call_gemini_api(model, prompt, timeout=120)
                        if res:
                            text, _ = get_response_text_safe(res)
                            if text:
                                st.session_state['ai_news_cache'] = text
                                st.session_state['ai_news_timestamp'] = time.strftime("%Y-%m-%d %H:%M")
                    except Exception as e:
                        st.error(str(e))
        
        if st.session_state.get('ai_news_timestamp'):
            st.caption(f"Updated: {st.session_state['ai_news_timestamp']}")
        
        if st.session_state.get('ai_news_cache'):
            st.markdown(st.session_state['ai_news_cache'])
        else:
            st.info("Click Refresh to fetch latest AI news")

# ==========================================
# TAB 6: NOTE PAD (SUPABASE)
# ==========================================
with tab6:
    with st.container(border=True):
        st.subheader("📝 Note Pad")
        
        if not api_key:
            st.warning("🔐 API Key ထည့်မှ Notes သုံးလို့ရမယ်")
            st.info("သင့် API Key က သင့် Notes တွေကို access လုပ်ဖို့ password အနေနဲ့ အလုပ်လုပ်ပါတယ်။")
        elif not SUPABASE_AVAILABLE:
            st.error("❌ Supabase not available. Add 'supabase' to requirements.txt")
        else:
            user_hash = get_user_hash(api_key)
            
            col_list, col_edit = st.columns([1, 2], gap="medium")
            
            with col_list:
                st.markdown("**📋 My Notes**")
                
                # Create new note button
                if st.button("➕ New Note", use_container_width=True):
                    new_note = create_note(user_hash, "Untitled Note", "")
                    if new_note:
                        st.session_state['current_note_id'] = new_note['id']
                        st.rerun()
                
                st.markdown("---")
                
                # List notes
                notes = get_notes(user_hash)
                
                if not notes:
                    st.info("No notes yet. Create one!")
                else:
                    for note in notes:
                        col_note, col_del = st.columns([4, 1])
                        with col_note:
                            if st.button(f"📄 {note['title'][:30]}", key=f"note_{note['id']}", use_container_width=True):
                                st.session_state['current_note_id'] = note['id']
                                st.rerun()
                        with col_del:
                            if st.button("🗑️", key=f"del_{note['id']}"):
                                delete_note(note['id'])
                                if st.session_state.get('current_note_id') == note['id']:
                                    st.session_state['current_note_id'] = None
                                st.rerun()
            
            with col_edit:
                st.markdown("**✏️ Editor**")
                
                current_id = st.session_state.get('current_note_id')
                
                if current_id:
                    # Find current note
                    current_note = next((n for n in notes if n['id'] == current_id), None)
                    
                    if current_note:
                        # Edit form
                        new_title = st.text_input("Title", value=current_note['title'], key="note_title")
                        new_content = st.text_area("Content", value=current_note['content'] or "", height=400, key="note_content")
                        
                        col_save, col_info = st.columns([1, 2])
                        with col_save:
                            if st.button("💾 Save", use_container_width=True):
                                update_note(current_id, new_title, new_content)
                                st.success("✅ Saved!")
                                time.sleep(1)
                                st.rerun()
                        with col_info:
                            st.caption(f"Last updated: {current_note.get('updated_at', 'N/A')[:19]}")
                    else:
                        st.session_state['current_note_id'] = None
                        st.rerun()
                else:
                    st.info("👈 Select a note or create new one")

# ==========================================
# TAB 7: TEXT-TO-SPEECH (EDGE TTS)
# ==========================================
with tab7:
    with st.container(border=True):
        st.subheader("🔊 Text-to-Speech")
        
        if not EDGE_TTS_AVAILABLE:
            st.error("❌ Edge TTS not available. Add 'edge-tts' to requirements.txt")
        else:
            col_input, col_output = st.columns([1, 1], gap="medium")
            
            with col_input:
                st.markdown("**📝 Input Text**")
                
                # Text input
                tts_text = st.text_area("Enter text to convert:", height=300, placeholder="ဒီမှာ စာသားထည့်ပါ...", key="tts_text")
                
                # Upload text file
                tts_file = st.file_uploader("Or upload text file", type=["txt"], key="tts_file")
                if tts_file:
                    tts_text = tts_file.getvalue().decode("utf-8")
                    st.text_area("File content:", value=tts_text, height=200, disabled=True)
                
                st.markdown("---")
                st.markdown("**⚙️ Settings**")
                
                voices = get_voice_list()
                selected_voice_name = st.selectbox("Voice:", list(voices.keys()), key="tts_voice")
                selected_voice = voices[selected_voice_name]
                
                rate = st.slider("Speed:", min_value=-50, max_value=50, value=0, format="%d%%", key="tts_rate")
                
                st.caption(f"Characters: {len(tts_text)}")
            
            with col_output:
                st.markdown("**🎧 Output**")
                
                if st.button("🔊 Generate Audio", use_container_width=True):
                    if tts_text.strip():
                        with st.spinner("Generating audio..."):
                            audio_path, error = generate_tts(tts_text, selected_voice, rate)
                            
                            if audio_path and os.path.exists(audio_path):
                                st.session_state['tts_audio'] = audio_path
                                st.success("✅ Audio generated!")
                            else:
                                st.error(f"❌ Error: {error}")
                    else:
                        st.warning("Please enter some text")
                
                # Display audio player
                if st.session_state.get('tts_audio') and os.path.exists(st.session_state['tts_audio']):
                    st.markdown("---")
                    st.markdown("**▶️ Preview:**")
                    
                    with open(st.session_state['tts_audio'], 'rb') as f:
                        audio_bytes = f.read()
                    
                    st.audio(audio_bytes, format='audio/mp3')
                    
                    st.download_button(
                        "📥 Download MP3",
                        audio_bytes,
                        file_name="tts_audio.mp3",
                        mime="audio/mp3",
                        use_container_width=True
                    )
                    
                    if st.button("🗑️ Clear Audio", use_container_width=True):
                        cleanup_temp_file(st.session_state['tts_audio'])
                        st.session_state['tts_audio'] = None
                        st.rerun()
                else:
                    st.info("Enter text and click Generate to create audio")
                
                st.markdown("---")
                st.markdown("**💡 Tips:**")
                st.markdown("""
                - 🇲🇲 Myanmar voices အတွက် မြန်မာစာ ရေးပါ
                - 🇺🇸 English voices အတွက် English ရေးပါ
                - Speed: -50% (နှေး) to +50% (မြန်)
                - Free & Unlimited! 🎉
                """)

# --- FOOTER ---
st.markdown("""
<div style='text-align: center; margin-top: 3rem; padding: 1.5rem 0; border-top: 1px solid rgba(0, 255, 100, 0.1);'>
    <p style='color: rgba(0, 255, 100, 0.4) !important; font-size: 0.85rem; font-family: "Share Tech Mono", monospace;'>
        ✨ ULTIMATE AI STUDIO v3.0 • POWERED BY GEMINI + SUPABASE + EDGE TTS
    </p>
</div>
""", unsafe_allow_html=True)
