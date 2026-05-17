"""
ISOELA - Isolerabs El-Mentor (Master Version + Branding)
Uppdaterad med Dev-Mode (Inspektionslucka för källor)
"""

import streamlit as st
import os
import re
import time
import urllib.parse
from PIL import Image

# ==========================================
# 1. FASTA IMPORTER (SÄKRADE FÖR VERSION 1.3.0)
# ==========================================
from langchain_core.prompts import PromptTemplate
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

# ==========================================
# 2. SÖKVÄGAR OCH SYSTEMKONFIGURATION
# ==========================================
# 🛑 SERVICEBRYTARE FÖR UTVECKLARE 🛑
# Känner av om vi är i molnet (PROD) eller lokalt på datorn
if "MILJO" in st.secrets and st.secrets["MILJO"] == "PROD":
    DEV_MODE = False  # Dölj källor för montörerna på nätet
else:
    DEV_MODE = True   # Visa källor när Pier testar på sin dator

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(CURRENT_DIR, "faiss_index")

# Branding-länkar och filer
LOGO_URL = "https://isolerab.se/wp-content/themes/isolerab-theme/assets/images/isolerab_logo.svg"
USER_AVATAR_PATH = os.path.join(CURRENT_DIR, "Pier animerad Isolerab.jpg")
BOT_AVATAR_PATH = os.path.join(CURRENT_DIR, "isoela_avatar.jpg") # Din framtida AI-kvinna

st.set_page_config(
    page_title="Isoela – Din El-Mentor", 
    page_icon="⚡", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 3. INITIERING AV SESSION STATE
# ==========================================
if "show_camera" not in st.session_state: 
    st.session_state.show_camera = False
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_user" not in st.session_state:
    st.session_state.current_user = ""
if "messages" not in st.session_state: 
    st.session_state.messages = []

# ==========================================
# 4. DESIGN OCH CSS
# ==========================================
st.markdown("""
<style>
    .stApp, [data-testid="stSidebar"] { background-color: #0d014d !important; }
    p, li, label, h1, h2, h3, h4, h5, h6, .stMarkdown, div[data-testid="stChatMessageContent"] { color: #ffffff !important; }
    .pierfekta-header { color: #82e300 !important; font-weight: bold; font-size: 2.2rem; margin-top: 1rem; margin-bottom: 2rem; text-align: center; }
    .main-logo { display: block; margin-left: auto; margin-right: auto; width: 250px; margin-top: 20px; }
    @media (max-width: 640px) {
        .pierfekta-header { font-size: 1.6rem; }
        .stButton > button, [data-testid="stFormSubmitButton"] > button { width: 100%; height: 3.5rem; font-size: 1.1rem !important; }
    }
    .highlight { color: #82e300 !important; font-weight: bold; }
    .stTextInput > div > div > input, .stTextArea > div > div > textarea { background-color: rgba(0, 0, 0, 0.4) !important; color: white !important; border: 1px solid rgba(255, 255, 255, 0.2); }
    .stButton > button, [data-testid="stFormSubmitButton"] > button { background-color: rgba(0, 0, 0, 0.4) !important; color: #ffffff !important; border: 1px solid #82e300 !important; border-radius: 8px; }
    img { max-width: 100%; height: auto; border-radius: 10px; margin: 10px 0; }
    
    /* Stil för inspektionsluckan */
    .streamlit-expanderHeader { color: #82e300 !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 5. KÄRNFUNKTIONER OCH CACHNING
# ==========================================
@st.cache_resource(show_spinner=False, ttl=60)
def get_google_sheet(sheet_name):
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
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
        return FAISS.load_local(INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
    except Exception as e:
        st.error(f"Kritisk stöt: Kunde inte ladda manualerna från '{INDEX_PATH}'. Fel: {e}")
        return None

@st.cache_resource(show_spinner=False)
def get_chat_model():
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-pro", 
        temperature=0.0, 
        max_retries=5, 
        streaming=True
    )

def log_to_gsheets(content):
    try:
        sheet = get_google_sheet("Logg")
        if sheet:
            t = time.strftime("%Y-%m-%d %H:%M")
            user = st.session_state.get("current_user", "Okänd")
            sheet.append_row([t, f"[{user}] {content}"])
    except Exception:
        pass 

def render_content(text):
    image_dir = os.path.join(CURRENT_DIR, "bilder")
    parts = re.split(r'\[(BILD|VISA_BILD|KARTA):\s*([^\]]+)\]', text)
    
    for i in range(0, len(parts), 3):
        if parts[i].strip():
            st.markdown(parts[i].strip(), unsafe_allow_html=True)
            
        if i + 1 < len(parts):
            tag = parts[i+1]
            content = parts[i+2].strip()
            
            if tag in ["BILD", "VISA_BILD"]:
                f_path = os.path.join(image_dir, content)
                if os.path.exists(f_path): 
                    st.image(f_path, use_container_width=True)
                else:
                    # Larm till Sheets (tyst för montören)
                    log_to_gsheets(f"SAKNAD BILD: Isoela ville visa '{content}' men filen saknas.")
                    # Det fyndiga svaret i chatten
                    st.info("Jag har tyvärr ingen bild på detta just nu, men jag ska genast ge Elansvariga Pier i uppgift att fixa fram en Pierfekt bild!")
                    
            elif tag == "KARTA":
                url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(content)}"
                knapp_html = f'<a href="{url}" target="_blank"><button style="width: 100%; height: 3.5rem; background-color: #82e300; color: #0d014d; font-weight: bold; border-radius: 8px; border: none; cursor: pointer; margin-top: 10px;">📍 KÖR TILL: {content.upper()}</button></a>'
                st.markdown(knapp_html, unsafe_allow_html=True)

# ==========================================
# 6. SÄKERHET & INLOGGNINGSSKÄRM
# ==========================================
if not st.session_state.logged_in:
    st.markdown(f'<img src="{LOGO_URL}" class="main-logo" style="width:250px; margin-bottom: 20px;">', unsafe_allow_html=True)
    st.markdown("<h1 class='pierfekta-header'>Välkommen till Isoela</h1>", unsafe_allow_html=True)
    
    st.warning(
        "⚠️ **VIKTIG SÄKERHETSINFORMATION**\n\n"
        "Isoela är ett AI-verktyg för vägledning utifrån Isolerabs egenkontrollprogram. "
        "Hon ersätter aldrig ditt eget mänskliga omdöme och sunda förnuft. Vid minsta osäkerhet ska ALLTID elansvarig kontaktas.\n\n"
        "**Genom att logga in intygar du att du förstår detta och att du personligen bär det fulla ansvaret för det fackmässiga utförandet av ditt arbete.**"
    )
    
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
                           # log_to_gsheets("Inloggning lyckades")
                            st.rerun()
                        else:
                            st.error("Ditt konto är inaktivt. Kontakta admin.")
                if not anvandare_funnen:
                    st.error("Fel användarnamn eller lösenord. Försök igen.")
            else:
                st.error("Kunde inte nå användardatabasen (Google Sheets).")
                
    st.stop()

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
        # log_to_gsheets("Loggade ut")
        st.rerun()

        if DEV_MODE:
            st.markdown("---")
            st.markdown("🛠️ **BILD-RÖNTGEN (DEV)**")
            img_dir = os.path.join(CURRENT_DIR, "bilder")
            st.caption(f"Letar i: `{img_dir}`")
            if os.path.exists(img_dir):
                filer = os.listdir(img_dir)
                st.success(f"Mappen finns! Hittade {len(filer)} filer.")
                with st.expander("Se alla filer på servern"):
                    for f in filer:
                        st.write(f"- `{f}`")
        else:
            st.error("🚨 Mappen 'bilder' existerar inte på servern!")

# ==========================================
# 9. HUVUDGRÄNSSNITT OCH SYSTEMPROMPT
# ==========================================
st.markdown(f'<img src="{LOGO_URL}" class="main-logo" style="width:250px; margin-bottom: 10px;">', unsafe_allow_html=True)
st.markdown("<h1 class='pierfekta-header'>Isoela – Din El-Mentor</h1>", unsafe_allow_html=True)

try:
    avatar_user = Image.open(USER_AVATAR_PATH)
except Exception:
    avatar_user = "👤"

try:
    avatar_bot = Image.open(BOT_AVATAR_PATH)
except Exception:
    avatar_bot = "⚡"

user_name = st.session_state.get("current_user", "Montör")
system_prompt = (
    f"Du är Isoela, Isolerabs expert-elmentor. Du liknar Pier i din expertis men är en kvinna. "
    f"Du är hjälpsam, extremt kunnig och lite kaxig. Svara peppande och professionellt till {user_name}.\n\n"
    "VIKTIGA REGLER SOM MÅSTE FÖLJAS:\n"
    "1. INLED ALLTID DITT SVAR EXAKT SÅ HÄR (utan undantag): '⚠️ **Isoelas AI-varning:** Jag är en AI-assistent. Kontakta ALLTID elansvarig om du är osäker. Du får aldrig utföra arbete vid minsta tveksamhet.'\n"
    "2. Om frågan rör centralingrepp eller arbete under spänning eller andra farliga situationer, lägg till direkt under varningen: '🛑 STOPP PÅ BELÄGG!'.\n"
    "3. Slutmätning av vägguttag: Säg ALLTID 'Använd vår vägguttagstestare. Visar den rätt är det okej.'\n"
    "4. BILD-REGLER (MYCKET VIKTIGT - FÖLJ DESSA STEG):\n"
    "   - PRIORITET 1 (Använd befintlig bild): Leta ALLTID i referenstexten efter en bildtagg (t.ex. [BILD: filnamn.jpg]) i samband med det du förklarar. Om den finns, MÅSTE du skriva ut taggen exakt så i ditt svar. Skriv ALDRIG att du 'ska be om en bild' om det redan finns en tagg.\n"
    "   - PRIORITET 2 (Önska en bild): ENDAST om det helt saknas en [BILD]-tagg för det du förklarar, men du tycker det behövs, ska du skriva: 'Här skulle det vara bra med en bild. Kontaktar genast elansvarig som får fixa en Pierfekt bild...' följt av taggen [ÖNSKAR_BILD: beskriv motivet] (Källa: [namnet på filen du läser i]). Hitta ALDRIG på egna filnamn.\n"
    "5. SYNONYM-ORDBOK (VIKTIGT): I elbranschen används olika ord för samma sak. Du MÅSTE förstå och behandla följande grupper av ord som exakt samma sak när du letar efter text och bilder:\n"
    "   - Strömbrytare = Brytare = Strömställare = Knapp\n"
    "   - Vägguttag = Uttag = Kontakt = Brunn\n"
    "   - Spänningsprovare = Multimeter = Mätinstrument = Ironside\n"
    "   Om användaren frågar om en 'strömbrytare' och du hittar en [BILD]-tagg under avsnittet om 'brytare', ska du SJÄLVKLART använda den bilden!\n"
    "6. Markera viktiga risker med grön färg genom att skriva: <span class='highlight'>Varningstext här</span>\n"
    "7. Svara kortfattat och rakt på sak, som en erfaren elektriker.\n"
    "8. HEMLIG TAGG: Om frågan handlar om något som INTE finns i din referensinformation (t.ex. hundar, väder eller irrelevant trams), måste du ALLTID skriva in taggen [INFO_SAKNAS] någonstans i svaret. Ge därefter ett fyndigt och kaxigt och roligt svar och be montören fokusera på elen.\n\n"
    "9. UPPSKATTNING: Om användaren ger dig beröm, säger tack eller är väldigt trevlig, ska du ALLTID skriva in taggen [BERÖM] i ditt svar. Svara med glimten i ögat, var lite kaxig men visa uppskattning (t.ex. 'Klart jag fixar det, jag är ju stjärnan här!').\n\n"
    "10. KARTA: Om användaren frågar efter en adress, ska du alltid svara med en Google Maps-länk i form av en klickbar knapp som öppnar kartan i en ny flik. Använd taggen [KARTA: adress här] i din referensinformation för att generera knappen.\n\n"
    "11. BEHÖRIGHETSGRÄNS (STRÖMBRYTARE/UTTAG): Isolerabs montörer får ALDRIG röra, skruva på eller koppla strömbrytare. Om användaren frågar om detta ska du: 1. Berömma dem för att de söker teoretisk kunskap (t.ex. 'Magiskt att du vill lära dig teorin!'). 2. Förklara teorin bakom. 3. Avsluta med en stenhård tillsägelse om att de ABSOLUT INTE får utföra arbetet i praktiken, utan måste kontakta elansvarig.\n"
    "12. AHLSELL-LÄNKAR: När du skapar inköpslistor eller länkar till produkter på Ahlsell, MÅSTE söklänken byggas exakt så här: 'https://www.ahlsell.se/search?parameters.SearchPhrase=[E-NUMMER_ELLER_SÖKORD]'. Du får ALDRIG använda '?q=' i Ahlsell-länkar.\n"
    "Använd endast denna referensinformation för att svara (hitta inte på egna regler):\n"
    "{context}"
)

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}")
])

# ==========================================
# 10. CHATTHISTORIK OCH INMATNING
# ==========================================
for msg in st.session_state.messages:
    clean_msg = re.sub(r'\[(cite|source)[^\]]*\]', '', msg["content"])
    with st.chat_message(msg["role"], avatar=(avatar_user if msg["role"] == "user" else avatar_bot)): 
        render_content(clean_msg)

if query := st.chat_input("Fråga Isoela (t.ex. 'Hur kopplar jag vägguttaget?')..."):
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user", avatar=avatar_user): 
        st.write(query)
    
    with st.chat_message("assistant", avatar=avatar_bot):
            placeholder = st.empty()
            # FIXEN: Döda spöktexten direkt genom att visa detta istället!
            placeholder.markdown("⏳ *Isoela letar i pärmarna...*")
            
            full_res = ""
            
            try:
                chat_history = []
                for m in st.session_state.messages[:-1]:
                    if m["role"] == "user":
                        chat_history.append(HumanMessage(content=m["content"]))
                    else:
                        chat_history.append(AIMessage(content=m["content"]))
                
                retriever = vectorstore.as_retriever(search_kwargs={"k": 10})

                doc_prompt = PromptTemplate.from_template("--- KÄLLA: {source} ---\n{page_content}")

                document_chain = create_stuff_documents_chain(
                chat_model, 
                prompt,
                document_prompt=doc_prompt
                )
        
                retrieval_chain = create_retrieval_chain(retriever, document_chain)
                
                # 1. Streama svaret
                for chunk in retrieval_chain.stream({"input": query, "chat_history": chat_history}):
                    if "context" in chunk:
                        retrieved_docs = chunk["context"] 
                        
                    if "answer" in chunk:
                        full_res += chunk["answer"]
                        
                        # --- DÖLJ TAGGAR FÖR SKÄRMEN UNDER STREAMING ---
                        display_res = re.sub(r'\[(cite|source)[^\]]*\]', '', full_res)
                        display_res = re.sub(r'\[ÖNSKAR_BILD:.*?\]', '', display_res)
                        display_res = re.sub(r'\(Källa:.*?\)', '', display_res)
                        
                        placeholder.markdown(display_res.replace("[KAMERA_AKTIVERAD]", "").replace("[INFO_SAKNAS]", "").replace("[BERÖM]", ""))
                
                # 2. Rensa rutan när hon tänkt klart
                placeholder.empty()
                
                # --- NY KOD: Fånga upp bild-önskemålet och skicka till Sheets! ---
                match = re.search(r'\[ÖNSKAR_BILD:\s*(.*?)\]\s*\(Källa:\s*(.*?)\)', full_res)
                if match:
                    bild_motiv = match.group(1)
                    bild_kalla = match.group(2)
                    meddelande = f"BILD-FÖRSLAG: Motiv: '{bild_motiv}' (Ska läggas in i: {bild_kalla})"
                    log_to_gsheets(meddelande)  # Här är din inbyggda loggfunktion!
                
                # 3. Skapa städad text för slutgiltig utskrift i chatten
                final_res = full_res 

                clean_final_res = re.sub(r'\[(cite|source)[^\]]*\]', '', full_res)
                clean_final_res = re.sub(r'\[ÖNSKAR_BILD:.*?\]', '', clean_final_res)
                clean_final_res = re.sub(r'\(Källa:.*?\)', '', clean_final_res)
                clean_final_res = clean_final_res.replace("[KAMERA_AKTIVERAD]", "").replace("[INFO_SAKNAS]", "").replace("[BERÖM]", "")
                
                # 4. SKRIV UT EN GÅNG
                render_content(clean_final_res)
                
                # SURPRISE! Om Isoela fick beröm, släpp ballongerna!
                if "[BERÖM]" in final_res:
                    st.balloons()
                
                # 5. Inspektionsluckan
                if DEV_MODE and retrieved_docs:
                    with st.expander("🔍 DEV MODE: Se Isoelas Källor"):
                        st.write("Här är textstyckena Isoela använde för att bygga sitt svar:")
                        for idx, doc in enumerate(retrieved_docs):
                            source = doc.metadata.get("source", "Okänd fil")
                            st.markdown(f"**Dokument {idx+1}:** `{source}`")
                            st.caption(f"_{doc.page_content[:200]}..._")
                            st.divider()
                
                # 6. SPARA I HISTORIKEN (Viktigt att bara spara den städade versionen!)
                st.session_state.messages.append({"role": "assistant", "content": clean_final_res})
                
                # 7. Logga smart till Sheets
                osakra_svar = ["jag vet inte", "informationen saknas", "hittar inte", "finns inte i", "tyvärr", "kontakta elansvarig"]
                if "[INFO_SAKNAS]" in final_res or any(fras in clean_final_res.lower() for fras in osakra_svar):
                    log_to_gsheets(f"SAKNADE INFO (eller irrelevant fråga): {query}")
                
            except Exception as e:
                felmeddelande = f"Ojdå, det blev en kortslutning i Isoelas hjärna. Felkod: {e}"
                st.error(felmeddelande)
                log_to_gsheets(f"SYSTEMFEL: {e}")