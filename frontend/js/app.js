(function () {
  const app = {
    init() {
      window.addEventListener("candidates:loaded", (event) => {
        const { candidates, stats } = event.detail;
        this.renderStats(stats);
        this.renderFacultyCards(candidates);
        this.populateFilters(candidates);
      });

      document.getElementById("theme-toggle")?.addEventListener("click", () => {
        const current = document.documentElement.getAttribute("data-theme") || "dark";
        const next = current === "dark" ? "light" : "dark";
        window.loader.applyTheme(next);
      });
    },

    renderStats(stats) {

    const container = document.getElementById("stats-grid");

    if (!container) return;

    const cards = [

        {
            icon: "👨‍🏫",
            title: "Total Faculty",
            value: stats.total
        },

        {
            icon: "🎓",
            title: "PhD Faculty",
            value: stats.phd
        },

        {
            icon: "🧑‍🏫",
            title: "Assistant Professors",
            value: stats.assistant
        },

        {
            icon: "👥",
            title: "Associate Professors",
            value: stats.associate
        },

        {
            icon: "🏛️",
            title: "Professors",
            value: stats.professor
        },

        {
            icon: "📅",
            title: "Average Experience",
            value: `${stats.average} yrs`
        },

        {
            icon: "📚",
            title: "Journal Publications",
            value: stats.journal
        },

        {
            icon: "📖",
            title: "Conference Publications",
            value: stats.conference
        },

        {
            icon: "📜",
            title: "Patents",
            value: stats.patents
        },

        {
            icon: "🏫",
            title: "Universities",
            value: stats.universities
        }

    ];

    container.innerHTML = cards.map(card => `

        <article class="metric-card">

            <div class="metric-icon">

                ${card.icon}

            </div>

            <div class="metric-title">

                ${card.title}

            </div>

            <div class="metric-value">

                ${card.value}

            </div>

        </article>

    `).join("");

},

    renderFacultyCards(candidates) {
      const container = document.getElementById("faculty-grid");
      const resultsCount = document.getElementById("results-count");
      if (!container) return;
      if (!candidates.length) {
        container.innerHTML = '<div class="empty-state">No faculty matched the current selection.</div>';
        if (resultsCount) resultsCount.textContent = "0 results";
        return;
      }
      if (resultsCount) resultsCount.textContent = `${candidates.length} results`;
      container.innerHTML = candidates.map((candidate) => this.buildCard(candidate)).join("");
      container.querySelectorAll(".view-btn").forEach((button) => {
        button.addEventListener("click", () => {
          const id = button.getAttribute("data-id");
          window.location.href = `faculty.html?id=${id}`;
        });
      });
    },

    buildCard(candidate) {

    const avatar = this.getInitials(candidate.fullName || "Faculty");

    const publications =
        Number(candidate.publicationSummary?.journal_publications || 0) +
        Number(candidate.publicationSummary?.conference_publications || 0);

    const institute =
        candidate.institution ||
        candidate.university ||
        "University";

    return `

    <article class="faculty-card">

        <div class="faculty-card-header">

            <div class="faculty-card-left">

                <div class="faculty-card__avatar">

                    ${avatar}

                </div>

                <div>

                    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">

                        <h3>${candidate.fullName || "Faculty"}</h3>

                        ${this.getDegreeBadge(candidate.highestDegree)}

                    </div>

                    <div class="designation">

                        ${candidate.designation || "Faculty"}

                    </div>

                </div>

            </div>

        </div>

        <div class="university-row">

            <i class="fa-solid fa-building-columns"></i>

            <span>${institute}</span>

        </div>

        <div class="mini-stats">

    <div class="mini-card">

        <span class="mini-value">

            ${candidate.experienceYears || 0}

        </span>

        <span class="mini-label">

            Years

        </span>

    </div>

    <div class="mini-card">

        <span class="mini-value">

            ${publications}

        </span>

        <span class="mini-label">

            Publications

        </span>

    </div>

    <div class="mini-card">

        <span class="mini-value">

            ${this.normalizeDegree(candidate.highestDegree)}

        </span>

        <span class="mini-label">

            Degree

        </span>

    </div>

</div>

        <div class="faculty-card__footer">

            <button
                class="view-btn"
                data-id="${candidate.id}">

                View Full Profile →

            </button>

        </div>

    </article>

    `;

},

    normalizeDegree(degree) {
      if (!degree) return "";
      if (window.DegreeNormalizer) {
        return window.DegreeNormalizer.normalizeDegree(degree);
      }
      return degree;
    },

    getDegreeBadge(degree) {
      const normalized = this.normalizeDegree(degree);
      if (normalized === "Ph.D.") {
        return `<span class="degree-badge">Ph.D.</span>`;
      }
      if (normalized === "Post Doctoral") {
        return `<span class="degree-badge" style="background:#4f46e5;">Postdoc</span>`;
      }
      return "";
    },

    getInitials(fullName) {
      return fullName.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
    },

    populateFilters(candidates) {
      const canonicalDegreeSet = new Set();
      candidates.forEach((c) => {
        if (c.highestDegree && c.highestDegree !== "Other") {
          canonicalDegreeSet.add(c.highestDegree);
        }
        if (Array.isArray(c.allDegrees)) {
          c.allDegrees.forEach((d) => {
            if (d && d !== "Other") canonicalDegreeSet.add(d);
          });
        }
      });

      const degrees = [
        "",
        ...Array.from(canonicalDegreeSet).sort((a, b) => {
          const rankA = window.DegreeNormalizer ? window.DegreeNormalizer.getDegreeRank(a) : 0;
          const rankB = window.DegreeNormalizer ? window.DegreeNormalizer.getDegreeRank(b) : 0;
          if (rankB !== rankA) return rankB - rankA;
          return a.localeCompare(b);
        }),
      ];

      const institutes = ["", ...new Set(candidates.map((item) => item.institution).filter(Boolean))].sort();
      const designations = ["", ...new Set(candidates.map((item) => item.designation).filter(Boolean))].sort();
      const experiences = ["", "0-2", "2-5", "5-10", "10+"];
      this.fillSelect("filter-degree", degrees, "Any degree");
      this.fillSelect("filter-institute", institutes, "Any institute");
      this.fillSelect("filter-designation", designations, "Any designation");
      this.fillSelect("filter-experience", experiences, "Any experience");
    },

    fillSelect(id, values, placeholder) {
      const select = document.getElementById(id);
      if (!select) return;
      select.innerHTML = values.map((value) => `<option value="${value || ""}">${value || placeholder}</option>`).join("");
    },
  };

  window.app = app;
  window.addEventListener("DOMContentLoaded", () => app.init());
})();
