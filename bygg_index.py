import os
import time
import streamlit as st
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Hämta nyckeln i smyg från Streamlits kista
os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]

def bygg_lokalt_index():
    print("⚡ Startar byggandet av el-registret...")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    doc_dir = os.path.join(current_dir, "dokument")
    index_path = os.path.join(current_dir, "faiss_index")
    
    if not os.path.exists(doc_dir):
        print("❌ Hittade ingen mapp som heter 'dokument'. Skapa den och lägg in dina .md-filer.")
        return

    # Läs in och hacka upp dokumenten
    print("📖 Läser in handböcker...")
    loader = DirectoryLoader(doc_dir, glob="**/*.md", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'})
    docs = loader.load()
    splits = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=50).split_documents(docs)
    
    if not splits:
        print("❌ Hittade ingen text i dokumenten.")
        return

    # Anslut till Google
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    vectorstore = None
    
    # Skicka till Google med små pauser
    print(f"🚀 Skickar {len(splits)} textstycken till Google...")
    for i in range(len(splits)):
        if vectorstore is None:
            vectorstore = FAISS.from_documents([splits[i]], embeddings)
        else:
            vectorstore.add_documents([splits[i]])
            
        # Skriv ut framsteg
        if (i + 1) % 5 == 0:
            print(f"⏳ Bearbetat {i + 1} av {len(splits)} stycken...")
            
        time.sleep(1.0) # Viktig paus för gratis-API!

    # Spara registret lokalt
    vectorstore.save_local(index_path)
    print("✅ KLART! Mappen 'faiss_index' har nu skapats på din dator.")

if __name__ == "__main__":
    bygg_lokalt_index()