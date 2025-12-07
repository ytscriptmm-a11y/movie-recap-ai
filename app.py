import streamlit as st
import google.generativeai as genai
import time
import os
import tempfile
from PIL import Image

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Ultimate AI Studio",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- GLASSMORPHISM CSS (THE NEW DESIGN) ---
st.markdown("""
<style>
    /* 1. Main Background (Purple/Blue Gradient) */
    .stApp {
        background: linear-gradient(135deg, #24243e 0%, #302b63 50%, #0f0c29 100%);
        background-attachment: fixed;
        color: #ffffff;
        font-family: 'Inter', sans-serif;
    }

    /* 2. Remove default top bar decoration */
    header {visibility: hidden;}
    
    /* 3. Glass Containers (For Cards & Inputs) */
    /* Targeting st.container(border=True) to look like Glass */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 20px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        padding: 20px;
    }

    /* 4. Inputs (Text Input, Select Box, Text Area) */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stTextArea textarea {
        background-color: rgba(255, 255, 255, 0.1) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 12px !important;
    }
    
    /* Input Focus State */
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #8E2DE2 !important;
        box-shadow: 0 0 10px rgba(142, 45, 226, 0.5);
    }

    /* 5. Buttons */
    .stButton>button {
        background: linear-gradient(to right, #8E2DE2, #4A00E0);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.6rem 1.2rem;
        font-weight: bold;
        transition: transform 0.2s;
        width: 100%;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 0 15px rgba(142, 45, 226, 0.6);
    }

    /* 6. Tabs Design */
    .stTabs [data-baseweb="tab-list"] {
        gap: 15px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(255,255,255,0.05);
        border-radius: 12px;
        color: #ddd;
        border: 1px solid rgba(255,255,255,0.1);
        padding: 10px 20px;
        height: auto;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(to right, #8E2DE2, #4A00E0);
        color: white;
        border: none;
    }

    /* 7. File Uploader */
    [data-testid="stFileUploader"] {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        padding: 10px;
        border: 1px dashed rgba(255, 255, 255, 0.3);
    }

    /* Headings */
    h1, h2, h3 { color: white !important; text-shadow: 0 2px 4px rgba(0,0,0,0.5); }
    p, label { color: #e0e0e0 !important; }
    
</style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def upload_to_gemini(file_path, mime_type=None):
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

# --- MAIN TITLE ---
# Using columns to center title slightly or add logo
c1, c2 = st.columns([0.1, 0.9])
with c1:
    st.markdown("<h1>✨</h1>", unsafe_allow_html=True)
with c2:
    st.markdown("<h1>Ultimate AI Studio</h1>", unsafe_allow_html=True)
st.markdown("<p style='opacity: 0.7; margin-top: -15px;'>Your All-in-One Creative Dashboard</p>", unsafe_allow_html=True)

# --- TOP CONTROL BAR (GLASS CARD) ---
with st.container(border=True):
    col_api, col_model, col_status = st.columns([3, 2, 1])
    
    with col_api:
        api_key = st.text_input("🔑 API Key", type="password", placeholder="Paste Google API Key here...")
        
    with col_model:
        model_name = st.selectbox(
            "🧠 AI Model",
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
        st.write("") # Spacer
        st.write("") # Spacer
        if api_key:
            genai.configure(api_key=api_key)
            st.markdown("✅ **Active**")
        else:
            st.markdown("⚠️ **Offline**")

# --- TABS NAVIGATION ---
st.write("") # Spacer
tab1, tab2, tab3 = st.tabs(["🎬 Movie Recap", "🌍 Translator", "🎨 Thumbnail AI"])

# ==========================================
# TAB 1: MOVIE RECAP GENERATOR
# ==========================================
with tab1:
    st.write("")
    # Layout mimicking the reference: Input on Left, Info/Output on Right
    col_left, col_right = st.columns([1, 1], gap="medium")

    with col_left:
        with st.container(border=True):
            st.subheader("📂 Input Files")
            uploaded_videos = st.file_uploader("Upload Movies", type=["mp4", "mkv", "mov"], accept_multiple_files=True)
            
            st.markdown("---")
            st.markdown("**⚙️ Settings**")
            style_file = st.file_uploader("Writing Style (Optional .txt)", type=["txt"])
            
            if st.button("🚀 Generate Scripts", use_container_width=True):
                if not api_key:
                    st.error("Please enter API Key above.")
                elif not uploaded_videos:
                    st.warning("Please upload video files.")
                else:
                    st.session_state['processing_recap'] = True

    with col_right:
        # Placeholder for output or Instructions
        if 'processing_recap' not in st.session_state:
            with st.container(border=True):
                st.info("💡 **How it works:**")
                st.markdown("""
                1. Upload your movie files on the left.
                2. (Optional) Upload a text file to mimic a writing style.
                3. Click **Generate**.
                4. AI will watch the video and write a full Burmese script.
                """)
                st.image("https://cdn-icons-png.flaticon.com/512/3669/3669493.png", width=100)

        # Processing Logic
        if st.session_state.get('processing_recap'):
            progress_bar = st.progress(0)
            status_box = st.empty()
            
            style_text = ""
            if style_file:
                style_content = style_file.getvalue().decode("utf-8")
                style_text = f"\n\n**STYLE REFERENCE:**\nMimic this style:\n---\n{style_content}\n---\n"

            for i, video_file in enumerate(uploaded_videos):
                status_box.markdown(f"**⏳ Processing:** `{video_file.name}`...")
                
                with st.container(border=True):
                    st.markdown(f"**✅ Result: {video_file.name}**")
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{video_file.name.split('.')[-1]}") as tmp:
                            tmp.write(video_file.getvalue())
                            tmp_path = tmp.name

                        gemini_file = upload_to_gemini(tmp_path)
                        if gemini_file:
                            model = genai.GenerativeModel(model_name)
                            prompt = f"""
                            Professional Burmese Movie Recap Scriptwriter.
                            Watch the video and write an **EXTREMELY DETAILED** movie recap script in **Burmese**.
                            {style_text}
                            Instructions: 1. Scene-by-scene. 2. Full narration. 3. 100% Burmese.
                            """
                            response = model.generate_content([gemini_file, prompt], request_options={"timeout": 600})
                            st.text_area("Script", response.text, height=150, key=f"rec_{i}")
                            st.download_button("📥 Download", response.text, file_name=f"{video_file.name}_recap.txt", key=f"btn_{i}")
                        os.remove(tmp_path)
                    except Exception as e:
                        st.error(f"Error: {e}")
                
                progress_bar.progress((i + 1) / len(uploaded_videos))
            
            status_box.success("🎉 All Completed!")
            st.session_state['processing_recap'] = False

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
                        model = genai.GenerativeModel(model_name)
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
                                model = genai.GenerativeModel(model_name)
                                res = model.generate_content([gemini_file, "Generate full transcript in **Burmese**."], request_options={"timeout": 600})
                                st.text_area("Transcript", res.text, height=300)
                                st.download_button("📥 Download", res.text, file_name=f"{uploaded_file.name}_trans.txt")
                            os.remove(tmp_path)
                except Exception as e: st.error(f"Error: {e}")
                st.session_state['run_translate'] = False
        elif not uploaded_file:
             with st.container(border=True):
                st.info("Waiting for file...")

# ==========================================
# TAB 3: AI THUMBNAIL STUDIO
# ==========================================
with tab3:
    st.write("")
    col_1, col_2 = st.columns([1, 1], gap="medium")
    
    with col_1:
        with st.container(border=True):
            st.subheader("🖼️ Reference Images")
            uploaded_images = st.file_uploader("Upload (Max 4)", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)
            if uploaded_images: 
                st.image([Image.open(i) for i in uploaded_images[:4]], width=100)
                
            st.subheader("✍️ Vision")
            user_prompt = st.text_area("Describe your idea...", placeholder="Action movie style, red background...", height=100)
            
            if st.button("✨ Generate Plan", use_container_width=True):
                st.session_state['run_thumb'] = True

    with col_2:
        if st.session_state.get('run_thumb') and api_key and uploaded_images:
            with st.container(border=True):
                st.subheader("🎨 AI Plan")
                try:
                    input_content = [user_prompt]
                    with st.spinner("Thinking..."):
                        for img_file in uploaded_images[:4]:
                            img = Image.open(img_file)
                            input_content.append(img)
                        
                        model = genai.GenerativeModel(model_name)
                        input_content.append("\n\nAct as a professional YouTube Thumbnail Designer. Output a structured plan: 1. Title, 2. Visual Description, 3. Text Overlay, 4. Detailed Image Generation Prompt.")
                        response = model.generate_content(input_content)
                        
                        st.markdown(response.text)
                        st.download_button("📥 Download Plan", response.text, file_name="thumbnail_plan.txt")
                except Exception as e: 
                    st.error(f"Error: {e}")
                st.session_state['run_thumb'] = False
        else:
             with st.container(border=True):
                st.info("Upload images to see the magic.")

# --- FOOTER ---
st.markdown("<div style='text-align: center; margin-top: 50px; opacity: 0.5; font-size: 0.8rem;'>Glassmorphism Edition • Powered by Gemini</div>", unsafe_allow_html=True)
