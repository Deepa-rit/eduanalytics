let subjectChartInstance = null;
let distributionChartInstance = null;
let trendChartInstance = null;

let cachedDashboardData = null;
let cachedPredictions = [];

const TAB_TITLES = {
  dashboard: "Class Performance Dashboard",
  students: "Student Management",
  assessments: "Assessment & Marks Management",
  gaps: "Learning Gap Identification",
  predictions: "ML Predictive Performance Analysis",
};

// Navigation
document.querySelectorAll(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    const tab = btn.dataset.tab;
    document.getElementById(`tab-${tab}`).classList.add("active");
    document.getElementById("page-title").textContent = TAB_TITLES[tab];

    if (tab === "dashboard" || tab === "gaps") loadDashboard();
    if (tab === "students") loadStudents();
    if (tab === "assessments") loadAssessments();
    if (tab === "predictions") loadPredictions();
  });
});

function toggleCustomInput(selectId, customInputId) {
  const selectEl = document.getElementById(selectId);
  const wrapEl = document.getElementById(`${customInputId}-wrap`);
  const inputEl = document.getElementById(customInputId);
  if (selectEl.value === "__other__") {
    wrapEl.style.display = "flex";
    inputEl.required = true;
    inputEl.focus();
  } else {
    wrapEl.style.display = "none";
    inputEl.required = false;
    inputEl.value = "";
  }
}

function statusBadge(pct) {
  if (pct === null || pct === undefined) return '<span class="badge">No Data</span>';
  if (pct >= 75) return `<span class="badge badge-strong">${pct}% (Strong)</span>`;
  if (pct >= 50) return `<span class="badge badge-monitor">${pct}% (Monitor)</span>`;
  return `<span class="badge badge-danger">${pct}% (Support)</span>`;
}

function populateSelect(selectId, items, defaultLabel) {
  const select = document.getElementById(selectId);
  const current = select.value;
  select.innerHTML =
    `<option value="">${defaultLabel}</option>` +
    items.map((item) => `<option value="${item}">${item}</option>`).join("");
  select.value = items.includes(current) ? current : "";
}

async function loadMetadata() {
  const res = await fetch("/api/metadata");
  const meta = await res.json();
  populateSelect("dept-filter", meta.departments, "All Departments");
  populateSelect("sem-filter", meta.semesters, "All Semesters");
  populateSelect("assess-dept-filter", meta.departments, "All Departments");
  populateSelect("subject-filter", meta.subjects, "All Subjects");
  populateSelect("assess-type-filter", meta.assessment_types, "All Types");
  populateSelect("gap-subject-filter", meta.subjects, "All Subjects");
  populateSelect("gap-dept-filter", meta.departments, "All Departments");
  populateSelect("pred-dept-filter", meta.departments, "All Departments");
}

async function loadDashboard() {
  const res = await fetch("/api/dashboard");
  const data = await res.json();
  cachedDashboardData = data;

  document.getElementById("kpi-total-students").textContent = data.kpis.total_students;
  document.getElementById("kpi-subjects-monitored").textContent = `${data.kpis.subjects_monitored} subjects monitored`;
  document.getElementById("kpi-avg-performance").textContent = `${data.kpis.average_performance}%`;
  document.getElementById("kpi-pass-rate").textContent = `${data.kpis.pass_rate}%`;
  document.getElementById("kpi-support-count").textContent = data.kpis.students_needing_support;

  renderCharts(data);
  applyGapFilters();
}

function renderCharts(data) {
  const subjCtx = document.getElementById("subjectChart").getContext("2d");
  if (subjectChartInstance) subjectChartInstance.destroy();
  subjectChartInstance = new Chart(subjCtx, {
    type: "bar",
    data: {
      labels: data.subject_performance.map((s) => s.subject),
      datasets: [
        {
          label: "Average Score (%)",
          data: data.subject_performance.map((s) => s.average),
          backgroundColor: data.subject_performance.map((s) =>
            s.average < 50 ? "#dc2626" : s.average < 65 ? "#d97706" : "#2563eb"
          ),
          borderRadius: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { beginAtZero: true, max: 100 } },
      plugins: { legend: { display: false } },
    },
  });

  const distCtx = document.getElementById("distributionChart").getContext("2d");
  if (distributionChartInstance) distributionChartInstance.destroy();
  const dist = data.performance_distribution;
  distributionChartInstance = new Chart(distCtx, {
    type: "doughnut",
    data: {
      labels: ["Strong (>=75%)", "Moderate (50-74%)", "Needs Support (<50%)"],
      datasets: [
        {
          data: [dist.strong, dist.moderate, dist.needs_support],
          backgroundColor: ["#16a34a", "#f59e0b", "#dc2626"],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "bottom" } },
    },
  });

  const trendCtx = document.getElementById("trendChart").getContext("2d");
  if (trendChartInstance) trendChartInstance.destroy();
  trendChartInstance = new Chart(trendCtx, {
    type: "line",
    data: {
      labels: data.assessment_trend.map((t) => t.date),
      datasets: [
        {
          label: "Class Average (%)",
          data: data.assessment_trend.map((t) => t.average),
          borderColor: "#1e40af",
          backgroundColor: "rgba(37, 99, 235, 0.12)",
          fill: true,
          tension: 0.3,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { beginAtZero: true, max: 100 } },
    },
  });
}

function applyGapFilters() {
  if (!cachedDashboardData) return;
  const search = document.getElementById("gap-search").value.trim().toLowerCase();
  const subj = document.getElementById("gap-subject-filter").value;
  const dept = document.getElementById("gap-dept-filter").value;
  const sev = document.getElementById("gap-severity-filter").value;

  const filteredTopics = cachedDashboardData.topic_gaps.filter((g) => {
    if (subj && g.subject !== subj) return false;
    if (sev === "high" && g.severity !== "Critical") return false;
    if (sev === "medium" && g.severity !== "Moderate") return false;
    if (
      search &&
      !g.subject.toLowerCase().includes(search) &&
      !g.topic.toLowerCase().includes(search) &&
      !g.recommendation.toLowerCase().includes(search)
    ) {
      return false;
    }
    return true;
  });

  const filteredStudents = cachedDashboardData.support_students.filter((s) => {
    if (dept && s.department !== dept) return false;
    if (sev === "high" && s.priority !== "High") return false;
    if (sev === "medium" && s.priority !== "Medium") return false;
    if (
      search &&
      !s.name.toLowerCase().includes(search) &&
      !s.roll_number.toLowerCase().includes(search)
    ) {
      return false;
    }
    return true;
  });

  document.getElementById("topic-gaps-count").textContent = filteredTopics.length;
  document.getElementById("support-students-count").textContent = filteredStudents.length;
  document.getElementById("gaps-count-pill").textContent =
    `${filteredTopics.length} topic gaps · ${filteredStudents.length} students`;

  const topicContainer = document.getElementById("topic-gaps-list");
  if (!filteredTopics.length) {
    topicContainer.innerHTML = "<p class='subtitle'>No topic gaps match the current filters.</p>";
  } else {
    topicContainer.innerHTML = filteredTopics
      .map(
        (g) => `
      <div class="gap-item">
        <div class="gap-item-head">
          <strong>${g.subject} — ${g.topic}</strong>
          <span class="badge ${g.severity === "Critical" ? "badge-danger" : "badge-monitor"}">
            ${g.average}% (${g.severity})
          </span>
        </div>
        <p class="gap-rec">${g.recommendation}</p>
      </div>`
      )
      .join("");
  }

  const supportContainer = document.getElementById("support-students-list");
  if (!filteredStudents.length) {
    supportContainer.innerHTML = "<p class='subtitle'>No students match the current filters.</p>";
  } else {
    supportContainer.innerHTML = filteredStudents
      .map(
        (s) => `
      <div class="gap-item">
        <div class="gap-item-head">
          <strong>${s.name} (${s.roll_number})</strong>
          <span class="badge ${s.priority === "High" ? "badge-danger" : "badge-monitor"}">
            ${s.average}% (${s.priority} Priority)
          </span>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px;">
          <span class="subtitle">${s.department}</span>
          <button class="btn btn-secondary btn-sm" onclick="viewStudentReport(${s.id})">View Report</button>
        </div>
      </div>`
      )
      .join("");
  }
}

function clearGapFilters() {
  document.getElementById("gap-search").value = "";
  document.getElementById("gap-subject-filter").value = "";
  document.getElementById("gap-dept-filter").value = "";
  document.getElementById("gap-severity-filter").value = "";
  applyGapFilters();
}

async function loadPredictions() {
  const res = await fetch("/api/predictions");
  const data = await res.json();
  cachedPredictions = data.predictions || [];
  document.getElementById("prediction-model-info").textContent = `Model: ${data.model}`;
  document.getElementById("prediction-disclaimer").textContent = data.disclaimer || "";
  applyPredictionFilters();
}

function applyPredictionFilters() {
  const search = document.getElementById("pred-search").value.trim().toLowerCase();
  const dept = document.getElementById("pred-dept-filter").value;
  const risk = document.getElementById("pred-risk-filter").value;

  const filtered = cachedPredictions.filter((p) => {
    if (dept && p.department !== dept) return false;
    if (risk && p.support_estimate !== risk) return false;
    if (
      search &&
      !p.name.toLowerCase().includes(search) &&
      !p.roll_number.toLowerCase().includes(search)
    ) {
      return false;
    }
    return true;
  });

  document.getElementById("predictions-count-pill").textContent =
    `${filtered.length} of ${cachedPredictions.length} students`;

  const tbody = document.getElementById("predictions-tbody");
  tbody.innerHTML = filtered
    .map((p) => {
      const badgeClass =
        p.support_estimate === "High Support Priority"
          ? "badge-danger"
          : p.support_estimate === "Monitor"
          ? "badge-monitor"
          : "badge-strong";
      const slopeSign = p.trend_slope > 0 ? `+${p.trend_slope}` : p.trend_slope;
      return `
      <tr>
        <td><strong>${p.roll_number}</strong></td>
        <td>${p.name}</td>
        <td>${p.department}</td>
        <td>${p.assessments_count}</td>
        <td>${p.current_average}%</td>
        <td><strong>${p.estimated_next_score}%</strong></td>
        <td>${slopeSign} / test</td>
        <td><span class="badge ${badgeClass}">${p.support_estimate}</span></td>
        <td>${p.confidence_note}</td>
      </tr>`;
    })
    .join("");
}

function clearPredictionFilters() {
  document.getElementById("pred-search").value = "";
  document.getElementById("pred-dept-filter").value = "";
  document.getElementById("pred-risk-filter").value = "";
  applyPredictionFilters();
}

async function loadStudents() {
  const q = document.getElementById("student-search").value;
  const department = document.getElementById("dept-filter").value;
  const semester = document.getElementById("sem-filter").value;
  const status = document.getElementById("student-status-filter").value;
  const params = new URLSearchParams({ q, department, semester, status });
  const res = await fetch(`/api/students?${params}`);
  const students = await res.json();

  document.getElementById("students-count-pill").textContent =
    `${students.length} student${students.length === 1 ? "" : "s"}`;

  const tbody = document.getElementById("students-tbody");
  tbody.innerHTML = students
    .map(
      (s) => `
    <tr>
      <td><strong>${s.roll_number}</strong></td>
      <td>${s.name}</td>
      <td>${s.department}</td>
      <td>${s.semester}</td>
      <td>${s.assessment_count}</td>
      <td>${statusBadge(s.average_pct)}</td>
      <td>
        <button class="btn btn-secondary btn-sm" onclick="viewStudentReport(${s.id})">Report</button>
        <button class="btn btn-outline btn-sm" onclick='openStudentModal(${JSON.stringify(s)})'>Edit</button>
        <button class="btn btn-danger btn-sm" onclick="deleteStudent(${s.id})">Delete</button>
      </td>
    </tr>`
    )
    .join("");
}

function clearStudentFilters() {
  document.getElementById("student-search").value = "";
  document.getElementById("dept-filter").value = "";
  document.getElementById("sem-filter").value = "";
  document.getElementById("student-status-filter").value = "";
  loadStudents();
}

async function loadAssessments() {
  const q = document.getElementById("assess-search").value;
  const department = document.getElementById("assess-dept-filter").value;
  const subject = document.getElementById("subject-filter").value;
  const assessment_type = document.getElementById("assess-type-filter").value;
  const status = document.getElementById("assess-status-filter").value;
  const params = new URLSearchParams({ q, department, subject, assessment_type, status });
  const res = await fetch(`/api/assessments?${params}`);
  const rows = await res.json();

  document.getElementById("assessments-count-pill").textContent =
    `${rows.length} record${rows.length === 1 ? "" : "s"}`;

  const tbody = document.getElementById("assessments-tbody");
  tbody.innerHTML = rows
    .map(
      (a) => `
    <tr>
      <td>${a.assessed_date}</td>
      <td>${a.roll_number}</td>
      <td>${a.student_name}</td>
      <td>${a.department}</td>
      <td>${a.subject}</td>
      <td>${a.topic}</td>
      <td>${a.assessment_type}</td>
      <td>${a.score} / ${a.max_score}</td>
      <td>${statusBadge(a.percentage)}</td>
      <td><button class="btn btn-danger btn-sm" onclick="deleteAssessment(${a.id})">Delete</button></td>
    </tr>`
    )
    .join("");
}

function clearAssessmentFilters() {
  document.getElementById("assess-search").value = "";
  document.getElementById("assess-dept-filter").value = "";
  document.getElementById("subject-filter").value = "";
  document.getElementById("assess-type-filter").value = "";
  document.getElementById("assess-status-filter").value = "";
  loadAssessments();
}

function openStudentModal(student = null) {
  document.getElementById("student-modal-title").textContent = student ? "Edit Student" : "Add Student";
  document.getElementById("student-id").value = student ? student.id : "";
  document.getElementById("student-roll").value = student ? student.roll_number : "";
  document.getElementById("student-name").value = student ? student.name : "";
  document.getElementById("student-dept").value = student ? student.department : "CSE";
  document.getElementById("student-sem").value = student ? student.semester : "Sem 4";
  document.getElementById("student-modal").classList.remove("hidden");
}

async function saveStudent(e) {
  e.preventDefault();
  const id = document.getElementById("student-id").value;
  const payload = {
    roll_number: document.getElementById("student-roll").value,
    name: document.getElementById("student-name").value,
    department: document.getElementById("student-dept").value,
    semester: document.getElementById("student-sem").value,
  };

  const url = id ? `/api/students/${id}` : "/api/students";
  const method = id ? "PUT" : "POST";
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    alert(data.error || "Failed to save student.");
    return;
  }
  closeModal("student-modal");
  await loadMetadata();
  loadStudents();
  loadDashboard();
}

async function deleteStudent(id) {
  if (!confirm("Delete this student and all their assessment records?")) return;
  await fetch(`/api/students/${id}`, { method: "DELETE" });
  await loadMetadata();
  loadStudents();
  loadDashboard();
}

async function openAssessmentModal() {
  const res = await fetch("/api/students");
  const students = await res.json();
  const select = document.getElementById("assess-student");
  select.innerHTML = students
    .map((s) => `<option value="${s.id}">${s.roll_number} — ${s.name}</option>`)
    .join("");
  document.getElementById("assess-date").value = new Date().toISOString().split("T")[0];
  toggleCustomInput("assess-subject", "assess-subject-custom");
  toggleCustomInput("assess-type", "assess-type-custom");
  document.getElementById("assessment-modal").classList.remove("hidden");
}

async function saveAssessment(e) {
  e.preventDefault();
  const subjectSelect = document.getElementById("assess-subject").value;
  const typeSelect = document.getElementById("assess-type").value;
  const subject =
    subjectSelect === "__other__"
      ? document.getElementById("assess-subject-custom").value
      : subjectSelect;
  const assessmentType =
    typeSelect === "__other__"
      ? document.getElementById("assess-type-custom").value
      : typeSelect;

  const payload = {
    student_id: document.getElementById("assess-student").value,
    subject,
    topic: document.getElementById("assess-topic").value,
    assessment_type: assessmentType,
    score: document.getElementById("assess-score").value,
    max_score: document.getElementById("assess-max").value,
    assessed_date: document.getElementById("assess-date").value,
  };
  const res = await fetch("/api/assessments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    alert(data.error || "Failed to record marks.");
    return;
  }
  closeModal("assessment-modal");
  document.getElementById("assessment-form").reset();
  await loadMetadata();
  loadAssessments();
  loadDashboard();
}

async function deleteAssessment(id) {
  if (!confirm("Delete this assessment record?")) return;
  await fetch(`/api/assessments/${id}`, { method: "DELETE" });
  await loadMetadata();
  loadAssessments();
  loadDashboard();
}

function openImportModal() {
  document.getElementById("import-form").reset();
  document.getElementById("import-modal").classList.remove("hidden");
}

async function uploadCsv(e) {
  e.preventDefault();
  const fileInput = document.getElementById("import-file");
  if (!fileInput.files.length) return;

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  const res = await fetch("/api/import/csv", {
    method: "POST",
    body: formData,
  });
  const data = await res.json();
  if (!res.ok) {
    alert(data.error || "CSV import failed.");
    return;
  }
  alert(data.message);
  closeModal("import-modal");
  await loadMetadata();
  loadStudents();
  loadAssessments();
  loadDashboard();
}

async function viewStudentReport(studentId) {
  const res = await fetch(`/api/students/${studentId}/report`);
  const r = await res.json();
  if (!res.ok) {
    alert(r.error || "Could not load report.");
    return;
  }

  document.getElementById("report-title").textContent = `${r.student.name} (${r.student.roll_number})`;
  document.getElementById("report-body").innerHTML = `
    <div class="report-summary">
      <div class="report-box"><span>Overall Average</span><strong>${r.overall_average}%</strong></div>
      <div class="report-box"><span>Progress Trend</span><strong>${r.trend}</strong></div>
      <div class="report-box"><span>Department</span><strong>${r.student.department} (${r.student.semester})</strong></div>
    </div>
    <h4>Subject Performance</h4>
    <table>
      <thead><tr><th>Subject</th><th>Average</th><th>Status</th></tr></thead>
      <tbody>
        ${r.subject_breakdown
          .map(
            (s) => `<tr><td>${s.subject}</td><td>${s.average}%</td><td>${s.status}</td></tr>`
          )
          .join("")}
      </tbody>
    </table>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-top:16px;">
      <h4>Personalised Learning Recommendations</h4>
      <button class="btn btn-secondary btn-sm" onclick="fetchAiRecommendations(${studentId})">
        Generate Gemini AI Study Plan
      </button>
    </div>
    <p class="subtitle" id="ai-rec-source" style="margin-top:4px;">Source: Rule-Based Analytics</p>
    <ul class="rec-list" id="ai-rec-list">
      ${r.recommendations.map((rec) => `<li>${rec}</li>`).join("")}
    </ul>
  `;
  document.getElementById("report-modal").classList.remove("hidden");
}

async function fetchAiRecommendations(studentId) {
  const sourceEl = document.getElementById("ai-rec-source");
  sourceEl.textContent = "Generating personalized recommendations...";
  const res = await fetch(`/api/students/${studentId}/ai-recommendations`, { method: "POST" });
  const data = await res.json();
  sourceEl.textContent = `Source: ${data.source}`;
  document.getElementById("ai-rec-list").innerHTML = data.suggestions
    .map((s) => `<li>${s}</li>`)
    .join("");
}

function closeModal(id) {
  document.getElementById(id).classList.add("hidden");
}

// Initial Load
(async function init() {
  await loadMetadata();
  loadDashboard();
  loadStudents();
  loadAssessments();
})();
