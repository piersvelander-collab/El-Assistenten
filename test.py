import langchain
print("--- DIAGNOSTIK ---")
print("1. Langchain version:", langchain.__version__)
print("2. Langchain laddas från:", langchain.__file__)

try:
    from langchain.chains import create_retrieval_chain
    print("3. SUCCÉ: create_retrieval_chain hittades utan problem!")
except Exception as e:
    print("3. FEL VID IMPORT:", type(e).__name__, "-", e)