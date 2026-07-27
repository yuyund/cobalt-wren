(() => {
  "use strict";

  const FALLBACK_INTERVAL_MS = 10000;

  function replaceFragment(current, html) {
    const template = document.createElement("template");
    template.innerHTML = html.trim();
    const replacement = template.content.firstElementChild;
    if (!replacement) return current;
    current.replaceWith(replacement);
    return replacement;
  }

  function startFallback(root) {
    if (root.dataset.fallbackStarted === "true" || root.dataset.terminal === "true") return;
    root.dataset.fallbackStarted = "true";
    const fragmentUrl = root.dataset.fragmentUrl;
    if (!fragmentUrl) return;
    const refresh = () => {
      if (!document.contains(root) || root.dataset.terminal === "true") return;
      if (globalThis.htmx) {
        globalThis.htmx.ajax("GET", fragmentUrl, {target: root, swap: "outerHTML"});
      }
    };
    window.setInterval(refresh, FALLBACK_INTERVAL_MS);
  }

  function connect(root) {
    if (!(root instanceof HTMLElement) || root.id !== "run-live-state") return;
    if (root.dataset.terminal === "true") return;
    const streamUrl = root.dataset.streamUrl;
    if (!streamUrl || !("EventSource" in window)) {
      startFallback(root);
      return;
    }
    if (root.dataset.streamConnected === "true") return;
    root.dataset.streamConnected = "true";
    const source = new EventSource(streamUrl);
    source.addEventListener("fragment", (event) => {
      let payload;
      try {
        payload = JSON.parse(event.data);
      } catch (_error) {
        return;
      }
      const replacement = replaceFragment(root, payload.html || "");
      if (payload.terminal === true) source.close();
      root = replacement;
    });
    source.addEventListener("unavailable", () => source.close());
    source.onerror = () => {
      root.dataset.streamConnected = "false";
      startFallback(root);
    };
  }

  document.addEventListener("DOMContentLoaded", () => connect(document.getElementById("run-live-state")));
  document.addEventListener("htmx:afterSwap", (event) => connect(event.target));
})();
