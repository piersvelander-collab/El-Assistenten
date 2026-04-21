import streamlit as st
import os
import re
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# 1. Webbsidans konfiguration
st.set_page_config(page_title="El-Assistenten", page_icon="⚡")
st.title("⚡ Din Pedagogiska El-Assistent")
st.write("Välkommen! Jag hjälper dig med logiska och korrekta svar om el och installation.")

# 2. API-nyckel hantering
if "HUGGINGFACEHUB_API_TOKEN" in st.secrets:
    hf_api_key = st.secrets["HUGGINGFACEHUB_API_TOKEN"]
else:
    hf_api_key = st.sidebar.text_input("API-nyckel:", type="password")

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
            else: st.warning(f"BILD SAKNAS: {part}")

# --- DOKUMENT-LOGIK ---
@st.cache_resource
def init_vector_db():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    doc_dir = os.path.join(current_dir, "dokument")
    if not os.path.exists(doc_dir) or not [f for f in os.listdir(doc_dir) if f.endswith('.md')]:
        return None
    loader = DirectoryLoader(doc_dir, glob="**/*.md", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'})
    docs = loader.load()
    splits = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200).split_documents(docs)
    return FAISS.from_documents(splits, HuggingFaceEmbeddings(model_name="paraphrase-multilingual-MiniLM-L12-v2"))

# --- HUVUDLOGIK ---
if hf_api_key:
    os.environ["HUGGINGFACEHUB_API_TOKEN"] = hf_api_key
    vectorstore = init_vector_db()
    
    # AI-modell med lägsta möjliga temperatur för att förhindra påhitt
    chat_model = ChatOpenAI(
        model="Qwen/Qwen2.5-7B-Instruct", 
        api_key=hf_api_key, 
        base_url="https://router.huggingface.co/v1", 
        temperature=0.0 
    )
    
    system_prompt = (
        "Du är en erfaren svensk el-mentor. Du svarar naturligt, korrekt och mänskligt.\n\n"
        "VIKTIGA REGLER:\n"
        "1. TALA SOM EN ELEKTRIKER: Använd aldrig ord som 'elskrämd', 'ledningssprängar' eller 'gasstrålar'. Om du inte vet det svenska ordet, använd en enkel beskrivning.\n"
        "2. LOGISK ORDNING: Svaret ska börja med det viktigaste (säkerhet) och flyta nedåt. Användaren ska kunna läsa uppifrån och ned utan att behöva scrolla tillbaks.\n"
        "3. INGA PÅHITT: Om information saknas i dokumenten, använd endast vedertagen svensk branschpraxis (t.ex. ångspärr, VP-rör, bryta strömmen). Hitta ALDRIG på egna regler eller risker.\n"
        "4. PEDAGOGIK: Förklara VARFÖR man gör något (t.ex. 'täta ångspärren för att undvika mögel').\n\n"
        "Kontext:\n{context}"
    )
    
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])
    
    if vectorstore:
        rag_chain = create_retrieval_chain(vectorstore.as_retriever(), create_stuff_documents_chain(chat_model, prompt))
    
    if "messages" not in st.session_state: st.session_state.messages = []
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): render_content(msg["content"])

    if query := st.chat_input("Fråga mig något..."):
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"): st.write(query)
        with st.chat_message("assistant"):
            with st.spinner("Håller på och letar, grejar och fixar i expertkunskapen..."):
                if vectorstore:
                    res = rag_chain.invoke({"input": query})["answer"]
                else:
                    # Fallback om dokument saknas - svara med ren logik
                    res = chat_model.invoke(query).content
                
                full_res = "**Använd mina svar med försiktighet, jag är en AI-bot och kan svara fel. Är du osäker så kontakta ALLTID elansvarig innan du utför något arbete!!**\n\n" + res
                render_content(full_res)
                st.session_state.messages.append({"role": "assistant", "content": full_res})
