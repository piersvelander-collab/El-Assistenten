import streamlit as st
import os
import re
import base64
import time
from PIL import Image
import streamlit.components.v1 as components
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage

# --- 1. SIDKONFIGURATION OCH BRANDING ---
current_dir = os.path.dirname(os.path.abspath(__file__))
log_path = os.path.join(current_dir, "saknade_fragor.txt")
logo_path = os.path.join(current_dir, "bilder", "logo.png")
index_path = os.path.join(current_dir, "faiss_index")

try:
    app_icon = Image.open(logo_path)
except:
    app_icon = "⚡"

st.set_page_config(page_title="El-Assistenten", page_icon=app_icon, layout="centered")

# --- OPTIMERING: CACHING AV TUNGA FUNKTIONER ---
# Detta gör att appen blir blixtsnabb och inte laddar om databasen på varje klick!
@st.cache_resource(show_spinner=False)
def load_knowledge_base():
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
        return FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
    except Exception as e:
        return None

@st.cache_resource(show_spinner=False)
def get_chat_model():
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0, max_retries=5)

vectorstore = load_knowledge_base()
chat_model = get_chat_model()

# --- 2. DESIGN OCH FÄRGSCHEMA ---
st.markdown("""
<style>
    .stApp, [data-testid="stSidebar"] { background-color: #0d014d !important; }
    p, li, label, h1, h2, h3, h4, h5, h6, .stMarkdown, div[data-testid="stChatMessageContent"] { color: #ffffff !important; }
    .pierfekta-header { color: #82e300 !important; font-weight: bold; font-size: 2.5rem; margin-bottom: 1rem; }
    .highlight { color: #82e300 !important; font-weight: bold; }
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        background-color: rgba(0, 0, 0, 0.4) !important; color: white !important; border: 1px solid rgba(255, 255, 255, 0.2);
    }
    .stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus { border-color: #82e300 !important; }
    .stButton > button { background-color: rgba(0, 0, 0, 0.4) !important; color: #ffffff !important; border: 1px solid #82e300 !important; }
</style>
""", unsafe_allow_html=True)

# --- 3. DÖRRVAKTEN & SIDOMENYN (Admin & Självinlärning) ---
with st.sidebar:
    st.markdown("### 🔒 Personal-inloggning")
    admin_password = st.text_input("Lösenord:", type="password")
    is_admin = False
    
    if "ADMIN_PASSWORD" in st.secrets and admin_password == st.secrets["ADMIN_PASSWORD"]:
        is_admin = True
        st.success("✅ Inloggad som Pierfekt Admin")
        st.divider()
        
        log_lines = []
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                log_lines = f.readlines()
        
        unanswered_qs = [line.strip().replace("- ", "") for line in log_lines if line.strip()]
        
        st.header("📝 Kunskaps-logg")
        if unanswered_qs:
            st.text_area("Frågor att åtgärda:", "\n".join(unanswered_qs), height=150)
            if st.button("Rensa hela loggen"):
                os.remove(log_path)
                st.rerun()
        else:
            st.info("Inga frågor loggade.")
            
        st.divider()
        st.header("🧠 Lär Assistenten")
        if unanswered_qs:
            selected_q = st.selectbox("Välj fråga att besvara:", unanswered_qs)
            new_answer = st.text_area(f"Skriv Isolerabs officiella svar:", height=150)
            
            if st.button("Generera och Lär in!"):
                if new_answer.strip():
                    try:
                        md_content = f"# Svar gällande: {selected_q}\n\n{new_answer}"
                        if vectorstore:
                            vectorstore.add_texts([md_content], metadatas=[{"source": "admin_inmatning"}])
                        
                        docs_dir = os.path.join(current_dir, "dokument")
                        if not os.path.exists(docs_dir): os.makedirs(docs_dir)
                        filename = f"inlart_fakta_{int(time.time())}.md"
                        with open(os.path.join(docs_dir, filename), "w", encoding="utf-8") as f:
                            f.write(md_content)
                        
                        unanswered_qs.remove(selected_q)
                        with open(log_path, "w", encoding="utf-8") as f:
                            for q in unanswered_qs: f.write(f"- {q}\n")
                                
                        st.success("✅ Inlärt! Boten kan svara nu.")
                        st.download_button(label="📥 Ladda ner .md-fil för GitHub", data=md_content, file_name=filename, mime="text/markdown")
                    except Exception as e:
                        st.error(f"Fel vid inlärning: {e}")
        else:
            st.success("Allt är besvarat!")
            
    elif admin_password:
        st.error("Fel lösenord")

# --- 4. API-NYCKEL ---
if "GOOGLE_API_KEY" in st.secrets:
    os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]
else:
    google_api_key = st.sidebar.text_input("API-nyckel:", type="password")
    if not google_api_key: st.stop()
    os.environ["GOOGLE_API_KEY"] = google_api_key

# --- 5. HEADER OCH VERKTYGSLÅDA ---
if os.path.exists(logo_path): st.image(logo_path, width=150)
st.markdown("<h1 class='pierfekta-header'>ISOLERABs Pierfekta El-Assistent</h1>", unsafe_allow_html=True)

if not vectorstore:
    if is_admin: st.error("Kunde inte ladda databasen. Kontrollera faiss_index mappen.")
    else: st.error("⚠️ Systemet uppdateras, försök igen snart.")
    st.stop()

# VERKTYG 1: Färg-hjälpen
with st.expander("📸 Färg-Hjälpen (Kamera)"):
    st.warning("⚠️ **LIVSVIKTIGT:** Kamerablixt och skuggor kan få mig att se fel färg. Kontrollmäta alltid!")
    cam_photo = st.camera_input("Ta en bild på dosan")
    if cam_photo and st.button("Analysera färgerna"):
        with st.spinner("Granskar bilden..."):
            try:
                img_b64 = base64.b64encode(cam_photo.getvalue()).decode()
                img_data = f"data:image/jpeg;base64,{img_b64}"
                vision_msg = HumanMessage(content=[
                    {"type": "text", "text": "Du är färg-tolk åt en färgblind elektriker. Beskriv vilka färger kablarna har baserat på deras placering (t.ex. vänster, mitten, höger). Var extra noga med rött, grönt och brunt."},
                    {"type": "image_url", "image_url": {"url": img_data}}
                ])
                vision_res = chat_model.invoke([vision_msg])
                st.session_state.messages.append({"role": "user", "content": "📸 *Skickade en bild för färganalys.*"})
                st.session_state.messages.append({"role": "assistant", "content": vision_res.content})
                st.rerun()
            except Exception as e:
                st.error("Fel vid bildanalys. Kan bero på överbelastning, försök igen.")

# VERKTYG 2: Kalkylatorn
with st.expander("🧮 Snabba Kalkylatorn"):
    st.markdown("Räkna snabbt ut om säkringen håller för utrustningen!")
    col1, col2 = st.columns(2)
    with col1:
        volt = st.number_input("Spänning (V)", value=230, step=10)
    with col2:
        amp = st.number_input("Ström / Belastning (A)", value=10.0, step=0.5)
    
    watt = volt * amp
    st.info(f"**Total effekt:** {watt:.0f} W ({watt/1000:.2f} kW)")
    
    säkring = st.selectbox("Säkringsstorlek (A)", [6, 10, 13, 16, 20, 25])
    if amp > säkring:
        st.error(f"⚠️ Varning: Belastningen ({amp}A) är för hög för en {säkring}A säkring!")
    else:
        st.success(f"✅ Säkringen håller. Du har {säkring - amp:.1f}A till godo på denna grupp.")

# --- 6. RIT- OCH BILDFUNKTION ---
def render_content(text):
    image_dir = os.path.join(current_dir, "bilder")
    parts = re.split(r'\[(?:VISA_BILD|BILD|SCHEMA):\s*([\s\S]+?)\]', text)
    for i, part in enumerate(parts):
        if i % 2 == 0:
            if part.strip():
                st.markdown(part.strip().replace("HIGHLIGHT:", "<span class='highlight'>").replace(":HIGHLIGHT", "</span>"), unsafe_allow_html=True)
        else:
            content = part.strip()
            if any(content.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif']):
                img_path = os.path.join(image_dir, content)
                if os.path.exists(img_path): st.image(img_path, use_container_width=True)
                elif is_admin: st.warning(f"⚠️ Hittar inte bild: {content}")
            else:
                components.html(f"<pre class='mermaid'>{content}</pre><script type='module'>import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';mermaid.initialize({{startOnLoad:true,theme:'dark',securityLevel:'loose'}});</script>", height=500, scrolling=True)

# --- 7. AI-MOTOR OCH CHATT ---
system_prompt = (
    "Du är Isolerabs el-mentor. Din uppgift är att svara med fakta, branschstandard och expertis.\n"
    "REGLER:\n"
    "1. Om användaren frågar om material, beställningar eller vad som ska köpas hem: Sök ALLTID först i dokumentet 'Isolerabs Materialkatalog' (24_materialkatalog_ahlsell.md). Lista de artiklar som finns där med art.nr och länkar.\n"
    "2. Om användaren frågar 'Vilket material ska jag beställa hem till lagret?', lista hela innehållet i materialkatalogen strukturerat.\n"
    "3. Använd [BILD: filnamn.jpg] eller [SCHEMA: graph TD...] om det behövs.\n"
    "4. Om du hittar svaret i dina manualer, använd det.\n"
    "5. Om du INTE hittar ett specifikt svar i manualerna, svara utifrån din allmänna yrkeskunskap enligt svensk elstandard (SEK 444). Inled då svaret med: 'Jag hittar inte detta i Isolerabs manualer, men min generella kunskap säger följande:'.\n"
    "6. SCENANVISNINGAR: Följ instruktioner som börjar med '(Instruktion för chatboten: ...)' men skriv ALDRIG ut själva instruktionen till användaren.\n"
    "7. Svara alltid på svenska.\n\n"
    "Expertkunskap (Isolerabs Manualer & Materialkatalog):\n{context}"
)

prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])

avatar_user = os.path.join(current_dir, "ikoner", "anvandare.png") if os.path.exists(os.path.join(current_dir, "ikoner", "anvandare.png")) else "👤"
avatar_bot = os.path.join(current_dir, "ikoner", "bot.png") if os.path.exists(os.path.join(current_dir, "ikoner", "bot.png")) else "🤖"

if "messages" not in st.session_state: st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar=(avatar_user if msg["role"]=="user" else avatar_bot)):
        render_content(msg["content"])

if query := st.chat_input("Ställ din spännande el-fråga... (Tips: Använd🎙️)"):
    # PÅSKÄGG: Fira framgång!
    if any(ord in query.lower() for ord in ["pierfekt", "tack", "löst det", "bra jobbat"]):
        st.balloons()
        
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user", avatar=avatar_user): st.write(query)
    
    with st.chat_message("assistant", avatar=avatar_bot):
        with st.spinner("Tänker..."):
            max_försök = 2
            försök = 0
            lyckades = False
            while försök < max_försök and not lyckades:
                try:
                    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
                    chain = create_retrieval_chain(retriever, create_stuff_documents_chain(chat_model, prompt))
                    response = chain.invoke({"input": query})
                    res_text = response["answer"]
                    
                    if "Jag hittar inte detta i Isolerabs manualer" in res_text:
                        with open(log_path, "a", encoding="utf-8") as f: f.write(f"- {query}\n")
                        if is_admin: st.toast("📌 Frågan loggad för inlärning!")
                    
                    safety = "**Använd mina svar med försiktighet, jag är en AI-bot och kan svara fel. Är du osäker så kontakta ALLTID elansvarig innan du utför något arbete!!**\n\n"
                    full_res = safety + res_text
                    render_content(full_res)
                    st.session_state.messages.append({"role": "assistant", "content": full_res})
                    lyckades = True
                except Exception as e:
                    if "503" in str(e) or "UNAVAILABLE" in str(e):
                        försök += 1
                        if försök < max_försök:
                            st.warning("⏳ Hjärnan är lite belastad hos Google just nu. Väntar 3 sekunder...")
                            time.sleep(3)
                        else: st.warning("⏳ Nu är den Pierfekta hjärnan överbelastad. Vänta en minut och försök igen.")
                    else: break
