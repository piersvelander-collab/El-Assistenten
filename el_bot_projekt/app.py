import streamlit as st
import os
import re
import base64
import time
import random
from PIL import Image
import streamlit.components.v1 as components
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
    initial_sidebar_state="collapsed" # Sparar plats på mobilen vid start
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
    # Använder PRO-modellen för maximal stabilitet och logik
    return ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.0, max_retries=5, streaming=True)

vectorstore = load_knowledge_base()
chat_model = get_chat_model()

# --- 2. MOBILANPASSAD DESIGN OCH CSS ---
st.markdown("""
<style>
    /* Grundfärger */
    .stApp, [data-testid="stSidebar"] { background-color: #0d014d !important; }
    p, li, label, h1, h2, h3, h4, h5, h6, .stMarkdown, div[data-testid="stChatMessageContent"] { color: #ffffff !important; }
    
    /* Header-stil */
    .pierfekta-header { 
        color: #82e300 !important; 
        font-weight: bold; 
        font-size: 1.8rem; /* Något mindre för mobilen */
        margin-bottom: 1rem; 
    }
    
    /* Mobilanpassning */
    @media (max-width: 640px) {
        .pierfekta-header { font-size: 1.4rem; }
        .stButton > button { width: 100%; height: 3rem; font-size: 1.1rem !important; }
        div[data-testid="stChatMessage"] { padding: 0.5rem !important; }
    }

    .highlight { color: #82e300 !important; font-weight: bold; }
    
    /* Input-fält */
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        background-color: rgba(0, 0, 0, 0.4) !important; color: white !important; border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    /* Knappar */
    .stButton > button { 
        background-color: rgba(0, 0, 0, 0.4) !important; 
        color: #ffffff !important; 
        border: 1px solid #82e300 !important; 
        border-radius: 8px;
    }
    
    /* Bilder */
    img { max-width: 100%; height: auto; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 3. DÖRRVAKTEN & SIDOMENYN ---
with st.sidebar:
    st.markdown("### 🛠️ Verktyg")
    
    # --- NY FUNKTION: RENSA CHATT ---
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
        
        # Logg för saknade frågor
        log_lines = []
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                log_lines = f.readlines()
        unanswered_qs = [line.strip().replace("- ", "") for line in log_lines if line.strip()]
        
        if unanswered_qs:
            st.header("📝 Kunskaps-logg")
            selected_q = st.selectbox("Välj fråga:", unanswered_qs)
            new_answer = st.text_area("Skriv svar:", height=100)
            if st.button("Lär in fakta"):
                if new_answer.strip():
                    try:
                        md_content = f"# Svar gällande: {selected_q}\n\n{new_answer}"
                        if vectorstore: vectorstore.add_texts([md_content])
                        
                        docs_dir = os.path.join(current_dir, "dokument")
                        if not os.path.exists(docs_dir): os.makedirs(docs_dir)
                        with open(os.path.join(docs_dir, f"inlart_{int(time.time())}.md"), "w", encoding="utf-8") as f:
                            f.write(md_content)
                        
                        unanswered_qs.remove(selected_q)
                        with open(log_path, "w", encoding="utf-8") as f:
                            for q in unanswered_qs: f.write(f"- {q}\n")
                        st.success("Inlärt!")
                        st.rerun()
                    except: st.error("Fel vid sparande.")
        
        st.divider()
        # Logg för bilder
        if os.path.exists(img_log_path):
            st.header("📸 Önskade Bilder")
            with open(img_log_path, "r", encoding="utf-8") as f:
                imgs = list(set(f.readlines()))
            for img in imgs: st.code(img.strip())
            if st.button("Rensa bild-logg"):
                os.remove(img_log_path)
                st.rerun()

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
    st.error("⚠️ Systemet laddas... vänta några sekunder.")
    st.stop()

# (Här lämnas Quizzet och Färg-hjälpen oförändrade från tidigare stabil version...)

# --- 6. RIT- OCH BILDFUNKTION ---
def render_content(text):
    image_dir = os.path.join(current_dir, "bilder")
    parts = re.split(r'\[(?:VISA_BILD|BILD|SCHEMA):\s*([\s\S]+?)\]', text)
    for i, part in enumerate(parts):
        if i % 2 == 0:
            if part.strip():
                st.markdown(part.strip().replace("HIGHLIGHT:", "<span class='highlight'>").replace(":HIGHLIGHT", "</span>"), unsafe_allow_html=True)
        else:
            content = part.strip()
            if any(content.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif']):
                # Smart sökning (ignorerar stora/små bokstäver)
                actual_file = None
                if os.path.exists(image_dir):
                    try:
                        for f in os.listdir(image_dir):
                            if f.lower() == content.lower():
                                actual_file = os.path.join(image_dir, f)
                                break
                    except: pass
                
                if actual_file:
                    st.image(actual_file, use_container_width=True)
                else:
                    with open(img_log_path, "a", encoding="utf-8") as f: f.write(f"{content}\n")
                    if is_admin: st.sidebar.warning(f"Saknas: {content}")
            else:
                # Mermaid Diagram med extra stabilitet
                clean_mermaid = content.replace('"', "'") # Mermaid gillar inte dubbla citationstecken
                components.html(f"<pre class='mermaid'>{clean_mermaid}</pre><script type='module'>import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';mermaid.initialize({{startOnLoad:true,theme:'dark',securityLevel:'loose'}});</script>", height=400, scrolling=True)

# --- 7. AI-MOTOR OCH CHATT ---
import random

system_prompt = (
    "Du är Isolerabs el-mentor och materialexpert. Svara med auktoritet och fakta.\n\n"
    "REGLER BILDER & SCHEMAN:\n"
    "1. Använd ENDAST [BILD: filnamn.jpg] om det står i manualen. Skriv aldrig 'filnamn.jpg' som placeholder.\n"
    "2. Om illustration behövs men bild saknas: Använd [SCHEMA: graph TD...]. Inled alltid koden med 'graph TD' eller 'graph LR'. Använd radbrytningar.\n\n"
    "REGLER MATERIAL:\n"
    "1. Vid frågor om uttag, utgå från Aqua Stark IP44 (Standard). Förklara inkopplingen noggrant.\n"
    "2. Hämta ALLT material från katalogen vid förfrågan. Förklara fördelar och tips.\n\n"
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
    if any(ord in query.lower() for ord in ["pierfekt", "tack", "bra jobbat"]): st.balloons()
        
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user", avatar=avatar_user): st.write(query)
    
    with st.chat_message("assistant", avatar=avatar_bot):
        status_box = st.empty()
        status_texts = ["*Gräver i manualerna...*", "*Kopplar trådarna...*", "*Laddar upp svaret...*", "*Bläddrar i Ahlsell-katalogen...*"]
        status_box.markdown(random.choice(status_texts))
        
        try:
            retriever = vectorstore.as_retriever(search_kwargs={"k": 15})
            chain = create_retrieval_chain(retriever, create_stuff_documents_chain(chat_model, prompt))
            
            safety_warning = "⚠️ **SÄKERHET:** *Är du minsta osäker, kontakta elansvarig!*\n\n"
            full_res = safety_warning
            message_placeholder = st.empty()
            
            for chunk in chain.stream({"input": query}):
                if "answer" in chunk:
                    status_box.empty()
                    full_res += chunk["answer"]
                    message_placeholder.markdown(full_res, unsafe_allow_html=True)
            
            message_placeholder.empty()
            if "Jag hittar inte detta i Isolerabs manualer" in full_res:
                with open(log_path, "a", encoding="utf-8") as f: f.write(f"- {query}\n")
            
            render_content(full_res)
            st.session_state.messages.append({"role": "assistant", "content": full_res})
            
        except Exception as e:
            st.error("Ett fel uppstod i kommunikationen med Google. Prova igen om en stund.")
            if is_admin: st.code(str(e))
