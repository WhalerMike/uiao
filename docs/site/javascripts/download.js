document.addEventListener("DOMContentLoaded", function () {
  const UIAO_REPO = "WhalerMike/uiao-docs";
  const EXPORT_WORKFLOW = "document-export.yml";
  const hideList = ["/", "/index.html"];

  var path = window.location.pathname;
  if (hideList.some(function (p) { return path.endsWith(p); })) {
    var bar = document.getElementById("uiao-download-bar");
    if (bar) bar.style.display = "none";
  }
});
