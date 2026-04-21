import streamlit as st
import os
import re
import time
from datetime import datetime
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.chains import create_retrieval_chain
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
def log_missing_knowledge(query):
    """Sparar frågor som assistenten inte kan svara på i en textfil."""
    with open("saknad_kunskap.txt", "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] Saknar info för: {query}\n")

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

# --- 4. DOKUMENT- OCH SÖKLOGIK (Med inbyggd paus för Googles API) ---
@st.cache_resource
def init_vector_db():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    doc_dir = os.path.join(current_dir, "dokument")
    index_path = os.path.join(current_dir, "faiss_index")
    
    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004", 
            google_api_key=google_api_key
        )
    except Exception as e:
        st.error("Kunde inte ansluta till Googles inbäddningsmodell. Kontrollera din API-nyckel.")
        st.stop()

    if os.path.exists(index_path):
        try:
            return FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
        except Exception:
            pass # Bygg en ny om den gamla är korrupt

    if not os.path.exists(doc_dir) or not [f for f in os.listdir(doc_dir) if f.endswith('.md')]:
        return None

    loader = DirectoryLoader(doc_dir, glob="**/*.md", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'})
    docs = loader.load()
    splits = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100).split_documents(docs)
    
    if not splits:
        return None

    try:
        vectorstore = None
        batch_size = 20 # Skickar
