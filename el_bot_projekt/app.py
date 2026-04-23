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
img_log_path = os.path.join(current_dir, "saknade_bilder.txt")
logo_path = os.path.join(current_dir, "bilder", "logo.png")
index_path = os.path.join(current_dir, "faiss_index")

try:
    app_icon = Image.open(logo_path)
except:
    app_icon = "⚡"

st.set_page_config(page_title="El-Assistenten", page_icon=app_icon, layout="centered")

# --- OPTIMERING: CACHING AV TUNGA FUNKTIONER ---
@st.cache_resource(show_spinner=False)
def load_knowledge_base():
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
        return FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
    except Exception as e:
        return None

@st.cache_resource(show_spinner=False)
def get_chat_model():
    # Rätt modell! Blixtsnabba 2.5-flash med streaming aktiverat
    return ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0.0, max_retries=5, streaming=True)

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

# --- 3. DÖRRVAKTEN & SIDOMENYN ---
with st.sidebar:
    st.markdown("### 🔒 Personal-inloggning")
    admin_password = st.text_input("Lösenord:", type="password")
    is_admin = False
    
    if "ADMIN_PASSWORD" in st.secrets and admin_password == st.secrets["ADMIN_PASSWORD"]:
        is_admin = True
        st.success("✅ Inloggad som Pierfekt Admin")
        st.divider()
        
        # Logg för saknade frågor
        log_lines = []
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                log_lines = f.readlines()
        unanswered_qs = [line.strip().replace("- ", "") for line in log_lines if line.strip()]
        
        st.header("📝 Kunskaps-logg")
        if unanswered_qs:
            st.text_area("Frågor att åtgärda:", "\n".join(unanswered_qs), height=100)
            if st.button("Rensa hela loggen"):
                os.remove(log_path)
                st.rerun()
            
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
            st.info("Inga frågor loggade.")
            
        st.divider()

        # Logg för saknade bilder
        img_log_lines = []
        if os.path.exists(img_log_path):
            with open(img_log_path, "r", encoding="utf-8") as f:
                img_log_lines = list(set(f.readlines()))
        missing_imgs = [l.strip() for l in img_log_lines if l.strip()]
        
        st.header("📸 Önskade Bilder")
        if missing_imgs:
            st.markdown("AI:n vill visa dessa bilder. Skapa dem och lägg i `/bilder`:")
            for img_name in missing_imgs:
                st.code(img_name)
            if st.button("Rensa bild-listan"):
                if os.path.exists(img_log_path): os.remove(img_log_path)
                st.rerun()
        else:
            st.info("Inga bild-önskemål än.")
            
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

# VERKTYG 2: Lärlings-Quizet
if 'quiz_q_num' not in st.session_state: st.session_state.quiz_q_num = 0
if 'quiz_score' not in st.session_state: st.session_state.quiz_score = 0
if 'quiz_show_exp' not in st.session_state: st.session_state.quiz_show_exp = False
if 'quiz_selected' not in st.session_state: st.session_state.quiz_selected = None

quiz_data = [
    # KATEGORI 1: Säkerhet, Asbest & Miljö
    {"q": "Vilket år totalförbjöds asbest i Sverige?", "opts": ["1972", "1982", "1992"], "ans": "1982", "exp": "Asbest förbjöds 1982. Hus byggda eller renoverade före detta år är alltid en riskzon."},
    {"q": "Vad är Isolerabs 'Stopp och Belägg'-rutin vid misstänkt asbest?", "opts": ["Ta på P3-mask och borra försiktigt", "Avbryt arbetet, fota och ring ansvarig", "Bryt loss en bit och ta med för analys"], "ans": "Avbryt arbetet, fota och ring ansvarig", "exp": "Din hälsa går först! Rör ingenting, då frigörs livsfarliga fibrer."},
    {"q": "Vilken typ av andningsskydd krävs om du måste vistas på en vind med svartmögel?", "opts": ["Vanligt munskydd/kirurgmask", "Halvmask med P3-filter", "Ingen mask behövs om det korsdrar"], "ans": "Halvmask med P3-filter", "exp": "Ett P3-filter skyddar dina lungor mot de skadliga mögelsporerna i luften."},
    {"q": "I vilken gammal el-utrustning är risken störst att hitta det extremt giftiga ämnet PCB?", "opts": ["I gamla porslinssäkringar", "I läckande kondensatorer i gamla lysrörsarmaturer", "I gamla ojordade vägguttag"], "ans": "I läckande kondensatorer i gamla lysrörsarmaturer", "exp": "PCB användes ofta som olja i kondensatorer fram till 70-talet. Rör aldrig läckande kondensatorer utan skyddshandskar!"},
    {"q": "Vad gör du om du råkar borra hål i husets ångspärr (plastfolien) i taket?", "opts": ["Tätar noggrant med åldersbeständig tejp", "Låter det vara, det ger bra ventilation", "Fyller hålet med tidningspapper"], "ans": "Tätar noggrant med åldersbeständig tejp", "exp": "Ett hål i ångspärren släpper upp fuktig inneluft på vinden, vilket snabbt kan orsaka röta och svartmögel."},
    {"q": "Får du som elektriker bygga en egen liten byggställning av lösvirke om du inte når upp till nocken?", "opts": ["Ja, om den känns stabil", "Nej, ställningar ska vara typgodkända och säkra", "Ja, men bara för korta jobb under 1 timme"], "ans": "Nej, ställningar ska vara typgodkända och säkra", "exp": "Fallolyckor är en av de vanligaste dödsorsakerna i byggbranschen. Chansa aldrig med hemmabyggen."},
    {"q": "Vilken färg har varningsmärkningen för asbest enligt Arbetsmiljöverket?", "opts": ["Gult med svart text", "Svart med röd text", "Vitt med röd text"], "ans": "Gult med svart text", "exp": "Varningstejp och säckar för asbest är alltid märkta med ett tydligt 'a' och varningstext på gul bakgrund."},
    {"q": "Varför är det farligt att lämna gamla bortklippta kabelstumpar på vindsbjälklaget?", "opts": ["Det är en brandfara om de blir varma", "Det bryter mot Isolerabs städrutiner och kan orsaka snubbelfara/skador", "Möss äter dem och dör"], "ans": "Det bryter mot Isolerabs städrutiner och kan orsaka snubbelfara/skador", "exp": "Snyggt och städat ger ett professionellt intryck och förhindrar olyckor för nästa hantverkare."},
    {"q": "Vad är den rekommenderade åtgärden vid en elolycka där en kollega 'fastnat' i strömmen?", "opts": ["Dra bort personen i kläderna", "Slå av strömmen omedelbart innan du rör personen", "Slå larm till 112 först"], "ans": "Slå av strömmen omedelbart innan du rör personen", "exp": "Om du rör personen innan strömmen är bruten riskerar du att själv bli en del av strömkretsen."},
    {"q": "När måste en olycka eller ett allvarligt tillbud (t.ex. kraftig stöt) rapporteras internt?", "opts": ["Endast om du måste åka till sjukhus", "Alltid, omedelbart till projektledare/elansvarig", "Vid slutet av arbetsveckan"], "ans": "Alltid, omedelbart till projektledare/elansvarig", "exp": "Alla tillbud ska rapporteras så att rutiner kan ändras och framtida olyckor undvikas."},
    # KATEGORI 2: Standard & Regler (SEK 444)
    {"q": "Vilken är den normala monteringshöjden för strömbrytare enligt svensk standard?", "opts": ["0.9 m", "1.0 m", "1.2 m"], "ans": "1.0 m", "exp": "Standardhöjden för brytare i bostäder är vanligtvis 1000 mm (1.0 meter) över färdigt golv."},
    {"q": "Vilken IP-klass krävs som minimum vid installation av ett vägguttag på en kallvind?", "opts": ["IP20", "IP21", "IP44"], "ans": "IP44", "exp": "IP44 (Sköljtätt) är standard för fuktiga utrymmen och vindar där kondens och dropp uppstår."},
    {"q": "Vid vilken läckström (felström) ska en jordfelsbrytare för personskydd lösa ut?", "opts": ["10 mA", "30 mA", "300 mA"], "ans": "30 mA", "exp": "För personskydd i bostäder används alltid 30 mA. 300 mA används främst som brandskydd."},
    {"q": "Hur snabbt måste en 30mA jordfelsbrytare senast lösa ut vid ett fel?", "opts": ["Inom 0.03 sekunder", "Inom 0.3 sekunder", "Inom 3 sekunder"], "ans": "Inom 0.3 sekunder", "exp": "Standardkravet är att den ska lösa ut inom 300 ms (0.3 sekunder), men moderna brytare är oftast mycket snabbare."},
    {"q": "Får du installera ett ojordat uttag vid utökning av en anläggning i ett rum som redan har jordade uttag?", "opts": ["Ja, om kunden ber om det", "Nej, aldrig blanda jordat och ojordat i samma rum", "Ja, om det är mer än 2 meter från de andra"], "ans": "Nej, aldrig blanda jordat och ojordat i samma rum", "exp": "Att blanda är livsfarligt. Vid fel kan en apparat bli spänningsförande medan den andra är jordad."},
    {"q": "Vad gäller om du ska byta ett trasigt ojordat uttag i ett gammalt vardagsrum där alla andra uttag är ojordade?", "opts": ["Du måste dra in jord till det uttaget", "Du ska ersätta det med ett likvärdigt ojordat uttag", "Du måste byta hela rummet till jordat direkt"], "ans": "Du ska ersätta det med ett likvärdigt ojordat uttag", "exp": "Vid rent underhåll (byte av trasig apparat) får du ersätta 'lika mot lika' om rummet i övrigt är ojordat."},
    {"q": "Vilken färg MÅSTE skyddsledaren (jorden) alltid ha enligt standard?", "opts": ["Svart", "Gul/Grön", "Blå"], "ans": "Gul/Grön", "exp": "Gul/Grön får ALDRIG användas till något annat än skyddsjord."},
    {"q": "Får den blåa ledaren i en kabel användas som tändtråd i en strömbrytare?", "opts": ["Nej, aldrig under några omständigheter", "Ja, men den måste tejpas om", "Ja, i kablar där blå inte behövs som neutralledare och förväxling ej kan ske"], "ans": "Ja, i kablar där blå inte behövs som neutralledare och förväxling ej kan ske", "exp": "Undantag finns för t.ex. en brytartändning med en 3G1.5, men det är bäst att undvika om möjligt."},
    {"q": "Vad är skillnaden på Typ A och Typ B på en jordfelsbrytare?", "opts": ["Typ B tar mindre plats i centralen", "Typ B känner av rena likströmsfel (DC), Typ A gör det inte", "Typ A är för utomhusbruk"], "ans": "Typ B känner av rena likströmsfel (DC), Typ A gör det inte", "exp": "Typ B krävs ofta för elbilsladdare, solceller eller vissa växelriktare. Typ A är standard i vanliga hushåll."},
    {"q": "Får man montera en kopplingsdosa dolt och oåtkomligt (t.ex. bygga in den med gips)?", "opts": ["Ja, om man svetsar trådarna", "Nej, kopplingspunkter ska alltid vara åtkomliga för underhåll", "Ja, om kunden godkänner det i skrift"], "ans": "Nej, kopplingspunkter ska alltid vara åtkomliga för underhåll", "exp": "En grundregel i elinstallationer är att alla kopplingar och dosor måste vara inspektionsbara."},
    # KATEGORI 3: Egenkontroll & Mätteknik
    {"q": "Vad innebär 'Kontinuitetsmätning'?", "opts": ["Att mäta att spänningen är exakt 230V", "Att mäta att skyddsjorden är hel från centralen ut till apparaten", "Att mäta kabelns isolationsmotstånd"], "ans": "Att mäta att skyddsjorden är hel från centralen ut till apparaten", "exp": "Detta görs för att bekräfta att jorden inte har lossnat eller skadats på vägen, vilket är livsviktigt."},
    {"q": "Vid meggning (isolationsmätning) av en vanlig 230V-anläggning, vilken testspänning används på instrumentet?", "opts": ["250V DC", "500V DC", "1000V DC"], "ans": "500V DC", "exp": "500V Likström (DC) är standard för att stressa isoleringen utan att slå sönder vanliga kablar."},
    {"q": "Vad är det minsta godkända värdet vid en isolationsmätning enligt föreskrifterna?", "opts": ["1 Mohm (Megaohm)", "500 kohm (Kiloohm)", "10 Mohm"], "ans": "1 Mohm (Megaohm)", "exp": "Kravet är >1 Mohm, men en frisk nydragen kabel ligger oftast på >500 Mohm (instrumentet visar OL)."},
    {"q": "Vad är det viktigaste att göra INNAN man meggar (isolationsmäter) en anläggning?", "opts": ["Se till att strömmen är påslagen", "Koppla ur all känslig elektronik (t.ex. Healthbox, dimmers)", "Byta batteri i mätaren"], "ans": "Koppla ur all känslig elektronik (t.ex. Healthbox, dimmers)", "exp": "Megger-instrumentet skickar ut 500V, vilket direkt förstör kretskort i smarta apparater om de sitter kvar i kretsen."},
    {"q": "Är 'Egenkontroll före idrifttagning' bara ett förslag eller ett lagkrav?", "opts": ["Ett bra förslag Isolerab har", "Ett krav från försäkringsbolag", "Ett absolut lagkrav enligt Elsäkerhetslagen"], "ans": "Ett absolut lagkrav enligt Elsäkerhetslagen", "exp": "Innan spänning sätts på MÅSTE anläggningen vara kontrollerad och uppmätt av elinstallatören."},
    {"q": "Du ska mäta spänningen i ett vanligt vägguttag. Mellan vilka stift förväntar du dig ca 230V?", "opts": ["Mellan Fas och Nolla, samt Fas och Jord", "Mellan Nolla och Jord", "Bara mellan Fas och Nolla"], "ans": "Mellan Fas och Nolla, samt Fas och Jord", "exp": "Eftersom både Nollan och Jorden har samma potential (0V) vid centralen, visar mätaren 230V mot båda från Fasen."},
    {"q": "Vad innebär ett 'Spänningslöst tillstånd' vid arbete?", "opts": ["Att du har stängt av strömbrytaren på väggen", "Att anläggningen är frånskild, spärrad, spänningsprovad och jordad vid behov", "Att kunden har sagt att proppen är ur"], "ans": "Att anläggningen är frånskild, spärrad, spänningsprovad och jordad vid behov", "exp": "Lita aldrig på brytare eller andra. Du måste personligen spänningsprova och låsa/säkra centralen."},
    {"q": "Hur kontrollerar du att din spänningsprovare fungerar INNAN du mäter en krets för att se om den är död?", "opts": ["Skakar på den", "Mäter på en känd spänningsförande källa", "Trycker på testknappen"], "ans": "Mäter på en känd spänningsförande källa", "exp": "Mät först på något som har ström (t.ex. inkommande faser) för att bevisa att ditt instrument fungerar, mät sedan den döda kretsen."},
    {"q": "Vad gör du om du upptäcker att det saknas jordfelsbrytare i en villa där du ska installera ventilation?", "opts": ["Skiter i det, det är inte ditt problem", "Informerar kunden, noterar det, och rekommenderar installation för personskydd", "Vägrar göra jobbet tills de installerat en"], "ans": "Informerar kunden, noterar det, och rekommenderar installation för personskydd", "exp": "Som fackman har du skyldighet att påpeka brister. Isolerab säljer gärna in en JFB som ett säkerhets-tillägg (ÄTA)."},
    {"q": "Vid felsökning med en multimeter ställer du den på 'Summer' (Pipsignal). Vad letar du efter?", "opts": ["Spänning", "Resistans/Kontinuitet (Kortslutning eller hel krets)", "Ström (Ampere)"], "ans": "Resistans/Kontinuitet (Kortslutning eller hel krets)", "exp": "Summerfunktionen piper när det är nära 0 ohm, vilket betyder att en ledare är hel (eller att det är kortslutning)."},
    # KATEGORI 4: Material & Verktyg (Ahlsell-Katalogen)
    {"q": "Vilken kabel är Isolerabs standardval för vanlig inomhusförläggning?", "opts": ["N1XV 3G1,5", "EKK-Light 5G1,5", "EXQ Easy 3G1,5"], "ans": "EXQ Easy 3G1,5", "exp": "EXQ Easy är halogenfri, vit och smidig. Det är det självklara valet för standardinstallationer inomhus."},
    {"q": "Varför väljer vi ofta en 'öppningsbar' Wago 221 (med orangea spakar) i kopplingsdosan?", "opts": ["För att den är billigast", "För att den godkänner både enkardelig, fåtrådig och mångtrådig ledare", "För att den lyser i mörkret"], "ans": "För att den godkänner både enkardelig, fåtrådig och mångtrådig ledare", "exp": "Den öppningsbara klämman klämmer åt ordentligt oavsett om det är en styv FK/EQ eller en mjuk anslutningskabel."},
    {"q": "Om du ska göra en skarv som drar extremt mycket ström över lång tid, vad bör du tänka på med snabbklämmor (Wago)?", "opts": ["Vira tejp runt klämman", "Att klämman ofta bara tål max 24A-32A och att en dålig skalning kan skapa varmgång", "Byt ut till en Torix (ubåt)"], "ans": "Att klämman ofta bara tål max 24A-32A och att en dålig skalning kan skapa varmgång", "exp": "Snabbklämmor är säkra, men hög belastning + dålig kontakt = brandrisk. Skala alltid rätt längd!"},
    {"q": "Vilket diameter-mått har standard flexrör (PM-Flex) som används vid de flesta dolda dragningar?", "opts": ["16 mm", "20 mm", "25 mm"], "ans": "16 mm", "exp": "16 mm är standard för vanliga rördragningar av t.ex. 3G1.5 och FK i vanliga väggar."},
    {"q": "Vilken klammer används ofta för att montera EXQ-kabel snyggt och diskret på trävägg?", "opts": ["Buntband", "Letti-klammer (Enkelbent)", "Skruvclips TC"], "ans": "Letti-klammer (Enkelbent)", "exp": "Lettiklammer ger en låg profil och slår fast kabeln dikt mot underlaget för en snygg installation."},
    {"q": "När används oftast en TKK-klammer (spikklammer med plastbygel)?", "opts": ["För att fästa stora VP-rör", "För snabb och standardmässig förläggning av kabel i gips/trä", "Bara utomhus"], "ans": "För snabb och standardmässig förläggning av kabel i gips/trä", "exp": "TKK (t.ex. 7-10) är montörens standardklammer för snabb montering av runda kablar."},
    {"q": "Du ska montera ett uttag på utsidan av huset, vilket uttag från materialkatalogen väljer du?", "opts": ["Ett vanligt ojordat 2-vägsuttag", "Aqua Stark IP44 (Polarvit)", "Vilket uttag som helst bara det sitter under tak"], "ans": "Aqua Stark IP44 (Polarvit)", "exp": "Uttag utomhus ska alltid vara jordade och minst uppfylla kapslingsklass IP44."},
    {"q": "Vad är fördelen med en 'Förhöjningsram' till ett vägguttag?", "opts": ["Man slipper fälla in en dosa i väggen (utanpåliggande montage)", "Den gör att uttaget tål vatten bättre", "Den förstärker strömmen"], "ans": "Man slipper fälla in en dosa i väggen (utanpåliggande montage)", "exp": "När du drar utanpåliggande kabel (EXQ) sätter du uttaget i en förhöjningsram istället för i en infälld dosa."},
    {"q": "Varför används ofta 'Montageband Rör (Hålband)' vid större ventilationsjobb?", "opts": ["För att hänga upp verktygen", "För att jorda aggregatet", "För att hänga upp spirorör eller stabilisera installationer"], "ans": "För att hänga upp spirorör eller stabilisera installationer", "exp": "Hålband är extremt starka och böjbara, perfekta för att fästa tunga ventilationsrör i takstolar."},
    {"q": "Vad är det viktigt att tänka på vid användning av buntband utomhus eller på kalla vindar?", "opts": ["Använda röda buntband för värme", "Använda UV- och köldbeständiga buntband (ofta svarta)", "Endast knyta med ståltråd utomhus"], "ans": "Använda UV- och köldbeständiga buntband (ofta svarta)", "exp": "Vanliga vita plast-buntband (natur) spricker lätt av kyla och solljus efter några år."},
    # KATEGORI 5: Kabelförläggning & Praktik
    {"q": "Vilket är det rekommenderade klammeravståndet (horisontellt) för en standardkabel (EXQ) för ett snyggt resultat?", "opts": ["Ca 10 cm", "Ca 20-25 cm", "Ca 50 cm"], "ans": "Ca 20-25 cm", "exp": "Ett tätare avstånd (ca en hammarlängd) gör att kabeln inte hänger ner sig och installationen ser professionell ut."},
    {"q": "Vad händer om du klamrar en kabel för hårt (t.ex. slår in spikklammern för långt)?", "opts": ["Isoleringen kan skadas och skapa kortslutning", "Strömmen flödar snabbare", "Kabeln blir styvare och snyggare"], "ans": "Isoleringen kan skadas och skapa kortslutning", "exp": "Trycker du ihop kabeln för hårt kan du krossa manteln och trycka ihop ledarna inuti, vilket leder till brand eller kortslutning."},
    {"q": "Hur ska en kabel dras in i en kopplingsdosa utomhus för att undvika vatteninträngning?", "opts": ["Uppifrån, vatten rinner neråt", "Snett från sidan", "Alltid underifrån (eller med en 'droppögla' om den måste komma ovanifrån)"], "ans": "Alltid underifrån (eller med en 'droppögla' om den måste komma ovanifrån)", "exp": "Vatten följer kabeln. Kommer den underifrån kan vattnet inte rinna in i dosan."},
    {"q": "Vad innebär uttrycket 'böjningsradie' för en kabel?", "opts": ["Hur många gånger den tål att böjas fram och tillbaka", "Den snävaste vinkel kabeln får böjas utan att ta skada", "Längden på kabeln"], "ans": "Den snävaste vinkel kabeln får böjas utan att ta skada", "exp": "Böjer du en kabel för skarpt (t.ex. 90 grader runt ett hörn) kan ledarna knäckas och isoleringen spricka."},
    {"q": "Vid förläggning i mark, vilket djup är generellt krav för en kabel utan extra skyddsrör?", "opts": ["10 cm", "35 cm", "65 cm"], "ans": "65 cm", "exp": "Standarddjupet är 65 cm. Om kabeln ligger grundare (tex 35cm) måste den ligga i ett kraftigt skyddsrör."},
    {"q": "Vilken färg har varningsbandet (kabelmarkeringsbandet) som läggs i marken ovanför en elkabel?", "opts": ["Rött", "Gult", "Grönt"], "ans": "Gult", "exp": "Gult band med svarta blixtar läggs ut för att varna grävmaskinister innan de träffar kabeln."},
    {"q": "När du skalar en EXQ-kabel med kniv/skalverktyg, vad är största risken?", "opts": ["Att kniven blir slö", "Att du skär ett osynligt snitt i de inre ledarnas isolering (FK/EQ)", "Att du skär av jorden av misstag"], "ans": "Att du skär ett osynligt snitt i de inre ledarnas isolering (FK/EQ)", "exp": "Skär du genom manteln och in i ledarisoleringen skapar du en framtida felpunkt/kortslutning. Använd alltid rätt verktyg (t.ex. Jokari)."},
    {"q": "Får du klamra en starkströmskabel (230V) och en nätverkskabel under samma klammer?", "opts": ["Ja, om klammern är stor nog", "Nej, de ska hållas separerade", "Ja, men bara korta sträckor"], "ans": "Nej, de ska hållas separerade", "exp": "Det finns krav på separation (isoleringsnivå) mellan starkström och svagström för att förhindra störningar och farliga fel."},
    {"q": "Vilken av följande kablar får ALDRIG grävas ner direkt i marken?", "opts": ["EKK", "N1XV", "EKLK"], "ans": "EKK", "exp": "Vanlig EKK/EXQ (installationskabel) är inte godkänd för förläggning i mark. Använd markkabel som N1XV (ofta svart)."},
    {"q": "Om du måste borra genom en brandcell (t.ex. en tjock vägg mellan två lägenheter), vad måste göras efteråt?", "opts": ["Ingenting, kabeln tätar hålet", "Foga noggrant med brandklassad massa/fogskum", "Sätta upp en varningsskylt"], "ans": "Foga noggrant med brandklassad massa/fogskum", "exp": "Brandtätning är livsviktigt. Lämnas hålet öppet sprider sig brand och rök till nästa lägenhet."},
    # KATEGORI 6: Isolerab & Healthbox/Ventilation
    {"q": "Vad är det primära syftet med att sätta en Arbetsbrytare (Säkerhetsbrytare) vid ett FTX-aggregat på vinden?", "opts": ["För att kunden ska kunna stänga av den enkelt", "För säker och låsbar brytning av strömmen när montören utför service på fläkten", "För att mäta elförbrukningen"], "ans": "För säker och låsbar brytning av strömmen när montören utför service på fläkten", "exp": "Brytaren garanterar att ingen oavsiktligt slår på strömmen från centralen medan du har händerna inne i maskinen."},
    {"q": "Healthbox 3.0 kommunicerar via nätverk. Vilken Wi-Fi-frekvens fungerar den bäst/kravs för smarta enheter oftast?", "opts": ["5 GHz", "2.4 GHz", "Infrarött"], "ans": "2.4 GHz", "exp": "Smarta hem-prylar använder nästan alltid 2.4 GHz för att det har längre räckvidd och går bättre genom väggar än 5 GHz."},
    {"q": "Hur förklarar du enklast för kunden att en Healthbox inte kommer ruinera dem i elförbrukning?", "opts": ["Den drar lika mycket som en ugn", "Fläktmotorn är av EC-typ och drar mycket lite ström (ofta som en gammal glödlampa)", "Den drar ingen ström alls"], "ans": "Fläktmotorn är av EC-typ och drar mycket lite ström (ofta som en gammal glödlampa)", "exp": "Moderna EC-motorer är extremt effektiva och anpassar varvtalet (behovsstyrning), vilket minimerar elförbrukningen."},
    {"q": "Vad gör du om kundens Wi-Fi-signal inte når upp till vinden där aggregatet står?", "opts": ["Dränker aggregatet i antenner", "Säger att appen inte fungerar", "Föreslår och installerar en Wi-Fi-förstärkare (Repeater) som en ÄTA"], "ans": "Föreslår och installerar en Wi-Fi-förstärkare (Repeater) som en ÄTA", "exp": "Detta är ett klassiskt problem. Genom att erbjuda en lösning direkt bygger vi Isolerabs goda rykte (och säljer lite extra)."},
    {"q": "Vad är en 'ÄTA' i byggbranschen?", "opts": ["Ett fikarast-system", "Ändringar, Tillägg och Avgående arbeten (Extrajobb)", "En typ av kabel"], "ans": "Ändringar, Tillägg och Avgående arbeten (Extrajobb)", "exp": "När kunden vill ha tre uttag till i garaget utöver det avtalade är det en ÄTA, och kunden ska debiteras för detta."},
    {"q": "När bör en Egenkontroll (Checklista för installation) fyllas i?", "opts": ["En vecka efter jobbet på kontoret", "Aldrig", "Direkt på plats innan anläggningen lämnas över till kund"], "ans": "Direkt på plats innan anläggningen lämnas över till kund", "exp": "Egenkontrollen ska skrivas medan du mäter upp anläggningen på plats, annars glömmer du mätvärdena."},
    {"q": "Kunden frågar hur ofta de bör byta/rengöra filter i sin anläggning. Vad svarar du?", "opts": ["Aldrig, de håller för evigt", "Minst en gång om året, men gärna kolla dem varje halvår", "Varje vecka"], "ans": "Minst en gång om året, men gärna kolla dem varje halvår", "exp": "Ett tätt filter ökar fläktens elförbrukning, minskar luftflödet och kan orsaka oljud i systemet."},
    {"q": "Varför är det viktigt att dammsuga och städa arbetsplatsen när jobbet är klart, även på en dammig vind?", "opts": ["För att kunden märker det. Ett rent bygge är ett tecken på kvalitet och yrkesstolthet.", "Det är inte viktigt, vinden är ändå skitig", "För att samla asbest"], "ans": "För att kunden märker det. Ett rent bygge är ett tecken på kvalitet och yrkesstolthet.", "exp": "Det sista kunden ser är hur du lämnar platsen. Städningen är Isolerabs billigaste marknadsföring."},
    {"q": "Vad ska du alltid göra om det uppstår en konflikt eller stort missförstånd med kunden på plats?", "opts": ["Bli arg och skrika", "Backa ett steg, vara lugn och ringa din projektledare", "Släppa verktygen och åka därifrån"], "ans": "Backa ett steg, vara lugn och ringa din projektledare", "exp": "Ta inte striden själv på plats. Låt projektledaren hantera det kommersiella medan du fokuserar på att vara ett proffs."},
    {"q": "Innan du stänger dörren och åker från kunden ('Den Pierfekta Överlämningen'), vad är det sista steget?", "opts": ["Be om dricks", "Säkerställa att kunden förstår hur aggregatet/appen fungerar och bekräfta att de är nöjda", "Ta av sig skorna"], "ans": "Säkerställa att kunden förstår hur aggregatet/appen fungerar och bekräfta att de är nöjda", "exp": "När kunden känner sig trygg med den nya tekniken minimerar vi supportsamtalen dagen efter."},
    # KATEGORI 7: Felsökning & Teori (Blandat)
    {"q": "Du skruvar i en propp (smältsäkring) och jordfelsbrytaren slår ifrån DIREKT (pang!). Vad är troligaste felet?", "opts": ["För mycket last (överbelastning)", "En kortslutning mellan Nolla och Skyddsjord någonstans i anläggningen", "Att proppen är för liten"], "ans": "En kortslutning mellan Nolla och Skyddsjord någonstans i anläggningen", "exp": "Om jordfelsbrytaren slår till och med utan belastning, finns det garanterat kontakt mellan Nolla och Jord efter JFB."},
    {"q": "Hur många Watt (W) kan en vanlig enfas 10A-säkring belastas med innan den löser ut (i teorin)?", "opts": ["1000 W", "2300 W", "3600 W"], "ans": "2300 W", "exp": "Effektlagen: P = U * I (230 Volt * 10 Ampere = 2300 Watt)."},
    {"q": "Om du har tre uttag monterade på samma 16A-säkring. Kan du koppla in tre 2000W vattenkokare samtidigt?", "opts": ["Ja, absolut", "Nej, totala effekten blir 6000W, vilket kräver över 26A. Säkringen går.", "Ja, om de är jordade"], "ans": "Nej, totala effekten blir 6000W, vilket kräver över 26A. Säkringen går.", "exp": "En 16A-grupp klarar max cirka 3680 Watt totalt."},
    {"q": "Vad är fördelen med en Dvärgbrytare (Automatsäkring) med C-karakteristik jämfört med en B-karakteristik?", "opts": ["C tål en högre startström under en kort tid (t.ex. motorer/kompressorer) utan att lösa ut", "B är snabbare och därmed bättre", "C är bara för likström"], "ans": "C tål en högre startström under en kort tid (t.ex. motorer/kompressorer) utan att lösa ut", "exp": "C-dvärgar ('Tröga') används ofta till fläktar och pumpar för att de inte ska trippa när motorn startar."},
    {"q": "Vad är oftast felet om en LED-lampa i taket står och 'glimmar' svagt när strömbrytaren är avslagen?", "opts": ["Den drar läckström. Kan ofta lösas med en bottenlast/kondensator över lampan", "Lampan är sönder och kommer explodera", "Huset är hemsökt"], "ans": "Den drar läckström. Kan ofta lösas med en bottenlast/kondensator över lampan", "exp": "LED drar så lite ström att inducerad spänning från kablar intill räcker för att få dem att lysa svagt."},
    {"q": "Vilken enhet mäter vi resistans (motstånd) i?", "opts": ["Volt (V)", "Ampere (A)", "Ohm (Ω)"], "ans": "Ohm (Ω)", "exp": "Ohm beskriver hur stort motstånd elektroner möter i en ledare."},
    {"q": "Vad gör en växelriktare i en solcellsanläggning?", "opts": ["Omvandlar likström (DC) från panelerna till växelström (AC) för huset", "Sparar strömmen i batterier", "Riktar solpanelerna mot solen"], "ans": "Omvandlar likström (DC) från panelerna till växelström (AC) för huset", "exp": "Batterier och paneler jobbar i DC, men våra eluttag kräver AC (50Hz)."},
    {"q": "Vad menas med att 'mäta i serie' respektive 'mäta parallellt'?", "opts": ["Spänning mäts parallellt över komponenten, Ström mäts i serie (genom komponenten)", "Båda mäts i serie", "Båda mäts parallellt"], "ans": "Spänning mäts parallellt över komponenten, Ström mäts i serie (genom komponenten)", "exp": "För att mäta ström måste du 'bryta upp' kretsen och låta strömmen passera GENOM multimetern."},
    {"q": "Hur många faser matar vi in i ett standard vägguttag i vardagsrummet?", "opts": ["1 Fas", "2 Faser", "3 Faser"], "ans": "1 Fas", "exp": "Ett vanligt uttag (Schuko) får in 1 Fas (brun), 1 Nolla (blå) och 1 Jord (gul/grön). Spänningen är 230V."},
    {"q": "Vilken spänning mäter vi normalt mellan två huvudfaser (t.ex. L1 och L2) i ett svenskt elnät?", "opts": ["230 V", "400 V", "1000 V"], "ans": "400 V", "exp": "Spänningen mellan en fas och nolla är 230V (Fasspänning). Spänningen mellan två faser är 400V (Huvudspänning)."}
]

with st.expander("🎓 Isolerabs Lärlings-Quiz"):
    st.markdown("Testa dina kunskaper! Hur bra koll har du på säkerhet och material?")
    
    if st.session_state.quiz_q_num < len(quiz_data):
        q_info = quiz_data[st.session_state.quiz_q_num]
        st.markdown(f"**Fråga {st.session_state.quiz_q_num + 1} av {len(quiz_data)}**")
        st.write(q_info["q"])

        if not st.session_state.quiz_show_exp:
            selected = st.radio("Välj ditt svar:", q_info["opts"], key=f"radio_{st.session_state.quiz_q_num}")
            if st.button("Svara"):
                st.session_state.quiz_selected = selected
                st.session_state.quiz_show_exp = True
                if selected == q_info["ans"]:
                    st.session_state.quiz_score += 1
                st.rerun()
        else:
            st.radio("Ditt val:", q_info["opts"], index=q_info["opts"].index(st.session_state.quiz_selected), disabled=True)
            if st.session_state.quiz_selected == q_info["ans"]:
                st.success("✅ Rätt svar! Pierfekt!")
            else:
                st.error(f"❌ Fel. Rätt svar är: {q_info['ans']}")
            st.info(f"**💡 Förklaring:** {q_info['exp']}")

            if st.button("Nästa fråga"):
                st.session_state.quiz_show_exp = False
                st.session_state.quiz_q_num += 1
                st.rerun()
    else:
        st.balloons()
        st.success(f"🎉 Quizet är klart! Du fick {st.session_state.quiz_score} av {len(quiz_data)} rätt.")
        if st.button("Börja om"):
            st.session_state.quiz_q_num = 0
            st.session_state.quiz_score = 0
            st.session_state.quiz_show_exp = False
            st.rerun()

# --- 6. RIT- OCH BILDFUNKTION ---
def render_content(text):
    image_dir = os.path.join(current_dir, "bilder")
    
    if is_admin and not os.path.exists(image_dir):
        st.sidebar.error(f"Systemfel: Hittar inte mappen '{image_dir}'")
        
    parts = re.split(r'\[(?:VISA_BILD|BILD|SCHEMA):\s*([\s\S]+?)\]', text)
    for i, part in enumerate(parts):
        if i % 2 == 0:
            if part.strip():
                st.markdown(part.strip().replace("HIGHLIGHT:", "<span class='highlight'>").replace(":HIGHLIGHT", "</span>"), unsafe_allow_html=True)
        else:
            content = part.strip()
            
            if any(content.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif']):
                actual_file_path = None
                if os.path.exists(image_dir):
                    try:
                        all_files = os.listdir(image_dir)
                        for f in all_files:
                            if f.lower() == content.lower():
                                actual_file_path = os.path.join(image_dir, f)
                                break
                    except: pass

                if actual_file_path:
                    st.image(actual_file_path, use_container_width=True)
                else:
                    try:
                        existing_log = ""
                        if os.path.exists(img_log_path):
                            with open(img_log_path, "r", encoding="utf-8") as f: existing_log = f.read()
                        if content not in existing_log:
                            with open(img_log_path, "a", encoding="utf-8") as f: f.write(f"{content}\n")
                    except: pass
                    
                    if is_admin:
                        st.sidebar.warning(f"Sökte efter: {content} i {image_dir}")
            else:
                components.html(f"<pre class='mermaid'>{content}</pre><script type='module'>import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';mermaid.initialize({{startOnLoad:true,theme:'dark',securityLevel:'loose'}});</script>", height=400, scrolling=True)

# --- 7. AI-MOTOR OCH CHATT ---
import random

system_prompt = (
    "Du är Isolerabs el-mentor och materialexpert. Din uppgift är att svara med auktoritet, fakta och praktisk erfarenhet.\n\n"
    "REGLER FÖR BILDER:\n"
    "1. Du får ABSOLUT INTE hitta på egna filnamn för bilder. Använd ENDAST [BILD: filnamn.jpg] om exakt det filnamnet redan står angivet i texten/manualen du läser.\n"
    "2. Om du vill illustrera något, men ingen specifik bild finns nämnd, rita hellre ett Mermaid-schema med [SCHEMA: graph TD...] istället för att gissa fram en bild.\n\n"
    "REGLER FÖR MATERIAL & INKÖP:\n"
    "1. Om användaren ber om en INKÖPSLISTA, 'allt material' eller 'vad som ska beställas': Du SKA hämta och presentera SAMTLIGA artiklar som finns i 'Isolerabs Materialkatalog' (24_materialkatalog_ahlsell.md). Missa inga rader. Presentera dem i en snygg tabell med art.nr och fungerande länkar.\n"
    "2. VAR SJÄLVTÄNKANDE: När du presenterar ett material (t.ex. en specifik kabel eller klämma), använd din allmänna expertis som el-mentor för att förklara VARFÖR vi använder just detta material, tekniska fördelar, montage-tips eller vad man bör tänka på (t.ex. temperatur, böjradie eller tidsvinst). Var mer beskrivande än vad som bara står i katalogen.\n"
    "3. Om en fråga rör material som INTE finns i katalogen, föreslå vad som är branschstandard men nämn att det inte är Isolerabs listade standardartikel.\n\n"
    "ALLMÄNNA REGLER:\n"
    "1. Om du hittar svaret i manualerna, prioritera det.\n"
    "2. Om du svarar utifrån allmän kunskap (SEK 444), inled med: 'Jag hittar inte detta i Isolerabs manualer, men som din el-mentor rekommenderar jag följande:'.\n"
    "3. SCENANVISNINGAR: Följ instruktioner som börjar med '(Instruktion för chatboten: ...)' men skriv ALDRIG ut själva instruktionen till användaren.\n"
    "4. Svara alltid på svenska och var peppande.\n\n"
    "Expertkunskap (Manualer & Materialkatalog):\n{context}"
)
prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])

avatar_user = os.path.join(current_dir, "ikoner", "anvandare.png") if os.path.exists(os.path.join(current_dir, "ikoner", "anvandare.png")) else "👤"
avatar_bot = os.path.join(current_dir, "ikoner", "bot.png") if os.path.exists(os.path.join(current_dir, "ikoner", "bot.png")) else "🤖"

if "messages" not in st.session_state: st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar=(avatar_user if msg["role"]=="user" else avatar_bot)):
        render_content(msg["content"])

if query := st.chat_input("Ställ din fråga... (Tips: Använd mikrofonen 🎙️)"):
    if any(ord in query.lower() for ord in ["pierfekt", "tack", "löst det", "bra jobbat"]):
        st.balloons()
        
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user", avatar=avatar_user): st.write(query)
    
    with st.chat_message("assistant", avatar=avatar_bot):
        max_försök = 2
        försök = 0
        lyckades = False
        while försök < max_försök and not lyckades:
            try:
                # --- LISTA MED SLUMPMÄSSIGA STATUS-TEXTER (UTAN IKONER) ---
                status_texts = [
                    "*Gräver djupt i Isolerabs manualer...*",
                    "*Kopplar rätt trådar för att ge dig ett bra svar...*",
                    "*Laddar upp lite extra spänning inför svaret...*",
                    "*Bläddrar frenetiskt i Ahlsell-katalogen...*",
                    "*Tänker så det knakar (men oroa dig inte, säkringen håller)...*",
                    "*Hämtar verktygen från den digitala servicebilen...*",
                    "*Beräknar det mest pierfekta svaret...*"
                ]
                
                status_box = st.empty()
                status_box.markdown(random.choice(status_texts))
                
                # SÄNKT K-VÄRDE TILL 5 FÖR FELSÖKNING
                retriever = vectorstore.as_retriever(search_kwargs={"k": 15})
                chain = create_retrieval_chain(retriever, create_stuff_documents_chain(chat_model, prompt))
                
                safety_warning = "⚠️ **VIKTIGT:** *Jag är en AI-assistent och finns här för att guida dig så gott jag kan, men mina svar är inte till 100 % garanterade. Är du det minsta osäker MÅSTE du alltid kontakta din elansvarige innan du påbörjar något arbete på anläggningen!*\n\n"
                full_res = safety_warning
                
                message_placeholder = st.empty()
                
                for chunk in chain.stream({"input": query}):
                    if "answer" in chunk:
                        status_box.empty()
                        full_res += chunk["answer"]
                        message_placeholder.markdown(full_res, unsafe_allow_html=True)
                
                message_placeholder.empty()
                
                if "Jag hittar inte detta i Isolerabs manualer" in full_res:
                    with open(log_path, "a", encoding="utf-8") as f: f.write(f"- {query}\n")
                    if is_admin: st.toast("📌 Frågan loggad för inlärning!")
                
                render_content(full_res)
                st.session_state.messages.append({"role": "assistant", "content": full_res})
                lyckades = True
            
            except Exception as e:
                # --- DIAGNOSTIK-LÄGE ---
                if 'status_box' in locals(): status_box.empty()
                if 'message_placeholder' in locals(): message_placeholder.empty()
                
                st.error("❌ Ett fel uppstod i kommunikationen med Google:")
                st.code(str(e))
                break
