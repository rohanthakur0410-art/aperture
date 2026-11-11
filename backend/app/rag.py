import json, hashlib, re
from functools import lru_cache
from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models
from pypdf import PdfReader
from .config import DATA, EMBED_MODEL, COLLECTION, SOURCE_URL

@lru_cache
def embedder():
    return TextEmbedding(EMBED_MODEL, cache_dir=str(DATA / 'models'), threads=2)
@lru_cache
def store():
    return QdrantClient(path=str(DATA / 'vectors'))

def chunk_text(text, size=210, overlap=40):
    words=re.sub(r'\s+',' ',text).split()
    for start in range(0,len(words),size-overlap):
        piece=' '.join(words[start:start+size])
        if len(piece)>180: yield piece

def ingest(pdf_path, batch_limit=None):
    q=store()
    if ready(): return q.count(COLLECTION).count
    cache=DATA/'chunks.json'
    if cache.exists(): chunks=json.loads(cache.read_text())
    else:
        reader=PdfReader(pdf_path); chunks=[]
        for page_number,page in enumerate(reader.pages,1):
            if page_number<14: continue
            for text in chunk_text(page.extract_text() or ''):
                chunks.append({'text':text,'page':page_number,'source':'Machine Learning - Tom M. Mitchell','url':SOURCE_URL})
        cache.write_text(json.dumps(chunks))
    if not q.collection_exists(COLLECTION):
        q.create_collection(COLLECTION,vectors_config=models.VectorParams(size=384,distance=models.Distance.COSINE))
    progress=DATA/'ingestion-progress.json'
    start=json.loads(progress.read_text())['next'] if progress.exists() else 0
    limit=min(len(chunks), start+batch_limit) if batch_limit else len(chunks)
    for offset in range(start,limit,32):
        batch=chunks[offset:min(offset+32,limit)]
        vectors=list(embedder().embed([c['text'] for c in batch]))
        points=[]
        for c,v in zip(batch,vectors):
            uid=hashlib.md5((str(c['page'])+c['text']).encode()).hexdigest()
            points.append(models.PointStruct(id=uid,vector=v.tolist(),payload=c))
        q.upsert(COLLECTION,points)
        progress.write_text(json.dumps({'next':offset+len(batch),'total':len(chunks)}))
        print(f'Indexed {offset+len(batch)}/{len(chunks)}',flush=True)
    if limit==len(chunks): (DATA/'index-ready.json').write_text(json.dumps({'chunks':len(chunks),'embedding':EMBED_MODEL,'source':SOURCE_URL}))
    return q.count(COLLECTION).count

def ready():
    try:return (DATA/'index-ready.json').exists() and store().collection_exists(COLLECTION) and store().count(COLLECTION).count>0
    except Exception:return False

def retrieve(query):
    vector=next(embedder().query_embed(query)).tolist()
    hits=store().query_points(COLLECTION,query=vector,limit=8).points
    chosen=[];pages=set()
    for h in hits:
        payload=h.payload
        if payload['page'] in pages:continue
        chosen.append({**payload,'id':str(h.id),'similarity':round(h.score,4)})
        pages.add(payload['page'])
        if len(chosen)==3:break
    return chosen
