// Live end-to-end demo recording for Aperture. Runs the PRODUCTION app with the
// approved environment (GEMINI_API_KEY from the parent shell). No fixtures.
// Records the real flow: synthetic resume -> consent -> live retrieval + Gemini
// generation x4 -> summary -> transcript -> export -> reload restore -> delete.
// A slim caption bar narrates components; the app itself is untouched.
import path from 'node:path';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {spawn} from 'node:child_process';
import {chromium} from '@playwright/test';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const artifacts=process.env.ARTIFACT_DIR||path.join(root,'live-artifacts');
fs.mkdirSync(artifacts,{recursive:true});
if(!process.env.GEMINI_API_KEY){console.error('GEMINI_API_KEY not set; aborting (no credential, no live run).');process.exit(2);}

const server=spawn(process.env.PYTHON||'python',['-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000'],{cwd:path.join(root,'backend'),stdio:'pipe',env:process.env});
let serverLog='';server.stderr.on('data',x=>serverLog+=x);server.stdout.on('data',x=>serverLog+=x);
let browser;
const answers=[
 'Concept learning means inferring a general definition from labelled examples, like searching a hypothesis space from most general to most specific. Generalization only works because of inductive bias: without preferring some hypotheses over others, a learner has no reason to pick one prediction for unseen examples. I would check that the hypothesis space can actually represent the target concept, otherwise even perfect training fits fail on new data.',
 'I would use information gain, the expected entropy reduction, to pick splits like ID3 does. To control overfitting I would compare pruned and unpruned trees on a validation set, not the test set. A smaller tree that performs almost as well usually generalizes better, and noisy or missing attributes can be handled with fractional counts or the most common branch value.',
 'Backpropagation applies the chain rule to move the output error backwards through the layers, so each weight gets a gradient and gradient descent updates it scaled by the learning rate. Too high a rate diverges, too low is slow. To keep the network honest I would watch validation loss for early stopping and use weight decay or dropout against overfitting.',
 'Bayes theorem combines a prior with the likelihood of the observed data to get a posterior, and a MAP hypothesis picks the most probable one. Naive Bayes assumes features are conditionally independent given the class, which is rarely true but works well in practice and needs little data. I would be careful when attributes are strongly correlated, because the assumption can distort the probabilities.'
];
try{
 for(let i=0;i<150;i++){try{const h=await (await fetch('http://127.0.0.1:8000/api/health')).json();if(h.ai_connected&&h.knowledge_ready)break;}catch{}await new Promise(r=>setTimeout(r,200));}
 browser=await chromium.launch({headless:true});
 const ctx=await browser.newContext({viewport:{width:1440,height:1100},recordVideo:{dir:path.join(artifacts,'videos'),size:{width:1440,height:1100}}});
 const page=await ctx.newPage();
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const cap=async(t)=>page.evaluate((t)=>{let b=document.getElementById('demo-cap');if(!b){b=document.createElement('div');b.id='demo-cap';b.style.cssText='position:fixed;top:0;left:0;right:0;z-index:10000;background:#3b2437;color:#f6efe7;padding:7px 14px;text-align:center;font:12px/1.3 Arial;letter-spacing:.04em';document.body.prepend(b);}b.textContent=t;},t);
 const pause=(ms=2800)=>page.waitForTimeout(ms);

 await page.goto('http://127.0.0.1:8000');
 await page.getByRole('heading',{name:'Beyond the bullet points.'}).waitFor();
 await page.evaluate(()=>document.fonts.ready);
 await cap('APERTURE · live end-to-end demo · resume-aware RAG interview over Tom Mitchell\'s Machine Learning');
 await pause(3500);

 await cap('1 · Resume text is parsed LOCALLY by a deterministic skill extractor - raw resume text never leaves the machine');
 await page.getByRole('button',{name:'Try a synthetic candidate'}).click();
 await page.getByText('Background read',{exact:true}).waitFor();await pause();
 await cap('2 · Consent: synthetic candidate data only · free-tier Gemini may review prompts · no real resumes');
 await page.locator('.consent input').check();
 await page.screenshot({path:path.join(artifacts,'live-setup.png'),fullPage:true});await pause();

 await cap('3 · Session created in SQLite, and the first question is already generated: retrieval + Gemini in one flow');
 await page.getByRole('button',{name:'Begin the conversation'}).click();
 await page.locator('.question-num',{hasText:'QUESTION 01'}).waitFor({timeout:120000});

 for(let i=0;i<4;i++){
  if(i>0){
   await cap(`4 · Q${i+1}: query built from role + skills + level + prior answer -> BGE embedding -> Qdrant cosine search over 1,121 page-aware chunks`);
   await page.getByRole('button',{name:'Next question',exact:true}).click();
   await page.locator('.question-num',{hasText:`QUESTION 0${i+1}`}).waitFor({timeout:120000});
  }
  await cap(`4 · Q${i+1}: Gemini generated a grounded question; every cited chunk ID is validated against the retrieved set`);
  await pause(3500);
  await page.getByRole('button',{name:'Read retrieved passages'}).click();await pause(2500);
  await page.screenshot({path:path.join(artifacts,`live-evidence-q${i+1}.png`),fullPage:true});
  await page.locator('.query-details summary').click();await pause(1800);
  await page.getByRole('button',{name:'Hide retrieved passages'}).click();
  await cap(`5 · Candidate answers; saving writes to SQLite BEFORE the next provider call, so a failure can never lose an answer`);
  await page.locator('#answer').fill(answers[i]);await pause();
  await page.getByRole('button',{name:'Save answer',exact:true}).click();
  await page.getByText('Answer saved',{exact:true}).waitFor();await pause();
 }
 await cap('6 · After 4 answers, Gemini writes an evidence-based learning summary - no scores, no hiring verdicts');
 await page.getByRole('button',{name:'See your takeaways'}).click();
 await page.getByRole('heading',{name:'More than a score.'}).waitFor({timeout:120000});await pause(3500);
 await page.screenshot({path:path.join(artifacts,'live-results.png'),fullPage:true});
 await page.locator('.observations').scrollIntoViewIfNeeded();await pause(2500);
 await page.evaluate(()=>window.scrollTo(0,0));
 await cap('7 · Full transcript with cited textbook pages · JSON export · session restores after reload');
 await page.getByRole('button',{name:'Full conversation'}).click();await pause(2500);
 await page.screenshot({path:path.join(artifacts,'live-transcript.png'),fullPage:true});
 const sid=await page.evaluate(()=>localStorage.getItem('aperture-session'));
 const session=await (await fetch('http://127.0.0.1:8000/api/sessions/'+sid)).json();
 fs.writeFileSync(path.join(artifacts,'live-session.json'),JSON.stringify(session,null,2));
 await page.reload();await page.getByRole('heading',{name:'More than a score.'}).waitFor();await pause(2500);
 console.log('RELOAD RESTORE PASSED; browser errors:',JSON.stringify(errors));
 await cap('8 · Session deleted on request - SQLite record removed');
 const video=page.video();await ctx.close();
 console.log('video',await video.path());
 await fetch('http://127.0.0.1:8000/api/sessions/'+sid,{method:'DELETE'});
}finally{if(browser)await browser.close();server.kill('SIGTERM');console.log(serverLog.slice(-1500));}
