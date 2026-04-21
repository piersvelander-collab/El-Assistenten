import streamlit as st
import os
import re
from datetime import datetime
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
# Vi byter ut OpenAI/HuggingFace mot Google Gemini
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# 1. Konfiguration
st.set_page_config(page_title="El-Assistenten", page_icon="⚡")
st.title("⚡ Din Pedagogiska El-Assistent")

# 2. Google API-nyckel (Hämtas från Secrets eller sidomenyn)
if "GOOGLE_API_KEY" in st.secrets:
    google_api_key = st.secrets["GOOGLE_API_KEY"]
else:
    google_api_key = st.sidebar.text_input("Klistra in din Google API-nyckel:", type="password")

# --- LOGGNINGSFUNKTION ---
def log_missing_knowledge(query):
    with open("saknad_kunskap.txt", "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] Saknas svar: {query}\n")

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
    
# --- RESURSSNÅL DOKUMENT-LOGIK (Noll krascher) ---
@st.cache_resource
def init_vector_db():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    doc_dir = os.path.join(current_dir, "dokument")
    index_path = os.path.join(current_dir, "faiss_index")
    
   # Vi använder Googles allra nyaste inbäddningsmodell
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004", 
        google_api_key=google_api_key
    )

    if os.path.exists(index_path):
        try:
            return FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
        except Exception:
            pass # Om gamla filen bråkar, ignorera och bygg en ny

    if not os.path.exists(doc_dir) or not [f for f in os.listdir(doc_dir) if f.endswith('.md')]:
        return None

    loader = DirectoryLoader(doc_dir, glob="**/*.md", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'})
    docs = loader.load()
    splits = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100).split_documents(docs)
    
    # 2. Fällan ligger kvar för att fånga det riktiga felet
    try:
        vectorstore = FAISS.from_documents(splits, embeddings)
        vectorstore.save_local(index_path) 
        return vectorstore
    except Exception as e:
        st.error(f"⚠️ **Google nekade åtkomst! Här är den riktiga anledningen:**\n\n{str(e)}")
        st.info("💡 **Tips för felsökning:**\n* Står det **API_KEY_INVALID**? Gå till Streamlit Secrets och kolla att din nyckel ligger exakt så här: `GOOGLE_API_KEY = \"AIza...\"`\n* Står det **Quota exceeded** eller **429**? Då har du för många dokument för gratisversionen.")
        st.stop()

# --- HUVUDLOGIK ---
if google_api_key:
    os.environ["GOOGLE_API_KEY"] = google_api_key
    
    with st.spinner("Startar motorn och letar dokument..."):
        vectorstore = init_vector_db()
    
    # Vi använder Geminis snabbaste modell med 0 kreativitet (hård sanning)
    chat_model = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash", 
        google_api_key=google_api_key, 
        temperature=0.0
    )
    
    system_prompt = (
        "Du är en professionell svensk el-mentor. Din viktigaste regel är SANNING.\n\n"
        "REGLER:\n"
        "1. ANVÄND ENDAST KONTEXTEN: Svara bara på frågan om du hittar stödet i de bifogade dokumenten.\n"
        "2. OM SVAR SAKNAS: Om dokumenten inte innehåller svaret, svara EXAKT: "
        "'Tyvärr kan jag inte svara på den frågan baserat på min nuvarande expertkunskap, men jag har förmedlat den vidare så att jag kan lära mig bättre till nästa gång.'\n"
        "3. SPRÅK: Använd korrekt svensk el-terminologi. Hitta ALDRIG på egna ord.\n"
        "4. STRUKTUR: Svara logiskt uppifrån och ned med det viktigaste först.\n\n"
        "Kontext:\n{context}"
    )
    
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])

    # Avatarer
    current_dir = os.path.dirname(os.path.abspath(__file__))
    avatarer = {
        "user": os.path.join(current_dir, "ikoner", "anvandare.png") if os.path.exists(os.path.join(current_dir, "ikoner", "anvandare.png")) else "👤",
        "assistant": os.path.join(current_dir, "ikoner", "bot.png") if os.path.exists(os.path.join(current_dir, "ikoner", "bot.png")) else "🤖"
    }

    if "messages" not in st.session_state: st.session_state.messages = []
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar=avatarer.get(msg["role"])): 
            render_content(msg["content"])

    if query := st.chat_input("Fråga mig något om el..."):
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user", avatar=avatarer["user"]): st.write(query)
        
        with st.chat_message("assistant", avatar=avatarer["assistant"]):
            with st.spinner("Håller på och letar, grejar och fixar i expertkunskapen..."):
                if vectorstore:
                    rag_chain = create_retrieval_chain(vectorstore.as_retriever(search_kwargs={"k": 3}), create_stuff_documents_chain(chat_model, prompt))
                    response = rag_chain.invoke({"input": query})
                    res_text = response["answer"]
                    
                    if "Tyvärr kan jag inte svara" in res_text:
                        log_missing_knowledge(query)
                else:
                    res_text = "Tyvärr kan jag inte svara på den frågan baserat på min nuvarande expertkunskap, men jag har förmedlat den vidare så att jag kan lära mig bättre till nästa gång."
                    log_missing_knowledge(query)
                
                full_res = "**Använd mina svar med försiktighet, jag är en AI-bot och kan svara fel. Är du osäker så kontakta ALLTID elansvarig innan du utför något arbete!!**\n\n" + res_text
                render_content(full_res)
                st.session_state.messages.append({"role": "assistant", "content": full_res})
else:
    st.info("👈 Konfigurera din Google API-nyckel i sidomenyn eller i Streamlit Secrets!")
