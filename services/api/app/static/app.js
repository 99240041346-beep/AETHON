(() => {
  "use strict";

  const $ = (selector) => document.querySelector(selector);
  const state = {
    session: null,
    busy: false,
    sessions: [],
    token: localStorage.getItem("aethon_token") || "",
    controller: null,
    lastPrompt: "",
    attachments: []
  };

  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"
  }[ch]));

  function authHeaders() {
    return state.token ? { Authorization: "Bearer " + state.token } : {};
  }

  function authErrorMessage(error) {
    const raw = String(error?.message || error || "");
    if (raw.includes("Not authenticated") || raw.includes('"detail":"Not authenticated"')) {
      return "AETHON requires an API token on this deployment. Open Settings and enter the Render AETHON_API_TOKEN.";
    }
    if (raw.includes("authentication is not configured")) {
      return "AETHON production authentication is not configured on the server.";
    }
    return raw;
  }

  async function api(path, options = {}) {
    const opts = { ...options, headers: { ...(options.headers || {}), ...authHeaders() } };
    if (opts.body && !opts.headers["Content-Type"]) opts.headers["Content-Type"] = "application/json";
    const response = await fetch(path, opts);
    if (!response.ok) {
      let message = response.statusText;
      try {
        const body = await response.text();
        if (body) message = body.slice(0, 600);
      } catch {}
      throw new Error(message || ("HTTP " + response.status));
    }
    const type = response.headers.get("content-type") || "";
    return type.includes("application/json") ? response.json() : response.text();
  }

  function renderText(value) {
    let text = esc(value);
    text = text.replace(/\`\`\`([\\s\\S]*?)\`\`\`/g, (_, code) => "<pre><code>" + code + "</code></pre>");
    text = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    text = text.replace(/\`([^\`]+)\`/g, "<code>$1</code>");
    text = text.replace(/^[-*] (.*)$/gm, "• $1");
    return text.split("\\n\\n").map((part) => "<p>" + part.replace(/\\n/g, "<br>") + "</p>").join("");
  }

  function showWelcome(show) {
    $("#welcome").style.display = show ? "block" : "none";
    $("#messages").style.display = show ? "none" : "block";
  }

  function setBusy(value) {
    state.busy = value;
    $("#send").disabled = false;
    $("#send").textContent = value ? "■" : "↑";
    $("#send").title = value ? "Stop generation" : "Send";
    $("#typing").classList.toggle("on", value);
  }

  function addMessage(role, text, events = []) {
    const box = $("#messages");
    const el = document.createElement("article");
    el.className = "message " + role;
    const eventHtml = events.map((event) => '<div class="event">• ' + esc(event) + "</div>").join("");
    el.innerHTML =
      '<div class="avatar">' + (role === "user" ? "YOU" : "A") + '</div>' +
      '<div class="bubble"><div class="message-name">' + (role === "user" ? "You" : "AETHON") +
      '</div><div class="content">' + renderText(text) + "</div>" + eventHtml + "</div>";
    box.appendChild(el);
    box.scrollTop = box.scrollHeight;
    return el;
  }

  function addMessageTools(el, prompt) {
    if (!el || el.dataset.tools) return;
    el.dataset.tools = "1";
    const tools = document.createElement("div");
    tools.className = "message-tools";

    const copy = document.createElement("button");
    copy.className = "message-tool";
    copy.textContent = "Copy";
    copy.onclick = () => navigator.clipboard?.writeText(el.querySelector(".content")?.innerText || "");
    tools.appendChild(copy);

    if (prompt) {
      const edit = document.createElement("button");
      edit.className = "message-tool";
      edit.textContent = "Edit";
      edit.onclick = () => {
        $("#input").value = prompt;
        $("#input").focus();
        $("#input").dispatchEvent(new Event("input"));
      };
      tools.appendChild(edit);

      const regenerate = document.createElement("button");
      regenerate.className = "message-tool";
      regenerate.textContent = "Regenerate";
      regenerate.onclick = () => send(prompt, true);
      tools.appendChild(regenerate);
    }

    el.querySelector(".bubble").appendChild(tools);
  }

  async function loadSessions(query = "") {
    try {
      const endpoint = query
        ? "/v1/assistant/sessions/search?q=" + encodeURIComponent(query) + "&limit=50"
        : "/v1/assistant/sessions?limit=50";
      const data = await api(endpoint);
      state.sessions = data.sessions || data || [];
      $("#sessions").innerHTML = state.sessions.map((session) =>
        '<div class="session ' + (session.session_id === state.session ? "active" : "") +
        '" data-id="' + esc(session.session_id) + '">' +
        '<span>◌</span><span class="session-title">' + esc(session.title || "New conversation") +
        '</span><button class="session-delete" data-delete="' + esc(session.session_id) + '">×</button></div>'
      ).join("");
    } catch (error) {
      $("#sessions").innerHTML = "";
      console.warn("Session loading failed:", error);
    }
  }

  async function openSession(id) {
    state.session = id;
    showWelcome(false);
    $("#messages").innerHTML = "";
    try {
      const data = await api("/v1/assistant/sessions/" + encodeURIComponent(id) + "/messages");
      const messages = data.messages || data || [];
      messages.forEach((message) => addMessage(message.role === "user" ? "user" : "assistant", message.content));
      const session = state.sessions.find((item) => item.session_id === id);
      $("#chatTitle").textContent = session?.title || "Conversation";
    } catch (error) {
      addMessage("assistant", "I could not load this conversation: " + error.message);
    }
    await loadSessions();
  }

  function renderAttachments() {
    const box = $("#attachmentList");
    box.innerHTML = state.attachments.map((item, index) => '<span class="attachment-chip">' + esc(item.filename) + ' <button type="button" data-remove-attachment="' + index + '">×</button></span>').join("");
  }

  async function uploadAttachments(files) {
    for (const file of Array.from(files).slice(0, 5 - state.attachments.length)) {
      const form = new FormData();
      form.append("file", file);
      try {
        const response = await fetch("/v1/assistant/runtime/attachments", { method: "POST", headers: authHeaders(), body: form });
        if (!response.ok) throw new Error((await response.text()).slice(0, 300));
        state.attachments.push(await response.json());
      } catch (error) {
        const chip = document.createElement("span");
        chip.className = "attachment-chip error";
        chip.textContent = file.name + ": " + authErrorMessage(error);
        $("#attachmentList").appendChild(chip);
      }
    }
    renderAttachments();
  }

  function newChat() {
    state.session = null;
    state.attachments = [];
    renderAttachments();
    $("#chatTitle").textContent = "AETHON";
    $("#messages").innerHTML = "";
    showWelcome(true);
    loadSessions();
    $("#input").focus();
  }

  function updateAssistant(el, response) {
    const content = el.querySelector(".content");
    if (content) content.innerHTML = renderText(response || "");
  }

  async function send(text, regenerate = false) {
    text = (text || $("#input").value).trim();
    if (!text || state.busy) return;

    state.lastPrompt = text;
    $("#input").value = "";
    state.attachments = [];
    renderAttachments();
    $("#input").style.height = "auto";
    showWelcome(false);
    if (!regenerate) addMessage("user", text);

    setBusy(true);
    const assistant = addMessage("assistant", "");
    const content = assistant.querySelector(".content");
    const events = [];

    try {
      state.controller = new AbortController();
      const response = await fetch("/v1/assistant/runtime/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({
          text,
          session_id: state.session,
          execute_tools: true,
          require_approval: false,
          attachment_ids: state.attachments.map((item) => item.attachment_id)
        }),
        signal: state.controller.signal
      });

      if (!response.ok) {
        let message = response.statusText;
        try {
          const body = await response.text();
          if (body) message = body.slice(0, 600);
        } catch {}
        throw new Error(message || ("HTTP " + response.status));
      }

      if (!response.body) throw new Error("Streaming response is unavailable.");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const chunk = await reader.read();
        if (chunk.done) break;
        buffer += decoder.decode(chunk.value, { stream: true });
        const records = buffer.split("\\n\\n");
        buffer = records.pop() || "";

        for (const record of records) {
          const dataLine = record.split("\\n").find((line) => line.startsWith("data: "));
          if (!dataLine) continue;

          let data;
          try { data = JSON.parse(dataLine.slice(6)); } catch { continue; }

          if (record.includes("event: progress")) {
            const message = data.data?.message || data.data?.status || data.type;
            if (message && !events.includes(message)) {
              events.push(message);
              assistant.querySelector(".bubble").insertAdjacentHTML(
                "beforeend", '<div class="event">• ' + esc(message) + "</div>"
              );
            }
          }

          if (record.includes("event: completed")) {
            if (data.session_id) state.session = data.session_id;
            updateAssistant(assistant, data.response || data.error || "No response.");
            addMessageTools(assistant, text);
            if (data.requires_confirmation) assistant.querySelector(".bubble").insertAdjacentHTML(
              "beforeend", '<div class="event">⚠ Approval required before this action can execute.</div>'
            );
            if (data.action_authorized) assistant.querySelector(".bubble").insertAdjacentHTML(
              "beforeend", '<div class="event">✓ Action authorized</div>'
            );
            if (data.verified) assistant.querySelector(".bubble").insertAdjacentHTML(
              "beforeend", '<div class="event">✓ Verified result</div>'
            );
          }
        }
      }

      await loadSessions();
      if (state.session) {
        const current = state.sessions.find((item) => item.session_id === state.session);
        $("#chatTitle").textContent = current?.title || "Conversation";
      }
    } catch (error) {
      if (error.name === "AbortError") {
        updateAssistant(assistant, "Generation stopped.");
      } else {
        updateAssistant(assistant, authErrorMessage(error));
      }
      addMessageTools(assistant, text);
    } finally {
      state.controller = null;
      setBusy(false);
      $("#input").focus();
    }
  }

  async function showCapabilities() {
    try {
      const data = await api("/v1/capabilities");
      $("#capList").innerHTML = (data.capabilities || []).map((capability) =>
        '<div class="cap"><div><div class="cap-name">' + esc(capability.name) +
        '</div><div class="cap-desc">' + esc(capability.description) +
        '</div></div><span class="pill ' + (capability.available ? "ok" : "") + '">' +
        (capability.available ? "AVAILABLE" : "NOT CONNECTED") + "</span></div>"
      ).join("");
      $("#capDialog").showModal();
    } catch (error) {
      alert(authErrorMessage(error));
    }
  }

  function exportConversation() {
    const rows = Array.from(document.querySelectorAll("#messages .message")).map((message) => ({
      role: message.classList.contains("user") ? "You" : "AETHON",
      text: message.querySelector(".content")?.innerText || ""
    }));
    if (!rows.length) {
      alert("There is no conversation to export yet.");
      return;
    }
    const body = rows.map((row) => "## " + row.role + "\\n\\n" + row.text).join("\\n\\n");
    const blob = new Blob([body], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = (state.sessions.find((item) => item.session_id === state.session)?.title || "aethon-conversation") + ".md";
    link.click();
    URL.revokeObjectURL(url);
  }

  function bind() {
    $("#newChat").onclick = newChat;
    $("#clearBtn").onclick = newChat;
    $("#send").onclick = () => state.busy ? state.controller?.abort() : send();
    $("#attachBtn").onclick = () => $("#attachmentInput").click();
    $("#attachmentInput").addEventListener("change", (event) => {
      uploadAttachments(event.target.files);
      event.target.value = "";
    });
    $("#attachmentList").addEventListener("click", (event) => {
      const button = event.target.closest("[data-remove-attachment]");
      if (!button) return;
      state.attachments.splice(Number(button.dataset.removeAttachment), 1);
      renderAttachments();
    });

    $("#capabilitiesBtn").onclick = showCapabilities;

    $("#settingsBtn").onclick = () => {
      $("#token").value = state.token;
      $("#settingsDialog").showModal();
    };

    $("#saveSettings").onclick = () => {
      state.token = $("#token").value.trim();
      if (state.token) localStorage.setItem("aethon_token", state.token);
      else localStorage.removeItem("aethon_token");
      $("#settingsDialog").close();
      loadSessions();
    };

    $("#docsBtn").onclick = () => window.open("/docs", "_blank", "noopener");
    $("#menuBtn").onclick = () => $("#sidebar").classList.toggle("open");
    $("#renameBtn").onclick = async () => {
      if (!state.session) return;
      const current = state.sessions.find((item) => item.session_id === state.session);
      const title = window.prompt("Conversation name", current?.title || "Conversation");
      if (!title?.trim()) return;
      try {
        await api("/v1/assistant/sessions/" + encodeURIComponent(state.session), {
          method: "PATCH",
          body: JSON.stringify({ title: title.trim() })
        });
        $("#chatTitle").textContent = title.trim();
        await loadSessions();
      } catch (error) {
        alert(authErrorMessage(error));
      }
    };

    document.querySelectorAll("[data-close]").forEach((button) => {
      button.onclick = () => button.closest("dialog").close();
    });

    document.querySelectorAll(".quick-grid button").forEach((button) => {
      button.onclick = () => send(button.dataset.prompt);
    });

    $("#input").addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        send();
      }
    });

    $("#input").addEventListener("input", (event) => {
      event.target.style.height = "auto";
      event.target.style.height = Math.min(event.target.scrollHeight, 180) + "px";
    });

    let searchTimer;
    $("#sessionSearch").addEventListener("input", (event) => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => loadSessions(event.target.value.trim()), 180);
    });

    $("#sessions").addEventListener("click", (event) => {
      const deleteButton = event.target.closest("[data-delete]");
      if (deleteButton) {
        event.stopPropagation();
        api("/v1/assistant/sessions/" + encodeURIComponent(deleteButton.dataset.delete), { method: "DELETE" })
          .then(loadSessions)
          .catch((error) => alert(error.message));
        return;
      }
      const session = event.target.closest(".session");
      if (session) openSession(session.dataset.id);
    });

    const exportButton = document.createElement("button");
    exportButton.className = "side-action";
    exportButton.textContent = "⇩ Export conversation";
    exportButton.onclick = exportConversation;
    $(".sidebar-bottom").insertBefore(exportButton, $("#docsBtn"));

    loadSessions();
  }

  window.addEventListener("error", (event) => {
    console.error("AETHON frontend error:", event.error || event.message);
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind, { once: true });
  } else {
    bind();
  }
})();