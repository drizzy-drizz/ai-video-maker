"use strict";
const state = { series: null, projects: [], episodeId: null, workflows: [], jobs: {} };
const byId = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let toastTimer;

async function api(path, method = "GET", body) {
  const config = { method, headers: { "Content-Type": "application/json" } };
  if (body !== undefined) config.body = JSON.stringify(body);
  const response = await fetch(path, config);
  let payload;
  try { payload = await response.json(); } catch { throw new Error("The local server returned an unreadable response."); }
  if (!response.ok) throw new Error(payload.error || "Request failed (" + response.status + ")");
  return payload;
}

function toast(message, failed = false) {
  const box = byId("toast");
  box.textContent = String(message);
  box.style.borderColor = failed ? "#b96975" : "#526574";
  box.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => box.classList.remove("visible"), 6500);
}

async function refreshLibrary() {
  state.projects = await api("/api/series");
  const list = byId("seriesList");
  list.innerHTML = "";
  if (!state.projects.length) {
    list.innerHTML = '<div class="muted">No projects yet. Create your first series.</div>';
    return;
  }
  state.projects.forEach((project) => {
    const button = document.createElement("button");
    button.className = "series-item" + (state.series && state.series.id === project.id ? " active" : "");
    button.innerHTML = "<strong>" + escapeHtml(project.title) + "</strong><small>" +
      escapeHtml(project.language === "tl" ? "Tagalog" : "English") + " · " +
      escapeHtml(project.episodes) + " episode(s)</small>";
    button.onclick = () => loadSeries(project.id);
    list.appendChild(button);
  });
}

async function loadSeries(id) {
  try {
    state.series = await api("/api/series/" + id);
    state.episodeId = state.series.episodes.some(e => e.id === state.episodeId) ?
      state.episodeId : (state.series.episodes[0] || {}).id;
    byId("createView").hidden = true;
    byId("studioView").hidden = false;
    byId("breadcrumb").textContent = state.series.title;
    byId("studioTitle").textContent = state.series.title;
    byId("studioMeta").textContent = (state.series.language === "tl" ? "Tagalog" : "English") +
      "  ·  " + state.series.genre + "  ·  " + state.series.format + "  ·  " +
      state.series.episodes.length + " episode(s)  ·  " + state.series.planner;
    byId("originalStory").textContent = state.series.storyline;
    byId("world").value = state.series.bible.world || "";
    byId("style").value = state.series.bible.style || "";
    byId("canon").value = state.series.bible.canon || "";
    byId("characters").value = JSON.stringify(state.series.bible.characters || [], null, 2);
    renderEpisodes();
    await refreshLibrary();
  } catch (error) { toast(error.message, true); }
}

function newProjectView() {
  state.series = null;
  state.episodeId = null;
  byId("studioView").hidden = true;
  byId("createView").hidden = false;
  byId("breadcrumb").textContent = "New Series";
  refreshLibrary().catch(error => toast(error.message, true));
}

async function saveSeries(showToast = true) {
  if (!state.series) return;
  const { id, title, genre, format, language, bible, episodes } = state.series;
  state.series = await api("/api/series/" + id, "PATCH", { title, genre, format, language, bible, episodes });
  if (showToast) toast("Series and all edited scenes saved locally.");
}

function renderEpisodes() {
  if (!state.series) return;
  byId("episodeCount").textContent = state.series.episodes.length;
  const list = byId("episodeList");
  list.innerHTML = "";
  state.series.episodes.forEach((episode) => {
    const button = document.createElement("button");
    button.className = "episode-button" + (state.episodeId === episode.id ? " active" : "");
    button.innerHTML = "<strong>" + escapeHtml(episode.title) + "</strong><small>" +
      episode.scenes.length + " shots · " + escapeHtml(episode.status) + "</small>";
    button.onclick = () => { state.episodeId = episode.id; renderEpisodes(); };
    list.appendChild(button);
  });
  const episode = state.series.episodes.find(e => e.id === state.episodeId);
  if (!episode) {
    byId("episodeHeader").textContent = "This series has no episodes.";
    byId("sceneList").innerHTML = "";
    return;
  }
  const head = byId("episodeHeader");
  head.innerHTML = '<label class="eyebrow">CURRENT EPISODE · EDIT TITLE</label><input id="episodeTitleInput" class="episode-name" maxlength="200" aria-label="Episode title" value="' +
    escapeHtml(episode.title) + '"><p class="episode-subtitle">' + episode.scenes.length +
    " scenes · " + escapeHtml(episode.status) + "</p>";
  const titleInput = byId("episodeTitleInput");
  titleInput.style.cssText = "background:transparent;color:var(--text);border:none;border-bottom:1px solid var(--line);width:100%;padding:8px 0;outline:none;font-weight:750";
  titleInput.oninput = () => { episode.title = titleInput.value; };
  const aiButton = document.createElement("button");
  aiButton.className = "button ghost";
  aiButton.style.marginTop = "10px";
  aiButton.textContent = "AI Direct Episode (Local Qwen)";
  aiButton.onclick = async () => {
    try {
      await saveSeries(false);
      const queued = await api("/api/series/" + state.series.id + "/episodes/" +
        episode.id + "/direct", "POST", {});
      state.jobs[queued.job_id] = "queued";
      toast("Local AI directing queued. Suggestions won't overwrite your current prompts.");
      refreshJobs();
    } catch (error) { toast(error.message, true); }
  };
  head.appendChild(aiButton);
  const sceneList = byId("sceneList");
  sceneList.innerHTML = "";
  episode.scenes.forEach((scene) => {
    const article = document.createElement("article");
    article.className = "scene-card";
    article.innerHTML =
      '<div class="scene-top"><span class="scene-num">SHOT ' + String(scene.number).padStart(2, "0") +
      '</span><strong>' + (scene.clip ? "MOVING VIDEO ATTACHED" : "AWAITING VIDEO FOOTAGE") + "</strong></div>" +
      '<label>Story beat / dialogue<textarea class="scene-script" rows="3">' + escapeHtml(scene.script) + "</textarea></label>" +
      '<label>Video direction / camera / action<textarea class="scene-prompt" rows="4">' + escapeHtml(scene.prompt) + "</textarea></label>" +
      '<label>Negative prompt<textarea class="scene-negative" rows="2">' + escapeHtml(scene.negative_prompt || "") + "</textarea></label>" +
      '<label>Local video file path (.mp4, .webm, .mov, .mkv)<input class="scene-clip" placeholder="C:\\Videos\\episode1-shot1.mp4" value="' + escapeHtml(scene.clip || "") + '"></label>' +
      '<div class="scene-controls"><span class="scene-state">' + (scene.provenance ? "Generated with: " + escapeHtml(scene.provenance.workflow) : "Tip: import a clip or generate via ComfyUI") +
      '</span><button class="button ghost generate-shot">Generate Moving Shot →</button></div>';
    if (scene.ai_suggestion) {
      const suggestion = document.createElement("div");
      suggestion.style.cssText = "background:#1c2d29;border:1px solid #355649;border-radius:9px;padding:12px;margin-top:13px";
      suggestion.innerHTML = '<div class="eyebrow">LOCAL QWEN SHOT SUGGESTION</div>' +
        '<p style="font-size:12px;white-space:pre-wrap;overflow-wrap:anywhere">' +
        escapeHtml(scene.ai_suggestion) + '</p>' +
        '<button class="button ghost use-suggestion">Apply Suggested Direction</button>';
      const controls = article.querySelector(".scene-controls");
      article.insertBefore(suggestion, controls);
      suggestion.querySelector(".use-suggestion").onclick = () => {
        scene.prompt = scene.ai_suggestion;
        article.querySelector(".scene-prompt").value = scene.prompt;
        toast("AI suggestion applied locally. Click Save Changes to keep it.");
      };
    }
    article.querySelector(".scene-script").oninput = (e) => scene.script = e.target.value;
    article.querySelector(".scene-prompt").oninput = (e) => scene.prompt = e.target.value;
    article.querySelector(".scene-negative").oninput = (e) => scene.negative_prompt = e.target.value;
    article.querySelector(".scene-clip").oninput = (e) => scene.clip = e.target.value;
    article.querySelector(".generate-shot").onclick = async () => {
      const workflow = byId("workflowSelect").value;
      if (!workflow) return toast("Install a ComfyUI API workflow first (see right panel).", true);
      try {
        await saveSeries(false);
        const result = await api("/api/series/" + state.series.id + "/episodes/" +
          episode.id + "/scenes/" + scene.id + "/generate", "POST", { workflow });
        state.jobs[result.job_id] = "queued";
        toast("Real AI video job queued: " + result.job_id + ". Open ComfyUI to view model execution.");
        refreshJobs();
      } catch (error) { toast(error.message, true); }
    };
    sceneList.appendChild(article);
  });
  const preview = byId("renderPreview");
  preview.hidden = !episode.render_path;
  if (episode.render_path) {
    const url = "/api/export/" + state.series.id + "/" + episode.id;
    byId("episodeVideo").src = url;
    byId("downloadVideo").href = url;
    byId("downloadVideo").download = state.series.title.replace(/[^a-z0-9-_]+/gi, "_") +
      "_episode_" + episode.number + ".mp4";
  }
}

function setupTabs() {
  const sections = ["episodes", "bible", "source"];
  document.querySelectorAll(".tab").forEach((button) => {
    button.onclick = () => {
      document.querySelectorAll(".tab").forEach(b => b.classList.toggle("active", b === button));
      sections.forEach(name => byId(name === "episodes" ? "episodeTab" : name + "Tab").hidden =
        name !== button.dataset.tab);
    };
  });
}

async function refreshHealth() {
  const info = await api("/api/health");
  const area = byId("healthCards");
  area.innerHTML = "";
  [["FFmpeg / Video Export", info.ffmpeg], ["Ollama / Story AI", info.ollama],
    ["ComfyUI / Moving Video", info.comfyui]].forEach(([label, isReady]) => {
      const row = document.createElement("div");
      row.className = "ready-row";
      row.innerHTML = "<div><strong>" + escapeHtml(label) +
        "</strong><small>" + (isReady ? "Connected and available" : "Not connected") +
        '</small></div><span class="light ' + (isReady ? "" : "off") + '"></span>';
      area.appendChild(row);
    });
  const gpu = info.gpu || {};
  const warning = document.createElement("div");
  warning.className = "ready-row";
  warning.style.display = "block";
  const good = gpu.video_generation === "not_validated";
  warning.innerHTML = '<strong style="font-size:12px">GPU / AI-video preflight</strong>' +
    '<small style="display:block;line-height:1.5;color:' +
    (good ? 'var(--accent)' : 'var(--warning)') + '">' +
    escapeHtml(gpu.message || "No GPU assessment available") + '</small>';
  area.appendChild(warning);
  const note = document.createElement("p");
  note.className = "tiny-note";
  note.textContent = info.comfyui_note || "Video generation is not verified.";
  area.appendChild(note);
  byId("serverStatus").textContent = "● Local editor online (generation unverified)";
}

async function refreshModels() {
  const models = await api("/api/models");
  const box = byId("modelCatalog");
  box.innerHTML = "";
  models.forEach(model => {
    const row = document.createElement("div");
    row.className = "model-row";
    row.innerHTML = '<a href="' + escapeHtml(model.url) + '" target="_blank" rel="noopener noreferrer"><strong>' +
      escapeHtml(model.id.split("/").pop()) + "</strong><small>" +
      escapeHtml(model.task) + "</small></a><small>" + escapeHtml(model.license) + "</small>";
    box.appendChild(row);
  });
}

async function refreshWorkflows() {
  state.workflows = await api("/api/workflows");
  const selection = byId("workflowSelect");
  const previous = selection.value;
  selection.innerHTML = '<option value="">Select a local workflow...</option>';
  state.workflows.forEach(name => {
    const item = document.createElement("option");
    item.value = name; item.textContent = name;
    selection.appendChild(item);
  });
  selection.value = state.workflows.includes(previous) ? previous : (state.workflows[0] || "");
}

async function refreshJobs() {
  const jobs = await api("/api/jobs");
  const box = byId("jobsList");
  box.innerHTML = "";
  if (!jobs.length) box.innerHTML = '<div class="muted">No background jobs.</div>';
  jobs.slice().reverse().forEach(job => {
    const row = document.createElement("div");
    row.className = "job";
    row.innerHTML = "<strong>" + escapeHtml(job.type) + " · " + escapeHtml(job.status) +
      "</strong><span>" + escapeHtml(job.detail || job.id) + "</span>";
    box.appendChild(row);
    if (state.jobs[job.id] && state.jobs[job.id] !== job.status && job.status === "completed" && state.series) {
      loadSeries(state.series.id);
      toast("Job completed: " + job.type + ". Footage/exports refreshed.");
    }
    if (state.jobs[job.id] && state.jobs[job.id] !== job.status && job.status === "failed") {
      toast("Job failed: " + job.detail, true);
    }
    state.jobs[job.id] = job.status;
  });
}

async function init() {
  setupTabs();
  byId("newButton").onclick = newProjectView;
  byId("seriesForm").onsubmit = async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(form.entries());
    const button = byId("createButton");
    button.disabled = true;
    try {
      const project = await api("/api/series", "POST", payload);
      state.episodeId = null;
      await loadSeries(project.id);
      toast("Series created with " + project.episodes.length + " editable episode(s).");
    } catch (error) { toast(error.message, true); }
    finally { button.disabled = false; }
  };
  byId("saveSeries").onclick = () => saveSeries().catch(e => toast(e.message, true));
  byId("saveBible").onclick = async () => {
    try {
      const characters = JSON.parse(byId("characters").value || "[]");
      if (!Array.isArray(characters)) throw new Error("Characters must be a JSON array");
      state.series.bible = { ...state.series.bible, characters,
        world: byId("world").value, style: byId("style").value, canon: byId("canon").value };
      await saveSeries();
    } catch (error) { toast("Series Bible: " + error.message, true); }
  };
  byId("copyScript").onclick = async () => {
    try { await navigator.clipboard.writeText(state.series.storyline); toast("Original story copied."); }
    catch { toast("Could not copy. Open the Original Story tab.", true); }
  };
  byId("renderButton").onclick = async () => {
    try {
      await saveSeries(false);
      const result = await api("/api/series/" + state.series.id + "/episodes/" +
        state.episodeId + "/render", "POST", {});
      state.jobs[result.job_id] = "queued";
      toast("Episode rendering queued: " + result.job_id);
      refreshJobs();
    } catch (error) { toast(error.message, true); }
  };
  byId("installWorkflow").onclick = async () => {
    try {
      const graph = JSON.parse(byId("workflowText").value);
      await api("/api/workflows", "POST", { name: byId("workflowName").value, graph });
      await refreshWorkflows();
      toast("ComfyUI API workflow installed locally. Your model must also be configured in ComfyUI.");
    } catch (error) { toast(error.message, true); }
  };
  await Promise.all([refreshLibrary(), refreshHealth(), refreshModels(), refreshWorkflows(), refreshJobs()]);
  setInterval(() => refreshJobs().catch(() => {}), 3500);
  setInterval(() => refreshHealth().catch(() => {}), 18000);
}
init().catch((error) => toast(error.message, true));
