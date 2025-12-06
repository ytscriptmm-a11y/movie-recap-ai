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
    initial_sidebar_state="collapsed" # Sidebar ကို ဖျောက်ထားမည်
)

# --- CUSTOM CSS (Modern Top Bar Style) ---
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    
    /* Top Control Bar Container Styling */
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
    }

    /* Headings */
    h1 {
        background: -webkit-linear-gradient(45deg, #4facfe, #00f2fe);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
    }
    h3 { color: #e6edf3 !important; }
    
    /* Input Fields */
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        background-color: #0d1117;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 6px;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #21262d;
        border-radius: 6px;
        color: #8b949e;
        border: none;
        margin-right: 5px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f6feb;
        color: white;
    }

    /* Buttons */
    .stButton>button {
        background-color: #238636;
        color: white;
        border: 1px solid rgba(27,31,35,0.15);
        border-radius: 6px;
        font-weight: 600;
        width: 100%;
    }
    .stButton>button:hover { background-color: #2ea043; }
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

# --- MAIN HEADER ---
st.title("✨ Ultimate AI Studio")

# --- TOP CONTROL BAR (REPLACED SIDEBAR) ---
# ဒီနေရာမှာ Sidebar အစား Top Bar ဖန်တီးထားပါတယ်
with st.container(border=True):
    col_title, col_api, col_model, col_status = st.columns([1.5, 3, 2, 1])
    
    with col_title:
        st.markdown("### ⚙️ Settings")
        st.caption("v2.1 • Control Panel")
        
    with col_api:
        api_key = st.text_input("🔑 Google API Key", type="password", placeholder="Paste your API Key here...", label_visibility="collapsed")
        
    with col_model:
        model_name = st.selectbox(
            "Select Model",
            [
            "gemini-2.0-flash-exp", 
            "gemini-1.5-pro", 
            "models/gemini-3-pro-image-preview",
            "gemini-1.5-flash", 
            "models/gemini-2.5-pro",
            "models/gemini-3-pro-preview",
            "models/gemini-2.5-flash"
            ],
            label_visibility="collapsed"
        )
        
    with col_status:
        if api_key:
            genai.configure(api_key=api_key)
            st.success("✅ Online")
        else:
            st.warning("⚠️ Offline")

# --- TABS NAVIGATION ---
st.markdown("---")
tab1, tab2, tab3 = st.tabs(["🎬 Movie Recap Generator", "🌍 Universal Translator", "🎨 AI Thumbnail Studio"])

# ==========================================
# TAB 1: MOVIE RECAP GENERATOR
# ==========================================
with tab1:
    st.subheader("🎬 Movie Recap Script Generator")
    
    # Layout: Input (Left) - Settings (Right)
    c1, c2 = st.columns([3, 1])

    with c2:
        with st.expander("📝 Writing Style (Optional)", expanded=True):
            style_file = st.file_uploader("Upload Sample Script", type=["txt"])
            style_text = ""
            if style_file:
                style_content = style_file.getvalue().decode("utf-8")
                style_text = f"\n\n**STYLE REFERENCE:**\nPlease mimic this style:\n---\n{style_content}\n---\n"
                st.info("Style Loaded!")

    with c1:
        uploaded_videos = st.file_uploader("Upload Movie Files", type=["mp4", "mkv", "mov", "avi"], accept_multiple_files=True)

    if uploaded_videos:
        st.info(f"📂 Queue: **{len(uploaded_videos)}** videos.")
        if st.button("🚀 Start Batch Generation", type="primary"):
            if not api_key:
                st.error("⚠️ Please enter API Key in the top bar!")
            else:
                progress_bar = st.progress(0)
                status_box = st.empty()
                
                for i, video_file in enumerate(uploaded_videos):
                    status_box.markdown(f"**⏳ Processing:** `{video_file.name}`...")
                    
                    with st.expander(f"✅ Result: {video_file.name}", expanded=True):
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
                                Instructions:
                                1. Scene-by-scene coverage.
                                2. Full narration, NO summaries.
                                3. 100% Burmese text.
                                """
                                response = model.generate_content([gemini_file, prompt], request_options={"timeout": 600})
                                st.success("Generated!")
                                st.text_area("Script", response.text, height=200, key=f"t_{i}")
                                st.download_button("📥 Save .txt", response.text, file_name=f"{video_file.name}_recap.txt", key=f"b_{i}")
                            os.remove(tmp_path)
                        except Exception as e:
                            st.error(f"Error: {e}")
                    progress_bar.progress((i + 1) / len(uploaded_videos))
                status_box.success("✅ Batch Complete!")
                st.balloons()

# ==========================================
# TAB 2: UNIVERSAL TRANSLATOR
# ==========================================
with tab2:
    st.subheader("🌍 Universal Translator")
    uploaded_file = st.file_uploader("Upload File (.mp3, .mp4, .txt, .srt)", type=["mp3", "mp4", "txt", "srt"])

    if uploaded_file and st.button("🚀 Translate"):
        if not api_key:
            st.error("Check API Key in Top Bar!")
        else:
            file_ext = uploaded_file.name.split('.')[-1].lower()
            if file_ext in ['txt', 'srt']:
                text_content = uploaded_file.getvalue().decode("utf-8")
                try:
                    model = genai.GenerativeModel(model_name)
                    res = model.generate_content(f"Translate to **Burmese**. Return ONLY translated text.\nInput:\n{text_content}")
                    st.text_area("Result", res.text, height=300)
                    st.download_button("📥 Download", res.text, file_name=f"trans_{uploaded_file.name}")
                except Exception as e: st.error(f"Error: {e}")
            else:
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

# ==========================================
# TAB 3: AI THUMBNAIL STUDIO
# ==========================================
with tab3:
    st.subheader("🎨 AI Thumbnail Studio")
    col_1, col_2 = st.columns(2)
    
    with col_1:
        st.info("1. Upload References")
        uploaded_images = st.file_uploader("Images (Max 4)", type=["png", "jpg"], accept_multiple_files=True)
        if uploaded_images: st.image([Image.open(i) for i in uploaded_images[:4]], width=100)

    with col_2:
        st.info("2. Describe Idea")
        user_prompt = st.text_area("Prompt", placeholder="Action style, red background...", height=100)
        
        if st.button("✨ Generate Plan"):
            if not api_key or not uploaded_images:
                st.warning("Needs API Key & Images.")
            else:
                try:
                    content = [user_prompt]
                    temps = []
                    for img in uploaded_images[:4]:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                            tmp.write(img.getvalue())
                            temps.append(tmp.name)
                        g_img = upload_to_gemini(tmp.name, mime_type="image/jpeg")
                        if g_img: content.append(g_img)
                    
                    model = genai.GenerativeModel(model_name)
                    content.append("Analyze images + prompt. Output: Title, Visual Desc, Image Gen Prompt.")
                    res = model.generate_content(content)
                    
                    for p in temps: os.remove(p)
                    st.markdown(res.text)
                    st.download_button("📥 Save Plan", res.text, file_name="thumbnail_plan.txt")
                except Exception as e: st.error(f"Error: {e}")

# --- FOOTER ---
st.markdown("<div style='text-align: center; margin-top: 50px; color: #555;'>Powered by Google Gemini</div>", unsafe_allow_html=True)
