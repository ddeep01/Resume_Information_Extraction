/* ==========================================================
   FACULTY.JS - Institutional Profile Logic
========================================================== */

"use strict";

const JSON_FOLDER = "../evaluation/result_llm/data/qwen2.5_7b/";
const RESUME_FOLDER = "../data/raw_resumes/";

let facultyData = null;
let facultyId = null;

document.addEventListener("DOMContentLoaded", init);

async function init() {
  try {
    showLoader(true);
    facultyId = getFacultyId();

    if (!facultyId) {
      showErrorState("Faculty ID is missing from the URL.");
      showLoader(false);
      return;
    }

    facultyData = await loadFacultyJSON(facultyId);

    if (!facultyData) {
      showErrorState("Faculty profile data could not be retrieved.");
      showLoader(false);
      return;
    }

    populatePage();
    initializeComponents();
    showLoader(false);
  } catch (error) {
    console.error("Error loading profile:", error);
    showErrorState("The requested faculty profile could not be found.");
    showLoader(false);
  }
}

function getFacultyId() {
  const params = new URLSearchParams(window.location.search);
  return params.get("id");
}

async function loadFacultyJSON(id) {
  const response = await fetch(`${JSON_FOLDER}${id}.json`);
  if (!response.ok) {
    throw new Error("JSON file not found.");
  }
  return await response.json();
}

function populatePage() {
  renderHero();
  renderStatistics();
  renderOverview();
  renderEducation();
  renderExperience();
  renderResearch();
  renderSkills();
}

function $(id) {
  return document.getElementById(id);
}

function value(data, fallback = "—") {
  if (data === undefined || data === null) {
    return fallback;
  }
  if (typeof data === "string" && data.trim() === "") {
    return fallback;
  }
  return data;
}

function personal() {
  return facultyData.personal_information || {};
}

function education() {
  return facultyData.education || [];
}

function experience() {
  return facultyData.experience || [];
}

function publications() {
  return facultyData.publication_summary || {};
}

function normalizeDegree(degree) {
  if (!degree) return "";
  if (window.DegreeNormalizer) {
    return window.DegreeNormalizer.normalizeDegree(degree);
  }
  return degree;
}

function initials(name) {
  if (!name) return "F";
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase();
}

/* ==========================================================
   RENDER HERO
========================================================== */

function renderHero() {
  const p = personal();
  const edu = education();

  const highestDegree =
    facultyData.normalized_highest_degree ||
    (window.DegreeNormalizer
      ? window.DegreeNormalizer.getHighestDegree(edu)
      : edu.length > 0
      ? normalizeDegree(edu[0].degree)
      : "—");

  const institute = edu.length > 0 ? value(edu[0].institution || edu[0].board_university, "—") : "—";

  if ($("facultyName")) $("facultyName").textContent = value(p.full_name, facultyId || "Faculty Member");

  if ($("designation"))
    $("designation").textContent = value(p.current_designation || experience()[0]?.designation, "Faculty Member");

  if ($("university")) {
    $("university").innerHTML = `<i class="fa-solid fa-building-columns"></i> ${institute}`;
  }

  if ($("email")) {
    if (p.email && p.email.trim()) {
      $("email").style.display = "inline-flex";
      $("email").innerHTML = `<i class="fa-solid fa-envelope"></i> ${p.email.trim()}`;
    } else {
      $("email").style.display = "none";
    }
  }

  if ($("phone")) {
    if (p.phone && p.phone.trim()) {
      $("phone").style.display = "inline-flex";
      $("phone").innerHTML = `<i class="fa-solid fa-phone"></i> ${p.phone.trim()}`;
    } else {
      $("phone").style.display = "none";
    }
  }

  if ($("location")) {
    if (p.address && p.address.trim()) {
      $("location").style.display = "inline-flex";
      $("location").innerHTML = `<i class="fa-solid fa-location-dot"></i> ${p.address.trim()}`;
    } else {
      $("location").style.display = "none";
    }
  }

  if ($("avatar")) $("avatar").textContent = initials(p.full_name || facultyId);

  if ($("degreeBadge")) {
    if (highestDegree && highestDegree !== "—" && highestDegree !== "Other") {
      $("degreeBadge").style.display = "inline-flex";
      $("degreeBadge").textContent = highestDegree;
    } else {
      $("degreeBadge").style.display = "none";
    }
  }
}

/* ==========================================================
   RENDER STATISTICS
========================================================== */

function renderStatistics() {
  const p = personal();
  const pub = publications();
  const years = parseExperienceYears(p.total_experience);

  if ($("experienceYears")) $("experienceYears").textContent = years;
  if ($("journalCount")) $("journalCount").textContent = pub.journal_publications || 0;
  if ($("conferenceCount")) $("conferenceCount").textContent = pub.conference_publications || 0;
  if ($("patentCount")) $("patentCount").textContent = pub.patents || 0;
}

/* ==========================================================
   RENDER OVERVIEW
========================================================== */

function renderOverview() {
  const p = personal();
  const edu = education();
  const expYears = parseExperienceYears(p.total_experience);

  const highestDegree =
    facultyData.normalized_highest_degree ||
    (window.DegreeNormalizer
      ? window.DegreeNormalizer.getHighestDegree(edu)
      : edu.length
      ? normalizeDegree(edu[0].degree)
      : "—");

  const institute = edu.length ? value(edu[0].institution || edu[0].board_university, "—") : "—";

  if ($("highestDegree")) $("highestDegree").textContent = highestDegree;
  if ($("currentPosition"))
    $("currentPosition").textContent = value(p.current_designation || experience()[0]?.designation, "Faculty Member");
  if ($("currentInstitute")) $("currentInstitute").textContent = institute;
  if ($("experienceText")) $("experienceText").textContent = `${expYears} Years`;
  if ($("aiSummary")) $("aiSummary").innerHTML = createSummary();
}

function createSummary() {
  const p = personal();
  const pub = publications();
  const years = parseExperienceYears(p.total_experience);

  const highestDegree =
    facultyData.normalized_highest_degree ||
    (window.DegreeNormalizer
      ? window.DegreeNormalizer.getHighestDegree(education())
      : education().length
      ? normalizeDegree(education()[0].degree)
      : "—");

  return `
    <p style="font-size:14px; line-height:1.6; color:#334155;">
        <strong>${value(p.full_name, "This faculty member")}</strong> is an
        <strong>${value(p.current_designation || "Faculty Member")}</strong>
        with approximately <strong>${years} years</strong> of academic and professional experience.
    </p>
    <div style="margin-top:10px; font-size:13px; color:#475569;">
        Highest qualification: <strong>${highestDegree}</strong>.
    </div>
    <div style="margin-top:8px; font-size:13px; color:#475569;">
        Research record includes <strong>${pub.journal_publications || 0}</strong> journal papers,
        <strong>${pub.conference_publications || 0}</strong> conference publications, and
        <strong>${pub.patents || 0}</strong> patents.
    </div>
  `;
}

function parseExperienceYears(text) {
  if (!text) return 0;
  const match = String(text).match(/\d+/);
  return match ? Number(match[0]) : 0;
}

/* ==========================================================
   RENDER EDUCATION
========================================================== */

function renderEducation() {
  const container = $("educationTimeline");
  if (!container) return;
  container.innerHTML = "";

  const list = education();

  if (!list.length) {
    container.innerHTML = `
      <div class="timeline-item">
        <div class="timeline-title">No education details extracted</div>
      </div>`;
    return;
  }

  list.forEach((item) => {
    const canonical = item.normalized_degree || normalizeDegree(item.degree);
    const rawDegree = item.degree && item.degree.trim() !== canonical ? item.degree.trim() : "";

    container.innerHTML += `
      <div class="timeline-item">
        <div class="timeline-title">
          ${canonical}
          ${rawDegree ? `<span style="font-size:12px; font-weight:normal; color:#64748B; margin-left:6px;">(${rawDegree})</span>` : ""}
        </div>
        <div class="timeline-subtitle">${value(item.institution || item.board_university)}</div>
        <div class="timeline-meta">${value(item.year)}</div>
      </div>`;
  });
}

/* ==========================================================
   RENDER EXPERIENCE
========================================================== */

function renderExperience() {
  const container = $("experienceTimeline");
  if (!container) return;
  container.innerHTML = "";

  const list = experience();

  if (!list.length) {
    container.innerHTML = `
      <div class="timeline-item">
        <div class="timeline-title">No experience details extracted</div>
      </div>`;
    return;
  }

  list.forEach((item) => {
    container.innerHTML += `
      <div class="timeline-item">
        <div class="timeline-title">${value(item.designation, "Faculty Role")}</div>
        <div class="timeline-subtitle">${value(item.organization || item.institution || item.company)}</div>
        <div class="timeline-meta">
          ${value(item.start_date)} ${item.end_date ? " - " + item.end_date : ""}
        </div>
      </div>`;
  });
}

/* ==========================================================
   RENDER RESEARCH
========================================================== */

function renderResearch() {
  const pub = publications();
  const journalEl = $("journalCount") || $("journalPublications");
  if (journalEl) journalEl.textContent = pub.journal_publications || 0;

  const confEl = $("conferenceCount") || $("conferencePublications");
  if (confEl) confEl.textContent = pub.conference_publications || 0;

  const patentEl = $("patentCount") || $("patentPublications");
  if (patentEl) patentEl.textContent = pub.patents || 0;
}

/* ==========================================================
   RENDER SKILLS
========================================================== */

function renderSkills() {
  const container = $("skillsContainer");
  if (!container) return;
  container.innerHTML = "";

  const raw = facultyData || {};
  const skillSet = new Set();

  [
    ...(raw.skills || []),
    ...(raw.technical_skills || []),
    ...(raw.key_skills || []),
    ...(raw.core_skills || []),
  ].forEach((skill) => {
    if (!skill) return;
    if (typeof skill === "string") skillSet.add(skill.trim());
    else if (skill.name) skillSet.add(skill.name.trim());
  });

  const skills = [...skillSet];

  if (!skills.length) {
    container.innerHTML = `<div style="font-size:13px; color:#94A3B8;">No skills extracted</div>`;
    return;
  }

  skills.forEach((skill) => {
    const badge = document.createElement("span");
    badge.className = "skill-chip";
    badge.textContent = skill;
    container.appendChild(badge);
  });
}

/* ==========================================================
   TAB SWITCHING & RESUME BUTTON
========================================================== */

function initializeTabs() {
  const buttons = document.querySelectorAll(".tab-btn");
  const panels = document.querySelectorAll(".tab-panel");

  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      buttons.forEach((btn) => btn.classList.remove("active"));
      panels.forEach((panel) => panel.classList.remove("active"));

      button.classList.add("active");
      const target = button.dataset.tab;
      if ($(target)) $(target).classList.add("active");
    });
  });
}

function initializeResumeButton() {
  const btn = $("resumeBtn");
  if (!btn) return;

  btn.addEventListener("click", () => {
    const url = `${RESUME_FOLDER}${facultyId}.pdf`;
    window.open(url, "_blank");
  });
}

function showLoader(show) {
  const loader = $("loadingScreen");
  if (!loader) return;
  loader.style.display = show ? "flex" : "none";
}

function showErrorState(message) {
  const profileContainer = $("profileContainer");
  const errorContainer = $("errorContainer");
  if (profileContainer) profileContainer.style.display = "none";
  if (errorContainer) {
    errorContainer.style.display = "block";
    const p = errorContainer.querySelector("p");
    if (p && message) p.textContent = message;
  }
}

function initializeComponents() {
  initializeTabs();
  initializeResumeButton();
}