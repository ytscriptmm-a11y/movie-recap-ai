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

# --- LIBRARY IMPORTS ---
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

# --- SUPABASE CONFIG ---
SUPABASE_URL = "https://ohjvgupjocgsirhwuobf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9oanZndXBqb2Nnc2lyaHd1b2JmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU5MzkwMTgsImV4cCI6MjA4MTUxNTAxOH0.oZxQZ6oksjbmEeA_m8c44dG_z5hHLwtgoJssgK2aogI"

supabase = None
if SUPABASE_AVAILABLE:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except:
        SUPABASE_AVAILABLE = False

# --- PAGE CONFIG ---
st.set_page_config(page_title="AI Studio Pro", page_icon="🎬", layout="wide", initial_sidebar_state="collapsed")

# --- SESSION STATE ---
def init_session_state():
    defaults = {
        'video_queue': [], 'processing_active': False, 'current_index': 0,
        'run_translate': False, 'run_rewrite': False, 'style_text': "",
        'custom_prompt': "", 'generated_images': [], 'notes_list': [],
        'current_note_id': None, 'tts_audio': None, 'editor_script': "",
        'editor_filename': 'script.txt', 'current_tab': 0
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()

# --- BEAUTIFUL DARK MODE CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Myanmar:wght@400;500;600;700&family=Orbitron:wght@400;500;600;700;800&family=Rajdhani:wght@400;500;600;700&display=swap');
    
    :root {
        --primary: #00f0ff;
        --secondary: #ff00e4;
        --accent: #00ff88;
        --bg-dark: #0a0a0f;
        --bg-card: #12121a;
        --text: #e0e0e0;
        --text-dim: #888;
    }
    
    .stApp {
        background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0a0a0f 100%) !important;
        font-family: 'Noto Sans Myanmar', 'Rajdhani', sans-serif;
    }
    
    /* Hide default elements */
    header, #MainMenu, footer { visibility: hidden; }
    
    /* Force 1500px max width */
    .main .block-container { 
        max-width: 1500px !important; 
        padding: 1.5rem 2rem !important;
        margin: 0 auto !important;
    }
    section.main > div { max-width: 1500px !important; }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #1a1a2e; }
    ::-webkit-scrollbar-thumb { background: linear-gradient(180deg, var(--primary), var(--secondary)); border-radius: 10px; }
    
    /* Cards/Containers */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        background: linear-gradient(145deg, rgba(18, 18, 26, 0.95), rgba(26, 26, 46, 0.9)) !important;
        backdrop-filter: blur(20px);
        border: 1px solid rgba(0, 240, 255, 0.15) !important;
        border-radius: 20px !important;
        box-shadow: 
            0 8px 32px rgba(0, 0, 0, 0.4),
            0 0 0 1px rgba(0, 240, 255, 0.05),
            inset 0 1px 0 rgba(255, 255, 255, 0.05);
        padding: 1.5rem;
    }
    
    /* Input fields */
    .stTextInput input, .stTextArea textarea {
        background: rgba(10, 10, 20, 0.8) !important;
        color: #e0e0e0 !important;
        border: 1px solid rgba(0, 240, 255, 0.2) !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        font-family: 'Noto Sans Myanmar', sans-serif !important;
        font-size: 14px !important;
        transition: all 0.3s ease;
    }
    
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 20px rgba(0, 240, 255, 0.2), 0 0 0 2px rgba(0, 240, 255, 0.1) !important;
    }
    
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {
        color: rgba(255, 255, 255, 0.3) !important;
    }
    
    /* Select boxes */
    .stSelectbox div[data-baseweb="select"] > div {
        background: rgba(10, 10, 20, 0.8) !important;
        border: 1px solid rgba(0, 240, 255, 0.2) !important;
        border-radius: 12px !important;
        color: #e0e0e0 !important;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, rgba(0, 240, 255, 0.9), rgba(0, 200, 255, 0.7)) !important;
        color: #000 !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.6rem 1.2rem !important;
        font-weight: 600 !important;
        font-family: 'Noto Sans Myanmar', 'Rajdhani', sans-serif !important;
        font-size: 14px !important;
        letter-spacing: 0.5px;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(0, 240, 255, 0.3), 0 0 30px rgba(0, 240, 255, 0.1);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 25px rgba(0, 240, 255, 0.5), 0 0 40px rgba(0, 240, 255, 0.2) !important;
        background: linear-gradient(135deg, rgba(0, 255, 255, 1), rgba(0, 220, 255, 0.9)) !important;
    }
    
    .stDownloadButton > button {
        background: linear-gradient(135deg, rgba(255, 0, 228, 0.9), rgba(200, 0, 180, 0.7)) !important;
        box-shadow: 0 4px 15px rgba(255, 0, 228, 0.3) !important;
    }
    
    .stDownloadButton > button:hover {
        box-shadow: 0 6px 25px rgba(255, 0, 228, 0.5) !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: rgba(10, 10, 20, 0.6);
        padding: 8px 10px;
        border-radius: 16px;
        border: 1px solid rgba(0, 240, 255, 0.1);
        flex-wrap: wrap;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 12px;
        color: rgba(255, 255, 255, 0.6);
        padding: 10px 18px;
        font-weight: 500;
        font-size: 13px;
        font-family: 'Noto Sans Myanmar', sans-serif;
        transition: all 0.3s ease;
        border: 1px solid transparent;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        color: var(--primary);
        background: rgba(0, 240, 255, 0.1);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--primary), rgba(0, 200, 255, 0.8)) !important;
        color: #000 !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 20px rgba(0, 240, 255, 0.4);
    }
    
    /* Typography */
    h1, h2, h3 {
        font-family: 'Orbitron', 'Noto Sans Myanmar', sans-serif !important;
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    h1 { font-size: 2rem !important; font-weight: 700 !important; }
    h2 { font-size: 1.3rem !important; font-weight: 600 !important; }
    h3 { font-size: 1.1rem !important; font-weight: 500 !important; }
    
    p, label, .stMarkdown, span {
        color: rgba(255, 255, 255, 0.85) !important;
        font-family: 'Noto Sans Myanmar', sans-serif !important;
    }
    
    /* File uploader */
    [data-testid="stFileUploader"] {
        background: rgba(10, 10, 20, 0.5);
        border-radius: 16px;
        padding: 16px;
        border: 2px dashed rgba(0, 240, 255, 0.3) !important;
    }
    
    [data-testid="stFileUploader"]:hover {
        border-color: var(--primary) !important;
        box-shadow: 0 0 30px rgba(0, 240, 255, 0.1);
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        font-family: 'Orbitron', monospace !important;
        font-size: 1.8rem !important;
        background: linear-gradient(135deg, var(--primary), var(--accent));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    [data-testid="stMetricLabel"] {
        color: rgba(255, 255, 255, 0.5) !important;
        font-size: 0.85rem !important;
    }
    
    /* Progress bar */
    .stProgress > div > div {
        background: linear-gradient(90deg, var(--primary), var(--secondary), var(--primary)) !important;
        background-size: 200% 100%;
        animation: shimmer 2s linear infinite;
        border-radius: 10px;
    }
    
    @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }
    
    /* Alerts */
    .stAlert {
        border-radius: 12px !important;
        border: none !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(10, 10, 20, 0.5) !important;
        border-radius: 12px !important;
        color: var(--primary) !important;
        font-family: 'Noto Sans Myanmar', sans-serif !important;
    }
    
    /* Custom title */
    .main-title {
        text-align: center;
        padding: 1rem 0 1.5rem 0;
    }
    
    .main-title h1 {
        font-family: 'Orbitron', sans-serif !important;
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        background: linear-gradient(135deg, #00f0ff 0%, #ff00e4 50%, #00ff88 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: none;
        animation: glow 3s ease-in-out infinite;
    }
    
    @keyframes glow {
        0%, 100% { filter: drop-shadow(0 0 20px rgba(0, 240, 255, 0.5)); }
        50% { filter: drop-shadow(0 0 40px rgba(255, 0, 228, 0.5)); }
    }
    
    .main-title p {
        color: rgba(255, 255, 255, 0.4) !important;
        font-family: 'Rajdhani', sans-serif;
        font-size: 0.9rem;
        letter-spacing: 3px;
        text-transform: uppercase;
    }
    
    /* Divider */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(0, 240, 255, 0.3), rgba(255, 0, 228, 0.3), transparent);
        margin: 1.5rem 0;
    }
    
    /* Radio buttons */
    .stRadio > div {
        background: rgba(10, 10, 20, 0.3);
        padding: 8px 12px;
        border-radius: 12px;
    }
    
    .stRadio label {
        color: rgba(255, 255, 255, 0.8) !important;
    }
    
    /* Slider */
    .stSlider > div > div > div {
        background: var(--primary) !important;
    }
    
    /* Caption */
    .stCaption {
        color: rgba(255, 255, 255, 0.4) !important;
        font-size: 0.8rem !important;
    }
</style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def get_user_hash(api_key):
    return hashlib.sha256(api_key.encode()).hexdigest()[:32]

def force_memory_cleanup():
    gc.collect()

# --- SUPABASE FUNCTIONS ---
def get_notes(user_hash):
    if not SUPABASE_AVAILABLE or not supabase: return []
    try:
        return supabase.table('notes').select('*').eq('user_hash', user_hash).order('updated_at', desc=True).execute().data or []
    except: return []

def create_note(user_hash, title, content):
    if not SUPABASE_AVAILABLE or not supabase: return None
    try:
        return supabase.table('notes').insert({'user_hash': user_hash, 'title': title, 'content': content}).execute().data[0]
    except: return None

def update_note(note_id, title, content):
    if not SUPABASE_AVAILABLE or not supabase: return None
    try:
        return supabase.table('notes').update({'title': title, 'content': content, 'updated_at': 'now()'}).eq('id', note_id).execute()
    except: return None

def delete_note(note_id):
    if not SUPABASE_AVAILABLE or not supabase: return False
    try:
        supabase.table('notes').delete().eq('id', note_id).execute()
        return True
    except: return False

# --- TTS FUNCTIONS ---
def get_voice_list():
    return {
        "🇲🇲 မြန်မာ (သီဟ)": "my-MM-ThihaNeural",
        "🇲🇲 မြန်မာ (နီလာ)": "my-MM-NilarNeural",
        "🇺🇸 အင်္ဂလိပ် US (Jenny)": "en-US-JennyNeural",
        "🇺🇸 အင်္ဂလိပ် US (Guy)": "en-US-GuyNeural",
        "🇬🇧 အင်္ဂလိပ် UK (Sonia)": "en-GB-SoniaNeural",
        "🇹🇭 ထိုင်း (Premwadee)": "th-TH-PremwadeeNeural",
        "🇨🇳 တရုတ် (Xiaoxiao)": "zh-CN-XiaoxiaoNeural",
        "🇯🇵 ဂျပန် (Nanami)": "ja-JP-NanamiNeural",
        "🇰🇷 ကိုရီးယား (SunHi)": "ko-KR-SunHiNeural",
    }

async def generate_tts_async(text, voice, rate, output_path):
    rate_str = f"+{rate}%" if rate >= 0 else f"{rate}%"
    communicate = edge_tts.Communicate(text, voice, rate=rate_str)
    await communicate.save(output_path)

def generate_tts(text, voice, rate=0):
    if not EDGE_TTS_AVAILABLE: return None, "Edge TTS မရရှိနိုင်ပါ"
    try:
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
        asyncio.run(generate_tts_async(text, voice, rate, output_path))
        return output_path, None
    except Exception as e: return None, str(e)

# --- VIDEO FUNCTIONS ---
def extract_file_id_from_url(url):
    try:
        if 'drive.google.com' in url:
            if '/file/d/' in url: return url.split('/file/d/')[1].split('/')[0].split('?')[0]
            elif 'id=' in url: return url.split('id=')[1].split('&')[0]
        return None
    except: return None

def download_video_from_url(url, progress_placeholder=None):
    try:
        file_id = extract_file_id_from_url(url)
        if not file_id: return None, "URL မမှန်ကန်ပါ"
        if progress_placeholder: progress_placeholder.info("📥 ဒေါင်းလုဒ်လုပ်နေသည်...")
        
        tmp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        gdrive_url = f"https://drive.google.com/uc?id={file_id}"
        
        if GDOWN_AVAILABLE:
            if gdown.download(gdrive_url, tmp_path, quiet=False, fuzzy=True):
                if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 1000:
                    if progress_placeholder: progress_placeholder.success(f"✅ ပြီးပါပြီ: {os.path.getsize(tmp_path)/(1024*1024):.1f} MB")
                    return tmp_path, None
        return None, "ဒေါင်းလုဒ်မအောင်မြင်ပါ"
    except Exception as e: return None, str(e)

def save_uploaded_file_chunked(uploaded_file, progress_placeholder=None):
    try:
        ext = uploaded_file.name.split('.')[-1] if '.' in uploaded_file.name else 'mp4'
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
        
        uploaded_file.seek(0, 2)
        file_size = uploaded_file.tell()
        uploaded_file.seek(0)
        
        if progress_placeholder: progress_placeholder.info(f"💾 သိမ်းနေသည် ({file_size/(1024*1024):.1f} MB)...")
        
        chunk_size = 10 * 1024 * 1024
        written = 0
        progress = st.progress(0)
        
        while chunk := uploaded_file.read(chunk_size):
            tmp_file.write(chunk)
            written += len(chunk)
            progress.progress(min(written / file_size, 1.0))
        
        tmp_file.close()
        progress.empty()
        if progress_placeholder: progress_placeholder.success(f"✅ သိမ်းပြီး: {written/(1024*1024):.1f} MB")
        return tmp_file.name, None
    except Exception as e: return None, str(e)

def upload_to_gemini(file_path, progress_placeholder=None):
    try:
        if progress_placeholder:
            progress_placeholder.info(f"📤 Gemini သို့ တင်နေသည် ({os.path.getsize(file_path)/(1024*1024):.1f} MB)...")
        
        file = genai.upload_file(file_path)
        wait = 0
        while file.state.name == "PROCESSING":
            wait += 1
            if progress_placeholder: progress_placeholder.info(f"⏳ စီမံနေသည်... ({wait*2} စက္ကန့်)")
            time.sleep(2)
            file = genai.get_file(file.name)
            if wait > 300: return None
        
        if file.state.name == "FAILED": return None
        if progress_placeholder: progress_placeholder.success("✅ တင်ပြီးပါပြီ!")
        return file
    except Exception as e:
        if progress_placeholder: progress_placeholder.error(f"❌ {e}")
        return None

def read_file_content(uploaded_file):
    try:
        ft = uploaded_file.type
        if ft == "text/plain": return uploaded_file.getvalue().decode("utf-8")
        elif ft == "application/pdf" and PDF_AVAILABLE:
            return "\n".join([p.extract_text() or "" for p in PyPDF2.PdfReader(io.BytesIO(uploaded_file.getvalue())).pages])
        elif "wordprocessingml" in ft and DOCX_AVAILABLE:
            return "\n".join([p.text for p in Document(io.BytesIO(uploaded_file.getvalue())).paragraphs])
        return None
    except: return None

def cleanup_temp_file(fp):
    if fp and os.path.exists(fp):
        try: os.remove(fp)
        except: pass

def get_response_text_safe(response):
    try:
        if not response or not response.candidates: return None, "တုံ့ပြန်မှုမရှိပါ"
        parts = response.candidates[0].content.parts if hasattr(response.candidates[0], 'content') else []
        text = "\n".join([p.text for p in parts if hasattr(p, 'text') and p.text])
        return (text, None) if text else (None, "စာသားမရှိပါ")
    except Exception as e: return None, str(e)

def call_gemini_api(model, content, timeout=600):
    for attempt in range(3):
        try:
            response = model.generate_content(content, request_options={"timeout": timeout})
            text, err = get_response_text_safe(response)
            if text: return response, None
            if attempt < 2: time.sleep(10)
        except Exception as e:
            if any(x in str(e).lower() for x in ['rate', 'quota', '429']):
                if attempt < 2:
                    st.warning(f"⏳ ခဏစောင့်ပါ {10*(2**attempt)} စက္ကန့်...")
                    time.sleep(10 * (2 ** attempt))
                else: return None, "Rate limit ကျော်သွားပါပြီ"
            else: return None, str(e)
    return None, "အကြိမ်အရေအတွက်ပြည့်သွားပါပြီ"

def process_video(file_path, video_name, vision_model, writer_model, style="", custom="", status=None):
    gemini_file = None
    try:
        if status: status.info("📤 အဆင့် ၁/၃: တင်နေသည်...")
        gemini_file = upload_to_gemini(file_path, status)
        if not gemini_file: return None, "တင်၍မရပါ"
        
        if status: status.info("👀 အဆင့် ၂/၃: ခွဲခြမ်းစိတ်ဖြာနေသည်...")
        vision = genai.GenerativeModel(vision_model)
        resp, err = call_gemini_api(vision, [gemini_file, "Watch this video carefully. 
        Generate a highly detailed, chronological scene-by-scene description. (Use a storytelling tone.)
        Include All the dialogue in the movie, visual details, emotions, and actions. (Use a storytelling tone.)
        No creative writing yet, just facts.
        """"], 600)
        if err: return None, f"ခွဲခြမ်းစိတ်ဖြာ မအောင်မြင်ပါ: {err}"
        desc, _ = get_response_text_safe(resp)
        
        time.sleep(5)
        
        if status: status.info("✍️ အဆင့် ၃/၃: Script ရေးနေသည်...")
        writer = genai.GenerativeModel(writer_model)
        prompt = f"""
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
        5. Scene-by-scene.(Use a storytelling tone.) 
        6. Full narration.                         
        """
        resp, err = call_gemini_api(writer, prompt, 600)
        if err: return None, f"ရေးသား မအောင်မြင်ပါ: {err}"
        
        text, _ = get_response_text_safe(resp)
        return text, None
    except Exception as e: return None, str(e)
    finally:
        if gemini_file:
            try: genai.delete_file(gemini_file.name)
            except: pass
        force_memory_cleanup()

# --- MAIN TITLE ---
st.markdown("""
<div class="main-title">
    <h1>AI STUDIO PRO</h1>
    <p>// သင့်အတွက် AI လက်ထောက် //</p>
</div>
""", unsafe_allow_html=True)

# --- API KEY (TOP) ---
with st.container(border=True):
    api_key = st.text_input("🔑 Google API Key ထည့်ပါ", type="password", placeholder="API Key ကို ဒီမှာထည့်ပါ...", label_visibility="collapsed")
    if api_key:
        try: genai.configure(api_key=api_key)
        except: pass

# --- LIBRARY STATUS ---
missing = [x for x, v in [("PyPDF2", PDF_AVAILABLE), ("python-docx", DOCX_AVAILABLE), ("gdown", GDOWN_AVAILABLE), ("supabase", SUPABASE_AVAILABLE), ("edge-tts", EDGE_TTS_AVAILABLE)] if not v]
if missing: st.warning(f"⚠️ လိုအပ်သော libraries: {', '.join(missing)}")

# --- TABS (Myanmar names) ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🎬 ရီကပ်", 
    "🌍 ဘာသာပြန်", 
    "🎨 Thumbnail", 
    "✍️ ပြန်ရေး", 
    "📝 မှတ်စု", 
    "🔊 အသံ", 
    "📝 တည်းဖြတ်"
])

# === TAB 1: MOVIE RECAP ===
with tab1:
    st.markdown("### 🎬 ဗီဒီယို ရီကပ် Script ဖန်တီးရန်")
    
    c1, c2 = st.columns([1, 1], gap="medium")
    
    with c1:
        with st.container(border=True):
            st.markdown("#### 📂 ဗီဒီယိုထည့်ရန်")
            
            # MODEL SELECTION - Only visible in this tab
            st.markdown("**🤖 AI Model ရွေးချယ်ရန်**")
            model_col1, model_col2 = st.columns(2)
            with model_col1:
                vision_model = st.selectbox(
                    "Vision Model",
                    ["models/gemini-2.5-flash", "models/gemini-2.5-pro", "models/gemini-3-pro-preview", "gemini-1.5-flash"],
                    key="vision_model",
                    help="ဗီဒီယို ခွဲခြမ်းစိတ်ဖြာရန်"
                )
            with model_col2:
                writer_model = st.selectbox(
                    "Writer Model", 
                    ["gemini-1.5-flash", "gemini-2.0-flash-exp", "models/gemini-2.5-flash", "models/gemini-2.5-pro"],
                    key="writer_model",
                    help="Script ရေးသားရန်"
                )
            
            st.markdown("---")
            
            method = st.radio("📥 ထည့်သွင်းနည်း:", ["📁 ဖိုင်တင်ရန်", "🔗 Google Drive Link"], horizontal=True)
            
            if method == "📁 ဖိုင်တင်ရန်":
                st.warning("⚠️ အများဆုံး 200MB။ ပိုကြီးရင် Google Drive သုံးပါ။")
                vids = st.file_uploader("ဗီဒီယိုဖိုင်များ", type=["mp4", "mkv", "mov"], accept_multiple_files=True, key="vids")
                if st.button("➕ Queue သို့ထည့်ရန်", key="add_local", use_container_width=True):
                    for v in (vids or [])[:10-len(st.session_state['video_queue'])]:
                        v.seek(0, 2)
                        if v.tell() <= 200*1024*1024:
                            v.seek(0)
                            path, _ = save_uploaded_file_chunked(v)
                            if path:
                                st.session_state['video_queue'].append({'name': v.name, 'type': 'file', 'path': path, 'url': None, 'status': 'waiting', 'script': None, 'error': None})
                    st.rerun()
            else:
                st.success("✅ ဖိုင်ကြီးများအတွက် အကြံပြုသည်")
                links = st.text_area("Link များ (တစ်ကြောင်းလျှင် တစ်ခု)", height=100, key="links", placeholder="https://drive.google.com/file/d/...")
                if st.button("➕ Queue သို့ထည့်ရန်", key="add_links", use_container_width=True):
                    for link in (links.strip().split('\n') if links else [])[:10-len(st.session_state['video_queue'])]:
                        if 'drive.google.com' in link and extract_file_id_from_url(link.strip()):
                            st.session_state['video_queue'].append({'name': f"ဗီဒီယို_{len(st.session_state['video_queue'])+1}", 'type': 'url', 'path': None, 'url': link.strip(), 'status': 'waiting', 'script': None, 'error': None})
                    st.rerun()
            
            st.markdown("---")
            
            with st.expander("📝 ညွှန်ကြားချက် (ရွေးချယ်နိုင်သည်)"):
                st.session_state['custom_prompt'] = st.text_area("သင့်ညွှန်ကြားချက်:", st.session_state.get('custom_prompt', ''), height=60, key="custom_instr", placeholder="ဥပမာ: အချစ်ဇာတ်ကြောင်းကို အဓိကထား...")
            
            style_file = st.file_uploader("📄 ရေးဟန် နမူနာ (ရွေးချယ်နိုင်သည်)", type=["txt", "pdf", "docx"], key="style_ref")
            if style_file and (content := read_file_content(style_file)):
                st.session_state['style_text'] = f"\n**STYLE:**\n{content[:5000]}\n"
            
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚀 စတင်ရန်", disabled=not st.session_state['video_queue'] or st.session_state['processing_active'], use_container_width=True):
                    if api_key:
                        st.session_state['processing_active'] = True
                        st.session_state['current_index'] = 0
                        st.rerun()
                    else:
                        st.error("API Key ထည့်ပါ")
            with col2:
                if st.button("🗑️ ရှင်းလင်းရန်", disabled=not st.session_state['video_queue'], use_container_width=True):
                    for i in st.session_state['video_queue']: cleanup_temp_file(i.get('path'))
                    st.session_state['video_queue'] = []
                    st.session_state['processing_active'] = False
                    st.rerun()
    
    with c2:
        with st.container(border=True):
            st.markdown("#### 📋 စီမံခန့်ခွဲမှု Queue")
            if not st.session_state['video_queue']:
                st.info("💡 ဗီဒီယိုများထည့်ပါ")
            else:
                total = len(st.session_state['video_queue'])
                done = sum(1 for v in st.session_state['video_queue'] if v['status'] == 'completed')
                st.progress(done/total if total else 0)
                st.caption(f"✅ {done}/{total} ပြီးစီးပြီ")
                
                for i, item in enumerate(st.session_state['video_queue']):
                    emoji = {'waiting': '⏳', 'processing': '🔄', 'completed': '✅', 'failed': '❌'}[item['status']]
                    st.markdown(f"**{emoji} {i+1}. {item['name']}**")
                    if item['status'] == 'completed' and item['script']:
                        st.download_button(f"📥 ဒေါင်းလုဒ် #{i+1}", item['script'], f"{item['name']}_recap.txt", key=f"dl_{i}")
                    if item['status'] == 'failed': st.error(item['error'][:150] if item['error'] else "Error")
        
        if st.session_state['processing_active']:
            idx = st.session_state['current_index']
            if idx < len(st.session_state['video_queue']):
                item = st.session_state['video_queue'][idx]
                if item['status'] == 'waiting':
                    st.session_state['video_queue'][idx]['status'] = 'processing'
                    with st.container(border=True):
                        st.markdown(f"### 🔄 {item['name']}")
                        status = st.empty()
                        
                        if item['type'] == 'file':
                            script, err = process_video(item['path'], item['name'], vision_model, writer_model, st.session_state.get('style_text', ''), st.session_state.get('custom_prompt', ''), status)
                            cleanup_temp_file(item['path'])
                        else:
                            path, err = download_video_from_url(item['url'], status)
                            if path:
                                script, err = process_video(path, item['name'], vision_model, writer_model, st.session_state.get('style_text', ''), st.session_state.get('custom_prompt', ''), status)
                                cleanup_temp_file(path)
                            else:
                                script = None
                        
                        if script:
                            st.session_state['video_queue'][idx]['status'] = 'completed'
                            st.session_state['video_queue'][idx]['script'] = script
                            status.success("✅ အောင်မြင်ပါပြီ!")
                        else:
                            st.session_state['video_queue'][idx]['status'] = 'failed'
                            st.session_state['video_queue'][idx]['error'] = err
                            status.error(f"❌ {err}")
                        
                        time.sleep(10)
                        st.session_state['current_index'] += 1
                        st.rerun()
            else:
                st.success("🎉 အားလုံးပြီးစီးပါပြီ!")
                st.balloons()
                st.session_state['processing_active'] = False

# === TAB 2: TRANSLATOR ===
with tab2:
    st.markdown("### 🌍 ဘာသာပြန်ဆိုရန်")
    c1, c2 = st.columns([1, 1], gap="medium")
    
    with c1:
        with st.container(border=True):
            st.markdown("#### 📄 ဖိုင်နှင့် ဆက်တင်များ")
            
            languages = {
                "🇲🇲 မြန်မာ": "Burmese", "🇺🇸 အင်္ဂလိပ်": "English", 
                "🇹🇭 ထိုင်း": "Thai", "🇨🇳 တရုတ်": "Chinese",
                "🇯🇵 ဂျပန်": "Japanese", "🇰🇷 ကိုရီးယား": "Korean",
                "🇻🇳 ဗီယက်နမ်": "Vietnamese", "🇮🇳 ဟိန္ဒူ": "Hindi",
                "🇫🇷 ပြင်သစ်": "French", "🇩🇪 ဂျာမန်": "German",
                "🇪🇸 စပိန်": "Spanish",
            }
            target_lang = st.selectbox("🌍 ဘာသာစကား ရွေးချယ်ရန်:", list(languages.keys()), key="trans_lang")
            
            trans_file = st.file_uploader("📁 ဖိုင်ရွေးချယ်ရန်", type=["mp3", "mp4", "txt", "srt", "docx"], key="trans_file")
            trans_style = st.file_uploader("📄 ရေးဟန် နမူနာ (ရွေးချယ်နိုင်သည်)", type=["txt", "pdf", "docx"], key="trans_style")
            
            if st.button("🚀 ဘာသာပြန်ရန်", use_container_width=True):
                if api_key and trans_file:
                    st.session_state['run_translate'] = True
                else:
                    st.error("API Key နှင့် ဖိုင်ထည့်ပါ")
    
    with c2:
        with st.container(border=True):
            st.markdown("#### 📝 ရလဒ်")
            if st.session_state.get('run_translate') and trans_file:
                try:
                    ext = trans_file.name.split('.')[-1].lower()
                    style_text = ""
                    if trans_style and (style_content := read_file_content(trans_style)):
                        style_text = f"\n\n**STYLE REFERENCE:**\n{style_content[:3000]}\n"
                    
                    target = languages[target_lang]
                    
                    if ext in ['txt', 'srt']:
                        with st.spinner("ဘာသာပြန်နေသည်..."):
                            text = trans_file.getvalue().decode("utf-8")
                            model = genai.GenerativeModel("gemini-1.5-flash")
                            prompt = f"Translate to **{target}**. Keep formatting. Return ONLY translated text.{style_text}\n\nInput:\n{text}"
                            res, _ = call_gemini_api(model, prompt)
                            if res:
                                result, _ = get_response_text_safe(res)
                                if result:
                                    st.text_area("ရလဒ်", result, height=300)
                                    st.download_button("📥 ဒေါင်းလုဒ်", result, f"trans_{trans_file.name}")
                    
                    elif ext == 'docx':
                        with st.spinner("စာရွက်စာတမ်း ဘာသာပြန်နေသည်..."):
                            text = read_file_content(trans_file)
                            if text:
                                model = genai.GenerativeModel("gemini-1.5-flash")
                                prompt = f"Translate to **{target}**. Keep formatting. Return ONLY translated text.{style_text}\n\nInput:\n{text}"
                                res, _ = call_gemini_api(model, prompt)
                                if res:
                                    result, _ = get_response_text_safe(res)
                                    if result:
                                        st.text_area("ရလဒ်", result, height=300)
                                        st.download_button("📥 ဒေါင်းလုဒ်", result, f"trans_{trans_file.name}.txt")
                    
                    else:
                        with st.spinner("အသံဖိုင် စီမံနေသည်..."):
                            path, _ = save_uploaded_file_chunked(trans_file)
                            if path:
                                gfile = upload_to_gemini(path)
                                if gfile:
                                    model = genai.GenerativeModel("gemini-1.5-flash")
                                    prompt = f"Transcribe and translate to **{target}**.{style_text}"
                                    res, _ = call_gemini_api(model, [gfile, prompt], 600)
                                    if res:
                                        result, _ = get_response_text_safe(res)
                                        if result:
                                            st.text_area("ရလဒ်", result, height=300)
                                            st.download_button("📥 ဒေါင်းလုဒ်", result, f"{trans_file.name}_trans.txt")
                                    try: genai.delete_file(gfile.name)
                                    except: pass
                                cleanup_temp_file(path)
                except Exception as e:
                    st.error(str(e))
                st.session_state['run_translate'] = False
            else:
                st.info("💡 ဖိုင်တင်ပြီး ဘာသာပြန်ခလုတ်နှိပ်ပါ")

# === TAB 3: THUMBNAIL ===
with tab3:
    st.markdown("### 🎨 Thumbnail ဖန်တီးရန်")
    c1, c2 = st.columns([1, 1], gap="medium")
    
    with c1:
        with st.container(border=True):
            st.markdown("#### 🖼️ ဆက်တင်များ")
            
            ref_images = st.file_uploader("🖼️ နမူနာပုံများ (အများဆုံး ၁၀ပုံ)", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True, key="thumb_refs")
            
            if ref_images:
                cols = st.columns(min(len(ref_images), 5))
                for i, img in enumerate(ref_images[:10]):
                    with cols[i % 5]:
                        st.image(img, width=70)
                st.caption(f"✅ {len(ref_images[:10])} ပုံ ထည့်ပြီး")
            
            templates = {
                "✍️ စိတ်ကြိုက်": "",
                "🎬 ရုပ်ရှင် ရီကပ်": "dramatic YouTube thumbnail, 1280x720, cinematic, emotional, bold Myanmar text",
                "😱 အံ့အားသင့်": "YouTube thumbnail, shocked expression, red/yellow, bold text, 1280x720",
                "📊 နှိုင်းယှဉ်": "split screen comparison, clear dividing line, contrasting colors, 1280x720",
            }
            template = st.selectbox("📋 Template ရွေးရန်", list(templates.keys()))
            prompt = st.text_area("✏️ ညွှန်ကြားချက်", value=templates[template], height=100, key="thumb_prompt", placeholder="သင်လိုချင်တဲ့ပုံကို ဖော်ပြပါ...")
            
            add_text = st.text_input("📝 ပုံပေါ်စာသား", placeholder="ဥပမာ: EP.1, အပိုင်း ၁", key="thumb_txt")
            num_imgs = st.selectbox("🔢 ပုံအရေအတွက်", [1, 2, 3, 4], key="thumb_cnt")
            
            gen = st.button("🚀 ပုံဖန်တီးရန်", use_container_width=True)
    
    with c2:
        with st.container(border=True):
            st.markdown("#### 🖼️ ရလဒ်")
            
            if gen and api_key and prompt:
                st.session_state['generated_images'] = []
                final_prompt = prompt + (f", with text overlay: '{add_text}'" if add_text else "") + ", high quality, professional"
                
                try:
                    # Use correct model for image generation
                    model = genai.GenerativeModel("models/gemini-2.0-flash-exp-image-generation")
                    
                    for i in range(num_imgs):
                        st.info(f"🎨 ပုံ {i+1}/{num_imgs} ဖန်တီးနေသည်...")
                        
                        content = [f"Generate an image: {final_prompt}"]
                        if ref_images:
                            for ref in ref_images[:5]:
                                ref.seek(0)
                                content.append(Image.open(ref))
                        
                        response = model.generate_content(content, request_options={"timeout": 180})
                        
                        if response.candidates:
                            for part in response.candidates[0].content.parts:
                                if hasattr(part, 'inline_data') and part.inline_data:
                                    st.session_state['generated_images'].append({
                                        'data': part.inline_data.data,
                                        'mime': part.inline_data.mime_type,
                                        'idx': i + 1
                                    })
                                    break
                        time.sleep(3)
                    
                    if st.session_state['generated_images']:
                        st.success(f"✅ {len(st.session_state['generated_images'])} ပုံ ဖန်တီးပြီး")
                    else:
                        st.warning("⚠️ ပုံမထွက်ပါ။ ညွှန်ကြားချက်ပြောင်းကြည့်ပါ။")
                except Exception as e:
                    st.error(f"❌ အမှား: {e}")
            
            for img in st.session_state.get('generated_images', []):
                st.image(img['data'], use_container_width=True)
                st.download_button(f"📥 ပုံ {img['idx']} ဒေါင်းလုဒ်", img['data'], f"thumbnail_{img['idx']}.png", key=f"dl_img_{img['idx']}_{time.time()}")

# === TAB 4: REWRITER ===
with tab4:
    st.markdown("### ✍️ Script ပြန်လည်ရေးသားရန်")
    c1, c2 = st.columns([1, 1], gap="medium")
    
    with c1:
        with st.container(border=True):
            st.markdown("#### 📥 ထည့်သွင်းရန်")
            style_file = st.file_uploader("📄 ရေးဟန် နမူနာ", type=["txt", "pdf", "docx"], key="rw_style")
            original = st.text_area("📝 မူရင်း Script", height=250, key="rw_orig", placeholder="ပြန်ရေးချင်တဲ့ script ကို ဒီမှာထည့်ပါ...")
            rewrite = st.button("✨ ပြန်ရေးရန်", use_container_width=True)
    
    with c2:
        with st.container(border=True):
            st.markdown("#### 📝 ရလဒ်")
            if rewrite and api_key and original:
                try:
                    style = read_file_content(style_file) if style_file else "Professional storytelling tone"
                    with st.spinner("ပြန်ရေးနေသည်..."):
                        model = genai.GenerativeModel("gemini-1.5-flash")
                        prompt = f"Rewrite in TARGET STYLE. Keep all details. Output: Burmese.\n\n**STYLE:** {style[:5000]}\n\n**ORIGINAL:** {original}"
                        res, err = call_gemini_api(model, prompt)
                        if res:
                            text, _ = get_response_text_safe(res)
                            if text:
                                st.text_area("ရလဒ်", text, height=350)
                                st.download_button("📥 ဒေါင်းလုဒ်", text, "rewritten.txt")
                        else:
                            st.error(err)
                except Exception as e:
                    st.error(str(e))
            else:
                st.info("💡 Script ထည့်ပြီး ပြန်ရေးခလုတ်နှိပ်ပါ")

# === TAB 5: NOTES ===
with tab5:
    st.markdown("### 📝 မှတ်စုများ")
    
    with st.container(border=True):
        if not api_key:
            st.warning("🔐 API Key ထည့်မှ မှတ်စုသုံးလို့ရမည်")
        elif not SUPABASE_AVAILABLE:
            st.error("❌ Supabase မရနိုင်ပါ")
        else:
            user_hash = get_user_hash(api_key)
            c1, c2 = st.columns([1, 2], gap="medium")
            
            with c1:
                st.markdown("**📋 မှတ်စုစာရင်း**")
                if st.button("➕ မှတ်စုအသစ်", use_container_width=True):
                    note = create_note(user_hash, "ခေါင်းစဉ်မဲ့", "")
                    if note:
                        st.session_state['current_note_id'] = note['id']
                        st.rerun()
                
                st.markdown("---")
                notes = get_notes(user_hash)
                
                if not notes:
                    st.info("မှတ်စုမရှိသေးပါ")
                else:
                    for n in notes:
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            if st.button(f"📄 {n['title'][:20]}", key=f"n_{n['id']}", use_container_width=True):
                                st.session_state['current_note_id'] = n['id']
                                st.rerun()
                        with col2:
                            if st.button("🗑️", key=f"d_{n['id']}"):
                                delete_note(n['id'])
                                if st.session_state.get('current_note_id') == n['id']:
                                    st.session_state['current_note_id'] = None
                                st.rerun()
            
            with c2:
                st.markdown("**✏️ တည်းဖြတ်ရန်**")
                current_id = st.session_state.get('current_note_id')
                
                if current_id:
                    note = next((n for n in notes if n['id'] == current_id), None)
                    if note:
                        title = st.text_input("ခေါင်းစဉ်", note['title'], key="n_title")
                        content = st.text_area("အကြောင်းအရာ", note['content'] or "", height=350, key="n_content")
                        
                        if st.button("💾 သိမ်းရန်", use_container_width=True):
                            update_note(current_id, title, content)
                            st.success("✅ သိမ်းပြီး!")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.session_state['current_note_id'] = None
                        st.rerun()
                else:
                    st.info("👈 မှတ်စုရွေးပါ သို့မဟုတ် အသစ်ဖန်တီးပါ")

# === TAB 6: TTS ===
with tab6:
    st.markdown("### 🔊 စာသားမှ အသံပြောင်းရန်")
    
    with st.container(border=True):
        if not EDGE_TTS_AVAILABLE:
            st.error("❌ Edge TTS မရနိုင်ပါ")
        else:
            c1, c2 = st.columns([1, 1], gap="medium")
            
            with c1:
                st.markdown("**📝 စာသားထည့်ရန်**")
                tts_text = st.text_area("စာသား:", height=250, placeholder="ဒီမှာ စာသားထည့်ပါ...", key="tts_txt")
                
                tts_file = st.file_uploader("သို့မဟုတ် ဖိုင်တင်ရန်", type=["txt"], key="tts_f")
                if tts_file:
                    tts_text = tts_file.getvalue().decode("utf-8")
                
                st.markdown("---")
                voices = get_voice_list()
                voice_name = st.selectbox("🎤 အသံရွေးရန်:", list(voices.keys()), key="tts_v")
                rate = st.slider("⚡ အမြန်နှုန်း:", -50, 50, 0, format="%d%%", key="tts_r")
                st.caption(f"စာလုံးအရေအတွက်: {len(tts_text)}")
            
            with c2:
                st.markdown("**🎧 ရလဒ်**")
                
                if st.button("🔊 အသံဖန်တီးရန်", use_container_width=True):
                    if tts_text.strip():
                        with st.spinner("အသံဖန်တီးနေသည်..."):
                            path, err = generate_tts(tts_text, voices[voice_name], rate)
                            if path and os.path.exists(path):
                                st.session_state['tts_audio'] = path
                                st.success("✅ ဖန်တီးပြီး!")
                            else:
                                st.error(f"❌ {err}")
                
                if st.session_state.get('tts_audio') and os.path.exists(st.session_state['tts_audio']):
                    st.markdown("---")
                    with open(st.session_state['tts_audio'], 'rb') as f:
                        audio = f.read()
                    st.audio(audio, format='audio/mp3')
                    st.download_button("📥 MP3 ဒေါင်းလုဒ်", audio, "audio.mp3", "audio/mp3", use_container_width=True)
                    
                    if st.button("🗑️ ရှင်းလင်းရန်"):
                        cleanup_temp_file(st.session_state['tts_audio'])
                        st.session_state['tts_audio'] = None
                        st.rerun()
                else:
                    st.info("💡 စာသားထည့်ပြီး အသံဖန်တီးခလုတ်နှိပ်ပါ")

# === TAB 7: SCRIPT EDITOR ===
with tab7:
    st.markdown("### 📝 Script တည်းဖြတ်ရန်")
    
    with st.container(border=True):
        # Toolbar
        tool1, tool2, tool3, tool4, tool5 = st.columns([1, 1, 1, 1, 1])
        
        with tool1:
            script_file = st.file_uploader("📂 ဖွင့်ရန်", type=["txt", "docx", "srt", "md"], key="script_open", label_visibility="collapsed")
        with tool2:
            if st.button("📋 အသစ်", use_container_width=True):
                st.session_state['editor_script'] = ""
                st.session_state['editor_filename'] = "script.txt"
                st.rerun()
        with tool3:
            if st.button("🔄 ရှင်းရန်", use_container_width=True):
                st.session_state['editor_script'] = ""
                st.rerun()
        with tool4:
            save_format = st.selectbox("Format", ["txt", "srt", "md"], key="save_fmt", label_visibility="collapsed")
        with tool5:
            if st.session_state.get('editor_script'):
                base = st.session_state.get('editor_filename', 'script').rsplit('.', 1)[0]
                st.download_button("💾 သိမ်းရန်", st.session_state['editor_script'], f"{base}.{save_format}", use_container_width=True)
            else:
                st.button("💾 သိမ်းရန်", disabled=True, use_container_width=True)
        
        st.markdown("---")
        
        if script_file:
            try:
                if script_file.name.endswith(('.txt', '.srt', '.md')):
                    st.session_state['editor_script'] = script_file.getvalue().decode("utf-8")
                elif DOCX_AVAILABLE and "wordprocessingml" in script_file.type:
                    st.session_state['editor_script'] = read_file_content(script_file) or ""
                st.session_state['editor_filename'] = script_file.name
                st.success(f"✅ {script_file.name} ဖွင့်ပြီး")
            except Exception as e:
                st.error(f"အမှား: {e}")
        
        editor_col, info_col = st.columns([3, 1])
        
        with editor_col:
            current = st.session_state.get('editor_script', '')
            new_script = st.text_area("Script", current, height=500, key="editor_main", label_visibility="collapsed", placeholder="ဒီမှာ script ရေးပါ...")
            if new_script != current:
                st.session_state['editor_script'] = new_script
        
        with info_col:
            st.markdown("**📊 စာရင်းအင်း**")
            text = st.session_state.get('editor_script', '')
            
            words = len(text.split()) if text.strip() else 0
            st.metric("စာလုံး", f"{words:,}")
            
            chars = len(text)
            st.metric("အက္ခရာ", f"{chars:,}")
            
            lines = len(text.split('\n')) if text else 0
            st.metric("စာကြောင်း", f"{lines:,}")
            
            st.markdown("---")
            st.markdown("**⏱️ အချိန်ခန့်မှန်း**")
            st.caption(f"ဖတ်ရန်: ~{max(1, words//200)} မိနစ်")
            st.caption(f"ပြောရန်: ~{max(1, words//150)} မိနစ်")
            
            st.markdown("---")
            st.markdown("**🛠️ ကိရိယာများ**")
            
            if st.button("🔠 စာလုံးကြီး", use_container_width=True):
                if st.session_state.get('editor_script'):
                    st.session_state['editor_script'] = st.session_state['editor_script'].upper()
                    st.rerun()
            
            if st.button("🔡 စာလုံးသေး", use_container_width=True):
                if st.session_state.get('editor_script'):
                    st.session_state['editor_script'] = st.session_state['editor_script'].lower()
                    st.rerun()
            
            if st.button("📋 အလွတ်ကြောင်းဖယ်", use_container_width=True):
                if st.session_state.get('editor_script'):
                    lines = st.session_state['editor_script'].split('\n')
                    st.session_state['editor_script'] = '\n'.join([l for l in lines if l.strip()])
                    st.rerun()

# --- FOOTER ---
st.markdown("""
<div style='text-align: center; margin-top: 2rem; padding: 1.5rem; border-top: 1px solid rgba(0, 240, 255, 0.1);'>
    <p style='color: rgba(255, 255, 255, 0.3) !important; font-size: 0.8rem; font-family: "Orbitron", monospace; letter-spacing: 2px;'>
        AI STUDIO PRO v5.0 - POWERED BY GEMINI
    </p>
</div>
""", unsafe_allow_html=True)
