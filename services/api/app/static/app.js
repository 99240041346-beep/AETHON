const $=s=>document.querySelector(s);
const state={session:null,busy:false,sessions:[],token:localStorage.getItem("aethon_token")||"",controller:null,lastPrompt:""};
const $all=s=>Array.from(document.querySelectorAll(s));
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function auth(){return state.token?{"Authorization":"Bearer "+state.token}:{}}
async function api(path,opt={}){opt.headers={...(opt.headers||{}),...auth(),"Content-Type":"application/json"};const r=await fetch(path,opt);if(!r.ok)throw new Error((await r.text()).slice(0,500)||r.statusText);return r.json()}
function renderText(text){let x=esc(text);x=x.replace(/\`\`\`([\\s\\S]*?)\`\`\`/g,(_,c)=>"<pre><code>"+c+"</code></pre>");x=x.replace(/\*\*(.*?)\*\*/g,"<strong>$1</strong>").replace(/\`([^\`]+)\`/g,"<code>$1</code>");x=x.replace(/^[-*] (.*)$/gm,"• $1");return x.split(/
{2,}/).map(p=>"<p>"+p.replace(/
/g,"<br>")+"</p>").join("")}
function addMessage(role,text,events=[]){const box=$("#messages"),el=document.createElement("article");el.className="message "+role;el.innerHTML='<div class="avatar">'+(role==="user"?"YOU":"A")+'</div><div class="bubble"><div class="message-name">'+(role==="user"?"You":"AETHON")+'</div><div class="content">'+renderText(text)+'</div>'+events.map(e=>'<div class="event">• '+esc(e)+'</div>').join("")+"</div>";box.appendChild(el);box.scrollTop=box.scrollHeight;return el}
function setBusy(v){state.busy=v;$("#send").disabled=false;$("#send").textContent=v?"■":"↑";$("#send").title=v?"Stop generation":"Send";$("#typing").classList.toggle("on",v)}
function showWelcome(v){$("#welcome").style.display=v?"block":"none";$("#messages").style.display=v?"none":"block"}
async function loadSessions(query=""){try{const endpoint=query?"/v1/assistant/sessions/search?q="+encodeURIComponent(query)+"&limit=50":"/v1/assistant/sessions?limit=50";const d=await api(endpoint);state.sessions=d.sessions||d||[];$("#sessions").innerHTML=state.sessions.map(s=>'<div class="session '+(s.session_id===state.session?"active":"")+'" data-id="'+esc(s.session_id)+'"><span>◌</span><span class="session-title">'+esc(s.title||"New conversation")+'</span><button class="session-delete" data-delete="'+esc(s.session_id)+'">×</button></div>').join("")}catch{}}
async function openSession(id){state.session=id;showWelcome(false);$("#messages").innerHTML="";try{const d=await api("/v1/assistant/sessions/"+encodeURIComponent(id)+"/messages");const msgs=d.messages||d||[];msgs.forEach(m=>addMessage(m.role==="user"?"user":"assistant",m.content));const s=state.sessions.find(x=>x.session_id===id);$("#chatTitle").textContent=s?.title||"Conversation"}catch(e){addMessage("assistant","I could not load this conversation: "+e.message)}await loadSessions()}
function newChat(){state.session=null;$("#chatTitle").textContent="AETHON";$("#messages").innerHTML="";showWelcome(true);loadSessions();$("#input").focus()}
function messageTools(el,prompt){
 if(!el||el.dataset.tools)return; el.dataset.tools="1";
 const tools=document.createElement("div");tools.className="message-tools";
 const add=(label,fn)=>{const b=document.createElement("button");b.className="message-tool";b.textContent=label;b.onclick=fn;tools.appendChild(b)};
 add("Copy",()=>navigator.clipboard?.writeText(el.querySelector(".content")?.innerText||""));
 if(prompt)add("Edit",()=>{ $("#input").value=prompt;$("#input").focus();$("#input").dispatchEvent(new Event("input")); });
 if(prompt)add("Regenerate",()=>send(prompt,true));
 boxSafeAppend(el,tools);
}
function boxSafeAppend(el,node){el.querySelector(".bubble").appendChild(node)}
function exportConversation(){
 const rows=$all("#messages .message").map(m=>({role:m.classList.contains("user")?"You":"AETHON",text:m.querySelector(".content")?.innerText||""}));
 if(!rows.length)return;
 const body=rows.map(x=>"## "+x.role+"

"+x.text).join("

");
 const blob=new Blob([body],{type:"text/markdown"}),url=URL.createObjectURL(blob),a=document.createElement("a");
 a.href=url;a.download=(state.sessions.find(s=>s.session_id===state.session)?.title||"aethon-conversation")+".md";a.click();URL.revokeObjectURL(url);
}
function setAssistantText(el,text){const content=el?.querySelector(".content");if(content)content.innerHTML=renderText(text||"");}
async function send(text,regenerate=false){text=(text||$("#input").value).trim();if(!text||state.busy)return;state.lastPrompt=text;$("#input").value="";$("#input").style.height="auto";showWelcome(false);if(!regenerate)addMessage("user",text);setBusy(true);const assistant=addMessage("assistant","");const content=assistant.querySelector(".content");let events=[];try{state.controller=new AbortController();const r=await fetch("/v1/assistant/runtime/stream",{method:"POST",headers:{"Content-Type":"application/json",...auth()},body:JSON.stringify({text,session_id:state.session,execute_tools:true,require_approval:false}),signal:state.controller.signal});if(!r.ok)throw new Error((await r.text()).slice(0,500));const reader=r.body.getReader(),dec=new TextDecoder();let buf="";while(true){const {value,done}=await reader.read();if(done)break;buf+=dec.decode(value,{stream:true});const chunks=buf.split("

");buf=chunks.pop();for(const chunk of chunks){const dm=chunk.split("
").find(x=>x.startsWith("data: "));if(!dm)continue;let d;try{d=JSON.parse(dm.slice(6))}catch{continue}if(chunk.startsWith("event: progress")){const t=d.data?.message||d.data?.status||d.type;if(t&&!events.includes(t)){events.push(t);assistant.querySelector(".bubble").insertAdjacentHTML("beforeend",'<div class="event">• '+esc(t)+'</div>')}}else if(chunk.startsWith("event: completed")){if(d.session_id)state.session=d.session_id;content.innerHTML=renderText(d.response||d.error||"No response.");messageTools(assistant,text);if(d.requires_confirmation)assistant.querySelector(".bubble").insertAdjacentHTML("beforeend",'<div class="event">⚠ Approval required before this action can execute.</div>');if(d.action_authorized)assistant.querySelector(".bubble").insertAdjacentHTML("beforeend",'<div class="event">✓ Action authorized</div>');if(d.verified)assistant.querySelector(".bubble").insertAdjacentHTML("beforeend",'<div class="event">✓ Verified result</div>')}}}}await loadSessions();$("#chatTitle").textContent=state.session?"Conversation":"AETHON"}catch(e){if(e.name==="AbortError"){content.innerHTML="<p>Generation stopped.</p>";messageTools(assistant,text)}else{content.innerHTML="<p>Something went wrong: "+esc(e.message)+"</p>";messageTools(assistant,text)}}finally{state.controller=null;setBusy(false);$("#input").focus()}}
async function capabilities(){const d=await api("/v1/capabilities");$("#capList").innerHTML=(d.capabilities||[]).map(c=>'<div class="cap"><div><div class="cap-name">'+esc(c.name)+'</div><div class="cap-desc">'+esc(c.description)+'</div></div><span class="pill '+(c.available?"ok":"")+'">'+(c.available?"AVAILABLE":"NOT CONNECTED")+"</span></div>").join("");$("#capDialog").showModal()}
$("#newChat").onclick=newChat;$("#clearBtn").onclick=newChat;$("#send").onclick=()=>state.busy?state.controller?.abort():send();$("#capabilitiesBtn").onclick=capabilities;let searchTimer;$("#sessionSearch").addEventListener("input",e=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>loadSessions(e.target.value.trim()),180)});$("#renameBtn").onclick=async()=>{if(!state.session)return;const current=state.sessions.find(s=>s.session_id===state.session);const title=prompt("Conversation name",current?.title||"Conversation");if(title&&title.trim()){try{await api("/v1/assistant/sessions/"+encodeURIComponent(state.session),{method:"PATCH",body:JSON.stringify({title:title.trim()})});await loadSessions();$("#chatTitle").textContent=title.trim()}catch(e){alert(e.message)}}};$("#docsBtn").onclick=()=>window.open("/docs","_blank","noopener");$("#settingsBtn").onclick=()=>{ $("#token").value=state.token;$("#settingsDialog").showModal()};$("#saveSettings").onclick=()=>{state.token=$("#token").value.trim();state.token?localStorage.setItem("aethon_token",state.token):localStorage.removeItem("aethon_token");$("#settingsDialog").close();loadSessions()};$("#menuBtn").onclick=()=>$("#sidebar").classList.toggle("open");
const exportBtn=document.createElement("button");exportBtn.className="side-action";exportBtn.textContent="⇩ Export conversation";exportBtn.onclick=exportConversation;$(".sidebar-bottom").insertBefore(exportBtn,$("#docsBtn"));
document.querySelectorAll("[data-close]").forEach(b=>b.onclick=()=>b.closest("dialog").close());
document.querySelectorAll(".quick-grid button").forEach(b=>b.onclick=()=>send(b.dataset.prompt));
$("#input").addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send()}});
$("#input").addEventListener("input",e=>{e.target.style.height="auto";e.target.style.height=Math.min(e.target.scrollHeight,180)+"px"});
$("#sessions").addEventListener("click",e=>{const del=e.target.closest("[data-delete]");if(del){e.stopPropagation();api("/v1/assistant/sessions/"+encodeURIComponent(del.dataset.delete),{method:"DELETE"}).then(loadSessions);return}const s=e.target.closest(".session");if(s)openSession(s.dataset.id)});
loadSessions();
