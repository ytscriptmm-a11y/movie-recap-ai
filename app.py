import streamlit as st
import google.generativeai as genai
import streamlit.components.v1 as components
import time
import os
import tempfile
import gc
import io
from PIL import Image

# --- LIBRARY IMPORTS FOR PDF/DOCX ---
try:
    import PyPDF2
    from docx import Document
except ImportError:
    st.error("⚠️ Libraries Missing! Please add 'PyPDF2' and 'python-docx' to your requirements.txt")

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Ultimate AI Studio",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- GLASSMORPHISM CSS ---
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #24243e 0%, #302b63 50%, #0f0c29 100%);
        background-attachment: fixed;
        color: #ffffff;
        font-family: 'Inter', sans-serif;
    }
    header {visibility: hidden;}
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 20px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        padding: 20px;
    }
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stTextArea textarea {
        background-color: rgba(255, 255, 255, 0.1) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 12px !important;
    }
    .stButton>button {
        background: linear-gradient(to right, #8E2DE2, #4A00E0);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.6rem 1.2rem;
        font-weight: bold;
        width: 100%;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 15px; background-color: transparent; }
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(255,255,255,0.05);
        border-radius: 12px;
        color: #ddd;
        border: 1px solid rgba(255,255,255,0.1);
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(to right, #8E2DE2, #4A00E0);
        color: white;
        border: none;
    }
    [data-testid="stFileUploader"] {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        padding: 10px;
        border: 1px dashed rgba(255, 255, 255, 0.3);
    }
    h1, h2, h3 { color: white !important; text-shadow: 0 2px 4px rgba(0,0,0,0.5); }
    p, label { color: #e0e0e0 !important; }
    .queue-item {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 10px;
        margin: 5px 0;
    }
    .queue-item.processing {
        background: rgba(142, 45, 226, 0.2);
        border: 2px solid rgba(142, 45, 226, 0.5);
    }
    .queue-item.completed {
        background: rgba(76, 175, 80, 0.2);
        border: 1px solid rgba(76, 175, 80, 0.5);
    }
</style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def upload_to_gemini(file_path, mime_type=None):
    try:
        file = genai.upload_file(file_path, mime_type=mime_type)
        while file.state.name == "PROCESSING":
            time.sleep(2)
            file = genai.get_file(file.name)
        if file.state.name == "FAILED":
            return None
        return file
    except Exception as e:
        st.error(f"Upload Error: {e}")
        return None

# --- READ TEXT/PDF/DOCX FUNCTION ---
def read_file_content(uploaded_file):
    """Reads content from txt, pdf, or docx files."""
    try:
        if uploaded_file.type == "text/plain":
            return uploaded_file.getvalue().decode("utf-8")
        
        elif uploaded_file.type == "application/pdf":
            reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.getvalue()))
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = Document(io.BytesIO(uploaded_file.getvalue()))
            text = "\n".join([para.text for para in doc.paragraphs])
            return text
        else:
            return None
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return None

# --- PROCESS SINGLE VIDEO FUNCTION ---
def process_single_video(video_bytes, video_name, writer_model_name, style_text=""):
    """Process one video file and return the script"""
    tmp_path = None
    try:
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{video_name.split('.')[-1]}") as tmp:
            tmp.write(video_bytes)
            tmp_path = tmp.name
        
        # Upload to Gemini
        gemini_file = upload_to_gemini(tmp_path)
        
        if not gemini_file:
            return None, "Failed to upload to Gemini"
        
        # Vision Analysis
        vision_model = genai.GenerativeModel("models/gemini-2.5-pro")
        vision_prompt = """
        Watch this video carefully. 
        Generate a highly detailed, chronological scene-by-scene description.
        Include dialogue summaries, visual details, emotions, and actions.
        No creative writing yet, just facts.
        """
        
        vision_response = vision_model.generate_content([gemini_file, vision_prompt], request_options={"timeout": 600})
        video_description = vision_response.text
        
        # Script Writing
        writer_model = genai.GenerativeModel(writer_model_name)
        writer_prompt = f"""
        You are a professional Burmese Movie Recap Scriptwriter.
        Turn this description into an engaging **Burmese Movie Recap Script**.
        
        **INPUT DATA:**
        {video_description}
        
        {style_text}
        
        **INSTRUCTIONS:**
        1. Write in 100% Burmese.
        2. Use a storytelling tone.
        3. Cover the whole story.
        4. Do not summarize too much; keep details.
        5. Scene-by-scene. 
        6. Full narration.                         
        """
        
        final_response = writer_model.generate_content(writer_prompt)
        
        # Cleanup
        try: 
            genai.delete_file(gemini_file.name)
        except: 
            pass
        
        return final_response.text, None
        
    except Exception as e:
        return None, str(e)
    
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass
        gc.collect()

# --- MAIN TITLE ---
c1, c2 = st.columns([0.1, 0.9])
with c1: st.markdown("<h1>✨</h1>", unsafe_allow_html=True)
with c2: st.markdown("<h1>Ultimate AI Studio</h1>", unsafe_allow_html=True)
st.markdown("<p style='opacity: 0.7; margin-top: -15px;'>Your All-in-One Creative Dashboard</p>", unsafe_allow_html=True)

# --- TOP CONTROL BAR ---
with st.container(border=True):
    col_api, col_model, col_status = st.columns([3, 2, 1])
    
    with col_api:
        api_key = st.text_input("🔑 API Key", type="password", placeholder="Paste Google API Key here...")
        
    with col_model:
        writer_model_name = st.selectbox(
            "🧠 Writer Model",
            [
            "gemini-2.0-flash-exp", 
            "gemini-1.5-pro", 
            "models/gemini-3-pro-image-preview",
            "gemini-1.5-flash", 
            "models/gemini-2.5-pro",
            "models/gemini-3-pro-preview",
            "models/gemini-2.5-flash"        
            ]
        )
        
    with col_status:
        st.write("") 
        st.write("") 
        if api_key:
            genai.configure(api_key=api_key)
            st.markdown("✅ **Active**")
        else:
            st.markdown("⚠️ **Offline**")

# --- TABS NAVIGATION ---
st.write("") 
tab1, tab2, tab3, tab4 = st.tabs(["🎬 Movie Recap", "🌍 Translator", "🎨 Thumbnail AI", "✍️ Script Rewriter"])

# ==========================================
# TAB 1: MOVIE RECAP GENERATOR (QUEUE-BASED SYSTEM)
# ==========================================
with tab1:
    st.write("")
    col_left, col_right = st.columns([1, 1], gap="medium")

    # Initialize session states
    if 'video_queue' not in st.session_state:
        st.session_state['video_queue'] = []
    if 'processing_queue' not in st.session_state:
        st.session_state['processing_queue'] = False
    if 'current_processing_index' not in st.session_state:
        st.session_state['current_processing_index'] = 0

    with col_left:
        with st.container(border=True):
            st.subheader("📂 Input Files")
            st.info("📌 Maximum 10 videos • Add files to queue, they'll process one by one")
            
            uploaded_videos = st.file_uploader(
                "Upload Movies (Max 10)", 
                type=["mp4", "mkv", "mov"], 
                accept_multiple_files=True,
                key="video_uploader"
            )
            
            # Add to Queue Button
            if st.button("➕ Add to Queue", use_container_width=True):
                if not uploaded_videos:
                    st.warning("Please select video files first!")
                else:
                    # Add files to queue
                    for video in uploaded_videos:
                        if len(st.session_state['video_queue']) >= 10:
                            st.warning(f"⚠️ Queue is full! Maximum 10 videos. Skipping: {video.name}")
                            break
                        # Store video data
                        st.session_state['video_queue'].append({
                            'name': video.name,
                            'bytes': video.getvalue(),
                            'status': 'waiting',  # waiting, processing, completed, failed
                            'script': None,
                            'error': None
                        })
                    st.success(f"✅ Added {min(len(uploaded_videos), 10)} file(s) to queue!")
                    st.rerun()
            
            st.markdown("---")
            st.markdown("**⚙️ Settings**")
            style_file = st.file_uploader("Writing Style (txt, pdf, docx)", type=["txt", "pdf", "docx"])
            
            # Read style file
            style_text = ""
            if style_file:
                extracted_style = read_file_content(style_file)
                if extracted_style:
                    style_text = f"\n\n**WRITING STYLE REFERENCE:**\nPlease mimic the tone and style of the following text:\n---\n{extracted_style[:5000]}\n---\n"
                    st.session_state['style_text'] = style_text
            
            st.markdown("---")
            
            # Start Processing Button
            if st.button("🚀 Start Processing Queue", use_container_width=True, disabled=len(st.session_state['video_queue']) == 0):
                if not api_key:
                    st.error("Please enter API Key above.")
                else:
                    st.session_state['processing_queue'] = True
                    st.session_state['current_processing_index'] = 0
                    st.rerun()
            
            # Clear Queue Button
            if st.button("🗑️ Clear Queue", use_container_width=True, disabled=len(st.session_state['video_queue']) == 0):
                st.session_state['video_queue'] = []
                st.session_state['processing_queue'] = False
                st.session_state['current_processing_index'] = 0
                st.success("Queue cleared!")
                st.rerun()

    with col_right:
        with st.container(border=True):
            st.subheader("📋 Processing Queue")
            
            if len(st.session_state['video_queue']) == 0:
                st.info("💡 Queue is empty. Add videos to start processing.")
            else:
                # Show queue status
                total = len(st.session_state['video_queue'])
                completed = sum(1 for v in st.session_state['video_queue'] if v['status'] == 'completed')
                failed = sum(1 for v in st.session_state['video_queue'] if v['status'] == 'failed')
                
                st.markdown(f"**Total:** {total} | **Completed:** {completed} | **Failed:** {failed}")
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
                    
                    css_class = item['status']
                    
                    st.markdown(f"""
                    <div class='queue-item {css_class}'>
                        <strong>{status_emoji[item['status']]} {idx + 1}. {item['name']}</strong>
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
                        st.error(f"Error: {item['error']}")
        
        # Process queue
        if st.session_state['processing_queue']:
            current_idx = st.session_state['current_processing_index']
            
            if current_idx < len(st.session_state['video_queue']):
                current_item = st.session_state['video_queue'][current_idx]
                
                if current_item['status'] == 'waiting':
                    # Update status to processing
                    st.session_state['video_queue'][current_idx]['status'] = 'processing'
                    
                    with st.container(border=True):
                        st.markdown(f"### 🔄 Processing: {current_item['name']}")
                        
                        progress_text = st.empty()
                        
                        # Step 1: Upload
                        progress_text.info("📤 Uploading to Gemini...")
                        
                        # Get style text
                        style_text = st.session_state.get('style_text', "")
                        
                        # Step 2: Process
                        progress_text.info("👀 AI is analyzing video...")
                        
                        # Process video
                        script, error = process_single_video(
                            current_item['bytes'],
                            current_item['name'],
                            writer_model_name,
                            style_text
                        )
                        
                        if script:
                            # Success
                            st.session_state['video_queue'][current_idx]['status'] = 'completed'
                            st.session_state['video_queue'][current_idx]['script'] = script
                            progress_text.success(f"✅ Completed: {current_item['name']}")
                            
                            # Auto download
                            filename = f"{current_item['name'].rsplit('.', 1)[0]}_recap.txt"
                            st.download_button(
                                "📥 Download Now",
                                script,
                                file_name=filename,
                                key=f"auto_dl_{current_idx}"
                            )
                        else:
                            # Failed
                            st.session_state['video_queue'][current_idx]['status'] = 'failed'
                            st.session_state['video_queue'][current_idx]['error'] = error
                            progress_text.error(f"❌ Failed: {current_item['name']}")
                        
                        # Move to next
                        st.session_state['current_processing_index'] += 1
                        time.sleep(1)
                        st.rerun()
            
            else:
                # All done
                st.success("🎉 All videos processed!")
                st.balloons()
                st.session_state['processing_queue'] = False

# ==========================================
# TAB 2: UNIVERSAL TRANSLATOR
# ==========================================
with tab2:
    st.write("")
    c1, c2 = st.columns([1, 1], gap="medium")
    
    with c1:
        with st.container(border=True):
            st.subheader("📄 Upload Media")
            uploaded_file = st.file_uploader("File (.mp3, .mp4, .txt, .srt)", type=["mp3", "mp4", "txt", "srt"])
            if st.button("🚀 Translate Now", use_container_width=True):
                st.session_state['run_translate'] = True

    with c2:
        if st.session_state.get('run_translate') and uploaded_file and api_key:
            with st.container(border=True):
                st.subheader("📝 Output")
                try:
                    file_ext = uploaded_file.name.split('.')[-1].lower()
                    if file_ext in ['txt', 'srt']:
                        text_content = uploaded_file.getvalue().decode("utf-8")
                        model = genai.GenerativeModel(writer_model_name)
                        res = model.generate_content(f"Translate to **Burmese**. Return ONLY translated text.\nInput:\n{text_content}")
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
                                res = model.generate_content([gemini_file, "Generate full transcript in **Burmese**."], request_options={"timeout": 600})
                                st.text_area("Transcript", res.text, height=300)
                                st.download_button("📥 Download", res.text, file_name=f"{uploaded_file.name}_trans.txt")
                                try: genai.delete_file(gemini_file.name)
                                except: pass
                            os.remove(tmp_path)
                            gc.collect()
                except Exception as e: st.error(f"Error: {e}")
                st.session_state['run_translate'] = False

# ==========================================
# TAB 3: AI THUMBNAIL STUDIO
# ==========================================
with tab3:
    st.write("")
    with st.container(border=True):
        st.subheader("🎨 Yupp.ai Thumbnail Studio")
        try:
            components.iframe("https://yupp.ai", height=800, scrolling=True)
        except Exception as e:
            st.error("Connection Error.")
            st.link_button("Open yupp.ai", "https://yupp.ai")

# ==========================================
# TAB 4: SCRIPT REWRITER
# ==========================================
with tab4:
    st.write("")
    col_re_1, col_re_2 = st.columns([1, 1], gap="medium")
    
    with col_re_1:
        with st.container(border=True):
            st.subheader("✍️ Style & Source")
            
            rewrite_style_file = st.file_uploader("1. Upload Writing Style", type=["txt", "pdf", "docx"])
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
                        
                        rewrite_response = rewrite_model.generate_content(rewrite_prompt)
                        
                        st.success("✅ Rewrite Complete!")
                        st.text_area("Result", rewrite_response.text, height=500)
                        st.download_button("📥 Download Rewritten Script", rewrite_response.text, file_name="rewritten_script.txt")
                        
                except Exception as e:
                    st.error(f"Error: {e}")
                
                st.session_state['run_rewrite'] = False
        else:
             with st.container(border=True):
                st.info("💡 Paste a script and upload a style (PDF/Docx/Txt) to rewrite.")

# --- FOOTER ---
st.markdown("<div style='text-align: center; margin-top: 50px; opacity: 0.5; font-size: 0.8rem;'>Glassmorphism Edition • Powered by Gemini</div>", unsafe_allow_html=True)
