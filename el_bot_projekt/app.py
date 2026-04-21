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
st.write("Välkommen! Jag är din guide i elens värld.")

# --- 2. API-NYCKEL ---
if "GOOGLE_API_KEY" in st.secrets:
    google_api_key = st.secrets["GOOGLE_API_KEY"]
else:
    google_api_key = st.sidebar.text_input("Klistra in din Google API-nyckel här:", type="password")

# --- 3. HJÄLPFUNKTIONER ---
def log_missing_knowledge(query):
    with open("saknad_kunskap.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] Saknar info för: {query}\n")

def render_content(text):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_dir = os.path.join(current_dir, "bilder")
    pattern = r'\[(?:VISA_BILD|BILD):\s*([^\]]+)\]'
    parts = re.split(pattern, text)
    for i, part in enumerate(parts):
        if i % 2 == 0:
            if part.strip(): st.write(part.strip())
        else:
            img_path = os.path.join(image_dir, part.strip())
            if os.path.exists(img_path): st.image(img_path, use_container_width=True)

# --- 4. DOKUMENT- OCH SÖKLOGIK (Super-försiktig version) ---
@st.cache_resource
def init_vector_db():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    doc_dir = os.path.join(current_dir, "dokument")
    index_path = os.path.join(current_dir, "faiss_index")
    
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004", 
        google_api_key=google_api_key
    )

    if os.path.exists(index_path):
        try:
            return FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
        except: pass 

    if not os.path.exists(doc_dir) or not [f for f in os.listdir(doc_dir) if f.endswith('.md')]:
        return None

    loader = DirectoryLoader(doc_dir, glob="**/*.md", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'})
    docs = loader.load()
    splits = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=50).split_documents(docs)
    
    if not splits: return None

    try:
        # Skapa första biten
        vectorstore = FAISS.from_documents([splits[0]], embeddings)
        
        my_bar = st.progress(0, text="Analyserar dokument... Detta görs bara en gång.")
        
        # Mata in resten ETT STYCKE i taget för att undvika Timeout
        for i in range(1, len(splits)):
            vectorstore.add_documents([splits[i]])
            
            # Uppdatera mätaren
            prog = i / len(splits)
            my_bar.progress(prog, text=f"Laddar kunskap: {int(prog*100)}% (Pausar för att inte överbelasta Google)")
            
            # Rejäl paus för att vara på säkra sidan (Gratis-API limit)
            time.sleep(1.0) 

        my_bar.empty()
        vectorstore.save_local(index_path) 
        return vectorstore
        
    except Exception as e:
        st.error(f"⚠️ Google Timeout! Vi försöker igen. Fel: {str(e)}")
        st.info("Tips: Om detta händer ofta, testa att starta om appen om en stund.")
        st.stop()

# --- 5. CHAT ---
if google_api_key:
    os.environ["GOOGLE_API_KEY"] = google_api_key
    vectorstore = init_vector_db()
    
    chat_model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=google_api_key, temperature=0.0)
    
    if "messages" not in st.session_state: st.session_state.messages = []
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): render_content(msg["content"])

    if query := st.chat_input("Ställ din fråga om el..."):
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"): st.write(query)
        
        with st.chat_message("assistant"):
            with st.spinner("Letar i handböckerna..."):
                if vectorstore:
                    prompt = ChatPromptTemplate.from_messages([
                        ("system", "Du är en svensk el-mentor. Svara ENBART baserat på kontexten: {context}"),
                        ("human", "{input}")
                    ])
                    chain = create_retrieval_chain(vectorstore.as_retriever(), create_stuff_documents_chain(chat_model, prompt))
                    res = chain.invoke({"input": query})["answer"]
                else:
                    res = "Jag hittar inga dokument att svara utifrån."
                
                final_res = "**AI-bot: Kontakta ALLTID elansvarig innan arbete!**\n\n" + res
                render_content(final_res)
                st.session_state.messages.append({"role": "assistant", "content": final_res})
