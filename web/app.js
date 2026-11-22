"use strict";
const state = { series: null, projects: [], episodeId: null, workflows: [], jobs: {}, dirty: false };
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
    state.dirty = false;
    renderAssets();
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
  state.dirty = false;
  if (showToast) toast("Series and all edited scenes saved locally.");
}

function renderAssets() {
  const project = state.series;
  if (!project) return;
  const list = byId("assetLibraryList");
  const replace = byId("assetReplace");
  list.replaceChildren();
  replace.innerHTML = '<option value="">New ingredient</option>';
  (project.assets || []).forEach(asset => {
    const opt = document.createElement("option");
    opt.value = asset.id;
    opt.textContent = asset.title + " · v" + asset.version;
    replace.appendChild(opt);
    const row = document.createElement("div");
    row.className = "asset-library-row";
    const picture = document.createElement("img");
    picture.src = "/api/assets/" + project.id + "/" + asset.id;
    picture.alt = asset.title;
    picture.loading = "lazy";
    const caption = document.createElement("div");
    caption.innerHTML = "<strong>" + escapeHtml(asset.title) +
      " · v" + asset.version + "</strong><small>" + escapeHtml(asset.rights) +
      " · " + escapeHtml(asset.id) + "</small><p>" + escapeHtml(asset.credit || "No source notes") +
      "</p><small>SHA256: " + escapeHtml(asset.sha256.slice(0, 16)) +
      "… · pinned version" + (asset.parent_asset_id ? " (replaces previous asset)" : "") + "</small>";
    row.append(picture, caption);
    list.appendChild(row);
  });
  if (!(project.assets || []).length) list.innerHTML = '<p class="muted">Import your first original or licensed image above.</p>';
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
  titleInput.oninput = () => { episode.title = titleInput.value; state.dirty = true; };
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
  const preflight = document.createElement("button");
  preflight.className = "button ghost";
  preflight.style.margin = "10px 0 0 10px";
  preflight.textContent = "Check Episode Quality";
  const reportBox = document.createElement("div");
  reportBox.className = "preflight-report";
  preflight.onclick = async () => {
    try {
      await saveSeries(false);
      const report = await api("/api/series/" + state.series.id +
        "/episodes/" + episode.id + "/preflight");
      reportBox.hidden = false;
      const items = report.findings.map(item => {
        const cls = item.level === "blocker" ? "fail" : "warn";
        return '<div class="preflight-row ' + cls + '"><b>' +
          escapeHtml(item.level.toUpperCase()) + (item.scene ? " · SHOT " + item.scene : "") +
          '</b><span>' + escapeHtml(item.message) + "</span></div>";
      }).join("");
      reportBox.innerHTML = "<strong>" + (report.can_render ?
        "TECHNICAL PREFLIGHT READY — HUMAN REVIEW STILL REQUIRED" :
        "EXPORT BLOCKED UNTIL FIXED") + "</strong><p>" +
        escapeHtml(report.duration_estimate_seconds) + " seconds estimated · " +
        escapeHtml(report.timing_note) + "</p>" +
        (items || '<p>No machine-detectable issues. Watch your final episode to verify quality.</p>');
    } catch (error) { toast(error.message, true); }
  };
  head.appendChild(preflight);
  head.appendChild(reportBox);
  reportBox.hidden = true;
  const music = document.createElement("div");
  music.className = "storyboard-music";
  music.innerHTML = '<label>Optional licensed background music (absolute local path)' +
    '<input type="text" class="storyboard-music-path" placeholder="C:\\Audio\\instrumental.mp3" value="' +
    escapeHtml(episode.soundtrack || "") + '"></label>' +
    '<label class="music-confirm"><input type="checkbox" class="storyboard-music-rights"' +
    (episode.soundtrack_rights_confirmed ? " checked" : "") +
    '> I own or have permission to use this soundtrack</label>';
  head.appendChild(music);
  music.querySelector(".storyboard-music-path").oninput = e => {
    episode.soundtrack = e.target.value; state.dirty = true;
  };
  music.querySelector(".storyboard-music-rights").onchange = e => {
    episode.soundtrack_rights_confirmed = e.target.checked; state.dirty = true;
  };
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
      '<label>Optional local narration audio (.wav, .mp3, .m4a, .flac, .ogg)<input class="scene-narration" placeholder="C:\\Voices\\episode1-shot1.wav" value="' + escapeHtml(scene.narration || "") + '"></label>' +
      '<label>Optional approved character reference image (.png, .jpg, .webp)<input class="scene-reference" placeholder="C:\\Images\\maria_reference.png" value="' + escapeHtml(scene.reference_image || "") + '"></label>' +
      '<label>Character names (comma-separated, for canon prompt)<input class="scene-characters" placeholder="Maria, Juan" value="' + escapeHtml((scene.character_ids || []).join(", ")) + '"></label>' +
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
        state.dirty = true;
        article.querySelector(".scene-prompt").value = scene.prompt;
        toast("AI suggestion applied locally. Click Save Changes to keep it.");
      };
    }
    article.querySelector(".scene-script").oninput = (e) => { scene.script = e.target.value; state.dirty = true; };
    article.querySelector(".scene-prompt").oninput = (e) => { scene.prompt = e.target.value; state.dirty = true; };
    article.querySelector(".scene-negative").oninput = (e) => { scene.negative_prompt = e.target.value; state.dirty = true; };
    article.querySelector(".scene-clip").oninput = (e) => { scene.clip = e.target.value; state.dirty = true; };
    article.querySelector(".scene-narration").oninput = (e) => { scene.narration = e.target.value; state.dirty = true; };
    article.querySelector(".scene-reference").oninput = (e) => { scene.reference_image = e.target.value; state.dirty = true; };
    article.querySelector(".scene-characters").oninput = (e) => { scene.character_ids =
      e.target.value.split(",").map(name => name.trim()).filter(Boolean); state.dirty = true; };
    const canonButton = document.createElement("button");
    canonButton.className = "button ghost";
    canonButton.style.marginTop = "10px";
    canonButton.textContent = "Preview Canon-Bound AI Prompt";
    canonButton.onclick = async () => {
      try {
        await saveSeries(false);
        const result = await api("/api/series/" + state.series.id + "/episodes/" +
          episode.id + "/scenes/" + scene.id + "/prompt");
        let preview = article.querySelector(".canon-preview");
        if (!preview) {
          preview = document.createElement("pre");
          preview.className = "canon-preview";
          article.appendChild(preview);
        }
        preview.textContent = result.prompt + "\n\n" + result.note;
      } catch (error) { toast(error.message, true); }
    };
    article.appendChild(canonButton);
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
    const assignment = document.createElement("div");
    assignment.className = "asset-scene-controls";
    const imageLabel = document.createElement("label");
    imageLabel.textContent = "Pinned library image — applies to AI I2V and CPU motion storyboard";
    const imageSelector = document.createElement("select");
    imageSelector.innerHTML = '<option value="">Use legacy scene/character path (if any)</option>';
    (state.series.assets || []).forEach(asset => {
      const opt = document.createElement("option");
      opt.value = asset.id;
      opt.textContent = asset.title + " · v" + asset.version;
      imageSelector.appendChild(opt);
    });
    imageSelector.value = scene.reference_asset_id || "";
    imageSelector.onchange = e => {
      scene.reference_asset_id = e.target.value;
      state.dirty = true;
      toast("Reference pinned to this shot. Use Save Changes to persist.");
    };
    imageLabel.appendChild(imageSelector);
    const motionLabel = document.createElement("label");
    motionLabel.textContent = "CPU storyboard camera motion";
    const motionSelector = document.createElement("select");
    ["zoom_in", "zoom_out", "pan_left", "pan_right", "still"].forEach(value => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value.replace("_", " ");
      motionSelector.appendChild(option);
    });
    motionSelector.value = scene.animatic_motion || "zoom_in";
    motionSelector.onchange = e => { scene.animatic_motion = e.target.value; state.dirty = true; };
    motionLabel.appendChild(motionSelector);
    const secondsLabel = document.createElement("label");
    secondsLabel.textContent = "Storyboarding shot duration (seconds; extends to fit narration)";
    const seconds = document.createElement("input");
    seconds.type = "number"; seconds.min = "2"; seconds.max = "3600"; seconds.step = ".1";
    seconds.value = scene.duration_hint_seconds || 6;
    seconds.oninput = e => {
      scene.duration_hint_seconds = Number(e.target.value) || 6;
      state.dirty = true;
    };
    secondsLabel.appendChild(seconds);
    assignment.append(imageLabel, motionLabel, secondsLabel);
    article.appendChild(assignment);
    sceneList.appendChild(article);
  });
  const motionPreview = byId("animaticPreview");
  motionPreview.hidden = !episode.animatic_path;
  if (episode.animatic_path) {
    const prefix = "/api/animatic/" + state.series.id + "/" + episode.id;
    byId("animaticVideo").src = prefix;
    const links = byId("animaticAttachments");
    links.replaceChildren();
    [
      [prefix, "Download motion storyboard (.mp4)", "storyboard.mp4"],
      [prefix + "/subtitles", "Download estimated captions (.srt)", "estimated.srt"],
      [prefix + "/quality", "Technical QA (.json)", "storyboard-QA.json"]
    ].forEach(([href, label, file]) => {
      const a = document.createElement("a");
      a.className = "button ghost";
      a.href = href;
      a.download = "episode_" + episode.number + "_" + file;
      a.textContent = label;
      links.appendChild(a);
    });
    const note = document.createElement("p");
    note.className = "muted";
    note.textContent = "Animated approved stills, not diffusion-generated footage. Captions are scene-duration estimates, not speech aligned.";
    links.appendChild(note);
  }
  const preview = byId("renderPreview");
  let attachments = byId("episodeAttachments");
  if (!attachments) {
    attachments = document.createElement("div");
    attachments.id = "episodeAttachments";
    attachments.className = "episode-attachments";
    preview.appendChild(attachments);
  }
  attachments.innerHTML = "";
  preview.hidden = !episode.render_path;
  if (episode.render_path) {
    const url = "/api/export/" + state.series.id + "/" + episode.id;
    byId("episodeVideo").src = url;
    byId("downloadVideo").href = url;
    byId("downloadVideo").download = state.series.title.replace(/[^a-z0-9-_]+/gi, "_") +
      "_episode_" + episode.number + ".mp4";
    const caption = document.createElement("a");
    caption.className = "button ghost";
    caption.href = url + "/subtitles";
    caption.download = "episode_" + episode.number + "_estimated.srt";
    caption.textContent = "Download Estimated Captions (.srt)";
    const report = document.createElement("a");
    report.className = "button ghost";
    report.href = url + "/quality";
    report.download = "episode_" + episode.number + "_technical_QA.json";
    report.textContent = "Technical QA Report";
    attachments.append(caption, report);
    const note = document.createElement("p");
    note.className = "muted";
    note.textContent = "Caption timing is proportional to scene length, not speech-aligned. Check subtitles and watch the MP4 before publishing.";
    attachments.appendChild(note);
  }
}

function setupTabs() {
  const sections = ["episodes", "bible", "assets", "source"];
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
      if (state.dirty) { toast("Job complete. Save your pending scene edits before reopening the series."); }
      else loadSeries(state.series.id);
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
  byId("assetForm").onsubmit = async event => {
    event.preventDefault();
    if (!state.series) return;
    const file = byId("assetFile").files[0];
    const rights = byId("assetRights").value;
    if (!file || !rights) return toast("Choose an image and confirm your rights.", true);
    if (file.size > 25 * 1024 * 1024) return toast("Image must be under 25 MB.", true);
    const button = byId("assetImportButton");
    button.disabled = true;
    try {
      await saveSeries(false);
      const params = new URLSearchParams({
        filename: file.name,
        title: byId("assetTitle").value,
        rights,
        credit: byId("assetCredit").value,
        replace_asset_id: byId("assetReplace").value
      });
      const response = await fetch("/api/series/" + state.series.id + "/assets-upload?" +
        params.toString(), { method: "POST", headers: { "Content-Type": "application/octet-stream" }, body: file });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Image import failed");
      byId("assetForm").reset();
      await loadSeries(state.series.id);
      document.querySelector('[data-tab="assets"]').click();
      toast("Approved image v" + result.version + " added. Existing shot assignments remain pinned.");
    } catch (error) { toast(error.message, true); }
    finally { button.disabled = false; }
  };
  byId("animaticPreflightButton").onclick = async () => {
    if (!state.series || !state.episodeId) return;
    try {
      await saveSeries(false);
      const report = await api("/api/series/" + state.series.id +
        "/episodes/" + state.episodeId + "/animatic-preflight");
      const target = byId("animaticPreflightResult");
      target.hidden = false;
      target.innerHTML = "<strong>" + (report.can_render ? "READY FOR CPU MOTION STORYBOARD" :
        "MISSING IMAGES OR AUDIO — CANNOT RENDER") + "</strong><p>" +
        escapeHtml(report.duration_estimate_seconds) + "s · " + escapeHtml(report.note) + "</p>" +
        (report.missing || []).map(f => '<div class="preflight-row fail"><b>' +
          (f.scene ? "SHOT " + f.scene : "EPISODE") + "</b><span>" +
          escapeHtml(f.message) + "</span></div>").join("");
    } catch (error) { toast(error.message, true); }
  };
  byId("animaticRenderButton").onclick = async () => {
    if (!state.series || !state.episodeId) return;
    try {
      await saveSeries(false);
      const report = await api("/api/series/" + state.series.id +
        "/episodes/" + state.episodeId + "/animatic-preflight");
      if (!report.can_render) {
        byId("animaticPreflightButton").click();
        return toast("Attach an approved image to every scene, then run Check Images.", true);
      }
      const result = await api("/api/series/" + state.series.id +
        "/episodes/" + state.episodeId + "/animatic-render", "POST", {});
      state.jobs[result.job_id] = "queued";
      toast("CPU motion storyboard queued. This is image animation, not a diffusion AI video.");
      refreshJobs();
    } catch (error) { toast(error.message, true); }
  };
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
window.addEventListener("beforeunload", event => {
  if (state.dirty) { event.preventDefault(); event.returnValue = ""; }
});
init().catch((error) => toast(error.message, true));
