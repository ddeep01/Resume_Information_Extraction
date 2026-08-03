(function () {
  const search = {
    init() {
      const input = document.getElementById("search-input");
      if (!input) return;
      input.addEventListener("input", (event) => {
        window.loader.state.search = event.target.value.trim();
        window.filters.renderFiltered();
      });
    },
  };

  window.search = search;
  window.addEventListener("DOMContentLoaded", () => search.init());
})();
