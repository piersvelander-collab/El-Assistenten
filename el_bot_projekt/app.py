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
# Vi kollar först om nyckeln finns sparad i Streamlits "Secrets" (TOML)
if "HUGGINGFACEHUB_API_TOKEN" in st.secrets:
    hf_api_key = st.secrets["HUGGINGFACEHUB_API_TOKEN"]
else:
    # Om inte, visar vi inmatningsfältet i sidomenyn som tidigare
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
        # Visa vanlig text
        if parts[i].strip():
            st.write(parts[i].strip())
        
        # Kontrollera om nästa del är ett bildfilnamn
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
    loader = DirectoryLoader('./dokument', glob="**/*.md", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'})
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

# 4. Huvudlogik
if hf_api_key:
    os.environ["HUGGINGFACEHUB_API_TOKEN"] = hf_api_key
    vectorstore = init_vector_db()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 6})
    chat_model = ChatOpenAI(model="Qwen/Qwen2.5-7B-Instruct", api_key=hf_api_key, base_url="https://router.huggingface.co/v1", max_tokens=1000, temperature=0.3)
    
    img_list = get_available_images()
    
    # --- UPPDATERAD SYSTEM PROMPT (Inriktad på mänsklig pedagogik) ---
    system_prompt = (
        "Du är en mänsklig, varm och ytterst pedagogisk expert och mentor inom el. "
        "Ditt mål är att förklara elens fantastiska värld på ett utförligt, intressant och lättförståeligt sätt. "
        "Använd gärna pedagogiska liknelser (som vattenslangen eller motorvägen).\n\n"
        "FAKTA OCH KÄLLOR:\n"
        "1. Du MÅSTE i absolut första hand basera dina svar på den medföljande kontexten (dokumenten).\n"
        "2. Om kontexten inte täcker hela frågan får du använda din egen expertkunskap för att göra svaret mer komplett. Prioritera dock alltid dokumenten.\n\n"
        f"TILLGÄNGLIGA BILDER I DITT ARKIV: {img_list}\n"
        "BILDREGLER:\n"
        "- Välj ut max 1-2 bilder som är direkt relevanta från listan ovan.\n"
        "- Infoga bilden genom att skriva taggen [VISA_BILD: filnamn.jpg] exakt där den passar i förklaringen.\n"
        "- Skriv aldrig en tom tagg och gissa aldrig filnamn.\n\n"
        "Kontext från dina dokument:\n{context}"
    )
    
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])
    rag_chain = create_retrieval_chain(retriever, create_stuff_documents_chain(chat_model, prompt))

    # Avatarer med fallback till emojis
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
            response = rag_chain.invoke({"input": user_query})
            
            # DIN TVINGANDE VARNINGSFRAS
            safety_warning = "**Använd mina svar med försiktighet, jag är en AI-bot och kan svara fel. Är du osäker så kontakta ALLTID elansvarig innan du utför något arbete!!**\n\n"
            final_answer = safety_warning + response["answer"]
            
            render_content(final_answer)
            st.session_state.messages.append({"role": "assistant", "content": final_answer})
else:
    st.info("👈 Vänligen konfigurera din API-nyckel i Streamlit Secrets (TOML) eller i sidomenyn!")