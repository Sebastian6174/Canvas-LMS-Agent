from agent.src.tools.doc_parser import read_google_doc
from agent.config import config

if __name__ == "__main__":
    SAMPLE_DOC_ID = config.doc_id
    text = read_google_doc(SAMPLE_DOC_ID)
    if text:
        print("--- Document Content ---")
        print(text)
        print("------------------------")
