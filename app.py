import streamlit as st
import google.generativeai as genai
import time
import os
import tempfile
from PIL import Image

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
    
    /* Image Grid Styling */
    .image-grid { display: flex; gap: 10px; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR: SETTINGS & NAVIGATION ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712035.png", width=60)
    st.title("🎛️ Control Panel")
    
    # Navigation Mode (Updated with Thumbnail Tool)
    app_mode = st.radio("Select Tool:", [
        "🎬 Movie Recap Generator", 
        "🌍 Universal Translator",
        "🎨 AI Thumbnail Studio"
    ])
    
    st.markdown("---")
    
    # API Key Input
    api_key = st.text_input("🔑 Google API Key", type="password", placeholder="Paste your API Key here...")
    
    # Model Selection (Updated)
    st.subheader("🧠 Model Settings")
    model_name = st.selectbox(
        "Select AI Model:",
        [
            "gemini-2.0-flash-exp", # Recommended for Vision
            "gemini-1.5-pro", 
            "models/gemini-3-pro-image-preview", # Requested Model
            "gemini-1.5-flash", 
            "models/gemini-2.5-pro",
            "models/gemini-3-pro-preview"
        ],
        index=0 
    )
    
    st.info(f"💡 **Current Model:** `{model_name}`")

    # Writing Style Upload (Only for Movie Recap)
    if app_mode == "🎬 Movie Recap Generator":
        st.markdown("---")
        st.subheader("📝 Writing Style (Optional)")
        style_file = st.file_uploader("Upload a sample script (.txt) to mimic style:", type=["txt"])

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

# ==========================================
# TOOL 1: MOVIE RECAP GENERATOR (BATCH MODE)
# ==========================================
if app_mode == "🎬 Movie Recap Generator":
    st.title("🎬 Movie Recap Script Generator (Batch Mode)")
    st.markdown(f"##### 🚀 ရုပ်ရှင်ဖိုင်အများကြီးကို တင်လိုက်ပါ၊ AI က တစ်ခုပြီးမှတစ်ခု Script ရေးပေးပါလိမ့်မယ်။")

    uploaded_videos = st.file_uploader("Upload Movie Files (.mp4, .mkv, .mov)", type=["mp4", "mkv", "mov", "avi"], accept_multiple_files=True)

    if uploaded_videos and api_key:
        genai.configure(api_key=api_key)
        st.info(f"📂 Total videos selected: **{len(uploaded_videos)}**")

        if st.button("🚀 Generate All Scripts"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            style_text = ""
            if style_file is not None:
                style_content = style_file.getvalue().decode("utf-8")
                style_text = f"\n\n**WRITING STYLE REFERENCE:**\nPlease mimic the tone and style of the following text:\n---\n{style_content}\n---\n"

            for i, video_file in enumerate(uploaded_videos):
                status_text.text(f"⏳ Processing Video {i+1} of {len(uploaded_videos)}: '{video_file.name}'...")
                
                with st.expander(f"✅ Result: {video_file.name}", expanded=True):
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{video_file.name.split('.')[-1]}") as tmp:
                            tmp.write(video_file.getvalue())
                            tmp_path = tmp.name

                        st.caption("⬆️ Uploading to Gemini...")
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
                            **Start writing now:**
                            """
                            st.caption("🤖 AI is writing the script...")
                            response = model.generate_content([gemini_file, prompt], request_options={"timeout": 600})
                            
                            st.success(f"🎉 Script for '{video_file.name}' Finished!")
                            st.text_area(f"Script ({video_file.name})", response.text, height=300, key=f"text_{i}")
                            st.download_button(f"📥 Download Script", response.text, file_name=f"{video_file.name}_recap.txt", key=f"btn_{i}")
                        else:
                            st.error(f"Failed to process {video_file.name}")
                        os.remove(tmp_path)
                    except Exception as e:
                        st.error(f"Error processing {video_file.name}: {e}")

                progress_bar.progress((i + 1) / len(uploaded_videos))
                time.sleep(1)

            status_text.text("✅ All Videos Processed Successfully!")
            st.balloons()

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
            
            if file_ext in ['txt', 'srt']:
                text_content = uploaded_file.getvalue().decode("utf-8")
                try:
                    model = genai.GenerativeModel(model_name)
                    prompt = f"Translate the following text into **Burmese (Myanmar)**. Return ONLY the translated text.\n\nInput:\n{text_content}"
                    with st.spinner("🤖 Translating Text..."):
                        response = model.generate_content(prompt)
                    st.success("🎉 Translation Complete!")
                    st.text_area("Result:", response.text, height=400)
                    st.download_button("📥 Download Translated File", response.text, file_name=f"translated_{uploaded_file.name}")
                except Exception as e:
                    st.error(f"Text Processing Error: {e}")

            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                
                gemini_file = upload_to_gemini(tmp_path)
                if gemini_file:
                    try:
                        model = genai.GenerativeModel(model_name)
                        prompt = "Listen/Watch. Generate a full transcript in **Burmese (Myanmar)**. If English/Thai -> Translate. If Burmese -> Transcribe."
                        with st.spinner("🤖 Transcribing & Translating..."):
                            response = model.generate_content([gemini_file, prompt], request_options={"timeout": 600})
                        st.success("🎉 Processing Complete!")
                        st.text_area("Result:", response.text, height=600)
                        st.download_button("📥 Download Transcript", response.text, file_name=f"{uploaded_file.name}_transcript.txt")
                    except Exception as e:
                        st.error(f"Generation Error: {e}")
                os.remove(tmp_path)

# ==========================================
# TOOL 3: AI THUMBNAIL STUDIO (NEW FEATURE)
# ==========================================
elif app_mode == "🎨 AI Thumbnail Studio":
    st.title("🎨 AI Thumbnail Studio")
    st.markdown("##### 🖼️ နမူနာပုံ (၄) ပုံတင်ပြီး မိမိလိုချင်တဲ့ Youtube Thumbnail ပုံစံကို ဖန်တီးပါ")

    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.info("အဆင့် (၁) - နမူနာပုံများ တင်ပါ")
        uploaded_images = st.file_uploader("Upload Reference Images (Max 4)", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)
        
    with col2:
        st.info("အဆင့် (၂) - လိုချင်တဲ့ပုံစံ ရေးပါ")
        user_prompt = st.text_area("Thumbnail Prompt (e.g., 'Action movie style, red background, hero holding a sword')", height=150)

    # Preview Images
    if uploaded_images:
        st.subheader("👀 Reference Images Preview")
        cols = st.columns(4)
        for idx, img_file in enumerate(uploaded_images[:4]): # Limit to 4
            with cols[idx]:
                image = Image.open(img_file)
                st.image(image, caption=f"Ref {idx+1}", use_column_width=True)

    if st.button("✨ Generate Thumbnail Concept") and api_key and uploaded_images and user_prompt:
        genai.configure(api_key=api_key)
        
        try:
            # Prepare inputs
            input_content = [user_prompt]
            temp_files = []
            
            with st.spinner("🎨 AI is analyzing your images and designing the thumbnail..."):
                # Upload images to Gemini
                for img_file in uploaded_images[:4]:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                        tmp.write(img_file.getvalue())
                        tmp_path = tmp.name
                        temp_files.append(tmp_path)
                    
                    gemini_img = upload_to_gemini(tmp_path, mime_type="image/jpeg")
                    if gemini_img:
                        input_content.append(gemini_img)

                # Send to Model
                model = genai.GenerativeModel(model_name)
                
                # Specialized Prompt for Thumbnail Generation/Description
                system_instruction = """
                You are an expert YouTube Thumbnail Designer and AI Prompt Engineer.
                
                **TASK:**
                1. Analyze the uploaded reference images (Style, Color Palette, Composition, Font choice).
                2. Combine these styles with the user's specific text request.
                3. Create a **Comprehensive Thumbnail Design Plan**.
                
                **OUTPUT FORMAT:**
                - **Title:** Catchy Title for the Thumbnail.
                - **Visual Description:** Detailed description of the scene, characters, and background.
                - **Text Overlay:** What text should be on the thumbnail?
                - **AI Image Prompt:** A highly detailed prompt (optimized for Midjourney/Stable Diffusion) to generate this exact image.
                """
                
                input_content.append(system_instruction)
                
                response = model.generate_content(input_content)
                
                # Cleanup
                for path in temp_files:
                    os.remove(path)
                
                st.success("✨ Thumbnail Design Generated!")
                st.markdown("### 🎨 AI Design Recommendation")
                st.write(response.text)
                
                st.download_button("📥 Download Design Plan", response.text, file_name="thumbnail_plan.txt")

        except Exception as e:
            st.error(f"Error: {e}")

elif not api_key:
    st.warning("⚠️ Please enter your API Key in the sidebar to start!")

