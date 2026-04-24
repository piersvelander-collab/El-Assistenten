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

# --- 5.1 NYTT VERKTYG: RUTT & PACKLISTA ---
st.markdown("### 🚗 Nästa Jobb: Rutt & Packlista")
with st.expander("Klicka här när du ska åka till nästa kund", expanded=False):
    st.info("Vi kör standardjobbet: Klamring till uttag vid healthbox.")
    dest_address = st.text_input("Skriv in kundens adress:")
    
    st.markdown("---")
    st.warning("⚠️ **Har du allt det här i bilen?**")
    st.markdown("""
    * **Vägguttag:** Aqua Stark IP44
    * **Kabel:** EKLK / EXQ (Tillräcklig längd)
    * **Fästmaterial:** Klammer, skruv & plugg
    * **Verktyg:** Skruvdragare, skalare, multimeter
    """)
    
    # Visar knappen direkt när de fyllt i en adress!
    if dest_address:
        maps_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(dest_address)}"
        st.markdown(f"""
            <a href="{maps_url}" target="_blank">
                <button style="width: 100%; height: 3.5rem; background-color: #82e300; color: #0d014d; font-weight: bold; border-radius: 8px; font-size: 1.1rem; border: none; cursor: pointer;">
                    ✅ ALLT I BILEN, NU ÅKER VI!
                </button>
            </a>
        """, unsafe_allow_html=True)

# --- 6. ÖVRIGA VERKTYG (KAMERA & QUIZ) ---
with st.expander("📸 Färg-Hjälpen (Kamera)"):
    cam_photo = st.camera_input("Ta en bild på kablarna")
    if cam_photo and st.button("Analysera färgerna", use_container_width=True):
        st.info("Analyserar färgerna...")

# --- 7. BILDFUNKTION ---
def render_content(text):
    image_dir = os.path.join(current_dir, "bilder")
    parts = re.split(r'\[(?:BILD):\s*([\s\S]+?)\]', text)
    for i, part in enumerate(parts):
        if i % 2 == 0:
            if part.strip():
                st.markdown(part.strip().replace("HIGHLIGHT:", "<span class='highlight'>").replace(":HIGHLIGHT", "</span>"), unsafe_allow_html=True)
        else:
            content = part.strip()
            actual_file = None
            if os.path.exists(image_dir):
                for f in os.listdir(image_dir):
                    if f.lower() == content.lower():
                        actual_file = os.path.join(image_dir, f)
                        break
            if actual_file: st.image(actual_file, use_container_width=True)
            else:
                with open(img_log_path, "a", encoding="utf-8") as f: f.write(f"{content}\n")

# --- 8. AI-MOTOR (GEMINI 2.5 PRO) ---
system_prompt = (
    "Du är Isolerabs el-mentor. Svara med auktoritet.\n\n"
    "REGLER BILDER:\n"
    "1. DU SKA VARA VISUELL: Leta alltid efter bilder i manualerna för att illustrera steg.\n"
    "2. AQUA STARK: Inkludera ALLTID [BILD: aqua_stark_inkoppling.jpg] vid inkoppling av uttag.\n\n"
    "Standardjobbet är alltid klamring av kabel till ett Aqua Stark-uttag vid en healthbox.\n"
    "Manualer:\n{context}"
)
prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])

avatar_user = os.path.join(current_dir, "ikoner", "anvandare.png") if os.path.exists(os.path.join(current_dir, "ikoner", "anvandare.png")) else "👤"
avatar_bot = os.path.join(current_dir, "ikoner", "bot.png") if os.path.exists(os.path.join(current_dir, "ikoner", "bot.png")) else "🤖"

if "messages" not in st.session_state: st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar=(avatar_user if msg["role"]=="user" else avatar_bot)):
        render_content(msg["content"])

if query := st.chat_input("Fråga el-assistenten..."):
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user", avatar=avatar_user): st.write(query)
    
    with st.chat_message("assistant", avatar=avatar_bot):
        status_box = st.empty()
        status_box.markdown("*Gräver i manualerna...*")
        try:
            retriever = vectorstore.as_retriever(search_kwargs={"k": 15})
            chain = create_retrieval_chain(retriever, create_stuff_documents_chain(chat_model, prompt))
            full_res = "⚠️ **VIKTIGT:** *Är du minsta osäker, kontakta elansvarig!*\n\n"
            message_placeholder = st.empty()
            for chunk in chain.stream({"input": query}):
                if "answer" in chunk:
                    status_box.empty()
                    full_res += chunk["answer"]
                    message_placeholder.markdown(full_res, unsafe_allow_html=True)
            message_placeholder.empty()
            render_content(full_res)
            st.session_state.messages.append({"role": "assistant", "content": full_res})
        except Exception as e:
            st.error("Tekniskt fel.")
