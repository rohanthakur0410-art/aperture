import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const artifacts=process.env.ARTIFACT_DIR||path.join(root,'review-artifacts');
fs.mkdirSync(artifacts,{recursive:true});
import {chromium} from '@playwright/test';
import {spawn} from 'node:child_process';
import fs from 'node:fs';
const server=spawn(process.env.PYTHON||'python',['-m','uvicorn','tests.ui_fixture:app','--host','127.0.0.1','--port','8000'],{cwd:path.join(root,'backend'),stdio:'pipe'});
let output='';server.stderr.on('data',x=>output+=x);let browser;
try{
 for(let i=0;i<100;i++){try{if((await fetch('http://127.0.0.1:8000/api/health')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
 browser=await chromium.launch({headless:true});const ctx=await browser.newContext({viewport:{width:1440,height:1100},recordVideo:{dir:path.join(artifacts,'videos'),size:{width:1440,height:1100}}});const page=await ctx.newPage();
 await page.goto('http://127.0.0.1:8000');await page.getByRole('heading',{name:'Beyond the bullet points.'}).waitFor();await page.evaluate(()=>document.fonts.ready);
 await page.evaluate(()=>{const b=document.createElement('div');b.textContent='DESIGN REVIEW · Scripted AI responses for UI testing. Real textbook retrieval. Not the final live demo.';b.style.cssText='position:sticky;top:0;z-index:10000;background:#f8d6b9;color:#58371e;padding:9px;text-align:center;font:11px Arial;border-bottom:1px solid #ddb18c';document.body.prepend(b);document.querySelector('.top-note').textContent='Design-test fixture';});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.getByRole('button',{name:'Try a synthetic candidate'}).click();await page.getByText('Background read',{exact:true}).waitFor();await page.locator('.consent input').check();await page.screenshot({path:path.join(artifacts,'review-setup.png'),fullPage:true});
 await page.getByRole('button',{name:'Begin the conversation'}).click();await page.getByRole('heading',{name:questionsFirst()}).waitFor();
 await page.screenshot({path:path.join(artifacts,'review-interview.png'),fullPage:true});await page.getByRole('button',{name:'Read retrieved passages'}).click();await page.screenshot({path:path.join(artifacts,'review-evidence.png'),fullPage:true});
 for(const width of [390,320]){await page.setViewportSize({width,height:844});await page.screenshot({path:path.join(artifacts,`review-interview-mobile-${width}.png`),fullPage:true});console.log('interview overflow',width,await page.evaluate(()=>document.documentElement.scrollWidth));}
 await page.setViewportSize({width:1440,height:1100});
 const answers=[
 'I would compare training and validation performance. A large gap would suggest overfitting. I would keep an untouched test set, use stratified splits and check for leakage. I would then try regularization and compare precision and recall on validation data.',
 'I would tune pruning with cross-validation. I would compare the validation error across tree depths, select a simpler tree if its performance is similar, and only once use the final test set to estimate generalization.',
 'I would use stratified cross-validation. Each fold would serve as a validation set while the other folds train the model. I would fit preprocessing inside each training fold and compare average metrics and their variation.',
 'I would ask for performance on unseen data. Training accuracy alone can hide overfitting and class imbalance. I would check validation and final test metrics, compare with a simple baseline, inspect recall for the minority class, and ask about monitoring.'
 ];
 for(let i=0;i<4;i++){
  await page.locator('#answer').fill(answers[i]);await page.getByRole('button',{name:'Save answer',exact:true}).click();await page.getByText('Answer saved',{exact:true}).waitFor();
  if(i<3){await page.getByRole('button',{name:'Next question',exact:true}).click();await page.locator('#answer').waitFor();}
 }
 await page.getByRole('button',{name:'See your takeaways'}).click();await page.getByRole('heading',{name:'More than a score.'}).waitFor();await page.screenshot({path:path.join(artifacts,'review-results.png'),fullPage:true});
 for(const width of [390,320]){await page.setViewportSize({width,height:844});await page.screenshot({path:path.join(artifacts,`review-results-mobile-${width}.png`),fullPage:true});console.log('results overflow',width,await page.evaluate(()=>document.documentElement.scrollWidth));}
 await page.setViewportSize({width:1440,height:1100});await page.getByRole('button',{name:'Full conversation'}).click();await page.screenshot({path:path.join(artifacts,'review-transcript.png'),fullPage:true});
 const sid=await page.evaluate(()=>localStorage.getItem('aperture-session'));const session=await (await fetch('http://127.0.0.1:8000/api/sessions/'+sid)).json();fs.writeFileSync(path.join(artifacts,'ui-test-session.json'),JSON.stringify(session,null,2));
 await page.reload();await page.getByRole('heading',{name:'More than a score.'}).waitFor();console.log('RESTORE PASSED; browser errors:',JSON.stringify(errors));
 const video=page.video();await ctx.close();console.log('video',await video.path());
 await fetch('http://127.0.0.1:8000/api/sessions/'+sid,{method:'DELETE'});
}finally{if(browser)await browser.close();server.kill('SIGTERM');console.log(output.slice(-2500));}
function questionsFirst(){return 'Your resume mentions a customer-churn classifier. Suppose it performs well on training data but poorly on new customers. How would you tell whether the problem is overfitting, and how would you redesign your evaluation?';}
