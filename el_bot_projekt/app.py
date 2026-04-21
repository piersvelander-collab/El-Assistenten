import streamlit as st
import os
import re
from datetime import datetime
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# 1. Konfiguration
st.set_page_config(page_title="El-Assistenten", page_icon="⚡")
st.title("⚡ Din Pedagogiska El-Assistent")

# 2. API-nyckel
if "HUGGINGFACEHUB_API_TOKEN" in st.secrets:
    hf_api_key = st.secrets["HUGGINGFACEHUB_API_TOKEN"]
else:
    hf_api_key = st.sidebar.text_input("API-nyckel:", type="password")

# --- LOGGNINGSFUNKTION ---
def log_missing_knowledge(query):
    with open("saknad_kunskap.txt", "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] Fråga utan svar: {query}\n")

# --- RENDERARE ---
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

# --- DOKUMENT-LOGIK ---
@st.cache_resource
def init_vector_db():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    doc_dir = os.path.join(current_dir, "dokument")
    if not os.path.exists(doc_dir) or not [f for f in os.listdir(doc_dir) if f.endswith('.md')]:
        return None
    loader = DirectoryLoader(doc_dir, glob="**/*.md", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'})
    docs = loader.load()
    splits = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100).split_documents(docs)
    return FAISS.from_documents(splits, HuggingFaceEmbeddings(model_name="paraphrase-multilingual-MiniLM-L12-v2"))

# --- HUVUDLOGIK ---
if hf_api_key:
    os.environ["HUGGINGFACEHUB_API_TOKEN"] = hf_api_key
    vectorstore = init_vector_db()
    
    chat_model = ChatOpenAI(
        model="Qwen/Qwen2.5-7B-Instruct", 
        api_key=hf_api_key, 
        base_url="https://router.huggingface.co/v1", 
        temperature=0.0 # Ingen kreativitet = inga påhitt
    )
    
    system_prompt = (
        "Du är en professionell svensk el-mentor. Din viktigaste regel är SANNING.\n\n"
        "REGLER:\n"
        "1. ANVÄND ENDAST KONTEXTEN: Svara bara på frågan om du hittar stödet i de bifogade dokumenten.\n"
        "2. OM SVAR SAKNAS: Om dokumenten inte innehåller svaret på just den frågan, svara EXAKT så här: "
        "'Tyvärr kan jag inte svara på den frågan baserat på min nuvarande expertkunskap, men jag har förmedlat den vidare så att jag kan lära mig bättre till nästa gång.'\n"
        "3. SPRÅK: Använd korrekt svensk el-terminologi (t.ex. spänning, strömstyrka, VP-rör). Inga direktöversättningar.\n"
        "4. STRUKTUR: Svara logiskt uppifrån och ned så att det viktigaste kommer först.\n\n"
        "Kontext:\n{context}"
    )
    
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])

    if "messages" not in st.session_state: st.session_state.messages = []
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): render_content(msg["content"])

    if query := st.chat_input("Fråga mig något..."):
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"): st.write(query)
        
        with st.chat_message("assistant"):
            with st.spinner("Håller på och letar, grejar och fixar i expertkunskapen..."):
                if vectorstore:
                    # Vi söker efter relevant fakta
                    rag_chain = create_retrieval_chain(vectorstore.as_retriever(search_kwargs={"k": 3}), create_stuff_documents_chain(chat_model, prompt))
                    response = rag_chain.invoke({"input": query})
                    res_text = response["answer"]
                    
                    # Om boten säger att den inte vet, loggar vi frågan
                    if "Tyvärr kan jag inte svara" in res_text:
                        log_missing_knowledge(query)
                else:
                    res_text = "Tyvärr kan jag inte svara på den frågan baserat på min nuvarande expertkunskap, men jag har förmedlat den vidare så att jag kan lära mig bättre till nästa gång."
                    log_missing_knowledge(query)
                
                full_res = "**Använd mina svar med försiktighet, jag är en AI-bot och kan svara fel. Är du osäker så kontakta ALLTID elansvarig innan du utför något arbete!!**\n\n" + res_text
                render_content(full_res)
                st.session_state.messages.append({"role": "assistant", "content": full_res})
else:
    st.info("👈 Konfigurera API-nyckeln i Secrets!")
