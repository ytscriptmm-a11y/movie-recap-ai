import streamlit as st
import google.generativeai as genai
import time
import os
import tempfile

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Movie Recap AI Pro",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS (DARK THEME & STYLING) ---
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161B22;
        border-right: 1px solid #30363D;
    }
    /* Headers */
    h1, h2, h3 {
        color: #58A6FF !important;
        font-family: 'Helvetica Neue', sans-serif;
    }
    /* Buttons */
    .stButton>button {
        background-color: #238636;
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: bold;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #2EA043;
        box-shadow: 0 0 10px #2EA043;
    }
    /* Text Inputs */
    .stTextInput>div>div>input {
        background-color: #0D1117;
        color: white;
        border: 1px solid #30363D;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR: CONFIGURATION ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2503/2503508.png", width=50)
    st.title("⚙️ Settings")
    
    # API Key
    api_key = st.text_input("🔑 Google API Key", type="password", placeholder="Enter Key here...")
    
    st.markdown("---")
    
    # Upload Writing Style
    st.subheader("📝 Writing Style (Optional)")
    style_file = st.file_uploader(
        "Upload a sample script (.txt) to mimic your style:", 
        type=["txt"]
    )
    
    st.info("💡 Tip: Uploading a previous script helps the AI learn your tone!")

# --- MAIN CONTENT ---
st.title("🎬 Movie Recap Generator AI (Pro)")
st.markdown("##### 🚀 ဗီဒီယိုဖိုင်မှ မြန်မာလို Recap Script ရေးသားပေးသောစနစ်")

# --- VIDEO UPLOAD SECTION ---
st.markdown("---")
st.subheader("📂 Upload Movie File")

uploaded_file = st.file_uploader(
    "Choose a video file (.mp4, .mkv, .mov)", 
    type=["mp4", "mkv", "mov", "avi"]
)

# --- FUNCTION TO GENERATE SCRIPT ---
def generate_script(video_path, style_content=None, model_name="models/gemini-3-pro-preview"):
    try:
        if api_key:
            genai.configure(api_key=api_key)
        else:
            st.error("❌ Please enter API Key in the sidebar!")
            return None

        model = genai.GenerativeModel(model_name)
        
        # 1. Upload Video
        with st.spinner("⬆️ Uploading video to Gemini AI... (Relax, this takes time for big files)"):
            video_file = genai.upload_file(path=video_path)
        
        # 2. Wait for Processing
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        while video_file.state.name == "PROCESSING":
            status_text.text("⏳ Google is analyzing the video content (Scene by Scene)...")
            time.sleep(5)
            video_file = genai.get_file(video_file.name)
            progress_bar.progress(50)

        if video_file.state.name == "FAILED":
            st.error("❌ Video processing failed on Google's side.")
            return None

        progress_bar.progress(80)
        status_text.text("✅ Video Ready! Writing Script...")

        # 3. Construct Prompt with Style
        style_instruction = ""
        if style_content:
            style_instruction = f"""
            **STYLE REFERENCE:**
            Below is a sample of the user's writing style. You MUST mimic this exact tone, sentence structure, and vocabulary:
            ---
            {style_content}
            ---
            """

        final_prompt = f"""
        You are an expert Burmese Movie Recap Scriptwriter.
        Your task is to watch the uploaded video and write an **EXTREMELY DETAILED, LONG-FORM** script in **Burmese**.

        {style_instruction}

        **CRITICAL INSTRUCTIONS:**
        1. **NO SKIPPING:** Do NOT skip any scenes. Write scene-by-scene.
        2. **NO SUMMARY:** This is NOT a summary. It is a full narration.
        3. **BURMESE ONLY:** 100% Burmese text. No English.
        4. **LENGTH:** The output must be long enough for a 15-20 minute video.
        5. **EMOTION:** Capture the emotions, dialogues, and atmosphere.

        **Start writing now:**
        """

        # 4. Generate
        response = model.generate_content(
            [video_file, final_prompt],
            request_options={"timeout": 600}
        )
        
        progress_bar.progress(100)
        status_text.text("🎉 Script Generated Successfully!")
        return response.text

    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

# --- GENERATE BUTTON ---
if uploaded_file is not None:
    if st.button("🚀 Generate Detailed Script"):
        # Save video temp
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_vid:
            tmp_vid.write(uploaded_file.getvalue())
            tmp_vid_path = tmp_vid.name

        # Read Style file if uploaded
        style_text = None
        if style_file is not None:
            style_text = style_file.getvalue().decode("utf-8")

        # Run Generation
        script_result = generate_script(tmp_vid_path, style_text)

        # Show Result
        if script_result:
            st.markdown("### 📝 Generated Script:")
            st.text_area("Copy your script here:", script_result, height=400)
            
            st.download_button(
                label="📥 Download Script (.txt)",
                data=script_result,
                file_name=f"{uploaded_file.name}_recap.txt",
                mime="text/plain"
            )
        
        os.remove(tmp_vid_path)

elif not uploaded_file:
    st.info("👈 Upload a video to start!")