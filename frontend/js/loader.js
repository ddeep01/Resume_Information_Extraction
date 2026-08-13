(function () {
  const loader = {
    state: {
      candidates: [],
      stats: {},
      filters: {
        degree: "",
        institute: "",
        designation: "",
        experience: "",
        journal: false,
        conference: false,
        patent: false,
      },
      search: "",
      theme: document.documentElement.getAttribute("data-theme") || "dark",
      applied: false,
    },

    init() {
      this.loadCandidates();
      this.attachTheme();
    },

    attachTheme() {
      const savedTheme = localStorage.getItem("faculty-theme") || this.state.theme;
      this.applyTheme(savedTheme);
    },

    applyTheme(theme) {
      document.documentElement.setAttribute("data-theme", theme);
      document.body.classList.toggle("light", theme === "light");
      localStorage.setItem("faculty-theme", theme);
      this.state.theme = theme;
      const icon = document.getElementById("theme-toggle")?.querySelector("i");
      if (icon) {
        icon.className = theme === "dark" ? "fa-solid fa-moon" : "fa-solid fa-sun";
      }
    },

    getJsonBaseUrl() {
      return new URL("../evaluation/result_llm/data/qwen2.5_7b/", window.location.href);
    },

    getResumeBaseUrl() {
      return new URL("../data/raw_resumes/", window.location.href);
    },

    async loadCandidates() {
      const available = [];
      const files = [];
      for (let i = 1; i <= 40; i += 1) {
        const id = String(i).padStart(3, "0");
        files.push(`R-${id}.json`);
      }
      for (const file of files) {
        try {
          const url = new URL(file, this.getJsonBaseUrl());
          const res = await fetch(url);
          if (!res.ok) continue;
          const data = await res.json();
          available.push(this.normalizeCandidate(data, file));
        } catch (error) {
          continue;
        }
      }
      this.state.candidates = available;
      this.state.stats = this.computeStats(available);
      window.dispatchEvent(new CustomEvent("candidates:loaded", { detail: { candidates: available, stats: this.state.stats } }));
    },

    normalizeCandidate(data, fileName) {
      const personal = data.personal_information || {};
      const education = data.education || [];
      const experience = data.experience || [];
      const publicationSummary = data.publication_summary || {};
      const id = fileName.replace(/\.json$/i, "");
      const resumeName = this.findResume(id);

      const normEdu = education.map((item) => ({
        ...item,
        normalized_degree:
          item.normalized_degree ||
          (window.DegreeNormalizer ? window.DegreeNormalizer.normalizeDegree(item.degree) : item.degree || ""),
      }));

      const highestDegree =
        data.normalized_highest_degree ||
        (window.DegreeNormalizer ? window.DegreeNormalizer.getHighestDegree(normEdu) : normEdu[0]?.degree || "");

      const allCanonicalDegrees = [
        ...new Set(
          normEdu
            .map((e) => e.normalized_degree || (window.DegreeNormalizer ? window.DegreeNormalizer.normalizeDegree(e.degree) : e.degree || ""))
            .filter((d) => d && d !== "Other")
        ),
      ];

      return {
        id,
        fileName,
        fullName: personal.full_name || id,
        designation: personal.current_designation || experience[0]?.designation || "Faculty Member",
        highestDegree,
        rawHighestDegree: education[0]?.degree || "",
        allDegrees: allCanonicalDegrees,
        institution: education[0]?.institution || education[0]?.board_university || "",
        university: education[0]?.institution || "",
        experienceText: personal.total_experience || this.getExperienceText(experience),
        experienceYears: this.parseExperience(personal.total_experience || this.getExperienceText(experience)),
        email: personal.email || "",
        phone: personal.phone || "",
        address: personal.address || "",
        gender: personal.gender || "",
        dateOfBirth: personal.date_of_birth || "",
        linkedin: personal.linkedin || "",
        googleScholar: personal.google_scholar || "",
        researchGate: personal.researchgate || "",
        education: normEdu,
        experience,
        publicationSummary,
        resumePath: resumeName,
        raw: data,
      };
    },

    findResume(id) {
      const candidates = [".pdf", ".docx", ".doc"].map((ext) => new URL(`${id}${ext}`, this.getResumeBaseUrl()).href);
      return candidates[0];
    },

    getExperienceText(experience) {
      if (!experience || !experience.length) return "0 years";
      return `${experience.length} roles`;
    },

    parseExperience(value) {
      if (!value) return 0;
      const match = String(value).match(/(\d+)/);
      return match ? Number(match[1]) : 0;
    },

    getExperienceRange(years) {
      if (years <= 2) return "0-2";
      if (years <= 5) return "2-5";
      if (years <= 10) return "5-10";
      return "10+";
    },

    computeStats(candidates) {
      const total = candidates.length;
      const phd = candidates.filter((item) => item.highestDegree === "Ph.D." || (item.allDegrees && item.allDegrees.includes("Ph.D."))).length;
      const assistant = candidates.filter((item) => /assistant/i.test(item.designation || "")).length;
      const associate = candidates.filter((item) => /associate/i.test(item.designation || "")).length;
      const professor = candidates.filter((item) => /professor/i.test(item.designation || "")).length;
      const average = total ? (candidates.reduce((sum, item) => sum + (item.experienceYears || 0), 0) / total).toFixed(1) : 0;
      const journal = candidates.reduce((sum, item) => sum + Number(item.publicationSummary?.journal_publications || 0), 0);
      const conference = candidates.reduce((sum, item) => sum + Number(item.publicationSummary?.conference_publications || 0), 0);
      const patents = candidates.reduce((sum, item) => sum + Number(item.publicationSummary?.patents || 0), 0);
      const universities = new Set(candidates.map((item) => item.university).filter(Boolean)).size;
      return { total, phd, assistant, associate, professor, average, journal, conference, patents, universities };
    },
  };

  window.loader = loader;
  window.addEventListener("DOMContentLoaded", () => loader.init());
})();
