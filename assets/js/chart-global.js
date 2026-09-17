(function (g) {
  if (g.Chart) return;
  if (typeof Chart !== "undefined") {
    g.Chart = Chart;
    return;
  }
  try {
    if (typeof module !== "undefined" && module.exports) {
      g.Chart = module.exports.Chart || module.exports;
    }
  } catch (err) {}
})(typeof window !== "undefined" ? window : globalThis);
