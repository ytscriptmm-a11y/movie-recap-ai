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
    page_title="Ultimate AI Studio - Matrix Edition",
    page_icon="🟢",
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
        'custom_prompt': ""
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- MATRIX THEME CSS ---
st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Main App Background with Matrix Effect */
    .stApp {
        background: #000000;
        background-attachment: fixed;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        position: relative;
        overflow-x: hidden;
    }
    
    /* Matrix Canvas Background */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(180deg, rgba(0, 20, 0, 0.9) 0%, rgba(0, 0, 0, 0.95) 100%);
        z-index: -1;
        pointer-events: none;
    }
    
    /* Matrix Animation */
    @keyframes matrix-fall {
        0% {
            transform: translateY(-100%);
            opacity: 0;
        }
        10% {
            opacity: 1;
        }
        90% {
            opacity: 1;
        }
        100% {
            transform: translateY(100vh);
            opacity: 0;
        }
    }
    
    /* Subtle Matrix Columns */
    .stApp::after {
        content: '01001010 01000001 01001110 01000101 01010100 01001000 01010101 01001110 01000111 00100000 01010000 01001001 01001110 01011001 01000001 01010010 01001100 01000001 01010100 01010011 01000001 01001110 01000111 00100000 01001101 01000001 01001100 01001111 01001110 01000101 00100000 01010000 01001111 01010101 01001110 01000111 01010100 01001000 01001001 01001110 01000111 01011001 01000001 01001110';
        position: fixed;
        top: -50%;
        left: 0;
        width: 100%;
        height: 200%;
        font-family: 'Courier New', monospace;
        font-size: 12px;
        line-height: 1.5;
        color: rgba(0, 255, 65, 0.15);
        white-space: pre-wrap;
        word-wrap: break-word;
        z-index: -1;
        animation: matrix-fall 20s linear infinite;
        text-shadow: 0 0 5px rgba(0, 255, 65, 0.5);
        pointer-events: none;
    }
    
    /* Hide Streamlit Header */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Main Container - 2000px Max Width */
    .main .block-container {
        max-width: 2000px !important;
        padding: 2rem 1rem !important;
    }
    
    /* Card Styling - Matrix Green Theme */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        background: linear-gradient(145deg, rgba(0, 30, 0, 0.85), rgba(0, 15, 0, 0.9)) !important;
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 2px solid rgba(0, 255, 65, 0.3) !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(0, 255, 65, 0.2), 0 0 20px rgba(0, 255, 65, 0.1);
        padding: 1.5rem;
    }
    
    /* Input Fields - Matrix Green */
    .stTextInput input, .stTextArea textarea {
        background: rgba(0, 20, 0, 0.6) !important;
        color: #00ff41 !important;
        border: 2px solid rgba(0, 255, 65, 0.3) !important;
        border-radius: 10px !important;
        padding: 12px 16px !important;
        font-size: 14px !important;
        transition: all 0.3s ease;
    }
    
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: rgba(0, 255, 65, 0.7) !important;
        box-shadow: 0 0 0 3px rgba(0, 255, 65, 0.15), 0 0 10px rgba(0, 255, 65, 0.3) !important;
    }
    
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {
        color: rgba(0, 255, 65, 0.4) !important;
    }
    
    /* Select Box - Matrix Green */
    .stSelectbox div[data-baseweb="select"] > div {
        background: rgba(0, 20, 0, 0.6) !important;
        border: 2px solid rgba(0, 255, 65, 0.3) !important;
        border-radius: 10px !important;
        color: #00ff41 !important;
    }
    
    .stSelectbox div[data-baseweb="select"] > div:hover {
        border-color: rgba(0, 255, 65, 0.6) !important;
        box-shadow: 0 0 10px rgba(0, 255, 65, 0.2);
    }
    
    /* Buttons - Matrix Green */
    .stButton > button {
        background: linear-gradient(135deg, #00ff41 0%, #00cc33 100%);
        color: #000000;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 1.5rem;
        font-weight: 700;
        font-size: 14px;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(0, 255, 65, 0.4), 0 0 15px rgba(0, 255, 65, 0.2);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 255, 65, 0.6), 0 0 25px rgba(0, 255, 65, 0.3);
        background: linear-gradient(135deg, #00ff41 0%, #00dd38 100%);
    }
    
    /* Download Button - Cyan accent */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #00ffff 0%, #00cccc 100%) !important;
        color: #000000 !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 12px rgba(0, 255, 255, 0.4), 0 0 15px rgba(0, 255, 255, 0.2);
    }
    
    .stDownloadButton > button:hover {
        box-shadow: 0 6px 20px rgba(0, 255, 255, 0.6), 0 0 25px rgba(0, 255, 255, 0.3) !important;
        transform: translateY(-2px);
    }
    
    /* Tabs - Matrix Green */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(0, 255, 65, 0.1);
        padding: 8px;
        border-radius: 12px;
        border: 1px solid rgba(0, 255, 65, 0.3);
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        color: rgba(0, 255, 65, 0.7);
        border: 1px solid transparent;
        padding: 10px 20px;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        color: #00ff41;
        background: rgba(0, 255, 65, 0.15);
        border: 1px solid rgba(0, 255, 65, 0.3);
        box-shadow: 0 0 10px rgba(0, 255, 65, 0.2);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #00ff41 0%, #00cc33 100%) !important;
        color: #000000 !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(0, 255, 65, 0.5), 0 0 15px rgba(0, 255, 65, 0.3);
        font-weight: 700;
    }
    
    /* File Uploader - Matrix Green */
    [data-testid="stFileUploader"] {
        background: rgba(0, 255, 65, 0.05);
        border-radius: 12px;
        padding: 16px;
        border: 2px dashed rgba(0, 255, 65, 0.5) !important;
        transition: all 0.3s ease;
    }
    
    [data-testid="stFileUploader"]:hover {
        border-color: rgba(0, 255, 65, 0.8) !important;
        background: rgba(0, 255, 65, 0.1);
        box-shadow: 0 0 20px rgba(0, 255, 65, 0.2);
    }
    
    /* Typography - Matrix Green */
    h1 {
        color: #00ff41 !important;
        font-weight: 700 !important;
        font-size: 2rem !important;
        letter-spacing: -0.5px;
        text-shadow: 0 0 10px rgba(0, 255, 65, 0.5);
    }
    
    h2, h3 {
        color: #00ff41 !important;
        font-weight: 600 !important;
        text-shadow: 0 0 8px rgba(0, 255, 65, 0.3);
    }
    
    p, label, .stMarkdown {
        color: rgba(0, 255, 65, 0.8) !important;
    }
    
    /* Queue Items - Matrix Green */
    .queue-item {
        background: rgba(0, 20, 0, 0.6);
        border: 2px solid rgba(0, 255, 65, 0.25);
        border-radius: 10px;
        padding: 12px 16px;
        margin: 8px 0;
        transition: all 0.3s ease;
    }
    
    .queue-item:hover {
        background: rgba(0, 30, 0, 0.8);
        border-color: rgba(0, 255, 65, 0.5);
        box-shadow: 0 0 15px rgba(0, 255, 65, 0.2);
    }
    
    .queue-item.processing {
        background: rgba(0, 255, 65, 0.15);
        border: 2px solid rgba(0, 255, 65, 0.6);
        box-shadow: 0 0 20px rgba(0, 255, 65, 0.3);
        animation: pulse-green 2s ease-in-out infinite;
    }
    
    @keyframes pulse-green {
        0%, 100% { box-shadow: 0 0 20px rgba(0, 255, 65, 0.3); }
        50% { box-shadow: 0 0 30px rgba(0, 255, 65, 0.5); }
    }
    
    .queue-item.completed {
        background: rgba(0, 255, 255, 0.15);
        border: 2px solid rgba(0, 255, 255, 0.5);
    }
    
    .queue-item.failed {
        background: rgba(255, 0, 0, 0.15);
        border: 2px solid rgba(255, 0, 0, 0.5);
    }
    
    /* Info/Success/Warning/Error boxes */
    .stAlert {
        border-radius: 10px !important;
        border-left: 4px solid rgba(0, 255, 65, 0.8);
    }
    
    /* Progress Bar - Matrix Green */
    .stProgress > div > div {
        background: linear-gradient(90deg, #00ff41, #00ffff) !important;
        border-radius: 10px;
        box-shadow: 0 0 10px rgba(0, 255, 65, 0.5);
    }
    
    /* Radio Buttons */
    .stRadio > div {
        gap: 12px;
    }
    
    .stRadio label {
        color: rgba(0, 255, 65, 0.8) !important;
    }
    
    /* Metric - Matrix Green */
    [data-testid="stMetricValue"] {
        color: #00ff41 !important;
        font-weight: 700 !important;
        text-shadow: 0 0 10px rgba(0, 255, 65, 0.5);
    }
    
    /* Expander - Matrix Green */
    .streamlit-expanderHeader {
        background: rgba(0, 20, 0, 0.5) !important;
        border-radius: 10px !important;
        border: 1px solid rgba(0, 255, 65, 0.3);
    }
    
    .streamlit-expanderHeader:hover {
        background: rgba(0, 30, 0, 0.7) !important;
        box-shadow: 0 0 10px rgba(0, 255, 65, 0.2);
    }
    
    /* Custom Title Styling - Matrix */
    .main-title {
        text-align: center;
        padding: 1rem 0 0.5rem 0;
    }
    
    .main-title h1 {
        background: linear-gradient(135deg, #00ff41, #00ffff, #00ff41);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.8rem !important;
        margin-bottom: 0.25rem;
        text-shadow: none;
        filter: drop-shadow(0 0 20px rgba(0, 255, 65, 0.6));
        animation: glow-pulse 3s ease-in-out infinite;
        font-weight: 900 !important;
    }
    
    @keyframes glow-pulse {
        0%, 100% { filter: drop-shadow(0 0 20px rgba(0, 255, 65, 0.6)); }
        50% { filter: drop-shadow(0 0 30px rgba(0, 255, 65, 0.8)); }
    }
    
    .main-title p {
        color: rgba(0, 255, 65, 0.6) !important;
        font-size: 1rem;
        letter-spacing: 1px;
    }
    
    /* Divider - Matrix Green */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(0, 255, 65, 0.3), transparent);
        margin: 1.5rem 0;
        box-shadow: 0 0 10px rgba(0, 255, 65, 0.2);
    }
    
    /* Scrollbar - Matrix Green */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(0, 0, 0, 0.5);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: rgba(0, 255, 65, 0.5);
        border-radius: 10px;
        box-shadow: 0 0 10px rgba(0, 255, 65, 0.3);
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(0, 255, 65, 0.8);
        box-shadow: 0 0 15px rgba(0, 255, 65, 0.5);
    }
    
    /* Caption text */
    .caption, small {
        color: rgba(0, 255, 65, 0.6) !important;
    }
    
    /* Code blocks */
    code {
        background: rgba(0, 20, 0, 0.8) !important;
        color: #00ff41 !important;
        border: 1px solid rgba(0, 255, 65, 0.3);
        padding: 2px 6px;
        border-radius: 4px;
    }
    
    /* Matrix Digital Rain Effect Enhancement */
    @keyframes flicker {
        0%, 100% { opacity: 0.15; }
        50% { opacity: 0.25; }
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

def process_video_from_url(url, video_name, writer_model_name, style_text="", custom_prompt="",
