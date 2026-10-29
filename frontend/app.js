const form = document.querySelector("#analyze-form");
const fileInput = document.querySelector("#resume-file");
const uploadZone = document.querySelector("#upload-zone");
const uploadTitle = document.querySelector("#upload-title");
const uploadSubtitle = document.querySelector("#upload-subtitle");
const jdInput = document.querySelector("#job-description");
const charCount = document.querySelector("#char-count");
const button = document.querySelector("#analyze-button");
const buttonLabel = document.querySelector("#button-label");
const errorBox = document.querySelector("#error-box");
const results = document.querySelector("#results");
let currentReport = null;
let activeFilter = "all";

jdInput.addEventListener("input", () => {
  charCount.textContent = `${jdInput.value.length.toLocaleString()} / 30,000`;
});
fileInput.addEventListener("change", updateFileLabel);
function updateFileLabel() {
  const file = fileInput.files[0];
  if (!file) {
    uploadTitle.innerHTML = 'Drop your resume here or <u>browse files</u>';
    uploadSubtitle.textContent = "PDF or DOCX · Maximum 5 MB";
    return;
  }
  uploadTitle.textContent = file.name;
  uploadSubtitle.textContent = `${(file.size / 1024).toFixed(0)} KB · Ready to analyze`;
}
["dragenter", "dragover"].forEach(evt => uploadZone.addEventListener(evt, e => {
  e.preventDefault(); uploadZone.classList.add("dragover");
}));
["dragleave", "drop"].forEach(evt => uploadZone.addEventListener(evt, e => {
  e.preventDefault(); uploadZone.classList.remove("dragover");
}));
uploadZone.addEventListener("drop", e => {
  const file = e.dataTransfer.files[0];
  if (!file) return;
  const name = file.name.toLowerCase();
  if (!name.endsWith(".pdf") && !name.endsWith(".docx")) {
    showError("Please choose a PDF or DOCX file.");
    return;
  }
  const transfer = new DataTransfer();
  transfer.items.add(file);
  fileInput.files = transfer.files;
  updateFileLabel();
  hideError();
});
function showError(message) { errorBox.textContent = message; errorBox.hidden = false; }
function hideError() { errorBox.hidden = true; errorBox.textContent = ""; }

form.addEventListener("submit", async event => {
  event.preventDefault();
  hideError();
  const file = fileInput.files[0];
  const jd = jdInput.value.trim();
  if (!file) return showError("Please upload your resume first.");
  if (jd.length < 50) return showError("Please paste a fuller job description (at least 50 characters).");
  if (file.size > 5 * 1024 * 1024) return showError("Your file is over 5 MB. Please upload a smaller file.");
  button.disabled = true;
  buttonLabel.textContent = "Analyzing resume…";
  try {
    const body = new FormData();
    body.append("file", file);
    body.append("job_description", jd);
    const response = await fetch("/api/analyze", { method: "POST", body });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || "Analysis failed. Please try again.");
    currentReport = data;
    renderReport(data);
    results.hidden = false;
    results.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    showError(error.message || "Could not connect to the analyzer. Is the backend running?");
  } finally {
    button.disabled = false;
    buttonLabel.textContent = "Analyze my resume";
  }
});

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function renderReport(data) {
  document.querySelector("#result-filename").textContent = `Resume: ${data.filename}`;
  document.querySelector("#overall-score").textContent = data.overall_score;
  document.querySelector("#overall-track").style.width = `${data.overall_score}%`;
  document.querySelector("#matched-count").textContent = data.summary.matched_requirements;
  document.querySelector("#total-count").textContent = `/ ${data.summary.requirements_detected} requirements`;
  document.querySelector("#required-score").textContent = data.required_match_score === null ? "N/A" : data.required_match_score;
  document.querySelector("#word-count").textContent = data.summary.word_count.toLocaleString();
  document.querySelector("#filter-all-count").textContent = data.requirements.length;
  document.querySelector("#filter-matched-count").textContent = data.requirements.filter(x => x.matched).length;
  document.querySelector("#filter-missing-count").textContent = data.requirements.filter(x => !x.matched).length;
  document.querySelector("#score-note").textContent = data.score_note;
  renderRequirements(data.requirements);
  renderReview(data.review);
  renderActionPlan(data);
}
function renderRequirements(requirements) {
  const list = document.querySelector("#requirements-list");
  list.replaceChildren();
  const filtered = requirements.filter(item => activeFilter === "all" || (activeFilter === "matched" ? item.matched : !item.matched));
  document.querySelector("#no-requirements").hidden = requirements.length !== 0;
  filtered.forEach(item => {
    const card = el("article", "requirement-item");
    const top = el("div", "requirement-top");
    top.append(el("span", "requirement-name", item.skill));
    top.append(el("span", `status-pill ${item.status}`, item.matched ? "Matched" : "Not found"));
    card.append(top);
    card.append(el("div", "priority", `${item.priority} · ${item.terms_found_in_jd.join(", ")}`));
    if (item.matched && item.resume_evidence) card.append(el("div", "requirement-advice", `Resume evidence detected: “${item.resume_evidence}”.`));
    card.append(el("div", "requirement-advice", item.recommendation));
    list.append(card);
  });
  if (!filtered.length && requirements.length) list.append(el("div", "empty-state", "No requirements in this filter."));
}
document.querySelectorAll(".filter-chip").forEach(chip => chip.addEventListener("click", () => {
  document.querySelectorAll(".filter-chip").forEach(c => c.classList.toggle("active", c === chip));
  activeFilter = chip.dataset.filter;
  if (currentReport) renderRequirements(currentReport.requirements);
}));
function renderReview(items) {
  const list = document.querySelector("#review-list");
  list.replaceChildren();
  items.forEach(item => {
    const card = el("article", "review-item");
    const statusClass = item.status.toLowerCase().replace(/[^a-z-]/g, "-");
    card.append(el("span", `review-dot ${statusClass}`));
    const content = el("div");
    const row = el("div", "review-title-row");
    row.append(el("span", "review-title", item.area));
    row.append(el("span", "review-status", item.status));
    content.append(row);
    content.append(el("div", "review-finding", item.finding));
    content.append(el("div", "review-suggestion", item.suggestion));
    card.append(content);
    list.append(card);
  });
}
function renderActionPlan(data) {
  const plan = document.querySelector("#action-plan");
  plan.replaceChildren();
  const missing = data.requirements.filter(x => !x.matched);
  const actions = [];
  missing.filter(x => x.priority === "required").forEach(x => actions.push({
    title: `Review ${x.skill}`, text: `This is a required signal in the JD but wasn't detected in the resume. Add evidence only if it reflects your real experience.`
  }));
  data.review.filter(x => ["High"].includes(x.priority) || ["Improve", "Not detected", "Check"].includes(x.status))
    .forEach(x => actions.push({ title: x.area, text: x.suggestion }));
  if (missing.some(x => x.priority === "preferred")) actions.push({
    title: "Review preferred skills", text: "Check the preferred requirements and highlight relevant evidence where accurate."
  });
  if (!actions.length) actions.push({title:"Polish your strongest evidence",text:"Keep the most relevant skills, projects, and measurable outcomes easy to find near the top of your resume."});
  actions.slice(0, 6).forEach((item, index) => {
    const card = el("article", "action-item");
    card.append(el("span", "action-number", String(index + 1).padStart(2, "0")));
    const content = el("div");
    content.append(el("strong", "", item.title));
    content.append(el("p", "", item.text));
    card.append(content);
    plan.append(card);
  });
}
document.querySelector("#download-button").addEventListener("click", () => {
  if (!currentReport) return;
  const blob = new Blob([JSON.stringify(currentReport, null, 2)], {type: "application/json"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `clearcv-analysis-${new Date().toISOString().slice(0,10)}.json`;
  document.body.append(a); a.click(); a.remove(); URL.revokeObjectURL(url);
});
