import streamlit as st
import os
import re
import base64
import time
import random
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
    # VIKTIGT: Vi använder Gemini 2.5 Pro som motor
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
        .stMarkdown p { font-size: 1.05rem; }
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
        st.success("✅ Inloggad som Admin")
        st.divider()
        
        # FULLSTÄNDIG LOGIK FÖR SAKNADE FRÅGOR
        log_lines = []
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                log_lines = f.readlines()
        unanswered_qs = [line.strip().replace("- ", "") for line in log_lines if line.strip()]
        
        if unanswered_qs:
            st.header("📝 Kunskaps-logg")
            selected_q = st.selectbox("Välj fråga att besvara:", unanswered_qs)
            new_answer = st.text_area("Skriv Isolerabs officiella svar:", height=150)
            if st.button("Lär in fakta", use_container_width=True):
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
                        st.success("✅ Fakta inlärd!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Kunde inte spara: {e}")
        else:
            st.info("Inga obesvarade frågor i loggen.")
        
        st.divider()
        
        # FULLSTÄNDIG LOGIK FÖR BILD-LOGG
        if os.path.exists(img_log_path):
            st.header("📸 Önskade Bilder")
            with open(img_log_path, "r", encoding="utf-8") as f:
                imgs = list(set(f.readlines()))
            if imgs:
                st.info("AI:n letade efter dessa bilder men hittade dem inte:")
                for img in imgs: st.code(img.strip())
                if st.button("Rensa bild-logg", use_container_width=True):
                    os.remove(img_log_path)
                    st.rerun()
            else:
                st.write("Inga saknade bilder loggade.")

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
    st.error("⚠️ Databasen laddas... vänligen vänta.")
    st.stop()

# --- 6. BILDFUNKTION ---
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
            
            if actual_file:
                st.image(actual_file, use_container_width=True)
            else:
                try:
                    with open(img_log_path, "a", encoding="utf-8") as f: f.write(f"{content}\n")
                except: pass
                if is_admin: st.sidebar.warning(f"⚠️ Bild saknas i mappen: {content}")

# --- 7. AI-MOTOR (GEMINI 2.5 PRO) ---
system_prompt = (
    "Du är Isolerabs el-mentor och materialexpert. Svara med auktoritet och precision.\n\n"
    "REGLER FÖR BILDER:\n"
    "1. DU SKA VARA VISUELL: För varje instruktionssteg du skriver, leta aktivt efter en bild i manualerna som kan illustrera det du pratar om.\n"
    "2. INGA FANTASIBILDER: Använd ENDAST exakta filnamn som finns i manualerna (t.ex. [BILD: aqua_stark_inkoppling.jpg]). Skapa aldrig egna namn.\n"
    "3. AQUA STARK: När du förklarar inkopplingen av vägguttaget Aqua Stark, MÅSTE du inkludera taggen [BILD: aqua_stark_inkoppling.jpg] under det steget.\n"
    "4. MERMAID: Du får ALDRIG rita egna scheman med Mermaid.\n\n"
    "REGLER FÖR MATERIAL:\n"
    "1. Utgå alltid från Aqua Stark IP44 vid frågor om uttag. Förklara inkopplingen steg-för-steg.\n"
    "2. Hämta materialfakta från katalogen. Förklara fördelar som tidsvinst och säkerhet.\n\n"
    "ALLMÄNT:\n"
    "1. Om du inte hittar svaret i Isolerabs manualer, inled med: 'Jag hittar inte detta i manualerna, men som din el-mentor rekommenderar jag följande:'.\n"
    "2. Svara alltid på svenska och var peppande.\n\n"
    "Expertkunskap (Manualer & Materialkatalog):\n{context}"
)
prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])

avatar_user = os.path.join(current_dir, "ikoner", "anvandare.png") if os.path.exists(os.path.join(current_dir, "ikoner", "anvandare.png")) else "👤"
avatar_bot = os.path.join(current_dir, "ikoner", "bot.png") if os.path.exists(os.path.join(current_dir, "ikoner", "bot.png")) else "🤖"

if "messages" not in st.session_state: st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar=(avatar_user if msg["role"]=="user" else avatar_bot)):
        render_content(msg["content"])

if query := st.chat_input("Fråga el-assistenten..."):
    # Easter eggs!
    if any(ord in query.lower() for ord in ["pierfekt", "tack", "bra jobbat"]): st.balloons()

    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user", avatar=avatar_user): st.write(query)
    
    with st.chat_message("assistant", avatar=avatar_bot):
        status_box = st.empty()
        status_texts = [
            "*Gräver djupt i Isolerabs manualer...*",
            "*Kopplar rätt trådar för att ge dig ett bra svar...*",
            "*Laddar upp lite extra spänning inför svaret...*",
            "*Bläddrar frenetiskt i Ahlsell-katalogen...*",
            "*Beräknar det mest pierfekta svaret...*"
        ]
        status_box.markdown(random.choice(status_texts))
        
        try:
            # Vi knackar hårt på dörren med k=15
            retriever = vectorstore.as_retriever(search_kwargs={"k": 15})
            chain = create_retrieval_chain(retriever, create_stuff_documents_chain(chat_model, prompt))
            
            full_res = "⚠️ **VIKTIGT:** *Är du minsta osäker, kontakta alltid din elansvarige!*\n\n"
            message_placeholder = st.empty()
            
            for chunk in chain.stream({"input": query}):
                if "answer" in chunk:
                    status_box.empty()
                    full_res += chunk["answer"]
                    message_placeholder.markdown(full_res, unsafe_allow_html=True)
            
            message_placeholder.empty()
            
            # Logga frågor som AI:n inte hittade i manualerna
            if "Jag hittar inte detta i manualerna" in full_res:
                try:
                    with open(log_path, "a", encoding="utf-8") as f: f.write(f"- {query}\n")
                except: pass
            
            render_content(full_res)
            st.session_state.messages.append({"role": "assistant", "content": full_res})
            
        except Exception as e:
            # Töm rutorna vid fel
            if 'status_box' in locals(): status_box.empty()
            if 'message_placeholder' in locals(): message_placeholder.empty()
            
            # DIAGNOSTIK: Visa exakt vad som hände med Google API
            st.error("❌ Ett tekniskt fel uppstod i kommunikationen med Google:")
            st.code(str(e))
