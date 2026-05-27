import docx
import os

def extract_languages(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
        
    doc = docx.Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    
    text = "\n".join(full_text)
    
    print("--- RAW TEXT START ---")
    print(text)
    print("--- RAW TEXT END ---")
    
    languages = []
    if "English" in text: languages.append("English")
    if "Hindi" in text: languages.append("Hindi")
    if "German" in text: languages.append("German")
    if "Swiss" in text: languages.append("Swiss German")
    
    print(f"Found languages: {languages}")

extract_languages(r"uploads\1\resume\db55808a-3265-447d-a6e0-a8a0d9fbe5a3.docx")
