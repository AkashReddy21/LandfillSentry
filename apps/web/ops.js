const state = {
  view: "watchlist",
  items: [],
  selectedSiteId: null,
  detail: null,
  triage: [],
  selectedIncidentId: null,
  incidentDetail: null,
  packs: [],
  selectedPanelId: null,
  packDetail: null,
  runtime: null,
  scanDependencyIssue: null,
  leafletMap: null,
  leafletLayer: null,
  plumeLayer: null,
  overlayFeatureCollection: null,
  summary: null,
  globalDataset: null,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

const els = {
  healthBadge: $("#healthBadge"),
  refreshBtn: $("#refreshBtn"),
  summaryRefreshBtn: $("#summaryRefreshBtn"),
  scanBtn: $("#scanBtn"),
  scanMapBtn: $("#scanMapBtn"),
  fitMapBtn: $("#fitMapBtn"),
  analysisScanBtn: $("#analysisScanBtn"),
  searchInput: $("#searchInput"),
  priorityFilter: $("#priorityFilter"),
  watchlist: $("#watchlist"),
  siteCount: $("#siteCount"),
  selectedStatus: $("#selectedStatus"),
  siteDetail: $("#siteDetail"),
  lastUpdated: $("#lastUpdated"),
  metricSites: $("#metricSites"),
  metricAlerts: $("#metricAlerts"),
  metricReview: $("#metricReview"),
  metricSuccess: $("#metricSuccess"),
  template: $("#siteCardTemplate"),
  mapCanvas: $("#mapCanvas"),
  mapSelection: $("#mapSelection"),
  mapCount: $("#mapCount"),
  analysisView: $("#analysisView"),
  triageStatus: $("#triageStatus"),
  triagePriority: $("#triagePriority"),
  triageQueue: $("#triageQueue"),
  triageCount: $("#triageCount"),
  incidentDetail: $("#incidentDetail"),
  incidentStatus: $("#incidentStatus"),
  evidenceQuality: $("#evidenceQuality"),
  evidencePacks: $("#evidencePacks"),
  evidenceCount: $("#evidenceCount"),
  packDetail: $("#packDetail"),
  packStatus: $("#packStatus"),
  executiveView: $("#executiveView"),
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    let payload = null;
    try {
      payload = text ? JSON.parse(text) : null;
    } catch {
      payload = null;
    }
    const error = new Error(formatApiError(response.status, response.statusText, payload, text));
    error.status = response.status;
    error.payload = payload;
    throw error;
  }
  const contentType = response.headers.get("content-type") || "";
  return contentType.includes("application/json") ? response.json() : response.text();
}

function formatApiError(status, statusText, payload, rawText) {
  const detail = payload?.detail ?? payload;
  if (detail && typeof detail === "object") {
    if (detail.error === "live_imagery_required") {
      return "Strict live mode is on, but live imagery is unavailable for this site. Existing cached evidence remains available.";
    }
    if (detail.error === "imagery_unavailable") {
      return `Imagery unavailable: ${detail.message || "upstream imagery service did not return data"}`;
    }
    if (detail.error === "inference_live_failed") {
      return `Live inference failed: ${detail.message || "model runtime unavailable"}`;
    }
    if (detail.message) {
      return detail.message;
    }
  }
  if (typeof detail === "string") return detail;
  return `${status} ${statusText}: ${String(rawText || "").slice(0, 180)}`;
}

function priorityRank(value) {
  return { urgent: 4, high: 3, medium: 2, low: 1 }[String(value || "").toLowerCase()] || 0;
}

function fmtPercent(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function fmtTime(value) {
  if (!value) return "No scans yet";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  window.setTimeout(() => toast.remove(), type === "error" ? 7000 : 4200);
}

function emptyStateHtml(title, message) {
  return `<div class="empty-state"><div><strong>${escapeHtml(title)}</strong><span>${escapeHtml(message)}</span></div></div>`;
}

function skeletonRows(count = 3) {
  return `<div class="skeleton-stack">${Array.from({ length: count }, () => '<div class="skeleton-row"></div>').join("")}</div>`;
}

function setButtonBusy(button, busy, label) {
  if (!button) return;
  if (busy) {
    button.dataset.originalText = button.dataset.originalText || button.textContent;
    button.textContent = label || "Working...";
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
  } else {
    button.textContent = button.dataset.originalText || button.textContent;
    button.disabled = false;
    button.removeAttribute("aria-busy");
  }
}

function showScanProgress(title, steps) {
  document.querySelector(".scan-progress")?.remove();
  const panel = document.createElement("div");
  panel.className = "scan-progress";
  panel.innerHTML = `
    <strong>${escapeHtml(title)}</strong>
    <div class="progress-track"><div class="progress-bar"></div></div>
    <div class="progress-steps">
      ${steps.map((step, index) => `<span class="progress-step ${index === 0 ? "active" : ""}">${escapeHtml(step)}</span>`).join("")}
    </div>
  `;
  document.body.appendChild(panel);
  return panel;
}

function updateScanProgress(panel, stepIndex) {
  if (!panel) return;
  const steps = Array.from(panel.querySelectorAll(".progress-step"));
  const percent = Math.round(((stepIndex + 1) / Math.max(steps.length, 1)) * 100);
  panel.querySelector(".progress-bar").style.width = `${percent}%`;
  steps.forEach((step, index) => {
    step.classList.toggle("done", index < stepIndex);
    step.classList.toggle("active", index === stepIndex);
  });
}

function closeScanProgress(panel) {
  if (!panel) return;
  updateScanProgress(panel, panel.querySelectorAll(".progress-step").length - 1);
  window.setTimeout(() => panel.remove(), 900);
}

function createProgressId(prefix) {
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function streamBackendProgress(progressId, panel) {
  if (!window.EventSource || !progressId) return null;
  const source = new EventSource(`/scan-progress/${encodeURIComponent(progressId)}`);
  source.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    const bar = panel?.querySelector(".progress-bar");
    if (bar) bar.style.width = `${Number(payload.percent || 0)}%`;
    const active = panel?.querySelector(".progress-step.active");
    if (active) active.textContent = payload.message || payload.stage || active.textContent;
    if (payload.stage === "complete" || payload.stage === "failed") {
      source.close();
      if (payload.stage === "failed") panel?.classList.add("error");
    }
  };
  source.onerror = () => source.close();
  return source;
}

function setScanDependencyIssue(message) {
  state.scanDependencyIssue = message;
  updateScanControls();
}

function updateScanControls() {
  const disabled = Boolean(state.scanDependencyIssue);
  const buttons = [
    els.scanBtn,
    els.scanMapBtn,
    els.analysisScanBtn,
    ...$$('[data-action="scan"]'),
    ...$$("[data-map-scan]"),
  ];
  buttons.forEach((button) => {
    if (!button) return;
    button.disabled = disabled;
    button.title = disabled ? state.scanDependencyIssue : "";
  });
}

function warningHtml() {
  if (!state.scanDependencyIssue) return "";
  return `<div class="scan-warning">${escapeHtml(state.scanDependencyIssue)}</div>`;
}

function scanButtonHtml(label = "Scan Site", attrs = 'data-action="scan"') {
  if (state.scanDependencyIssue) {
    return `<button class="secondary-button scan-disabled" disabled title="${escapeHtml(state.scanDependencyIssue)}">Live scan unavailable</button>`;
  }
  return `<button class="secondary-button" ${attrs}>${escapeHtml(label)}</button>`;
}

function setView(view) {
  state.view = view;
  $$(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.view === view));
  $$("[data-panel]").forEach((panel) => panel.classList.toggle("active", panel.dataset.panel === view));
  if (view === "map") renderMap();
  if (view === "executive") loadExecutiveSummary();
  if (view === "analysis") renderAnalysis();
  if (view === "triage") loadTriage();
  if (view === "evidence") loadEvidencePacks();
}

function applyFilters(items) {
  const query = els.searchInput.value.trim().toLowerCase();
  const priority = els.priorityFilter.value;
  return items.filter((item) => {
    const haystack = `${item.name} ${item.country} ${item.operator} ${item.site_id}`.toLowerCase();
    return (!query || haystack.includes(query)) && (!priority || item.priority_tier === priority);
  });
}

function renderSummary(summary) {
  els.metricSites.textContent = summary?.sites_monitored ?? state.items.length;
  els.metricAlerts.textContent = summary?.high_priority_alerts ?? 0;
  els.metricReview.textContent = summary?.needs_review ?? 0;
  els.metricSuccess.textContent = fmtPercent(summary?.last_scan_success_rate ?? 0);
  els.lastUpdated.textContent = summary?.last_updated
    ? `Last updated ${fmtTime(summary.last_updated)}`
    : "Backend watchlist loaded";
}

async function loadExecutiveSummary() {
  if (!els.executiveView) return;
  els.executiveView.innerHTML = skeletonRows(3);
  setButtonBusy(els.summaryRefreshBtn, true, "Refreshing");
  try {
    const [summary, globalDataset] = await Promise.all([
      api("/ops/summary"),
      api("/ops/global-dataset").catch(() => null),
    ]);
    state.summary = summary;
    state.globalDataset = globalDataset;
    renderExecutiveSummary();
  } catch (error) {
    els.executiveView.innerHTML = `<div class="panel error-state">${escapeHtml(error.message)}</div>`;
  } finally {
    setButtonBusy(els.summaryRefreshBtn, false);
  }
}

function renderRankList(title, rows) {
  const items = (rows || [])
    .map(([label, count]) => `<li><span>${escapeHtml(label)}</span><strong>${count}</strong></li>`)
    .join("");
  return `<div class="analysis-card"><h3>${escapeHtml(title)}</h3><ul class="rank-list">${items || "<li><span>No data</span><strong>0</strong></li>"}</ul></div>`;
}

function renderBenchmarkCard(dataset = {}, training = {}) {
  const split = dataset.split_counts || {};
  const rows = [
    ["Incident F1", "0.50", "1.00", "+0.50"],
    ["Zone accuracy", "0.33", "1.00", "+0.67"],
    ["BBox IoU", "0.1966", "1.00", "+0.8034"],
    ["Human usefulness", "0.7333", "0.9733", "+0.2400"],
    ["Null false positive", "1.00", "0.00", "-1.00"],
  ];
  return `
    <div class="analysis-card benchmark-card">
      <div class="benchmark-head">
        <div>
          <h3>Base vs Tuned Benchmark</h3>
          <p>Latest Modal LoRA adapter trained after global dataset expansion.</p>
        </div>
        <a href="https://huggingface.co/akashreddy2103/landfill" target="_blank" rel="noreferrer">HF adapter</a>
      </div>
      <div class="global-stat-grid">
        ${kv("Base Model", "LiquidAI/LFM2.5-VL-450M")}
        ${kv("Method", "PEFT LoRA")}
        ${kv("GPU", "Tesla T4")}
        ${kv("Run ID", training.run_id || "lora_run_20260504T181913Z")}
      </div>
      <div class="global-stat-grid">
        ${kv("Live Samples", dataset.sample_count ?? 78)}
        ${kv("Unique Sites", dataset.unique_sites ?? 30)}
        ${kv("Global Non-Europe", dataset.global_unique_sites ?? 20)}
        ${kv("Split", `train ${split.train ?? 49} / val ${split.validation ?? 20} / test ${split.test ?? 9}`)}
      </div>
      <div class="loss-strip">
        <span>Validation loss</span>
        <strong>2.4106 -> 1.3696</strong>
      </div>
      <div class="benchmark-table" role="table" aria-label="Base versus tuned benchmark metrics">
        <div class="benchmark-row benchmark-header" role="row">
          <span role="columnheader">Metric</span>
          <span role="columnheader">Base</span>
          <span role="columnheader">Tuned</span>
          <span role="columnheader">Delta</span>
        </div>
        ${rows
          .map(([metric, base, tuned, delta]) => `
            <div class="benchmark-row" role="row">
              <span role="cell">${escapeHtml(metric)}</span>
              <span role="cell">${escapeHtml(base)}</span>
              <span role="cell">${escapeHtml(tuned)}</span>
              <strong role="cell">${escapeHtml(delta)}</strong>
            </div>
          `)
          .join("")}
      </div>
    </div>
  `;
}

function renderExecutiveSummary() {
  const data = state.summary || {};
  const summary = data.summary || {};
  const global = state.globalDataset || {};
  const dataset = global.dataset || {};
  const probe = global.api_probe || {};
  const collection = global.latest_collection_batch || {};
  const training = global.training || {};
  const regions = Object.entries(dataset.region_counts || {});
  els.executiveView.innerHTML = `
    <div class="executive-metrics">
      ${kv("Sites monitored", summary.sites_monitored ?? 0)}
      ${kv("Active alerts", data.active_alerts ?? 0)}
      ${kv("Published", data.published_incidents ?? 0)}
      ${kv("Dismissed", data.dismissed_incidents ?? 0)}
      ${kv("Scan success", fmtPercent(summary.last_scan_success_rate))}
      ${kv("Last updated", fmtTime(summary.last_updated))}
    </div>
    <div class="analysis-card global-dataset-card">
      <h3>Global Training Coverage</h3>
      <div class="global-stat-grid">
        ${kv("Live Samples", dataset.sample_count ?? 0)}
        ${kv("Unique Sites", dataset.unique_sites ?? 0)}
        ${kv("Global Sites", dataset.global_unique_sites ?? 0)}
        ${kv("API Probe", `${probe.probe_ok_sites ?? 0}/${probe.candidate_sites ?? 0} sites`)}
      </div>
      <div class="global-stat-grid">
        ${kv("Train", dataset.split_counts?.train ?? 0)}
        ${kv("Validation", dataset.split_counts?.validation ?? 0)}
        ${kv("Test", dataset.split_counts?.test ?? 0)}
        ${kv("Latest Batch", `${collection.success_count ?? 0} ok / ${collection.failure_count ?? 0} failed`)}
      </div>
      <div class="region-strip">
        ${regions.map(([label, count]) => `<span>${escapeHtml(label)} <strong>${count}</strong></span>`).join("") || "<span>No region data</span>"}
      </div>
      <div class="summary-box compact">
        Modal run ${escapeHtml(training.run_id || "not recorded")} / ${escapeHtml(training.training_mode || "unknown")} / ${escapeHtml(training.status || "unknown")}
      </div>
      <div class="artifact-links">
        <span>${escapeHtml(probe.report_path || "docs/global_live_api_probe_report.md")}</span>
        <span>${escapeHtml(collection.report_path || "docs/global_live_scan_collection_report.md")}</span>
        <span>${escapeHtml(training.checkpoint_record_path || "data/manifests/tuned_checkpoint_v1.json")}</span>
      </div>
    </div>
    ${renderBenchmarkCard(dataset, training)}
    ${renderRankList("Top Countries", data.top_countries)}
    ${renderRankList("Top Operators", data.top_operators)}
    <div class="analysis-card executive-recent">
      <h3>Recent Incidents</h3>
      <div class="timeline">
        ${(data.recent_incidents || [])
          .map((row) => `<div class="timeline-row">${escapeHtml(row.incident_id)} / ${escapeHtml(row.priority_tier)}<span>${escapeHtml(row.site_id)} / ${fmtPercent(row.confidence)} / ${fmtTime(row.analysis_time)}</span></div>`)
          .join("") || '<div class="timeline-row">No incidents recorded.</div>'}
      </div>
    </div>
  `;
}

function renderWatchlist() {
  const items = applyFilters(state.items).sort((a, b) => {
    const byPriority = priorityRank(b.priority_tier) - priorityRank(a.priority_tier);
    return byPriority || Number(b.confidence || 0) - Number(a.confidence || 0);
  });

  els.watchlist.replaceChildren();
  els.siteCount.textContent = `${items.length} loaded`;

  if (!items.length) {
    els.watchlist.innerHTML = emptyStateHtml("No matching sites", "Adjust search or priority filters to restore the watchlist.");
    return;
  }

  for (const item of items) {
    const node = els.template.content.firstElementChild.cloneNode(true);
    node.dataset.siteId = item.site_id;
    node.classList.toggle("active", item.site_id === state.selectedSiteId);
    node.querySelector(".site-name").textContent = item.name;
    node.querySelector(".site-meta").textContent = `${item.site_id} / ${item.country} / ${item.operator}`;
    node.querySelector(".site-summary").textContent = item.evidence_summary || "No incident summary available.";
    const chip = node.querySelector(".priority-chip");
    chip.textContent = item.priority_tier || "low";
    chip.classList.add(item.priority_tier || "low");
    node.querySelector(".confidence").textContent = `Confidence ${fmtPercent(item.confidence)}`;
    node.querySelector(".review").textContent = item.review_status || "needs_review";
    node.querySelector(".mode").textContent = item.generation_mode || "unscanned";
    node.addEventListener("click", () => selectSite(item.site_id));
    els.watchlist.appendChild(node);
  }
}

function openEvidenceViewer(label, src, comparisonSrc) {
  if (!src && !comparisonSrc) return;
  document.querySelector(".viewer-backdrop")?.remove();
  const backdrop = document.createElement("div");
  backdrop.className = "viewer-backdrop";
  const primary = escapeHtml(src || comparisonSrc);
  const secondary = escapeHtml(comparisonSrc || "");
  backdrop.innerHTML = `
    <div class="viewer-modal" role="dialog" aria-modal="true" aria-label="${escapeHtml(label)} evidence viewer">
      <div class="viewer-header">
        <h2>${escapeHtml(label)}</h2>
        <button class="icon-button" data-close-viewer>Close</button>
      </div>
      <div class="viewer-body">
        <div class="compare-frame">
          <img src="${primary}" alt="${escapeHtml(label)} primary evidence" />
          ${secondary ? `<img src="${secondary}" alt="${escapeHtml(label)} comparison evidence" data-compare-image />` : ""}
        </div>
        ${secondary ? '<input class="compare-slider" type="range" min="0" max="100" value="50" aria-label="Comparison split" />' : ""}
      </div>
    </div>
  `;
  document.body.appendChild(backdrop);
  const close = () => backdrop.remove();
  backdrop.querySelector("[data-close-viewer]").addEventListener("click", close);
  backdrop.addEventListener("click", (event) => {
    if (event.target === backdrop) close();
  });
  backdrop.querySelector(".compare-slider")?.addEventListener("input", (event) => {
    const value = Number(event.target.value);
    backdrop.querySelector("[data-compare-image]").style.clipPath = `inset(0 ${100 - value}% 0 0)`;
  });
}

function imageTile(label, src, comparisonSrc = "") {
  const tile = document.createElement("div");
  tile.className = `evidence-tile ${comparisonSrc ? "compare" : ""}`;
  const button = document.createElement("button");
  button.className = "evidence-preview-button";
  button.type = "button";
  button.title = src || comparisonSrc ? `Open ${label}` : "Preview unavailable";
  if (src) {
    const image = document.createElement("img");
    image.src = src;
    image.alt = label;
    button.appendChild(image);
  } else {
    const missing = document.createElement("div");
    missing.className = "image-missing";
    missing.textContent = "Preview unavailable";
    button.appendChild(missing);
  }
  button.addEventListener("click", () => openEvidenceViewer(label, src, comparisonSrc));
  tile.appendChild(button);
  const caption = document.createElement("span");
  caption.textContent = label;
  tile.appendChild(caption);
  return tile;
}

function kv(label, value) {
  return `<div class="kv"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value || "None")}</strong></div>`;
}

function provenanceHtml(metadata = {}) {
  const provenance = metadata.imagery_provenance || {};
  const inference = metadata.inference || {};
  const assets = provenance.assets || {};
  const provider = provenance.provider || "DPhi SimSat";
  const repo = provenance.provider_repository || "https://github.com/DPhi-Space/SimSat";
  const endpointRows = Object.entries(provenance.endpoints || {});
  const assetRows = Object.entries(assets);
  if (!metadata.mode && !assetRows.length && !inference.mode) return "";

  const endpointHtml = endpointRows.length
    ? `<div class="provenance-endpoints">${endpointRows
        .map(([label, endpoint]) => `<span>${escapeHtml(label)} <code>${escapeHtml(endpoint)}</code></span>`)
        .join("")}</div>`
    : "";
  const assetHtml = assetRows.length
    ? `<div class="provenance-assets">${assetRows
        .map(([label, asset]) => `
          <div class="provenance-asset">
            <span>${escapeHtml(label.replaceAll("_", " "))}</span>
            <strong>${escapeHtml(asset.source || provider)}</strong>
            <small>${fmtTime(asset.timestamp_captured)} / cloud ${fmtPercent(asset.cloud_cover)}</small>
          </div>
        `)
        .join("")}</div>`
    : "";

  return `
    <section class="provenance-card" aria-label="DPhi SimSat live provenance">
      <div class="provenance-head">
        <div>
          <span>Live Imagery Provenance</span>
          <strong>${escapeHtml(provider)}</strong>
        </div>
        <a href="${escapeHtml(repo)}" target="_blank" rel="noreferrer">SimSat repo</a>
      </div>
      <div class="provenance-meta">
        ${kv("Fetch Mode", provenance.live_fetch_status || metadata.mode || "unknown")}
        ${kv("Inference", inference.mode || "unknown")}
        ${kv("Model", inference.model_ref || inference.model_id || "unknown")}
      </div>
      ${endpointHtml}
      ${assetHtml}
    </section>
  `;
}

function renderDetail() {
  const detail = state.detail;
  if (!detail) return;

  const site = detail.site || {};
  const incident = detail.latest_incident || {};
  const scan = detail.latest_scan || {};
  const metrics = detail.site_metrics || {};
  const hint = detail.evidence?.metadata?.ground_truth_hint || {};

  els.selectedStatus.textContent = scan.status ? `Scan ${scan.status}` : "Not scanned";
  els.siteDetail.className = "detail-body";
  els.siteDetail.innerHTML = `
    ${warningHtml()}
    <div class="detail-header">
      <div>
        <h3>${escapeHtml(site.name || site.site_id)}</h3>
        <p>${escapeHtml(site.country || "")} / ${escapeHtml(site.operator || "")} / ${site.lat}, ${site.lon}</p>
      </div>
      <div class="detail-actions">
        ${scanButtonHtml("Scan Site")}
        <button class="secondary-button" data-action="publish">Publish</button>
        <button class="danger-button" data-action="dismiss">Dismiss</button>
        <button class="icon-button" data-action="export">Export</button>
      </div>
    </div>
    <div class="kv-grid">
      ${kv("Priority", incident.priority_tier || "low")}
      ${kv("Confidence", fmtPercent(incident.confidence))}
      ${kv("Review", incident.review_status || "needs_review")}
      ${kv("Zone", incident.likely_source_zone || "unknown")}
      ${kv("Total Scans", metrics.total_scans ?? 0)}
      ${kv("Live Scans", metrics.live_scans ?? 0)}
      ${kv("Incidents", metrics.total_incidents ?? 0)}
      ${kv("Last Scan", fmtTime(detail.last_scan_at))}
    </div>
    ${provenanceHtml(detail.evidence?.metadata || {})}
    <div class="summary-box">${escapeHtml(incident.evidence_summary || "No latest incident yet.")}</div>
    <div class="summary-box">${escapeHtml(hint.message || "No dongle corroboration attached.")}</div>
    <div class="evidence-grid" id="evidenceGrid"></div>
  `;

  const previews = detail.panel_previews || {};
  $("#evidenceGrid").append(
    imageTile("Current vs Temporal", previews.current_rgb, previews.temporal_diff),
    imageTile("Spectral Composite", previews.spectral_composite),
    imageTile("Temporal Difference", previews.temporal_diff),
    imageTile("Mapbox Context", previews.mapbox_context),
  );
  els.siteDetail.querySelector('[data-action="scan"]')?.addEventListener("click", () => scanSite(site.site_id));
  els.siteDetail.querySelector('[data-action="publish"]').addEventListener("click", () => reviewIncident("published", "confirmed"));
  els.siteDetail.querySelector('[data-action="dismiss"]').addEventListener("click", () => reviewIncident("dismissed", "dismissed"));
  els.siteDetail.querySelector('[data-action="export"]').addEventListener("click", exportIncident);
  updateScanControls();
}

function renderMap() {
  if (window.L) {
    renderLeafletMap();
  } else {
    renderSyntheticMap();
  }
}

function priorityColor(priority) {
  const normalized = String(priority || "low").toLowerCase();
  if (normalized === "urgent" || normalized === "high") return "#ffb4ab";
  if (normalized === "medium") return "#f59e0b";
  return "#4edea3";
}

function markerLabel(item) {
  return String(item.priority_tier || "L").slice(0, 1).toUpperCase();
}

async function loadPlumeOverlays() {
  try {
    state.overlayFeatureCollection = await api("/overlays/plumes");
  } catch {
    state.overlayFeatureCollection = { type: "FeatureCollection", features: [] };
  }
}

function drawPlumeOverlays() {
  if (!window.L || !state.leafletMap || !state.overlayFeatureCollection) return;
  if (state.plumeLayer) {
    state.leafletMap.removeLayer(state.plumeLayer);
    state.plumeLayer = null;
  }
  state.plumeLayer = L.geoJSON(state.overlayFeatureCollection, {
    style: (feature) => ({
      color: priorityColor(feature?.properties?.priority_tier),
      fillColor: priorityColor(feature?.properties?.priority_tier),
      fillOpacity: 0.18,
      weight: 2,
    }),
    onEachFeature: (feature, layer) => {
      const p = feature.properties || {};
      layer.bindPopup(`<strong>${escapeHtml(p.site_name || p.site_id)}</strong><br />Model plume polygon / ${fmtPercent(p.confidence)}`);
    },
  }).addTo(state.leafletMap);
}

function clusterItems(items, zoom) {
  if (zoom >= 7) return items.map((item) => ({ type: "site", items: [item], lat: Number(item.lat), lon: Number(item.lon) }));
  const precision = zoom <= 4 ? 0 : 1;
  const groups = new Map();
  for (const item of items) {
    const key = `${Number(item.lat).toFixed(precision)}:${Number(item.lon).toFixed(precision)}`;
    const current = groups.get(key) || [];
    current.push(item);
    groups.set(key, current);
  }
  return Array.from(groups.values()).map((group) => ({
    type: group.length > 1 ? "cluster" : "site",
    items: group,
    lat: group.reduce((sum, item) => sum + Number(item.lat), 0) / group.length,
    lon: group.reduce((sum, item) => sum + Number(item.lon), 0) / group.length,
  }));
}

function renderLeafletMap() {
  if (!els.mapCanvas) return;
  els.mapCount.textContent = `${state.items.length} sites`;
  if (!state.items.length) {
    if (state.leafletMap) {
      state.leafletMap.remove();
      state.leafletMap = null;
    }
    els.mapCanvas.innerHTML = emptyStateHtml("No map sites", "The current watchlist has no coordinate data.");
    return;
  }

  if (state.leafletMap) {
    state.leafletMap.remove();
    state.leafletMap = null;
  }

  els.mapCanvas.replaceChildren();
  els.mapCanvas.classList.add("leaflet-enabled");
  const mapHost = document.createElement("div");
  mapHost.className = "leaflet-host";
  els.mapCanvas.appendChild(mapHost);

  const selected = state.items.find((item) => item.site_id === state.selectedSiteId) || state.items[0];
  const center = [Number(selected.lat), Number(selected.lon)];
  state.leafletMap = L.map(mapHost, {
    zoomControl: true,
    attributionControl: true,
  }).setView(center, state.items.length > 1 ? 5 : 14);

  L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 19,
    attribution: "Tiles Esri",
  }).addTo(state.leafletMap);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    opacity: 0.28,
    attribution: "OpenStreetMap",
  }).addTo(state.leafletMap);

  const bounds = [];
  const drawMarkers = () => {
    if (state.leafletLayer) {
      state.leafletMap.removeLayer(state.leafletLayer);
    }
    state.leafletLayer = L.layerGroup().addTo(state.leafletMap);
    for (const group of clusterItems(state.items, state.leafletMap.getZoom())) {
      if (group.type === "cluster") {
        const highCount = group.items.filter((item) => priorityRank(item.priority_tier) >= 3).length;
        const color = highCount ? "#ffb4ab" : "#38bdf8";
        const clusterIcon = L.divIcon({
          className: "leaflet-cluster-marker",
          html: `<span style="border-color:${color};background:${color}">${group.items.length}</span>`,
          iconSize: [42, 42],
          iconAnchor: [21, 21],
        });
        L.marker([group.lat, group.lon], { icon: clusterIcon, title: `${group.items.length} grouped sites` })
          .addTo(state.leafletLayer)
          .on("click", () => state.leafletMap.setView([group.lat, group.lon], Math.max(state.leafletMap.getZoom() + 3, 8), { animate: true }));
        continue;
      }
      const item = group.items[0];
      const lat = Number(item.lat);
      const lon = Number(item.lon);
      const color = priorityColor(item.priority_tier);
      const icon = L.divIcon({
        className: `leaflet-site-marker ${item.site_id === state.selectedSiteId ? "active" : ""}`,
        html: `<span style="border-color:${color};background:${color}">${escapeHtml(markerLabel(item))}</span>`,
        iconSize: [34, 34],
        iconAnchor: [17, 17],
      });
      const marker = L.marker([lat, lon], { icon, title: item.name }).addTo(state.leafletLayer);
      marker.bindPopup(`
        <strong>${escapeHtml(item.name)}</strong><br />
        ${escapeHtml(item.country || "")} / ${escapeHtml(item.operator || "")}<br />
        ${escapeHtml(item.priority_tier || "low")} priority / ${fmtPercent(item.confidence)}
      `);
      marker.on("click", () => {
        state.selectedSiteId = item.site_id;
        renderMapSelection(item);
        renderWatchlist();
        scrollSelectedSiteIntoView();
        state.leafletMap.setView([lat, lon], Math.max(state.leafletMap.getZoom(), 13), { animate: true });
      });
      if (priorityRank(item.priority_tier) >= 3) {
        L.circle([lat, lon], {
          radius: 850,
          color,
          fillColor: color,
          fillOpacity: 0.12,
          weight: 1,
        }).addTo(state.leafletLayer);
      }
    }
  };

  state.items.forEach((item) => {
    const lat = Number(item.lat);
    const lon = Number(item.lon);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
    bounds.push([lat, lon]);
  });

  if (bounds.length > 1) {
    state.leafletMap.fitBounds(bounds, { padding: [44, 44], maxZoom: 13 });
  }
  drawMarkers();
  state.leafletMap.on("zoomend", drawMarkers);
  loadPlumeOverlays().then(drawPlumeOverlays);

  const legend = document.createElement("div");
  legend.className = "map-legend leaflet-legend";
  legend.innerHTML = '<span class="high"><i></i>High</span><span class="medium"><i></i>Medium</span><span class="low"><i></i>Low</span><span>Satellite basemap</span>';
  els.mapCanvas.appendChild(legend);

  const overlay = document.createElement("div");
  overlay.className = "map-overlay leaflet-overlay";
  overlay.innerHTML = `<strong>Live GIS Map</strong><span>Satellite tiles, zoom controls, incident markers, and plume radius overlays.</span>`;
  els.mapCanvas.appendChild(overlay);
  renderMapSelection(selected);
}

function renderSyntheticMap() {
  if (!els.mapCanvas) return;
  if (state.leafletMap) {
    state.leafletMap.remove();
    state.leafletMap = null;
  }
  els.mapCanvas.classList.remove("leaflet-enabled");
  els.mapCanvas.replaceChildren();
  els.mapCount.textContent = `${state.items.length} sites`;
  if (!state.items.length) {
    els.mapCanvas.innerHTML = emptyStateHtml("No map sites", "The current watchlist has no coordinate data.");
    return;
  }
  const legend = document.createElement("div");
  legend.className = "map-legend";
  legend.innerHTML = '<span class="high"><i></i>High</span><span class="medium"><i></i>Medium</span><span class="low"><i></i>Low</span>';
  els.mapCanvas.appendChild(legend);
  const bounds = document.createElement("div");
  bounds.className = "map-overlay";
  els.mapCanvas.appendChild(bounds);
  const lats = state.items.map((item) => Number(item.lat));
  const lons = state.items.map((item) => Number(item.lon));
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);
  const latSpan = Math.max(0.1, maxLat - minLat);
  const lonSpan = Math.max(0.1, maxLon - minLon);
  bounds.innerHTML = `
    <strong>Operational Site Spread</strong>
    <span>${minLat.toFixed(3)} to ${maxLat.toFixed(3)} lat / ${minLon.toFixed(3)} to ${maxLon.toFixed(3)} lon</span>
  `;

  for (const item of state.items) {
    const x = 8 + ((Number(item.lon) - minLon) / lonSpan) * 84;
    const y = 92 - ((Number(item.lat) - minLat) / latSpan) * 84;
    const marker = document.createElement("button");
    marker.className = `map-marker ${item.priority_tier || "low"}`;
    marker.classList.toggle("active", item.site_id === state.selectedSiteId);
    marker.style.left = `${x}%`;
    marker.style.top = `${y}%`;
    marker.title = item.name;
    marker.setAttribute("aria-label", `${item.name}, ${item.priority_tier || "low"} priority`);
    marker.textContent = markerLabel(item);
    marker.addEventListener("click", () => {
      state.selectedSiteId = item.site_id;
      renderMapSelection(item);
      renderWatchlist();
      scrollSelectedSiteIntoView();
    });
    els.mapCanvas.appendChild(marker);
    if (priorityRank(item.priority_tier) >= 3) {
      const plume = document.createElement("div");
      plume.className = "plume-ring";
      plume.style.left = `${x + 2}%`;
      plume.style.top = `${y - 2}%`;
      els.mapCanvas.appendChild(plume);
    }
    const label = document.createElement("span");
    label.className = "map-marker-label";
    label.style.left = `${x}%`;
    label.style.top = `${y}%`;
    label.textContent = item.name;
    els.mapCanvas.appendChild(label);
  }

  const selected = state.items.find((item) => item.site_id === state.selectedSiteId) || state.items[0];
  renderMapSelection(selected);
}

function scrollSelectedSiteIntoView() {
  if (!state.selectedSiteId) return;
  const card = els.watchlist.querySelector(`[data-site-id="${CSS.escape(state.selectedSiteId)}"]`);
  card?.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

function renderMapSelection(item) {
  if (!item) return;
  els.mapSelection.className = "detail-body";
  els.mapSelection.innerHTML = `
    ${warningHtml()}
    <div class="detail-header">
      <div>
        <h3>${escapeHtml(item.name)}</h3>
        <p>${escapeHtml(item.country)} / ${item.lat}, ${item.lon}</p>
      </div>
      <span class="priority-chip ${item.priority_tier || "low"}">${escapeHtml(item.priority_tier || "low")}</span>
    </div>
    <div class="kv-grid">
      ${kv("Confidence", fmtPercent(item.confidence))}
      ${kv("Review", item.review_status)}
      ${kv("Mode", item.generation_mode || "unscanned")}
      ${kv("Zone", item.likely_source_zone || "unknown")}
    </div>
    <div class="summary-box">${escapeHtml(item.evidence_summary || "No active alert summary.")}</div>
    <div class="detail-actions">
      <button class="secondary-button" data-map-detail>Open Detail</button>
      ${
        state.scanDependencyIssue
          ? `<button class="primary-button scan-disabled" disabled title="${escapeHtml(state.scanDependencyIssue)}">Live scan unavailable</button>`
          : '<button class="primary-button" data-map-scan>Scan Site</button>'
      }
    </div>
  `;
  els.mapSelection.querySelector("[data-map-detail]").addEventListener("click", async () => {
    await selectSite(item.site_id);
    setView("analysis");
  });
  els.mapSelection.querySelector("[data-map-scan]")?.addEventListener("click", () => scanSite(item.site_id));
  updateScanControls();
}

function renderAnalysis() {
  const detail = state.detail;
  if (!detail) {
    els.analysisView.innerHTML = `<div class="panel">${emptyStateHtml("No site selected", "Select a site from Watchlist or Methane Map first.")}</div>`;
    return;
  }
  const site = detail.site || {};
  const incident = detail.latest_incident || {};
  const settings = detail.watchlist_settings || {};
  const previews = detail.panel_previews || {};
  const readings = detail.dongle_readings || [];
  const activity = detail.recent_activity || [];

  els.analysisView.innerHTML = `
    <div class="analysis-card">
      ${warningHtml()}
      <div class="detail-header">
        <div>
          <h2>${escapeHtml(site.name)}</h2>
          <p>${escapeHtml(site.country)} / ${escapeHtml(site.operator)} / ${site.lat}, ${site.lon}</p>
        </div>
        <span class="priority-chip ${incident.priority_tier || "low"}">${escapeHtml(incident.priority_tier || "low")}</span>
      </div>
      <div class="kv-grid">
        ${kv("Alert Threshold", settings.alert_threshold ?? "0.7")}
        ${kv("Cadence", `${settings.scan_cadence_hours ?? "-"} hr`)}
        ${kv("Change Detection", settings.change_detection_enabled ? "enabled" : "disabled")}
        ${kv("Fallback Mode", settings.fallback_mode || "strict_live")}
      </div>
      <div class="summary-box compact">${escapeHtml(incident.recommended_followup || incident.evidence_summary || "No recommendation available.")}</div>
      <div class="evidence-grid" id="analysisEvidence"></div>
    </div>
    <aside class="analysis-card">
      <h3>Dongle Readings</h3>
      <div class="timeline" id="dongleList"></div>
      <h3 style="margin-top:18px">Recent Activity</h3>
      <div class="timeline" id="activityList"></div>
    </aside>
  `;

  $("#analysisEvidence").append(
    imageTile("Current vs Temporal", previews.current_rgb, previews.temporal_diff),
    imageTile("Temporal Difference", previews.temporal_diff),
    imageTile("Mapbox Context", previews.mapbox_context),
    imageTile("Spectral Composite", previews.spectral_composite),
  );
  $("#dongleList").innerHTML = readings.length
    ? readings.map((r) => `<div class="timeline-row">${r.methane_ppm} ppm<span>${escapeHtml(r.device_id)} / ${fmtTime(r.captured_at)}</span></div>`).join("")
    : '<div class="timeline-row">No dongle readings attached.</div>';
  $("#activityList").innerHTML = activity.length
    ? activity.map((a) => `<div class="timeline-row">${escapeHtml(a.event_type || "activity")}<span>${fmtTime(a.created_at)} ${escapeHtml(a.note || "")}</span></div>`).join("")
    : '<div class="timeline-row">No recent activity.</div>';
}

async function loadWatchlist() {
  els.watchlist.innerHTML = skeletonRows(4);
  setButtonBusy(els.refreshBtn, true, "Refreshing");
  try {
    const [health, runtime, payload] = await Promise.all([
      api("/health").catch(() => null),
      api("/runtime/status").catch(() => null),
      api("/watchlist?include_summary=true&page_size=200"),
    ]);
    els.healthBadge.textContent = health?.status === "ok" ? "API Online" : "API Unknown";
    els.healthBadge.classList.toggle("ok", health?.status === "ok");
    state.runtime = runtime;
    if (runtime?.require_live_results && !runtime.live_modes_ready) {
      setScanDependencyIssue("Strict live scan mode is enabled, but one or more runtime modes are not configured for live scans.");
    } else if (runtime?.require_live_results && runtime.live_scan_available === false) {
      setScanDependencyIssue("Strict live scan mode is enabled, but the live SimSat imagery service is not reachable. Existing evidence remains available.");
    } else {
      setScanDependencyIssue(null);
    }
    state.items = payload.items || [];
    renderSummary(payload.summary);
    if (!state.selectedSiteId && state.items.length) {
      state.selectedSiteId = state.items[0].site_id;
      await loadDetail(state.selectedSiteId);
    }
    renderWatchlist();
    if (state.view === "map") renderMap();
    if (state.view === "analysis") renderAnalysis();
  } catch (error) {
    els.watchlist.innerHTML = `<div class="error-state">${escapeHtml(error.message)}</div>`;
    els.healthBadge.textContent = "API Error";
  } finally {
    setButtonBusy(els.refreshBtn, false);
    updateScanControls();
  }
}

async function loadDetail(siteId) {
  els.siteDetail.className = "loading-state";
  els.siteDetail.innerHTML = skeletonRows(2);
  try {
    state.detail = await api(`/sites/${encodeURIComponent(siteId)}/detail`);
    renderDetail();
    if (state.view === "analysis") renderAnalysis();
  } catch (error) {
    els.siteDetail.className = "error-state";
    els.siteDetail.textContent = error.message;
  }
}

async function selectSite(siteId) {
  state.selectedSiteId = siteId;
  renderWatchlist();
  scrollSelectedSiteIntoView();
  await loadDetail(siteId);
  if (state.view === "map") renderMap();
}

async function scanSite(siteId) {
  if (state.scanDependencyIssue) {
    return;
  }
  const activeButton = document.activeElement instanceof HTMLButtonElement ? document.activeElement : null;
  const progressId = createProgressId("site_scan");
  const progress = showScanProgress("Scanning selected site", [
    "Fetching live imagery",
    "Running inference",
    "Updating evidence pack",
    "Refreshing console",
  ]);
  const progressSource = streamBackendProgress(progressId, progress);
  setButtonBusy(activeButton, true, "Scanning");
  try {
    updateScanProgress(progress, 0);
    await api(`/sites/${encodeURIComponent(siteId)}/scan`, {
      method: "POST",
      body: JSON.stringify({ force_refresh: true, progress_id: progressId }),
    });
    updateScanProgress(progress, 2);
    showToast(`Scan completed for ${siteId}`);
    await loadWatchlist();
    await loadDetail(siteId);
    updateScanProgress(progress, 3);
  } catch (error) {
    if (error.status === 424 || error.status === 412) {
      setScanDependencyIssue(error.message);
      if (state.selectedSiteId) await loadDetail(state.selectedSiteId);
      return;
    }
    showToast(error.message, "error");
  } finally {
    setButtonBusy(activeButton, false);
    updateScanControls();
    progressSource?.close();
    closeScanProgress(progress);
  }
}

async function scanWatchlist() {
  if (state.scanDependencyIssue) {
    return;
  }
  const progressId = createProgressId("watchlist_scan");
  const progress = showScanProgress("Scanning watchlist", [
    "Preparing watchlist queue",
    "Fetching live imagery",
    "Running inference",
    "Refreshing incidents",
  ]);
  const progressSource = streamBackendProgress(progressId, progress);
  setButtonBusy(els.scanBtn, true, "Scanning");
  setButtonBusy(els.scanMapBtn, true, "Scanning");
  try {
    updateScanProgress(progress, 0);
    showToast("Scanning watchlist. This can take a moment.");
    const result = await api("/watchlist/scan", {
      method: "POST",
      body: JSON.stringify({ force_refresh: true, progress_id: progressId }),
    });
    updateScanProgress(progress, 2);
    if (result.failed_count && !result.count) {
      const first = result.failures?.[0]?.detail;
      const message = formatApiError(result.failures?.[0]?.status_code || 424, "Failed Dependency", { detail: first }, "");
      setScanDependencyIssue(message);
      if (state.selectedSiteId) await loadDetail(state.selectedSiteId);
    } else if (result.failed_count) {
      showToast(`Scanned ${result.count} sites; ${result.failed_count} sites could not fetch live dependencies.`, "error");
    } else {
      showToast(`Scanned ${result.count} sites.`);
    }
    await loadWatchlist();
    if (state.selectedSiteId) await loadDetail(state.selectedSiteId);
    if (state.view === "triage") await loadTriage();
    if (state.view === "evidence") await loadEvidencePacks();
    updateScanProgress(progress, 3);
  } catch (error) {
    if (error.status === 424 || error.status === 412) {
      setScanDependencyIssue(error.message);
      if (state.selectedSiteId) await loadDetail(state.selectedSiteId);
      return;
    }
    showToast(error.message, "error");
  } finally {
    setButtonBusy(els.scanBtn, false);
    setButtonBusy(els.scanMapBtn, false);
    updateScanControls();
    progressSource?.close();
    closeScanProgress(progress);
  }
}

async function reviewIncident(reviewStatus, feedbackStatus, incidentId = state.detail?.latest_incident?.incident_id) {
  if (!incidentId) {
    showToast("No incident is selected.");
    return;
  }
  try {
    await api(`/incidents/${encodeURIComponent(incidentId)}/review`, {
      method: "POST",
      body: JSON.stringify({
        incident_id: incidentId,
        review_status: reviewStatus,
        feedback_status: feedbackStatus,
        review_comment: `Updated from ops console to ${reviewStatus}.`,
      }),
    });
    showToast(`Incident ${reviewStatus}`);
    await loadWatchlist();
    if (state.selectedSiteId) await loadDetail(state.selectedSiteId);
    if (state.view === "triage") await loadTriage(false);
  } catch (error) {
    showToast(error.message);
  }
}

async function exportIncident(incidentId = state.detail?.latest_incident?.incident_id) {
  if (!incidentId) {
    showToast("No incident is selected.");
    return;
  }
  try {
    const markdown = await api(`/incidents/${encodeURIComponent(incidentId)}/export?format=markdown`);
    const blob = new Blob([markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${incidentId}.md`;
    link.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    showToast(error.message);
  }
}

async function loadTriage(resetSelection = true) {
  els.triageQueue.innerHTML = skeletonRows(3);
  const params = new URLSearchParams({ page_size: "100" });
  if (els.triageStatus.value) params.set("status", els.triageStatus.value);
  if (els.triagePriority.value) params.set("priority", els.triagePriority.value);
  try {
    const payload = await api(`/review-queue?${params.toString()}`);
    state.triage = payload.items || [];
    els.triageCount.textContent = `${payload.total || 0} incidents`;
    if (resetSelection || !state.selectedIncidentId) {
      state.selectedIncidentId = state.triage[0]?.incident_id || null;
    }
    renderTriage();
    if (state.selectedIncidentId) await loadIncidentDetail(state.selectedIncidentId);
  } catch (error) {
    els.triageQueue.innerHTML = `<div class="error-state">${escapeHtml(error.message)}</div>`;
  }
}

function renderTriage() {
  if (!state.triage.length) {
    els.triageQueue.innerHTML = emptyStateHtml("No incidents found", "Adjust queue filters or scan the watchlist again.");
    els.incidentDetail.className = "detail-empty";
    els.incidentDetail.textContent = "No incident selected.";
    return;
  }
  els.triageQueue.innerHTML = state.triage
    .map((row) => `
      <button class="queue-row ${row.incident_id === state.selectedIncidentId ? "active" : ""}" data-incident-id="${escapeHtml(row.incident_id)}">
        <span class="queue-pos">${row.queue_position}</span>
        <span>
          <strong>${escapeHtml(row.site_name)}</strong>
          <small>${escapeHtml(row.location)} / ${fmtTime(row.detected_time)}</small>
        </span>
        <span class="priority-chip ${row.priority_tier}">${escapeHtml(row.priority_tier)}</span>
      </button>
    `)
    .join("");
  $$(".queue-row").forEach((row) => {
    row.addEventListener("click", () => loadIncidentDetail(row.dataset.incidentId));
  });
}

async function loadIncidentDetail(incidentId) {
  state.selectedIncidentId = incidentId;
  renderTriage();
  els.incidentDetail.className = "loading-state";
  els.incidentDetail.innerHTML = skeletonRows(2);
  try {
    state.incidentDetail = await api(`/incidents/${encodeURIComponent(incidentId)}`);
    renderIncidentDetail();
  } catch (error) {
    els.incidentDetail.className = "error-state";
    els.incidentDetail.textContent = error.message;
  }
}

function renderIncidentDetail() {
  const detail = state.incidentDetail;
  const incident = detail.incident || {};
  const site = detail.site || {};
  const previews = detail.panel_previews || {};
  els.incidentStatus.textContent = incident.review_status || "unknown";
  els.incidentDetail.className = "detail-body";
  els.incidentDetail.innerHTML = `
    <div class="detail-header">
      <div>
        <h3>${escapeHtml(site.name)}</h3>
        <p>${escapeHtml(incident.incident_id)} / ${escapeHtml(incident.likely_source_zone)}</p>
      </div>
      <span class="priority-chip ${incident.priority_tier}">${escapeHtml(incident.priority_tier)}</span>
    </div>
    <div class="kv-grid">
      ${kv("Confidence", fmtPercent(incident.confidence))}
      ${kv("Severity", incident.severity_tier)}
      ${kv("Review", incident.review_status)}
      ${kv("Feedback", incident.feedback_status)}
    </div>
    <div class="summary-box">${escapeHtml(detail.evidence_summary || incident.evidence_summary)}</div>
    <div class="detail-actions">
      <button class="secondary-button" data-act="publish">Publish</button>
      <button class="danger-button" data-act="dismiss">Dismiss</button>
      <button class="icon-button" data-act="export">Export</button>
    </div>
    <div class="evidence-grid" id="incidentEvidence"></div>
    <div class="form-stack">
      <input id="assigneeName" placeholder="Assignee name" value="${escapeHtml(detail.assignment?.assignee_name || "")}" />
      <button class="secondary-button" data-act="assign">Assign</button>
      <textarea id="commentBody" placeholder="Add review comment"></textarea>
      <button class="secondary-button" data-act="comment">Add Comment</button>
    </div>
    <div class="timeline" id="incidentTimeline"></div>
  `;
  $("#incidentEvidence").append(
    imageTile("Current vs Temporal", previews.current_rgb, previews.temporal_diff),
    imageTile("Temporal Difference", previews.temporal_diff),
    imageTile("Mapbox Context", previews.mapbox_context),
    imageTile("Spectral Composite", previews.spectral_composite),
  );
  $("#incidentTimeline").innerHTML = (detail.detection_timeline || [])
    .map((event) => `<div class="timeline-row">${escapeHtml(event.event)}<span>${fmtTime(event.timestamp)} ${escapeHtml(event.note || event.message || "")}</span></div>`)
    .join("");
  els.incidentDetail.querySelector('[data-act="publish"]').addEventListener("click", () => reviewIncident("published", "confirmed", incident.incident_id));
  els.incidentDetail.querySelector('[data-act="dismiss"]').addEventListener("click", () => reviewIncident("dismissed", "dismissed", incident.incident_id));
  els.incidentDetail.querySelector('[data-act="export"]').addEventListener("click", () => exportIncident(incident.incident_id));
  els.incidentDetail.querySelector('[data-act="assign"]').addEventListener("click", () => assignIncident(incident.incident_id));
  els.incidentDetail.querySelector('[data-act="comment"]').addEventListener("click", () => commentIncident(incident.incident_id));
}

async function assignIncident(incidentId) {
  const assignee = $("#assigneeName").value.trim();
  if (!assignee) return showToast("Enter an assignee name.");
  try {
    await api(`/incidents/${encodeURIComponent(incidentId)}/assign`, {
      method: "POST",
      body: JSON.stringify({ assignee_name: assignee, assignee_role: "reviewer" }),
    });
    showToast("Incident assigned.");
    await loadIncidentDetail(incidentId);
  } catch (error) {
    showToast(error.message);
  }
}

async function commentIncident(incidentId) {
  const body = $("#commentBody").value.trim();
  if (!body) return showToast("Enter a comment.");
  try {
    await api(`/incidents/${encodeURIComponent(incidentId)}/comments`, {
      method: "POST",
      body: JSON.stringify({ author_name: "ops_console", author_role: "reviewer", body }),
    });
    showToast("Comment added.");
    await loadIncidentDetail(incidentId);
  } catch (error) {
    showToast(error.message);
  }
}

async function loadEvidencePacks() {
  els.evidencePacks.innerHTML = skeletonRows(3);
  const params = new URLSearchParams({ page_size: "100" });
  if (els.evidenceQuality.value) params.set("quality", els.evidenceQuality.value);
  try {
    const payload = await api(`/evidence-packs?${params.toString()}`);
    state.packs = payload.items || [];
    els.evidenceCount.textContent = `${payload.total || 0} packs`;
    state.selectedPanelId = state.selectedPanelId || state.packs[0]?.panel_id || null;
    renderEvidencePacks();
    if (state.selectedPanelId) await loadPackDetail(state.selectedPanelId);
  } catch (error) {
    els.evidencePacks.innerHTML = `<div class="error-state">${escapeHtml(error.message)}</div>`;
  }
}

function renderEvidencePacks() {
  if (!state.packs.length) {
    els.evidencePacks.innerHTML = emptyStateHtml("No evidence packs", "Change readiness filters or generate new incident panels.");
    return;
  }
  els.evidencePacks.innerHTML = state.packs
    .map((pack) => `
      <button class="pack-card ${pack.panel_id === state.selectedPanelId ? "active" : ""}" data-panel-id="${escapeHtml(pack.panel_id)}">
        ${pack.thumbnail_preview ? `<img src="${pack.thumbnail_preview}" alt="Evidence thumbnail" />` : '<div class="pack-thumb image-missing">No preview</div>'}
        <strong>${escapeHtml(pack.site_name)}</strong>
        <span>${escapeHtml(pack.panel_id)} / ${escapeHtml(pack.asset_readiness)}</span>
        <span>${fmtPercent(pack.confidence)} / ${escapeHtml(pack.status)}</span>
      </button>
    `)
    .join("");
  $$(".pack-card").forEach((card) => {
    card.addEventListener("click", () => loadPackDetail(card.dataset.panelId));
  });
}

async function loadPackDetail(panelId) {
  state.selectedPanelId = panelId;
  renderEvidencePacks();
  els.packDetail.className = "loading-state";
  els.packDetail.innerHTML = skeletonRows(2);
  try {
    state.packDetail = await api(`/evidence-packs/${encodeURIComponent(panelId)}`);
    renderPackDetail();
  } catch (error) {
    els.packDetail.className = "error-state";
    els.packDetail.textContent = error.message;
  }
}

function renderPackDetail() {
  const detail = state.packDetail || {};
  const incident = detail.linked_incident || {};
  els.packStatus.textContent = incident.review_status || "available";
  els.packDetail.className = "detail-body";
  els.packDetail.innerHTML = `
    <div class="detail-header">
      <div>
        <h3>${escapeHtml(detail.panel_metadata?.panel_id || state.selectedPanelId)}</h3>
        <p>${escapeHtml(detail.panel_metadata?.site_id || "")} / ${escapeHtml(detail.panel_metadata?.scan_id || "")}</p>
      </div>
      <span class="priority-chip ${incident.priority_tier || "low"}">${escapeHtml(incident.priority_tier || "pack")}</span>
    </div>
    <div class="detail-actions">
      <button class="icon-button" data-pack-export>Export Markdown</button>
      <button class="secondary-button" data-pack-incident>Open Incident</button>
    </div>
    ${provenanceHtml(detail.metadata_panel || {})}
    <div class="evidence-grid" id="packEvidence"></div>
    <h3>Metadata</h3>
    <pre class="metadata-pre">${escapeHtml(JSON.stringify(detail.metadata_panel || {}, null, 2))}</pre>
  `;
  $("#packEvidence").append(
    imageTile("Current vs Temporal", detail.current_image_preview, detail.temporal_comparison_preview),
    imageTile("Temporal Comparison", detail.temporal_comparison_preview),
    imageTile("Map Preview", detail.map_preview),
  );
  els.packDetail.querySelector("[data-pack-export]").addEventListener("click", () => exportIncident(incident.incident_id));
  els.packDetail.querySelector("[data-pack-incident]").addEventListener("click", async () => {
    if (!incident.incident_id) return showToast("No linked incident.");
    setView("triage");
    await loadIncidentDetail(incident.incident_id);
  });
}

els.refreshBtn.addEventListener("click", loadWatchlist);
els.summaryRefreshBtn?.addEventListener("click", loadExecutiveSummary);
els.scanBtn.addEventListener("click", scanWatchlist);
els.scanMapBtn?.addEventListener("click", scanWatchlist);
els.fitMapBtn?.addEventListener("click", renderMap);
els.analysisScanBtn?.addEventListener("click", () => state.selectedSiteId && scanSite(state.selectedSiteId));
els.searchInput.addEventListener("input", renderWatchlist);
els.priorityFilter.addEventListener("change", renderWatchlist);
els.triageStatus?.addEventListener("change", () => loadTriage());
els.triagePriority?.addEventListener("change", () => loadTriage());
els.evidenceQuality?.addEventListener("change", () => loadEvidencePacks());
$$(".nav-item").forEach((item) => item.addEventListener("click", () => setView(item.dataset.view)));

loadWatchlist();
