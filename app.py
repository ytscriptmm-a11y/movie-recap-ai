import streamlit as st
import google.generativeai as genai
import time
import os
import tempfile
import gc
import io
import hashlib
import asyncio
import struct  # Added for WAV conversion
import mimetypes # Added for MIME type guessing
from PIL import Image

# --- LIBRARY IMPORTS & CHECKS ---
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
st.set_page_config(
    page_title="AI Studio Pro", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CSS STYLING ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Myanmar:wght@400;500;600;700&display=swap');
    
    .stApp {
        background: #0f172a !important;
        font-family: 'Noto Sans Myanmar', sans-serif;
    }
    
    header, #MainMenu, footer { visibility: hidden; }
    
    /* --- MAIN CONTAINER FIX (1000px) --- */
    [data-testid="block-container"] {
        max-width: 1000px !important;
        padding: 2rem !important;
        margin-left: auto !important;
        margin-right: auto !important;
        margin-top: 2rem !important;
        border: 2px solid rgba(0, 212, 255, 0.5) !important; 
        border-radius: 20px !important;
        background: #151f32 !important;
        box-shadow: 0 0 25px rgba(0, 212, 255, 0.15) !important;
    }

    @media (max-width: 640px) {
        [data-testid="block-container"] {
            max-width: 95% !important;
            padding: 1rem !important;
        }
    }
    
    /* Input Fields */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background-color: #0f172a !important;
        color: #f8fafc !important;
        border: 1px solid rgba(0, 212, 255, 0.6) !important;
        border-radius: 10px !important;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #00d4ff, #0099cc) !important;
        color: #000 !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
    }
    .stDownloadButton > button {
        background: linear-gradient(135deg, #10b981, #059669) !important;
        color: #fff !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: #1e293b;
        padding: 10px;
        border-radius: 12px;
        border: 1px solid rgba(0, 212, 255, 0.3);
    }
    .stTabs [data-baseweb="tab"] { color: #cbd5e1; padding: 10px 20px; }
    .stTabs [aria-selected="true"] {
        background: #00d4ff !important;
        color: #000 !important;
        border-radius: 8px;
    }
    
    /* Text Colors */
    h1, h2, h3, h4, p, span, label, div[data-testid="stMarkdownContainer"] p {
        color: #f8fafc !important;
    }
    [data-testid="stMetricValue"] { color: #00d4ff !important; }
    hr { background: rgba(0, 212, 255, 0.5) !important; height: 1px; border: none; }
    
    /* Elements Fixes */
    div[data-testid="stFileUploader"] section {
        background-color: #1e293b !important;
        border: 1px dashed rgba(0, 212, 255, 0.5) !important;
    }
    div[data-testid="stExpander"] {
        background-color: transparent !important;
        border: 1px solid rgba(0, 212, 255, 0.4) !important;
    }
    .stSelectbox > div > div {
        background-color: #0f172a !important;
        color: #f8fafc !important;
        border: 1px solid rgba(0, 212, 255, 0.6) !important;
    }
</style>
""", unsafe_allow_html=True)

# --- AUDIO CONVERSION HELPERS (New!) ---
def parse_audio_mime_type(mime_type: str) -> dict:
    bits_per_sample = 16
    rate = 24000
    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate = int(param.split("=", 1)[1])
            except: pass
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except: pass
    return {"bits_per_sample": bits_per_sample, "rate": rate}

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size
    
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", chunk_size, b"WAVE", b"fmt ", 16, 1, num_channels,
        sample_rate, byte_rate, block_align, bits_per_sample, b"data", data_size
    )
    return header + audio_data

# --- HELPER FUNCTIONS (GLOBAL) ---
def get_user_hash(api_key):
    return hashlib.sha256(api_key.encode()).hexdigest()[:32]

def force_memory_cleanup():
    gc.collect()

def get_response_text_safe(response):
    try:
        if not response or not response.candidates: return None, "No response"
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
                if attempt < 2: time.sleep(10 * (2 ** attempt))
                else: return None, "Rate limit exceeded"
            else: return None, str(e)
    return None, "Max retries exceeded"

def upload_to_gemini(file_path, progress_placeholder=None):
    try:
        if progress_placeholder:
            progress_placeholder.info(f"Uploading ({os.path.getsize(file_path)/(1024*1024):.1f} MB)...")
        file = genai.upload_file(file_path)
        wait = 0
        while file.state.name == "PROCESSING":
            wait += 1
            if progress_placeholder: progress_placeholder.info(f"Processing... ({wait*2}s)")
            time.sleep(2)
            file = genai.get_file(file.name)
            if wait > 300: return None
        if file.state.name == "FAILED": return None
        return file
    except Exception as e:
        if progress_placeholder: progress_placeholder.error(str(e))
        return None

def save_uploaded_file_chunked(uploaded_file):
    try:
        ext = uploaded_file.name.split('.')[-1] if '.' in uploaded_file.name else 'mp4'
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
        uploaded_file.seek(0, 2)
        file_size = uploaded_file.tell()
        uploaded_file.seek(0)
        
        chunk_size = 10 * 1024 * 1024
        written = 0
        progress = st.progress(0)
        while chunk := uploaded_file.read(chunk_size):
            tmp_file.write(chunk)
            written += len(chunk)
            progress.progress(min(written / file_size, 1.0))
        tmp_file.close()
        progress.empty()
        return tmp_file.name, None
    except Exception as e: return None, str(e)

def cleanup_temp_file(fp):
    if fp and os.path.exists(fp):
        try: os.remove(fp)
        except: pass

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
        if progress_placeholder: progress_placeholder.info("Downloading...")
        
        tmp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        gdrive_url = f"https://drive.google.com/uc?id={file_id}"
        
        if GDOWN_AVAILABLE:
            if gdown.download(gdrive_url, tmp_path, quiet=False, fuzzy=True):
                if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 1000:
                    return tmp_path, None
        return None, "Download failed"
    except Exception as e: return None, str(e)

def process_video(file_path, video_name, vision_model, writer_model, style="", custom="", status=None):
    gemini_file = None
    try:
        if status: status.info("Step 1/3: Uploading to Gemini...")
        gemini_file = upload_to_gemini(file_path, status)
        if not gemini_file: return None, "Upload failed"
        
        if status: status.info("Step 2/3: AI analyzing video...")
        vision = genai.GenerativeModel(vision_model)
        
        vision_prompt = """
        Watch this video carefully. 
        Generate a highly detailed, chronological scene-by-scene description. (Use a storytelling tone.)
        Include All the dialogue in the movie, visual details, emotions, and actions. (Use a storytelling tone.)
        No creative writing yet, just facts.
        """
        
        resp, err = call_gemini_api(vision, [gemini_file, vision_prompt], 600)
        if err: return None, f"Analysis failed: {err}"
        video_description, _ = get_response_text_safe(resp)
        
        time.sleep(5)
        
        if status: status.info("Step 3/3: Writing Burmese recap script...")
        writer = genai.GenerativeModel(writer_model)
        
        custom_instructions = f"\n\n**CUSTOM INSTRUCTIONS:**\n{custom}\n" if custom else ""
        style_text = f"\n\n**WRITING STYLE REFERENCE:**\n{style}\n" if style else ""
        
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
        5. Scene-by-scene.(Use a storytelling tone.) 
        6. Full narration.
        """
        
        resp, err = call_gemini_api(writer, writer_prompt, 600)
        if err: return None, f"Writing failed: {err}"
        
        text, _ = get_response_text_safe(resp)
        return text, None
    except Exception as e: return None, str(e)
    finally:
        if gemini_file:
            try: genai.delete_file(gemini_file.name)
            except: pass
        force_memory_cleanup()

# --- AUTH HELPER FUNCTIONS ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_user(email, password):
    if not supabase: return None, "Database Error"
    try:
        response = supabase.table('users').select('*').eq('email', email).eq('password', hash_password(password)).execute()
        if response.data:
            user = response.data[0]
            if user['approved']:
                return user, "Success"
            else:
                return None, "Approval Pending"
        return None, "Invalid Email or Password"
    except Exception as e:
        return None, str(e)

def register_user(email, password):
    if not supabase: return False, "Database Error"
    try:
        check = supabase.table('users').select('email').eq('email', email).execute()
        if check.data:
            return False, "Email already exists"
        
        data = {
            "email": email, 
            "password": hash_password(password),
            "approved": False,
            "is_admin": False
        }
        supabase.table('users').insert(data).execute()
        return True, "Registration successful! Please wait for admin approval."
    except Exception as e:
        return False, str(e)

def toggle_approval(user_id, current_status):
    if not supabase: return
    try:
        supabase.table('users').update({'approved': not current_status}).eq('id', user_id).execute()
        st.rerun()
    except: pass

# --- NOTES & TTS HELPERS ---
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

def get_voice_list():
    return {
        "Myanmar (Thiha)": "my-MM-ThihaNeural",
        "Myanmar (Nilar)": "my-MM-NilarNeural",
        "English US (Jenny)": "en-US-JennyNeural",
        "English US (Guy)": "en-US-GuyNeural",
        "Thai (Premwadee)": "th-TH-PremwadeeNeural",
    }

def generate_tts(text, voice, rate=0):
    if not EDGE_TTS_AVAILABLE: return None, "Edge TTS not available"
    try:
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
        rate_str = f"+{rate}%" if rate >= 0 else f"{rate}%"
        async def _gen():
            communicate = edge_tts.Communicate(text, voice, rate=rate_str)
            await communicate.save(output_path)
        asyncio.run(_gen())
        return output_path, None
    except Exception as e: return None, str(e)

# --- SESSION STATE ---
def init_session_state():
    defaults = {
        'video_queue': [], 'processing_active': False, 'current_index': 0,
        'run_translate': False, 'style_text': "", 'custom_prompt': "",
        'generated_images': [], 'current_note_id': None, 'tts_audio': None,
        'editor_script': "", 'editor_filename': 'script.txt',
        'user_session': None # Auth Session
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()

# ==========================================
# AUTH FLOW & MAIN APP
# ==========================================

# 1. NOT LOGGED IN
if not st.session_state['user_session']:
    st.title("🔒 Login / Sign Up")
    st.markdown("---")
    
    tab_login, tab_signup = st.tabs(["Login", "Sign Up"])
    
    with tab_login:
        st.subheader("Welcome Back!")
        # Use st.form to enable browser password saving
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_pass")
            submit_login = st.form_submit_button("Login", use_container_width=True)
            
        if submit_login:
            user, msg = login_user(email, password)
            if user:
                st.session_state['user_session'] = user
                st.success("Welcome back!")
                st.rerun()
            elif msg == "Approval Pending":
                st.warning("⚠️ သင့်အကောင့်ကို Admin ခွင့်ပြုချက်စောင့်နေဆဲပါ။")
            else:
                st.error(f"❌ {msg}")

    with tab_signup:
        st.subheader("Create Account")
        new_email = st.text_input("Email", key="reg_email")
        new_pass = st.text_input("Password", type="password", key="reg_pass")
        if st.button("Sign Up", use_container_width=True):
            if new_email and new_pass:
                success, msg = register_user(new_email, new_pass)
                if success:
                    st.success("✅ " + msg)
                else:
                    st.error("❌ " + msg)
            else:
                st.warning("Please fill all fields")

# 2. LOGGED IN (MAIN APP)
else:
    user = st.session_state['user_session']
    
    # --- HEADER & LOGOUT ---
    col_main, col_log = st.columns([5, 1])
    with col_main:
        st.title("AI Studio Pro")
        st.caption(f"User: {user['email']}")
    with col_log:
        if st.button("Logout"):
            st.session_state['user_session'] = None
            st.rerun()

    # --- ADMIN PANEL ---
    if user.get('is_admin', False):
        with st.expander("🛡️ Admin Panel (User Approvals)"):
            if supabase:
                users = supabase.table('users').select('*').order('created_at', desc=True).execute().data
                if users:
                    for u in users:
                        c1, c2, c3 = st.columns([3, 1, 1])
                        with c1: st.write(f"📧 {u['email']}")
                        with c2: 
                            status = "✅ Approved" if u['approved'] else "⏳ Pending"
                            st.caption(status)
                        with c3:
                            if u['email'] != user['email']:
                                btn_label = "Block" if u['approved'] else "Approve"
                                if st.button(btn_label, key=f"btn_{u['id']}"):
                                    toggle_approval(u['id'], u['approved'])
                else:
                    st.info("No users found.")
    
    st.markdown("---")

    # --- API SETTINGS ---
    with st.container(border=True):
        st.subheader("Settings")
        api_key = st.text_input("Google API Key", type="password", placeholder="Enter API Key...")
        if api_key:
            try:
                genai.configure(api_key=api_key)
                st.success("API Key connected")
            except Exception as e:
                st.error(f"Invalid API Key")

    st.markdown("---")

    # --- TABS ---
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["Recap", "Translate", "Thumbnail", "Rewrite", "Notes", "TTS", "Editor"])

    # === TAB 1: RECAP ===
    with tab1:
        st.header("Video Recap")
        
        with st.container(border=True):
            st.subheader("Model Selection")
            vision_model = st.selectbox("Vision Model", ["gemini-3-pro-image-preview", "models/gemini-2.5-flash", "models/gemini-2.5-pro", "models/gemini-3-pro-preview", "gemini-1.5-flash"], key="vm")
            writer_model = st.selectbox("Writer Model", ["gemini-3-pro-image-preview", "gemini-1.5-flash", "gemini-2.0-flash-exp", "models/gemini-2.5-flash", "models/gemini-2.5-pro", "models/gemini-3-pro-preview"], key="wm")
        
        with st.container(border=True):
            st.subheader("Add Videos")
            method = st.radio("Method", ["Upload (Max 200MB)", "Google Drive Link"], horizontal=True)
            
            if method == "Upload (Max 200MB)":
                vids = st.file_uploader("Videos", type=["mp4", "mkv", "mov"], accept_multiple_files=True)
                if st.button("Add to Queue", key="add1"):
                    for v in (vids or [])[:10-len(st.session_state['video_queue'])]:
                        v.seek(0, 2)
                        if v.tell() <= 200*1024*1024:
                            v.seek(0)
                            path, _ = save_uploaded_file_chunked(v)
                            if path:
                                st.session_state['video_queue'].append({'name': v.name, 'type': 'file', 'path': path, 'url': None, 'status': 'waiting', 'script': None, 'error': None})
                    st.rerun()
            else:
                links = st.text_area("Links (one per line)", height=100)
                if st.button("Add to Queue", key="add2"):
                    for link in (links.strip().split('\n') if links else []):
                        if 'drive.google.com' in link and extract_file_id_from_url(link.strip()):
                            st.session_state['video_queue'].append({'name': f"Video_{len(st.session_state['video_queue'])+1}", 'type': 'url', 'path': None, 'url': link.strip(), 'status': 'waiting', 'script': None, 'error': None})
                    st.rerun()
        
        with st.expander("Custom Instructions"):
            st.session_state['custom_prompt'] = st.text_area("Instructions", st.session_state.get('custom_prompt', ''), height=60)
            style_file = st.file_uploader("Style Reference", type=["txt", "pdf", "docx"], key="sf")
            if style_file and (content := read_file_content(style_file)):
                st.session_state['style_text'] = content[:5000]
        
        with st.container(border=True):
            st.subheader("Queue")
            if not st.session_state['video_queue']:
                st.info("No videos")
            else:
                total = len(st.session_state['video_queue'])
                done = sum(1 for v in st.session_state['video_queue'] if v['status'] == 'completed')
                st.progress(done/total)
                st.caption(f"{done}/{total} done")
                
                for i, item in enumerate(st.session_state['video_queue']):
                    st.markdown(f"**{i+1}. {item['name']}** - {item['status']}")
                    if item['status'] == 'completed' and item['script']:
                        st.download_button(f"Download #{i+1}", item['script'], f"{item['name']}_recap.txt", key=f"dl_{i}")
                    if item['status'] == 'failed':
                        st.error(item['error'][:150] if item['error'] else "Error")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Start", disabled=not st.session_state['video_queue'] or st.session_state['processing_active'] or not api_key, use_container_width=True):
                    st.session_state['processing_active'] = True
                    st.session_state['current_index'] = 0
                    st.rerun()
            with col2:
                if st.button("Clear", disabled=not st.session_state['video_queue'], use_container_width=True, key="clear_queue"):
                    for item in st.session_state['video_queue']: cleanup_temp_file(item.get('path'))
                    st.session_state['video_queue'] = []
                    st.session_state['processing_active'] = False
                    st.rerun()
        
        if st.session_state['processing_active']:
            idx = st.session_state['current_index']
            if idx < len(st.session_state['video_queue']):
                item = st.session_state['video_queue'][idx]
                if item['status'] == 'waiting':
                    st.session_state['video_queue'][idx]['status'] = 'processing'
                    with st.container(border=True):
                        st.markdown(f"### Processing: {item['name']}")
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
                            status.success("Done!")
                        else:
                            st.session_state['video_queue'][idx]['status'] = 'failed'
                            st.session_state['video_queue'][idx]['error'] = err
                            status.error(err)
                        
                        time.sleep(10)
                        st.session_state['current_index'] += 1
                        st.rerun()
            else:
                st.success("All done!")
                st.balloons()
                st.session_state['processing_active'] = False

    # === TAB 2: TRANSLATE ===
    with tab2:
        st.header("Translator")
        
        with st.container(border=True):
            col_t1, col_t2 = st.columns([3, 1])
            with col_t2:
                trans_model = st.selectbox("Model", ["gemini-1.5-flash", "gemini-2.0-flash-exp", "models/gemini-2.5-flash"], key="trans_model_select")
            with col_t1:
                languages = {"Burmese": "Burmese", "English": "English", "Thai": "Thai", "Chinese": "Chinese", "Japanese": "Japanese", "Korean": "Korean"}
                target_lang = st.selectbox("Target Language", list(languages.keys()))
                
            trans_file = st.file_uploader("File", type=["mp3", "mp4", "txt", "srt", "docx"], key="tf")
            
            if st.button("Translate", use_container_width=True):
                if api_key and trans_file:
                    ext = trans_file.name.split('.')[-1].lower()
                    target = languages[target_lang]
                    model = genai.GenerativeModel(trans_model)
                    
                    if ext in ['txt', 'srt']:
                        with st.spinner("Translating..."):
                            text = trans_file.getvalue().decode("utf-8")
                            res, _ = call_gemini_api(model, f"Translate to {target}. Return ONLY translated text.\n\n{text}")
                            if res:
                                result, _ = get_response_text_safe(res)
                                if result:
                                    st.text_area("Result", result, height=300)
                                    st.download_button("Download", result, f"trans_{trans_file.name}")
                    elif ext == 'docx':
                        with st.spinner("Translating..."):
                            text = read_file_content(trans_file)
                            if text:
                                res, _ = call_gemini_api(model, f"Translate to {target}. Return ONLY translated text.\n\n{text}")
                                if res:
                                    result, _ = get_response_text_safe(res)
                                    if result:
                                        st.text_area("Result", result, height=300)
                                        st.download_button("Download", result, f"trans_{trans_file.name}.txt")
                    else:
                        with st.spinner("Processing..."):
                            path, _ = save_uploaded_file_chunked(trans_file)
                            if path:
                                gfile = upload_to_gemini(path)
                                if gfile:
                                    res, _ = call_gemini_api(model, [gfile, f"Transcribe and translate to {target}."], 600)
                                    if res:
                                        result, _ = get_response_text_safe(res)
                                        if result:
                                            st.text_area("Result", result, height=300)
                                            st.download_button("Download", result, f"{trans_file.name}_trans.txt")
                                    try: genai.delete_file(gfile.name)
                                    except: pass
                                cleanup_temp_file(path)

    # === TAB 3: THUMBNAIL ===
    with tab3:
        st.header("AI Thumbnail Generator")
        st.caption("Gemini 3 Pro (Nano Banana) ကိုအသုံးပြုထားသည်")

        with st.container(border=True):
            st.markdown("**🖼️ Reference Images (Max 10):**")
            ref_images = st.file_uploader("Upload reference images", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True, key="thumb_ref_images")
            
            if ref_images:
                st.caption(f"Selected {len(ref_images)} reference image(s)")
                cols = st.columns(min(len(ref_images), 6))
                for i, img in enumerate(ref_images[:6]):
                    with cols[i]: st.image(img, use_container_width=True)
            
            st.markdown("---")
            col_temp, col_prompt = st.columns([1, 2])
            with col_temp:
                st.markdown("**📝 Template:**")
                prompt_templates = {
                    "✍️ Custom Prompt": "",
                    "🎬 Movie Recap Thumbnail": "Create a dramatic YouTube movie recap thumbnail, 1280x720 pixels, with cinematic dark color grading, showing dramatic scene with emotional expressions, bold eye-catching title text, professional high contrast style",
                    "😱 Shocking/Dramatic Style": "Create a YouTube thumbnail with shocked surprised expression style, bright red and yellow accent colors, large bold text with outline, arrow pointing to key element, exaggerated expressions, 1280x720 pixels",
                }
                selected_template = st.selectbox("Select a style:", list(prompt_templates.keys()), key="thumb_template", label_visibility="collapsed")
            with col_prompt:
                st.markdown("**🖼️ Prompt:**")
                default_prompt = prompt_templates[selected_template]
                user_prompt = st.text_area("Prompt Input", value=default_prompt, height=100, placeholder="Describe the thumbnail...", key="thumb_prompt_input", label_visibility="collapsed")

            st.markdown("**⚙️ Settings:**")
            col_s1, col_s2, col_s3 = st.columns([2, 1, 2])
            with col_s1: add_text = st.text_input("Text Overlay:", placeholder="e.g., EP.1", key="thumb_text")
            with col_s2: num_images = st.selectbox("Count:", [1, 2, 3, 4], index=0, key="thumb_num")
            with col_s3: style_options = st.multiselect("Styles:", ["Cinematic", "Dramatic Lighting", "High Contrast", "Vibrant Colors", "YouTube Style"], default=["YouTube Style", "High Contrast"], key="thumb_styles")

            st.write("")
            generate_clicked = st.button("🚀 Generate Thumbnail", use_container_width=True, key="btn_gen_thumb")

        if generate_clicked:
            if not api_key: st.error("⚠️ Please enter API Key in Settings first!")
            elif not user_prompt.strip(): st.warning("⚠️ Please enter a prompt!")
            else:
                st.session_state['generated_images'] = []
                final_prompt = user_prompt.strip()
                if add_text: final_prompt += f", with bold text overlay showing '{add_text}'"
                if style_options: final_prompt += f", style: {', '.join(style_options)}"
                final_prompt += ", high quality, detailed, sharp focus"
                
                with st.container(border=True):
                    st.info(f"🎨 Generating with Nano Banana Pro...")
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    try:
                        image_model = genai.GenerativeModel("gemini-3-pro-image-preview")
                        for i in range(num_images):
                            try:
                                status_text.info(f"🔄 Generating image {i+1}/{num_images}...")
                                progress_bar.progress((i) / num_images)
                                content_request = [f"Generate an image: {final_prompt}"]
                                if ref_images:
                                    for ref in ref_images[:10]:
                                        ref.seek(0)
                                        content_request.append(Image.open(ref))
                                response = image_model.generate_content(content_request, request_options={"timeout": 180})
                                image_found = False
                                if response.candidates:
                                    for part in response.candidates[0].content.parts:
                                        if hasattr(part, 'inline_data') and part.inline_data:
                                            st.session_state['generated_images'].append({'data': part.inline_data.data, 'mime_type': part.inline_data.mime_type, 'index': i + 1})
                                            image_found = True
                                            status_text.success(f"✅ Image {i+1} generated!")
                                            break
                                if not image_found: status_text.warning(f"⚠️ Image {i+1} Failed (Safety Filter).")
                                time.sleep(2)
                            except Exception as inner_e: status_text.error(f"⚠️ Image {i+1} Error: {str(inner_e)}")
                        progress_bar.progress(1.0)
                    except Exception as e: st.error(f"❌ Critical Error: {str(e)}")

        if st.session_state.get('generated_images'):
            st.markdown("### 🖼️ Results")
            if st.button("🗑️ Clear All", key="clear_thumb_btn"):
                st.session_state['generated_images'] = []
                st.rerun()
            for idx, img_data in enumerate(st.session_state['generated_images']):
                if idx % 2 == 0: cols = st.columns(2)
                with cols[idx % 2]:
                    with st.container(border=True):
                        st.image(img_data['data'], use_container_width=True)
                        file_ext = "png" if "png" in img_data.get('mime_type', 'png') else "jpg"
                        st.download_button(f"⬇️ Download #{img_data['index']}", img_data['data'], file_name=f"thumbnail_{idx+1}.{file_ext}", mime=img_data.get('mime_type', 'image/png'), key=f"dl_thumb_{idx}_{time.time()}", use_container_width=True)

    # === TAB 4: REWRITE ===
    with tab4:
        st.header("Script Rewriter")
        with st.container(border=True):
            col_r1, col_r2 = st.columns([3, 1])
            with col_r2: rewrite_model = st.selectbox("Model", ["gemini-1.5-flash", "gemini-2.0-flash-exp", "models/gemini-2.5-flash"], key="rewrite_model_select")
            style_file = st.file_uploader("Style Reference", type=["txt", "pdf", "docx"], key="rsf")
            original = st.text_area("Original Script", height=250)
            
            if st.button("Rewrite", use_container_width=True):
                if api_key and original:
                    style = read_file_content(style_file) if style_file else "Professional tone"
                    with st.spinner("Rewriting..."):
                        model = genai.GenerativeModel(rewrite_model)
                        res, err = call_gemini_api(model, f"Rewrite in this style. Keep details. Output Burmese.\n\nSTYLE:\n{style[:5000]}\n\nORIGINAL:\n{original}")
                        if res:
                            text, _ = get_response_text_safe(res)
                            if text:
                                st.text_area("Result", text, height=350)
                                st.download_button("Download", text, "rewritten.txt")

    # === TAB 5: NOTES ===
    with tab5:
        st.header("Notes")
        with st.container(border=True):
            if not api_key: st.warning("Enter API Key to use Notes")
            elif not SUPABASE_AVAILABLE: st.error("Supabase not available")
            else:
                user_hash = get_user_hash(api_key)
                if st.button("New Note", use_container_width=True):
                    note = create_note(user_hash, "Untitled", "")
                    if note:
                        st.session_state['current_note_id'] = note['id']
                        st.rerun()
                notes = get_notes(user_hash)
                if notes:
                    for n in notes:
                        col1, col2 = st.columns([5, 1])
                        with col1:
                            if st.button(n['title'][:25], key=f"n_{n['id']}", use_container_width=True):
                                st.session_state['current_note_id'] = n['id']
                                st.rerun()
                        with col2:
                            if st.button("X", key=f"d_{n['id']}"):
                                delete_note(n['id'])
                                st.rerun()
                current_id = st.session_state.get('current_note_id')
                if current_id and notes:
                    note = next((n for n in notes if n['id'] == current_id), None)
                    if note:
                        st.markdown("---")
                        title = st.text_input("Title", note['title'])
                        content = st.text_area("Content", note['content'] or "", height=300)
                        if st.button("Save", use_container_width=True):
                            update_note(current_id, title, content)
                            st.success("Saved!")
                            st.rerun()

    # === TAB 6: TTS ===
    with tab6:
        st.header("Text to Speech")
        
        with st.container(border=True):
            # Engine Selection
            tts_engine = st.radio("TTS Engine", ["Edge TTS (Free/Reliable)", "Gemini AI (Pro/Experimental)"], horizontal=True)
            
            st.markdown("---")
            
            # --- OPTION 1: EDGE TTS ---
            if "Edge" in tts_engine:
                if not EDGE_TTS_AVAILABLE:
                    st.error("Edge TTS not available")
                else:
                    tts_text = st.text_area("Text Input", height=200, key="edge_text")
                    c1, c2 = st.columns(2)
                    with c1:
                        voices = get_voice_list()
                        voice = st.selectbox("Voice", list(voices.keys()), key="edge_voice")
                    with c2:
                        rate = st.slider("Speed", -50, 50, 0, format="%d%%", key="edge_rate")
                        
                    if st.button("Generate (Edge)", use_container_width=True, key="gen_tts_edge"):
                        if tts_text.strip():
                            with st.spinner("Generating with Edge TTS..."):
                                path, err = generate_tts(tts_text, voices[voice], rate)
                                if path and os.path.exists(path):
                                    st.session_state['tts_audio'] = path
                                    st.success("Done!")
                                else:
                                    st.error(f"Error: {err}")

            # --- OPTION 2: GEMINI AI TTS (With PCM to WAV) ---
            else:
                st.info("💡 Supports 'gemini-2.5-pro-preview-tts' (Raw PCM Audio)")
                
                gemini_text = st.text_area("Text Input", height=200, key="gemini_tts_text")
                
                # Model Selection
                gemini_tts_model = st.selectbox(
                    "Select Gemini Model",
                    [
                        "models/gemini-2.5-pro-preview-tts",
                        "models/gemini-2.5-flash-preview-tts",
                        "gemini-2.0-flash-exp"
                    ],
                    index=0
                )
                
                if st.button("Generate (Gemini AI)", use_container_width=True, key="gen_tts_gemini"):
                    if not api_key:
                        st.error("Please enter API Key in Settings first!")
                    elif not gemini_text.strip():
                        st.warning("Please enter text!")
                    else:
                        with st.spinner(f"Generating audio with {gemini_tts_model}..."):
                            try:
                                model = genai.GenerativeModel(gemini_tts_model)
                                
                                # Request generation (automatically handles Audio response)
                                response = model.generate_content(
                                    f"Please read the following text naturally in Burmese. Text: {gemini_text}"
                                )
                                
                                # Process Response parts
                                audio_found = False
                                if hasattr(response, 'parts'):
                                    for part in response.parts:
                                        if hasattr(part, 'inline_data') and part.inline_data:
                                            # Found Audio Data (Inline Blob)
                                            raw_audio = part.inline_data.data
                                            mime_type = part.inline_data.mime_type
                                            
                                            # If raw PCM, convert to WAV using the code you found!
                                            if "audio/L16" in mime_type or "audio/pcm" in mime_type:
                                                final_audio = convert_to_wav(raw_audio, mime_type)
                                                ext = ".wav"
                                            else:
                                                final_audio = raw_audio
                                                ext = ".mp3"
                                            
                                            # Save File
                                            output_path = tempfile.NamedTemporaryFile(delete=False, suffix=ext).name
                                            with open(output_path, "wb") as f:
                                                f.write(final_audio)
                                            
                                            st.session_state['tts_audio'] = output_path
                                            st.success(f"Done! ({mime_type})")
                                            audio_found = True
                                            break
                                
                                if not audio_found:
                                    # Fallback if text is returned
                                    text_response, _ = get_response_text_safe(response)
                                    st.warning(f"Model returned text: {text_response[:100]}...")
                                    
                            except Exception as e:
                                st.error(f"Gemini TTS Error: {str(e)}")

        # --- AUDIO PLAYER & DOWNLOAD ---
        if st.session_state.get('tts_audio') and os.path.exists(st.session_state['tts_audio']):
            st.markdown("### 🎧 Audio Output")
            with st.container(border=True):
                with open(st.session_state['tts_audio'], 'rb') as f:
                    audio_bytes = f.read()
                
                # Use correct mime type based on file extension
                mime = "audio/wav" if st.session_state['tts_audio'].endswith(".wav") else "audio/mp3"
                st.audio(audio_bytes, format=mime)
                
                st.download_button(
                    label=f"⬇️ Download Audio",
                    data=audio_bytes,
                    file_name=f"tts_audio.{mime.split('/')[1]}",
                    mime=mime,
                    use_container_width=True
                )

    # === TAB 7: EDITOR ===
    with tab7:
        st.header("Script Editor")
        with st.container(border=True):
            col1, col2, col3 = st.columns(3)
            with col1: script_file = st.file_uploader("Open", type=["txt", "docx", "srt"], key="ef", label_visibility="collapsed")
            with col2: 
                if st.button("Clear", use_container_width=True, key="clear_editor"):
                    st.session_state['editor_script'] = ""
                    st.rerun()
            with col3: save_format = st.selectbox("Format", ["txt", "srt", "md"], label_visibility="collapsed")
            
            if script_file:
                if script_file.name.endswith(('.txt', '.srt')): st.session_state['editor_script'] = script_file.getvalue().decode("utf-8")
                elif DOCX_AVAILABLE: st.session_state['editor_script'] = read_file_content(script_file) or ""
            
            current = st.session_state.get('editor_script', '')
            new_script = st.text_area("Script", current, height=400, label_visibility="collapsed")
            if new_script != current: st.session_state['editor_script'] = new_script
            
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Words", len(new_script.split()) if new_script else 0)
            with c2: st.metric("Chars", len(new_script))
            with c3:
                if new_script: st.download_button("Save", new_script, f"script.{save_format}", use_container_width=True)

    st.markdown("---")
    st.caption("AI Studio Pro v6.1")
