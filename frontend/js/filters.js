(function () {
  const filters = {
    init() {
      document.getElementById("apply-filters")?.addEventListener("click", () => this.applyFilters());
      document.getElementById("clear-filters")?.addEventListener("click", () => this.clearFilters());
      window.addEventListener("candidates:loaded", () => {
        this.attachFilterState();
      });
    },

    attachFilterState() {
      const state = window.loader.state.filters;
      document.getElementById("filter-degree") && (document.getElementById("filter-degree").value = state.degree || "");
      document.getElementById("filter-institute") && (document.getElementById("filter-institute").value = state.institute || "");
      document.getElementById("filter-designation") && (document.getElementById("filter-designation").value = state.designation || "");
      document.getElementById("filter-experience") && (document.getElementById("filter-experience").value = state.experience || "");
      document.getElementById("filter-journal") && (document.getElementById("filter-journal").checked = state.journal || false);
      document.getElementById("filter-conference") && (document.getElementById("filter-conference").checked = state.conference || false);
      document.getElementById("filter-patent") && (document.getElementById("filter-patent").checked = state.patent || false);
    },

    applyFilters() {
      const state = window.loader.state;
      state.filters.degree = document.getElementById("filter-degree")?.value || "";
      state.filters.institute = document.getElementById("filter-institute")?.value || "";
      state.filters.designation = document.getElementById("filter-designation")?.value || "";
      state.filters.experience = document.getElementById("filter-experience")?.value || "";
      state.filters.journal = document.getElementById("filter-journal")?.checked || false;
      state.filters.conference = document.getElementById("filter-conference")?.checked || false;
      state.filters.patent = document.getElementById("filter-patent")?.checked || false;
      state.applied = true;
      this.renderFiltered();
    },

    clearFilters() {
      const state = window.loader.state;
      state.filters = { degree: "", institute: "", designation: "", experience: "", journal: false, conference: false, patent: false };
      state.applied = false;
      this.attachFilterState();
      this.renderFiltered();
    },

    renderFiltered() {
      const state = window.loader.state;
      const filtered = state.candidates.filter((candidate) => {
        const degree = state.filters.degree;
        const institute = state.filters.institute;
        const designation = state.filters.designation;
        const experience = state.filters.experience;
        const search = state.search.toLowerCase();
        const matchesSearch = !search || [candidate.fullName, candidate.designation, candidate.university, candidate.highestDegree].join(" ").toLowerCase().includes(search);
        const matchesDegree = !degree || (candidate.highestDegree || "").toLowerCase().includes(degree.toLowerCase());
        const matchesInstitute = !institute || (candidate.institution || "").toLowerCase().includes(institute.toLowerCase());
        const matchesDesignation = !designation || (candidate.designation || "").toLowerCase().includes(designation.toLowerCase());
        const matchesExperience = !experience || this.matchesExperience(candidate.experienceYears, experience);
        const matchesJournal = !state.filters.journal || Number(candidate.publicationSummary?.journal_publications || 0) > 0;
        const matchesConference = !state.filters.conference || Number(candidate.publicationSummary?.conference_publications || 0) > 0;
        const matchesPatent = !state.filters.patent || Number(candidate.publicationSummary?.patents || 0) > 0;
        return matchesSearch && matchesDegree && matchesInstitute && matchesDesignation && matchesExperience && matchesJournal && matchesConference && matchesPatent;
      });
      window.app.renderFacultyCards(filtered);
    },

    matchesExperience(years, range) {
      const value = Number(years || 0);
      switch (range) {
        case "0-2": return value <= 2;
        case "2-5": return value > 2 && value <= 5;
        case "5-10": return value > 5 && value <= 10;
        case "10+": return value > 10;
        default: return true;
      }
    },
  };

  window.filters = filters;
  window.addEventListener("DOMContentLoaded", () => filters.init());
})();
