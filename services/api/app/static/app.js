(()=>{"use strict";
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const state={session:null,busy:false,token:localStorage.getItem("aethon_token")||"",attachments:[],voiceReplies:false,recognition:null,wakeRecognition:null,wakeEnabled:false,voiceLanguage:navigator.language||"en-IN"};
const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const api=async(path,opt={})=>{const o={...opt,headers:{...(opt.headers||{}),...(state.token?{Authorization:"Bearer "+state.token}:{})}};if(o.body&&!(o.body instanceof FormData))o.headers["Content-Type"]="application/json";const r=await fetch(path,o);if(!r.ok)throw Error((await r.text()).slice(0,600)||r.statusText);return (r.headers.get("content-type")||"").includes("json")?r.json():r.text()};
const text=v=>esc(v).replace(/\*\*(.*?)\*\*/g,"<strong>$1</strong>").replace(/\`([^\`]+)\`/g,"<code>$1</code>").split("\n").map(x=>"<div>"+x+"</div>").join("");
function speakResponse(value){if(!("speechSynthesis"in window))return;speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(String(value||""));u.lang=detectSpeechLanguage(String(value||""))||state.voiceLanguage||"en-IN";speechSynthesis.speak(u)}
function detectSpeechLanguage(s){if(/[\u0C00-\u0C7F]/.test(s))return "te-IN";if(/[\u0900-\u097F]/.test(s))return "hi-IN";if(/[\u0B80-\u0BFF]/.test(s))return "ta-IN";if(/[\u0C80-\u0CFF]/.test(s))return "kn-IN";if(/[\u0D00-\u0D7F]/.test(s))return "ml-IN";if(/[\u0980-\u09FF]/.test(s))return "bn-IN";if(/[\u0A00-\u0A7F]/.test(s))return "pa-IN";if(/[\u0A80-\u0AFF]/.test(s))return "gu-IN";if(/[\u0600-\u06FF]/.test(s))return "ur-PK";if(/[\u4E00-\u9FFF]/.test(s))return "zh-CN";if(/[\u3040-\u30FF]/.test(s))return "ja-JP";if(/[\uAC00-\uD7AF]/.test(s))return "ko-KR";if(/[\u0400-\u04FF]/.test(s))return "ru-RU";return null}
function toast(msg){let x=document.createElement("div");x.className="toast";x.textContent=msg;document.body.appendChild(x);setTimeout(()=>x.remove(),3000)}
function setView(name){$$(".view").forEach(x=>x.classList.toggle("active",x.id==="view-"+name));$$(".navitem").forEach(x=>x.classList.toggle("active",x.dataset.view===name));const titles={chat:"Assistant",agents:"Autonomous Agents",factory:"AI Factory",devices:"Device Control",projects:"Projects",research:"Research"};$("#viewTitle").textContent=titles[name]||"Assistant";if(name==="agents")loadAgents();if(name==="factory")loadFactory();if(name==="devices")loadDevices();if(name==="projects")loadProjects()}
function addMessage(role,content){$("#welcome").style.display="none";const el=document.createElement("article");el.className="message "+role;el.innerHTML='<div class="avatar">'+(role==="user"?"YOU":"A")+'</div><div class="bubble"><small>'+(role==="user"?"You":"Assistant")+'</small><div class="content">'+text(content)+'</div></div>';$("#messages").appendChild(el);$("#messages").scrollTop=$("#messages").scrollHeight;return el}
function renderAttachments(){$("#attachmentList").innerHTML=state.attachments.map((a,i)=>'<span>'+esc(a.filename)+' <button data-rm="'+i+'">×</button></span>').join("")}
async function uploadFiles(files){for(const f of [...files].slice(0,5-state.attachments.length)){const fd=new FormData();fd.append("file",f);try{const r=await api("/v1/assistant/runtime/attachments",{method:"POST",body:fd});state.attachments.push(r)}catch(e){toast("Attachment failed: "+e.message)}}renderAttachments()}
async function send(value){
  const q=(value||$("#input").value).trim();
  if(!q||state.busy)return;
  $("#input").value="";
  const attachmentIds=state.attachments.map(x=>x.attachment_id);
  state.attachments=[]; renderAttachments();
  addMessage("user",q);
  state.busy=true; $("#typing").classList.add("on");
  const el=addMessage("assistant","Thinking…");
  const content=el.querySelector(".content");
  const setProgress=s=>{ if(s) content.innerHTML=text(s); };
  const finish=result=>{
    state.session=result.session_id||state.session;
    const answer=String(result.response||"");
    content.innerHTML=text(answer||"I’m ready. What would you like me to do?");
    if(result.visualization){
      const pre=document.createElement("pre");
      pre.textContent=JSON.stringify(result.visualization,null,2);
      el.querySelector(".bubble").appendChild(pre);
    }
    if(result.requires_confirmation)toast("Confirmation required before this action.");
    if(state.voiceReplies&&answer&&"speechSynthesis"in window)speakResponse(answer);
    $("#messages").scrollTop=$("#messages").scrollHeight;
    loadSessions();
  };
  const requestBody={text:q,session_id:state.session,execute_tools:true,require_approval:false,attachment_ids:attachmentIds};
  try{
    let completed=null;
    try{
      const response=await fetch("/v1/assistant/runtime/stream",{
        method:"POST",
        headers:{...(state.token?{Authorization:"Bearer "+state.token}:{}),"Content-Type":"application/json","Accept":"text/event-stream"},
        body:JSON.stringify(requestBody)
      });
      if(!response.ok)throw Error("stream "+response.status);
      if(!response.body)throw Error("stream unavailable");
      const reader=response.body.getReader(), decoder=new TextDecoder();
      let buffer="";
      while(true){
        const part=await reader.read();
        if(part.done)break;
        buffer+=decoder.decode(part.value,{stream:true});
        const frames=buffer.split("\\n\\n"); buffer=frames.pop()||"";
        for(const frame of frames){
          const event=(frame.match(/^event:\\s*(.+)$/m)||[])[1]||"message";
          const data=(frame.match(/^data:\\s*(.+)$/m)||[])[1];
          if(!data)continue;
          let payload; try{payload=JSON.parse(data)}catch{continue}
          if(event==="progress"){
            const labels={"context.loaded":"Reading context…","intent.classified":"Understanding your request…","ai.provider.completed":"Generating response…","ai.provider.fallback":"Selecting another AI path…","response.ready":"Finalizing response…","creation.completed":"Finishing your creation…"};
            if(labels[payload.type])setProgress(labels[payload.type]);
          }else if(event==="completed")completed=payload;
          else if(event==="error")throw Error(payload.error||"stream failed");
        }
      }
    }catch(streamError){
      setProgress("Preparing your response…");
    }
    if(!completed){
      const response=await fetch("/v1/assistant/runtime/respond",{
        method:"POST",
        headers:{...(state.token?{Authorization:"Bearer "+state.token}:{}),"Content-Type":"application/json"},
        body:JSON.stringify(requestBody)
      });
      const raw=await response.text();
      let payload; try{payload=JSON.parse(raw)}catch{throw Error(raw||"assistant request failed")}
      if(!response.ok)throw Error(payload.detail||payload.error||"assistant request failed");
      completed=payload;
    }
    finish(completed);
  }catch(e){
    content.innerHTML=text("I couldn’t complete that request. "+(e.message||"Please try again."));
  }finally{
    state.busy=false; $("#typing").classList.remove("on");
  }
}
async function loadSessions(){try{const r=await api("/v1/assistant/sessions?limit=30");const xs=r.sessions||r||[];$("#sessions").innerHTML=xs.map(s=>'<button class="session" data-id="'+esc(s.session_id)+'">◌ <span>'+esc(s.title||"Conversation")+'</span></button>').join("")}catch{}}
async function loadAgents(){try{const r=await api("/v1/agents");$("#agentList").innerHTML=(r.agents||[]).map(a=>'<article class="card"><div><b>'+esc(a.name||a.id||"Agent")+'</b><p>'+esc(a.description||"Specialist ASTRA agent")+'</p></div><span class="badge">READY</span></article>').join("")||'<div class="empty">No agents available.</div>'}catch(e){$("#agentList").innerHTML='<div class="empty">'+esc(e.message)+'</div>'}}
async function loadFactory(){try{const r=await api("/v1/ai-factory");const xs=r.agents||[];$("#factoryList").innerHTML=xs.map(a=>factoryCard(a)).join("")||'<div class="empty">Create your first AI agent above.</div>'}catch(e){$("#factoryList").innerHTML='<div class="empty">'+esc(e.message)+'</div>'}}
function factoryCard(a){const actions={specified:["generate"],generated:["sandbox"],sandboxed:["evaluate"],evaluated:["approve"],approved:["deploy"],deployed:["pause"],paused:[]}[a.stage]||[];return '<article class="card factoryCard"><div class="cardtop"><div><b>'+esc(a.spec.name)+'</b><p>'+esc(a.spec.goal)+'</p></div><span class="stage '+esc(a.stage)+'">'+esc(a.stage.replace("_"," "))+'</span></div><div class="mini">v'+a.version+' · '+(a.spec.tools||[]).join(", ")+'</div><div class="cardactions">'+actions.map(x=>'<button data-factory="'+x+'" data-id="'+esc(a.agent_id)+'">'+x+'</button>').join("")+'</div>'+(a.artifacts["agent_spec.md"]?'<details><summary>Generated artifact</summary><pre>'+esc(a.artifacts["agent_spec.md"])+'</pre></details>':"")+'</article>'}
async function loadDevices(){const box=$("#deviceList");box.innerHTML='<div class="empty">Registered device status is available when an Android endpoint has paired with this account.</div>';try{const r=await api("/v1/devices");box.innerHTML='<div class="capGrid">'+(r.capabilities||[]).map(x=>'<span>'+esc(x)+'</span>').join("")+'</div>'}catch{}}
async function loadProjects(){try{const r=await api("/v1/projects");$("#projectList").innerHTML=(r.projects||[]).map(p=>'<article class="card"><b>'+esc(p.name)+'</b><p>'+esc(p.description||"No description")+'</p><span class="mini">'+esc(p.project_id)+'</span></article>').join("")||'<div class="empty">No projects yet.</div>'}catch(e){$("#projectList").innerHTML='<div class="empty">'+esc(e.message)+'</div>'}}
async function createProject(){const name=prompt("Project name");if(!name)return;const description=prompt("Description")||"";try{await api("/v1/projects",{method:"POST",body:JSON.stringify({name,description,instructions:""})});loadProjects()}catch(e){toast(e.message)}}
async function runResearch(){const q=$("#researchQuery").value.trim();if(!q)return;$("#researchResult").innerHTML="<div class='empty'>Researching…</div>";try{const r=await api("/v1/assistant/runtime/respond",{method:"POST",body:JSON.stringify({text:"deep research "+q,execute_tools:true})});$("#researchResult").innerHTML='<h3>ASTRA synthesis</h3><div>'+text(r.response)+'</div>'}catch(e){$("#researchResult").innerHTML='<div class="empty">'+esc(e.message)+'</div>'}}
function initVoice(){
const R=window.SpeechRecognition||window.webkitSpeechRecognition;
if(!R){$("#voiceBtn").disabled=true;$("#wakeBtn").disabled=true;$("#voiceStatus").textContent="Voice input is not supported in this browser. Try Chrome or Edge.";return}
const wakePhrases=[
/^(hey assistant|ok assistant|okay assistant|hey aethon|ok aethon|okay aethon)[, ]*/i,
/^(नमस्ते असिस्टेंट|हे असिस्टेंट|ओके असिस्टेंट|हे एथॉन|ओके एथॉन)[, ]*/i,
/^(హే అసిస్టెంట్|ఓకే అసిస్టెంట్|హే ఏథాన్|ఓకే ఏథాన్)[, ]*/i,
/^(ஹே அசிஸ்டன்ட்|ஓகே அசிஸ்டன்ட்)[, ]*/i,
/^(ಹೇ ಅಸಿಸ್ಟೆಂಟ್|ಓಕೆ ಅಸಿಸ್ಟೆಂಟ್)[, ]*/i,
/^(ഹേ അസിസ്റ്റന്റ്|ഓക്കേ അസിസ്റ്റന്റ്)[, ]*/i,
/^(hola asistente|oye asistente|ok asistente)[, ]*/i,
/^(bonjour assistant|ok assistant)[, ]*/i,
/^(hallo assistent|ok assistent)[, ]*/i,
/^(こんにちはアシスタント|ねえアシスタント|你好助手|嗨助手)[, ]*/i
];
const cleanWake=s=>{let out=String(s||"").trim();for(const re of wakePhrases){if(re.test(out)){out=out.replace(re,"").trim();break}}return out};
const rec=new R();rec.lang=navigator.language||"en-US";rec.interimResults=true;rec.continuous=false;
rec.onstart=()=>$("#voiceStatus").textContent="Listening… speak naturally";
rec.onresult=e=>{let transcript="";for(let i=0;i<e.results.length;i++)transcript+=e.results[i][0].transcript;$("#input").value=cleanWake(transcript);if(e.results[e.results.length-1].isFinal){const q=cleanWake(transcript);if(q)send(q)}};
rec.onend=()=>$("#voiceStatus").textContent=state.wakeEnabled?"Wake phrase listening enabled":"Ready for your next message";
rec.onerror=e=>{if(e.error!=="no-speech"&&e.error!=="aborted")toast("Microphone issue: "+e.error)};
state.recognition=rec;
$("#voiceBtn").onclick=()=>{try{rec.lang=navigator.language||"en-US";rec.start()}catch{toast("Voice listening is already active.")}};
$("#speakBtn").onclick=()=>{state.voiceReplies=!state.voiceReplies;$("#speakBtn").classList.toggle("active",state.voiceReplies);toast(state.voiceReplies?"Spoken replies enabled":"Spoken replies disabled")};
const wake=new R();wake.continuous=true;wake.interimResults=false;wake.lang=navigator.language||"en-US";
const startWake=()=>{if(!state.wakeEnabled)return;try{wake.lang=navigator.language||"en-US";wake.start()}catch{}};
wake.onresult=e=>{for(let i=e.resultIndex;i<e.results.length;i++){if(!e.results[i].isFinal)continue;const raw=e.results[i][0].transcript,q=cleanWake(raw);if(q!==raw){try{wake.stop()}catch{};if(q)send(q);else toast("Wake phrase detected. Say your command.")}}};
wake.onend=()=>{if(state.wakeEnabled)setTimeout(startWake,350)};
wake.onerror=e=>{if(e.error==="not-allowed"||e.error==="service-not-allowed"){state.wakeEnabled=false;$("#wakeBtn").classList.remove("wakeOn");toast("Allow microphone access to use wake phrases.")}};
state.wakeRecognition=wake;
$("#wakeBtn").onclick=()=>{state.wakeEnabled=!state.wakeEnabled;$("#wakeBtn").classList.toggle("wakeOn",state.wakeEnabled);if(state.wakeEnabled){toast("Wake listening enabled. Keep this tab open and allow microphone access.");startWake()}else{try{wake.stop()}catch{};toast("Wake listening disabled")}};
}
async function capabilities(){try{const r=await api("/v1/capabilities");$("#capList").innerHTML=(r.capabilities||[]).map(x=>'<div class="caprow"><span>'+esc(x.name||x)+'</span><span class="badge">AVAILABLE</span></div>').join("");$("#capDialog").showModal()}catch(e){toast(e.message)}}
async function modelStatus(){try{const r=await api("/v1/model/health");$("#modelStatus").textContent=(r.ok?"● ":"○ ")+(r.provider||"runtime");$("#modelStatus").title=r.mode||""}catch{$("#modelStatus").textContent="○ runtime unavailable"}}
async function factoryAction(action,id){try{await api("/v1/ai-factory/"+id+"/"+action,{method:"POST"});loadFactory()}catch(e){toast(e.message)}}
function bind(){ $$(".navitem").forEach(b=>b.onclick=()=>setView(b.dataset.view));$("#newChat").onclick=()=>{state.session=null;$("#messages").innerHTML="";$("#welcome").style.display="block";setView("chat");$("#input").focus()};$("#renameBtn").onclick=()=>{const name=prompt("Conversation name",$("#viewTitle").textContent||"Assistant");if(name&&name.trim()){const clean=name.trim().slice(0,80);$("#viewTitle").textContent=clean;document.title=clean+" · AETHON";toast("Conversation renamed")}};$("#send").onclick=()=>send();$("#input").addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send()}});$("#input").addEventListener("input",e=>{e.target.style.height="auto";e.target.style.height=Math.min(180,e.target.scrollHeight)+"px"});$("#attachBtn").onclick=()=>$("#attachmentInput").click();$("#attachmentInput").onchange=e=>uploadFiles(e.target.files);$("#attachmentList").onclick=e=>{const b=e.target.closest("[data-rm]");if(b){state.attachments.splice(+b.dataset.rm,1);renderAttachments()}};$("#docsBtn").onclick=()=>window.open("/docs","_blank");$("#menuBtn").onclick=()=>$("#sidebar").classList.toggle("open");$("#capabilitiesBtn").onclick=capabilities;$("#settingsBtn").onclick=()=>{$("#token").value=state.token;$("#settingsDialog").showModal()};$("#saveSettings").onclick=()=>{state.token=$("#token").value.trim();state.token?localStorage.setItem("aethon_token",state.token):localStorage.removeItem("aethon_token");$("#settingsDialog").close();modelStatus()};$$("[data-close]").forEach(b=>b.onclick=()=>b.closest("dialog").close());$$("dialog").forEach(d=>d.addEventListener("click",e=>{if(e.target===d)d.close()}));$$(".quick button").forEach(b=>b.onclick=()=>send(b.dataset.prompt));$("#refreshAgents").onclick=loadAgents;$("#refreshDevices").onclick=loadDevices;$("#newProject").onclick=createProject;$("#runResearch").onclick=runResearch;$("#factoryForm").onsubmit=async e=>{e.preventDefault();const f=new FormData(e.target);try{await api("/v1/ai-factory",{method:"POST",body:JSON.stringify({name:f.get("name"),goal:f.get("goal"),model:f.get("model"),capabilities:String(f.get("capabilities")).split(",").map(x=>x.trim()).filter(Boolean),tools:String(f.get("tools")).split(",").map(x=>x.trim()).filter(Boolean),constraints:String(f.get("constraints")).split(",").map(x=>x.trim()).filter(Boolean)})});e.target.reset();loadFactory()}catch(x){toast(x.message)}};$("#factoryList").onclick=e=>{const b=e.target.closest("[data-factory]");if(b)factoryAction(b.dataset.factory,b.dataset.id)};$("#sessions").onclick=e=>{const b=e.target.closest("[data-id]");if(b){state.session=b.dataset.id;setView("chat");api("/v1/assistant/sessions/"+encodeURIComponent(state.session)+"/messages").then(r=>{$("#messages").innerHTML="";$("#welcome").style.display="none";(r.messages||[]).forEach(m=>addMessage(m.role==="user"?"user":"assistant",m.content))}).catch(()=>{})}};initVoice();loadSessions();modelStatus()}
document.readyState==="loading"?document.addEventListener("DOMContentLoaded",bind):bind();
})();