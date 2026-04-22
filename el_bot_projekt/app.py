import streamlit as st
import os
import re
import streamlit.components.v1 as components
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate

# --- 1. SIDKONFIGURATION OCH BRANDING ---
st.set_page_config(page_title="Isolerab El-Assistent", page_icon="⚡", layout="centered")

current_dir = os.path.dirname(os.path.abspath(__file__))
log_path = os.path.join(current_dir, "saknade_fragor.txt")

# --- 2. DESIGN OCH FÄRGSCHEMA (Korrigerad för Isolerab-grön rubrik) ---
st.markdown("""
<style>
    .stApp, [data-testid="stSidebar"] { 
        background-color: #0d014d !important; 
    }
    
    /* Vit text för chatt och listor, men vi exkluderar h1 härifrån */
    p, li, label, .stMarkdown, div[data-testid="stChatMessageContent"] { 
        color: #ffffff !important; 
    }
    
    /* Specifik färg för rubriken: Isolerab-grön (#82e300) */
    .pierfekta-header {
        color: #82e300 !important;
        font-weight: bold;
        font-size: 2.5rem;
        margin-bottom: 1rem;
    }
    
    .highlight { color: #82e300 !important; font-weight: bold; }
    
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        background-color: rgba(0, 0, 0, 0.4) !important; 
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus {
        border-color: #82e300 !important; 
    }
    
    .stButton > button {
        background-color: rgba(0, 0, 0, 0.4) !important;
        color: #ffffff !important;
        border: 1px solid #82e300 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. SIDOMENY ---
with st.sidebar:
    st.header("📝 Kunskaps-logg")
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            log_content = f.read()
        st.text_area("Behöver skrivas manualer för:", log_content, height=200)
        if st.button("Rensa logg"):
            os.remove(log_path)
            st.rerun()
    else:
        st.info("Inga frågor loggade ännu.")
    st.divider()
    st.header("🛠 Felsökning")
    if st.checkbox("Visa hittade filer (Debug)"):
        img_dir = os.path.join(current_dir, "bilder")
        if os.path.exists(img_dir):
            st.write(f"Filer i /bilder: {os.listdir(img_dir)}")

# --- 4. API-NYCKEL ---
if "GOOGLE_API_KEY" in st.secrets:
    google_api_key = st.secrets["GOOGLE_API_KEY"]
else:
    google_api_key = st.sidebar.text_input("API-nyckel:", type="password")

if not google_api_key:
    st.info("👈 Vänligen klistra in din Google API-nyckel i sidomenyn.")
    st.stop()
os.environ["GOOGLE_API_KEY"] = google_api_key

# --- 5. RENDERERA HEADER (Logga + Den nya gröna titeln) ---
logo_path = os.path.join(current_dir, "bilder", "logo.png")
if os.path.exists(logo_path):
    st.image(logo_path, width=150)

# Här är din nya Isolerab-gröna och personliga rubrik
st.markdown("<h1 class='pierfekta-header'>ISOLERABs Pierfekta El-Assistent</h1>", unsafe_allow_html=True)

# --- 6. RIT- OCH BILDFUNKTION ---
def render_content(text):
    image_dir = os.path.join(current_dir, "bilder")
    pattern = r'\[(?:VISA_BILD|BILD|SCHEMA):\s*([\s\S]+?)\]'
    parts = re.split(pattern, text)
    for i, part in enumerate(parts):
        if i % 2 == 0:
            if part.strip():
                h_text = part.strip().replace("HIGHLIGHT:", "<span class='highlight'>").replace(":HIGHLIGHT", "</span>")
                st.markdown(h_text, unsafe_allow_html=True)
        else:
            content = part.strip()
            if any(content.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif']):
                img_path = os.path.join(image_dir, content)
                if os.path.exists(img_path): st.image(img_path, use_container_width=True)
                else: st.warning(f"⚠️ Hittar inte: {content}")
            else:
                html_code = f"<pre class='mermaid'>{content}</pre><script type='module'>import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';mermaid.initialize({{startOnLoad:true,theme:'dark',securityLevel:'loose'}});</script>"
                components.html(html_code, height=500, scrolling=True)

# --- 7. HUVUDPROGRAM ---
index_path = os.path.join(current_dir, "faiss_index")
try:
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    vectorstore = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
except Exception as e:
    st.error(f"Kunde inte ladda expertkunskap: {e}")
    st.stop()

chat_model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0, max_retries=5)

system_prompt = (
    "Du är Isolerabs el-mentor. Din uppgift är att svara med fakta.\n"
    "REGLER:\n1. Om användaren vill se en bild, använd: [BILD: filnamn.jpg]\n"
    "2. Om användaren vill rita, använd Mermaid i: [SCHEMA: graph TD...]\n"
    "3. Om du inte hittar svar i dokumenten, inled med: 'Jag hittar inte detta i Isolerabs manualer, men min generella kunskap säger följande:'\n"
    "4. Svara på svenska.\n\nExpertkunskap:\n{context}"
)

prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])

avatar_user_path = os.path.join(current_dir, "ikoner", "anvandare.png")
avatar_bot_path = os.path.join(current_dir, "ikoner", "bot.png")
avatar_user = avatar_user_path if os.path.exists(avatar_user_path) else "👤"
avatar_bot = avatar_bot_path if os.path.exists(avatar_bot_path) else "🤖"

if "messages" not in st.session_state: st.session_state.messages = []

for msg in st.session_state.messages:
    avatar = avatar_user if msg["role"] == "user" else avatar_bot
    with st.chat_message(msg["role"], avatar=avatar): render_content(msg["content"])

if query := st.chat_input("Ställ din fråga..."):
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user", avatar=avatar_user): st.write(query)
    with st.chat_message("assistant", avatar=avatar_bot):
        with st.spinner("Tänker..."):
            try:
                retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
                chain = create_retrieval_chain(retriever, create_stuff_documents_chain(chat_model, prompt))
                response = chain.invoke({"input": query})
                res_text = response["answer"]
                if "Jag hittar inte detta i Isolerabs manualer" in res_text:
                    with open(log_path, "a", encoding="utf-8") as f: f.write(f"- {query}\n")
                    st.toast("📌 Frågan loggad!")
                safety = "**Använd mina svar med försiktighet...**\n\n"
                full_res = safety + res_text
                render_content(full_res)
                st.session_state.messages.append({"role": "assistant", "content": full_res})
            except Exception as e: st.error(f"Fel: {e}")
