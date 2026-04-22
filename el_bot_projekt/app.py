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

# Försök ladda Isolerab-loggan för att använda som flik-ikon (favicon)
try:
    app_icon = Image.open(logo_path)
except:
    app_icon = "⚡"

# Sätter namnet i webbläsarfliken och ikonen
st.set_page_config(
    page_title="El-Assistenten", 
    page_icon=app_icon, 
    layout="centered"
)

# --- 2. DESIGN OCH FÄRGSCHEMA (Isolerab-tema) ---
st.markdown("""
<style>
    /* Mörkblå bakgrund för app och sidomeny */
    .stApp, [data-testid="stSidebar"] { 
        background-color: #0d014d !important; 
    }
    
    /* Tvingar ALL text och ALLA rubriker (h1-h6) att bli kritvita för läsbarhet */
    p, li, label, h1, h2, h3, h4, h5, h6, .stMarkdown, div[data-testid="stChatMessageContent"] { 
        color: #ffffff !important; 
    }
    
    /* Isolerab-grön rubrik (Pierfekta-stilen - denna vinner över den vita regeln ovan) */
    .pierfekta-header { 
        color: #82e300 !important; 
        font-weight: bold; 
        font-size: 2.5rem; 
        margin-bottom: 1rem; 
    }
    
    /* Grön färg för highlights */
    .highlight { color: #82e300 !important; font-weight: bold; }
    
    /* Mörka inmatningsfält med vit text */
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        background-color: rgba(0, 0, 0, 0.4) !important; 
        color: white !important; 
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    /* Grön ram vid fokus på fält */
    .stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus { 
        border-color: #82e300 !important; 
    }
    
    /* Gröna knappar */
    .stButton > button { 
        background-color: rgba(0, 0, 0, 0.4) !important; 
        color: #ffffff !important; 
        border: 1px solid #82e300 !important; 
    }
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
        
        # --- LOGGBOKS-HANTERING ---
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
        
        # --- SJÄLVINLÄRNINGS-MODUL ---
        st.header("🧠 Lär Assistenten")
        if unanswered_qs:
            selected_q = st.selectbox("Välj fråga att besvara:", unanswered_qs)
            new_answer = st.text_area(f"Skriv Isolerabs officiella svar:", height=150)
            
            if st.button("Generera och Lär in!"):
                if new_answer.strip():
                    try:
                        md_content = f"# Svar gällande: {selected_q}\n\n{new_answer}"
                        
                        # Uppdatera AI-hjärnan direkt i minnet
                        if 'vectorstore' in st.session_state:
                            st.session_state.vectorstore.add_texts([md_content], metadatas=[{"source": "admin_inmatning"}])
                        
                        # Spara tillfällig fil
                        docs_dir = os.path.join(current_dir, "dokument")
                        if not os.path.exists(docs_dir): os.makedirs(docs_dir)
                        filename = f"inlart_fakta_{int(time.time())}.md"
                        with open(os.path.join(docs_dir, filename), "w", encoding="utf-8") as f:
                            f.write(md_content)
                        
                        # Ta bort frågan ur loggen
                        unanswered_qs.remove(selected_q)
                        with open(log_path, "w", encoding="utf-8") as f:
                            for q in unanswered_qs: f.write(f"- {q}\n")
                                
                        st.success("✅ Inlärt! Boten kan svara nu.")
                        
                        # Nedladdningsknapp för GitHub-uppladdning
                        st.download_button(
                            label="📥 Ladda ner .md-fil för GitHub",
                            data=md_content,
                            file_name=filename,
                            mime="text/markdown"
                        )
                    except Exception as e:
                        st.error(f"Fel vid inlärning: {e}")
        else:
            st.success("Allt är besvarat!")
            
        st.divider()
        st.header("🛠 Felsökning")
        if st.checkbox("Visa hittade filer (Debug)"):
            img_dir = os.path.join(current_dir, "bilder")
            if os.path.exists(img_dir): st.write(f"Bilder: {os.listdir(img_dir)}")
    elif admin_password:
        st.error("Fel lösenord")

# --- 4. API-NYCKEL ---
if "GOOGLE_API_KEY" in st.secrets:
    google_api_key = st.secrets["GOOGLE_API_KEY"]
else:
    google_api_key = st.sidebar.text_input("API-nyckel:", type="password")
    if not google_api_key: st.stop()
os.environ["GOOGLE_API_KEY"] = google_api_key

# --- 5. RENDERERA HEADER ---
if os.path.exists(logo_path):
    st.image(logo_path, width=150)
st.markdown("<h1 class='pierfekta-header'>ISOLERABs Pierfekta El-Assistent</h1>", unsafe_allow_html=True)

# --- 6. RIT- OCH BILDFUNKTION ---
def render_content(text):
    image_dir = os.path.join(current_dir, "bilder")
    pattern = r'\[(?:VISA_BILD|BILD|SCHEMA):\s*([\s\S]+?)\]'
    parts = re.split(pattern, text)
    for i, part in enumerate(parts):
        if i % 2 == 0:
            if part.strip():
                h_text = part.strip().replace("HIGHLIGHT:", "<span class='highlight'>").replace(":HIGHLIGHT", "</span>")
                st.markdown(h_text, unsafe_allow_html=True)
        else:
            content = part.strip()
            if any(content.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif']):
                img_path = os.path.join(image_dir, content)
                if os.path.exists(img_path): st.image(img_path, use_container_width=True)
                elif is_admin: st.warning(f"⚠️ Hittar inte bild: {content}")
            else:
                html_code = f"<pre class='mermaid'>{content}</pre><script type='module'>import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';mermaid.initialize({{startOnLoad:true,theme:'dark',securityLevel:'loose'}});</script>"
                components.html(html_code, height=500, scrolling=True)

# --- 7. HUVUDPROGRAM ---
index_path = os.path.join(current_dir, "faiss_index")
if 'vectorstore' not in st.session_state:
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
        st.session_state.vectorstore = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
    except Exception as e:
        if is_admin: st.error(f"Index-fel: {e}")
        else: st.error("⚠️ Systemet uppdateras, försök igen snart.")
        st.stop()

chat_model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0, max_retries=5)

system_prompt = (
    "Du är Isolerabs el-mentor. Svara alltid med fakta.\n"
    "REGLER:\n1. För bild: [BILD: filnamn.jpg]\n"
    "2. För schema: [SCHEMA: graph TD...]\n"
    "3. Vid osäkerhet, inled: 'Jag hittar inte detta i Isolerabs manualer, men min generella kunskap säger följande:'\n"
    "4. Svara på svenska.\n"
    "5. SCENANVISNINGAR: Följ instruktioner i texten som börjar med '(Instruktion för chatboten: ...)' men skriv ALDRIG ut själva instruktionen till användaren.\n\n"
    "Expertkunskap:\n{context}"
)
prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])

avatar_user_path = os.path.join(current_dir, "ikoner", "anvandare.png")
avatar_bot_path = os.path.join(current_dir, "ikoner", "bot.png")
avatar_user = avatar_user_path if os.path.exists(avatar_user_path) else "👤"
avatar_bot = avatar_bot_path if os.path.exists(avatar_bot_path) else "🤖"

if "messages" not in st.session_state: st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar=(avatar_user if msg["role"]=="user" else avatar_bot)):
        render_content(msg["content"])

# --- KAMERA-FUNKTION (Färg-Hjälpen) ---
with st.expander("📸 Färg-Hjälpen (Titta på kablar med kameran)"):
    st.warning("⚠️ **LIVSVIKTIGT:** Jag är en AI. Kamerablixt och skuggor kan få mig att se fel färg. Du MÅSTE alltid kontrollmäta!")
    cam_photo = st.camera_input("Ta en bild på dosan")
    
    if cam_photo:
        if st.button("Analysera färgerna"):
            with st.spinner("Granskar bilden..."):
                max_försök = 2
                försök = 0
                lyckades = False
                while försök < max_försök and not lyckades:
                    try:
                        img_b64 = base64.b64encode(cam_photo.getvalue()).decode()
                        img_data = f"data:image/jpeg;base64,{img_b64}"
                        vision_msg = HumanMessage(content=[
                            {"type": "text", "text": "Du är färg-tolk åt en färgblind elektriker. Beskriv vilka färger kablarna har baserat på deras placering (t.ex. vänster, mitten, höger). Var extra noga med rött, grönt och brunt. Avsluta med en skarp varning om att alltid kontrollmäta."},
                            {"type": "image_url", "image_url": {"url": img_data}}
                        ])
                        vision_res = chat_model.invoke([vision_msg])
                        st.session_state.messages.append({"role": "user", "content": "📸 *Skickade en bild för färganalys.*"})
                        st.session_state.messages.append({"role": "assistant", "content": vision_res.content})
                        st.rerun()
                        lyckades = True
                    except Exception as e:
                        if "503" in str(e) or "UNAVAILABLE" in str(e):
                            försök += 1
                            if försök < max_försök:
                                st.warning("⏳ Hjärnan är lite belastad. Väntar 5 sekunder...")
                                time.sleep(5)
                            else: st.warning("⏳ Fortfarande hög belastning. Försök igen om en stund.")
                        else: break

# --- CHATT-INMATNING ---
if query := st.chat_input("Ställ din fråga..."):
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user", avatar=avatar_user): st.write(query)
    with st.chat_message("assistant", avatar=avatar_bot):
        with st.spinner("Tänker..."):
            max_försök = 2
            försök = 0
            lyckades = False
            while försök < max_försök and not lyckades:
                try:
                    retriever = st.session_state.vectorstore.as_retriever(search_kwargs={"k": 3})
                    chain = create_retrieval_chain(retriever, create_stuff_documents_chain(chat_model, prompt))
                    response = chain.invoke({"input": query})
                    res_text = response["answer"]
                    
                    if "Jag hittar inte detta i Isolerabs manualer" in res_text:
                        with open(log_path, "a", encoding="utf-8") as f: f.write(f"- {query}\n")
                        if is_admin: st.toast("📌 Loggad!")
                    
                    safety = "**Använd mina svar med försiktighet, jag är en AI-bot och kan svara fel. Är du osäker så kontakta ALLTID elansvarig innan du utför något arbete!!**\n\n"
                    full_res = safety + res_text
                    render_content(full_res)
                    st.session_state.messages.append({"role": "assistant", "content": full_res})
                    lyckades = True
                except Exception as e:
                    if "503" in str(e) or "UNAVAILABLE" in str(e):
                        försök += 1
                        if försök < max_försök:
                            st.warning("⏳ Hjärnan är lite belastad. Väntar 5 sekunder...")
                            time.sleep(5)
                        else: st.warning("⏳ Nu är den Pierfekta hjärnan lite överbelastad. Försök igen snart!")
                    else: break
