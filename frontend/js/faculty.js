/* ==========================================================
                FACULTY.JS
                PART 1
========================================================== */

"use strict";

/* ==========================================================
                CONFIGURATION
========================================================== */

const JSON_FOLDER =
    "../evaluation/result_llm/data/qwen2.5_7b/";

const RESUME_FOLDER =
    "../data/raw_resumes/";

/* ==========================================================
                GLOBAL STATE
========================================================== */

let facultyData = null;

let facultyId = null;


/* ==========================================================
                START
========================================================== */

document.addEventListener("DOMContentLoaded", init);


/* ==========================================================
                INITIALIZATION
========================================================== */

async function init() {

    try {

        showLoader(true);

        facultyId = getFacultyId();

        if (!facultyId) {

            alert("Faculty ID not found.");
            window.location.href = "index.html";
            return;

        }

        facultyData = await loadFacultyJSON(facultyId);

        populatePage();

        // IMPORTANT
        initializeComponents();

        showLoader(false);

    }

    catch (error) {

        console.error(error);

        showLoader(false);

        alert(error.message);

    }

}
button.addEventListener("click", () => {

    console.log("Clicked:", button.dataset.tab);

    buttons.forEach(btn => btn.classList.remove("active"));

    panels.forEach(panel => panel.classList.remove("active"));

    button.classList.add("active");

    const target = button.dataset.tab;

    document.getElementById(target).classList.add("active");

});


/* ==========================================================
                GET FACULTY ID
========================================================== */

function getFacultyId() {

    const params = new URLSearchParams(window.location.search);

    return params.get("id");

}


/* ==========================================================
                LOAD JSON
========================================================== */

async function loadFacultyJSON(id) {

    const response = await fetch(`${JSON_FOLDER}${id}.json`);

    if (!response.ok) {

        throw new Error("JSON file not found.");

    }

    return await response.json();

}


/* ==========================================================
                POPULATE PAGE
========================================================== */

function populatePage() {

    renderHero();

    renderStatistics();

    renderOverview();

    renderEducation();

    renderExperience();

    renderResearch();

    renderSkills();

}


/* ==========================================================
                HELPERS
========================================================== */

function $(id) {

    return document.getElementById(id);

}


function value(data, fallback = "-") {

    if (data === undefined || data === null) {

        return fallback;

    }

    if (typeof data === "string" && data.trim() === "") {

        return fallback;

    }

    return data;

}


/* ==========================================================
                GET PERSONAL INFO
========================================================== */

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


/* ==========================================================
                NORMALIZE DEGREE
========================================================== */

function normalizeDegree(degree) {
    if (!degree) return "";
    if (window.DegreeNormalizer) {
        return window.DegreeNormalizer.normalizeDegree(degree);
    }
    return degree;
}


/* ==========================================================
                GET INITIALS
========================================================== */

function initials(name) {

    if (!name) return "F";

    return name

        .split(" ")

        .map(word => word[0])

        .slice(0, 2)

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
            : (edu.length > 0 ? normalizeDegree(edu[0].degree) : "-"));

    const institute =
        edu.length > 0
            ? value(
                edu[0].institution ||
                edu[0].board_university
            )
            : "-";

    $("facultyName").textContent =
        value(p.full_name);

    $("designation").textContent =
        value(
            p.current_designation ||
            experience()[0]?.designation
        );

    $("university").innerHTML = `
        <i class="fa-solid fa-building-columns"></i>
        ${institute}
    `;

    $("email").innerHTML = `
        <i class="fa-solid fa-envelope"></i>
        ${value(p.email)}
    `;

    $("phone").innerHTML = `
        <i class="fa-solid fa-phone"></i>
        ${value(p.phone)}
    `;

    $("location").innerHTML = `
        <i class="fa-solid fa-location-dot"></i>
        ${value(p.address)}
    `;

    $("avatar").textContent =
        initials(p.full_name);

    if (highestDegree === "Ph.D.") {

        $("degreeBadge").style.display = "inline-flex";

        $("degreeBadge").textContent = highestDegree;

    }

    else {

        $("degreeBadge").style.display = "none";

    }

}



/* ==========================================================
                RENDER STATISTICS
========================================================== */

function renderStatistics() {

    const p = personal();

    const pub = publications();

    const years =
        parseExperienceYears(
            p.total_experience
        );

    $("experienceYears").textContent =
        years;

    $("journalCount").textContent =
        pub.journal_publications || 0;

    $("conferenceCount").textContent =
        pub.conference_publications || 0;

    $("patentCount").textContent =
        pub.patents || 0;

}



/* ==========================================================
                RENDER OVERVIEW
========================================================== */

function renderOverview() {

    const p = personal();

    const edu = education();

    const expYears =
        parseExperienceYears(
            p.total_experience
        );

    const highestDegree =
        facultyData.normalized_highest_degree ||
        (window.DegreeNormalizer
            ? window.DegreeNormalizer.getHighestDegree(edu)
            : (edu.length ? normalizeDegree(edu[0].degree) : "-"));

    const institute =
        edu.length
            ? value(
                edu[0].institution ||
                edu[0].board_university
            )
            : "-";

    $("highestDegree").textContent =
        highestDegree;

    $("currentPosition").textContent =
        value(
            p.current_designation ||
            experience()[0]?.designation
        );

    $("currentInstitute").textContent =
        institute;

    $("experienceText").textContent =
        `${expYears} Years`;

    $("aiSummary").innerHTML = createSummary();

}



/* ==========================================================
                AI SUMMARY
========================================================== */

function createSummary() {

    const p = personal();

    const pub = publications();

    const years =
        parseExperienceYears(
            p.total_experience
        );

    const highestDegree =
        facultyData.normalized_highest_degree ||
        (window.DegreeNormalizer
            ? window.DegreeNormalizer.getHighestDegree(education())
            : (education().length ? normalizeDegree(education()[0].degree) : "-"));

    return `
        <p>
            <strong>${value(p.full_name)}</strong>
            is an
            <strong>${value(
                p.current_designation ||
                "Faculty Member"
            )}</strong>
            with approximately
            <strong>${years} years</strong>
            of academic experience.
        </p>

        <br>

        <p>
            Highest qualification:
            <strong>${highestDegree}</strong>.
        </p>

        <br>

        <p>
            Research output includes
            <strong>${pub.journal_publications || 0}</strong>
            journal publications,
            <strong>${pub.conference_publications || 0}</strong>
            conference papers and
            <strong>${pub.patents || 0}</strong>
            patents.
        </p>
    `;

}



/* ==========================================================
                EXPERIENCE PARSER
========================================================== */

function parseExperienceYears(text) {

    if (!text) return 0;

    const match =
        String(text).match(/\d+/);

    return match
        ? Number(match[0])
        : 0;

}

/* ==========================================================
                RENDER EDUCATION
========================================================== */

function renderEducation() {

    const container = $("educationTimeline");

    container.innerHTML = "";

    const list = education();

    if (!list.length) {

        container.innerHTML = `
            <div class="timeline-item">
                <div class="timeline-title">
                    No education information available
                </div>
            </div>
        `;

        return;

    }

    list.forEach(item => {
        const canonical = item.normalized_degree || normalizeDegree(item.degree);
        const rawDegree = item.degree && item.degree.trim() !== canonical ? item.degree.trim() : "";

        container.innerHTML += `

            <div class="timeline-item">

                <div class="timeline-title">

                    ${canonical}
                    ${rawDegree ? `<span style="font-size:13px; font-weight:normal; opacity:0.85; margin-left:8px;">(${rawDegree})</span>` : ""}

                </div>

                <div class="timeline-subtitle">

                    ${value(
                        item.institution ||
                        item.board_university
                    )}

                </div>

                <div class="timeline-meta">

                    ${value(item.year)}

                </div>

            </div>

        `;

    });

}



/* ==========================================================
                RENDER EXPERIENCE
========================================================== */

function renderExperience() {

    const container = $("experienceTimeline");

    container.innerHTML = "";

    const list = experience();

    if (!list.length) {

        container.innerHTML = `
            <div class="timeline-item">
                <div class="timeline-title">
                    No experience information available
                </div>
            </div>
        `;

        return;

    }

    list.forEach(item => {

        container.innerHTML += `

            <div class="timeline-item">

                <div class="timeline-title">

                    ${value(item.designation)}

                </div>

                <div class="timeline-subtitle">

                    ${value(
                        item.organization ||
                        item.institution ||
                        item.company
                    )}

                </div>

                <div class="timeline-meta">

                    ${value(item.start_date)}

                    ${item.end_date
                        ? " - " + item.end_date
                        : ""}

                </div>

            </div>

        `;

    });

}



/* ==========================================================
                RENDER RESEARCH
========================================================== */

function renderResearch() {

    const pub = publications();

    $("journalPublications").textContent =
        pub.journal_publications || 0;

    $("conferencePublications").textContent =
        pub.conference_publications || 0;

    $("patentPublications").textContent =
        pub.patents || 0;

}



/* ==========================================================
                RENDER SKILLS
========================================================== */

function renderSkills() {

    const container = $("skillsContainer");

    container.innerHTML = "";

    const raw = facultyData;

    const skillSet = new Set();

    [
        ...(raw.skills || []),
        ...(raw.technical_skills || []),
        ...(raw.key_skills || []),
        ...(raw.core_skills || [])
    ].forEach(skill => {

        if (!skill) return;

        if (typeof skill === "string") {

            skillSet.add(skill.trim());

        }

        else if (skill.name) {

            skillSet.add(skill.name.trim());

        }

    });

    const skills = [...skillSet];

    if (!skills.length) {

        container.innerHTML = `

            <div class="empty-card">

                No skills extracted.

            </div>

        `;

        return;

    }

    skills.forEach(skill => {

        const badge = document.createElement("span");

        badge.className = "skill-chip";

        badge.textContent = skill;

        container.appendChild(badge);

    });

}
/* ==========================================================
                TAB SWITCHING
========================================================== */

function initializeTabs() {

    const buttons =
        document.querySelectorAll(".tab-btn");

    const panels =
        document.querySelectorAll(".tab-panel");

    buttons.forEach(button => {

        button.addEventListener("click", () => {

            buttons.forEach(btn =>
                btn.classList.remove("active")
            );

            panels.forEach(panel =>
                panel.classList.remove("active")
            );

            button.classList.add("active");

            const target =
                button.dataset.tab;

            document
                .getElementById(target)
                .classList.add("active");

        });

    });

}



/* ==========================================================
                JSON MODAL
========================================================== */

function initializeJsonModal() {

    const modal = $("jsonModal");

    const viewer = $("jsonViewer");

    $("jsonBtn").addEventListener("click", () => {

        viewer.textContent =
            JSON.stringify(
                facultyData,
                null,
                2
            );

        modal.classList.add("active");

    });

    $("closeModal").addEventListener("click", () => {

        modal.classList.remove("active");

    });

    modal.addEventListener("click", e => {

        if (e.target === modal) {

            modal.classList.remove("active");

        }

    });

}



/* ==========================================================
                RESUME BUTTON
========================================================== */

function initializeResumeButton() {

    $("resumeBtn").addEventListener("click", () => {

        const extensions = [
            ".pdf",
            ".docx",
            ".doc"
        ];

        for (const ext of extensions) {

            const url =
                `${RESUME_FOLDER}${facultyId}${ext}`;

            window.open(url, "_blank");

            break;

        }

    });

}



/* ==========================================================
                DOWNLOAD JSON
========================================================== */

function initializeDownloadButton() {

    $("downloadBtn").addEventListener("click", () => {

        const blob = new Blob(

            [
                JSON.stringify(
                    facultyData,
                    null,
                    2
                )
            ],

            {
                type: "application/json"
            }

        );

        const url =
            URL.createObjectURL(blob);

        const a =
            document.createElement("a");

        a.href = url;

        a.download =
            `${facultyId}.json`;

        document.body.appendChild(a);

        a.click();

        a.remove();

        URL.revokeObjectURL(url);

    });

}



/* ==========================================================
                LOADER
========================================================== */

function showLoader(show) {

    const loader =
        $("loadingScreen");

    if (!loader) return;

    loader.style.display =
        show ? "flex" : "none";

}



/* ==========================================================
                TOAST
========================================================== */

function showToast(message) {

    const toast =
        $("toast");

    if (!toast) return;

    $("toastMessage").textContent =
        message;

    toast.classList.add("show");

    setTimeout(() => {

        toast.classList.remove("show");

    }, 2500);

}



/* ==========================================================
                INITIALIZE COMPONENTS
========================================================== */

function initializeComponents() {

    initializeTabs();

    initializeJsonModal();

    initializeResumeButton();

    initializeDownloadButton();

}



/* ==========================================================
                UPDATE INIT()
========================================================== */

/*
Replace the end of your init() function with:

facultyData = await loadFacultyJSON(facultyId);

populatePage();

initializeComponents();

showLoader(false);

*/


/* ==========================================================
                OPTIONAL
========================================================== */

/*
If your index.html passes the filename instead of
an ID, for example

faculty.html?id=resume1

everything will work automatically because

resume1.json
resume1.pdf

will both be used.

No further changes required.
*/