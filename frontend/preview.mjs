import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const artifacts=process.env.ARTIFACT_DIR||path.join(root,'review-artifacts');
fs.mkdirSync(artifacts,{recursive:true});
import {chromium} from '@playwright/test';
import {spawn} from 'node:child_process';
import fs from 'node:fs';
const server=spawn(process.env.PYTHON||'python',['-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000'],{cwd:path.join(root,'backend'),stdio:'pipe'});
let output='';server.stdout.on('data',x=>output+=x);server.stderr.on('data',x=>output+=x);
let browser;
try{
 for(let i=0;i<100;i++){try{const r=await fetch('http://127.0.0.1:8000/api/health');if(r.ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
 browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1100},deviceScaleFactor:1});
 await page.goto('http://127.0.0.1:8000');await page.getByRole('heading',{name:'Beyond the bullet points.'}).waitFor();await page.evaluate(()=>document.fonts.ready);
 await page.screenshot({path:path.join(artifacts,'aperture-desktop.png'),fullPage:true});
 await page.getByRole('button',{name:'Try a synthetic candidate'}).click();await page.getByText('Background read',{exact:true}).waitFor();
 await page.screenshot({path:path.join(artifacts,'aperture-prepared.png'),fullPage:true});
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(artifacts,'aperture-mobile.png'),fullPage:true});
 console.log('overflow',await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,viewport:window.innerWidth})));
 await page.setViewportSize({width:320,height:800});console.log('320 overflow',await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,viewport:window.innerWidth})));
 console.log('CAPTURED');
}finally{if(browser)await browser.close();server.kill('SIGTERM');console.log(output.slice(-2500));}
