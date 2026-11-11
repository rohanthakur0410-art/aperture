import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from . import db, resume, service, rag
from .config import KEY, MODEL, DATA

@asynccontextmanager
async def lifespan(app):
    db.init()
    yield
app=FastAPI(title='Aperture Interview API',version='1.0.0',lifespan=lifespan)
class ProfileRequest(BaseModel):
    text:str=Field(min_length=80,max_length=30000)
class SessionRequest(BaseModel):
    role:str
    text:str=Field(min_length=80,max_length=30000)
    consent:bool=False
class AnswerRequest(BaseModel):
    number:int=Field(ge=1,le=4)
    answer:str=Field(min_length=20,max_length=6000)
    @field_validator('answer')
    @classmethod
    def meaningful(cls,value):
        if len(value.strip())<20:raise ValueError('Write at least 20 non-whitespace characters.')
        return value.strip()

@app.get('/api/health')
def health():return {'status':'ok','ai_connected':bool(KEY),'model':MODEL if KEY else None,'knowledge_ready':rag.ready(),'source':'Machine Learning - Tom M. Mitchell','scope':'Private prototype. No hiring decisions. Synthetic candidate data only.'}
@app.post('/api/resume/upload')
async def upload(file:UploadFile=File(...)):
    try:
        content=await file.read(2*1024*1024+1)
    finally:
        await file.close()
    return await asyncio.to_thread(resume.parse_resume,content,file.filename or '')
@app.post('/api/resume/parse')
def parse(r:ProfileRequest):return resume.profile_from_text(r.text)
@app.post('/api/sessions')
def create(r:SessionRequest):
    if r.role not in service.TOPICS:raise HTTPException(422,'Choose one of the two supported roles.')
    if not r.consent:raise HTTPException(422,'Confirm synthetic-data use and provider disclosure before starting.')
    if not KEY:raise HTTPException(503,'Live AI is not connected yet. Resume preparation is available.')
    if not rag.ready():raise HTTPException(503,'Knowledge base is not indexed yet.')
    return service.public(service.create(r.role,resume.profile_from_text(r.text)))
@app.get('/api/sessions/{sid}')
def read(sid:str):return service.public(service.load(sid))
@app.post('/api/sessions/{sid}/next')
async def next_question(sid:str):return await service.next_question(sid)
@app.post('/api/sessions/{sid}/answers')
async def answer(sid:str,r:AnswerRequest):return await service.answer(sid,r.number,r.answer.strip())
@app.post('/api/sessions/{sid}/finish')
async def finish(sid:str):return await service.finish(sid)
@app.delete('/api/sessions/{sid}')
def remove(sid:str):
    service.load(sid)
    with db.connection() as c:c.execute('DELETE FROM sessions WHERE id=?',(sid,))
    return {'deleted':True}
@app.get('/api/sessions/{sid}/export')
def export(sid:str):return service.public(service.load(sid))

FRONTEND=Path(__file__).resolve().parents[2]/'frontend'/'dist'
if FRONTEND.exists():
    app.mount('/assets',StaticFiles(directory=FRONTEND/'assets'),name='assets')
    app.mount('/fonts',StaticFiles(directory=FRONTEND/'fonts'),name='fonts')
    @app.get('/{path:path}')
    def index(path:str):
        if path.startswith('api/'):raise HTTPException(404,'API route not found')
        return FileResponse(FRONTEND/'index.html')
