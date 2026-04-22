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

# --- NYHET: FELSÖKNINGS-MENY I SIDOMENYN ---
with st.sidebar:
    st.header("🛠 Felsökning")
    if st.checkbox("Visa hittade filer (Debug)"):
        st.write(f"Appens mapp: `{current_dir}`")
        img_dir = os.path.join(current_dir, "bilder")
        if os.path.exists(img_dir):
            st.write(f"Filer i /bilder: {os.listdir(img_dir)}")
        else:
            st.error("Mappen /bilder hittades inte!")

# --- 2. API-NYCKEL ---
if "GOOGLE_API_KEY" in st.secrets:
    google_api_key = st.secrets["GOOGLE_API_KEY"]
else:
    google_api_key = st.sidebar.text_input("API-nyckel:", type="password")

if not google_api_key:
    st.info("👈 Vänligen klistra in din Google API-nyckel i sidomenyn.")
    st.stop()

os.environ["GOOGLE_API_KEY"] = google_api_key

# --- 3. ANPASSAD STYLING ---
st.markdown("""
<style>
    .stApp { background-color: #0d014d; }
    p, li, .stMarkdown, div[data-testid="stChatMessageContent"] { color: #ffffff !important; }
    .brand-header { display: flex; align-items: center; border-bottom: 2px solid #82e300; margin-bottom: 20px; }
    .brand-header h1 { color: #82e300 !important; }
    .highlight { color: #82e300 !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 4. RENDERERA HEADER ---
logo_path = os.path.join(current_dir, "bilder", "logo.png")
if os.path.exists(logo_path):
    st.image(logo_path, width=150)
st.markdown("<h1><span class='highlight'>ISOLERAB</span> El-Assistent</h1>", unsafe_allow_html=True)

# --- 5. UPPGRADERAD RIT- OCH BILDFUNKTION ---
def render_content(text):
    image_dir = os.path.join(current_dir, "bilder")
    # Mönster för att hitta [BILD: filnamn.jpg] eller [SCHEMA: mermaid_kod]
    pattern = r'\[(?:VISA_BILD|BILD|SCHEMA):\s*([\s\S]+?)\]'
    parts = re.split(pattern, text)
    
    for i, part in enumerate(parts):
        if i % 2 == 0:
            if part.strip():
                h_text = part.strip().replace("HIGHLIGHT:", "<span class='highlight'>").replace(":HIGHLIGHT", "</span>")
                st.markdown(h_text, unsafe_allow_html=True)
        else:
            content = part.strip()
            # Om det är en bildfil
            if any(content.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif']):
                img_path = os.path.join(image_dir, content)
                if os.path.exists(img_path):
                    st.image(img_path, use_container_width=True)
                else:
                    st.warning(f"⚠️ Hittar inte: {content}. Kontrollera mappen /bilder.")
            # Om det är Mermaid-kod (Schema)
            else:
                html_code = f"""
                <pre class="mermaid" style="background: transparent;">
                {content}
                </pre>
                <script type="module">
                    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                    mermaid.initialize({{ startOnLoad: true, theme: 'dark', securityLevel: 'loose' }});
                </script>
                """
                components.html(html_code, height=500, scrolling=True)

# --- 6. HUVUDPROGRAM ---
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
    "REGLER:\n"
    "1. Om användaren vill se en bild, använd formatet: [BILD: filnamn.jpg]\n"
    "2. Om användaren vill se ett schema eller rita, använd Mermaid-syntax inuti: [SCHEMA: graph TD...]\n"
    "3. Om du inte hittar svar i dokumenten, inled med: 'Jag hittar inte detta i Isolerabs manualer, men min generella kunskap säger följande:'\n"
    "4. Svara alltid strukturerat och pedagogiskt på svenska."
)

prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        render_content(msg["content"])

if query := st.chat_input("Ställ din fråga..."):
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.write(query)
    
    with st.chat_message("assistant"):
        with st.spinner("Tänker..."):
            try:
                retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
                chain = create_retrieval_chain(retriever, create_stuff_documents_chain(chat_model, prompt))
                response = chain.invoke({"input": query})
                res_text = response["answer"]
                
                safety = "**Använd mina svar med försiktighet...**\n\n"
                full_res = safety + res_text
                render_content(full_res)
                st.session_state.messages.append({"role": "assistant", "content": full_res})
            except Exception as e:
                st.error(f"Fel vid svar: {e}")
