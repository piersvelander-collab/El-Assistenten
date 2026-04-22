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
st.set_page_config(
    page_title="Isolerab El-Assistent",
    page_icon="⚡", 
    layout="centered"
)

# --- 2. API-NYCKEL ---
if "GOOGLE_API_KEY" in st.secrets:
    google_api_key = st.secrets["GOOGLE_API_KEY"]
else:
    google_api_key = st.sidebar.text_input("Klistra in din Google API-nyckel här:", type="password")

if not google_api_key:
    st.info("👈 Vänligen klistra in din Google API-nyckel i sidomenyn.")
    st.stop()

# Aktivera nyckeln i bakgrunden
os.environ["GOOGLE_API_KEY"] = google_api_key

# --- 3. ANPASSAD STYLING (CSS) ---
st.markdown("""
<style>
    .stApp {
        background-color: #0d014d;
    }
    
    /* TVINGAR ALL TEXT ATT BLI VIT */
    p, li, .stMarkdown, div[data-testid="stChatMessageContent"] {
        color: #ffffff !important;
    }
    
    .brand-header {
        display: flex;
        align-items: center;
        margin-bottom: 20px;
        padding: 10px;
        background-color: #0d014d;
        border-bottom: 2px solid #82e300;
    }
    .brand-header img {
        height: 40px;
        margin-right: 15px;
    }
    .brand-header h1 {
        margin: 0;
        color: #82e300 !important;
        font-size: 1.8em;
    }
    .stTextInput > div > div > input {
        background-color: rgba(255, 255, 255, 0.1);
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    .stTextInput > div > div > input:focus {
        border-color: #82e300;
        box-shadow: 0 0 0 0.2rem rgba(130, 227, 0, 0.25);
    }
    .highlight {
        color: #82e300 !important;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. RENDERERA HEADER ---
current_dir = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(current_dir, "bilder", "logo.png")

if os.path.exists(logo_path):
    st.image(logo_path, width=150, use_container_width=False)
    st.markdown("<h1><span class='highlight'>ISOLERAB</span> El-Assistent</h1>", unsafe_allow_html=True)
else:
    st.markdown("<h1><span class='highlight'>ISOLERAB</span> El-Assistent</h1>", unsafe_allow_html=True)

st.write("Välkommen! Jag är din guide i elens värld. Fråga mig om installationer, regler och teori.")

# --- 5. HJÄLPFUNKTIONER ---
def render_content(text):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_dir = os.path.join(current_dir, "bilder")
    
    # Letar efter antingen bilder eller SCHEMA-taggar
    pattern = r'\[(?:VISA_BILD|BILD|SCHEMA):\s*([\s\S]+?)\]'
    parts = re.split(pattern, text)
    
    for i, part in enumerate(parts):
        if i % 2 == 0:
            if part.strip(): 
                highlighted_text = part.strip().replace("HIGHLIGHT:", "<span class='highlight'>").replace(":HIGHLIGHT", "</span>")
                st.markdown(highlighted_text, unsafe_allow_html=True)
        else:
            part = part.strip()
            # Om det är en bildfil (slutar på .png, .jpg etc)
            if part.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                img_path = os.path.join(image_dir, part)
                if os.path.exists(img_path): 
                    st.image(img_path, use_container_width=True)
                else:
                    st.warning(f"⚠️ Bilden '{part}' saknas.")
            # Om det är ett Mermaid-schema (kod)
            else:
                mermaid_html = f"""
                <div class="mermaid">
                {part}
                </div>
                <script type="module">
                import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});
                </script>
                """
                components.html(mermaid_html, height=400)

# --- 6. HUVUDPROGRAM ---
index_path = os.path.join(current_dir, "faiss_index")
try:
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=google_api_key
    )
    vectorstore = FAISS.load_local(
        index_path, 
        embeddings, 
        allow_dangerous_deserialization=True
    )
except Exception as e:
    st.error("⚠️ **Kunde inte ladda expertkunskapen!**")
    st.error(f"🔍 Systemets dolda felmeddelande: {str(e)}")
    st.info("Kontrollera att mappen 'faiss_index' är uppladdad till GitHub och innehåller rätt filer.")
    st.stop()

chat_model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    google_api_key=google_api_key,
    temperature=0.0
)

system_prompt = (
        "Du är en logisk, strikt och professionell svensk el-mentor för företaget Isolerab. Din viktigaste regel är SANNING.\n\n"
        "REGLER:\n"
        "1. ANVÄND ENDAST KONTEXTEN: Svara bara om stödet finns i de bifogade dokumenten.\n"
        "2. OM SVAR SAKNAS: Svara att du inte kan svara baserat på din nuvarande expertkunskap.\n"
        "3. SPRÅK: Använd uteslutande korrekt svensk el-terminologi.\n"
        "4. STRUKTUR: Svara i punktform med säkerhetsföreskrifter allra högst upp.\n"
        "5. VISUALISERING: Om användaren ber dig 'rita', 'visa ett schema' eller 'förklara visuellt', rita ett diagram med Mermaid.js-syntax. Kapsla in hela din Mermaid-kod EXAKT så här: [SCHEMA: din_mermaid_kod_här]\n\n"
        "Expertkunskap:\n{context}"
)

prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])

avatar_user_path = os.path.join(current_dir, "ikoner", "anvandare.png")
avatar_bot_path = os.path.join(current_dir, "ikoner", "bot.png")

avatar_user = avatar_user_path if os.path.exists(avatar_user_path) else "👤"
avatar_bot = avatar_bot_path if os.path.exists(avatar_bot_path) else "🤖"

if "messages" not in st.session_state: 
    st.session_state.messages = []
    
for msg in st.session_state.messages:
    if msg["role"] == "user":
        avatar = avatar_user
    else:
        avatar = avatar_bot
    with st.chat_message(msg["role"], avatar=avatar): 
        render_content(msg["content"])

if query := st.chat_input("Ställ din fråga om el till Isolerab..."):
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user", avatar=avatar_user): 
        st.write(query)
    
    with st.chat_message("assistant", avatar=avatar_bot):
        with st.spinner("Isolerabs el-mentor tänker..."):
            try:
                retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
                rag_chain = create_retrieval_chain(retriever, create_stuff_documents_chain(chat_model, prompt))
                
                response = rag_chain.invoke({"input": query})
                res_text = response["answer"]
                
                safety_warning = "**Använd mina svar med försiktighet, jag är en AI-bot och kan svara fel. Är du osäker så kontakta ALLTID elansvarig innan du utför något arbete!!**\n\n"
                full_res = safety_warning + res_text
                
                render_content(full_res)
                st.session_state.messages.append({"role": "assistant", "content": full_res})
            except Exception as e:
                st.error("⚠️ **Ett fel uppstod när boten skulle svara!**")
                st.error(f"🔍 Systemets dolda felmeddelande: {str(e)}")
