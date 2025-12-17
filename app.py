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
st.set_page_config(page_title="Ultimate AI Studio", page_icon="✨", layout="wide", initial_sidebar_state="collapsed")

# --- SESSION STATE ---
def init_session_state():
    defaults = {
        'video_queue': [], 'processing_active': False, 'current_index': 0,
        'run_translate': False, 'run_rewrite': False, 'style_text': "",
        'custom_prompt': "", 'generated_images': [], 'ai_news_cache': None,
        'ai_news_timestamp': None, 'notes_list': [], 'current_note_id': None,
        'tts_audio': None, 'editor_script': "", 'editor_video_path': None
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()

# --- CSS (1600px width) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');
    
    .matrix-bg {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        z-index: -1; overflow: hidden;
        background: linear-gradient(180deg, #0a0a0f 0%, #0d1117 50%, #0a0f0a 100%);
    }
    
    .matrix-column {
        position: absolute; top: -100%;
        font-family: 'Share Tech Mono', monospace; font-size: 14px;
        color: #0f0; text-shadow: 0 0 8px #0f0;
        animation: matrix-fall linear infinite;
        opacity: 0.7; writing-mode: vertical-rl;
    }
    
    @keyframes matrix-fall {
        0% { transform: translateY(-100%); opacity: 1; }
        100% { transform: translateY(200vh); opacity: 0; }
    }
    
    .matrix-column:nth-child(1) { left: 3%; animation-duration: 8s; }
    .matrix-column:nth-child(2) { left: 8%; animation-duration: 12s; animation-delay: 1s; opacity: 0.5; }
    .matrix-column:nth-child(3) { left: 13%; animation-duration: 9s; animation-delay: 2s; }
    .matrix-column:nth-child(4) { left: 18%; animation-duration: 15s; animation-delay: 0.5s; opacity: 0.4; }
    .matrix-column:nth-child(5) { left: 23%; animation-duration: 10s; animation-delay: 3s; }
    .matrix-column:nth-child(6) { left: 28%; animation-duration: 11s; animation-delay: 1.5s; opacity: 0.6; }
    .matrix-column:nth-child(7) { left: 33%; animation-duration: 14s; animation-delay: 2.5s; }
    .matrix-column:nth-child(8) { left: 38%; animation-duration: 8s; animation-delay: 0.8s; opacity: 0.5; }
    .matrix-column:nth-child(9) { left: 43%; animation-duration: 13s; animation-delay: 4s; }
    .matrix-column:nth-child(10) { left: 48%; animation-duration: 9s; animation-delay: 1.2s; opacity: 0.4; }
    .matrix-column:nth-child(11) { left: 53%; animation-duration: 16s; animation-delay: 3.5s; }
    .matrix-column:nth-child(12) { left: 58%; animation-duration: 10s; animation-delay: 0.3s; opacity: 0.6; }
    .matrix-column:nth-child(13) { left: 63%; animation-duration: 12s; animation-delay: 2.8s; }
    .matrix-column:nth-child(14) { left: 68%; animation-duration: 8s; animation-delay: 1.8s; opacity: 0.5; }
    .matrix-column:nth-child(15) { left: 73%; animation-duration: 14s; animation-delay: 4.5s; }
    .matrix-column:nth-child(16) { left: 78%; animation-duration: 11s; animation-delay: 0.6s; opacity: 0.4; }
    .matrix-column:nth-child(17) { left: 83%; animation-duration: 9s; animation-delay: 3.2s; }
    .matrix-column:nth-child(18) { left: 88%; animation-duration: 15s; animation-delay: 2.2s; opacity: 0.6; }
    .matrix-column:nth-child(19) { left: 93%; animation-duration: 10s; animation-delay: 1.4s; }
    .matrix-column:nth-child(20) { left: 98%; animation-duration: 13s; animation-delay: 5s; opacity: 0.5; }
    
    .stApp { background: transparent !important; font-family: 'Inter', sans-serif; }
    .stApp::before {
        content: ''; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(10, 15, 20, 0.85); z-index: -1; pointer-events: none;
    }
    
    header, #MainMenu, footer { visibility: hidden; }
    
    .main .block-container { max-width: 1600px !important; padding: 2rem !important; }
    
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        background: linear-gradient(145deg, rgba(0, 40, 20, 0.85), rgba(10, 30, 15, 0.9)) !important;
        backdrop-filter: blur(20px); border: 2px solid rgba(0, 255, 100, 0.25) !important;
        border-radius: 16px !important; box-shadow: 0 4px 24px rgba(0, 255, 100, 0.15); padding: 1.5rem;
    }
    
    .stTextInput input, .stTextArea textarea {
        background: rgba(0, 20, 10, 0.7) !important; color: #00ff66 !important;
        border: 2px solid rgba(0, 255, 100, 0.3) !important; border-radius: 10px !important;
        font-family: 'Share Tech Mono', monospace !important;
    }
    
    .stSelectbox div[data-baseweb="select"] > div {
        background: rgba(0, 20, 10, 0.7) !important; border: 2px solid rgba(0, 255, 100, 0.3) !important;
        border-radius: 10px !important; color: #00ff66 !important;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, rgba(0, 200, 80, 0.9), rgba(0, 150, 60, 0.9));
        color: #000 !important; border: none; border-radius: 10px; font-weight: 700;
        box-shadow: 0 4px 15px rgba(0, 255, 100, 0.3); text-transform: uppercase;
    }
    
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 6px 25px rgba(0, 255, 100, 0.5); }
    
    .stDownloadButton > button {
        background: linear-gradient(135deg, rgba(0, 180, 255, 0.9), rgba(0, 120, 200, 0.9)) !important;
        color: #000 !important;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px; background: rgba(0, 40, 20, 0.6); padding: 8px;
        border-radius: 12px; border: 1px solid rgba(0, 255, 100, 0.2); flex-wrap: wrap;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent; border-radius: 8px; color: rgba(0, 255, 100, 0.7);
        padding: 8px 14px; font-weight: 500; font-size: 12px;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(0, 200, 80, 0.9), rgba(0, 150, 60, 0.9)) !important;
        color: #000 !important; font-weight: 700;
    }
    
    h1, h2, h3 { color: #00ff66 !important; font-weight: 600 !important; }
    p, label, .stMarkdown { color: rgba(0, 255, 100, 0.85) !important; }
    
    .main-title { text-align: center; padding: 1rem 0 0.5rem 0; }
    .main-title h1 {
        background: linear-gradient(135deg, #00ff66, #00ffaa);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-size: 2.5rem !important;
    }
    .main-title p { color: rgba(0, 255, 100, 0.5) !important; font-family: 'Share Tech Mono', monospace; }
    
    hr { border: none; height: 1px; background: linear-gradient(90deg, transparent, rgba(0, 255, 100, 0.3), transparent); }
    
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: rgba(0, 20, 10, 0.5); }
    ::-webkit-scrollbar-thumb { background: rgba(0, 255, 100, 0.4); border-radius: 10px; }
</style>

<div class="matrix-bg">
    <div class="matrix-column">ア イ ウ エ オ 0 1 0 1</div>
    <div class="matrix-column">1 0 1 カ キ ク ケ コ</div>
    <div class="matrix-column">サ シ ス 0 1 1 0</div>
    <div class="matrix-column">0 1 0 タ チ ツ テ</div>
    <div class="matrix-column">ナ ニ ヌ 0 1 0 1</div>
    <div class="matrix-column">1 0 ハ ヒ フ ヘ ホ</div>
    <div class="matrix-column">マ ミ ム 1 0 1</div>
    <div class="matrix-column">0 ヤ ユ ヨ 1 0</div>
    <div class="matrix-column">ラ リ ル 0 1 0</div>
    <div class="matrix-column">1 0 1 ワ ヲ ン</div>
    <div class="matrix-column">ア 0 カ 1 サ 0</div>
    <div class="matrix-column">1 タ 0 ナ 1 ハ</div>
    <div class="matrix-column">0 マ 1 ヤ 0 ラ</div>
    <div class="matrix-column">1 0 1 0 1 0 1</div>
    <div class="matrix-column">ア イ ウ エ オ</div>
    <div class="matrix-column">0 1 0 1 0 1</div>
    <div class="matrix-column">カ キ ク ケ コ</div>
    <div class="matrix-column">1 0 1 0 1 0</div>
    <div class="matrix-column">サ シ ス セ ソ</div>
    <div class="matrix-column">0 1 0 1 0 1</div>
</div>
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
        "🇲🇲 Myanmar (Thiha)": "my-MM-ThihaNeural",
        "🇲🇲 Myanmar (Nilar)": "my-MM-NilarNeural",
        "🇺🇸 English US (Jenny)": "en-US-JennyNeural",
        "🇺🇸 English US (Guy)": "en-US-GuyNeural",
        "🇬🇧 English UK (Sonia)": "en-GB-SoniaNeural",
        "🇹🇭 Thai (Premwadee)": "th-TH-PremwadeeNeural",
        "🇨🇳 Chinese (Xiaoxiao)": "zh-CN-XiaoxiaoNeural",
        "🇯🇵 Japanese (Nanami)": "ja-JP-NanamiNeural",
        "🇰🇷 Korean (SunHi)": "ko-KR-SunHiNeural",
    }

async def generate_tts_async(text, voice, rate, output_path):
    rate_str = f"+{rate}%" if rate >= 0 else f"{rate}%"
    communicate = edge_tts.Communicate(text, voice, rate=rate_str)
    await communicate.save(output_path)

def generate_tts(text, voice, rate=0):
    if not EDGE_TTS_AVAILABLE: return None, "Edge TTS not available"
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
        if not file_id: return None, "Invalid URL"
        if progress_placeholder: progress_placeholder.info("📥 Downloading...")
        
        tmp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        gdrive_url = f"https://drive.google.com/uc?id={file_id}"
        
        if GDOWN_AVAILABLE:
            if gdown.download(gdrive_url, tmp_path, quiet=False, fuzzy=True):
                if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 1000:
                    if progress_placeholder: progress_placeholder.success(f"✅ Downloaded: {os.path.getsize(tmp_path)/(1024*1024):.1f} MB")
                    return tmp_path, None
        return None, "Download failed"
    except Exception as e: return None, str(e)

def save_uploaded_file_chunked(uploaded_file, progress_placeholder=None):
    try:
        ext = uploaded_file.name.split('.')[-1] if '.' in uploaded_file.name else 'mp4'
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
        
        uploaded_file.seek(0, 2)
        file_size = uploaded_file.tell()
        uploaded_file.seek(0)
        
        if progress_placeholder: progress_placeholder.info(f"💾 Saving ({file_size/(1024*1024):.1f} MB)...")
        
        chunk_size = 10 * 1024 * 1024
        written = 0
        progress = st.progress(0)
        
        while chunk := uploaded_file.read(chunk_size):
            tmp_file.write(chunk)
            written += len(chunk)
            progress.progress(min(written / file_size, 1.0))
        
        tmp_file.close()
        progress.empty()
        if progress_placeholder: progress_placeholder.success(f"✅ Saved: {written/(1024*1024):.1f} MB")
        return tmp_file.name, None
    except Exception as e: return None, str(e)

def upload_to_gemini(file_path, progress_placeholder=None):
    try:
        if progress_placeholder:
            progress_placeholder.info(f"📤 Uploading ({os.path.getsize(file_path)/(1024*1024):.1f} MB)...")
        
        file = genai.upload_file(file_path)
        wait = 0
        while file.state.name == "PROCESSING":
            wait += 1
            if progress_placeholder: progress_placeholder.info(f"⏳ Processing... ({wait*2}s)")
            time.sleep(2)
            file = genai.get_file(file.name)
            if wait > 300: return None
        
        if file.state.name == "FAILED": return None
        if progress_placeholder: progress_placeholder.success("✅ Uploaded!")
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
        if not response or not response.candidates: return None, "Empty response"
        parts = response.candidates[0].content.parts if hasattr(response.candidates[0], 'content') else []
        text = "\n".join([p.text for p in parts if hasattr(p, 'text') and p.text])
        return (text, None) if text else (None, "No text")
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
                    st.warning(f"⏳ Rate limited. Waiting {10*(2**attempt)}s...")
                    time.sleep(10 * (2 ** attempt))
                else: return None, "Rate limit exceeded"
            else: return None, str(e)
    return None, "Max retries"

def process_video(file_path, video_name, vision_model, writer_model, style="", custom="", status=None):
    gemini_file = None
    try:
        if status: status.info("📤 Step 1/3: Uploading...")
        gemini_file = upload_to_gemini(file_path, status)
        if not gemini_file: return None, "Upload failed"
        
        if status: status.info("👀 Step 2/3: Analyzing...")
        vision = genai.GenerativeModel(vision_model)
        resp, err = call_gemini_api(vision, [gemini_file, "Watch carefully. Generate detailed scene-by-scene description with dialogue, emotions, actions."], 600)
        if err: return None, f"Vision failed: {err}"
        desc, _ = get_response_text_safe(resp)
        
        time.sleep(5)
        
        if status: status.info("✍️ Step 3/3: Writing script...")
        writer = genai.GenerativeModel(writer_model)
        prompt = f"You are a Burmese Movie Recap Scriptwriter.\n\n**INPUT:** {desc}\n{style}\n{f'**CUSTOM:** {custom}' if custom else ''}\n\n**Write in 100% Burmese, storytelling tone, scene-by-scene.**"
        resp, err = call_gemini_api(writer, prompt, 600)
        if err: return None, f"Writing failed: {err}"
        
        text, _ = get_response_text_safe(resp)
        return text, None
    except Exception as e: return None, str(e)
    finally:
        if gemini_file:
            try: genai.delete_file(gemini_file.name)
            except: pass
        force_memory_cleanup()

# --- MAIN TITLE ---
st.markdown('<div class="main-title"><h1>✨ Ultimate AI Studio</h1><p>// ALL-IN-ONE CREATIVE DASHBOARD //</p></div>', unsafe_allow_html=True)

# --- LIBRARY STATUS ---
missing = [x for x, v in [("PyPDF2", PDF_AVAILABLE), ("python-docx", DOCX_AVAILABLE), ("gdown", GDOWN_AVAILABLE), ("supabase", SUPABASE_AVAILABLE), ("edge-tts", EDGE_TTS_AVAILABLE)] if not v]
if missing: st.warning(f"⚠️ Missing: {', '.join(missing)}")

# --- TOP BAR ---
with st.container(border=True):
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1: api_key = st.text_input("🔑 API Key", type="password", placeholder="Paste API key...", label_visibility="collapsed")
    with c2: vision_model = st.selectbox("Vision", ["models/gemini-2.5-flash", "models/gemini-2.5-pro", "models/gemini-3-pro-preview", "gemini-1.5-flash", "gemini-2.0-flash-exp"], label_visibility="collapsed")
    with c3: writer_model = st.selectbox("Writer", ["gemini-1.5-flash", "gemini-2.0-flash-exp", "models/gemini-2.5-flash", "models/gemini-3-pro-preview", "models/gemini-2.5-pro"], label_visibility="collapsed")
    
    if api_key:
        try: genai.configure(api_key=api_key)
        except: pass

# --- TABS ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(["🎬 Recap", "🌍 Translator", "🎨 Thumbnail", "✍️ Rewriter", "📰 News", "📝 Notes", "🔊 TTS", "🎬 Editor"])

# === TAB 1: MOVIE RECAP ===
with tab1:
    c1, c2 = st.columns([1, 1], gap="medium")
    
    with c1:
        with st.container(border=True):
            st.subheader("📂 Add Videos")
            method = st.radio("Method:", ["📁 Local", "🔗 Google Drive"], horizontal=True)
            st.markdown("---")
            
            if method == "📁 Local":
                st.warning("⚠️ Max 200MB. Use Google Drive for larger files.")
                vids = st.file_uploader("Videos", type=["mp4", "mkv", "mov"], accept_multiple_files=True, key="vids")
                if st.button("➕ Add", key="add_local"):
                    for v in (vids or [])[:10-len(st.session_state['video_queue'])]:
                        v.seek(0, 2)
                        if v.tell() <= 200*1024*1024:
                            v.seek(0)
                            path, _ = save_uploaded_file_chunked(v)
                            if path:
                                st.session_state['video_queue'].append({'name': v.name, 'type': 'file', 'path': path, 'url': None, 'status': 'waiting', 'script': None, 'error': None})
                    st.rerun()
            else:
                st.success("✅ Recommended for large files")
                links = st.text_area("Links (one per line)", height=120, key="links")
                if st.button("➕ Add", key="add_links"):
                    for link in (links.strip().split('\n') if links else [])[:10-len(st.session_state['video_queue'])]:
                        if 'drive.google.com' in link and extract_file_id_from_url(link.strip()):
                            st.session_state['video_queue'].append({'name': f"Video_{len(st.session_state['video_queue'])+1}", 'type': 'url', 'path': None, 'url': link.strip(), 'status': 'waiting', 'script': None, 'error': None})
                    st.rerun()
            
            st.markdown("---")
            st.caption(f"Vision: {vision_model.split('/')[-1]} | Writer: {writer_model.split('/')[-1]}")
            
            with st.expander("📝 Custom Instructions"):
                st.session_state['custom_prompt'] = st.text_area("Instructions:", st.session_state.get('custom_prompt', ''), height=60, key="custom_instr")
            
            style_file = st.file_uploader("📄 Style", type=["txt", "pdf", "docx"], key="style_ref")
            if style_file and (content := read_file_content(style_file)):
                st.session_state['style_text'] = f"\n**STYLE:**\n{content[:5000]}\n"
            
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚀 Start", disabled=not st.session_state['video_queue'] or st.session_state['processing_active']):
                    if api_key:
                        st.session_state['processing_active'] = True
                        st.session_state['current_index'] = 0
                        st.rerun()
            with col2:
                if st.button("🗑️ Clear", disabled=not st.session_state['video_queue']):
                    for i in st.session_state['video_queue']: cleanup_temp_file(i.get('path'))
                    st.session_state['video_queue'] = []
                    st.session_state['processing_active'] = False
                    st.rerun()
    
    with c2:
        with st.container(border=True):
            st.subheader("📋 Queue")
            if not st.session_state['video_queue']:
                st.info("Add videos to start")
            else:
                total = len(st.session_state['video_queue'])
                done = sum(1 for v in st.session_state['video_queue'] if v['status'] == 'completed')
                st.progress(done/total if total else 0)
                st.caption(f"✅ {done}/{total}")
                
                for i, item in enumerate(st.session_state['video_queue']):
                    emoji = {'waiting': '⏳', 'processing': '🔄', 'completed': '✅', 'failed': '❌'}[item['status']]
                    st.markdown(f"**{emoji} {i+1}. {item['name']}**")
                    if item['status'] == 'completed' and item['script']:
                        st.download_button(f"📥 #{i+1}", item['script'], f"{item['name']}_recap.txt", key=f"dl_{i}")
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
                            status.success("✅ Done!")
                        else:
                            st.session_state['video_queue'][idx]['status'] = 'failed'
                            st.session_state['video_queue'][idx]['error'] = err
                            status.error(f"❌ {err}")
                        
                        time.sleep(10)
                        st.session_state['current_index'] += 1
                        st.rerun()
            else:
                st.success("🎉 All done!")
                st.balloons()
                st.session_state['processing_active'] = False

# === TAB 2: TRANSLATOR (IMPROVED) ===
with tab2:
    c1, c2 = st.columns([1, 1], gap="medium")
    
    with c1:
        with st.container(border=True):
            st.subheader("📄 Upload & Settings")
            
            # Language selection
            languages = {
                "🇲🇲 Myanmar (Burmese)": "Burmese",
                "🇺🇸 English": "English", 
                "🇹🇭 Thai": "Thai",
                "🇨🇳 Chinese": "Chinese",
                "🇯🇵 Japanese": "Japanese",
                "🇰🇷 Korean": "Korean",
                "🇻🇳 Vietnamese": "Vietnamese",
                "🇮🇳 Hindi": "Hindi",
                "🇫🇷 French": "French",
                "🇩🇪 German": "German",
                "🇪🇸 Spanish": "Spanish",
            }
            target_lang = st.selectbox("🌍 Target Language:", list(languages.keys()), key="trans_lang")
            
            # File upload - now includes docx
            trans_file = st.file_uploader("📁 File", type=["mp3", "mp4", "txt", "srt", "docx"], key="trans_file")
            
            # Style reference
            trans_style = st.file_uploader("📄 Style Reference (Optional)", type=["txt", "pdf", "docx"], key="trans_style")
            
            if st.button("🚀 Translate", use_container_width=True):
                if api_key and trans_file:
                    st.session_state['run_translate'] = True
    
    with c2:
        with st.container(border=True):
            st.subheader("📝 Output")
            if st.session_state.get('run_translate') and trans_file:
                try:
                    ext = trans_file.name.split('.')[-1].lower()
                    style_text = ""
                    if trans_style:
                        style_content = read_file_content(trans_style)
                        if style_content:
                            style_text = f"\n\n**STYLE REFERENCE:**\n{style_content[:3000]}\n"
                    
                    target = languages[target_lang]
                    
                    if ext in ['txt', 'srt']:
                        with st.spinner("Translating..."):
                            text = trans_file.getvalue().decode("utf-8")
                            model = genai.GenerativeModel(writer_model)
                            prompt = f"Translate to **{target}**. Keep formatting. Return ONLY translated text.{style_text}\n\nInput:\n{text}"
                            res, _ = call_gemini_api(model, prompt)
                            if res:
                                result, _ = get_response_text_safe(res)
                                if result:
                                    st.text_area("Result", result, height=300)
                                    st.download_button("📥 Download", result, f"trans_{trans_file.name}")
                    
                    elif ext == 'docx':
                        with st.spinner("Translating document..."):
                            text = read_file_content(trans_file)
                            if text:
                                model = genai.GenerativeModel(writer_model)
                                prompt = f"Translate to **{target}**. Keep formatting. Return ONLY translated text.{style_text}\n\nInput:\n{text}"
                                res, _ = call_gemini_api(model, prompt)
                                if res:
                                    result, _ = get_response_text_safe(res)
                                    if result:
                                        st.text_area("Result", result, height=300)
                                        st.download_button("📥 Download", result, f"trans_{trans_file.name}.txt")
                    
                    else:  # audio/video
                        with st.spinner("Processing audio..."):
                            path, _ = save_uploaded_file_chunked(trans_file)
                            if path:
                                gfile = upload_to_gemini(path)
                                if gfile:
                                    model = genai.GenerativeModel(writer_model)
                                    prompt = f"Transcribe and translate to **{target}**.{style_text}"
                                    res, _ = call_gemini_api(model, [gfile, prompt], 600)
                                    if res:
                                        result, _ = get_response_text_safe(res)
                                        if result:
                                            st.text_area("Result", result, height=300)
                                            st.download_button("📥 Download", result, f"{trans_file.name}_trans.txt")
                                    try: genai.delete_file(gfile.name)
                                    except: pass
                                cleanup_temp_file(path)
                except Exception as e:
                    st.error(str(e))
                st.session_state['run_translate'] = False
            else:
                st.info("Upload a file and click Translate")

# === TAB 3: THUMBNAIL (MULTIPLE REFS) ===
with tab3:
    c1, c2 = st.columns([1, 1], gap="medium")
    
    with c1:
        with st.container(border=True):
            st.subheader("🎨 Generator")
            
            # Multiple reference images (up to 10)
            ref_images = st.file_uploader("🖼️ Reference Images (max 10)", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True, key="thumb_refs")
            
            if ref_images:
                cols = st.columns(min(len(ref_images), 5))
                for i, img in enumerate(ref_images[:10]):
                    with cols[i % 5]:
                        st.image(img, width=80, caption=f"Ref {i+1}")
                st.caption(f"✅ {len(ref_images[:10])} reference image(s) loaded")
            
            templates = {
                "Custom": "",
                "Movie Recap": "dramatic YouTube thumbnail, 1280x720, cinematic, emotional, bold text",
                "Shocking": "YouTube thumbnail, shocked expression, red/yellow, bold text, 1280x720",
                "Before/After": "split screen comparison, clear dividing line, contrasting colors, 1280x720",
            }
            template = st.selectbox("Template", list(templates.keys()))
            prompt = st.text_area("Prompt", value=templates[template], height=100, key="thumb_prompt")
            
            add_text = st.text_input("Text overlay", placeholder="EP.1", key="thumb_txt")
            num_imgs = st.selectbox("Count", [1, 2, 3, 4], key="thumb_cnt")
            
            gen = st.button("🚀 Generate", use_container_width=True)
    
    with c2:
        with st.container(border=True):
            st.subheader("🖼️ Results")
            
            if gen and api_key and prompt:
                st.session_state['generated_images'] = []
                final_prompt = prompt + (f", text: '{add_text}'" if add_text else "") + ", high quality"
                
                try:
                    model = genai.GenerativeModel("models/gemini-3-pro-image-preview")
                    
                    for i in range(num_imgs):
                        st.info(f"Generating {i+1}/{num_imgs}...")
                        
                        # Build content with all reference images
                        content = [f"Generate: {final_prompt}"]
                        if ref_images:
                            for ref in ref_images[:10]:
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
                        time.sleep(2)
                    
                    st.success(f"Generated {len(st.session_state['generated_images'])} images")
                except Exception as e:
                    st.error(str(e))
            
            for img in st.session_state.get('generated_images', []):
                st.image(img['data'], use_container_width=True)
                st.download_button(f"📥 {img['idx']}", img['data'], f"thumb_{img['idx']}.png", key=f"dl_img_{img['idx']}_{time.time()}")

# === TAB 4: REWRITER ===
with tab4:
    c1, c2 = st.columns([1, 1], gap="medium")
    
    with c1:
        with st.container(border=True):
            st.subheader("✍️ Input")
            style_file = st.file_uploader("Style Reference", type=["txt", "pdf", "docx"], key="rw_style")
            original = st.text_area("Original Script", height=250, key="rw_orig")
            rewrite = st.button("✨ Rewrite", use_container_width=True)
    
    with c2:
        with st.container(border=True):
            st.subheader("📝 Output")
            if rewrite and api_key and original:
                try:
                    style = read_file_content(style_file) if style_file else "Professional tone"
                    with st.spinner("Rewriting..."):
                        model = genai.GenerativeModel(writer_model)
                        prompt = f"Rewrite in TARGET STYLE. Keep all details. Output: Burmese.\n\n**STYLE:** {style[:5000]}\n\n**ORIGINAL:** {original}"
                        res, err = call_gemini_api(model, prompt)
                        if res:
                            text, _ = get_response_text_safe(res)
                            if text:
                                st.text_area("Result", text, height=350)
                                st.download_button("📥 Download", text, "rewritten.txt")
                        else:
                            st.error(err)
                except Exception as e:
                    st.error(str(e))
            else:
                st.info("Paste script and click Rewrite")

# === TAB 5: AI NEWS (FIXED) ===
with tab5:
    with st.container(border=True):
        st.subheader("📰 AI News")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            refresh = st.button("🔄 Refresh", use_container_width=True)
        with col2:
            if st.session_state.get('ai_news_timestamp'):
                st.caption(f"Updated: {st.session_state['ai_news_timestamp']}")
        
        if refresh:
            if not api_key:
                st.error("⚠️ API Key required")
            else:
                with st.spinner("Fetching latest AI news..."):
                    try:
                        model = genai.GenerativeModel("gemini-1.5-flash")  # Use faster model for news
                        prompt = """You are an AI news reporter. Provide the LATEST news (December 2024 - present) about:

1. **OpenAI** - ChatGPT, GPT-4, Sora updates
2. **Google** - Gemini 2.0, AI Studio updates  
3. **Anthropic** - Claude 3.5, Claude updates
4. **Meta** - Llama 3, AI features
5. **Microsoft** - Copilot updates
6. **Other** - Notable AI developments

For each: Latest updates, new features, pricing changes. Be concise and factual."""
                        
                        response, err = call_gemini_api(model, prompt, 120)
                        if response:
                            text, _ = get_response_text_safe(response)
                            if text:
                                st.session_state['ai_news_cache'] = text
                                st.session_state['ai_news_timestamp'] = time.strftime("%Y-%m-%d %H:%M")
                                st.rerun()
                            else:
                                st.error("Failed to get response")
                        else:
                            st.error(f"Error: {err}")
                    except Exception as e:
                        st.error(f"Error: {e}")
        
        st.markdown("---")
        
        if st.session_state.get('ai_news_cache'):
            st.markdown(st.session_state['ai_news_cache'])
        else:
            st.info("👆 Click 'Refresh' to fetch the latest AI news")
            st.markdown("""
**Covered Topics:**
- 🤖 OpenAI (ChatGPT, GPT-4, Sora)
- 🔷 Google (Gemini, AI Studio)
- 🟠 Anthropic (Claude)
- 🔵 Meta (Llama)
- 🟦 Microsoft (Copilot)
""")

# === TAB 6: NOTES ===
with tab6:
    with st.container(border=True):
        st.subheader("📝 Note Pad")
        
        if not api_key:
            st.warning("🔐 API Key ထည့်မှ Notes သုံးလို့ရမယ်")
        elif not SUPABASE_AVAILABLE:
            st.error("❌ Supabase not available")
        else:
            user_hash = get_user_hash(api_key)
            c1, c2 = st.columns([1, 2], gap="medium")
            
            with c1:
                st.markdown("**📋 My Notes**")
                if st.button("➕ New Note", use_container_width=True):
                    note = create_note(user_hash, "Untitled", "")
                    if note:
                        st.session_state['current_note_id'] = note['id']
                        st.rerun()
                
                st.markdown("---")
                notes = get_notes(user_hash)
                
                if not notes:
                    st.info("No notes yet")
                else:
                    for n in notes:
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            if st.button(f"📄 {n['title'][:25]}", key=f"n_{n['id']}", use_container_width=True):
                                st.session_state['current_note_id'] = n['id']
                                st.rerun()
                        with col2:
                            if st.button("🗑️", key=f"d_{n['id']}"):
                                delete_note(n['id'])
                                if st.session_state.get('current_note_id') == n['id']:
                                    st.session_state['current_note_id'] = None
                                st.rerun()
            
            with c2:
                st.markdown("**✏️ Editor**")
                current_id = st.session_state.get('current_note_id')
                
                if current_id:
                    note = next((n for n in notes if n['id'] == current_id), None)
                    if note:
                        title = st.text_input("Title", note['title'], key="n_title")
                        content = st.text_area("Content", note['content'] or "", height=350, key="n_content")
                        
                        if st.button("💾 Save", use_container_width=True):
                            update_note(current_id, title, content)
                            st.success("✅ Saved!")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.session_state['current_note_id'] = None
                        st.rerun()
                else:
                    st.info("👈 Select or create a note")

# === TAB 7: TTS ===
with tab7:
    with st.container(border=True):
        st.subheader("🔊 Text-to-Speech")
        
        if not EDGE_TTS_AVAILABLE:
            st.error("❌ Edge TTS not available")
        else:
            c1, c2 = st.columns([1, 1], gap="medium")
            
            with c1:
                st.markdown("**📝 Input**")
                tts_text = st.text_area("Text:", height=250, placeholder="ဒီမှာ စာသားထည့်ပါ...", key="tts_txt")
                
                tts_file = st.file_uploader("Or upload", type=["txt"], key="tts_f")
                if tts_file:
                    tts_text = tts_file.getvalue().decode("utf-8")
                
                st.markdown("---")
                voices = get_voice_list()
                voice_name = st.selectbox("Voice:", list(voices.keys()), key="tts_v")
                rate = st.slider("Speed:", -50, 50, 0, format="%d%%", key="tts_r")
                st.caption(f"Characters: {len(tts_text)}")
            
            with c2:
                st.markdown("**🎧 Output**")
                
                if st.button("🔊 Generate", use_container_width=True):
                    if tts_text.strip():
                        with st.spinner("Generating..."):
                            path, err = generate_tts(tts_text, voices[voice_name], rate)
                            if path and os.path.exists(path):
                                st.session_state['tts_audio'] = path
                                st.success("✅ Generated!")
                            else:
                                st.error(f"❌ {err}")
                
                if st.session_state.get('tts_audio') and os.path.exists(st.session_state['tts_audio']):
                    st.markdown("---")
                    with open(st.session_state['tts_audio'], 'rb') as f:
                        audio = f.read()
                    st.audio(audio, format='audio/mp3')
                    st.download_button("📥 Download MP3", audio, "tts.mp3", "audio/mp3", use_container_width=True)
                    
                    if st.button("🗑️ Clear"):
                        cleanup_temp_file(st.session_state['tts_audio'])
                        st.session_state['tts_audio'] = None
                        st.rerun()
                else:
                    st.info("Enter text and generate")

# === TAB 8: EDITOR MODE ===
with tab8:
    with st.container(border=True):
        st.subheader("🎬 Editor Mode")
        st.caption("Script editing with video player - side by side")
        
        # Slider for panel ratio
        ratio = st.slider("📐 Panel Ratio (Script : Video)", 20, 80, 50, 5, key="editor_ratio")
        
        st.markdown("---")
        
        # Create columns based on ratio
        script_col, video_col = st.columns([ratio, 100-ratio])
        
        with script_col:
            st.markdown("### 📝 Script Editor")
            
            # File operations
            col1, col2, col3 = st.columns(3)
            with col1:
                script_file = st.file_uploader("📂 Open", type=["txt", "docx"], key="ed_open", label_visibility="collapsed")
            with col2:
                if st.button("📋 Clear", use_container_width=True):
                    st.session_state['editor_script'] = ""
                    st.rerun()
            with col3:
                if st.session_state.get('editor_script'):
                    st.download_button("💾 Save", st.session_state['editor_script'], "script.txt", use_container_width=True)
            
            # Load file content
            if script_file:
                if script_file.type == "text/plain":
                    st.session_state['editor_script'] = script_file.getvalue().decode("utf-8")
                elif DOCX_AVAILABLE:
                    content = read_file_content(script_file)
                    if content:
                        st.session_state['editor_script'] = content
            
            # Text editor
            new_script = st.text_area(
                "Edit script here:",
                value=st.session_state.get('editor_script', ''),
                height=500,
                key="ed_script",
                label_visibility="collapsed"
            )
            st.session_state['editor_script'] = new_script
            
            # Word count
            words = len(new_script.split()) if new_script else 0
            chars = len(new_script) if new_script else 0
            st.caption(f"📊 Words: {words} | Characters: {chars}")
            
            # Google Docs link
            st.markdown("---")
            st.markdown("[📝 Open Google Docs](https://docs.google.com/document/create) to save online")
        
        with video_col:
            st.markdown("### 🎥 Video Player")
            
            # Video upload
            video_file = st.file_uploader("📂 Load Video", type=["mp4", "mkv", "mov", "webm"], key="ed_video")
            
            if video_file:
                # Save to temp and play
                try:
                    video_bytes = video_file.read()
                    st.video(video_bytes)
                    st.success(f"✅ Loaded: {video_file.name}")
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.info("👆 Upload a video file to play")
                st.markdown("""
                **Supported formats:**
                - MP4, MKV, MOV, WebM
                
                **Tips:**
                - Drag the slider above to resize panels
                - Script on left, video on right
                - Use Google Docs link to save online
                """)

# --- FOOTER ---
st.markdown("""
<div style='text-align: center; margin-top: 2rem; padding: 1rem; border-top: 1px solid rgba(0, 255, 100, 0.1);'>
    <p style='color: rgba(0, 255, 100, 0.4) !important; font-size: 0.8rem; font-family: "Share Tech Mono", monospace;'>
        ✨ ULTIMATE AI STUDIO v4.0 • GEMINI + SUPABASE + EDGE TTS
    </p>
</div>
""", unsafe_allow_html=True)
