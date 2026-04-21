import streamlit as st
import os
import re
import datetime 
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# 1. Konfigurera webbsidans utseende
st.set_page_config(page_title="El-Assistenten", page_icon="⚡")
st.title("⚡ Din Pedagogiska El-Assistent")
st.write("Hej! Jag är din guide i elens fantastiska värld. Fråga mig om installationer, teori eller regler.")

# 2. Hantering av API-nyckel (Secrets för molnet, Sidebar för lokal test)
if "HUGGINGFACEHUB_API_TOKEN" in st.secrets:
    hf_api_key = st.secrets["HUGGINGFACEHUB_API_TOKEN"]
else:
    hf_api_key = st.sidebar.text_input("Klistra in din Hugging Face API-nyckel här:", type="password")
    st.sidebar.markdown("*För att appen ska fungera i molnet, lägg till nyckeln i 'Secrets' som TOML.*")

# --- RENDERARE FÖR TEXT OCH BILDER ---
def render_content(text):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_dir = os.path.join(current_dir, "bilder")
    
    # Regex som fångar upp bildtaggar
    pattern = r'\[(?:VISA_BILD|BILD|VISABILD):\s*([^\]]+)\]'
    parts = re.split(pattern, text)
    
    i = 0
    while i < len(parts):
        if parts[i].strip():
            st.write(parts[i].strip())
        
        if i + 1 < len(parts):
            image_filename = parts[i+1].strip()
            image_path = os.path.join(image_dir, image_filename)
            
            if os.path.exists(image_path):
                st.image(image_path, use_container_width=True)
            else:
                st.warning(f"⚠️ Hittade inte bild: {image_filename}")
        i += 2

# --- DOKUMENT-LOGIK ---
@st.cache_resource
def init_vector_db():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    doc_dir = os.path.join(current_dir, "dokument")
    
    if not os.path.exists(doc_dir):
        os.makedirs(doc_dir, exist_ok=True)
        return None

    md_files = [f for f in os.listdir(doc_dir) if f.endswith('.md')]
    if not md_files:
        return None

    loader = DirectoryLoader(doc_dir, glob="**/*.md", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'})
    docs = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    embeddings = HuggingFaceEmbeddings(model_name="paraphrase-multilingual-MiniLM-L12-v2")
    return FAISS.from_documents(splits, embeddings)

def get_available_images():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_dir = os.path.join(current_dir, "bilder")
    if os.path.exists(image_dir):
        files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        return ", ".join(files) if files else "Inga bilder"
    return "Inga bilder"

# --- FÖRBEREDELSER ---
img_list = get_available_images()

# 4. Huvudlogik
if hf_api_key:
    os.environ["HUGGINGFACEHUB_API_TOKEN"] = hf_api_key
    vectorstore = init_vector_db()
    
    if vectorstore is None:
        st.warning("⚠️ Inga dokument (.md) hittades i mappen 'dokument'. Ladda upp filer för att aktivera experten!")
        st.stop()

    retriever = vectorstore.as_retriever(search_kwargs={"k": 6})
    
    # Vi sänker temperaturen till 0.2 för att få mer korrekta svar men behålla flytet
    chat_model = ChatOpenAI(
        model="Qwen/Qwen2.5-7B-Instruct", 
        api_key=hf_api_key, 
        base_url="https://router.huggingface.co/v1", 
        max_tokens=1500, 
        temperature=0.2
    )
    
    # --- UPPDATERAD SYSTEM PROMPT FÖR LOGIK OCH KORREKT SVENSKA ---
    system_prompt = (
        "Du är en erfaren svensk el-expert och mentor. Din personlighet är lugn, logisk och ytterst professionell.\n\n"
        "SPRÅKKRAV:\n"
        "- Du MÅSTE svara på naturlig, korrekt svensk fackterminologi. Använd ALDRIG direktöversättningar från engelska.\n"
        "- Exempel: Använd 'isolerade verktyg' (inte 'elskrämda'), 'spänningsprovare' (inte 'voltmätare'), 'gruppsäkring' (inte 'kretsbrytare').\n"
        "- Skriv flytande och pedagogiskt, men undvik att krångla till det. Var rak och logisk.\n\n"
        "SVARSRUTINER:\n"
        "1. Prioritera ALLTID informationen i de bifogade dokumenten.\n"
        "2. Om dokumenten inte räcker, använd din djupa kunskap för att ge ett säkert och logiskt svar.\n"
        "3. Strukturera dina svar med rubriker och punktlistor för att göra dem lätta att läsa på en mobilskärm.\n\n"
        f"TILLGÄNGLIGA BILDER: {img_list}\n"
        "BILDREGLER:\n"
        "- Välj ut de 1-2 mest relevanta bilderna för att förstärka din förklaring.\n"
        "- Infoga dem med [VISA_BILD: filnamn.jpg] precis där de behövs i texten.\n\n"
        "Kontext från dina expert-dokument:\n{context}"
    )
    
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])
    rag_chain = create_retrieval_chain(retriever, create_stuff_documents_chain(chat_model, prompt))

    # Avatarer
    current_dir = os.path.dirname(os.path.abspath(__file__))
    user_icon_path = os.path.join(current_dir, "ikoner", "anvandare.png")
    bot_icon_path = os.path.join(current_dir, "ikoner", "bot.png")

    avatarer = {
        "user": user_icon_path if os.path.exists(user_icon_path) else "👤",
        "assistant": bot_icon_path if os.path.exists(bot_icon_path) else "🤖"
    }

    if "messages" not in st.session_state: st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar=avatarer.get(msg["role"])):
            render_content(msg["content"])

    if user_query := st.chat_input("Ställ din fråga om elens fantastiska värld, så ska jag försöka förklara..."):
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user", avatar=avatarer["user"]): st.write(user_query)
        
        with st.chat_message("assistant", avatar=avatarer["assistant"]):
            with st.spinner("Håller på och letar, grejar och fixar i expertkunskapen..."):
                response = rag_chain.invoke({"input": user_query})
            
            # Din obligatoriska varningsfras
            safety_warning = "**Använd mina svar med försiktighet, jag är en AI-bot och kan svara fel. Är du osäker så kontakta ALLTID elansvarig innan du utför något arbete!!**\n\n"
            final_answer = safety_warning + response["answer"]
            
            render_content(final_answer)
            st.session_state.messages.append({"role": "assistant", "content": final_answer})
else:
    st.info("👈 Vänligen konfigurera din API-nyckel i Streamlit Secrets (TOML) eller i sidomenyn!")
