import streamlit as st
import google.generativeai as genai
import time
import os
import tempfile
from PIL import Image

# --- PAGE CONFIGURATION (MUST BE FIRST) ---
st.set_page_config(
    page_title="Ultimate AI Studio",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- PRO CUSTOM CSS (Dark & Modern) ---
st.markdown("""
<style>
    /* Main Background & Text */
    .stApp {
        background-color: #0E1117;
        color: #E0E0E0;
    }
    
    /* Headings */
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        color: #FFFFFF !important;
    }
    h1 { background: -webkit-linear-gradient(45deg, #4facfe, #00f2fe); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #1F2937;
        border-radius: 10px 10px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
        color: #A0AEC0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0E1117;
        color: #38BDF8;
        border-top: 2px solid #38BDF8;
    }

    /* Buttons */
    .stButton>button {
        background: linear-gradient(90deg, #3B82F6 0%, #2563EB 100%);
        color: white;
        border: none;
        padding: 0.6rem 1.2rem;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
        width: 100%;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
    }

    /* Input Fields */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #1F2937;
        color: #F3F4F6;
        border: 1px solid #374151;
        border-radius: 8px;
    }
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #38BDF8;
        box-shadow: 0 0 0 1px #38BDF8;
    }

    /* Expanders & Cards */
    .streamlit-expanderHeader {
        background-color: #1F2937;
        border-radius: 8px;
        color: #F3F4F6;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #374151;
    }
</style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def upload_to_gemini(file_path, mime_type=None):
    """Uploads media file to Google AI Studio"""
    try:
        file = genai.upload_file(file_path, mime_type=mime_type)
        while file.state.name == "PROCESSING":
            time.sleep(1)
            file = genai.get_file(file.name)
        if file.state.name == "FAILED":
            return None
        return file
    except Exception as e:
        st.error(f"Upload Error: {e}")
        return None

# --- SIDEBAR: GLOBAL SETTINGS ---
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    st.info("Configure your AI settings here. These apply to all tools.")
    
    # API Key Input
    api_key = st.text_input("🔑 Google API Key", type="password", placeholder="Enter API Key...")
    if api_key:
        genai.configure(api_key=api_key)
        st.caption("✅ API Key Connected")
    else:
        st.caption("⚠️ API Key Required")

    st.markdown("---")
    
    # Model Selection
    st.markdown("#### 🧠 Model Selection")
    model_name = st.selectbox(
        "Choose AI Model:",
        [
            "gemini-2.0-flash-exp", 
            "gemini-1.5-pro", 
            "models/gemini-3-pro-image-preview",
            "gemini-1.5-flash", 
            "models/gemini-2.5-pro",
            "models/gemini-3-pro-preview",
            "models/gemini-2.5-flash"
        ],
        index=0 
    )
    st.caption(f"Active: `{model_name}`")
    st.markdown("---")
    st.markdown("Made with ❤️ by Manoj")

# --- MAIN PAGE HEADER ---
st.title("✨ Ultimate AI Studio")
st.markdown("Your all-in-one workspace for Video Recaps, Translation, and Creative Design.")
st.markdown("---")

# --- TABS NAVIGATION (THE NEW DESIGN) ---
tab1, tab2, tab3 = st.tabs(["🎬 Movie Recap Generator", "🌍 Universal Translator", "🎨 AI Thumbnail Studio"])

# ==========================================
# TAB 1: MOVIE RECAP GENERATOR
# ==========================================
with tab1:
    st.header("🎬 Movie Recap Script Generator")
    st.caption("Upload multiple movie files and let AI write detailed narration scripts scene-by-scene.")

    # Layout: Input on left, settings on right (using columns for pro look)
    col_input, col_settings = st.columns([2, 1])

    with col_settings:
        with st.expander("⚙️ Advanced Settings (Writing Style)", expanded=False):
            st.markdown("Upload a sample text file to mimic a specific narration style.")
            style_file = st.file_uploader("Upload Sample Script (.txt)", type=["txt"])
            style_text = ""
            if style_file:
                style_content = style_file.getvalue().decode("utf-8")
                style_text = f"\n\n**WRITING STYLE REFERENCE:**\nPlease mimic the tone and style of the following text:\n---\n{style_content}\n---\n"
                st.success("Style Loaded!")

    with col_input:
        uploaded_videos = st.file_uploader("Upload Movie Files", type=["mp4", "mkv", "mov", "avi"], accept_multiple_files=True)

    if uploaded_videos:
        st.info(f"📂 **{len(uploaded_videos)}** videos queued for processing.")
        
        if st.button("🚀 Start Batch Generation", type="primary"):
            if not api_key:
                st.error("Please enter your API Key in the sidebar first!")
            else:
                progress_bar = st.progress(0)
                status_box = st.empty()
                
                for i, video_file in enumerate(uploaded_videos):
                    status_box.markdown(f"### ⏳ Processing: `{video_file.name}`...")
                    
                    with st.expander(f"✅ Result: {video_file.name}", expanded=True):
                        try:
                            # Temp file handling
                            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{video_file.name.split('.')[-1]}") as tmp:
                                tmp.write(video_file.getvalue())
                                tmp_path = tmp.name

                            with st.spinner("⬆️ Uploading to Gemini Cloud..."):
                                gemini_file = upload_to_gemini(tmp_path)

                            if gemini_file:
                                model = genai.GenerativeModel(model_name)
                                prompt = f"""
                                You are a professional Burmese Movie Recap Scriptwriter.
                                Watch the video and write an **EXTREMELY DETAILED** movie recap script in **Burmese**.
                                {style_text}
                                **CRITICAL INSTRUCTIONS:**
                                1. **SCENE-BY-SCENE:** Write scene-by-scene. Do NOT skip any scenes.
                                2. **NO SUMMARY:** This is a full narration script, not a summary.
                                3. **BURMESE ONLY:** 100% Burmese text. No English.
                                4. **LENGTH:** Must be suitable for a 15-20 min video.
                                5. **TONE:** Engaging, dramatic, and storytelling style.
                                """
                                
                                with st.spinner("🤖 AI is watching & writing..."):
                                    response = model.generate_content([gemini_file, prompt], request_options={"timeout": 600})
                                
                                st.success(f"🎉 Script Generated!")
                                st.text_area(f"Script Preview", response.text, height=200, key=f"text_{i}")
                                st.download_button(f"📥 Download .txt", response.text, file_name=f"{video_file.name}_recap.txt", key=f"btn_{i}")
                            else:
                                st.error("Upload failed.")
                            
                            os.remove(tmp_path)
                        except Exception as e:
                            st.error(f"Error: {e}")

                    progress_bar.progress((i + 1) / len(uploaded_videos))
                    time.sleep(1)
                
                status_box.success("✅ All batch jobs completed successfully!")
                st.balloons()

# ==========================================
# TAB 2: UNIVERSAL TRANSLATOR
# ==========================================
with tab2:
    st.header("🌍 Universal Translator & Transcriber")
    st.caption("Translate text, audio, or video files directly into Burmese (Myanmar).")

    uploaded_file = st.file_uploader("Upload File (.mp3, .mp4, .txt, .srt)", type=["mp3", "wav", "m4a", "mp4", "mkv", "mov", "txt", "srt"])

    if uploaded_file:
        col_act, col_info = st.columns([1, 2])
        with col_act:
            if st.button("🚀 Process File"):
                if not api_key:
                    st.error("Please enter API Key in Sidebar!")
                else:
                    file_ext = uploaded_file.name.split('.')[-1].lower()
                    
                    # Text Mode
                    if file_ext in ['txt', 'srt']:
                        text_content = uploaded_file.getvalue().decode("utf-8")
                        try:
                            model = genai.GenerativeModel(model_name)
                            prompt = f"Translate to **Burmese**. Return ONLY translated text.\nInput:\n{text_content}"
                            with st.spinner("Processing Text..."):
                                response = model.generate_content(prompt)
                            st.success("Done!")
                            st.text_area("Translation", response.text, height=300)
                            st.download_button("📥 Download", response.text, file_name=f"translated_{uploaded_file.name}")
                        except Exception as e:
                            st.error(f"Error: {e}")
                    
                    # Media Mode
                    else:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
                            tmp.write(uploaded_file.getvalue())
                            tmp_path = tmp.name
                        
                        gemini_file = upload_to_gemini(tmp_path)
                        if gemini_file:
                            try:
                                model = genai.GenerativeModel(model_name)
                                prompt = "Listen/Watch. Generate full transcript in **Burmese**. English/Thai -> Translate. Burmese -> Transcribe."
                                with st.spinner("Analyzing Audio/Video..."):
                                    response = model.generate_content([gemini_file, prompt], request_options={"timeout": 600})
                                st.success("Done!")
                                st.text_area("Transcript", response.text, height=400)
                                st.download_button("📥 Download", response.text, file_name=f"{uploaded_file.name}_transcript.txt")
                            except Exception as e:
                                st.error(f"Error: {e}")
                        os.remove(tmp_path)

# ==========================================
# TAB 3: AI THUMBNAIL STUDIO
# ==========================================
with tab3:
    st.header("🎨 AI Thumbnail Studio")
    st.caption("Generate professional YouTube thumbnail concepts from reference images.")

    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("#### 1. Upload References")
        uploaded_images = st.file_uploader("Upload Images (Max 4)", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)
        if uploaded_images:
            st.image([Image.open(img) for img in uploaded_images[:4]], width=100, caption=[f"Img {i+1}" for i in range(len(uploaded_images[:4]))])

    with c2:
        st.markdown("#### 2. Describe Your Vision")
        user_prompt = st.text_area("Enter Prompt", placeholder="e.g., 'Action movie style, high contrast, hero holding a sword, text: REVENGE'", height=150)
        
        if st.button("✨ Generate Concept"):
            if not api_key or not uploaded_images or not user_prompt:
                st.warning("Please check API Key, Images, and Prompt.")
            else:
                try:
                    input_content = [user_prompt]
                    temp_files = []
                    
                    with st.spinner("🎨 Designing..."):
                        for img_file in uploaded_images[:4]:
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                                tmp.write(img_file.getvalue())
                                temp_files.append(tmp.name)
                            gemini_img = upload_to_gemini(tmp.name, mime_type="image/jpeg")
                            if gemini_img: input_content.append(gemini_img)

                        model = genai.GenerativeModel(model_name)
                        sys_prompt = """
                        You are an expert YouTube Thumbnail Designer.
                        Analyze images + user prompt.
                        Output: Title, Visual Description, Text Overlay, and a Detailed Image Generation Prompt.
                        """
                        input_content.append(sys_prompt)
                        response = model.generate_content(input_content)
                        
                        for p in temp_files: os.remove(p)
                        
                        st.success("Generated!")
                        st.markdown(response.text)
                        st.download_button("📥 Save Plan", response.text, file_name="thumbnail_plan.txt")
                except Exception as e:
                    st.error(f"Error: {e}")

# --- FOOTER ---
st.markdown("---")
st.markdown("<div style='text-align: center; color: #6B7280; font-size: 0.8rem;'>© 2025 Ultimate AI Studio. Powered by Google Gemini.</div>", unsafe_allow_html=True)

