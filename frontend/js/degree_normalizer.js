(function () {
  const DEGREE_HIERARCHY = {
    "Post Doctoral": 90,
    "Ph.D.": 80,
    "M.Tech": 70,
    "M.E.": 70,
    "M.Sc.": 70,
    "MCA": 70,
    "MBA": 70,
    "M.A.": 70,
    "M.Phil.": 70,
    "M.S.": 70,
    "B.Tech": 60,
    "B.E.": 60,
    "B.Sc.": 60,
    "BCA": 60,
    "B.A.": 60,
    "B.Ed": 60,
    "Diploma": 50,
    "Higher Secondary (12th)": 40,
    "Secondary (10th)": 30,
    "Other": 10,
  };

  const DegreeNormalizer = {
    DEGREE_HIERARCHY,

    normalizeDegree(rawDegree) {
      if (!rawDegree || typeof rawDegree !== "string") {
        return "Other";
      }

      const s = rawDegree.trim();
      if (!s) return "Other";
      const lower = s.toLowerCase();

      // 1. Post Doctoral
      if (
        lower.includes("post doc") ||
        lower.includes("postdoc") ||
        lower.includes("post-doc") ||
        lower.includes("post doctoral")
      ) {
        return "Post Doctoral";
      }

      // 2. Ph.D. / Doctorate / Doctor of Philosophy
      if (
        lower.includes("ph.d") ||
        lower.includes("phd") ||
        lower.includes("doctor of philosophy") ||
        lower.includes("doctorate") ||
        lower.includes("dr. of philosophy") ||
        lower.includes("ph. d")
      ) {
        return "Ph.D.";
      }

      // 3. M.Tech / Master of Technology
      if (
        lower.includes("m.tech") ||
        lower.includes("mtech") ||
        lower.includes("m. tech") ||
        lower.includes("master of technology") ||
        lower.includes("masters in technology")
      ) {
        return "M.Tech";
      }

      // 4. B.Tech / Bachelor of Technology
      if (
        lower.includes("b.tech") ||
        lower.includes("btech") ||
        lower.includes("b. tech") ||
        lower.includes("bachelor of technology")
      ) {
        return "B.Tech";
      }

      // 5. MBA / Master of Business Administration
      if (
        lower.includes("mba") ||
        lower.includes("m.b.a") ||
        lower.includes("master of business administration")
      ) {
        return "MBA";
      }

      // 6. M.E. / Master of Engineering
      if (
        lower.includes("master of engineering") ||
        lower.includes("m.e") ||
        lower === "me" ||
        /\bm\.?e\.?\b/.test(lower)
      ) {
        if (!lower.includes("mech") && !lower.includes("media")) {
          return "M.E.";
        }
      }

      // 7. B.E. / Bachelor of Engineering
      if (
        lower.includes("bachelor of engineering") ||
        lower.includes("b.e") ||
        lower === "be" ||
        /\bb\.?e\.?\b/.test(lower)
      ) {
        return "B.E.";
      }

      // 8. MCA / Master of Computer Applications / Master of Computer Science
      if (
        lower.includes("mca") ||
        lower.includes("m.c.a") ||
        lower.includes("master of computer application") ||
        lower.includes("masters in computer application") ||
        lower.includes("msc cs") ||
        lower.includes("master of computer science")
      ) {
        return "MCA";
      }

      // 9. BCA / Bachelor of Computer Applications
      if (
        lower.includes("bca") ||
        lower.includes("b.c.a") ||
        lower.includes("bachelor of computer application")
      ) {
        return "BCA";
      }

      // 10. M.Sc. / Master of Science
      if (
        lower.includes("m.sc") ||
        lower.includes("msc") ||
        lower.includes("m. sc") ||
        lower.includes("m sc") ||
        lower.includes("master of science") ||
        lower.includes("masters of science") ||
        lower.includes("master in science")
      ) {
        return "M.Sc.";
      }

      // 11. B.Sc. / Bachelor of Science
      if (
        lower.includes("b.sc") ||
        lower.includes("bsc") ||
        lower.includes("b. sc") ||
        lower.includes("b sc") ||
        lower.includes("bachelor of science") ||
        lower.includes("bachelor in science")
      ) {
        return "B.Sc.";
      }

      // 12. M.Phil. / Master of Philosophy
      if (
        lower.includes("m.phil") ||
        lower.includes("mphil") ||
        lower.includes("master of philosophy")
      ) {
        return "M.Phil.";
      }

      // 13. M.S. / Master of Science (MS)
      if (/\bm\.?s\.?\b/.test(lower)) {
        return "M.S.";
      }

      // 14. M.A. / Master of Arts / MSW
      if (
        lower.includes("m.a") ||
        lower.includes("master of arts") ||
        lower.includes("master in arts") ||
        lower.includes("master of social work") ||
        lower.includes("msw")
      ) {
        return "M.A.";
      }

      // 15. B.A. / Bachelor of Arts
      if (
        lower.includes("b.a") ||
        lower.includes("ba(h)") ||
        lower.includes("bachelor of arts")
      ) {
        return "B.A.";
      }

      // 16. B.Ed / Bachelor of Education
      if (lower.includes("b.ed") || lower.includes("bachelor of education")) {
        return "B.Ed";
      }

      // 17. Diploma
      if (lower.includes("diploma")) {
        return "Diploma";
      }

      // 18. Higher Secondary (12th)
      if (
        ["12th", "10+2", "hsc", "h.s.c", "higher secondary", "senior secondary", "intermediate", "pre degree", "w.b.c.h.s.e", "a levels"].some(
          (p) => lower.includes(p)
        )
      ) {
        return "Higher Secondary (12th)";
      }

      // 19. Secondary (10th)
      if (
        ["10th", "ssc", "s.s.c", "secondary", "high school", "madhyamik", "matric", "metric", "sslc", "w.b.b.s.e"].some(
          (p) => lower.includes(p)
        )
      ) {
        return "Secondary (10th)";
      }

      return "Other";
    },

    getDegreeRank(canonicalDegree) {
      return DEGREE_HIERARCHY[canonicalDegree] || 10;
    },

    getHighestDegree(educationList) {
      if (!Array.isArray(educationList) || !educationList.length) {
        return "Other";
      }
      let highest = "Other";
      let highestRank = 0;

      for (const item of educationList) {
        if (!item) continue;
        const norm = item.normalized_degree || this.normalizeDegree(item.degree);
        const rank = this.getDegreeRank(norm);
        if (rank > highestRank) {
          highestRank = rank;
          highest = norm;
        }
      }

      return highest;
    },
  };

  window.DegreeNormalizer = DegreeNormalizer;
})();
