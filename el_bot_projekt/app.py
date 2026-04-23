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
    # VIKTIGT: Vi använder nu Gemini 2.5 Pro som huvudmotor
    return ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0.0, max_retries=5, streaming=True)

vectorstore = load_knowledge_base()
chat_model = get_chat_model()

# --- 2. MOBILANPASSAD DESIGN OCH CSS ---
st.markdown("""
<style>
    /* Grundfärger Isolerab Blå */
    .stApp, [data-testid="stSidebar"] { background-color: #0d014d !important; }
    p, li, label, h1, h2, h3, h4, h5, h6, .stMarkdown, div[data-testid="stChatMessageContent"] { color: #ffffff !important; }
    
    /* Header-stil Pierfekt Grön */
    .pierfekta-header { 
        color: #82e300 !important; 
        font-weight: bold; 
        font-size: 1.8rem; 
        margin-bottom: 1rem; 
    }
    
    /* Mobilanpassning - Större knappar och bättre text */
    @media (max-width: 640px) {
        .pierfekta-header { font-size: 1.4rem; }
        .stButton > button { width: 100%; height: 3.5rem; font-size: 1.1rem !important; margin-bottom: 10px; }
        div[data-testid="stChatMessage"] { padding: 0.5rem !important; }
        .stMarkdown p { font-size: 1.05rem; }
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
    
    img { max-width: 100%; height: auto; border-radius: 10px; box-shadow: 0px 4px 10px rgba(0,0,0,0.3); }
</style>
""", unsafe_allow_html=True)

# --- 3. DÖRRVAKTEN & SIDOMENYN ---
with st.sidebar:
    st.markdown("### 🛠️ Verktyg")
    
    # Knapp för att rensa chatten
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
        
        # Sektion för saknade frågor
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
                    except: st.error("Kunde inte spara.")
        
        st.divider()
        # Sektion för bild-logg
        if os.path.exists(img_log_path):
            st.header("📸 Önskade Bilder")
            with open(img_log_path, "r", encoding="utf-8") as f:
                imgs = list(set(f.readlines()))
            if imgs:
                st.info("AI:n efterfrågade dessa bilder:")
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

# --- 6. BILDFUNKTION (ENBART RIKTIGA BILDER) ---
def render_content(text):
    image_dir = os.path.join(current_dir, "bilder")
    # Vi har tagit bort Mermaid helt. Letar bara efter [BILD: ...]
    parts = re.split(r'\[(?:BILD):\s*([\s\S]+?)\]', text)
    for i, part in enumerate(parts):
        if i % 2 == 0:
            if part.strip():
                st.markdown(part.strip().replace("HIGHLIGHT:", "<span class='highlight'>").replace(":HIGHLIGHT", "</span>"), unsafe_allow_html=True)
        else:
            content = part.strip()
            if any(content.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif']):
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
                    # Logga tyst om bilden saknas
                    try:
                        with open(img_log_path, "a", encoding="utf-8") as f: f.write(f"{content}\n")
                    except: pass
                    if is_admin: st.sidebar.warning(f"⚠️ Bild saknas i mappen: {content}")

# --- 7. AI-MOTOR OCH CHATT ---
system_prompt = (
    "Du är Isolerabs el-mentor och materialexpert. Svara med auktoritet, precision och erfarenhet.\n\n"
    "REGLER FÖR BILDER:\n"
    "1. Du får ABSOLUT INTE hitta på egna filnamn för bilder. Använd ENDAST [BILD: filnamn.jpg] om det exakta filnamnet står angivet i manualen du läser.\n"
    "2. Du får ALDRIG rita egna scheman eller använda Mermaid. Om en bild saknas, förklara med tydlig text istället.\n\n"
    "REGLER FÖR MATERIAL:\n"
    "1. Vid frågor om vägguttag, utgå ALLTID från Aqua Stark IP44 (Isolerabs standard). Förklara inkopplingen noggrant steg-för-steg.\n"
    "2. Hämta materialfakta från katalogen. Förklara fördelar som tidsvinst och säkerhet.\n\n"
    "ALLMÄNT:\n"
    "1. Om du inte hittar svaret i Isolerabs manualer, inled med: 'Jag hittar inte detta i manualerna, men som din el-mentor rekommenderar jag följande:'.\n"
    "2. Svara alltid på svenska och var peppande.\n\n"
    "Expertkunskap (Manualer & Materialkatalog):\n{context}"
)
prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])

if "messages" not in st.session_state: st.session_state.messages = []

# Rita ut chatthistoriken
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar=(avatar_user if msg["role"]=="user" else avatar_bot)):
        render_content(msg["content"])

# Chat-input
if query := st.chat_input("Fråga el-assistenten..."):
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
            
            safety_warning = "⚠️ **VIKTIGT:** *Är du minsta osäker, kontakta alltid din elansvarige innan du börjar skruva!*\n\n"
            full_res = safety_warning
            message_placeholder = st.empty()
            
            # Streaming-loop
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
            
            # Rendera färdigt svar med bilder
            render_content(full_res)
            st.session_state.messages.append({"role": "assistant", "content": full_res})
            
        except Exception as e:
            # Töm rutorna vid fel
            if 'status_box' in locals(): status_box.empty()
            if 'message_placeholder' in locals(): message_placeholder.empty()
            
            # DIAGNOSTIK: Visa exakt vad som hände med Google API
            st.error("❌ Ett tekniskt fel uppstod i kommunikationen med Google:")
            st.code(str(e))
