(function () {
  const dashboard = {
    chartInstances: {},

    renderAnalyticsCharts(candidates) {
      if (!candidates || !candidates.length) return;

      this.renderDegreeChart(candidates);
      this.renderDesignationChart(candidates);
      this.renderExperienceChart(candidates);
      this.renderResearchChart(candidates);
    },

    destroyChart(chartId) {
      if (this.chartInstances[chartId]) {
        this.chartInstances[chartId].destroy();
        delete this.chartInstances[chartId];
      }
    },

    renderDegreeChart(candidates) {
      const canvas = document.getElementById("chart-degree");
      if (!canvas) return;
      this.destroyChart("chart-degree");

      const counts = {};
      candidates.forEach((c) => {
        const deg = c.highestDegree || "Other";
        counts[deg] = (counts[deg] || 0) + 1;
      });

      const labels = Object.keys(counts).sort((a, b) => counts[b] - counts[a]);
      const data = labels.map((l) => counts[l]);

      const ctx = canvas.getContext("2d");
      this.chartInstances["chart-degree"] = new Chart(ctx, {
        type: "bar",
        data: {
          labels,
          datasets: [
            {
              label: "Faculty Members",
              data,
              backgroundColor: "#163A63",
              borderColor: "#0B1F3A",
              borderWidth: 1,
              borderRadius: 6,
            },
          ],
        },
        options: {
          indexAxis: "y",
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
          },
          scales: {
            x: {
              beginAtZero: true,
              grid: { color: "#E2E8F0" },
              ticks: { color: "#64748B", precision: 0 },
            },
            y: {
              grid: { display: false },
              ticks: { color: "#0F172A", font: { weight: "600" } },
            },
          },
        },
      });
    },

    renderDesignationChart(candidates) {
      const canvas = document.getElementById("chart-designation");
      if (!canvas) return;
      this.destroyChart("chart-designation");

      const counts = {
        Professor: 0,
        "Associate Professor": 0,
        "Assistant Professor": 0,
        Researcher: 0,
        Other: 0,
      };

      candidates.forEach((c) => {
        const d = (c.designation || "").toLowerCase();
        if (d.includes("assistant")) counts["Assistant Professor"]++;
        else if (d.includes("associate")) counts["Associate Professor"]++;
        else if (d.includes("professor")) counts["Professor"]++;
        else if (d.includes("postdoc") || d.includes("research")) counts["Researcher"]++;
        else counts["Other"]++;
      });

      const labels = Object.keys(counts).filter((k) => counts[k] > 0);
      const data = labels.map((k) => counts[k]);

      const ctx = canvas.getContext("2d");
      this.chartInstances["chart-designation"] = new Chart(ctx, {
        type: "doughnut",
        data: {
          labels,
          datasets: [
            {
              data,
              backgroundColor: ["#0B1F3A", "#163A63", "#2563EB", "#C9A227", "#64748B"],
              borderWidth: 2,
              borderColor: "#FFFFFF",
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: "right", labels: { color: "#0F172A", font: { size: 12 } } },
          },
        },
      });
    },

    renderExperienceChart(candidates) {
      const canvas = document.getElementById("chart-experience");
      if (!canvas) return;
      this.destroyChart("chart-experience");

      const ranges = { "0-2 Yrs": 0, "2-5 Yrs": 0, "5-10 Yrs": 0, "10+ Yrs": 0 };
      candidates.forEach((c) => {
        const yrs = c.experienceYears || 0;
        if (yrs <= 2) ranges["0-2 Yrs"]++;
        else if (yrs <= 5) ranges["2-5 Yrs"]++;
        else if (yrs <= 10) ranges["5-10 Yrs"]++;
        else ranges["10+ Yrs"]++;
      });

      const labels = Object.keys(ranges);
      const data = labels.map((k) => ranges[k]);

      const ctx = canvas.getContext("2d");
      this.chartInstances["chart-experience"] = new Chart(ctx, {
        type: "bar",
        data: {
          labels,
          datasets: [
            {
              label: "Faculty Count",
              data,
              backgroundColor: "#2563EB",
              borderRadius: 6,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            y: { beginAtZero: true, grid: { color: "#E2E8F0" }, ticks: { precision: 0 } },
            x: { grid: { display: false } },
          },
        },
      });
    },

    renderResearchChart(candidates) {
      const canvas = document.getElementById("chart-research");
      if (!canvas) return;
      this.destroyChart("chart-research");

      let journals = 0;
      let conferences = 0;
      let patents = 0;

      candidates.forEach((c) => {
        journals += Number(c.publicationSummary?.journal_publications || 0);
        conferences += Number(c.publicationSummary?.conference_publications || 0);
        patents += Number(c.publicationSummary?.patents || 0);
      });

      const ctx = canvas.getContext("2d");
      this.chartInstances["chart-research"] = new Chart(ctx, {
        type: "bar",
        data: {
          labels: ["Journal Papers", "Conference Papers", "Patents"],
          datasets: [
            {
              label: "Total Publications",
              data: [journals, conferences, patents],
              backgroundColor: ["#0B1F3A", "#2563EB", "#C9A227"],
              borderRadius: 6,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            y: { beginAtZero: true, grid: { color: "#E2E8F0" }, ticks: { precision: 0 } },
            x: { grid: { display: false } },
          },
        },
      });
    },
  };

  window.dashboard = dashboard;
})();