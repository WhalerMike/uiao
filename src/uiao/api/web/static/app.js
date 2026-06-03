// OrgPath console — Run governance pass.
// Posts the textarea snapshot to /orgpath/api/govern and renders the report.
"use strict";

(function () {
  const btn = document.getElementById("run-btn");
  if (!btn) return;
  const statusEl = document.getElementById("run-status");
  const out = document.getElementById("report");

  const esc = (s) =>
    String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function severityBadges(counts) {
    return ["P1", "P2", "P3"]
      .map((s) => `<span class="badge badge-${s.toLowerCase()}">${s} ${counts[s] || 0}</span>`)
      .join(" ");
  }

  function renderReport(r) {
    const rows = (r.findings || [])
      .map(
        (f) => `<tr>
          <td><span class="badge badge-${esc(f.severity.toLowerCase())}">${esc(f.severity)}</span></td>
          <td><code>${esc(f.facet)}</code></td>
          <td>${esc(f.drift_category)}</td>
          <td class="reason">${esc(f.reason)}</td>
        </tr>`
      )
      .join("");

    out.innerHTML = `
      <div class="rsummary">
        <div class="rstat"><b>${r.drift_count}</b><span>drift</span></div>
        <div class="rstat"><b>${r.planned_count}</b><span>planned</span></div>
        <div class="rstat"><b>${r.remediated_count}</b><span>remediated</span></div>
        <div class="rstat"><b>${(r.events || []).length}</b><span>events</span></div>
      </div>
      <p>${severityBadges(r.severity_counts || {})}
         ${r.halted ? '<span class="badge badge-p1">HALTED</span>' : ""}</p>
      ${
        rows
          ? `<table class="grid"><thead><tr><th>Sev</th><th>Facet</th><th>Category</th><th>Reason</th></tr></thead><tbody>${rows}</tbody></table>`
          : '<p class="empty">No drift detected.</p>'
      }
      <p class="hint">Active snapshot updated — <a href="/orgpath/">view on the dashboard</a>.</p>`;
  }

  btn.addEventListener("click", async function () {
    let payload;
    try {
      payload = JSON.parse(document.getElementById("snapshot").value);
    } catch (e) {
      statusEl.textContent = "Invalid JSON: " + e.message;
      return;
    }
    statusEl.textContent = "Running…";
    btn.disabled = true;
    try {
      const resp = await fetch("/orgpath/api/govern", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!resp.ok) {
        statusEl.textContent = data.message || "Run failed.";
        return;
      }
      statusEl.textContent = "Done.";
      renderReport(data);
    } catch (e) {
      statusEl.textContent = "Request failed: " + e.message;
    } finally {
      btn.disabled = false;
    }
  });
})();
