(function () {
  const app = {
    viewMode: "table", // 'table' or 'grid'

    init() {
      window.addEventListener("candidates:loaded", (event) => {
        const { candidates, stats } = event.detail;
        this.renderStats(stats);
        this.renderFacultyDirectory(candidates);
        this.populateFilters(candidates);

        if (window.dashboard) {
          window.dashboard.renderAnalyticsCharts(candidates);
        }
      });

      this.attachViewSwitcher();
      this.attachTabSwitcher();
    },

    attachViewSwitcher() {
      const tableBtn = document.getElementById("view-table-btn");
      const gridBtn = document.getElementById("view-grid-btn");

      if (tableBtn && gridBtn) {
        tableBtn.addEventListener("click", () => {
          this.viewMode = "table";
          tableBtn.classList.add("active");
          gridBtn.classList.remove("active");
          const state = window.loader.state;
          if (window.filters) window.filters.renderFiltered();
          else this.renderFacultyDirectory(state.candidates);
        });

        gridBtn.addEventListener("click", () => {
          this.viewMode = "grid";
          gridBtn.classList.add("active");
          tableBtn.classList.remove("active");
          const state = window.loader.state;
          if (window.filters) window.filters.renderFiltered();
          else this.renderFacultyDirectory(state.candidates);
        });
      }
    },

    attachTabSwitcher() {
      const navItems = document.querySelectorAll("[data-tab]");
      navItems.forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.preventDefault();
          const targetTab = btn.getAttribute("data-tab");
          if (!targetTab) return;

          document.querySelectorAll(".portal-nav__item").forEach((b) => {
            b.classList.toggle("active", b.getAttribute("data-tab") === targetTab);
          });
          document.querySelectorAll(".sidebar-menu__link").forEach((b) => {
            b.classList.toggle("active", b.getAttribute("data-tab") === targetTab);
          });

          document.querySelectorAll(".tab-pane").forEach((pane) => {
            if (pane.id === targetTab) {
              pane.style.display = "block";
              pane.classList.add("active");
            } else {
              pane.style.display = "none";
              pane.classList.remove("active");
            }
          });

          if (targetTab === "tab-analytics" && window.dashboard) {
            window.dashboard.renderAnalyticsCharts(window.loader.state.candidates);
          }
        });
      });
    },

    renderStats(stats) {
      const container = document.getElementById("stats-grid");
      if (!container) return;

      const cards = [
        { icon: "fa-users", title: "Total Faculty", value: stats.total },
        { icon: "fa-graduation-cap", title: "PhD Faculty", value: stats.phd },
        { icon: "fa-user-tie", title: "Assistant Professors", value: stats.assistant },
        { icon: "fa-user-gear", title: "Associate Professors", value: stats.associate },
        { icon: "fa-award", title: "Professors", value: stats.professor },
        { icon: "fa-clock-rotate-left", title: "Avg. Experience", value: `${stats.average} yrs` },
        { icon: "fa-book-bookmark", title: "Journal Papers", value: stats.journal },
        { icon: "fa-scroll", title: "Conference Papers", value: stats.conference },
        { icon: "fa-stamp", title: "Patents", value: stats.patents },
        { icon: "fa-building-columns", title: "Universities", value: stats.universities },
      ];

      container.innerHTML = cards
        .map(
          (card) => `
        <article class="metric-card">
            <div class="metric-card__header">
                <span class="metric-card__title">${card.title}</span>
                <div class="metric-card__icon">
                    <i class="fa-solid ${card.icon}"></i>
                </div>
            </div>
            <div class="metric-card__value">${card.value}</div>
        </article>
      `
        )
        .join("");
    },

    renderFacultyCards(candidates) {
      this.renderFacultyDirectory(candidates);
    },

    renderFacultyDirectory(candidates) {
      const container = document.getElementById("faculty-directory-container");
      const resultsCount = document.getElementById("results-count");
      if (!container) return;

      if (resultsCount) {
        resultsCount.textContent = `${candidates.length} Faculty Profiles`;
      }

      if (!candidates.length) {
        container.innerHTML = `
          <div class="empty-state">
            <i class="fa-solid fa-users-slash"></i>
            <h3>No faculty members found</h3>
            <p>Try adjusting your search criteria or filter options.</p>
          </div>`;
        return;
      }

      if (this.viewMode === "table") {
        container.innerHTML = this.buildTable(candidates);
      } else {
        container.innerHTML = `
          <div class="faculty-grid">
            ${candidates.map((c) => this.buildCard(c)).join("")}
          </div>`;
      }

      container.querySelectorAll(".view-btn").forEach((button) => {
        button.addEventListener("click", () => {
          const id = button.getAttribute("data-id");
          window.location.href = `faculty.html?id=${id}`;
        });
      });
    },

    buildTable(candidates) {
      const rows = candidates.map((c) => this.buildTableRow(c)).join("");
      return `
        <div class="table-container">
          <table class="faculty-table">
            <thead>
              <tr>
                <th>Faculty Member</th>
                <th>Designation</th>
                <th>Institution</th>
                <th>Highest Degree</th>
                <th>Experience</th>
                <th>Publications</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              ${rows}
            </tbody>
          </table>
        </div>`;
    },

    buildTableRow(candidate) {
      const avatar = this.getInitials(candidate.fullName || "Faculty");
      const publications =
        Number(candidate.publicationSummary?.journal_publications || 0) +
        Number(candidate.publicationSummary?.conference_publications || 0);
      const institute = candidate.institution || candidate.university || "University";

      return `
        <tr>
          <td>
            <div class="table-faculty-cell">
              <div class="table-avatar">${avatar}</div>
              <div class="table-faculty-info">
                <h4>${candidate.fullName || "Faculty Member"}</h4>
                <p>${candidate.email || candidate.id}</p>
              </div>
            </div>
          </td>
          <td><strong>${candidate.designation || "Faculty"}</strong></td>
          <td>${institute}</td>
          <td>${this.getDegreeBadge(candidate.highestDegree)}</td>
          <td>${candidate.experienceYears || 0} Yrs</td>
          <td><strong>${publications}</strong> Papers</td>
          <td>
            <button class="btn btn-secondary view-btn" data-id="${candidate.id}" style="padding:4px 10px; font-size:12px;">
              View Profile &rarr;
            </button>
          </td>
        </tr>`;
    },

    buildCard(candidate) {
      const avatar = this.getInitials(candidate.fullName || "Faculty");
      const publications =
        Number(candidate.publicationSummary?.journal_publications || 0) +
        Number(candidate.publicationSummary?.conference_publications || 0);
      const institute = candidate.institution || candidate.university || "University";

      return `
      <article class="faculty-card">
        <div>
          <div class="faculty-card__top">
            <div class="faculty-card__avatar">${avatar}</div>
            <div class="faculty-card__meta">
              <h3>${candidate.fullName || "Faculty"}</h3>
              <div class="faculty-card__designation">${candidate.designation || "Faculty Member"}</div>
            </div>
          </div>

          <div class="faculty-card__institution">
            <i class="fa-solid fa-building-columns"></i>
            <span>${institute}</span>
          </div>

          <div class="faculty-card__stats">
            <div class="stat-item">
              <div class="stat-item__value">${candidate.experienceYears || 0} Yrs</div>
              <div class="stat-item__label">Experience</div>
            </div>
            <div class="stat-item">
              <div class="stat-item__value">${publications}</div>
              <div class="stat-item__label">Papers</div>
            </div>
            <div class="stat-item">
              <div class="stat-item__value">${this.normalizeDegree(candidate.highestDegree)}</div>
              <div class="stat-item__label">Degree</div>
            </div>
          </div>
        </div>

        <button class="btn btn-primary view-btn" data-id="${candidate.id}" style="width:100%;">
          View Profile &rarr;
        </button>
      </article>`;
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
        return `<span class="badge-canonical badge-phd"><i class="fa-solid fa-graduation-cap"></i> Ph.D.</span>`;
      }
      if (normalized === "Post Doctoral") {
        return `<span class="badge-canonical badge-postdoc"><i class="fa-solid fa-award"></i> Postdoc</span>`;
      }
      return `<span class="badge-canonical">${normalized || "Degree"}</span>`;
    },

    getInitials(fullName) {
      if (!fullName) return "F";
      return fullName
        .split(/\s+/)
        .slice(0, 2)
        .map((part) => part[0])
        .join("")
        .toUpperCase();
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

      this.fillSelect("filter-degree", degrees, "All Degrees");
      this.fillSelect("filter-institute", institutes, "All Institutions");
      this.fillSelect("filter-designation", designations, "All Designations");
      this.fillSelect("filter-experience", experiences, "Any Experience");
    },

    fillSelect(id, values, placeholder) {
      const select = document.getElementById(id);
      if (!select) return;
      select.innerHTML = values
        .map((value) => `<option value="${value || ""}">${value || placeholder}</option>`)
        .join("");
    },
  };

  window.app = app;
  window.addEventListener("DOMContentLoaded", () => app.init());
})();
