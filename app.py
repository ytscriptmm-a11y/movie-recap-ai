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
st.set_page_config(page_title="AI Studio Pro", layout="wide", initial_sidebar_state="collapsed")

# --- SESSION STATE ---
def init_session_state():
    defaults = {
        'video_queue': [], 'processing_active': False, 'current_index': 0,
        'run_translate': False, 'style_text': "", 'custom_prompt': "",
        'generated_images': [], 'current_note_id': None, 'tts_audio': None,
        'editor_script': "", 'editor_filename': 'script.txt'
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()

# --- CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Myanmar:wght@400;500;600;700&display=swap');
    
    .stApp {
        background: #0f172a !important;
        font-family: 'Noto Sans Myanmar', sans-serif;
    }
    
    header, #MainMenu, footer { visibility: hidden; }
    
    .main .block-container { 
        max-width: 800px !important; 
        padding: 1rem 2rem !important;
    }
    
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        background: #1e293b !important;
        border: 1px solid rgba(0, 212, 255, 0.2) !important;
        border-radius: 16px !important;
        padding: 1.5rem;
    }
    
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: #0f172a !important;
        color: #e2e8f0 !important;
        border: 1px solid rgba(0, 212, 255, 0.3) !important;
        border-radius: 10px !important;
    }
    
    .stSelectbox > div > div {
        background: #0f172a !important;
        border: 1px solid rgba(0, 212, 255, 0.3) !important;
        border-radius: 10px !important;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #00d4ff, #0099cc) !important;
        color: #000 !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
    }
    
    .stDownloadButton > button {
        background: linear-gradient(135deg, #10b981, #059669) !important;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        background: #1e293b;
        padding: 10px;
        border-radius: 12px;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #94a3b8;
        padding: 10px 20px;
    }
    
    .stTabs [aria-selected="true"] {
        background: #00d4ff !important;
        color: #000 !important;
        border-radius: 8px;
    }
    
    h1, h2, h3, h4, p, span, label {
        color: #e2e8f0 !important;
    }
    
    [data-testid="stMetricValue"] { color: #00d4ff !important; }
    
    hr { background: rgba(0, 212, 255, 0.2); height: 1px; border: none; }
</style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def get_user_hash(api_key):
    return hashlib.sha256(api_key.encode()).hexdigest()[:32]

def force_memory_cleanup():
    gc.collect()

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
        "Chinese (Xiaoxiao)": "zh-CN-XiaoxiaoNeural",
        "Japanese (Nanami)": "ja-JP-NanamiNeural",
        "Korean (SunHi)": "ko-KR-SunHiNeural",
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

def save_uploaded_file_chunked(uploaded_file, progress_placeholder=None):
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
                if attempt < 2:
                    st.warning(f"Rate limited. Waiting {10*(2**attempt)}s...")
                    time.sleep(10 * (2 ** attempt))
                else: return None, "Rate limit exceeded"
            else: return None, str(e)
    return None, "Max retries exceeded"

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

# ========================================
# MAIN APP
# ========================================

st.title("AI Studio Pro")
st.caption("Video Recap, Translation, Thumbnail & More")

# --- API KEY & MODEL ---
with st.container(border=True):
    st.subheader("Settings")
    
    api_key = st.text_input("Google API Key", type="password", placeholder="Enter API Key...")
    
    global_model = st.selectbox(
        "Default AI Model",
        ["gemini-1.5-flash", "gemini-2.0-flash-exp", "models/gemini-2.5-flash", "models/gemini-2.5-pro", "models/gemini-3-pro-preview"],
        index=0,
        help="Used for Translation, Rewriting"
    )
    
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
        vision_model = st.selectbox("Vision Model", ["models/gemini-2.5-flash", "models/gemini-2.5-pro", "models/gemini-3-pro-preview", "gemini-1.5-flash"], key="vm")
        writer_model = st.selectbox("Writer Model", ["gemini-1.5-flash", "gemini-2.0-flash-exp", "models/gemini-2.5-flash", "models/gemini-2.5-pro", "models/gemini-3-pro-preview"], key="wm")
    
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
        languages = {"Burmese": "Burmese", "English": "English", "Thai": "Thai", "Chinese": "Chinese", "Japanese": "Japanese", "Korean": "Korean"}
        target_lang = st.selectbox("Target Language", list(languages.keys()))
        trans_file = st.file_uploader("File", type=["mp3", "mp4", "txt", "srt", "docx"], key="tf")
        
        if st.button("Translate", use_container_width=True):
            if api_key and trans_file:
                ext = trans_file.name.split('.')[-1].lower()
                target = languages[target_lang]
                
                if ext in ['txt', 'srt']:
                    with st.spinner("Translating..."):
                        text = trans_file.getvalue().decode("utf-8")
                        model = genai.GenerativeModel(global_model)
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
                            model = genai.GenerativeModel(global_model)
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
                                model = genai.GenerativeModel(global_model)
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
    st.header("Thumbnail Generator")
    
    with st.container(border=True):
        ref_images = st.file_uploader("Reference Images (Max 10)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="ri")
        
        if ref_images:
            cols = st.columns(min(len(ref_images), 5))
            for i, img in enumerate(ref_images[:10]):
                with cols[i % 5]:
                    st.image(img, width=80)
        
        prompt = st.text_area("Description", height=100, placeholder="Describe the thumbnail...")
        add_text = st.text_input("Text Overlay", placeholder="e.g. EP.1")
        num_imgs = st.selectbox("Count", [1, 2, 3, 4])
        
        # ပြင်ထားသောလိုင်း (key="gen_thumb" ထည့်ထားသည်)
        if st.button("Generate", use_container_width=True, key="gen_thumb"):
            if api_key and prompt:
                st.session_state['generated_images'] = []
                final_prompt = prompt + (f", text: {add_text}" if add_text else "") + ", high quality"
                
                with st.spinner("Generating..."):
                    try:
                        model = genai.GenerativeModel("models/gemini-2.0-flash-exp")
                        
                        for i in range(num_imgs):
                            st.info(f"Image {i+1}/{num_imgs}...")
                            content = [f"Generate image: {final_prompt}"]
                            if ref_images:
                                for ref in ref_images[:3]:
                                    ref.seek(0)
                                    content.append(Image.open(ref))
                            
                            response = model.generate_content(content, request_options={"timeout": 180})
                            
                            if response.candidates:
                                for part in response.candidates[0].content.parts:
                                    if hasattr(part, 'inline_data') and part.inline_data:
                                        st.session_state['generated_images'].append({'data': part.inline_data.data, 'idx': i+1})
                                        break
                            time.sleep(3)
                        
                        if st.session_state['generated_images']:
                            st.success(f"Generated {len(st.session_state['generated_images'])} image(s)")
                    except Exception as e:
                        st.error(str(e))
    
    if st.session_state.get('generated_images'):
        with st.container(border=True):
            st.subheader("Results")
            for img in st.session_state['generated_images']:
                st.image(img['data'], use_container_width=True)
                st.download_button(f"Download {img['idx']}", img['data'], f"thumb_{img['idx']}.png", key=f"dli_{img['idx']}_{time.time()}")

# === TAB 4: REWRITE ===
with tab4:
    st.header("Script Rewriter")
    
    with st.container(border=True):
        style_file = st.file_uploader("Style Reference", type=["txt", "pdf", "docx"], key="rsf")
        original = st.text_area("Original Script", height=250)
        
        if st.button("Rewrite", use_container_width=True):
            if api_key and original:
                style = read_file_content(style_file) if style_file else "Professional tone"
                with st.spinner("Rewriting..."):
                    model = genai.GenerativeModel(global_model)
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
        if not api_key:
            st.warning("Enter API Key to use Notes")
        elif not SUPABASE_AVAILABLE:
            st.error("Supabase not available")
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
        if not EDGE_TTS_AVAILABLE:
            st.error("Edge TTS not available")
        else:
            tts_text = st.text_area("Text", height=200)
            voices = get_voice_list()
            voice = st.selectbox("Voice", list(voices.keys()))
            rate = st.slider("Speed", -50, 50, 0, format="%d%%")
            
            # ပြင်ထားသောလိုင်း (key="gen_tts" ထည့်ထားသည်)
            if st.button("Generate", use_container_width=True, key="gen_tts"):
                if tts_text.strip():
                    with st.spinner("Generating..."):
                        path, err = generate_tts(tts_text, voices[voice], rate)
                        if path and os.path.exists(path):
                            st.session_state['tts_audio'] = path
                            st.success("Done!")
    
    if st.session_state.get('tts_audio') and os.path.exists(st.session_state['tts_audio']):
        with st.container(border=True):
            with open(st.session_state['tts_audio'], 'rb') as f:
                audio = f.read()
            st.audio(audio, format='audio/mp3')
            st.download_button("Download MP3", audio, "audio.mp3", use_container_width=True)

# === TAB 7: EDITOR ===
with tab7:
    st.header("Script Editor")
    
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            script_file = st.file_uploader("Open", type=["txt", "docx", "srt"], key="ef", label_visibility="collapsed")
        with col2:
            # key="clear_editor" ထည့်ထားသည်
            if st.button("Clear", use_container_width=True, key="clear_editor"):
                st.session_state['editor_script'] = ""
                st.rerun()
        with col3:
            save_format = st.selectbox("Format", ["txt", "srt", "md"], label_visibility="collapsed")
        
        if script_file:
            if script_file.name.endswith(('.txt', '.srt')):
                st.session_state['editor_script'] = script_file.getvalue().decode("utf-8")
            elif DOCX_AVAILABLE:
                st.session_state['editor_script'] = read_file_content(script_file) or ""
        
        current = st.session_state.get('editor_script', '')
        new_script = st.text_area("Script", current, height=400, label_visibility="collapsed")
        if new_script != current:
            st.session_state['editor_script'] = new_script
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Words", len(new_script.split()) if new_script else 0)
        with col2:
            st.metric("Chars", len(new_script))
        with col3:
            if new_script:
                st.download_button("Save", new_script, f"script.{save_format}", use_container_width=True)

st.markdown("---")
st.caption("AI Studio Pro v5.1")
