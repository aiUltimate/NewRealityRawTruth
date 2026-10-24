const $ = (id) => document.getElementById(id);
const endpoint = () => $("api").value.trim().replace(/\\/$/, "");
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function list(items) { return items?.length ? '<ul>' + items.map(x => '<li>'+esc(x)+'</li>').join('') + '</ul>' : '<p class="muted">No supported findings recorded.</p>'; }
function evidence(items) {
  if (!items?.length) return '<p class="muted">No excerpt-backed evidence recorded.</p>';
  return items.map(e => '<div class="evidence"><strong>“'+esc(e.excerpt || 'No excerpt')+'”</strong><p>'+esc(e.observation)+'</p><p class="muted">Interpretation: '+esc(e.interpretation)+' · Confidence: '+esc(e.confidence)+'</p></div>').join('');
}
function render(result) {
  $("results").innerHTML = `
    <div class="card"><h2>Reality brief</h2><p>${esc(result.summary)}</p><p class="muted">${esc(result.domain)} · ${esc(result.provider)} · confidence: ${esc(result.overall_confidence)}</p></div>
    <div class="card"><h2>1 · Economic & structural incentives</h2><div class="score">${esc(result.incentives.rating)}/100</div><p class="muted">Heuristic signal score, not a deception probability.</p><h3>Observable incentives</h3>${list(result.incentives.observable_incentives)}<h3>Hypotheses</h3>${list(result.incentives.hypotheses)}<h3>Evidence</h3>${evidence(result.incentives.evidence)}<h3>Unknowns</h3>${list(result.incentives.unknowns)}</div>
    <div class="card"><h2>2 · Narrative engineering & spin</h2><div class="score">${esc(result.spin.score)}/100</div><p class="muted">Heuristic framing-signal score; higher does not automatically mean false.</p><h3>Techniques</h3>${list(result.spin.techniques)}<h3>Omissions to investigate</h3>${list(result.spin.omissions_to_check)}<h3>Evidence</h3>${evidence(result.spin.evidence)}</div>
    <div class="card"><h2>3 · Behavioral psychology & crowd dynamics</h2><h3>Observed dynamics</h3>${list(result.psychology.observed_dynamics)}<h3>Possible mechanisms</h3>${list(result.psychology.possible_mechanisms)}<p>${esc(result.psychology.coordination_assessment)}</p><h3>Evidence</h3>${evidence(result.psychology.evidence)}</div>
    <div class="card"><h2>4 · First-principles reality</h2><p>${esc(result.raw_truth.plain_language_summary)}</p><h3>Factual claims</h3>${list(result.raw_truth.factual_claims)}<h3>Supported conclusions</h3>${list(result.raw_truth.supported_conclusions)}<h3>Unresolved questions</h3>${list(result.raw_truth.unresolved_questions)}<h3>Limitations</h3>${list(result.raw_truth.evidence_limitations)}</div>
    <div class="card"><h2>Caveats</h2>${list(result.caveats)}</div>`;
}
async function extractPage() {
  const [tab] = await chrome.tabs.query({active:true,currentWindow:true});
  if (!tab?.id || !/^https?:/.test(tab.url || "")) throw new Error("Open a regular http(s) webpage first.");
  try {
    const response = await chrome.tabs.sendMessage(tab.id, {type:"OMNI_EXTRACT_PAGE"});
    if (response?.ok && response.page?.text?.length >= 40) return response.page;
  } catch (_) {}
  // activeTab permits a one-time injection after the user clicks Analyze.
  const [page] = await chrome.scripting.executeScript({
    target:{tabId:tab.id}, func:() => ({
      url:location.href,title:document.title||"",
      text:((document.querySelector("article, main, [role='main']")||document.body)?.innerText||"").replace(/\\s+/g," ").trim().slice(0,18000),
      comments:[]
    })
  });
  if (!page?.result?.text || page.result.text.length < 40) throw new Error("Not enough readable page text was found.");
  return page.result;
}
$("analyze").addEventListener("click", async () => {
  $("analyze").disabled = true; $("status").textContent = "Extracting page text…";
  try {
    const page = await extractPage();
    $("status").textContent = "Analyzing submitted text…";
    const response = await fetch(endpoint()+"/api/analyze", {
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({url:page.url,title:page.title,text:page.text,comments:page.comments||[]})
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || "API request failed.");
    render(body.result);
    $("status").textContent = "Saved analysis #"+body.analysis_id+". Page text was sent to the configured local API/provider.";
  } catch (error) { $("status").textContent = "Error: "+error.message; }
  finally { $("analyze").disabled = false; }
});
$("history").addEventListener("click", async () => {
  $("status").textContent = "Loading saved history…";
  try {
    const response = await fetch(endpoint()+"/api/history?limit=50");
    if (!response.ok) throw new Error("History endpoint unavailable.");
    const body = await response.json();
    $("results").innerHTML = '<div class="card"><h2>Analysis history</h2>'+(body.items.length ? body.items.map(item =>
      '<div class="history-item"><strong>'+esc(item.title || item.domain)+'</strong><p class="muted">'+esc(item.domain)+' · '+esc(item.analyzed_at)+'</p><button class="secondary" data-id="'+item.id+'">Open analysis #'+item.id+'</button></div>'
    ).join('') : '<p class="muted">No saved analyses yet.</p>')+'</div>';
    $("results").querySelectorAll("[data-id]").forEach(button => button.addEventListener("click", async () => {
      try { const r=await fetch(endpoint()+"/api/history/"+button.dataset.id); const data=await r.json(); if(!r.ok) throw new Error(data.detail||"Could not load record"); render(data.result); }
      catch(e) { $("status").textContent=e.message; }
    }));
    $("status").textContent = body.items.length+" saved analyses.";
  } catch (error) { $("status").textContent = "Error: "+error.message; }
});
