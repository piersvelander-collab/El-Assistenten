import streamlit as st
import os
import re
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.chains.retrieval import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# --- 1. SIDKONFIGURATION ---
st.set_page_config(page_title="El-Assistenten", page_icon="⚡", layout="centered")
st.title("⚡ Din Pedagogiska El-Assistent")
st.write("Välkommen! Jag är din guide i elens värld. Fråga mig om installationer, regler och teori.")

# --- 2. API-NYCKEL (Hanterar både molnet och lokal körning) ---
if "GOOGLE_API_KEY" in st.secrets:
    google_api_key = st.secrets["GOOGLE_API_KEY"]
else:
    google_api_key = st.sidebar.text_input("Klistra in din Google API-nyckel här:", type="password")
    st.sidebar.info("Hämta en gratis nyckel på Google AI Studio om du saknar en.")

# --- 3. HJÄLPFUNKTIONER ---
def render_content(text):
    """Ritar ut text och letar efter bild-taggar för att visa bilder."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_dir = os.path.join(current_dir, "bilder")
    
    pattern = r'\[(?:VISA_BILD|BILD):\s*([^\]]+)\]'
    parts = re.split(pattern, text)
    
    for i, part in enumerate(parts):
        if i % 2 == 0:
            if part.strip(): 
                st.write(part.strip())
        else:
            img_path = os.path.join(image_dir, part.strip())
            if os.path.exists(img_path): 
                st.image(img_path, use_container_width=True)
            else:
                st.warning(f"⚠️ Bilden '{part.strip()}' saknas i bild-mappen.")

# --- 4. HUVUDPROGRAM ---
if google_api_key:
    os.environ["GOOGLE_API_KEY"] = google_api_key
    current_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(current_dir, "faiss_index")
    
    # --- LADDA EXPERTKUNSKAP (Blixtsnabbt) ---
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

    # Initierar AI-hjärnan (Gemini 1.5 Flash är snabb och gratis)
    chat_model = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash", 
        google_api_key=google_api_key, 
        temperature=0.0
    )
    
    # Instruktioner för botens personlighet
    system_prompt = (
        "Du är en logisk, strikt och professionell svensk el-mentor. Din viktigaste regel är SANNING.\n\n"
        "REGLER:\n"
        "1. ANVÄND ENDAST KONTEXTEN: Svara bara om stödet finns i de bifogade dokumenten.\n"
        "2. OM SVAR SAKNAS: Svara att du inte kan svara baserat på din nuvarande expertkunskap.\n"
        "3. SPRÅK: Använd uteslutande korrekt svensk el-terminologi (spänningsprovare, dvärgbrytare etc.).\n"
        "4. STRUKTUR: Svara i punktform med säkerhetsföreskrifter allra högst upp.\n\n"
        "Expertkunskap:\n{context}"
    )
    
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])

    # Avatarer
    avatarer = {
        "user": os.path.join(current_dir, "ikoner", "anvandare.png") if os.path.exists(os.path.join(current_dir, "ikoner", "anvandare.png")) else "👤",
        "assistant": os.path.join(current_dir, "ikoner", "bot.png") if os.path.exists(os.path.join(current_dir, "ikoner", "bot.png")) else "🤖"
    }

    # Chatthistorik
    if "messages" not in st.session_state: 
        st.session_state.messages = []
        
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar=avatarer.get(msg["role"])): 
            render_content(msg["content"])

    # Själva chatten
    if query := st.chat_input("Ställ din fråga om el..."):
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user", avatar=avatarer["user"]): 
            st.write(query)
        
        with st.chat_message("assistant", avatar=avatarer["assistant"]):
            with st.spinner("Letar i handböckerna..."):
                retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
                rag_chain = create_retrieval_chain(retriever, create_stuff_documents_chain(chat_model, prompt))
                
                response = rag_chain.invoke({"input": query})
                res_text = response["answer"]
                
                safety_warning = "**Använd mina svar med försiktighet, jag är en AI-bot och kan svara fel. Är du osäker så kontakta ALLTID elansvarig innan du utför något arbete!!**\n\n"
                full_res = safety_warning + res_text
                
                render_content(full_res)
                st.session_state.messages.append({"role": "assistant", "content": full_res})
else:
    st.info("👈 Vänligen klistra in din Google API-nyckel i sidomenyn.")
