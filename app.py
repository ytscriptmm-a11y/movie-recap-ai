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
from PIL import Image

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

def call_api(m,c,to=600):
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

def process_vid(p,n,vm,wm,st_txt="",cust="",s=None):
    gf=None
    try:
        if s: s.info("Step 1/3: Uploading...")
        gf=upload_gem(p,s)
        if not gf: return None,"Upload failed"
        if s: s.info("Step 2/3: Analyzing...")
        v=genai.GenerativeModel(vm)
        r,e=call_api(v,[gf," Watch this video carefully. 
        Generate a highly detailed, chronological scene-by-scene description. (Use a storytelling tone.)
        Include All the dialogue in the movie, visual details, emotions, and actions. (Use a storytelling tone.)
        No creative writing yet, just facts. "],600)
        if e: return None,f"Analysis failed: {e}"
        desc,_=get_text(r)
        time.sleep(5)
        if s: s.info("Step 3/3: Writing script...")
        w=genai.GenerativeModel(wm)
        pr=f"Professional Burmese Movie Recap Scriptwriter.\n\nINPUT:\n{desc}\n{f'STYLE:{st_txt}' if st_txt else ''}\n{f'CUSTOM:{cust}' if cust else ''}\n\nYou are a professional Burmese Movie Recap Scriptwriter.
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
        6. Full narration.                         
        """"
        r,e=call_api(w,pr,600)
        if e: return None,f"Writing failed: {e}"
        txt,_=get_text(r)
        return txt,None
    except Exception as e: return None,str(e)
    finally:
        if gf:
            try: genai.delete_file(gf.name)
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
def gem_v(): return {"Zephyr":"Zephyr","Puck":"Puck","Charon":"Charon","Kore":"Kore","Fenrir":"Fenrir","Leda":"Leda","Orus":"Orus","Aoede":"Aoede"}

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
        ne=st.text_input("Email",key="re")
        np=st.text_input("Password",type="password",key="rp")
        if st.button("Sign Up",use_container_width=True):
            if ne and np: ok,m=register(ne,np);st.success(m) if ok else st.error(m)
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
            vm=st.selectbox("Vision",["models/gemini-2.5-flash","models/gemini-2.5-pro","models/gemini-3-pro-preview","gemini-1.5-flash"],key="vm")
            wm=st.selectbox("Writer",["gemini-1.5-flash","gemini-2.0-flash-exp","models/gemini-2.5-flash","models/gemini-2.5-pro","models/gemini-3-pro-preview"],key="wm")
        with st.container(border=True):
            st.subheader("Add Videos")
            mt=st.radio("Method",["Upload (200MB)","Google Drive"],horizontal=True)
            if mt=="Upload (200MB)":
                vids=st.file_uploader("Videos",type=["mp4","mkv","mov"],accept_multiple_files=True)
                if st.button("Add",key="a1"):
                    for v in (vids or [])[:10-len(st.session_state['video_queue'])]:
                        v.seek(0,2)
                        if v.tell()<=200*1024*1024:
                            v.seek(0);p,_=save_up(v)
                            if p: st.session_state['video_queue'].append({'name':v.name,'type':'file','path':p,'url':None,'status':'waiting','script':None,'error':None})
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
            if sf and (c:=read_file(sf)): st.session_state['style_text']=c[:5000];st.success(f"Loaded: {sf.name}")
        with st.container(border=True):
            st.subheader("Queue")
            if not st.session_state['video_queue']: st.info("No videos")
            else:
                tot=len(st.session_state['video_queue']);dn=sum(1 for v in st.session_state['video_queue'] if v['status']=='completed')
                st.progress(dn/tot);st.caption(f"{dn}/{tot}")
                for i,it in enumerate(st.session_state['video_queue']):
                    st.markdown(f"**{i+1}. {it['name']}** - {it['status']}")
                    if it['status']=='completed' and it['script']: st.download_button(f"DL#{i+1}",it['script'],f"{it['name']}_recap.txt",key=f"dl_{i}")
                    if it['status']=='failed': st.error(it['error'][:100] if it['error'] else "Error")
            c1,c2=st.columns(2)
            with c1:
                if st.button("Start",disabled=not st.session_state['video_queue'] or st.session_state['processing_active'] or not api_key,use_container_width=True):
                    st.session_state['processing_active']=True;st.session_state['current_index']=0;st.rerun()
            with c2:
                if st.button("Clear",disabled=not st.session_state['video_queue'],use_container_width=True,key="cq"):
                    for it in st.session_state['video_queue']: rm_file(it.get('path'))
                    st.session_state['video_queue']=[];st.session_state['processing_active']=False;st.rerun()
        if st.session_state['processing_active']:
            idx=st.session_state['current_index']
            if idx<len(st.session_state['video_queue']):
                it=st.session_state['video_queue'][idx]
                if it['status']=='waiting':
                    st.session_state['video_queue'][idx]['status']='processing'
                    with st.container(border=True):
                        st.markdown(f"### Processing: {it['name']}")
                        sts=st.empty()
                        if it['type']=='file':
                            scr,er=process_vid(it['path'],it['name'],vm,wm,st.session_state.get('style_text',''),st.session_state.get('custom_prompt',''),sts)
                            rm_file(it['path'])
                        else:
                            pth,er=dl_gdrive(it['url'],sts)
                            if pth: scr,er=process_vid(pth,it['name'],vm,wm,st.session_state.get('style_text',''),st.session_state.get('custom_prompt',''),sts);rm_file(pth)
                            else: scr=None
                        if scr: st.session_state['video_queue'][idx]['status']='completed';st.session_state['video_queue'][idx]['script']=scr;sts.success("Done!")
                        else: st.session_state['video_queue'][idx]['status']='failed';st.session_state['video_queue'][idx]['error']=er;sts.error(er)
                        time.sleep(10);st.session_state['current_index']+=1;st.rerun()
            else: st.success("All done!");st.balloons();st.session_state['processing_active']=False

    with t2:
        st.header("Translator")
        with st.container(border=True):
            c1,c2=st.columns([3,1])
            with c2: tm=st.selectbox("Model",["gemini-1.5-flash","gemini-2.0-flash-exp","models/gemini-2.5-flash","models/gemini-3-pro-preview"],key="tm")
            with c1: lngs={"Burmese":"Burmese","English":"English","Thai":"Thai","Chinese":"Chinese","Japanese":"Japanese","Korean":"Korean"};tl=st.selectbox("Target",list(lngs.keys()))
            tf=st.file_uploader("File",type=["mp3","mp4","txt","srt","docx"],key="tf")
            tsf=st.file_uploader("Style (Optional)",type=["txt","pdf","docx"],key="tsf")
            tst=""
            if tsf and (c:=read_file(tsf)): tst=c[:3000];st.success(f"Style: {tsf.name}")
            if st.button("Translate",use_container_width=True):
                if api_key and tf:
                    ext=tf.name.split('.')[-1].lower();tgt=lngs[tl];mdl=genai.GenerativeModel(tm)
                    sty=f"\n\nStyle reference:\n{tst}" if tst else ""
                    if ext in ['txt','srt']:
                        with st.spinner("Translating..."):
                            txt=tf.getvalue().decode("utf-8")
                            r,_=call_api(mdl,f"Translate to {tgt}. Return ONLY translated text.{sty}\n\n{txt}")
                            if r:
                                res,_=get_text(r)
                                if res: st.text_area("Result",res,height=300);st.download_button("Download",res,f"trans_{tf.name}")
                    elif ext=='docx':
                        with st.spinner("Translating..."):
                            txt=read_file(tf)
                            if txt:
                                r,_=call_api(mdl,f"Translate to {tgt}. Return ONLY translated text.{sty}\n\n{txt}")
                                if r:
                                    res,_=get_text(r)
                                    if res: st.text_area("Result",res,height=300);st.download_button("Download",res,f"trans_{tf.name}.txt")
                    else:
                        with st.spinner("Processing..."):
                            pth,_=save_up(tf)
                            if pth:
                                gf=upload_gem(pth)
                                if gf:
                                    r,_=call_api(mdl,[gf,f"Transcribe and translate to {tgt}.{sty}"],600)
                                    if r:
                                        res,_=get_text(r)
                                        if res: st.text_area("Result",res,height=300);st.download_button("Download",res,f"{tf.name}_trans.txt")
                                    try: genai.delete_file(gf.name)
                                    except: pass
                                rm_file(pth)

    with t3:
        st.header("AI Thumbnail")
        st.caption("Nanobanana Pro (gemini-3-pro-image-preview)")
        with st.container(border=True):
            ri=st.file_uploader("Reference (Max 10)",type=["png","jpg","jpeg","webp"],accept_multiple_files=True,key="ri")
            if ri:
                st.caption(f"{len(ri)} image(s)")
                cols=st.columns(min(len(ri),6))
                for i,im in enumerate(ri[:6]):
                    with cols[i]: st.image(im,use_container_width=True)
            st.markdown("---")
            tmps={"Custom":"","Movie Recap":"dramatic YouTube movie recap thumbnail, 1280x720, cinematic, emotional, bold text","Shocking":"YouTube thumbnail, shocked expression, red yellow, bold text, 1280x720"}
            sel=st.selectbox("Template",list(tmps.keys()))
            pr=st.text_area("Prompt",value=tmps[sel],height=100)
            c1,c2=st.columns(2)
            with c1: atxt=st.text_input("Text",placeholder="EP.1")
            with c2: num=st.selectbox("Count",[1,2,3,4])
            if st.button("Generate",use_container_width=True):
                if not api_key: st.error("Enter API Key!")
                elif not pr.strip(): st.warning("Enter prompt!")
                else:
                    st.session_state['generated_images']=[]
                    fp=pr.strip()+(f", text:'{atxt}'" if atxt else "")+", high quality"
                    with st.spinner("Generating..."):
                        try:
                            im=genai.GenerativeModel("models/gemini-3-pro-image-preview")
                            for i in range(num):
                                st.info(f"Generating {i+1}/{num}...")
                                ct=[f"Generate image: {fp}"]
                                if ri:
                                    for r in ri[:10]: r.seek(0);ct.append(Image.open(r))
                                rsp=im.generate_content(ct,request_options={"timeout":180})
                                if rsp.candidates:
                                    for p in rsp.candidates[0].content.parts:
                                        if hasattr(p,'inline_data') and p.inline_data:
                                            st.session_state['generated_images'].append({'data':p.inline_data.data,'mime':p.inline_data.mime_type,'idx':i+1});break
                                time.sleep(2)
                            if st.session_state['generated_images']: st.success(f"Generated {len(st.session_state['generated_images'])}")
                        except Exception as e: st.error(str(e))
        if st.session_state.get('generated_images'):
            st.markdown("### Results")
            if st.button("Clear",key="ct"): st.session_state['generated_images']=[];st.rerun()
            for i,im in enumerate(st.session_state['generated_images']):
                with st.container(border=True):
                    st.image(im['data'],use_container_width=True)
                    st.download_button(f"Download #{im['idx']}",im['data'],f"thumb_{i+1}.png",key=f"dt_{i}_{time.time()}",use_container_width=True)

    with t4:
        st.header("Rewriter")
        with st.container(border=True):
            rm=st.selectbox("Model",["gemini-1.5-flash","gemini-2.0-flash-exp","models/gemini-2.5-flash","models/gemini-3-pro-preview"],key="rm")
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
                    st.info("Gemini TTS supports multiple languages")
                    txt=st.text_area("Text",height=200,key="gt")
                    c1,c2=st.columns(2)
                    with c1: vc=st.selectbox("Voice",list(gem_v().keys()),key="gv")
                    with c2: mdl=st.selectbox("Model",["gemini-2.5-flash-preview-tts","gemini-2.5-pro-preview-tts"],key="gm")
                    st.caption(f"Chars: {len(txt)}")
                    if st.button("Generate",use_container_width=True,key="gg"):
                        if not api_key: st.error("Enter API Key!")
                        elif not txt.strip(): st.warning("Enter text!")
                        else:
                            with st.spinner(f"Generating with {mdl}..."):
                                p,e=gen_gem(api_key,txt,gem_v()[vc],mdl)
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
