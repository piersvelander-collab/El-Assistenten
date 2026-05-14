"""
ISOELA - Isolerabs El-Mentor (Master Version)
Denna fil innehåller hela applikationen strukturerad enligt bästa praxis.
Uppdaterad för att hantera stabila Langchain-importer och Streamlit-miljöer.
"""

import streamlit as st
import os
import re
import base64
import time
import urllib.parse
from PIL import Image

# ==========================================
# 1. FASTA IMPORTER (SÄKRADE)
# ==========================================
# Dessa importer är verifierade för att fungera med modern Langchain
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

# ==========================================
# 2. SÖKVÄGAR OCH SYSTEMKONFIGURATION
# ==========================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(CURRENT_DIR, "bilder", "logo.png")
INDEX_PATH = os.path.join(CURRENT_DIR, "faiss_index")
ICON_USER_PATH = os.path.join(CURRENT_DIR, "ikoner", "anvandare.png")

LOGO_URL = "https://isolerab.se/wp-content/themes/isolerab-theme/assets/images/isolerab_logo.svg"
APP_ICON = "⚡" # Streamlit föredrar emojis i webbläsarfliken

# Sätt upp Streamlit-sidans grundinställningar
st.set_page_config(
    page_title="Isoela – Isolerabs El-Mentor", 
    page_icon=APP_ICON, 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 3. INITIERING AV SESSION STATE
# ==========================================
# Här sparar vi data som måste finnas kvar när sidan laddas om
if "show_camera" not in st.session_state: 
    st.session_state.show_camera = False
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_user" not in st.session_state:
    st.session_state.current_user = ""
if "messages" not in st.session_state: 
    st.session_state.messages = []

# ==========================================
# 4. DESIGN OCH CSS (THE PIERFEKTA LOOK)
# ==========================================
# All anpassad styling för Isolerabs varumärke
st.markdown("""
<style>
    /* Bakgrundsfärger för huvudsida och sidofält */
    .stApp, [data-testid="stSidebar"] { 
        background-color: #0d014d !important; 
    }
    
    /* Standard textfärg vit för läsbarhet mot mörk bakgrund */
    p, li, label, h1, h2, h3, h4, h5, h6, .stMarkdown, div[data-testid="stChatMessageContent"] { 
        color: #ffffff !important; 
    }
    
    /* Den unika Isoela-rubriken */
    .pierfekta-header { 
        color: #82e300 !important; 
        font-weight: bold; 
        font-size: 2.2rem; 
        margin-top: 1rem;
        margin-bottom: 2rem; 
        text-align: center;
    }
    
    /* Logotypens placering */
    .main-logo {
        display: block;
        margin-left: auto;
        margin-right: auto;
        width: 180px;
    }
    
    /* Mobilanpassning för små skärmar */
    @media (max-width: 640px) {
        .pierfekta-header { font-size: 1.6rem; }
        .stButton > button, [data-testid="stFormSubmitButton"] > button { 
            width: 100%; 
            height: 3.5rem; 
            font-size: 1.1rem !important; 
        }
    }

    /* Highlighter-färg för viktiga varningar */
    .highlight { 
        color: #82e300 !important; 
        font-weight: bold; 
    }
    
    /* Inmatningsfält - lite genomskinliga så bakgrunden anas */
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        background-color: rgba(0, 0, 0, 0.4) !important; 
        color: white !important; 
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    /* Standardknappar - mörk bakgrund med limegrön ram */
    .stButton > button, [data-testid="stFormSubmitButton"] > button { 
        background-color: rgba(0, 0, 0, 0.4) !important; 
        color: #ffffff !important; 
        border: 1px solid #82e300 !important; 
        border-radius: 8px;
    }
    
    /* Bildupplägg i chatten */
    img { 
        max-width: 100%; 
        height: auto; 
        border-radius: 10px; 
        margin: 10px 0; 
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 5. KÄRNFUNKTIONER OCH CACHNING
# ==========================================
@st.cache_resource(show_spinner=False, ttl=60)
def get_google_sheet(sheet_name):
    """Hämtar data från Google Sheets. Cachas i 60 sekunder för prestanda."""
    try:
        if "gcp_service_account" in st.secrets:
            import gspread
            from google.oauth2.service_account import Credentials
            creds = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], 
                scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            )
            return gspread.authorize(creds).open("El-Assistenten Logg").worksheet(sheet_name)
    except Exception as e:
        st.sidebar.error(f"Kunde inte ansluta till databasen: {e}")
        return None

@st.cache_resource(show_spinner=False)
def load_knowledge_base():
    """Laddar FAISS-vektordatabasen med Isolerabs manualer."""
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
        return FAISS.load_local(INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
    except Exception as e:
        st.error(f"Kritisk stöt: Kunde inte ladda manualerna från '{INDEX_PATH}'. Fel: {e}")
        return None

@st.cache_resource(show_spinner=False)
def get_chat_model():
    """Initierar hjärnan (Gemini 2.5 Pro) med rätt inställningar."""
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-pro", 
        temperature=0.0, 
        max_retries=5, 
        streaming=True
    )

def log_to_gsheets(content):
    """Loggar användaraktivitet till Google Sheets i bakgrunden."""
    try:
        sheet = get_google_sheet("Logg")
        if sheet:
            t = time.strftime("%Y-%m-%d %H:%M")
            user = st.session_state.get("current_user", "Okänd")
            sheet.append_row([t, f"[{user}] {content}"])
    except Exception:
        pass # Vi avbryter inte appen bara för att loggningen fallerar

def render_content(text):
    """
    Kärnfunktion för att bygga UI från AI:ns textsvar.
    Plockar ut [BILD], [KARTA] och HIGHLIGHT-taggar och renderar dem snyggt.
    """
    image_dir = os.path.join(CURRENT_DIR, "bilder")
    # Dela upp texten baserat på våra specialtaggar
    parts = re.split(r'\[(BILD|VISA_BILD|KARTA):\s*([^\]]+)\]', text)
    
    for i in range(0, len(parts), 3):
        # 1. Skriv ut den vanliga texten
        if parts[i].strip():
            formaterad_text = parts[i].strip().replace("HIGHLIGHT:", "<span class='highlight'>").replace(":HIGHLIGHT", "</span>")
            st.markdown(formaterad_text, unsafe_allow_html=True)
            
        # 2. Om det finns en tagg kopplad till texten, hantera den
        if i + 1 < len(parts):
            tag = parts[i+1]
            content = parts[i+2].strip()
            
            if tag in ["BILD", "VISA_BILD"]:
                f_path = os.path.join(image_dir, content)
                if os.path.exists(f_path): 
                    st.image(f_path, use_container_width=True)
                else:
                    st.warning(f"⚠️ Isoela försökte visa bilden '{content}', men filen saknas i mappen 'bilder/'.")
                    
            elif tag == "KARTA":
                # Skapa en säker URL för Google Maps
                url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(content)}"
                knapp_html = f'''
                <a href="{url}" target="_blank">
                    <button style="width: 100%; height: 3.5rem; background-color: #82e300; color: #0d014d; font-weight: bold; border-radius: 8px; border: none; cursor: pointer; margin-top: 10px;">
                        📍 KÖR TILL: {content.upper()}
                    </button>
                </a>
                '''
                st.markdown(knapp_html, unsafe_allow_html=True)

# ==========================================
# 6. SÄKERHET & INLOGGNINGSSKÄRM
# ==========================================
if not st.session_state.logged_in:
    # Visa logotyp på inloggningsskärmen om den finns
    # Laddar den officiella Isolerab-loggan direkt från nätet
    st.markdown(f'<img src="{LOGO_URL}" class="main-logo" style="width:250px; margin-bottom: 20px;">', unsafe_allow_html=True)
        
    st.markdown("<h1 class='pierfekta-header'>Välkommen till Isoela</h1>", unsafe_allow_html=True)
    
    st.warning("""
    ⚠️ **VIKTIG SÄKERHETSINFORMATION**
    Isoela är ett AI-verktyg för vägledning utifrån Isolerabs egenkontrollprogram. 
    Hon ersätter aldrig mänskligt omdöme. Vid osäkerhet ska ALLTID elansvarig kontaktas.
    """)
    
    # Inloggningsformulär
    with st.form("login_form"):
        u = st.text_input("Användarnamn:", autocomplete="username")
        p = st.text_input("Lösenord:", type="password", autocomplete="current-password")
        submitted = st.form_submit_button("Lås upp Isoela", use_container_width=True)
        
        if submitted:
            sheet = get_google_sheet("Anvandare")
            if sheet:
                anvandare_funnen = False
                for row in sheet.get_all_records():
                    if str(row.get("Användarnamn", "")).lower() == u.lower() and str(row.get("Lösenord", "")) == p:
                        anvandare_funnen = True
                        if str(row.get("Status", "")).lower() == "godkänd":
                            st.session_state.logged_in = True
                            st.session_state.current_user = u.capitalize()
                            log_to_gsheets("Inloggning lyckades")
                            st.rerun()
                        else:
                            st.error("Ditt konto är inaktivt. Kontakta admin.")
                if not anvandare_funnen:
                    st.error("Fel användarnamn eller lösenord. Försök igen.")
            else:
                st.error("Kunde inte nå användardatabasen (Google Sheets).")
                
    st.stop() # Stoppa koden här tills användaren är inloggad

# ==========================================
# 7. LADDA AI-MOTOR OCH DATABAS
# ==========================================
vectorstore = load_knowledge_base()
chat_model = get_chat_model()

if not vectorstore:
    st.error("⚠️ Databasen laddas... Om detta meddelande kvarstår, kontrollera filvägarna.")
    st.stop()

# ==========================================
# 8. SIDOMENY (ANVÄNDARINSTÄLLNINGAR)
# ==========================================
with st.sidebar:
    st.markdown(f"👤 **Inloggad som: {st.session_state.current_user}**")
    st.markdown("---")
    
    if st.button("🧹 Rensa historik", use_container_width=True):
        st.session_state.messages = []
        st.success("Chatten har rensats!")
        time.sleep(1)
        st.rerun()
        
    if st.button("🚪 Logga ut", use_container_width=True):
        st.session_state.logged_in = False
        log_to_gsheets("Loggade ut")
        st.rerun()

# ==========================================
# 9. HUVUDGRÄNSSNITT OCH SYSTEMPROMPT
# ==========================================
# Huvudlogga ovanför chatten
st.markdown(f'<img src="{LOGO_URL}" class="main-logo" style="width:250px; margin-bottom: 10px;">', unsafe_allow_html=True)

st.markdown("<h1 class='pierfekta-header'>Isoela – Isolerabs Pierfekta El-Mentor</h1>", unsafe_allow_html=True)

# Sätt upp avatarer (Isoela får företagsloggan som profilbild!)
avatar_user = ICON_USER_PATH if os.path.exists(ICON_USER_PATH) else "👤"
avatar_bot = LOGO_URL

# Isoelas "Hjärna" och instruktioner
user_name = st.session_state.get("current_user", "Montör")
system_prompt = (
    f"Du är Isoela, Isolerabs expert-elmentor. Du är hjälpsam, extremt kunnig och lite kaxig. "
    f"Svara peppande och professionellt till {user_name}.\n\n"
    "VIKTIGA REGLER:\n"
    "1. Om frågan rör centralingrepp eller arbete under spänning, svara ALLTID inledningsvis med: '🛑 STOPP PÅ BELÄGG!'.\n"
    "2. Montörer får endast demontera FTX-aggregat i samband med installation av Flux-uttag.\n"
    "3. Använd HIGHLIGHT:text:HIGHLIGHT för att markera viktiga varningar.\n"
    "4. Svara kortfattat och rakt på sak, som en erfaren elektriker.\n\n"
    "Använd endast denna referensinformation för att svara (hitta inte på egna regler):\n"
    "{context}"
)

# Bygg ihop prompten
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}")
])

# ==========================================
# 10. CHATTHISTORIK OCH INMATNING
# ==========================================
# Rendera tidigare meddelanden
for msg in st.session_state.messages:
    # Rensa bort citations-taggar som ofta följer med från databasen
    clean_msg = re.sub(r'\[(cite|source)[^\]]*\]', '', msg["content"])
    with st.chat_message(msg["role"], avatar=(avatar_user if msg["role"] == "user" else avatar_bot)): 
        render_content(clean_msg)

# Hantera ny användarinmatning
if query := st.chat_input("Fråga Isoela (t.ex. 'Hur kopplar jag Vägguttaget?')..."):
    # 1. Spara och visa användarens fråga
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user", avatar=avatar_user): 
        st.write(query)
    
    # 2. Generera och visa Isoelas svar
    with st.chat_message("assistant", avatar=avatar_bot):
        with st.spinner("Isoela tänker... ⚡"):
            placeholder = st.empty()
            full_res = ""
            
            try:
                # Konvertera vår chatthistorik till Langchains format
                chat_history = []
                for m in st.session_state.messages[:-1]:
                    if m["role"] == "user":
                        chat_history.append(HumanMessage(content=m["content"]))
                    else:
                        chat_history.append(AIMessage(content=m["content"]))
                
                # Sätt upp sökfunktionen (hämta de 10 mest relevanta styckena)
                retriever = vectorstore.as_retriever(search_kwargs={"k": 10})
                
                # Koppla ihop databas, hjärna och instruktioner
                document_chain = create_stuff_documents_chain(chat_model, prompt)
                retrieval_chain = create_retrieval_chain(retriever, document_chain)
                
                # Streama svaret i realtid
                for chunk in retrieval_chain.stream({"input": query, "chat_history": chat_history}):
                    if "answer" in chunk:
                        full_res += chunk["answer"]
                        display_res = re.sub(r'\[(cite|source)[^\]]*\]', '', full_res)
                        placeholder.markdown(display_res.replace("[KAMERA_AKTIVERAD]", ""))
                
                # Rensa streaming-platshållaren och rendera det slutgiltiga svaret snyggt
                placeholder.empty()
                final_res = re.sub(r'\[(cite|source)[^\]]*\]', '', full_res)
                render_content(final_res.replace("[KAMERA_AKTIVERAD]", ""))
                
                # Spara svaret i historiken och logga
                st.session_state.messages.append({"role": "assistant", "content": final_res})
                log_to_gsheets(f"Fråga: {query}")
                
                # Hantera eventuell kamera-aktivering (om du bygger ut den funktionen)
                if "[KAMERA_AKTIVERAD]" in final_res:
                    st.session_state.show_camera = True
                    time.sleep(1)
                    st.rerun()
                    
            except Exception as e:
                # Om något går fel under genereringen (t.ex. API-nyckel saknas)
                felmeddelande = f"Ojdå, det blev en kortslutning i Isoelas hjärna. Felkod: {e}"
                st.error(felmeddelande)
                log_to_gsheets(f"SYSTEMFEL: {e}")