import streamlit as st
import os
import re
from datetime import datetime
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
# Vi byter till API-baserade embeddings för att spara RAM
from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings

# 1. Konfiguration
st.set_page_config(page_title="El-Assistenten", page_icon="⚡")
st.title("⚡ Resurssnål El-Assistent")

# 2. API-nyckel
if "HUGGINGFACEHUB_API_TOKEN" in st.secrets:
    hf_api_key = st.secrets["HUGGINGFACEHUB_API_TOKEN"]
else:
    hf_api_key = st.sidebar.text_input("API-nyckel:", type="password")

def log_missing_knowledge(query):
    with open("saknad_kunskap.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] Saknas svar: {query}\n")

# --- RESURSSNÅL DOKUMENT-LOGIK ---
@st.cache_resource
def init_vector_db():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    doc_dir = os.path.join(current_dir, "dokument")
    index_path = os.path.join(current_dir, "faiss_index")
    
    # Använd API-embeddings för att spara 500MB+ RAM
    embeddings = HuggingFaceInferenceAPIEmbeddings(
        api_key=hf_api_key, 
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )

    # Om vi redan har sparat indexet på disk, ladda det direkt
    if os.path.exists(index_path):
        return FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)

    # Annars skapa det (sker bara en gång)
    if not os.path.exists(doc_dir) or not [f for f in os.listdir(doc_dir) if f.endswith('.md')]:
        return None

    loader = DirectoryLoader(doc_dir, glob="**/*.md", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'})
    docs = loader.load()
    splits = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=50).split_documents(docs)
    vectorstore = FAISS.from_documents(splits, embeddings)
    
    # Spara lokalt för att slippa räkna om nästa gång
    vectorstore.save_local(index_path)
    return vectorstore

# --- HUVUDLOGIK ---
if hf_api_key:
    os.environ["HUGGINGFACEHUB_API_TOKEN"] = hf_api_key
    vectorstore = init_vector_db()
    
    chat_model = ChatOpenAI(
        model="Qwen/Qwen2.5-7B-Instruct", 
        api_key=hf_api_key, 
        base_url="https://router.huggingface.co/v1", 
        temperature=0.0
    )
    
    system_prompt = (
        "Du är en professionell svensk el-mentor. Svara ENDAST baserat på kontexten.\n"
        "Om svar saknas, säg: 'Tyvärr kan jag inte svara på den frågan baserat på min nuvarande expertkunskap...'\n\n"
        "Kontext:\n{context}"
    )
    
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])

    if "messages" not in st.session_state: st.session_state.messages = []
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.write(msg["content"])

    if query := st.chat_input("Fråga mig något..."):
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"): st.write(query)
        
        with st.chat_message("assistant"):
            if vectorstore:
                rag_chain = create_retrieval_chain(vectorstore.as_retriever(search_kwargs={"k": 3}), create_stuff_documents_chain(chat_model, prompt))
                res_text = rag_chain.invoke({"input": query})["answer"]
                if "Tyvärr kan jag inte svara" in res_text: log_missing_knowledge(query)
            else:
                res_text = "Tyvärr saknas kunskapsdokument."
                log_missing_knowledge(query)
            
            full_res = "**Använd mina svar med försiktighet, jag är en AI-bot och kan svara fel. Är du osäker så kontakta ALLTID elansvarig innan du utför något arbete!!**\n\n" + res_text
            st.write(full_res)
            st.session_state.messages.append({"role": "assistant", "content": full_res})
