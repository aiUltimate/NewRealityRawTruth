(() => {
  const clean = (value) => (value || "").replace(/\\s+/g, " ").trim();
  function extract() {
    const main = document.querySelector("article, main, [role='main']") || document.body;
    const text = clean(main?.innerText || "").slice(0, 18000);
    const comments = Array.from(document.querySelectorAll(
      '[role="comment"], [data-testid*="comment"], .comment'
    )).map(node => clean(node.innerText)).filter(Boolean).slice(0, 50);
    return {
      url: location.href,
      title: document.title || "",
      text,
      comments,
      metadata: {
        description: document.querySelector('meta[name="description"]')?.content || "",
        author: document.querySelector('meta[name="author"]')?.content || "",
        published: document.querySelector('meta[property="article:published_time"]')?.content || ""
      }
    };
  }
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message?.type === "OMNI_EXTRACT_PAGE") {
      try { sendResponse({ ok: true, page: extract() }); }
      catch (error) { sendResponse({ ok: false, error: String(error) }); }
    }
    return true;
  });
})();