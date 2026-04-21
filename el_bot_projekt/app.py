import streamlit as st
import os
import re
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
    
    # Delar upp texten där bild-taggar finns, t.ex. [VISA_BILD: skiss.jpg]
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

# --- 4. DOKUMENT- OCH SÖKLOGIK (Optimerad för att inte krascha) ---
@st.cache_resource
def init_vector_db():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    doc_dir = os.path.join(current_dir, "dokument")
    index_path = os.path.join(current_dir, "faiss_index")
    
    # Använder Googles rekommenderade modell för sökning
    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004", 
            google_api_key=google_api_key
        )
    except Exception as e:
        st.error("Kunde inte ansluta till Googles inbäddningsmodell. Kontrollera din API-nyckel.")
        st.stop()

    # Försök ladda det färdiga indexet från disk för att spara minne
    if os.path.exists(index_path):
        try:
            return FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
        except Exception:
            pass # Om gamla filen är trasig går vi vidare och bygger en ny

    # Kontrollera om det finns några .md-filer att läsa
    if not os.path.exists(doc_dir) or not [f for f in os.listdir(doc_dir) if f.endswith('.md')]:
        return None

    # Läs in, hacka upp och skapa sökregister
    loader = DirectoryLoader(doc_dir, glob="**/*.md", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'})
    docs = loader.load()
    splits = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100).split_documents(docs)
    
    try:
        vectorstore = FAISS.from_documents(splits, embeddings)
        vectorstore.save_local(index_path) 
        return vectorstore
    except Exception as e:
        st.error(f"⚠️ Ett fel uppstod när dokumenten skulle analyseras:\n{str(e)}")
        st.stop()

# --- 5. HUVUDPROGRAM ---
if google_api_key:
    # Sätter miljövariabeln så att LangChain hittar nyckeln
    os.environ["GOOGLE_API_KEY"] = google_api_key
    
    with st.spinner("Startar motorn och läser in dina handböcker..."):
        vectorstore = init_vector_db()
    
    # Initierar Googles snabba AI-hjärna. Temperature 0.0 gör henne extremt saklig.
    chat_model = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash", 
        google_api_key=google_api_key, 
        temperature=0.0
    )
    
    # Den stränga instruktionen (Personlighet & Regler)
    system_prompt = (
        "Du är en logisk, strikt och professionell svensk el-mentor. Din viktigaste regel är SANNING.\n\n"
        "REGLER:\n"
        "1. ANVÄND ENDAST KONTEXTEN: Du får under inga omständigheter gissa. Svara bara om stödet finns i dokumenten.\n"
        "2. OM SVAR SAKNAS: Svara EXAKT så här: 'Tyvärr kan jag inte svara på den frågan baserat på min nuvarande expertkunskap, men jag har förmedlat den vidare så att jag kan lära mig bättre till nästa gång.'\n"
        "3. SPRÅK: Använd uteslutande korrekt svensk el-terminologi (t.ex. 'spänningsprovare', 'VP-rör', 'dvärgbrytare'). Direktöversätt aldrig engelska termer.\n"
        "4. STRUKTUR: Svara i punktform med det absolut viktigaste (t.ex. säkerhet) allra högst upp. Användaren ska inte behöva scrolla.\n\n"
        "Kontext från dina expert-dokument:\n{context}"
    )
    
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])

    # Sätter upp avatar-ikoner om de finns i mappen "ikoner"
    current_dir = os.path.dirname(os.path.abspath(__file__))
    avatarer = {
        "user": os.path.join(current_dir, "ikoner", "anvandare.png") if os.path.exists(os.path.join(current_dir, "ikoner", "anvandare.png")) else "👤",
        "assistant": os.path.join(current_dir, "ikoner", "bot.png") if os.path.exists(os.path.join(current_dir, "ikoner", "bot.png")) else "🤖"
    }

    # Hanterar chatthistoriken
    if "messages" not in st.session_state: 
        st.session_state.messages = []
        
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar=avatarer.get(msg["role"])): 
            render_content(msg["content"])

    # Själva chattrutan och svarslogiken
    if query := st.chat_input("Ställ din fråga om el..."):
        # Visa användarens fråga
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user", avatar=avatarer["user"]): 
            st.write(query)
        
        # Generera och visa assistentens svar
        with st.chat_message("assistant", avatar=avatarer["assistant"]):
            with st.spinner("Håller på och letar, grejar och fixar i expertkunskapen..."):
                if vectorstore:
                    # Söker fram de 3 mest relevanta textstyckena
                    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
                    rag_chain = create_retrieval_chain(retriever, create_stuff_documents_chain(chat_model, prompt))
                    response = rag_chain.invoke({"input": query})
                    res_text = response["answer"]
                    
                    # Om boten tvingades erkänna att den inte vet, logga frågan
                    if "Tyvärr kan jag inte svara" in res_text:
                        log_missing_knowledge(query)
                else:
                    res_text = "Tyvärr kan jag inte svara på den frågan baserat på min nuvarande expertkunskap, men jag har förmedlat den vidare så att jag kan lära mig bättre till nästa gång."
                    log_missing_knowledge(query)
                
                # Baka in din tvingande säkerhetsvarning
                safety_warning = "**Använd mina svar med försiktighet, jag är en AI-bot och kan svara fel. Är du osäker så kontakta ALLTID elansvarig innan du utför något arbete!!**\n\n"
                full_res = safety_warning + res_text
                
                render_content(full_res)
                st.session_state.messages.append({"role": "assistant", "content": full_res})
else:
    st.info("👈 Vänligen klistra in din Google API-nyckel i sidomenyn för att starta assistenten.")
