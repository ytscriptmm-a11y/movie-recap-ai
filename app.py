import streamlit as st
import google.generativeai as genai
import time
import os
import tempfile
import gc
import io
import hashlib
import asyncio
import struct
import re
import yt_dlp
from PIL import Image
from examples import get_recap_examples

# --- LIBRARY IMPORTS ---
PDF_AVAILABLE, DOCX_AVAILABLE, GDOWN_AVAILABLE, SUPABASE_AVAILABLE, EDGE_TTS_AVAILABLE, GENAI_NEW_AVAILABLE = True, True, True, True, True, True

try: import PyPDF2
except: PDF_AVAILABLE = False
try: from docx import Document
except: DOCX_AVAILABLE = False
try: import gdown
except: GDOWN_AVAILABLE = False
try: from supabase import create_client
except: SUPABASE_AVAILABLE = False
try: import edge_tts
except: EDGE_TTS_AVAILABLE = False
try: from google import genai as genai_new; from google.genai import types
except: GENAI_NEW_AVAILABLE = False

SUPABASE_URL = "https://ohjvgupjocgsirhwuobf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9oanZndXBqb2Nnc2lyaHd1b2JmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU5MzkwMTgsImV4cCI6MjA4MTUxNTAxOH0.oZxQZ6oksjbmEeA_m8c44dG_z5hHLwtgoJssgK2aogI"
supabase = None
if SUPABASE_AVAILABLE:
    try: supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except: SUPABASE_AVAILABLE = False

st.set_page_config(page_title="AI Studio Pro", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Myanmar:wght@400;600&display=swap');
.stApp{background:#0f172a!important;font-family:'Noto Sans Myanmar',sans-serif}
header,#MainMenu,footer{visibility:hidden}
[data-testid="block-container"]{max-width:1000px!important;padding:2rem!important;margin:2rem auto!important;border:2px solid rgba(0,212,255,0.5)!important;border-radius:20px!important;background:#151f32!important}
.stTextInput>div>div>input,.stTextArea>div>div>textarea{background:#0f172a!important;color:#f8fafc!important;border:1px solid rgba(0,212,255,0.6)!important;border-radius:10px!important}
.stButton>button{background:linear-gradient(135deg,#00d4ff,#0099cc)!important;color:#000!important;border:none!important;border-radius:10px!important;font-weight:600!important}
.stDownloadButton>button{background:linear-gradient(135deg,#10b981,#059669)!important;color:#fff!important}
.stTabs [data-baseweb="tab-list"]{background:#1e293b;padding:10px;border-radius:12px}
.stTabs [data-baseweb="tab"]{color:#cbd5e1;padding:10px 20px}
.stTabs [aria-selected="true"]{background:#00d4ff!important;color:#000!important;border-radius:8px}
h1,h2,h3,h4,p,span,label,div[data-testid="stMarkdownContainer"] p{color:#f8fafc!important}
[data-testid="stMetricValue"]{color:#00d4ff!important}
hr{background:rgba(0,212,255,0.5)!important;height:1px;border:none}
div[data-testid="stFileUploader"] section{background:#1e293b!important;border:1px dashed rgba(0,212,255,0.5)!important}
.stSelectbox>div>div{background:#0f172a!important;color:#f8fafc!important;border:1px solid rgba(0,212,255,0.6)!important}
</style>""", unsafe_allow_html=True)

def parse_mime(m):
    b,r=16,24000
    for p in m.split(";"):
        p=p.strip()
        if p.lower().startswith("rate="):r=int(p.split("=")[1])
        elif p.startswith("audio/L"):b=int(p.split("L")[1])
    return b,r

def to_wav(d,m):
    b,r=parse_mime(m)
    h=struct.pack("<4sI4s4sIHHIIHH4sI",b"RIFF",36+len(d),b"WAVE",b"fmt ",16,1,1,r,r*b//8,b//8,b,b"data",len(d))
    return h+d

def get_hash(k): return hashlib.sha256(k.encode()).hexdigest()[:32]
def cleanup(): gc.collect()

def get_text(r):
    try:
        if not r or not r.candidates: return None,"No response"
        parts=r.candidates[0].content.parts if hasattr(r.candidates[0],'content') else []
        t="\n".join([p.text for p in parts if hasattr(p,'text') and p.text])
        return (t,None) if t else (None,"No text")
    except Exception as e: return None,str(e)

def call_api(m,c,to=900):
    for i in range(3):
        try:
            r=m.generate_content(c,request_options={"timeout":to})
            t,e=get_text(r)
            if t: return r,None
            if i<2: time.sleep(10)
        except Exception as e:
            if any(x in str(e).lower() for x in ['rate','quota','429']):
                if i<2: time.sleep(10*(2**i))
                else: return None,"Rate limit"
            else: return None,str(e)
    return None,"Max retries"

def upload_gem(p,s=None):
    try:
        if s: s.info(f"Uploading ({os.path.getsize(p)/(1024*1024):.1f}MB)...")
        f=genai.upload_file(p)
        w=0
        while f.state.name=="PROCESSING":
            w+=1
            if s: s.info(f"Processing...({w*2}s)")
            time.sleep(2)
            f=genai.get_file(f.name)
            if w>300: return None
        return f if f.state.name!="FAILED" else None
    except Exception as e:
        if s: s.error(str(e))
        return None

def save_up(u):
    try:
        ext=u.name.split('.')[-1] if '.' in u.name else 'mp4'
        tmp=tempfile.NamedTemporaryFile(delete=False,suffix=f".{ext}")
        u.seek(0,2);sz=u.tell();u.seek(0)
        prog=st.progress(0);wr=0
        while ch:=u.read(10*1024*1024):
            tmp.write(ch);wr+=len(ch);prog.progress(min(wr/sz,1.0))
        tmp.close();prog.empty()
        return tmp.name,None
    except Exception as e: return None,str(e)

def rm_file(p):
    if p and os.path.exists(p):
        try: os.remove(p)
        except: pass

def read_file(u):
    try:
        t=u.type
        if t=="text/plain": return u.getvalue().decode("utf-8")
        elif t=="application/pdf" and PDF_AVAILABLE: return "\n".join([p.extract_text() or "" for p in PyPDF2.PdfReader(io.BytesIO(u.getvalue())).pages])
        elif "wordprocessingml" in t and DOCX_AVAILABLE: return "\n".join([p.text for p in Document(io.BytesIO(u.getvalue())).paragraphs])
        return None
    except: return None

def get_gid(url):
    try:
        if 'drive.google.com' in url:
            if '/file/d/' in url: return url.split('/file/d/')[1].split('/')[0].split('?')[0]
            elif 'id=' in url: return url.split('id=')[1].split('&')[0]
        return None
    except: return None

def dl_gdrive(url,s=None):
    try:
        fid=get_gid(url)
        if not fid: return None,"Invalid URL"
        if s: s.info("Downloading...")
        tmp=tempfile.NamedTemporaryFile(delete=False,suffix=".mp4").name
        if GDOWN_AVAILABLE and gdown.download(f"https://drive.google.com/uc?id={fid}",tmp,quiet=False,fuzzy=True):
            if os.path.exists(tmp) and os.path.getsize(tmp)>1000: return tmp,None
        return None,"Download failed"
    except Exception as e: return None,str(e)

def download_video_url(url, status=None):
    """YouTube, Facebook, TikTok, Google Drive link download"""
    try:
        if status: status.info("Downloading video...")
        
        # Write cookies from secrets
        try:
            cookies_content = st.secrets["youtube"]["cookies"]
            with open("/tmp/cookies.txt", "w") as f:
                f.write(cookies_content)
        except:
            pass
        
        if 'drive.google.com' in url:
            path, err = dl_gdrive(url, status)
            return path, err
        output_path = f"/tmp/video_{int(time.time())}.mp4"
        ydl_opts = {
    'format': 'best[ext=mp4]/best',
    'outtmpl': output_path,
    'quiet': True,
    'no_warnings': True,
    'socket_timeout': 60,
    'cookiefile': '/tmp/cookies.txt' if os.path.exists('/tmp/cookies.txt') else None,
}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        if os.path.exists(output_path):
            return output_path, None
        else:
            return None, "Download failed"
    except Exception as e:
        return None, str(e)
def process_vid(file_path, video_name, vision_model, writer_model, style="", custom="", status=None):
    gemini_file = None
    try:
        if status: status.info("Step 1/3: Uploading to Gemini...")
        gemini_file = upload_gem(file_path, status)
        if not gemini_file: return None, "Upload failed"
        
        if status: status.info("Step 2/3: AI analyzing video...")
        vision = genai.GenerativeModel(vision_model)
        
        vision_prompt = """
        Watch this video carefully. 
        Generate a highly detailed, chronological scene-by-scene description. (Use a storytelling tone.)
        Include All the dialogue in the movie, visual details, emotions, and actions. (Scene-by-scene)
        No creative writing yet, just facts. Double-check that character names and identities are accurate. 
        Verify the chronological order of the scenes. 
        Ensure strict adherence to the timeline so that earlier and later scenes are not out of sequence.

        """
        
        resp, err = call_api(vision, [gemini_file, vision_prompt], 600)
        if err: return None, f"Analysis failed: {err}"
        video_description, _ = get_text(resp)
        
        time.sleep(5)
        
        if status: status.info("Step 3/3: Writing Burmese recap script...")
        writer = genai.GenerativeModel(writer_model)
        
        custom_instructions = f"\n\n**CUSTOM INSTRUCTIONS:**\n{custom}\n" if custom else ""
        style_text = f"\n\n**WRITING STYLE REFERENCE:**\n{style}\n" if style else ""
        
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
        5. Scene-by-scene.(Use a storytelling tone.) 
        6. Full narration.Double-check that character names and identities are accurate. 
        Verify the chronological order of the scenes. 
        Ensure strict adherence to the timeline so that earlier and later scenes are not out of sequence.
        "Follow these steps for quality control:
        Watch the full video again after writing.
        Verify the script against the video content.
        Make immediate corrections if any errors or gaps are found." 
        """
        
        resp, err = call_api(writer, writer_prompt, 600)
        if err: return None, f"Writing failed: {err}"
        
        text, _ = get_text(resp)
        return text, None
    except Exception as e: return None, str(e)
    finally:
        if gemini_file:
            try: genai.delete_file(gemini_file.name)
            except: pass
        cleanup()

def hash_pw(p): return hashlib.sha256(p.encode()).hexdigest()

def login(e,p):
    if not supabase: return None,"DB Error"
    try:
        r=supabase.table('users').select('*').eq('email',e).eq('password',hash_pw(p)).execute()
        if r.data:
            u=r.data[0]
            return (u,"OK") if u['approved'] else (None,"Pending")
        return None,"Invalid"
    except Exception as ex: return None,str(ex)

def register(e,p):
    if not supabase: return False,"DB Error"
    try:
        if supabase.table('users').select('email').eq('email',e).execute().data: return False,"Email exists"
        supabase.table('users').insert({"email":e,"password":hash_pw(p),"approved":False,"is_admin":False}).execute()
        return True,"Registered! Wait for approval."
    except Exception as ex: return False,str(ex)

def toggle_app(uid,st): 
    if supabase:
        try: supabase.table('users').update({'approved':not st}).eq('id',uid).execute();st.rerun()
        except: pass

def get_notes(h):
    if not supabase: return []
    try: return supabase.table('notes').select('*').eq('user_hash',h).order('updated_at',desc=True).execute().data or []
    except: return []

def create_note(h,t,c):
    if not supabase: return None
    try: return supabase.table('notes').insert({'user_hash':h,'title':t,'content':c}).execute().data[0]
    except: return None

def update_note(id,t,c):
    if supabase:
        try: supabase.table('notes').update({'title':t,'content':c,'updated_at':'now()'}).eq('id',id).execute()
        except: pass

def delete_note(id):
    if supabase:
        try: supabase.table('notes').delete().eq('id',id).execute()
        except: pass

def edge_v(): return {"Myanmar-Thiha":"my-MM-ThihaNeural","Myanmar-Nilar":"my-MM-NilarNeural","English-Jenny":"en-US-JennyNeural","English-Guy":"en-US-GuyNeural","Thai":"th-TH-PremwadeeNeural","Chinese":"zh-CN-XiaoxiaoNeural","Japanese":"ja-JP-NanamiNeural","Korean":"ko-KR-SunHiNeural"}

def gem_v(): return {"Puck (ကျား)":"Puck","Charon (ကျား)":"Charon","Kore (မ)":"Kore","Fenrir (ကျား)":"Fenrir","Aoede (မ)":"Aoede","Leda (မ)":"Leda","Orus (ကျား)":"Orus","Zephyr (ကျား)":"Zephyr","Helios (ကျား)":"Helios","Perseus (ကျား)":"Perseus","Callirrhoe (မ)":"Callirrhoe","Autonoe (မ)":"Autonoe","Enceladus (ကျား)":"Enceladus","Iapetus (ကျား)":"Iapetus","Umbriel (ကျား)":"Umbriel","Algieba (မ)":"Algieba","Despina (မ)":"Despina","Erinome (မ)":"Erinome","Gacrux (ကျား)":"Gacrux","Achird (ကျား)":"Achird","Zubenelgenubi (ကျား)":"Zubenelgenubi","Schedar (မ)":"Schedar","Sadachbia (ကျား)":"Sadachbia","Sadaltager (ကျား)":"Sadaltager","Sulafat (မ)":"Sulafat"}

def get_voice_styles(): return {"🎬 Standard Storytelling (အကောင်းဆုံး)":"Narrate in an engaging and expressive storytelling style, suitable for a movie recap.","🔥 Dramatic & Suspenseful (သည်းထိတ်ရင်ဖို)":"A deep, dramatic, and suspenseful narration style. The voice should sound serious and intense.","😊 Casual & Friendly (ပေါ့ပေါ့ပါးပါး)":"Speak in a casual, friendly, and energetic manner, like a YouTuber summarizing a movie to a friend.","🎃 Horror & Creepy (သရဲဝတ္တု)":"Narrate in a chilling, eerie, and unsettling tone perfect for ghost stories and horror content.","🎭 Emotional & Dialogue (ခံစားချက်ပြည့်)":"Deliver the narration with deep emotional expression, as if performing a dramatic reading.","📺 News Anchor (သတင်းကြေငြာ)":"Speak in a professional, clear, and authoritative news anchor style.","🎓 Documentary (မှတ်တမ်းရုပ်ရှင်)":"Narrate in a calm, educational, and informative documentary style.","🎪 Custom (စိတ်ကြိုက်)":""}

def gen_gem_styled(key,txt,v,mdl,style_prompt="",speed=1.0):
    if not GENAI_NEW_AVAILABLE: return None,"google-genai not installed"
    try:
        cl=genai_new.Client(api_key=key)
        speed_instruction=""
        if speed<1.0: speed_instruction=f" Speak slowly at {speed}x speed."
        elif speed>1.0: speed_instruction=f" Speak faster at {speed}x speed."
        full_text=f"[Voice Style: {style_prompt}{speed_instruction}]\n\n{txt}" if style_prompt or speed_instruction else txt
        cfg=types.GenerateContentConfig(temperature=1,response_modalities=["audio"],speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=v))))
        aud=b"";mime="audio/L16;rate=24000"
        for ch in cl.models.generate_content_stream(model=mdl,contents=[types.Content(role="user",parts=[types.Part.from_text(text=full_text)])],config=cfg):
            if ch.candidates and ch.candidates[0].content and ch.candidates[0].content.parts:
                p=ch.candidates[0].content.parts[0]
                if hasattr(p,'inline_data') and p.inline_data and p.inline_data.data:
                    aud+=p.inline_data.data;mime=p.inline_data.mime_type
        if not aud: return None,"No audio"
        out=tempfile.NamedTemporaryFile(delete=False,suffix=".wav").name
        with open(out,"wb") as f: f.write(to_wav(aud,mime))
        return out,None
    except Exception as e: return None,str(e)

def gen_edge(txt,v,r=0):
    if not EDGE_TTS_AVAILABLE: return None,"Not available"
    try:
        out=tempfile.NamedTemporaryFile(delete=False,suffix=".mp3").name
        rs=f"+{r}%" if r>=0 else f"{r}%"
        async def _g(): await edge_tts.Communicate(txt,v,rate=rs).save(out)
        asyncio.run(_g())
        return out,None
    except Exception as e: return None,str(e)

def gen_gem(key,txt,v,mdl="gemini-2.5-flash-preview-tts"):
    if not GENAI_NEW_AVAILABLE: return None,"google-genai not installed"
    try:
        cl=genai_new.Client(api_key=key)
        cfg=types.GenerateContentConfig(temperature=1,response_modalities=["audio"],speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=v))))
        aud=b"";mime="audio/L16;rate=24000"
        for ch in cl.models.generate_content_stream(model=mdl,contents=[types.Content(role="user",parts=[types.Part.from_text(text=txt)])],config=cfg):
            if ch.candidates and ch.candidates[0].content and ch.candidates[0].content.parts:
                p=ch.candidates[0].content.parts[0]
                if hasattr(p,'inline_data') and p.inline_data and p.inline_data.data:
                    aud+=p.inline_data.data;mime=p.inline_data.mime_type
        if not aud: return None,"No audio"
        out=tempfile.NamedTemporaryFile(delete=False,suffix=".wav").name
        with open(out,"wb") as f: f.write(to_wav(aud,mime))
        return out,None
    except Exception as e: return None,str(e)

def cnt_w(t): return len(t.split()) if t.strip() else 0
def cnt_c(t): return len(t)
def cnt_l(t): return len(t.split('\n')) if t else 0
def to_up(t): return t.upper()
def to_lo(t): return t.lower()
def to_ti(t): return t.title()
def rm_empty(t): return '\n'.join([l for l in t.split('\n') if l.strip()])
def add_num(t): return '\n'.join([f"{i+1}. {l}" for i,l in enumerate(t.split('\n'))])
def rm_num(t): return '\n'.join([re.sub(r'^\d+[\.\)\-\:]\s*','',l) for l in t.split('\n')])
def sort_a(t): return '\n'.join(sorted(t.split('\n')))
def sort_d(t): return '\n'.join(sorted(t.split('\n'),reverse=True))
def rev_l(t): return '\n'.join(reversed(t.split('\n')))
def rm_dup(t): seen=set();return '\n'.join([l for l in t.split('\n') if not(l in seen or seen.add(l))])
def fr(t,f,r): return t.replace(f,r)
def add_pf(t,p): return '\n'.join([p+l for l in t.split('\n')])
def add_sf(t,s): return '\n'.join([l+s for l in t.split('\n')])
def srt_to_text(srt_content):
    lines=srt_content.split('\n')
    text_lines=[]
    for line in lines:
        line=line.strip()
        if not line:
            continue
        if line.isdigit():
            continue
        if '-->' in line:
            continue
        text_lines.append(line)
    return '\n'.join(text_lines)

def text_to_srt(text, sec_per_line=3):
    lines=[l.strip() for l in text.split('\n') if l.strip()]
    srt_out=[]
    for i,line in enumerate(lines):
        start=i*sec_per_line
        end=(i+1)*sec_per_line
        sh,sm,ss=start//3600,(start%3600)//60,start%60
        eh,em,es=end//3600,(end%3600)//60,end%60
        srt_out.append(f"{i+1}")
        srt_out.append(f"{sh:02d}:{sm:02d}:{ss:02d},000 --> {eh:02d}:{em:02d}:{es:02d},000")
        srt_out.append(line)
        srt_out.append("")
    return '\n'.join(srt_out)    
def to_srt(t,s=3):
    ls=[l for l in t.split('\n') if l.strip()];o=[]
    for i,l in enumerate(ls):
        st,et=i*s,(i+1)*s
        o.append(f"{i+1}\n{st//3600:02d}:{(st%3600)//60:02d}:{st%60:02d},000 --> {et//3600:02d}:{(et%3600)//60:02d}:{et%60:02d},000\n{l}\n")
    return '\n'.join(o)

def init_st():
    for k,v in {'video_queue':[],'processing_active':False,'current_index':0,'style_text':"",'custom_prompt':"",'generated_images':[],'current_note_id':None,'tts_audio':None,'editor_script':"",'editor_filename':'script.txt','user_session':None}.items():
        if k not in st.session_state: st.session_state[k]=v
init_st()

if not st.session_state['user_session']:
    st.title("Login / Sign Up")
    st.markdown("---")
    t1,t2=st.tabs(["Login","Sign Up"])
    with t1:
        with st.form("lf"):
            e=st.text_input("Email")
            p=st.text_input("Password",type="password")
            if st.form_submit_button("Login",use_container_width=True):
                u,m=login(e,p)
                if u: st.session_state['user_session']=u;st.rerun()
                elif m=="Pending": st.warning("Pending approval")
                else: st.error(m)
    with t2:
        st.subheader("Create Account")
        new_email = st.text_input("Email", key="reg_email")
        new_pass = st.text_input("Password", type="password", key="reg_pass")
        if st.button("Sign Up", use_container_width=True):
            if new_email and new_pass:
                success, msg = register(new_email, new_pass)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
            else:
                st.warning("Please fill all fields")
else:
    user=st.session_state['user_session']
    c1,c2=st.columns([5,1])
    with c1: st.title("AI Studio Pro");st.caption(f"User: {user['email']}")
    with c2:
        if st.button("Logout"): st.session_state['user_session']=None;st.rerun()
    
    if user.get('is_admin'):
        with st.expander("Admin"):
            if supabase:
                for u in supabase.table('users').select('*').order('created_at',desc=True).execute().data or []:
                    c1,c2,c3=st.columns([3,1,1])
                    with c1: st.write(u['email'])
                    with c2: st.caption("OK" if u['approved'] else "Pending")
                    with c3:
                        if u['email']!=user['email'] and st.button("Toggle",key=f"t_{u['id']}"): 
                            supabase.table('users').update({'approved':not u['approved']}).eq('id',u['id']).execute();st.rerun()
    
    st.markdown("---")
    with st.container(border=True):
        st.subheader("Settings")
        api_key=st.text_input("Google API Key",type="password",placeholder="Enter API Key...")
        if api_key:
            try: genai.configure(api_key=api_key);st.success("Connected")
            except: st.error("Invalid")
    
    st.markdown("---")
    t1,t2,t3,t4,t5,t6,t7=st.tabs(["Recap","Translate","Thumbnail","Rewrite","Notes","TTS","Editor"])
    
    with t1:
        st.header("Video Recap")
        with st.container(border=True):
            st.subheader("Models")
            vm=st.selectbox("Vision",["gemini-1.5-flash","gemini-2.0-flash-exp","models/gemini-2.5-flash","models/gemini-2.5-pro","models/gemini-3-flash-preview","models/gemini-3-pro-preview"],key="vm")
            wm=st.selectbox("Writer",["gemini-1.5-flash","gemini-2.0-flash-exp","models/gemini-2.5-flash","models/gemini-2.5-pro","models/gemini-3-flash-preview","models/gemini-3-pro-preview"],key="wm")
            use_examples=st.checkbox("Use Built-in Training Data",value=True,key="use_examples")
        vision_model = vm
        writer_model = wm
        with st.container(border=True):
            st.subheader("Add Videos")
            mt=st.radio("Method",["Upload (200MB)","Google Drive"],horizontal=True)
            if mt=="Upload (200MB)":
                vids=st.file_uploader("Videos",type=["mp4","mkv","mov"],accept_multiple_files=True)
                if st.button("Add",key="a1"):
                    for v in (vids or [])[:10-len(st.session_state['video_queue'])]:
                        v.seek(0,2)
                        if v.tell()<=200*1024*1024:
                            v.seek(0)
                            p,_=save_up(v)
                            if p:
                                st.session_state['video_queue'].append({'name':v.name,'type':'file','path':p,'url':None,'status':'waiting','script':None,'error':None})
                    st.rerun()
            else:
                lks=st.text_area("Links",height=100)
                if st.button("Add",key="a2"):
                    for l in (lks.strip().split('\n') if lks else []):
                        if 'drive.google.com' in l and get_gid(l.strip()):
                            st.session_state['video_queue'].append({'name':f"Vid_{len(st.session_state['video_queue'])+1}",'type':'url','path':None,'url':l.strip(),'status':'waiting','script':None,'error':None})
                    st.rerun()
        with st.expander("Custom"):
            st.session_state['custom_prompt']=st.text_area("Instructions",st.session_state.get('custom_prompt',''),height=60)
            sf=st.file_uploader("Style",type=["txt","pdf","docx"],key="sf")
            if sf:
                c=read_file(sf)
                if c:
                    st.session_state['style_text']=c[:5000]
                    st.success(f"Loaded: {sf.name}")
        with st.container(border=True):
            st.subheader("Queue")
            if not st.session_state['video_queue']:
                st.info("No videos")
            else:
                tot=len(st.session_state['video_queue'])
                dn=sum(1 for v in st.session_state['video_queue'] if v['status']=='completed')
                st.progress(dn/tot)
                st.caption(f"{dn}/{tot}")
                for i,it in enumerate(st.session_state['video_queue']):
                    st.markdown(f"**{i+1}. {it['name']}** - {it['status']}")
                    if it['status']=='completed' and it['script']:
                        st.download_button(f"DL#{i+1}",it['script'],f"{it['name']}_recap.txt",key=f"dl_{i}")
                    if it['status']=='failed':
                        st.error(it['error'][:100] if it['error'] else "Error")
            c1,c2=st.columns(2)
            with c1:
                if st.button("Start",disabled=not st.session_state['video_queue'] or st.session_state['processing_active'] or not api_key,use_container_width=True):
                    st.session_state['processing_active']=True
                    st.session_state['current_index']=0
                    st.rerun()
            with c2:
                if st.button("Clear",disabled=not st.session_state['video_queue'],use_container_width=True,key="cq"):
                    for it in st.session_state['video_queue']:
                        rm_file(it.get('path'))
                    st.session_state['video_queue']=[]
                    st.session_state['processing_active']=False
                    st.rerun()
        if st.session_state['processing_active']:
            idx=st.session_state['current_index']
            if idx<len(st.session_state['video_queue']):
                it=st.session_state['video_queue'][idx]
                if it['status']=='waiting':
                    st.session_state['video_queue'][idx]['status']='processing'
                    with st.container(border=True):
                        st.markdown(f"### Processing: {it['name']}")
                        sts=st.empty()
                        scr=None
                        er=None
                        if it['type']=='file':
                            scr,er=process_vid(it['path'],it['name'],vision_model,writer_model,st.session_state.get('style_text',''),st.session_state.get('custom_prompt',''),sts)
                            rm_file(it['path'])
                        else:
                            pth,er=dl_gdrive(it['url'],sts)
                            if pth:
                                scr,er=process_vid(pth,it['name'],vision_model,writer_model,st.session_state.get('style_text',''),st.session_state.get('custom_prompt',''),sts)
                                rm_file(pth)
                        if scr:
                            st.session_state['video_queue'][idx]['status']='completed'
                            st.session_state['video_queue'][idx]['script']=scr
                            sts.success("Done!")
                        else:
                            st.session_state['video_queue'][idx]['status']='failed'
                            st.session_state['video_queue'][idx]['error']=er
                            sts.error(er if er else "Unknown error")
                        time.sleep(10)
                        st.session_state['current_index']+=1
                        st.rerun()
            else:
                st.success("All done!")
                st.balloons()
                st.session_state['processing_active']=False

    with t2:
        st.header("Translator")
        with st.container(border=True):
            c1,c2=st.columns([3,1])
            with c2:
                tm=st.selectbox("Model",["models/gemini-2.5-flash","models/gemini-2.5-pro","models/gemini-3-pro-preview","models/gemini-3-flash-preview","gemini-2.0-flash-exp","gemini-1.5-flash"],key="tm")
            with c1:
                lngs={"Burmese":"Burmese","English":"English","Thai":"Thai","Chinese":"Chinese","Japanese":"Japanese","Korean":"Korean"}
                tl=st.selectbox("Target",list(lngs.keys()))
            input_type=st.radio("Input Type",["File Upload","Video URL"],horizontal=True,key="input_type")
            if input_type=="File Upload":
                tf=st.file_uploader("File",type=["mp3","mp4","txt","srt","docx"],key="tf")
                video_url=None
            else:
                tf=None
                video_url=st.text_input("Video URL",placeholder="YouTube, Facebook, TikTok, Google Drive link",key="video_url")
            tsf=st.file_uploader("Style (Optional)",type=["txt","pdf","docx"],key="tsf")    
            use_trans_examples=st.checkbox("📚 Use Built-in Training Data",value=False,key="use_trans_examples")
            tst=""
            if tsf:
                c=read_file(tsf)
                if c:
                    tst=c[:3000]
                    st.success(f"Style: {tsf.name}")
            if st.button("Translate",use_container_width=True):
                if not api_key:
                    st.error("Enter API Key first!")
                elif not tf and not video_url:
                    st.warning("Upload a file or enter URL!")
                else:
                    tgt=lngs[tl]
                    mdl=genai.GenerativeModel(tm)
                    trans_examples=get_recap_examples() if st.session_state.get('use_trans_examples',False) else ""
                    trans_ex_text=f"\n\nWriting Style Examples:\n{trans_examples}" if trans_examples else ""
                    
                    # Video URL handling
                    trans_examples=get_recap_examples() if st.session_state.get('use_trans_examples',False) else ""
                    trans_ex_text=f"\n\nWriting Style Examples:\n{trans_examples}" if trans_examples else ""
                    if video_url and not tf:
                        sty=f"\n\nStyle reference:\n{tst}" if tst else ""
                        progress=st.progress(0)
                        status=st.empty()
                        status.info("Downloading video...")
                        progress.progress(10)
                        pth,err=download_video_url(video_url,status)
                        if pth:
                            progress.progress(30)
                            status.info("Uploading to Gemini...")
                            gf=upload_gem(pth)
                            if gf:
                                trans_examples=get_recap_examples() if st.session_state.get('use_trans_examples',False) else ""
                                trans_ex_text=f"\n\nWriting Style Examples:\n{trans_examples}" if trans_examples else ""
                                status.info("Transcribing & Translating...")
                                progress.progress(50)
                                r,err=call_api(mdl,[gf,f"Listen to this video/audio carefully. Transcribe all spoken words and translate them to {tgt}. Return ONLY the translated text in {tgt} language. Do not include original language.{sty}\n\nUse the writing style from these examples (natural storytelling tone, emotional, engaging):\n{trans_ex_text}"],900)
                                progress.progress(90)
                                if r:
                                    res,_=get_text(r)
                                    progress.progress(100)
                                    status.success("Done!")
                                    if res:
                                        st.text_area("Result",res,height=300)
                                        if '-->' in res:
                                            srt_res=res
                                            txt_res=srt_to_text(res)
                                        else:
                                            srt_res=text_to_srt(res,3)
                                            txt_res=res
                                        dc1,dc2=st.columns(2)
                                        with dc1:
                                            st.download_button("TXT Download",txt_res,"translated.txt",use_container_width=True)
                                        with dc2:
                                            st.download_button("SRT Download",srt_res,"translated.srt",use_container_width=True)
                                else:
                                    progress.empty()
                                    status.error(f"Error: {err if err else 'Timeout'}")
                                try:
                                    genai.delete_file(gf.name)
                                except:
                                    pass
                            else:
                                progress.empty()
                                status.error("Upload to Gemini failed")
                            rm_file(pth)
                        else:
                            status.error(f"Download failed: {err}")
                    
                    # File Upload handling
                    elif tf:
                        ext=tf.name.split('.')[-1].lower()
                        
                        if ext in ['txt','srt']:
                            txt=tf.getvalue().decode("utf-8")
                            st.info(f"File: {tf.name} | {len(txt):,} chars")
                            progress=st.progress(0)
                            status=st.empty()
                            status.info("Translating... (may take 2-5 min)")
                            progress.progress(30)
                            r,err=call_api(mdl,f"Translate to {tgt}. Return ONLY translated text.{sty}{trans_ex_text}\n\n{txt}",900)
                            progress.progress(90)
                            if r:
                                res,_=get_text(r)
                                progress.progress(100)
                                status.success("Done!")
                                if res:
                                    st.text_area("Result",res,height=300)
                                    if '-->' in res:
                                        srt_res=res
                                        txt_res=srt_to_text(res)
                                    else:
                                        srt_res=text_to_srt(res,3)
                                        txt_res=res
                                    dc1,dc2=st.columns(2)
                                    with dc1:
                                        st.download_button("TXT Download",txt_res,f"trans_{tf.name.rsplit('.',1)[0]}.txt",use_container_width=True)
                                    with dc2:
                                        st.download_button("SRT Download",srt_res,f"trans_{tf.name.rsplit('.',1)[0]}.srt",use_container_width=True)
                            else:
                                progress.empty()
                                status.error(f"Error: {err if err else 'Timeout'}")
                        
                        elif ext=='docx':
                            txt=read_file(tf)
                            if txt:
                                st.info(f"File: {tf.name} | {len(txt):,} chars")
                                progress=st.progress(0)
                                status=st.empty()
                                status.info("Translating...")
                                progress.progress(30)
                                r,err=call_api(mdl,f"Translate to {tgt}. Return ONLY translated text.{sty}{trans_ex_text}\n\n{txt}",900)
                                progress.progress(90)
                                if r:
                                    res,_=get_text(r)
                                    progress.progress(100)
                                    status.success("Done!")
                                    if res:
                                        st.text_area("Result",res,height=300)
                                        if '-->' in res:
                                            srt_res=res
                                            txt_res=srt_to_text(res)
                                        else:
                                            srt_res=text_to_srt(res,3)
                                            txt_res=res
                                        dc1,dc2=st.columns(2)
                                        with dc1:
                                            st.download_button("TXT Download",txt_res,f"trans_{tf.name.rsplit('.',1)[0]}.txt",use_container_width=True)
                                        with dc2:
                                            st.download_button("SRT Download",srt_res,f"trans_{tf.name.rsplit('.',1)[0]}.srt",use_container_width=True)
                                else:
                                    progress.empty()
                                    status.error(f"Error: {err if err else 'Timeout'}")
                        
                        else:
                            st.info(f"File: {tf.name}")
                            progress=st.progress(0)
                            status=st.empty()
                            status.info("Uploading file...")
                            progress.progress(20)
                            pth,_=save_up(tf)
                            if pth:
                                status.info("Processing on Gemini...")
                                progress.progress(40)
                                gf=upload_gem(pth)
                                if gf:
                                    status.info("Transcribing & Translating...")
                                    progress.progress(60)
                                    r,err=call_api(mdl,[gf,f"Listen to this video/audio carefully. Transcribe all spoken words and translate them to {tgt}. Return ONLY the translated text in {tgt} language. Do not include original language.{sty}{trans_ex_text}"],900)
                                    progress.progress(90)
                                    if r:
                                        res,_=get_text(r)
                                        progress.progress(100)
                                        status.success("Done!")
                                        if res:
                                            st.text_area("Result",res,height=300)
                                            if '-->' in res:
                                                srt_res=res
                                                txt_res=srt_to_text(res)
                                            else:
                                                srt_res=text_to_srt(res,3)
                                                txt_res=res
                                            dc1,dc2=st.columns(2)
                                            with dc1:
                                                st.download_button("TXT Download",txt_res,f"{tf.name.rsplit('.',1)[0]}_trans.txt",use_container_width=True)
                                            with dc2:
                                                st.download_button("SRT Download",srt_res,f"{tf.name.rsplit('.',1)[0]}_trans.srt",use_container_width=True)
                                    else:
                                        progress.empty()
                                        status.error(f"Error: {err if err else 'Timeout'}")
                                    try:
                                        genai.delete_file(gf.name)
                                    except:
                                        pass
                                else:
                                    progress.empty()
                                    status.error("Upload failed")
                                rm_file(pth)

    # === TAB 3: THUMBNAIL ===
    with t3:
        st.header("AI Thumbnail")
        st.caption("Nanobanana Pro (gemini-3-pro-image-preview)")
        with st.container(border=True):
            # Reference Images - အပေါ်ဆုံးမှာထား
            ri=st.file_uploader("Reference (Max 10)",type=["png","jpg","jpeg","webp"],accept_multiple_files=True,key="ri")
            if ri:
                st.caption(f"{len(ri)} image(s)")
                cols=st.columns(min(len(ri),6))
                for i,im in enumerate(ri[:6]):
                    with cols[i]: st.image(im,use_container_width=True)
            st.markdown("---")
            
            # Templates
            tmps={
                "Custom (စိတ်ကြိုက်)":"",
                "Movie Recap (ရုပ်ရှင်အကျဉ်းချုပ်)":"dramatic YouTube movie recap thumbnail, cinematic lighting, emotional scene, bold title text, film grain effect, dark moody atmosphere",
                "Shocking (အံ့ဩစရာ)":"YouTube thumbnail, shocked surprised expression, bright red yellow background, bold dramatic text, eye-catching, viral style",
                "Horror (ထိတ်လန့်)":"horror movie thumbnail, dark scary atmosphere, creepy shadows, fear expression, blood red accents, haunted feeling",
                "Comedy (ဟာသ)":"funny comedy thumbnail, bright colorful, laughing expression, playful text, cheerful mood, cartoon style elements",
                "Romance (အချစ်)":"romantic movie thumbnail, soft pink lighting, couple silhouette, heart elements, dreamy bokeh background, emotional",
                "Action (အက်ရှင်)":"action movie thumbnail, explosive background, fire sparks, intense expression, dynamic pose, bold red orange colors",
                "Drama (ဒရာမာ)":"emotional drama thumbnail, tears sad expression, rain effect, blue moody lighting, touching moment, cinematic",
                "Thriller (သည်းထိတ်)":"thriller suspense thumbnail, mysterious dark, half face shadow, intense eyes, danger feeling, noir style",
                "Fantasy (စိတ်ကူးယဉ်)":"fantasy magical thumbnail, glowing effects, mystical atmosphere, enchanted, purple blue colors, epic scene",
                "Documentary (မှတ်တမ်း)":"documentary style thumbnail, realistic, informative look, clean professional, news style, factual feeling"
            }
            sel=st.selectbox("Template",list(tmps.keys()))
            
            # Size options
            sizes={"16:9 (1280x720)":"1280x720","9:16 (720x1280)":"720x1280","1:1 (1024x1024)":"1024x1024","4:3 (1024x768)":"1024x768","3:4 (768x1024)":"768x1024"}
            sz=st.selectbox("Size",list(sizes.keys()))
            
            # Prompt
            pr=st.text_area("Prompt",value=tmps[sel],height=100)
            
            # Text, Style, Count
            c1,c2,c3=st.columns([2,2,1])
            with c1:
                atxt=st.text_input("Text",placeholder="EP.1")
            with c2:
                text_styles={
                    "Default (မူလ)":"bold text",
                    "Shocking (အံ့ဩ)":"bold dramatic red yellow gradient text, impact font",
                    "Horror (ထိတ်လန့်)":"creepy horror text, blood dripping, scary font",
                    "Comedy (ဟာသ)":"fun colorful cartoon text, playful bubble font",
                    "Romance (အချစ်)":"elegant romantic pink text, script font, heart accents",
                    "Action (အက်ရှင်)":"bold explosive metallic text, fire effect, impact font",
                    "Drama (ဒရာမာ)":"emotional elegant text, serif font, subtle glow",
                    "Thriller (သည်းထိတ်)":"mysterious dark text, noir style, shadow effect",
                    "Fantasy (စိတ်ကူးယဉ်)":"magical glowing text, enchanted fantasy font",
                    "Documentary (မှတ်တမ်း)":"clean professional text, sans-serif, news style",
                    "Gold 3D":"gold 3D metallic text, shiny, luxurious",
                    "White 3D Blue Outline":"white 3D text with dark blue outline, bold",
                    "Yellow 3D Black Outline":"yellow 3D text with black outline, bold impact",
                    "Red 3D Yellow Outline":"red 3D text with yellow outline, bold dramatic"
                }
                txt_style=st.selectbox("Text Style",list(text_styles.keys()))
            with c3:
                num=st.selectbox("Count",[1,2,3,4])
            
            # Generate Button
            if st.button("Generate",use_container_width=True,type="primary"):
                if not api_key:
                    st.error("Enter API Key!")
                elif not pr.strip():
                    st.warning("Enter prompt!")
                else:
                    # Clear previous results
                    st.session_state['generated_images']=[]
                    
                    # Build final prompt
                    szv=sizes[sz]
                    txt_style_prompt=text_styles[txt_style] if atxt else ""
                    fp=pr.strip()+(f", text:'{atxt}', {txt_style_prompt}" if atxt else "")+f", {szv}, high quality"
                    
                    # Load reference images into memory BEFORE threading
                    ref_pil_images=[]
                    if ri:
                        for r in ri[:10]:
                            try:
                                r.seek(0)
                                img_bytes = r.read()
                                ref_pil_images.append(Image.open(io.BytesIO(img_bytes)))
                            except Exception as e:
                                st.warning(f"Reference image load failed: {e}")
                    
                    # Sequential generation function (safer than parallel for Gemini)
                    def generate_single(idx, prompt, ref_imgs):
                        try:
                            mdl=genai.GenerativeModel("models/gemini-3-pro-image-preview")
                            
                            # Build content
                            content_parts = [f"Generate image: {prompt}"]
                            if ref_imgs:
                                content_parts.extend(ref_imgs)
                            
                            # Generate
                            rsp=mdl.generate_content(
                                content_parts,
                                request_options={"timeout":300}
                            )
                            
                            # Extract image
                            if rsp.candidates:
                                for p in rsp.candidates[0].content.parts:
                                    if hasattr(p,'inline_data') and p.inline_data:
                                        img_data = p.inline_data.data
                                        mime = p.inline_data.mime_type
                                        
                                        # Validate image data
                                        if img_data and len(img_data) > 1000:  # At least 1KB
                                            return {'data': img_data, 'mime': mime, 'idx': idx, 'success': True}
                                        else:
                                            return {'error': 'Image data too small or empty', 'idx': idx, 'success': False}
                            
                            return {'error': 'No image in response', 'idx': idx, 'success': False}
                            
                        except Exception as e:
                            return {'error': str(e), 'idx': idx, 'success': False}
                    
                    # Progress container
                    progress_placeholder = st.empty()
                    results_container = st.container()
                    
                    generated_count = 0
                    failed_count = 0
                    
                    with progress_placeholder.container():
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        # Generate images one by one (more reliable than parallel)
                        for i in range(1, num + 1):
                            status_text.info(f"🎨 Generating image {i}/{num}...")
                            
                            result = generate_single(i, fp, ref_pil_images)
                            
                            if result and result.get('success'):
                                st.session_state['generated_images'].append(result)
                                generated_count += 1
                                status_text.success(f"✅ Image {i} generated!")
                            else:
                                failed_count += 1
                                error_msg = result.get('error', 'Unknown error') if result else 'No response'
                                status_text.warning(f"⚠️ Image {i} failed: {error_msg}")
                            
                            # Update progress
                            progress_bar.progress(i / num)
                            
                            # Small delay between requests
                            if i < num:
                                time.sleep(1)
                        
                        # Final status
                        if generated_count > 0:
                            status_text.success(f"✅ Done! Generated {generated_count}/{num} images")
                        else:
                            status_text.error(f"❌ All {num} images failed to generate")
            
            # Display Results
            if st.session_state.get('generated_images'):
                st.markdown("---")
                st.markdown("### 🖼️ Results")
                
                col_clear, _ = st.columns([1, 3])
                with col_clear:
                    if st.button("🗑️ Clear All", key="ct"):
                        st.session_state['generated_images'] = []
                        st.rerun()
                
                # Display images
                for i, im in enumerate(st.session_state['generated_images']):
                    with st.container(border=True):
                        try:
                            st.image(im['data'], use_container_width=True)
                            
                            # Download button
                            st.download_button(
                                f"⬇️ Download #{im['idx']}",
                                im['data'],
                                f"thumbnail_{im['idx']}.png",
                                mime=im.get('mime', 'image/png'),
                                key=f"dl_{i}_{int(time.time()*1000)}",
                                use_container_width=True
                            )
                        except Exception as e:
                            st.error(f"Error displaying image {im['idx']}: {e}")

    with t4:
        st.header("Rewriter")
        with st.container(border=True):
            rm=st.selectbox("Model",["gemini-1.5-flash","gemini-2.0-flash-exp","models/gemini-2.5-flash","models/gemini-2.5-pro","models/gemini-3-flash-preview","models/gemini-3-pro-preview"],key="rm")
            rsf=st.file_uploader("Style",type=["txt","pdf","docx"],key="rsf")
            orig=st.text_area("Original",height=250)
            if st.button("Rewrite",use_container_width=True):
                if api_key and orig:
                    sty=read_file(rsf) if rsf else "Professional storytelling"
                    with st.spinner("Rewriting..."):
                        m=genai.GenerativeModel(rm)
                        r,e=call_api(m,f"Rewrite in style. Keep details. Burmese output.\n\nSTYLE:\n{sty[:5000]}\n\nORIGINAL:\n{orig}")
                        if r:
                            txt,_=get_text(r)
                            if txt: st.text_area("Result",txt,height=350);st.download_button("Download",txt,"rewritten.txt")
                        else: st.error(e)

    with t5:
        st.header("Notes")
        with st.container(border=True):
            if not api_key: st.warning("Enter API Key")
            elif not SUPABASE_AVAILABLE: st.error("Supabase unavailable")
            else:
                uh=get_hash(api_key)
                if st.button("New Note",use_container_width=True):
                    nt=create_note(uh,"Untitled","")
                    if nt: st.session_state['current_note_id']=nt['id'];st.rerun()
                nts=get_notes(uh)
                if nts:
                    for n in nts:
                        c1,c2=st.columns([5,1])
                        with c1:
                            if st.button(n['title'][:25],key=f"n_{n['id']}",use_container_width=True): st.session_state['current_note_id']=n['id'];st.rerun()
                        with c2:
                            if st.button("X",key=f"d_{n['id']}"): delete_note(n['id']);st.rerun()
                cid=st.session_state.get('current_note_id')
                if cid and nts:
                    nt=next((n for n in nts if n['id']==cid),None)
                    if nt:
                        st.markdown("---")
                        ti=st.text_input("Title",nt['title'])
                        co=st.text_area("Content",nt['content'] or "",height=300)
                        if st.button("Save",use_container_width=True): update_note(cid,ti,co);st.success("Saved!");st.rerun()

    with t6:
        st.header("Text to Speech")
        with st.container(border=True):
            eng=st.radio("Engine",["Edge TTS (Myanmar)","Gemini TTS"],horizontal=True)
            st.markdown("---")
            if "Edge" in eng:
                if not EDGE_TTS_AVAILABLE: st.error("Edge TTS unavailable")
                else:
                    txt=st.text_area("Text",height=200,key="et")
                    c1,c2=st.columns(2)
                    with c1: vc=st.selectbox("Voice",list(edge_v().keys()),key="ev")
                    with c2: rt=st.slider("Speed",-50,50,0,format="%d%%",key="er")
                    st.caption(f"Chars: {len(txt)}")
                    if st.button("Generate",use_container_width=True,key="ge"):
                        if txt.strip():
                            with st.spinner("Generating..."):
                                p,e=gen_edge(txt,edge_v()[vc],rt)
                                if p: st.session_state['tts_audio']=p;st.success("Done!")
                                else: st.error(e)
            else:
                if not GENAI_NEW_AVAILABLE: st.error("google-genai not installed")
                else:
                    st.info("🎙️ Gemini TTS - Voice Styles Supported")
                    txt=st.text_area("Text",height=200,key="gt")
                    
                    # Voice Style Selection
                    voice_styles=get_voice_styles()
                    selected_style=st.selectbox("🎨 Voice Style",list(voice_styles.keys()),key="gvs")
                    style_prompt=voice_styles[selected_style]
                    
                    # Custom style input
                    if "Custom" in selected_style:
                        style_prompt=st.text_area("Custom Style Prompt",height=80,key="custom_style",placeholder="Describe how you want the voice to sound...")
                    
                    c1,c2,c3=st.columns(3)
                    with c1: vc=st.selectbox("🔊 Voice",list(gem_v().keys()),key="gv")
                    with c2: mdl=st.selectbox("🤖 Model",["gemini-2.5-flash-preview-tts","gemini-2.5-pro-preview-tts"],key="gm")
                    with c3: spd=st.slider("⚡ Speed",0.50,2.00,1.00,0.02,key="gspd")
                    st.caption(f"Chars: {len(txt)}")
                    
                    if st.button("🎙️ Generate",use_container_width=True,key="gg",type="primary"):
                        if not api_key: st.error("Enter API Key!")
                        elif not txt.strip(): st.warning("Enter text!")
                        else:
                            with st.spinner(f"Generating with {mdl}..."):
                                p,e=gen_gem_styled(api_key,txt,gem_v()[vc],mdl,style_prompt,spd)
                                if p: st.session_state['tts_audio']=p;st.success("Done!")
                                else: st.error(e)
        if st.session_state.get('tts_audio') and os.path.exists(st.session_state['tts_audio']):
            st.markdown("### Output")
            with st.container(border=True):
                with open(st.session_state['tts_audio'],'rb') as f: ab=f.read()
                mime="audio/wav" if st.session_state['tts_audio'].endswith(".wav") else "audio/mp3"
                st.audio(ab,format=mime)
                ext="wav" if ".wav" in st.session_state['tts_audio'] else "mp3"
                st.download_button("Download",ab,f"audio.{ext}",mime,use_container_width=True)
                if st.button("Clear",use_container_width=True,key="ca"): rm_file(st.session_state['tts_audio']);st.session_state['tts_audio']=None;st.rerun()

    with t7:
        st.header("Script Editor")
        with st.container(border=True):
            c1,c2,c3,c4=st.columns(4)
            with c1: ef=st.file_uploader("Open",type=["txt","docx","srt","md"],key="ef",label_visibility="collapsed")
            with c2:
                if st.button("New",use_container_width=True): st.session_state['editor_script']="";st.session_state['editor_filename']="script.txt";st.rerun()
            with c3:
                if st.button("Clear",use_container_width=True,key="ce"): st.session_state['editor_script']="";st.rerun()
            with c4: fmt=st.selectbox("Format",["txt","srt","md"],label_visibility="collapsed")
            if ef:
                if ef.name.endswith(('.txt','.srt','.md')): st.session_state['editor_script']=ef.getvalue().decode("utf-8")
                elif DOCX_AVAILABLE: st.session_state['editor_script']=read_file(ef) or ""
                st.session_state['editor_filename']=ef.name;st.success(f"Opened: {ef.name}")
        with st.container(border=True):
            cur=st.session_state.get('editor_script','')
            new=st.text_area("Editor",cur,height=350,label_visibility="collapsed",placeholder="Start typing...")
            if new!=cur: st.session_state['editor_script']=new
        with st.container(border=True):
            txt=st.session_state.get('editor_script','')
            c1,c2,c3,c4,c5=st.columns(5)
            with c1: st.metric("Words",cnt_w(txt))
            with c2: st.metric("Chars",cnt_c(txt))
            with c3: st.metric("Lines",cnt_l(txt))
            with c4: st.caption(f"Read: ~{max(1,cnt_w(txt)//200)}min")
            with c5: st.caption(f"Speak: ~{max(1,cnt_w(txt)//150)}min")
        with st.expander("Case"):
            c1,c2,c3=st.columns(3)
            with c1:
                if st.button("UPPER",use_container_width=True): st.session_state['editor_script']=to_up(st.session_state['editor_script']);st.rerun()
            with c2:
                if st.button("lower",use_container_width=True): st.session_state['editor_script']=to_lo(st.session_state['editor_script']);st.rerun()
            with c3:
                if st.button("Title",use_container_width=True): st.session_state['editor_script']=to_ti(st.session_state['editor_script']);st.rerun()
        with st.expander("Lines"):
            c1,c2,c3,c4=st.columns(4)
            with c1:
                if st.button("Add #",use_container_width=True): st.session_state['editor_script']=add_num(st.session_state['editor_script']);st.rerun()
            with c2:
                if st.button("Rm #",use_container_width=True): st.session_state['editor_script']=rm_num(st.session_state['editor_script']);st.rerun()
            with c3:
                if st.button("Sort A-Z",use_container_width=True): st.session_state['editor_script']=sort_a(st.session_state['editor_script']);st.rerun()
            with c4:
                if st.button("Sort Z-A",use_container_width=True): st.session_state['editor_script']=sort_d(st.session_state['editor_script']);st.rerun()
            c1,c2,c3,c4=st.columns(4)
            with c1:
                if st.button("Reverse",use_container_width=True): st.session_state['editor_script']=rev_l(st.session_state['editor_script']);st.rerun()
            with c2:
                if st.button("Rm Dup",use_container_width=True): st.session_state['editor_script']=rm_dup(st.session_state['editor_script']);st.rerun()
            with c3:
                if st.button("Rm Empty",use_container_width=True): st.session_state['editor_script']=rm_empty(st.session_state['editor_script']);st.rerun()
            with c4: pass
        with st.expander("Find/Replace"):
            c1,c2=st.columns(2)
            with c1: fnd=st.text_input("Find:",key="fnd")
            with c2: rpl=st.text_input("Replace:",key="rpl")
            if st.button("Replace All",use_container_width=True):
                if fnd: st.session_state['editor_script']=fr(st.session_state['editor_script'],fnd,rpl);st.rerun()
        with st.expander("Prefix/Suffix"):
            c1,c2=st.columns(2)
            with c1:
                pf=st.text_input("Prefix:",key="pf")
                if st.button("Add Prefix",use_container_width=True):
                    if pf: st.session_state['editor_script']=add_pf(st.session_state['editor_script'],pf);st.rerun()
            with c2:
                sf=st.text_input("Suffix:",key="sf2")
                if st.button("Add Suffix",use_container_width=True):
                    if sf: st.session_state['editor_script']=add_sf(st.session_state['editor_script'],sf);st.rerun()
        with st.expander("SRT"):
            sec=st.number_input("Sec/line:",min_value=1,max_value=10,value=3,key="srt_s")
            if st.button("To SRT",use_container_width=True): st.session_state['editor_script']=to_srt(st.session_state['editor_script'],sec);st.rerun()
        with st.container(border=True):
            if st.session_state.get('editor_script'):
                bn=st.session_state.get('editor_filename','script').rsplit('.',1)[0]
                st.download_button(f"Download .{fmt}",st.session_state['editor_script'],f"{bn}.{fmt}",use_container_width=True)

    st.markdown("---")
    st.caption("AI Studio Pro v6.3")
