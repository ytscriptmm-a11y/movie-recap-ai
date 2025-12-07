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

# --- LIBRARY IMPORTS WITH GRACEFUL FALLBACK ---
PDF_AVAILABLE = True
DOCX_AVAILABLE = True

try:
    import PyPDF2
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document
except ImportError:
    DOCX_AVAILABLE = False

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Ultimate AI Studio",
    page_icon="✨",
    layout="centered",  # Changed from wide to centered for narrower layout
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
        'custom_prompt': ""
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- PROFESSIONAL DARK THEME CSS ---
st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Main App Background */
    .stApp {
        background: linear-gradient(180deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
        background-attachment: fixed;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Hide Streamlit Header */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Main Container - Narrower */
    .main .block-container {
        max-width: 1000px !important;
        padding: 2rem 1rem !important;
    }
    
    /* Card Styling */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        background: linear-gradient(145deg, rgba(30, 30, 50, 0.9), rgba(20, 20, 35, 0.95)) !important;
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05);
        padding: 1.5rem;
    }
    
    /* Input Fields */
    .stTextInput input, .stTextArea textarea {
        background: rgba(255, 255, 255, 0.03) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        padding: 12px 16px !important;
        font-size: 14px !important;
        transition: all 0.3s ease;
    }
    
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: rgba(139, 92, 246, 0.5) !important;
        box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1) !important;
    }
    
    /* Select Box */
    .stSelectbox div[data-baseweb="select"] > div {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        color: white !important;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #8B5CF6 0%, #6366F1 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        font-size: 14px;
        letter-spacing: 0.3px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4);
    }
    
    /* Download Button */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%) !important;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(0, 0, 0, 0.2);
        padding: 8px;
        border-radius: 12px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        color: rgba(255, 255, 255, 0.6);
        border: none;
        padding: 10px 20px;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        color: rgba(255, 255, 255, 0.9);
        background: rgba(255, 255, 255, 0.05);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #8B5CF6 0%, #6366F1 100%) !important;
        color: white !important;
    }
    
    /* File Uploader */
    [data-testid="stFileUploader"] {
        background: rgba(255, 255, 255, 0.02);
        border-radius: 12px;
        padding: 16px;
        border: 2px dashed rgba(139, 92, 246, 0.3);
        transition: all 0.3s ease;
    }
    
    [data-testid="stFileUploader"]:hover {
        border-color: rgba(139, 92, 246, 0.5);
        background: rgba(139, 92, 246, 0.05);
    }
    
    /* Typography */
    h1 {
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 2rem !important;
        letter-spacing: -0.5px;
    }
    
    h2, h3 {
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    
    p, label, .stMarkdown {
        color: rgba(255, 255, 255, 0.8) !important;
    }
    
    /* Queue Items */
    .queue-item {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 10px;
        padding: 12px 16px;
        margin: 8px 0;
        transition: all 0.3s ease;
    }
    
    .queue-item:hover {
        background: rgba(255, 255, 255, 0.05);
    }
    
    .queue-item.processing {
        background: rgba(139, 92, 246, 0.1);
        border: 1px solid rgba(139, 92, 246, 0.3);
    }
    
    .queue-item.completed {
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    .queue-item.failed {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    
    /* Info/Success/Warning/Error boxes */
    .stAlert {
        border-radius: 10px !important;
    }
    
    /* Progress Bar */
    .stProgress > div > div {
        background: linear-gradient(90deg, #8B5CF6, #6366F1) !important;
        border-radius: 10px;
    }
    
    /* Radio Buttons */
    .stRadio > div {
        gap: 12px;
    }
    
    /* Metric */
    [data-testid="stMetricValue"] {
        color: #8B5CF6 !important;
        font-weight: 700 !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(255, 255, 255, 0.03) !important;
        border-radius: 10px !important;
    }
    
    /* Custom Title Styling */
    .main-title {
        text-align: center;
        padding: 1rem 0 0.5rem 0;
    }
    
    .main-title h1 {
        background: linear-gradient(135deg, #8B5CF6, #EC4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.5rem !important;
        margin-bottom: 0.25rem;
    }
    
    .main-title p {
        color: rgba(255, 255, 255, 0.5) !important;
        font-size: 0.95rem;
    }
    
    /* Divider */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
        margin: 1.5rem 0;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(0, 0, 0, 0.2);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: rgba(139, 92, 246, 0.5);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(139, 92, 246, 0.7);
    }
</style>
""", unsafe_allow_html=True)

# --- RETRY DECORATOR FOR API CALLS ---
def retry_with_backoff(func, max_retries=3, base_delay=2):
    """Retry function with exponential backoff for rate limiting"""
    def wrapper(*args, **kwargs):
        last_exception = None
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                error_str = str(e).lower()
                
                # Check if it's a rate limit error
                if 'rate' in error_str or 'quota' in error_str or '429' in error_str:
                    delay = base_delay * (2 ** attempt)
                    st.warning(f"⏳ Rate limited. Retrying in {delay}s... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    # For other errors, raise immediately
                    raise e
        
        # If all retries failed
        raise last_exception
    return wrapper

# --- HELPER FUNCTIONS ---
def convert_google_drive_link(url):
    """Convert Google Drive sharing link to direct download link"""
    try:
        if 'drive.google.com' in url:
            if '/file/d/' in url:
                file_id = url.split('/file/d/')[1].split('/')[0]
            elif 'id=' in url:
                file_id = url.split('id=')[1].split('&')[0]
            else:
                return None
            return f"https://drive.google.com/uc?export=download&id={file_id}"
        return url
    except Exception:
        return None

def download_video_from_url(url, progress_callback=None):
    """Download video from URL to temp file with progress tracking"""
    try:
        download_url = convert_google_drive_link(url)
        if not download_url:
            return None, "Invalid URL format"
        
        session = requests.Session()
        
        # First request to get file info and handle confirmation
        response = session.get(download_url, stream=True, timeout=60)
        
        # Handle Google Drive virus scan warning for large files
        if 'text/html' in response.headers.get('content-type', ''):
            # Look for confirmation token in cookies or response
            for key, value in response.cookies.items():
                if key.startswith('download_warning'):
                    params = {'confirm': value}
                    response = session.get(download_url, params=params, stream=True, timeout=300)
                    break
            else:
                # Try with confirm=t parameter
                if 'confirm=' not in download_url:
                    confirm_url = download_url + "&confirm=t"
                    response = session.get(confirm_url, stream=True, timeout=300)
        
        if response.status_code != 200:
            return None, f"Download failed with status {response.status_code}"
        
        # Get file size if available
        total_size = int(response.headers.get('content-length', 0))
        
        # Determine file extension
        file_ext = "mp4"
        if 'content-disposition' in response.headers:
            cd = response.headers['content-disposition']
            if 'filename=' in cd:
                filename = cd.split('filename=')[-1].strip('"\'')
                file_ext = filename.split('.')[-1] if '.' in filename else 'mp4'
        
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}")
        
        downloaded = 0
        chunk_size = 8192
        
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                tmp_file.write(chunk)
                downloaded += len(chunk)
                
                if progress_callback and total_size > 0:
                    progress_callback(downloaded / total_size)
        
        tmp_file.close()
        
        # Verify file is not empty or HTML error page
        file_size = os.path.getsize(tmp_file.name)
        if file_size < 1000:  # Less than 1KB probably means error
            with open(tmp_file.name, 'rb') as f:
                content_start = f.read(100)
                if b'<!DOCTYPE' in content_start or b'<html' in content_start:
                    os.remove(tmp_file.name)
                    return None, "Google Drive returned an error page. Please ensure the file is shared publicly."
        
        return tmp_file.name, None
        
    except requests.Timeout:
        return None, "Download timed out. Please try again."
    except Exception as e:
        return None, str(e)

def upload_to_gemini(file_path, mime_type=None, progress_placeholder=None):
    """Upload file to Gemini with status updates"""
    try:
        if progress_placeholder:
            progress_placeholder.info("📤 Uploading to Gemini...")
        
        file = genai.upload_file(file_path, mime_type=mime_type)
        
        # Wait for processing with status updates
        wait_count = 0
        while file.state.name == "PROCESSING":
            wait_count += 1
            if progress_placeholder:
                progress_placeholder.info(f"⏳ Processing file... ({wait_count * 2}s)")
            time.sleep(2)
            file = genai.get_file(file.name)
            
            # Timeout after 10 minutes
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
    """Reads content from txt, pdf, or docx files with availability checks"""
    try:
        file_type = uploaded_file.type
        
        if file_type == "text/plain":
            return uploaded_file.getvalue().decode("utf-8")
        
        elif file_type == "application/pdf":
            if not PDF_AVAILABLE:
                st.error("⚠️ PyPDF2 library not installed. Cannot read PDF files.")
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
                st.error("⚠️ python-docx library not installed. Cannot read DOCX files.")
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

def call_gemini_api(model, content, timeout=600):
    """Call Gemini API with retry logic for rate limiting"""
    max_retries = 3
    base_delay = 5
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(content, request_options={"timeout": timeout})
            return response
        except Exception as e:
            error_str = str(e).lower()
            
            # Check if it's a rate limit error
            if 'rate' in error_str or 'quota' in error_str or '429' in error_str or 'resource' in error_str:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    st.warning(f"⏳ API rate limited. Waiting {delay}s before retry... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    raise Exception(f"Rate limit exceeded after {max_retries} retries. Please wait a few minutes and try again.")
            else:
                raise e
    
    return None

def process_video_from_path(file_path, video_name, writer_model_name, style_text="", custom_prompt="", status_placeholder=None):
    """Process video from local file path with progress updates"""
    gemini_file = None
    try:
        # Step 1: Upload to Gemini
        if status_placeholder:
            status_placeholder.info("📤 Step 1/3: Uploading video to Gemini...")
        
        gemini_file = upload_to_gemini(file_path, progress_placeholder=status_placeholder)
        if not gemini_file:
            return None, "Failed to upload to Gemini"
        
        # Step 2: Vision Analysis
        if status_placeholder:
            status_placeholder.info("👀 Step 2/3: AI is analyzing video content...")
        
        vision_model = genai.GenerativeModel("models/gemini-2.5-pro")
        vision_prompt = """
        Watch this video carefully. 
        Generate a highly detailed, chronological scene-by-scene description.
        Include dialogue summaries, visual details, emotions, and actions.
        No creative writing yet, just facts.
        """
        
        vision_response = call_gemini_api(vision_model, [gemini_file, vision_prompt], timeout=600)
        if not vision_response:
            return None, "Vision analysis failed"
        
        video_description = vision_response.text
        
        # Step 3: Script Writing
        if status_placeholder:
            status_placeholder.info("✍️ Step 3/3: Writing Burmese recap script...")
        
        # Build custom instructions section
        custom_instructions = ""
        if custom_prompt:
            custom_instructions = f"\n\n**CUSTOM INSTRUCTIONS FROM USER:**\n{custom_prompt}\n"
        
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
        
        final_response = call_gemini_api(writer_model, writer_prompt, timeout=600)
        if not final_response:
            return None, "Script writing failed"
        
        return final_response.text, None
        
    except Exception as e:
        return None, str(e)
    
    finally:
        # Cleanup Gemini file
        if gemini_file:
            try: 
                genai.delete_file(gemini_file.name)
            except Exception: 
                pass
        gc.collect()

def process_video_from_url(url, video_name, writer_model_name, style_text="", custom_prompt="", status_placeholder=None):
    """Process video from URL with progress updates"""
    tmp_path = None
    try:
        if status_placeholder:
            status_placeholder.info("📥 Downloading from Google Drive...")
        
        # Create progress bar for download
        progress_bar = st.progress(0)
        
        def update_progress(progress):
            progress_bar.progress(progress)
        
        tmp_path, error = download_video_from_url(url, progress_callback=update_progress)
        progress_bar.empty()
        
        if error or not tmp_path:
            return None, error or "Download failed"
        
        if status_placeholder:
            status_placeholder.success("✅ Download complete!")
        
        script, error = process_video_from_path(tmp_path, video_name, writer_model_name, style_text, custom_prompt, status_placeholder)
        return script, error
        
    except Exception as e:
        return None, str(e)
    
    finally:
        cleanup_temp_file(tmp_path)
        gc.collect()

# --- MAIN TITLE ---
st.markdown("""
<div class="main-title">
    <h1>✨ Ultimate AI Studio</h1>
    <p>Your All-in-One Creative Dashboard</p>
</div>
""", unsafe_allow_html=True)

# --- LIBRARY STATUS CHECK ---
if not PDF_AVAILABLE or not DOCX_AVAILABLE:
    missing = []
    if not PDF_AVAILABLE:
        missing.append("PyPDF2")
    if not DOCX_AVAILABLE:
        missing.append("python-docx")
    st.warning(f"⚠️ Optional libraries missing: {', '.join(missing)}. Add them to requirements.txt for full functionality.")

# --- TOP CONTROL BAR ---
with st.container(border=True):
    col_api, col_model = st.columns([2, 1])
    
    with col_api:
        api_key = st.text_input("🔑 Google API Key", type="password", placeholder="Paste your API key here...", label_visibility="collapsed")
        
    with col_model:
        writer_model_name = st.selectbox(
            "Writer Model",
            [
                "gemini-2.0-flash-exp", 
                "gemini-1.5-pro", 
                "models/gemini-2.5-pro",
                "gemini-1.5-flash", 
                "models/gemini-2.5-flash"        
            ],
            label_visibility="collapsed"
        )
    
    # Configure API
    if api_key:
        try:
            genai.configure(api_key=api_key)
        except Exception:
            pass

# --- TABS NAVIGATION ---
st.write("") 
tab1, tab2, tab3, tab4 = st.tabs(["🎬 Movie Recap", "🌍 Translator", "🎨 Thumbnail AI", "✍️ Script Rewriter"])

# ==========================================
# TAB 1: MOVIE RECAP - DUAL INPUT METHOD
# ==========================================
with tab1:
    st.write("")
    col_left, col_right = st.columns([1, 1], gap="medium")

    with col_left:
        with st.container(border=True):
            st.subheader("📂 Add Videos to Queue")
            
            # Method Toggle
            upload_method = st.radio(
                "Choose Input Method:",
                ["📁 Upload Files (Local)", "🔗 Google Drive Links"],
                horizontal=True
            )
            
            st.markdown("---")
            
            # METHOD 1: FILE UPLOAD
            if upload_method == "📁 Upload Files (Local)":
                st.info("📌 Upload up to 10 videos • Drag & drop or click to browse")
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
                        # Limit to 10 total items in queue
                        available_slots = 10 - len(st.session_state['video_queue'])
                        if available_slots <= 0:
                            st.error("Queue is full! Maximum 10 videos.")
                        else:
                            files_to_add = uploaded_videos[:available_slots]
                            added_count = 0
                            
                            for video in files_to_add:
                                try:
                                    # Save to temp file immediately
                                    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{video.name.split('.')[-1]}")
                                    tmp_file.write(video.getvalue())
                                    tmp_file.close()
                                    
                                    st.session_state['video_queue'].append({
                                        'name': video.name,
                                        'source_type': 'file',
                                        'file_path': tmp_file.name,
                                        'url': None,
                                        'status': 'waiting',
                                        'script': None,
                                        'error': None
                                    })
                                    added_count += 1
                                except Exception as e:
                                    st.error(f"Failed to add {video.name}: {e}")
                            
                            if added_count > 0:
                                st.success(f"✅ Added {added_count} file(s) to queue!")
                            if len(uploaded_videos) > available_slots:
                                st.warning(f"⚠️ Only added {available_slots} files. Queue limit is 10.")
                            st.rerun()
            
            # METHOD 2: GOOGLE DRIVE LINKS
            else:
                st.info("📌 Paste Google Drive links (Max 10) • One link per line")
                st.markdown("""
                <small style='opacity: 0.7;'>
                💡 <b>Tip:</b> Make sure files are shared as "Anyone with link can view"
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
                                # Validate link format
                                if 'drive.google.com' not in link:
                                    st.warning(f"⚠️ Skipping invalid link: {link[:50]}...")
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
                            if len(raw_links) > available_slots:
                                st.warning(f"⚠️ Only added {available_slots} links. Queue limit is 10.")
                            st.rerun()
            
            st.markdown("---")
            st.markdown("**⚙️ Settings**")
            
            # Custom Prompt Input
            with st.expander("📝 Custom Instructions (Optional)", expanded=False):
                custom_prompt = st.text_area(
                    "Add your custom instructions here:",
                    value=st.session_state.get('custom_prompt', ''),
                    height=100,
                    placeholder="Example: Focus on romantic scenes, Include character names, Make it more dramatic...",
                    key="custom_prompt_input"
                )
                if custom_prompt:
                    st.session_state['custom_prompt'] = custom_prompt
                    st.caption("✅ Custom instructions will be added to the AI prompt")
            
            # Style File Upload
            style_file = st.file_uploader("📄 Writing Style Reference (Optional)", type=["txt", "pdf", "docx"], key="style_uploader")
            
            # Read style file
            if style_file:
                extracted_style = read_file_content(style_file)
                if extracted_style:
                    style_text = f"\n\n**WRITING STYLE REFERENCE:**\nPlease mimic the tone and style of the following text:\n---\n{extracted_style[:5000]}\n---\n"
                    st.session_state['style_text'] = style_text
                    st.caption(f"✅ Style loaded: {style_file.name}")
            
            st.markdown("---")
            
            # Control Buttons
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
                    # Clean up temp files
                    for item in st.session_state['video_queue']:
                        cleanup_temp_file(item.get('file_path'))
                    
                    st.session_state['video_queue'] = []
                    st.session_state['processing_active'] = False
                    st.session_state['current_index'] = 0
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
                - Click "Upload Files" tab
                - Drag & drop or browse for video files
                - Best for small files (<200MB)
                
                **Method 2: Google Drive Links** 🔗
                - Click "Google Drive Links" tab
                - Upload videos to Google Drive first
                - Share → "Anyone with link can view"
                - Copy links and paste here
                - Best for large files
                """)
            else:
                # Show queue status
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
                
                # Display queue items
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
                    
                    # Show download button for completed items
                    if item['status'] == 'completed' and item['script']:
                        filename = f"{item['name'].rsplit('.', 1)[0]}_recap.txt"
                        st.download_button(
                            f"📥 Download Script #{idx + 1}",
                            item['script'],
                            file_name=filename,
                            key=f"download_{idx}"
                        )
                    
                    # Show error for failed items
                    if item['status'] == 'failed' and item['error']:
                        st.error(f"Error: {item['error'][:200]}")
        
        # Process queue
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
                        
                        # Process based on source type
                        if current_item['source_type'] == 'file':
                            script, error = process_video_from_path(
                                current_item['file_path'],
                                current_item['name'],
                                writer_model_name,
                                style_text,
                                custom_prompt,
                                status_placeholder
                            )
                            
                            # Clean up temp file after processing
                            cleanup_temp_file(current_item['file_path'])
                        
                        else:  # URL
                            script, error = process_video_from_url(
                                current_item['url'],
                                current_item['name'],
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
                        
                        st.session_state['current_index'] += 1
                        time.sleep(2)
                        st.rerun()
            
            else:
                completed_count = sum(1 for v in st.session_state['video_queue'] if v['status'] == 'completed')
                failed_count = sum(1 for v in st.session_state['video_queue'] if v['status'] == 'failed')
                
                st.success(f"🎉 All videos processed! ✅ {completed_count} completed, ❌ {failed_count} failed")
                st.balloons()
                st.session_state['processing_active'] = False

# ==========================================
# TAB 2: UNIVERSAL TRANSLATOR
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
                            res = call_gemini_api(model, f"Translate to **Burmese**. Return ONLY translated text.\nInput:\n{text_content}")
                            if res:
                                st.text_area("Result", res.text, height=300)
                                st.download_button("📥 Download", res.text, file_name=f"trans_{uploaded_file.name}")
                    else:
                        with st.spinner("🎧 Listening & Translating..."):
                            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
                                tmp.write(uploaded_file.getvalue())
                                tmp_path = tmp.name
                            
                            gemini_file = upload_to_gemini(tmp_path)
                            if gemini_file:
                                model = genai.GenerativeModel(writer_model_name)
                                res = call_gemini_api(model, [gemini_file, "Generate full transcript in **Burmese**."], timeout=600)
                                if res:
                                    st.text_area("Transcript", res.text, height=300)
                                    st.download_button("📥 Download", res.text, file_name=f"{uploaded_file.name}_trans.txt")
                                try: 
                                    genai.delete_file(gemini_file.name)
                                except Exception: 
                                    pass
                            
                            cleanup_temp_file(tmp_path)
                            gc.collect()
                            
                except Exception as e: 
                    st.error(f"Error: {e}")
                st.session_state['run_translate'] = False
        else:
            with st.container(border=True):
                st.info("💡 Upload a file and click 'Translate Now' to start.")

# ==========================================
# TAB 3: AI THUMBNAIL STUDIO (GEMINI API)
# ==========================================
with tab3:
    st.write("")
    
    # Initialize thumbnail session states
    if 'generated_images' not in st.session_state:
        st.session_state['generated_images'] = []
    if 'thumb_prompt_to_generate' not in st.session_state:
        st.session_state['thumb_prompt_to_generate'] = None
    
    col_thumb_left, col_thumb_right = st.columns([1, 1], gap="medium")
    
    with col_thumb_left:
        with st.container(border=True):
            st.subheader("🎨 AI Thumbnail Generator")
            st.markdown("<p style='opacity: 0.7;'>Gemini API နဲ့ တိုက်ရိုက် Image Generate လုပ်ပါ</p>", unsafe_allow_html=True)
            
            # Reference image upload (MOVED TO TOP)
            st.markdown("**🖼️ Reference Image (Optional):**")
            ref_image = st.file_uploader(
                "Upload reference image for style guidance",
                type=["png", "jpg", "jpeg", "webp"],
                key="thumb_ref_image"
            )
            
            if ref_image:
                # Show small preview
                col_img_preview, col_img_space = st.columns([1, 2])
                with col_img_preview:
                    st.image(ref_image, caption="Reference", width=150)
            
            st.markdown("---")
            
            # Prompt Templates
            st.markdown("**📝 Quick Templates:**")
            prompt_templates = {
                "✍️ Custom Prompt": "",
                "🎬 Movie Recap Thumbnail": "Create a dramatic YouTube movie recap thumbnail, 1280x720 pixels, with cinematic dark color grading, showing dramatic scene with emotional expressions, bold eye-catching title text, professional high contrast style",
                "😱 Shocking/Dramatic Style": "Create a YouTube thumbnail with shocked surprised expression style, bright red and yellow accent colors, large bold text with outline, arrow pointing to key element, exaggerated expressions, 1280x720 pixels",
                "🎭 Before/After Comparison": "Create a before and after comparison YouTube thumbnail, split screen design with clear dividing line, contrasting colors for each side, bold BEFORE and AFTER labels, 1280x720 pixels",
                "🔥 Top 10 List Style": "Create a Top 10 list style YouTube thumbnail, large number prominently displayed, grid collage of related images, bright energetic colors, bold sans-serif title, 1280x720 pixels",
                "💡 Tutorial/How-To": "Create a tutorial how-to YouTube thumbnail, clean professional look, step numbers visible, friendly approachable style, light background with accent colors, 1280x720 pixels",
                "🌄 Cinematic Landscape": "Create a cinematic landscape thumbnail with dramatic lighting, golden hour colors, epic wide shot composition, movie poster style, 1280x720 pixels",
                "👤 Portrait Style": "Create a professional portrait style thumbnail with soft lighting, blurred background bokeh effect, centered subject, warm color tones, 1280x720 pixels"
            }
            
            selected_template = st.selectbox(
                "Template ရွေးပါ:",
                list(prompt_templates.keys()),
                key="thumb_template"
            )
            
            # Main prompt input
            default_prompt = prompt_templates[selected_template]
            user_prompt = st.text_area(
                "🖼️ Image Prompt:",
                value=default_prompt,
                height=150,
                placeholder="Describe the thumbnail you want to generate...\nExample: Create a dramatic movie recap thumbnail with dark cinematic colors, showing an emotional scene...",
                key="thumb_prompt_input"
            )
            
            # Additional customization
            st.markdown("**⚙️ Customization:**")
            col_opt1, col_opt2 = st.columns(2)
            
            with col_opt1:
                add_text = st.text_input(
                    "Text on Image (Optional):",
                    placeholder="e.g., EP.1, PART 2, မြန်မာစာ",
                    key="thumb_text"
                )
            
            with col_opt2:
                num_images = st.selectbox(
                    "Number of Images:",
                    [1, 2, 3, 4],
                    index=0,
                    key="thumb_num"
                )
            
            # Style modifiers
            style_options = st.multiselect(
                "Style Modifiers:",
                ["Cinematic", "Dramatic Lighting", "High Contrast", "Vibrant Colors", "Dark Mood", "Professional", "YouTube Style", "4K Quality"],
                default=["YouTube Style", "High Contrast"],
                key="thumb_styles"
            )
            
            st.markdown("---")
            
            # Model Selection - Only Gemini 3 Pro since it works well
            st.markdown("**🤖 Image Generation Model:**")
            st.success("🎯 Using Gemini 3 Pro - မြန်မာဘာသာ caption နဲ့ text overlay ထည့်ရေးပေးနိုင်တယ်။")
            
            # Hidden variable for compatibility
            image_model_choice = "🎯 Gemini 3 Pro (Myanmar Text Support)"
            
            st.markdown("---")
            
            # Generate button
            generate_clicked = st.button("🚀 Generate Thumbnail", use_container_width=True)
    
    with col_thumb_right:
        with st.container(border=True):
            st.subheader("🖼️ Generated Images")
            
            # Process generation when button is clicked
            if generate_clicked:
                if not api_key:
                    st.error("⚠️ Please enter API Key first!")
                elif not user_prompt.strip():
                    st.warning("⚠️ Please enter a prompt!")
                else:
                    # Clear previous images
                    st.session_state['generated_images'] = []
                    
                    # Build final prompt
                    final_prompt = user_prompt.strip()
                    
                    # Add text overlay instruction
                    if add_text:
                        final_prompt += f", with bold text overlay showing '{add_text}'"
                    
                    # Add style modifiers
                    if style_options:
                        final_prompt += f", style: {', '.join(style_options)}"
                    
                    # Always add quality instruction
                    final_prompt += ", high quality, detailed, sharp focus"
                    
                    # Use Gemini 3 Pro for image generation
                    selected_image_model = "models/gemini-3-pro-image-preview"
                    model_name_display = "Gemini 3 Pro"
                    
                    st.info(f"🎨 Using {model_name_display}...")
                    st.markdown(f"**Prompt:** {final_prompt[:200]}...")
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    generated_images = []
                    
                    try:
                        generated_images = []
                        
                        # Initialize Gemini 3 Pro Model
                        image_model = genai.GenerativeModel(selected_image_model)
                        
                        for i in range(num_images):
                            try:
                                status_text.info(f"🔄 Generating image {i+1}/{num_images}... Please wait...")
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
                                
                                # Extract image from response
                                image_found = False
                                if response.candidates:
                                    for part in response.candidates[0].content.parts:
                                        if hasattr(part, 'inline_data') and part.inline_data:
                                            image_data = part.inline_data.data
                                            generated_images.append({
                                                'data': image_data,
                                                'mime_type': part.inline_data.mime_type,
                                                'index': i + 1
                                            })
                                            image_found = True
                                            status_text.success(f"✅ Image {i+1} generated!")
                                            break
                                
                                if not image_found:
                                    text_response = ""
                                    if response.candidates:
                                        for part in response.candidates[0].content.parts:
                                            if hasattr(part, 'text') and part.text:
                                                text_response = part.text[:200]
                                                break
                                    if text_response:
                                        status_text.warning(f"⚠️ Image {i+1}: {text_response}")
                                    else:
                                        status_text.warning(f"⚠️ Image {i+1}: No image generated.")
                                
                                # Small delay between generations
                                if i < num_images - 1:
                                    time.sleep(2)
                                    
                            except Exception as e:
                                error_msg = str(e)
                                status_text.error(f"⚠️ Image {i+1} failed: {error_msg[:150]}")
                                st.error(f"Full error: {error_msg}")
                                continue
                        
                        progress_bar.progress(1.0)
                        
                        # Save to session state
                        st.session_state['generated_images'] = generated_images
                        
                        if generated_images:
                            status_text.success(f"🎉 Done! Generated {len(generated_images)}/{num_images} image(s)")
                        else:
                            status_text.error("❌ No images were generated. Try a different prompt or check your API key.")
                    
                    except Exception as e:
                        st.error(f"❌ Generation Error: {e}")
                        progress_bar.empty()
            
            # Display generated images
            if st.session_state['generated_images']:
                st.markdown("---")
                for idx, img_data in enumerate(st.session_state['generated_images']):
                    st.markdown(f"**Image {img_data['index']}:**")
                    
                    image_bytes = img_data['data']
                    
                    # Display image
                    st.image(image_bytes, use_container_width=True)
                    
                    # Download button
                    file_ext = "png" if "png" in img_data.get('mime_type', 'png') else "jpg"
                    st.download_button(
                        f"📥 Download Image {img_data['index']}",
                        image_bytes,
                        file_name=f"thumbnail_{idx+1}.{file_ext}",
                        mime=img_data.get('mime_type', 'image/png'),
                        key=f"dl_thumb_{idx}_{time.time()}"
                    )
                    
                    st.markdown("---")
                
                # Clear button
                if st.button("🗑️ Clear All Images", use_container_width=True, key="clear_thumb"):
                    st.session_state['generated_images'] = []
                    st.rerun()
            
            elif not generate_clicked:
                st.info("💡 Enter a prompt and click 'Generate Thumbnail' to create images.")
                st.markdown("""
                **Tips for better results:**
                - Be specific about colors, style, and composition
                - Mention "YouTube thumbnail" or "1280x720" for proper sizing
                - Use style modifiers like "cinematic", "dramatic", "professional"
                - Add text overlay using the text input field (မြန်မာစာ supported with Gemini 3 Pro)
                - Upload a reference image for style guidance
                """)
                
                st.markdown("---")
                st.markdown("**Example Prompts:**")
                st.code("Create a dramatic movie recap thumbnail with dark cinematic colors, emotional scene, bold title text, professional YouTube style, 1280x720")
                st.code("Shocked face reaction thumbnail, bright red yellow colors, large bold text, arrow pointing, exaggerated expression, YouTube style")

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
                            else:
                                st.warning("Could not read style file. Using default.")

                    with st.spinner("🤖 Rewriting... (Keeping 100% Content, Changing Style)"):
                        rewrite_model = genai.GenerativeModel(writer_model_name)
                        
                        rewrite_prompt = f"""
                        You are an expert Script Editor and Ghostwriter.
                        
                        **YOUR TASK:**
                        Rewrite the following "ORIGINAL SCRIPT" using the "TARGET WRITING STYLE".
                        
                        **CRITICAL RULES (MUST FOLLOW):**
                        1. **NO SUMMARIZATION:** You must NOT summarize. Every single scene, dialogue, and detail from the original script must be present.
                        2. **100% CONTENT PRESERVATION:** Do not remove any information. Just change the *way* it is written (word choice, sentence structure, flow).
                        3. **MATCH STYLE:** Strictly mimic the tone, vocabulary, and rhythm of the provided style sample.
                        4. **OUTPUT LANGUAGE:** Burmese (Myanmar).
                        
                        **TARGET WRITING STYLE REFERENCE:**
                        {style_content_rewrite[:5000]} 
                        
                        **ORIGINAL SCRIPT:**
                        {original_script}
                        """
                        
                        rewrite_response = call_gemini_api(rewrite_model, rewrite_prompt)
                        
                        if rewrite_response:
                            st.success("✅ Rewrite Complete!")
                            st.text_area("Result", rewrite_response.text, height=500)
                            st.download_button("📥 Download Rewritten Script", rewrite_response.text, file_name="rewritten_script.txt")
                        else:
                            st.error("❌ Rewrite failed. Please try again.")
                        
                except Exception as e:
                    st.error(f"Error: {e}")
                
                st.session_state['run_rewrite'] = False
        else:
            with st.container(border=True):
                st.info("💡 Paste a script and upload a style (PDF/Docx/Txt) to rewrite.")

# --- FOOTER ---
st.markdown("""
<div style='text-align: center; margin-top: 3rem; padding: 1.5rem 0; border-top: 1px solid rgba(255,255,255,0.05);'>
    <p style='color: rgba(255,255,255,0.4) !important; font-size: 0.85rem; margin: 0;'>
        ✨ Ultimate AI Studio • Powered by Google Gemini
    </p>
</div>
""", unsafe_allow_html=True)
