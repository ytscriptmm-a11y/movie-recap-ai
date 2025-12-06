import streamlit as st
import google.generativeai as genai
import time
import os
import tempfile

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Ultimate AI Studio",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS (Dark Theme & Styling) ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    h1, h2, h3 { color: #58A6FF !important; font-family: sans-serif; }
    .stButton>button { 
        background-color: #238636; 
        color: white; 
        font-weight: bold; 
        border-radius: 8px; 
        border: none;
        padding: 0.5rem 1rem;
    }
    .stButton>button:hover { background-color: #2EA043; box-shadow: 0 0 10px #2EA043; }
    .stSuccess { background-color: #1f2937; color: #4ade80; }
    .stInfo { background-color: #1f2937; color: #60a5fa; }
    .stWarning { background-color: #1f2937; color: #facc15; }
    .stError { background-color: #1f2937; color: #f87171; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR: SETTINGS & NAVIGATION ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712035.png", width=60)
    st.title("🎛️ Control Panel")
    
    # Navigation Mode
    app_mode = st.radio("Select Tool:", ["🎬 Movie Recap Generator", "🌍 Universal Translator"])
    
    st.markdown("---")
    
    # API Key Input
    api_key = st.text_input("🔑 Google API Key", type="password", placeholder="Paste your API Key here...")
    
    # Model Selection (Flexible)
    st.subheader("🧠 Model Settings")
    model_name = st.selectbox(
        "Select AI Model:",
        [
            "gemini-1.5-pro", 
            "gemini-1.5-flash", 
            "gemini-2.0-flash-exp", 
            "models/gemini-3-pro-preview", 
            "models/gemini-2.5-pro"
        ],
        index=0  # Default to 1.5-pro
    )
    
    st.info(f"💡 **Current Model:** `{model_name}`\n\nUse '1.5-pro' for best quality, '1.5-flash' for speed.")

    # Writing Style Upload (Only for Movie Recap)
    if app_mode == "🎬 Movie Recap Generator":
        st.markdown("---")
        st.subheader("📝 Writing Style (Optional)")
        style_file = st.file_uploader("Upload a sample script (.txt) to mimic style:", type=["txt"])

# --- HELPER FUNCTIONS ---

def upload_to_gemini(file_path, mime_type=None):
    """Uploads media file to Google AI Studio"""
    try:
        with st.spinner("⬆️ Uploading to Gemini... (Please wait)"):
            file = genai.upload_file(file_path, mime_type=mime_type)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        while file.state.name == "PROCESSING":
            status_text.text("⏳ Google is processing the file...")
            time.sleep(2)
            file = genai.get_file(file.name)
            progress_bar.progress(50)
            
        if file.state.name == "FAILED":
            st.error("❌ Processing failed on Google's side.")
            return None
            
        progress_bar.progress(100)
        status_text.text("✅ File Ready!")
        time.sleep(1) 
        status_text.empty() 
        progress_bar.empty() 
        return file
    except Exception as e:
        st.error(f"Upload Error: {e}")
        return None

# ==========================================
# TOOL 1: MOVIE RECAP GENERATOR
# ==========================================
if app_mode == "🎬 Movie Recap Generator":
    st.title("🎬 Movie Recap Script Generator")
    st.markdown(f"##### 🚀 ရုပ်ရှင်ဖိုင်တင်လိုက်ရုံနဲ့ မြန်မာလို Recap Script အသေးစိတ် ရေးပေးမယ့် စနစ်")

    uploaded_video = st.file_uploader("Upload Movie File (.mp4, .mkv, .mov)", type=["mp4", "mkv", "mov", "avi"])

    if uploaded_video and api_key:
        genai.configure(api_key=api_key)
        
        if st.button("🚀 Generate Recap Script"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_video.name.split('.')[-1]}") as tmp:
                tmp.write(uploaded_video.getvalue())
                tmp_path = tmp.name
            
            gemini_file = upload_to_gemini(tmp_path)
            
            # Read style file if uploaded
            style_text = ""
            if style_file is not None:
                style_content = style_file.getvalue().decode("utf-8")
                style_text = f"\n\n**WRITING STYLE REFERENCE:**\nPlease mimic the tone and style of the following text:\n---\n{style_content}\n---\n"

            if gemini_file:
                try:
                    model = genai.GenerativeModel(model_name)
                    
                    # Prompt with Style Injection
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

                    **Start writing now:**
                    """
                    
                    with st.spinner("🤖 AI is watching the movie and writing the script..."):
                        response = model.generate_content([gemini_file, prompt], request_options={"timeout": 600})
                        
                    st.success("🎉 Script Generated Successfully!")
                    st.subheader("📝 Generated Script")
                    st.text_area("Result:", response.text, height=600)
                    st.download_button("📥 Download Script (.txt)", response.text, file_name=f"{uploaded_video.name}_recap.txt")
                
                except Exception as e:
                    st.error(f"Generation Error: {e}")
            
            os.remove(tmp_path)

# ==========================================
# TOOL 2: UNIVERSAL TRANSLATOR
# ==========================================
elif app_mode == "🌍 Universal Translator":
    st.title("🌍 Universal Translator & Transcriber")
    st.markdown(f"##### 🔊 Audio/Video/Text ဖိုင်များကို မြန်မာလို ဘာသာပြန်/စာထုတ်ပေးမယ့် စနစ်")
    
    uploaded_file = st.file_uploader("Upload File (.mp3, .mp4, .txt, .srt)", type=["mp3", "wav", "m4a", "mp4", "mkv", "mov", "txt", "srt"])

    if uploaded_file and api_key:
        genai.configure(api_key=api_key)
        
        if st.button("🚀 Process & Translate"):
            file_ext = uploaded_file.name.split('.')[-1].lower()
            
            # --- TEXT/SRT PROCESSING ---
            if file_ext in ['txt', 'srt']:
                text_content = uploaded_file.getvalue().decode("utf-8")
                try:
                    model = genai.GenerativeModel(model_name)
                    
                    prompt = f"""
                    Translate the following text into **Burmese (Myanmar)**.
                    - Keep the exact line count (important for SRT).
                    - Do not translate if it's already Burmese.
                    - Return ONLY the translated text.
                    
                    Input:
                    {text_content}
                    """
                    
                    with st.spinner("🤖 Translating Text..."):
                        response = model.generate_content(prompt)
                        
                    st.success("🎉 Translation Complete!")
                    st.subheader("📝 Translated Text")
                    st.text_area("Result:", response.text, height=400)
                    st.download_button("📥 Download Translated File", response.text, file_name=f"translated_{uploaded_file.name}")
                except Exception as e:
                    st.error(f"Text Processing Error: {e}")

            # --- MEDIA (AUDIO/VIDEO) PROCESSING ---
            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                
                gemini_file = upload_to_gemini(tmp_path)
                
                if gemini_file:
                    try:
                        model = genai.GenerativeModel(model_name)
                        
                        prompt = """
                        Listen to the audio/video.
                        **Task:** Generate a full transcript in **Burmese (Myanmar)**.
                        
                        **LOGIC:**
                        - If audio is English/Thai -> **Translate** to Burmese.
                        - If audio is Burmese -> **Transcribe** exactly as spoken.
                        
                        **CRITICAL:**
                        - Do NOT summarize.
                        - Write sentence by sentence.
                        - Return ONLY the Burmese text.
                        """
                        
                        with st.spinner("🤖 Transcribing & Translating..."):
                            response = model.generate_content([gemini_file, prompt], request_options={"timeout": 600})
                            
                        st.success("🎉 Processing Complete!")
                        st.subheader("📝 Translated Transcript")
                        st.text_area("Result:", response.text, height=600)
                        st.download_button("📥 Download Transcript", response.text, file_name=f"{uploaded_file.name}_transcript.txt")
                    except Exception as e:
                        st.error(f"Generation Error: {e}")
                
                os.remove(tmp_path)

elif not api_key:
    st.warning("⚠️ Please enter your API Key in the sidebar to start!")
