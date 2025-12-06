import streamlit as st
import google.generativeai as genai
import time
import os
import tempfile

# --- PAGE CONFIGURATION (Dark Theme & Icon) ---
st.set_page_config(
    page_title="🎬 Movie Recap AI Studio",
    page_icon="🎥",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS (Styling) ---
st.markdown("""
<style>
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    .stButton>button {
        background-color: #E50914; /* Netflix Red */
        color: white;
        border-radius: 8px;
        font-weight: bold;
    }
    h1 {
        color: #E50914;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR CONFIG ---
with st.sidebar:
    st.title("⚙️ Settings")
    api_key = st.text_input("🔑 Google API Key", type="password", placeholder="Paste your API Key here...")
    
    # Model Selection (Flexible)
    model_name = st.selectbox(
        "🧠 Select Model:",
        ["gemini-1.5-pro", "gemini-1.5-flash", "models/gemini-3-pro-preview", "models/gemini-2.5-pro", "models/gemini-2.0-flash" ]
    )
    
    st.markdown("---")
    st.info("💡 **Pro Tip:** Use '1.5-pro' for better storytelling and '1.5-flash' for speed.")

# --- MAIN APP ---
st.title("🎬 Movie Recap AI Studio")
st.markdown("##### 🚀 ဗီဒီယိုဖိုင်တင်လိုက်ရုံနဲ့ မြန်မာလို Recap Script အလိုအလျောက် ရေးပေးမယ့် စနစ်")

# --- FILE UPLOADER ---
st.markdown("---")
uploaded_file = st.file_uploader("📂 Upload Video File (.mp4, .mkv, .mov)", type=["mp4", "mkv", "mov", "avi"])

# --- GENERATE FUNCTION ---
def generate_recap(video_path, api_key, model_name):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        # 1. Upload
        with st.spinner("⬆️ Uploading video to Gemini AI... (Large files take time)"):
            video_file = genai.upload_file(path=video_path)
            
        # 2. Processing
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        while video_file.state.name == "PROCESSING":
            status_text.text("⏳ Google is analyzing the video content...")
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


        # 4. Generate Content
        response = model.generate_content(
            [video_file, prompt],
            request_options={"timeout": 600}
        )
        
        progress_bar.progress(100)
        status_text.text("🎉 Script Generated Successfully!")
        return response.text

    except Exception as e:
        st.error(f"Error: {e}")
        return None

# --- ACTION BUTTON ---
if uploaded_file and api_key:
    if st.button("🚀 Generate Script (စတင်ရေးသားပါ)"):
        # Save temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
            
        result = generate_recap(tmp_path, api_key, model_name)
        
        if result:
            st.markdown("### 📝 Generated Script:")
            st.text_area("Your Script:", result, height=400)
            
            st.download_button(
                label="📥 Download Script (.txt)",
                data=result,
                file_name=f"{uploaded_file.name}_recap.txt",
                mime="text/plain"
            )
            
        os.remove(tmp_path)

elif uploaded_file and not api_key:
    st.warning("⚠️ Please enter your Google API Key in the sidebar.")
