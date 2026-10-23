// Documentation-only renderer. Pass installed Mermaid/dist and Playwright package paths.
// Product manifests and lockfiles do not need to change.
import { readFile, writeFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { resolve, dirname, extname, sep } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here=dirname(fileURLToPath(import.meta.url));
const [mermaidArg,playwrightArg]=process.argv.slice(2);
if(!mermaidArg||!playwrightArg)throw new Error('Usage: node docs/diagrams/render.mjs <mermaid/dist> <playwright/index.mjs>');
const vendor=resolve(mermaidArg);
const {chromium}=await import(pathToFileURL(resolve(playwrightArg)).href);
const markdown=(await readFile(resolve(here,'../../README.md'),'utf8')).replaceAll('\r\n','\n');
const blocks=[];
let heading='';
for(const match of markdown.matchAll(/^(#{2,3}) (.+)$|^```mermaid\r?\n([\s\S]*?)^```/gm)){
  if(match[2])heading=match[2];
  else {
    const title=heading.replace(/^\d+(?:\.\d+)*\.?\s*/, '');
    const id=title.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
    if(blocks.some(b=>b.id===id))throw new Error('Duplicate diagram id: '+id);
    blocks.push({id,title,source:match[3].trim()});
  }
}
const server=createServer(async(req,res)=>{
  try{
    if(req.url==='/'){res.writeHead(200,{'Content-Type':'text/html'});res.end('<!doctype html><html><head><meta charset="utf-8"></head><body></body></html>');return;}
    const target=resolve(vendor,'.'+decodeURIComponent(req.url.split('?')[0]));
    if(!target.startsWith(vendor+sep)){res.writeHead(403);res.end();return;}
    const contents=await readFile(target);
    res.writeHead(200,{'Content-Type':['.mjs','.js'].includes(extname(target))?'text/javascript':'application/octet-stream'});res.end(contents);
  }catch{res.writeHead(404);res.end();}
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
let browser;
try{
  browser=await chromium.launch({headless:true,...(process.env.DIAGRAM_BROWSER_CHANNEL?{channel:process.env.DIAGRAM_BROWSER_CHANNEL}:{})});
  const page=await browser.newPage({viewport:{width:1600,height:1000}});
  await page.goto(`http://127.0.0.1:${server.address().port}/`);
  await page.evaluate(async()=>{
    window.diagramMermaid=(await import('/mermaid.esm.min.mjs')).default;
    window.diagramMermaid.initialize({startOnLoad:false,securityLevel:'strict',theme:'base',fontFamily:'Arial, sans-serif',fontSize:18,themeVariables:{primaryColor:'#e7efdf',primaryBorderColor:'#54744d',primaryTextColor:'#18231c',lineColor:'#47604a',secondaryColor:'#f0f4ed',tertiaryColor:'#f7f8f3',fontSize:'18px'},flowchart:{htmlLabels:false,useMaxWidth:false,nodeSpacing:30,rankSpacing:45},sequence:{useMaxWidth:false,actorFontSize:16,messageFontSize:16,noteFontSize:16,wrap:true},er:{useMaxWidth:false,fontSize:16}});
  });
  for(let i=0;i<blocks.length;i++){
    const block=blocks[i];
    block.svg=await page.evaluate(async({source,i})=>{await window.diagramMermaid.parse(source);const {svg}=await window.diagramMermaid.render('diagram'+i,source);return svg;},{source:block.source,i});
    const box=await page.evaluate(svg=>{document.body.innerHTML=svg;const el=document.querySelector('svg');const b=el.viewBox.baseVal;return {width:b.width,height:b.height};},block.svg);
    if(!box.width||!box.height)throw new Error('Empty diagram: '+block.title);
    console.log(`${i+1}. ${block.title}: ${Math.round(box.width)} x ${Math.round(box.height)}`);
  }
  const template=await readFile(resolve(here,'viewer.template.html'),'utf8');
  const json=JSON.stringify(blocks).replaceAll('<','\\u003c');
  const html=template.replace('@@DIAGRAMS@@',()=>json);
  await writeFile(resolve(here,'index.html'),html);
  console.log(`Generated ${blocks.length} diagrams; ${Buffer.byteLength(html)} bytes; no runtime dependency.`);
}finally{
  if(browser)await browser.close();
  await new Promise(r=>server.close(r));
}
