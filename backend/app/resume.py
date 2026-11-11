import re
from io import BytesIO
from pypdf import PdfReader
from fastapi import HTTPException
SKILLS = ['Python','JavaScript','TypeScript','React','Next.js','FastAPI','Django','Flask','SQL','PostgreSQL','Docker','Git','Pandas','NumPy','Scikit-learn','PyTorch','TensorFlow','Machine learning','Deep learning','NLP','RAG','LLM','Regression','Classification','Decision trees','Neural networks','Statistics','Data analysis']

def parse_resume(content: bytes, filename: str):
    if len(content)>2*1024*1024: raise HTTPException(413,'Resume must be smaller than 2 MB.')
    try:
        if filename.lower().endswith('.pdf'):
            if not content.startswith(b'%PDF'): raise ValueError('Not a PDF')
            r=PdfReader(BytesIO(content))
            if r.is_encrypted or len(r.pages)>10: raise ValueError('Use an unlocked PDF of 10 pages or fewer')
            text='\n'.join(page.extract_text() or '' for page in r.pages)
        elif filename.lower().endswith('.txt'): text=content.decode('utf-8')
        else: raise HTTPException(415,'Please upload a PDF or UTF-8 text file.')
    except HTTPException: raise
    except Exception: raise HTTPException(422,'Could not read this resume. Use a text-based PDF or paste the text instead.')
    return {**profile_from_text(text), "resume_text":text}

def profile_from_text(text):
    text=text.strip()
    if len(text)<80 or len(text)>30000: raise HTTPException(422,'Resume text must contain 80 to 30,000 characters. Scanned PDFs need OCR first.')
    skills=[s for s in SKILLS if re.search(r'(?<!\w)'+re.escape(s)+r'(?!\w)',text,re.I)]
    years = [int(x) for x in re.findall(r'(\d+)\+?\s*years?',text,re.I)]
    level='Applied' if max(years,default=0)>=2 else 'Foundational'
    # Name/email/phone are unnecessary for screening. Never forward raw resume text.
    sentences=re.split(r'[\n.!?]',text)
    projects=[x.strip()[:180] for x in sentences if any(w in x.lower() for w in ['built','developed','project','implemented','trained'])][:3]
    return {'skills':skills[:16],'level':level,'project_signals':projects,'character_count':len(text),'extraction':'Rule-based skill matching; candidate can review before starting.'}
