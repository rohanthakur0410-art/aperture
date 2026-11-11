from datetime import datetime, timezone
import json, secrets, asyncio
from fastapi import HTTPException
from . import db, rag, llm
from .config import MAX_QUESTIONS
LOCKS={}
TOPICS={'AI / ML Engineer':['concept learning generalization inductive bias','decision trees information gain overfitting','neural networks backpropagation learning rate','Bayesian learning classification evaluation'], 'Data Science / Applied ML':['training test split cross validation evaluation','regression hypothesis space inductive bias','Bayesian learning probability estimation','decision trees noise missing attributes']}

def load(sid):
    s=db.get(sid)
    if not s: raise HTTPException(404,'Session not found or removed. Start a new interview.')
    return s

def public(s):
    return {**s,'questions':[{k:v for k,v in q.items() if k!='expected_points'} for q in s['questions']], 'total_questions':MAX_QUESTIONS}

def create(role,profile):
    sid=secrets.token_urlsafe(24)
    with db.connection() as c:
        c.execute('INSERT INTO sessions(id,created_at,role,profile) VALUES(?,?,?,?)',(sid,datetime.now(timezone.utc).isoformat(),role,json.dumps(profile)))
    return load(sid)

async def next_question(sid):
    lock=LOCKS.setdefault(sid,asyncio.Lock())
    async with lock:
        s=load(sid)
        if s['questions'] and s['questions'][-1].get('answer') is None: return public(s)
        if len(s['questions'])>=MAX_QUESTIONS: raise HTTPException(409,'All questions are answered. Open your summary.')
        if not rag.ready():raise HTTPException(503,'Knowledge base is not indexed. Run the ingestion command first.')
        idx=len(s['questions']);profile=s['profile']
        topic=TOPICS[s['role']][idx]
        query=f"{topic}. Candidate skills: {', '.join(profile['skills'])}. {profile['level']} level. "
        if idx:query+='Previous answer: '+s['questions'][-1]['answer'][:600]
        contexts=await asyncio.to_thread(rag.retrieve,query)
        payload={'task':'Generate ONE original interview question, not a generic or fixed template. Use the source context, resume skills and prior answers. Keep it under 100 words. Use conceptual or applied questions and avoid asking personal background questions. Cite at least one supplied source ID. Expected points are private evaluation notes.','role':s['role'],'candidate':{'skills':profile['skills'],'level':profile['level']},'focus':topic,'previous':[{'question':q['question'],'answer':q['answer']} for q in s['questions']], 'retrieval_query':query,'sources':contexts}
        out=await llm.generate(payload,llm.QUESTION_SCHEMA)
        if not all(k in out for k in ('question','topic','rationale','source_ids','expected_points')):raise HTTPException(502,'Question was incomplete. Retry this step.')
        ids={c['id'] for c in contexts}
        if not out['source_ids'] or any(i not in ids for i in out['source_ids']):raise HTTPException(502,'Question citations did not validate. Retry this step.')
        if not 25<=len(out['question'])<=1200:raise HTTPException(502,'Question length did not validate. Retry this step.')
        out.update({'number':idx+1,'contexts':contexts,'query':query,'answer':None,'generated_at':datetime.now(timezone.utc).isoformat()})
        s['questions'].append(out);db.save(s)
        return public(s)

async def answer(sid, number, text):
    lock=LOCKS.setdefault(sid,asyncio.Lock())
    async with lock:
        s=load(sid)
        if not s['questions'] or number!=len(s['questions']):raise HTTPException(409,'This question changed. Refresh the session.')
        q=s['questions'][-1]
        if q['answer'] is not None:
            if q['answer']==text:return public(s)
            raise HTTPException(409,'This answer is already saved.')
        q['answer']=text;q['answered_at']=datetime.now(timezone.utc).isoformat();db.save(s)
        return public(s)

async def finish(sid):
    lock=LOCKS.setdefault(sid,asyncio.Lock())
    async with lock:
        s=load(sid)
        if s['summary']:return public(s)
        if len(s['questions'])!=MAX_QUESTIONS or any(q['answer'] is None for q in s['questions']):raise HTTPException(409,'Answer all four questions before generating your summary.')
        out=await llm.generate({'task':'Write a cautious evidence-based learning summary, not a hiring recommendation or score. Assess answers against expected points and sources. Quote brief exact evidence from each answer. Do not infer personality, protected traits or unsupported ability. Empty or weak answers must be noted.','role':s['role'],'questions':s['questions']},llm.SUMMARY_SCHEMA)
        if not all(k in out for k in ('overview','strengths','practice_next','observations')):raise HTTPException(502,'Summary did not validate. Retry this step.')
        for o in out['observations']:
            n=o.get('question_number',0)
            if not 1<=n<=len(s['questions']):raise HTTPException(502,'Summary references did not validate. Retry.')
            if o['evidence'] not in s['questions'][n-1]['answer']:o['evidence']='No exact supporting quote returned.'
        s['summary']=out;s['status']='complete';db.save(s)
        return public(s)
