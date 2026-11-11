import asyncio,json
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from app import db,main,service,llm,rag,resume

TEXT='Synthetic candidate. Python SQL Pandas Scikit-learn FastAPI. Built a classification project using logistic regression and decision trees and evaluated precision and recall.'
CTX=[{'id':'book-1','text':'Use independent test examples to estimate generalization error.','page':81,'source':'Machine Learning - Tom M. Mitchell','url':'https://www.cs.cmu.edu/~tom/files/MachineLearningTomMitchell.pdf','similarity':0.8}]
@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(db,'DATA',tmp_path)
    monkeypatch.setattr(main,'KEY','test-only-not-a-real-key')
    monkeypatch.setattr(rag,'ready',lambda:True)
    monkeypatch.setattr(rag,'retrieve',lambda query:CTX)
    async def fixture_generate(payload,schema):
        if schema==llm.QUESTION_SCHEMA:
            n=len(payload['previous'])+1
            return {'question':f'Fixture question {n}: explain how you would check generalization error for your classifier.','topic':'Model evaluation','rationale':'Fixture-only question for an isolated backend test.','source_ids':['book-1'],'expected_points':['Unseen test data']}
        return {'overview':'Fixture summary','strengths':['Mentions test data'],'practice_next':['Study evaluation'],'observations':[{'question_number':1,'assessment':'Test evidence','evidence':'unseen test data'}]}
    monkeypatch.setattr(llm,'generate',fixture_generate)
    with TestClient(main.app) as c:yield c

def new(c):
    r=c.post('/api/sessions',json={'role':'AI / ML Engineer','text':TEXT,'consent':True});assert r.status_code==200,r.text;return r.json()['id']

def test_profile_rejects_short_and_tracks_skills(client):
    assert client.post('/api/resume/parse',json={'text':'short'}).status_code==422
    p=client.post('/api/resume/parse',json={'text':TEXT}).json()
    assert 'Python' in p['skills'] and 'SQL' in p['skills'] and p['level']=='Foundational'

def test_file_validation(client):
    assert client.post('/api/resume/upload',files={'file':('x.exe',b'x'*200)}).status_code==415
    assert client.post('/api/resume/upload',files={'file':('x.pdf',b'not pdf'*30)}).status_code==422
    assert client.post('/api/resume/upload',files={'file':('x.txt',b'x'*(2*1024*1024+1))}).status_code==413
    p=client.post('/api/resume/upload',files={'file':('x.txt',TEXT.encode())}).json();assert p['resume_text']==TEXT

def test_role_and_consent(client):
    assert client.post('/api/sessions',json={'role':'AI / ML Engineer','text':TEXT}).status_code==422
    assert client.post('/api/sessions',json={'role':'Unsupported','text':TEXT,'consent':True}).status_code==422

def test_no_fake_ai_when_disconnected(client,monkeypatch):
    monkeypatch.setattr(main,'KEY','')
    r=client.post('/api/sessions',json={'role':'AI / ML Engineer','text':TEXT,'consent':True})
    assert r.status_code==503 and 'not connected' in r.json()['detail']

def test_lifecycle_persistence_and_export(client):
    sid=new(client)
    assert client.post(f'/api/sessions/{sid}/finish').status_code==409
    for n in range(1,5):
        s=client.post(f'/api/sessions/{sid}/next').json()
        assert len(s['questions'])==n and 'expected_points' not in s['questions'][-1]
        same=client.post(f'/api/sessions/{sid}/next').json();assert len(same['questions'])==n
        assert client.post(f'/api/sessions/{sid}/answers',json={'number':n,'answer':'Use unseen test data for honest evaluation.'}).status_code==200
    s=client.post(f'/api/sessions/{sid}/finish').json()
    assert s['status']=='complete' and s['summary']['observations'][0]['evidence']=='unseen test data'
    assert client.get(f'/api/sessions/{sid}').json()['summary']==s['summary']
    assert client.get(f'/api/sessions/{sid}/export').status_code==200
    assert client.post(f'/api/sessions/{sid}/next').status_code==409
    assert client.delete(f'/api/sessions/{sid}').json()['deleted']
    assert client.get(f'/api/sessions/{sid}').status_code==404

def test_answer_validation_idempotency(client):
    sid=new(client);client.post(f'/api/sessions/{sid}/next')
    assert client.post(f'/api/sessions/{sid}/answers',json={'number':1,'answer':'short'}).status_code==422
    assert client.post(f'/api/sessions/{sid}/answers',json={'number':2,'answer':'Wrong question number answer is rejected.'}).status_code==409
    a={'number':1,'answer':'A long enough answer stored only once.'}
    assert client.post(f'/api/sessions/{sid}/answers',json=a).status_code==200
    assert client.post(f'/api/sessions/{sid}/answers',json=a).status_code==200
    assert client.post(f'/api/sessions/{sid}/answers',json={'number':1,'answer':'Trying to overwrite an existing saved answer.'}).status_code==409

def test_provider_failure_keeps_session(client,monkeypatch):
    sid=new(client)
    async def fail(*args):raise HTTPException(429,'Free quota exhausted')
    monkeypatch.setattr(llm,'generate',fail)
    assert client.post(f'/api/sessions/{sid}/next').status_code==429
    assert client.get(f'/api/sessions/{sid}').json()['questions']==[]

def test_bad_citation_rejected(client,monkeypatch):
    sid=new(client)
    async def bad(*args):return {'question':'What would you do with your classifier?','topic':'X','rationale':'X','source_ids':['invented'],'expected_points':[]}
    monkeypatch.setattr(llm,'generate',bad)
    assert client.post(f'/api/sessions/{sid}/next').status_code==502
    assert client.get(f'/api/sessions/{sid}').json()['questions']==[]

def test_raw_resume_not_forwarded(client,monkeypatch):
    sid=new(client)
    async def capture(payload,schema):
        assert TEXT not in json.dumps(payload)
        assert 'project_signals' not in payload['candidate']
        return {'question':'How would you use unseen examples to test your classifier?','topic':'Evaluation','rationale':'Resume skills match','source_ids':['book-1'],'expected_points':['Test set']}
    monkeypatch.setattr(llm,'generate',capture)
    assert client.post(f'/api/sessions/{sid}/next').status_code==200

def test_chunk_overlap_preserves_context():
    text=' '.join('word'+str(i) for i in range(500))
    c=list(rag.chunk_text(text));assert len(c)==3
    assert c[0].split()[-40:]==c[1].split()[:40]

def test_knowledge_unready_is_honest(client,monkeypatch):
    monkeypatch.setattr(rag,'ready',lambda:False)
    assert client.post('/api/sessions',json={'role':'AI / ML Engineer','text':TEXT,'consent':True}).status_code==503
