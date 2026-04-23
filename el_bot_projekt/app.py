import streamlit as st
import os
import re
import base64
import time
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
img_log_path = os.path.join(current_dir, "saknade_bilder.txt") # Ny logg för bilder
logo_path = os.path.join(current_dir, "bilder", "logo.png")
index_path = os.path.join(current_dir, "faiss_index")

try:
    app_icon = Image.open(logo_path)
except:
    app_icon = "⚡"

st.set_page_config(page_title="El-Assistenten", page_icon=app_icon, layout="centered")

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
    # Använder den snabbaste 1.5-flash modellen
    return ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.0, max_retries=5)

vectorstore = load_knowledge_base()
chat_model = get_chat_model()

# --- 2. DESIGN OCH FÄRGSCHEMA ---
st.markdown("""
<style>
    .stApp, [data-testid="stSidebar"] { background-color: #0d014d !important; }
    p, li, label, h1, h2, h3, h4, h5, h6, .stMarkdown, div[data-testid="stChatMessageContent"] { color: #ffffff !important; }
    .pierfekta-header { color: #82e300 !important; font-weight: bold; font-size: 2.5rem; margin-bottom: 1rem; }
    .highlight { color: #82e300 !important; font-weight: bold; }
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        background-color: rgba(0, 0, 0, 0.4) !important; color: white !important; border: 1px solid rgba(255, 255, 255, 0.2);
    }
    .stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus { border-color: #82e300 !important; }
    .stButton > button { background-color: rgba(0, 0, 0, 0.4) !important; color: #ffffff !important; border: 1px solid #82e300 !important; }
</style>
""", unsafe_allow_html=True)

# --- 3. DÖRRVAKTEN & SIDOMENYN (Uppdaterad med bildlogg) ---
with st.sidebar:
    st.markdown("### 🔒 Personal-inloggning")
    admin_password = st.text_input("Lösenord:", type="password")
    is_admin = False
    
    if "ADMIN_PASSWORD" in st.secrets and admin_password == st.secrets["ADMIN_PASSWORD"]:
        is_admin = True
        st.success("✅ Inloggad som Pierfekt Admin")
        st.divider()
        
        # Sektion för saknade frågor
        log_lines = []
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                log_lines = f.readlines()
        unanswered_qs = [line.strip().replace("- ", "") for line in log_lines if line.strip()]
        
        st.header("📝 Kunskaps-logg")
        if unanswered_qs:
            st.text_area("Frågor att åtgärda:", "\n".join(unanswered_qs), height=100)
            if st.button("Rensa frågor"):
                if os.path.exists(log_path): os.remove(log_path)
                st.rerun()
        else:
            st.info("Inga frågor loggade.")

        st.divider()

        # NY SEKTION: Saknade Bilder
        img_log_lines = []
        if os.path.exists(img_log_path):
            with open(img_log_path, "r", encoding="utf-8") as f:
                img_log_lines = list(set(f.readlines())) # Endast unika namn
        
        missing_imgs = [l.strip() for l in img_log_lines if l.strip()]
        
        st.header("📸 Önskade Bilder")
        if missing_imgs:
            st.markdown("AI:n vill visa dessa bilder. Skapa dem och lägg i `/bilder`:")
            for img_name in missing_imgs:
                st.code(img_name)
            if st.button("Rensa bild-listan"):
                if os.path.exists(img_log_path): os.remove(img_log_path)
                st.rerun()
        else:
            st.info("Inga bild-önskemål än.")
            
    elif admin_password:
        st.error("Fel lösenord")

# --- 4. API-NYCKEL ---
if "GOOGLE_API_KEY" in st.secrets:
    os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]
else:
    google_api_key = st.sidebar.text_input("API-nyckel:", type="password")
    if not google_api_key: st.stop()
    os.environ["GOOGLE_API_KEY"] = google_api_key

# --- 5. HEADER ---
if os.path.exists(logo_path): st.image(logo_path, width=150)
st.markdown("<h1 class='pierfekta-header'>ISOLERABs Pierfekta El-Assistent</h1>", unsafe_allow_html=True)

if not vectorstore:
    st.error("⚠️ Systemet uppdateras, försök igen snart.")
    st.stop()

# --- 6. RIT- OCH BILDFUNKTION (Uppdaterad för tyst loggning) ---
def render_content(text):
    image_dir = os.path.join(current_dir, "bilder")
    parts = re.split(r'\[(?:VISA_BILD|BILD|SCHEMA):\s*([\s\S]+?)\]', text)
    for i, part in enumerate(parts):
        if i % 2 == 0:
            if part.strip():
                st.markdown(part.strip().replace("HIGHLIGHT:", "<span class='highlight'>").replace(":HIGHLIGHT", "</span>"), unsafe_allow_html=True)
        else:
            content = part.strip()
            # Om det är en bildfil
            if any(content.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif']):
                img_path = os.path.join(image_dir, content)
                if os.path.exists(img_path):
                    st.image(img_path, use_container_width=True)
                else:
                    # Logga den saknade bilden i bakgrunden utan att varna användaren
                    try:
                        existing_log = ""
                        if os.path.exists(img_log_path):
                            with open(img_log_path, "r", encoding="utf-8") as f: existing_log = f.read()
                        
                        if content not in existing_log:
                            with open(img_log_path, "a", encoding="utf-8") as f: f.write(f"{content}\n")
                    except: pass
            else:
                # Mermaid Diagram
                components.html(f"<pre class='mermaid'>{content}</pre><script type='module'>import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';mermaid.initialize({{startOnLoad:true,theme:'dark',securityLevel:'loose'}});</script>", height=400, scrolling=True)

# (Här lämnas quiz_data oförändrat från din version...)
quiz_data = [
    # Dina 60 frågor här...
]

# (Här lämnas quiz-logiken i expandern oförändrad...)

# --- 7. AI-MOTOR OCH CHATT (Uppdaterad för streaming och art-direction) ---
system_prompt = (
    "Du är Isolerabs el-mentor och materialexpert. Din uppgift är att svara med auktoritet, fakta och expertis.\n\n"
    "REGLER FÖR BILDER:\n"
    "1. Om du förklarar något som vinner på att visas (t.ex. ett specifikt material, en koppling eller en asbest-risk), föreslå en bild genom att skriva [BILD: beskrivande_namn.jpg].\n"
    "2. Du behöver inte veta om bilden finns; systemet loggar ditt förslag så att chefen kan skapa bilden senare.\n\n"
    "REGLER FÖR MATERIAL & INKÖP:\n"
    "1. Vid förfrågan om inköpslista: Hämta ALLT från '24_materialkatalog_ahlsell.md'. Missa ingenting.\n"
    "2. Förklara VARFÖR vi valt materialet (fördelar, tips, tidsvinst).\n\n"
    "Expertkunskap (Manualer & Materialkatalog):\n{context}"
)
prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])

if "messages" not in st.session_state: st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar=(avatar_user if msg["role"]=="user" else avatar_bot)):
        render_content(msg["content"])

if query := st.chat_input("Ställ din fråga..."):
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user", avatar=avatar_user): st.write(query)
    
    with st.chat_message("assistant", avatar=avatar_bot):
        with st.spinner("Tänker..."):
            try:
                retriever = vectorstore.as_retriever(search_kwargs={"k": 15})
                chain = create_retrieval_chain(retriever, create_stuff_documents_chain(chat_model, prompt))
                
                safety_warning = "⚠️ **VIKTIGT:** *Jag är en AI-assistent. Är du minsta osäker MÅSTE du kontakta elansvarig innan arbete utförs!*\n\n"
                full_res = safety_warning
                
                # Streaming-output
                placeholder = st.empty()
                placeholder.markdown(full_res + "▌")
                
                for chunk in chain.stream({"input": query}):
                    if "answer" in chunk:
                        full_res += chunk["answer"]
                        placeholder.markdown(full_res + "▌")
                
                placeholder.empty()
                
                # Logga saknade svar
                if "Jag hittar inte detta i Isolerabs manualer" in full_res:
                    with open(log_path, "a", encoding="utf-8") as f: f.write(f"- {query}\n")

                render_content(full_res)
                st.session_state.messages.append({"role": "assistant", "content": full_res})
                
            except Exception as e:
                st.error(f"Ett fel uppstod. Försök igen om en liten stund.")
