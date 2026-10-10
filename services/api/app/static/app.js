(()=>{"use strict";
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const readPrefs=()=>{try{return JSON.parse(localStorage.getItem("aethon_preferences")||"{}")}catch{return {}}};
const prefs={theme:"dark",accent:"blue",language:"auto",enterToSend:true,showModelStatus:true,name:"",style:"balanced",instructions:"",personalization:true,voiceReplies:false,voiceLanguage:"auto",wakeEnabled:false,rememberToken:true,...readPrefs()};
const state={session:null,busy:false,token:localStorage.getItem("aethon_token")||"",attachments:[],voiceReplies:!!prefs.voiceReplies,recognition:null,wakeRecognition:null,wakeEnabled:!!prefs.wakeEnabled,voiceLanguage:prefs.voiceLanguage==="auto"?(navigator.language||"en-IN"):prefs.voiceLanguage,mediaRecorder:null,recordedChunks:[],mediaStream:null};
const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const api=async(path,opt={})=>{const o={...opt,headers:{...(opt.headers||{}),...(state.token?{Authorization:"Bearer "+state.token}:{})}};if(o.body&&!(o.body instanceof FormData))o.headers["Content-Type"]="application/json";const r=await fetch(path,o);if(!r.ok)throw Error((await r.text()).slice(0,600)||r.statusText);return (r.headers.get("content-type")||"").includes("json")?r.json():r.text()};
const text=v=>esc(v).replace(/\*\*(.*?)\*\*/g,"<strong>$1</strong>").replace(/\`([^\`]+)\`/g,"<code>$1</code>").split("\n").map(x=>"<div>"+x+"</div>").join("");
function speakResponse(value){if(!("speechSynthesis"in window))return;speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(String(value||""));u.lang=detectSpeechLanguage(String(value||""))||(state.voiceLanguage!=="auto"?state.voiceLanguage:null)||navigator.language||"en-IN";speechSynthesis.speak(u)}
function detectSpeechLanguage(s){if(/[\u0C00-\u0C7F]/.test(s))return "te-IN";if(/[\u0900-\u097F]/.test(s))return "hi-IN";if(/[\u0B80-\u0BFF]/.test(s))return "ta-IN";if(/[\u0C80-\u0CFF]/.test(s))return "kn-IN";if(/[\u0D00-\u0D7F]/.test(s))return "ml-IN";if(/[\u0980-\u09FF]/.test(s))return "bn-IN";if(/[\u0A00-\u0A7F]/.test(s))return "pa-IN";if(/[\u0A80-\u0AFF]/.test(s))return "gu-IN";if(/[\u0600-\u06FF]/.test(s))return "ur-PK";if(/[\u4E00-\u9FFF]/.test(s))return "zh-CN";if(/[\u3040-\u30FF]/.test(s))return "ja-JP";if(/[\uAC00-\uD7AF]/.test(s))return "ko-KR";if(/[\u0400-\u04FF]/.test(s))return "ru-RU";return null}
function toast(msg){let x=document.createElement("div");x.className="toast";x.textContent=msg;document.body.appendChild(x);setTimeout(()=>x.remove(),3000)}
function setView(name){$$(".view").forEach(x=>x.classList.toggle("active",x.id==="view-"+name));$$(".navitem").forEach(x=>x.classList.toggle("active",x.dataset.view===name));const titles={chat:"Assistant",agents:"Autonomous Agents",factory:"AI Factory",devices:"Device Control",projects:"Projects",research:"Research"};$("#viewTitle").textContent=titles[name]||"Assistant";if(name==="agents")loadAgents();if(name==="factory")loadFactory();if(name==="devices")loadDevices();if(name==="projects")loadProjects()}
function addMessage(role,content){$("#welcome").style.display="none";const el=document.createElement("article");el.className="message "+role;el.innerHTML='<div class="avatar">'+(role==="user"?"YOU":"A")+'</div><div class="bubble"><small>'+(role==="user"?"You":"Assistant")+'</small><div class="content">'+text(content)+'</div></div>';$("#messages").appendChild(el);$("#messages").scrollTop=$("#messages").scrollHeight;return el}
function renderAttachments(){$("#attachmentList").innerHTML=state.attachments.map((a,i)=>'<span>'+esc(a.filename)+' <button data-rm="'+i+'">×</button></span>').join("")}
async function uploadFiles(files){for(const f of [...files].slice(0,5-state.attachments.length)){const fd=new FormData();fd.append("file",f);try{const r=await api("/v1/assistant/runtime/attachments",{method:"POST",body:fd});state.attachments.push(r)}catch(e){toast("Attachment failed: "+e.message)}}renderAttachments()}
async function send(value){
  let q=(value||$("#input").value).trim();\n  if(prefs.personalization&&prefs.instructions.trim())q += "\\n\\nUser response preferences (follow when relevant): "+prefs.instructions.trim().slice(0,2000);\n  if(prefs.personalization&&prefs.name.trim())q += "\\n\\nThe user prefers to be called "+prefs.name.trim().slice(0,80)+".";\n  if(prefs.personalization&&prefs.style==="concise")q += "\\n\\nPrefer concise answers.";else if(prefs.personalization&&prefs.style==="detailed")q += "\\n\\nPrefer detailed explanations.";else if(prefs.personalization&&prefs.style==="friendly")q += "\\n\\nUse a friendly, conversational tone.";
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
const stopTracks=()=>{if(state.mediaStream){state.mediaStream.getTracks().forEach(t=>t.stop());state.mediaStream=null}};
const transcribeRecording=async blob=>{
  if(!blob||!blob.size){toast("No audio captured. Please try again.");return}
  const fd=new FormData();const ext=blob.type.includes("mp4")?".m4a":blob.type.includes("ogg")?".ogg":blob.type.includes("wav")?".wav":".webm";fd.append("file",blob,"aethon-voice"+ext);
  $("#voiceStatus").textContent="Transcribing speech… detecting language automatically";
  try{
    const result=await api("/v1/voice/transcribe",{method:"POST",body:fd});
    const phrase=String(result.text||"").trim();
    if(!phrase){toast("No speech detected. Try speaking a little closer to the microphone.");return}
    $("#input").value=phrase;
    $("#voiceStatus").textContent=result.language?"Detected language: "+result.language:"Speech recognized";
    await send(phrase);
  }catch(e){$("#voiceStatus").textContent="Voice transcription unavailable";toast(e.message||"Voice transcription failed")}
};
$("#voiceBtn").onclick=async()=>{
  if(state.mediaRecorder&&state.mediaRecorder.state==="recording"){state.mediaRecorder.stop();$("#voiceBtn").classList.remove("active");$("#voiceStatus").textContent="Finishing recording…";return}
  if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia||!window.MediaRecorder){toast("Audio recording is not supported here. Try the latest Chrome or Edge over HTTPS.");return}
  try{
    state.mediaStream=await navigator.mediaDevices.getUserMedia({audio:true});
    const preferred=["audio/webm;codecs=opus","audio/webm","audio/mp4"].find(t=>MediaRecorder.isTypeSupported(t));
    state.mediaRecorder=preferred?new MediaRecorder(state.mediaStream,{mimeType:preferred}):new MediaRecorder(state.mediaStream);
    state.recordedChunks=[];
    state.mediaRecorder.ondataavailable=e=>{if(e.data&&e.data.size)state.recordedChunks.push(e.data)};
    state.mediaRecorder.onerror=()=>{stopTracks();$("#voiceBtn").classList.remove("active");toast("Audio recording failed.")};
    state.mediaRecorder.onstop=()=>{
      const blob=new Blob(state.recordedChunks,{type:state.mediaRecorder.mimeType||"audio/webm"});
      state.recordedChunks=[];stopTracks();$("#voiceBtn").classList.remove("active");transcribeRecording(blob);
    };
    state.mediaRecorder.start();$("#voiceBtn").classList.add("active");$("#voiceStatus").textContent="Recording… click the microphone again when you finish";
  }catch(e){stopTracks();toast(e.name==="NotAllowedError"?"Allow microphone access to use voice chat.":("Could not start microphone: "+(e.message||"unknown error")))}
};
$("#speakBtn").onclick=()=>{state.voiceReplies=!state.voiceReplies;$("#speakBtn").classList.toggle("active",state.voiceReplies);toast(state.voiceReplies?"Spoken replies enabled":"Spoken replies disabled")};
if(!R){$("#wakeBtn").disabled=true;$("#voiceStatus").textContent="Tap the microphone to record a voice message; multilingual transcription needs server setup." ;return}
const wakePhrases=[
/^(hey buddy|ok buddy|okay buddy|hey assistant|ok assistant|okay assistant|hey aethon|ok aethon|okay aethon)[, ]*/i,
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
const wake=new R();wake.continuous=true;wake.interimResults=false;wake.lang=navigator.language||"en-US";
const startWake=()=>{if(!state.wakeEnabled)return;try{wake.lang=navigator.language||"en-US";wake.start()}catch{}};
wake.onresult=e=>{for(let i=e.resultIndex;i<e.results.length;i++){if(!e.results[i].isFinal)continue;const raw=e.results[i][0].transcript,q=cleanWake(raw);if(q!==raw){try{wake.stop()}catch{};if(q){$("#input").value=q;$("#voiceStatus").textContent="Wake phrase detected. Tap microphone to record your request."}else toast("Wake phrase detected. Tap the microphone and speak.")}}};
wake.onend=()=>{if(state.wakeEnabled)setTimeout(startWake,500)};
wake.onerror=e=>{if(e.error==="not-allowed"||e.error==="service-not-allowed"){state.wakeEnabled=false;$("#wakeBtn").classList.remove("wakeOn");toast("Allow microphone access to use wake phrases.")}};
state.wakeRecognition=wake;
$("#wakeBtn").onclick=()=>{state.wakeEnabled=!state.wakeEnabled;$("#wakeBtn").classList.toggle("wakeOn",state.wakeEnabled);if(state.wakeEnabled){toast("Wake-word listening enabled. Keep this tab open and allow microphone access.");startWake()}else{try{wake.stop()}catch{};toast("Wake-word listening disabled")}};
}
async function capabilities(){try{const r=await api("/v1/capabilities");$("#capList").innerHTML=(r.capabilities||[]).map(x=>'<div class="caprow"><span>'+esc(x.name||x)+'</span><span class="badge">AVAILABLE</span></div>').join("");$("#capDialog").showModal()}catch(e){toast(e.message)}}
async function modelStatus(){try{const r=await api("/v1/model/health");$("#modelStatus").textContent=(r.ok?"● ":"○ ")+(r.provider||"runtime");$("#modelStatus").title=r.mode||""}catch{$("#modelStatus").textContent="○ runtime unavailable"}}
async function factoryAction(action,id){try{await api("/v1/ai-factory/"+id+"/"+action,{method:"POST"});loadFactory()}catch(e){toast(e.message)}}
function applyPrefs(){
  const theme=prefs.theme==="system"?(window.matchMedia&&window.matchMedia("(prefers-color-scheme: light)").matches?"light":"dark"):prefs.theme;
  document.documentElement.dataset.theme=theme;document.documentElement.dataset.accent=prefs.accent;
  $("#modelStatus").style.display=prefs.showModelStatus?"":"none";
  $("#speakBtn").classList.toggle("active",!!prefs.voiceReplies);$("#wakeBtn").classList.toggle("wakeOn",!!prefs.wakeEnabled);
  state.voiceReplies=!!prefs.voiceReplies;state.wakeEnabled=!!prefs.wakeEnabled;state.voiceLanguage=prefs.voiceLanguage==="auto"?(navigator.language||"en-IN"):prefs.voiceLanguage;
}
function openSettings(){
  const map={prefTheme:"theme",prefAccent:"accent",prefLanguage:"language",prefEnter:"enterToSend",prefModelStatus:"showModelStatus",prefName:"name",prefStyle:"style",prefInstructions:"instructions",prefPersonalization:"personalization",prefVoiceReplies:"voiceReplies",prefVoiceLanguage:"voiceLanguage",prefWake:"wakeEnabled",prefRememberToken:"rememberToken"};
  for(const [id,key] of Object.entries(map)){const el=$("#"+id);if(!el)continue;if(el.type==="checkbox")el.checked=!!prefs[key];else el.value=prefs[key]??"";}
  $("#token").value=state.token;switchSettingsTab("general");$("#settingsDialog").showModal();refreshSettingsStatus();
}
function switchSettingsTab(name){$("[data-setting-tab]").forEach(b=>b.classList.toggle("active",b.dataset.settingTab===name));$("[data-setting-panel]").forEach(p=>p.classList.toggle("active",p.dataset.settingPanel===name));}
async function refreshSettingsStatus(){try{const r=await api("/v1/model/health");$("#settingApiStatus").textContent="Connected";$("#settingModelStatus").textContent=(r.provider||"Runtime")+(r.ok?" · Ready":" · Check");}catch{$("#settingApiStatus").textContent="Unreachable";$("#settingModelStatus").textContent="Unavailable";}}
function savePrefs(){
 const map={prefTheme:"theme",prefAccent:"accent",prefLanguage:"language",prefEnter:"enterToSend",prefModelStatus:"showModelStatus",prefName:"name",prefStyle:"style",prefInstructions:"instructions",prefPersonalization:"personalization",prefVoiceReplies:"voiceReplies",prefVoiceLanguage:"voiceLanguage",prefWake:"wakeEnabled",prefRememberToken:"rememberToken"};
 for(const [id,key] of Object.entries(map)){const el=$("#"+id);if(el)prefs[key]=el.type==="checkbox"?el.checked:el.value;}
 localStorage.setItem("aethon_preferences",JSON.stringify(prefs));state.token=$("#token").value.trim();if(prefs.rememberToken&&state.token)localStorage.setItem("aethon_token",state.token);else localStorage.removeItem("aethon_token");applyPrefs();$("#settingsSaved").textContent="Saved just now";$("#settingsDialog").close();modelStatus();
 if(state.wakeEnabled&&state.wakeRecognition){try{state.wakeRecognition.start()}catch{}}else if(state.wakeRecognition){try{state.wakeRecognition.stop()}catch{}}
 toast("Settings saved on this device");
}
function exportCurrentChat(){const lines=[];$(".message").forEach(m=>{const who=m.classList.contains("user")?"You":"AETHON";lines.push(who+": "+(m.querySelector(".content")?.innerText||""));});const blob=new Blob([lines.join("\
\
")||"No messages in the current chat."],{type:"text/plain;charset=utf-8"});const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download="aethon-conversation.txt";a.click();URL.revokeObjectURL(url);}
function bind(){ $(".navitem").forEach(b=>b.onclick=()=>setView(b.dataset.view));$("#newChat").onclick=()=>{state.session=null;$("#messages").innerHTML="";$("#welcome").style.display="block";setView("chat");$("#input").focus()};$("#renameBtn").onclick=()=>{const name=prompt("Conversation name",$("#viewTitle").textContent||"Assistant");if(name&&name.trim()){const clean=name.trim().slice(0,80);$("#viewTitle").textContent=clean;document.title=clean+" · AETHON";toast("Conversation renamed")}};$("#send").onclick=()=>send();$("#input").addEventListener("keydown",e=>{if(prefs.enterToSend&&e.key==="Enter"&&!e.shiftKey){e.preventDefault();send()}});$("#input").addEventListener("input",e=>{e.target.style.height="auto";e.target.style.height=Math.min(180,e.target.scrollHeight)+"px"});$("#attachBtn").onclick=()=>$("#attachmentInput").click();$("#attachmentInput").onchange=e=>uploadFiles(e.target.files);$("#attachmentList").onclick=e=>{const b=e.target.closest("[data-rm]");if(b){state.attachments.splice(+b.dataset.rm,1);renderAttachments()}};$("#docsBtn").onclick=()=>window.open("/docs","_blank");$("#menuBtn").onclick=()=>$("#sidebar").classList.toggle("open");$("#capabilitiesBtn").onclick=capabilities;$("#settingsBtn").onclick=openSettings;$("#saveSettings").onclick=savePrefs;$("[data-setting-tab]").forEach(b=>b.onclick=()=>switchSettingsTab(b.dataset.settingTab));$("#exportChat").onclick=exportCurrentChat;$("#clearCurrentChat").onclick=()=>{if(confirm("Clear messages from this view? Server history will remain saved.")){$("#messages").innerHTML="";$("#welcome").style.display="block";state.session=null;}};$("#resetPreferences").onclick=()=>{if(confirm("Reset AETHON preferences on this device?")){localStorage.removeItem("aethon_preferences");Object.assign(prefs,{theme:"dark",accent:"blue",language:"auto",enterToSend:true,showModelStatus:true,name:"",style:"balanced",instructions:"",personalization:true,voiceReplies:false,voiceLanguage:"auto",wakeEnabled:false,rememberToken:true});applyPrefs();openSettings();}};$("#clearToken").onclick=()=>{$("#token").value="";state.token="";localStorage.removeItem("aethon_token");$("#prefRememberToken").checked=false;toast("Saved token removed")};$("#refreshSettingsStatus").onclick=refreshSettingsStatus;$("#openApiDocs").onclick=()=>window.open("/docs","_blank");$$("[data-close]").forEach(b=>b.onclick=()=>b.closest("dialog").close());$$("dialog").forEach(d=>d.addEventListener("click",e=>{if(e.target===d)d.close()}));$$(".quick button").forEach(b=>b.onclick=()=>send(b.dataset.prompt));$("#refreshAgents").onclick=loadAgents;$("#refreshDevices").onclick=loadDevices;$("#newProject").onclick=createProject;$("#runResearch").onclick=runResearch;$("#factoryForm").onsubmit=async e=>{e.preventDefault();const f=new FormData(e.target);try{await api("/v1/ai-factory",{method:"POST",body:JSON.stringify({name:f.get("name"),goal:f.get("goal"),model:f.get("model"),capabilities:String(f.get("capabilities")).split(",").map(x=>x.trim()).filter(Boolean),tools:String(f.get("tools")).split(",").map(x=>x.trim()).filter(Boolean),constraints:String(f.get("constraints")).split(",").map(x=>x.trim()).filter(Boolean)})});e.target.reset();loadFactory()}catch(x){toast(x.message)}};$("#factoryList").onclick=e=>{const b=e.target.closest("[data-factory]");if(b)factoryAction(b.dataset.factory,b.dataset.id)};$("#sessions").onclick=e=>{const b=e.target.closest("[data-id]");if(b){state.session=b.dataset.id;setView("chat");api("/v1/assistant/sessions/"+encodeURIComponent(state.session)+"/messages").then(r=>{$("#messages").innerHTML="";$("#welcome").style.display="none";(r.messages||[]).forEach(m=>addMessage(m.role==="user"?"user":"assistant",m.content))}).catch(()=>{})}};initVoice();applyPrefs();if(state.wakeEnabled&&state.wakeRecognition){try{state.wakeRecognition.start()}catch{}}loadSessions();modelStatus()}
document.readyState==="loading"?document.addEventListener("DOMContentLoaded",bind):bind();
})();