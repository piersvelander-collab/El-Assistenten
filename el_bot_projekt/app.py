import streamlit as st
import os
import re
import base64
import time
import random
from PIL import Image
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

st.set_page_config(
    page_title="El-Assistenten", 
    page_icon=app_icon, 
    layout="centered",
    initial_sidebar_state="collapsed"
)

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
    # VIKTIGT: Vi använder nu Gemini 2.5 Pro som huvudmotor
    return ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0.0, max_retries=5, streaming=True)

vectorstore = load_knowledge_base()
chat_model = get_chat_model()

# --- 2. MOBILANPASSAD DESIGN OCH CSS ---
st.markdown("""
<style>
    /* Grundfärger Isolerab Blå */
    .stApp, [data-testid="stSidebar"] { background-color: #0d014d !important; }
    p, li, label, h1, h2, h3, h4, h5, h6, .stMarkdown, div[data-testid="stChatMessageContent"] { color: #ffffff !important; }
    
    /* Header-stil Pierfekt Grön */
    .pierfekta-header { 
        color: #82e300 !important; 
        font-weight: bold; 
        font-size: 1.8rem; 
        margin-bottom: 1rem; 
    }
    
    /* Mobilanpassning - Större knappar och bättre text */
    @media (max-width: 640px) {
        .pierfekta-header { font-size: 1.4rem; }
        .stButton > button { width: 100%; height: 3.5rem; font-size: 1.1rem !important; margin-bottom: 10px; }
        div[data-testid="stChatMessage"] { padding: 0.5rem !important; }
        .stMarkdown p { font-size: 1.05rem; }
    }

    .highlight { color: #82e300 !important; font-weight: bold; }
    
    /* Input-fält */
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        background-color: rgba(0, 0, 0, 0.4) !important; color: white !important; border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    /* Knappar */
    .stButton > button { 
        background-color: rgba(0, 0, 0, 0.4) !important; 
        color: #ffffff !important; 
        border: 1px solid #82e300 !important; 
        border-radius: 8px;
    }
    
    img { max-width: 100%; height: auto; border-radius: 10px; box-shadow: 0px 4px 10px rgba(0,0,0,0.3); }
</style>
""", unsafe_allow_html=True)

# --- 3. DÖRRVAKTEN & SIDOMENYN ---
with st.sidebar:
    st.markdown("### 🛠️ Verktyg")
    
    # Knapp för att rensa chatten
    if st.button("🧹 Rensa konversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    st.markdown("### 🔒 Personal-inloggning")
    admin_password = st.text_input("Lösenord:", type="password")
    is_admin = False
    
    if "ADMIN_PASSWORD" in st.secrets and admin_password == st.secrets["ADMIN_PASSWORD"]:
        is_admin = True
        st.success("✅ Inloggad som Admin")
        st.divider()
        
        # Sektion för saknade frågor
        log_lines = []
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                log_lines = f.readlines()
        unanswered_qs = [line.strip().replace("- ", "") for line in log_lines if
