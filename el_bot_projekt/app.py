import streamlit as st
import os
import re
import base64
import time
import random
import urllib.parse
from PIL import Image
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage

# --- 1. SIDKONFIGURATION OCH BRANDING ---
current_dir = os.path.dirname(os.path.abspath(__file__))
log_path = os.path.join(current_dir, "saknade_fragor.txt")
img_log_path = os.path.join(current_dir, "saknade_bilder.txt")
logo_path = os.path.join(current_dir, "bilder", "logo.png")
index_path = os.path.join(current_dir, "faiss_index")

try:
    app_icon = Image.open(logo_path)
except:
    app_icon = "⚡"

st.set_page_config(
    page_title="El-Assistenten", 
    page_icon=app_icon, 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# INITIERA KAMERA-TILLSTÅND
if "show_camera" not in st.session_state: 
    st.session_state.show_camera = False

# --- OPTIMERING: CACHING AV TUNGA FUNKTIONER ---
@st.cache_resource(show_spinner=False)
def load_knowledge_base():
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
        return FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
    except Exception as e:
        return None

@st.cache_resource(show_spinner=False)
def get_chat_model():
    return ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0.0, max_retries=5, streaming=True)

vectorstore = load_knowledge_base()
chat_model = get_chat_model()

# --- 2. MOBILANPASSAD DESIGN OCH CSS ---
st.markdown("""
<style>
    .stApp, [data-testid="stSidebar"] { background-color: #0d014d !important; }
    p, li, label, h1, h2, h3, h4, h5, h6, .stMarkdown, div[data-testid="stChatMessageContent"] { color: #ffffff !important; }
    
    .pierfekta-header { 
        color: #82e300 !important; 
        font-weight: bold; 
        font-size: 1.8rem; 
        margin-bottom: 1rem; 
    }
    
    @media (max-width: 640px) {
        .pierfekta-header { font-size: 1.4rem; }
        .stButton > button { width: 100%; height: 3.5rem; font-size: 1.1rem !important; margin-bottom: 10px; }
        div[data-testid="stChatMessage"] { padding: 0.5rem !important; }
    }

    .highlight { color: #82e300 !important; font-weight: bold; }
    
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        background-color: rgba(0, 0, 0, 0.4) !important; color: white !important; border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .stButton > button { 
        background-color: rgba(0, 0, 0, 0.4) !important; 
        color: #ffffff !important; 
        border: 1px solid #82e300 !important; 
        border-radius: 8px;
    }
    
    img { max-width: 100%; height: auto; border-radius: 10px; box-shadow: 0px 4px 10px rgba(0,0,0,0.3); margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

# --- 3. SIDOMENYN & DÖRRVAKTEN ---
with st.sidebar:
    st.markdown("### 🛠️ Verktyg")
    if st.button("🧹 Rensa konversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    st.markdown("### 🔒 Personal-inloggning")
    admin_password = st.text_input("Lösenord:", type="password")
    is_admin = False
    
    if "ADMIN_PASSWORD" in st.secrets and admin_password == st.secrets["ADMIN_PASSWORD"]:
        is_admin = True
        st.success("✅ Admin-läge")
        st.divider()
        
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f: log_lines = f.readlines()
            unanswered = [line.strip().replace("- ", "") for line in log_lines if line.strip()]
            if unanswered:
                st.header("📝 Kunskaps-logg")
                selected_q = st.selectbox("Välj fråga:", unanswered)
                new_answer = st.text_area("Svar:", height=100)
                if st.button("Lär in fakta", use_container_width=True):
                    # Inlärningslogik
                    st.success("Fakta sparad!")

# --- 4. API-NYCKEL ---
if "GOOGLE_API_KEY" in st.secrets:
    os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]
else:
    google_api_key = st.sidebar.text_input("API-nyckel:", type="password")
    if not google_api_key: st.stop()
    os.environ["GOOGLE_API_KEY"] = google_api_key

# --- 5. HEADER ---
if os.path.exists(logo_path): st.image(logo_path, width=120)
st.markdown("<h1 class='pierfekta-header'>ISOLERABs Pierfekta El-Assistent</h1>", unsafe_allow_html=True)

if not vectorstore:
    st.error("⚠️ Databasen laddas... vänta några sekunder.")
    st.stop()

# --- 6. SMART MAGISK RENDERINGS-FUNKTION ---
def render_content(text):
    image_dir = os.path.join(current_dir, "bilder")
    
    # Hittar alla [BILD: x] och [KARTA: x] i texten och bygger in dem snyggt!
    parts = re.split(r'\[(BILD|KARTA):\s*([^\]]+)\]', text)
    
    for i in range(0, len(parts), 3):
        # Steg 1: Skriv ut den vanliga texten
        if parts[i].strip():
            st.markdown(parts[i].strip().replace("HIGHLIGHT:", "<span class='highlight'>").replace(":HIGHLIGHT", "</span>"), unsafe_allow_html=True)
        
        # Steg 2: Om det finns en special-tagg direkt efter texten
        if i + 1 < len(parts):
            tag_type = parts[i+1]
            content = parts[i+2].strip()
            
            # --- BYGGER BILD ---
            if tag_type == "BILD":
                actual_file = None
                if os.path.exists(image_dir):
                    for f in os.listdir(image_dir):
                        if f.lower() == content.lower():
                            actual_file = os.path.join(image_dir, f)
                            break
                if actual_file: st.image(actual_file, use_container_width=True)
                else:
                    try:
                        with open(img_log_path, "a", encoding="utf-8") as f: f.write(f"{content}\n")
                    except: pass
                    if is_admin: st.sidebar.warning(f"⚠️ Bild saknas: {content}")
            
            # --- BYGGER KART-KNAPP ---
            elif tag_type == "KARTA":
                maps_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(content)}"
                st.markdown(f'''
                    <a href="{maps_url}" target="_blank" style="text-decoration: none;">
                        <button style="width: 100%; height: 4rem; background-color: #82e300; color: #0d014d; font-weight: bold; border-radius: 8px; font-size: 1.1rem; border: none; cursor: pointer; margin-top: 15px; margin-bottom: 15px;">
                            📍 KÖR TILL: {content.upper()}<br>
                            <span style="font-size: 0.8rem; font-weight: normal;">(Allt material är med i bilen!)</span>
                        </button>
                    </a>
                ''', unsafe_allow_html=True)

# --- 7. AI-MOTOR (GEMINI 2.5 PRO MED MAGISKA KRAFTER) ---
system_prompt = (
    "Du är Isolerabs el-mentor. Svara med auktoritet och en peppande, kollegial ton.\n\n"
    "HUR DU ANVÄNDER DINA INBYGGDA VERKTYG:\n"
    "1. NAVIGERING & RUTT: Om användaren anger en adress, frågar efter vägen eller ska åka:\n"
    "   - Skriv FÖRST en tydlig och kaxig packlista i chatten med allt material som behövs för standardjobbet (Klamring till Aqua Stark IP44 vid healthbox, samt kabel, klammer, plugg, verktyg).\n"
    "   - Avsluta ditt svar EXAKT med taggen [KARTA: kundens adress] (t.ex. [KARTA: Storgatan 1]). Appen kommer bygga om detta till en stor grön knapp automatiskt!\n\n"
    "2. FÄRG-HJÄLP (KAMERA): Om användaren ber dig titta på en färg, använda kameran eller säger att de är färgblinda:\n"
    "   - Svara glatt att du fäller fram kameran och var uppmuntrande. Du MÅSTE inkludera taggen [KAMERA_AKTIVERAD] någonstans i ditt svar (appen döljer texten och slår igång linsen).\n\n"
    "3. QUIZET: Om användaren vill göra quizet eller testas:\n"
    "   - Du är nu Quizmaster! Ställ EN (1) fackmässig fråga om el, säkerhet eller material i taget. Ge svarsalternativ. Vänta på att användaren svarar, rätta dem pedagogiskt och gå sen vidare.\n\n"
    "REGLER BILDER:\n"
    "1. Leta ALLTID efter relevanta bilder i manualen.\n"
    "2. Inkludera ALLTID [BILD: aqua_stark_inkoppling.jpg] vid beskrivning av uttags-inkoppling.\n\n"
    "Manualer:\n{context}"
)
prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])

avatar_user = os.path.join(current_dir, "ikoner", "anvandare.png") if os.path.exists(os.path.join(current_dir, "ikoner", "anvandare.png")) else "👤"
avatar_bot = os.path.join(current_dir, "ikoner", "bot.png") if os.path.exists(os.path.join(current_dir, "ikoner", "bot.png")) else "🤖"

if "messages" not in st.session_state: st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar=(avatar_user if msg["role"]=="user" else avatar_bot)):
        render_content(msg["content"])

# --- 8. DOLDA KAMERAN (Träder fram vid [KAMERA_AKTIVERAD]) ---
if st.session_state.show_camera:
    st.warning("⚠️ **LIVSVIKTIGT:** Blixt och skuggor kan få mig att se fel färg. Kontrollmät alltid!")
    cam_photo = st.camera_input("Ta en bild på dosan/kablarna")
    if cam_photo:
        with st.spinner("Granskar bilden..."):
            try:
                img_b64 = base64.b64encode(cam_photo.getvalue()).decode()
                img_data = f"data:image/jpeg;base64,{img_b64}"
                vision_msg = HumanMessage(content=[
                    {"type": "text", "text": "Du är färg-tolk åt en färgblind elektriker. Beskriv vilka färger kablarna har baserat på deras placering. Var extra noga med rött, grönt och brunt."},
                    {"type": "image_url", "image_url": {"url": img_data}}
                ])
                vision_res = chat_model.invoke([vision_msg])
                st.session_state.messages.append({"role": "user", "content": "📸 *Skickade en bild för färganalys.*"})
                st.session_state.messages.append({"role": "assistant", "content": vision_res.content})
                st.session_state.show_camera = False # Dölj kameran igen
                st.rerun()
            except Exception:
                st.error("Kunde inte tyda bilden. Prova igen!")
    if st.button("❌ Avbryt kamera", use_container_width=True):
        st.session_state.show_camera = False
        st.rerun()

# --- 9. CHATT-INPUT ---
if query := st.chat_input("Fråga el-assistenten (eller be om en rutt/kamera)..."):
    if any(ord in query.lower() for ord in ["pierfekt", "tack", "bra jobbat"]): st.balloons()

    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user", avatar=avatar_user): st.write(query)
    
    with st.chat_message("assistant", avatar=avatar_bot):
        status_box = st.empty()
        status_box.markdown("*Tänker...*")
        try:
            retriever = vectorstore.as_retriever(search_kwargs={"k": 15})
            chain = create_retrieval_chain(retriever, create_stuff_documents_chain(chat_model, prompt))
            full_res = ""
            message_placeholder = st.empty()
            
            for chunk in chain.stream({"input": query}):
                if "answer" in chunk:
                    status_box.empty()
                    full_res += chunk["answer"]
                    # Dölj kamerakoden medan texten rinner in så den inte blinkar fult på skärmen
                    display_text = full_res.replace("[KAMERA_AKTIVERAD]", "")
                    message_placeholder.markdown(display_text, unsafe_allow_html=True)
            
            message_placeholder.empty()
            
            # --- TRIGGA MAGISKA FUNKTIONER I BAKGRUNDEN ---
            if "[KAMERA_AKTIVERAD]" in full_res:
                st.session_state.show_camera = True
                full_res = full_res.replace("[KAMERA_AKTIVERAD]", "")
            
            if "Jag hittar inte detta i manualerna" in full_res:
                try:
                    with open(log_path, "a", encoding="utf-8") as f: f.write(f"- {query}\n")
                except: pass
            
            render_content(full_res)
            st.session_state.messages.append({"role": "assistant", "content": full_res})
            
            # Om kameran slogs på, starta om sidan direkt så linsen öppnas!
            if st.session_state.show_camera:
                st.rerun()
                
        except Exception as e:
            st.error("Tekniskt fel.")
