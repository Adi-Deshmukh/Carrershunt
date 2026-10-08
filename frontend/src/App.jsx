import { useEffect, useMemo, useRef, useState } from "react";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

const nav = [
  ["overview", "Overview", "⌂"],
  ["jobs", "Jobs", "▣"],
  ["companies", "Companies", "◈"],
  ["candidate", "Candidate", "◎"],
  ["people", "People", "◉"],
  ["applications", "Applications", "✓"],
  ["settings", "Settings", "⚙"],
];

async function api(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options);
  const type = res.headers.get("content-type") || "";
  const data = type.includes("application/json") ? await res.json() : await res.text();
  if (!res.ok) throw new Error(data?.detail || data?.message || "Request failed");
  return data;
}

function Metric({ label, value, hint, tone = "" }) {
  return <div className="metric-card">
    <div className="metric-label">{label}</div>
    <div className={`metric-value ${tone}`}>{value}</div>
    {hint && <div className="metric-hint">{hint}</div>}
  </div>;
}

function Badge({ children, tone = "neutral" }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

function Empty({ title, text }) {
  return <div className="empty"><div className="empty-mark">+</div><strong>{title}</strong><span>{text}</span></div>;
}

function Overview({ stats, jobs, companies, candidate, go }) {
  const topJobs = jobs.slice(0, 5);
  return <div className="page">
    <div className="page-head">
      <div><div className="eyebrow">CONTROL CENTER</div><h1>Good roles. Better matches.</h1><p>Run the complete discovery → matching → resume → outreach workflow from one place.</p></div>
      <button className="primary" onClick={() => go("jobs")}>Process jobs <span>→</span></button>
    </div>

    <div className="metrics">
      <Metric label="OPEN ROLES" value={stats.jobs} hint="from imported companies" />
      <Metric label="COMPANIES" value={stats.companies} hint="tracked sources" />
      <Metric label="PROCESSABLE" value={stats.matched} hint="roles ready to analyze" />
      <Metric label="APPLICATIONS" value={stats.applications} hint="tracked outcomes" />
    </div>

    <div className="grid-2">
      <section className="panel">
        <div className="panel-head"><div><h2>Candidate readiness</h2><span>Your source of truth for every match.</span></div><button className="ghost" onClick={() => go("candidate")}>Open profile</button></div>
        {candidate ? <div className="candidate-card">
          <div className="avatar">{candidate.name?.slice(0,1)?.toUpperCase() || "C"}</div>
          <div className="candidate-main"><strong>{candidate.name}</strong><span>{candidate.email || "Email not set"} · {candidate.location || "Location not set"}</span>
            <div className="chips"><Badge tone={candidate.resume_text ? "success" : "warning"}>{candidate.resume_text ? "Resume indexed" : "Resume missing"}</Badge><Badge>{candidate.experience_years ?? 0} yrs experience</Badge><Badge>{candidate.has_evidence ? "Evidence indexed" : "No evidence"}</Badge></div>
          </div>
        </div> : <Empty title="Set up your candidate profile" text="Upload your master resume and connect GitHub to make matching useful." />}
      </section>

      <section className="panel">
        <div className="panel-head"><div><h2>Workflow</h2><span>Everything needed to go from source to application.</span></div></div>
        <div className="workflow">
          {["Import companies", "Ingest jobs", "Match candidates", "Tailor resume", "Find people", "Track outcome"].map((x,i) =>
            <div className="workflow-row" key={x}><span className="step">{String(i+1).padStart(2,"0")}</span><span>{x}</span><span className="arrow">→</span></div>
          )}
        </div>
      </section>
    </div>

    <section className="panel">
      <div className="panel-head"><div><h2>Latest jobs</h2><span>Newest roles available to process.</span></div><button className="ghost" onClick={() => go("jobs")}>View all</button></div>
      {topJobs.length ? <div className="table-wrap"><table><thead><tr><th>ROLE</th><th>LOCATION</th><th>SOURCE</th><th></th></tr></thead><tbody>
        {topJobs.map(j => <tr key={j.id}><td><strong>{j.title}</strong></td><td>{j.location || "—"}</td><td><Badge>{j.source || "job source"}</Badge></td><td><button className="table-action" onClick={() => go("jobs")}>Open</button></td></tr>)}
      </tbody></table></div> : <Empty title="No jobs yet" text="Import your company Excel and ingest job sources." />}
    </section>
  </div>;
}

function Jobs({ jobs, companies, candidate, refresh }) {
  const [running, setRunning] = useState({});
  const [selected, setSelected] = useState(null);
  const [result, setResult] = useState(null);
  const [message, setMessage] = useState("");

  const openResult = async (job) => {
    setSelected(job); setMessage("");
    try {
      const r = await api(`/pipeline/jobs/${job.id}/latest`);
      setResult(r.result);
    } catch { setResult(null); }
  };

  const run = async (jobId, useLlm = false) => {
    setRunning(r => ({...r, [jobId]: true})); setMessage("");
    try {
      const r = await api(`/pipeline/${jobId}?use_llm=${useLlm}`, {method:"POST"});
      setResult(r); setSelected(jobs.find(j => j.id === jobId)); setMessage(`Pipeline completed: ${r.status}.`);
      await refresh();
    } catch(e) { setMessage(e.message); } finally { setRunning(r => ({...r, [jobId]: false})); }
  };

  return <div className="page">
    <div className="page-head"><div><div className="eyebrow">JOB INTELLIGENCE</div><h1>Jobs</h1><p>Review eligibility, evidence, gaps, score breakdown, and the tailored resume before applying.</p></div></div>
    {message && <div className="notice">{message}</div>}
    {!candidate && <div className="warning-box">Create your candidate profile before running the pipeline.</div>}
    <section className="panel">
      <div className="panel-head"><div><h2>{jobs.length} roles in pipeline</h2><span>Click a role to inspect its latest analysis.</span></div></div>
      {jobs.length ? <div className="job-grid">{jobs.map(j => {
        const company = companies.find(c => c.id === j.company_id);
        return <article className="job-card" key={j.id} onClick={() => openResult(j)}>
          <div className="job-top"><Badge>{j.source || "source"}</Badge><span className="job-id">#{j.id}</span></div>
          <h3>{j.title}</h3><p>{company?.name || "Unknown company"} · {j.location || "Location not specified"}</p>
          <div className="job-meta"><span>{j.employment_type || "Role"}</span><a href={j.job_url} target="_blank" rel="noreferrer" onClick={e=>e.stopPropagation()}>View posting ↗</a></div>
          <button className="primary full" disabled={!candidate || running[j.id]} onClick={e => {e.stopPropagation();run(j.id, false)}}>{running[j.id] ? "Processing…" : "Analyze + tailor resume →"}</button>
        </article>
      })}</div> : <Empty title="No jobs imported" text="Go to Companies, upload your Excel, then ingest the sources." />}
    </section>

    {selected && <section className="panel result-panel">
      <div className="panel-head"><div><div className="eyebrow">MATCH RESULT</div><h2>{selected.title}</h2><span>{companies.find(c=>c.id===selected.company_id)?.name || "Company"} · {selected.location || "Location unspecified"}</span></div>
        {result?.resume_download_url && <a className="primary download-link" href={`${API_BASE}${result.resume_download_url}`}>Download tailored DOCX ↓</a>}
      </div>
      {result ? <div className="result-grid">
        <div className="score-card"><span>FIT SCORE</span><strong>{Math.round(result.match?.fit_score ?? 0)}</strong><small>{result.match?.eligible ? "Eligible" : "Hard eligibility failure"}</small></div>
        <div className="score-card"><span>INTERVIEW ESTIMATE</span><strong className="small-score">{result.match?.interview_estimate || "—"}</strong><small>Confidence: {result.match?.confidence || "—"}</small></div>
        <div className="score-card"><span>RESUME</span><strong className="small-score">{result.resume_generated ? "Ready" : "Blocked"}</strong><small>{result.validation_errors?.length ? result.validation_errors.length + " validation issues" : "Validated"}</small></div>
      </div> : <Empty title="No analysis yet" text="Run the pipeline to generate the match and tailored resume."/>}
      {result && <div className="result-details">
        <div><h3>Why this matches</h3><p>{result.match?.explanation || "No explanation available."}</p></div>
        <div><h3>Gaps</h3>{(result.match?.gaps||[]).length ? <ul>{result.match.gaps.map((g,i)=><li key={i}>{g}</li>)}</ul> : <p className="muted">No material gaps identified.</p>}</div>
        <div><h3>Score breakdown</h3><div className="breakdown">{Object.entries(result.match?.score_breakdown||{}).map(([k,v])=><div key={k}><span>{k.replaceAll("_"," ")}</span><b>{Number(v).toFixed(1)}</b></div>)}</div></div>
        {result.resume && <div><h3>Tailored resume plan</h3><p><strong>Summary:</strong> {result.resume.summary}</p><div className="chips">{result.resume.skills?.map(s=><Badge key={s}>{s}</Badge>)}</div></div>}
        {result.resume_id && <div className="resume-preview-box"><div><h3>Resume preview</h3><span>Browser preview of generated content; the downloaded DOCX retains the master template's formatting.</span></div><iframe title="Resume preview" src={`${API_BASE}/resumes/${result.resume_id}/preview`}/></div>}
      </div>}
    </section>}
  </div>;
}

function Companies({ companies, refresh, go }) {
  const input = useRef();
  const [busy, setBusy] = useState(false); const [message,setMessage]=useState("");
  const upload = async () => {
    const file=input.current?.files?.[0]; if(!file) return;
    setBusy(true); setMessage("");
    try {
      const body=new FormData(); body.append("file",file);
      const r=await api("/companies/import",{method:"POST",body});
      const p = r.pipeline || {};
      const pipelineText = p.requires_candidate
        ? "Create/upload your candidate resume to run matching."
        : `${p.processed} jobs processed, ${p.failed} pipeline failures.`;
      setMessage(`Imported ${r.imported} companies, ingested ${r.jobs_ingested || 0} jobs. ${pipelineText}`);
      await refresh();
      go("jobs");
    } catch(e){setMessage(e.message)} finally{setBusy(false)}
  };
  const ingest = async (id) => {
    setBusy(true); setMessage("");
    try { const r=await api(`/jobs/ingest/company/${id}`,{method:"POST"}); setMessage(`Ingested ${r.jobs_ingested} jobs.`); await refresh(); }
    catch(e){setMessage(e.message)} finally{setBusy(false)}
  };
  return <div className="page">
    <div className="page-head"><div><div className="eyebrow">SOURCE MANAGEMENT</div><h1>Companies</h1><p>Your Excel is the input layer. Carrershunt turns those sources into normalized jobs.</p></div>
      <label className="primary upload-btn">Upload Excel<input ref={input} type="file" accept=".xlsx,.xls" onChange={upload} hidden />{busy && <span>…</span>}</label>
    </div>
    <div className="import-strip"><div className="file-icon">XLS</div><div><strong>Expected columns</strong><span>Company · Careers URL · ATS (optional) · Active (optional)</span></div><div className="import-arrow">Excel → Companies → Jobs</div></div>
    {message && <div className="notice">{message}</div>}
    <section className="panel">
      <div className="panel-head"><div><h2>Tracked sources</h2><span>{companies.length} companies configured</span></div></div>
      {companies.length ? <div className="table-wrap"><table><thead><tr><th>COMPANY</th><th>CAREERS URL</th><th>PLATFORM</th><th>STATUS</th><th></th></tr></thead><tbody>
        {companies.map(c=><tr key={c.id}><td><strong>{c.name}</strong></td><td><a className="link" href={c.careers_url} target="_blank" rel="noreferrer">{c.careers_url}</a></td><td><Badge>{c.platform || "auto"}</Badge></td><td><Badge tone={c.active ? "success":"neutral"}>{c.active ? "Active":"Inactive"}</Badge></td><td><button className="table-action" disabled={busy} onClick={()=>ingest(c.id)}>Ingest jobs</button></td></tr>)}
      </tbody></table></div> : <Empty title="Upload your company Excel" text="No companies are configured yet." />}
    </section>
  </div>;
}

function Candidate({ candidate, refresh }) {
  const [form,setForm]=useState({name:candidate?.name||"",email:candidate?.email||"",education:candidate?.education||"",graduation_year:candidate?.graduation_year||"",experience_years:candidate?.experience_years||0,location:candidate?.location||"",work_authorization:candidate?.work_authorization||""});
  const [resume,setResume]=useState(null); const [github,setGithub]=useState(""); const [busy,setBusy]=useState(false); const [message,setMessage]=useState("");
  useEffect(()=>{if(candidate)setForm({name:candidate.name||"",email:candidate.email||"",education:candidate.education||"",graduation_year:candidate.graduation_year||"",experience_years:candidate.experience_years||0,location:candidate.location||"",work_authorization:candidate.work_authorization||""})},[candidate]);
  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const existing = candidate?.id;
      if (existing) {
        await api(`/candidates/${existing}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ...form,
            graduation_year: form.graduation_year ? Number(form.graduation_year) : null,
            experience_years: Number(form.experience_years) || 0,
          }),
        });
        setMessage("Profile updated.");
        await refresh();
        return;
      }
      const r = await api("/candidates", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          graduation_year: form.graduation_year ? Number(form.graduation_year) : null,
          experience_years: Number(form.experience_years) || 0,
          resume_text: "Master resume pending",
          evidence: {},
        }),
      });
      setMessage(`Candidate created (#${r.id}). Upload the master resume below.`);
      await refresh();
    } catch (e) {
      setMessage(e.message);
    } finally {
      setBusy(false);
    }
  };
  const uploadResume=async()=>{
    if(!candidate?.id||!resume)return;
    setBusy(true);setMessage("");
    try{const b=new FormData();b.append("file",resume);const r=await api(`/candidates/${candidate.id}/resume`,{method:"POST",body:b});setMessage(`Master resume indexed: ${r.characters_extracted.toLocaleString()} characters.`);await refresh();}
    catch(e){setMessage(e.message)}finally{setBusy(false)}
  };
  const syncGithub=async()=>{
    if(!candidate?.id||!github)return;
    setBusy(true);setMessage("");
    try{const r=await api(`/candidates/${candidate.id}/github/sync`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username_or_url:github,max_repos:25})});setMessage(`GitHub synced: ${r.indexed ?? r.repositories_indexed ?? "completed"} evidence records.`);await refresh();}
    catch(e){setMessage(e.message)}finally{setBusy(false)}
  };
  return <div className="page">
    <div className="page-head"><div><div className="eyebrow">CANDIDATE INTELLIGENCE</div><h1>Candidate</h1><p>One master profile feeds every job match. Tailored resumes are generated from evidence, not invented claims.</p></div></div>
    {message&&<div className="notice">{message}</div>}
    <div className="grid-2">
      <section className="panel"><div className="panel-head"><div><h2>Master profile</h2><span>Keep this information current.</span></div></div>
        <form className="form-grid" onSubmit={save}>
          {["name","email","location","education","graduation_year","experience_years","work_authorization"].map(k=><label key={k}>{k.replaceAll("_"," ")}<input value={form[k]??""} onChange={e=>setForm({...form,[k]:e.target.value})} placeholder={k==="experience_years"?"0":""}/></label>)}
          <button className="primary" disabled={busy}>{candidate ? "Save profile" : "Create profile"}</button>
        </form>
      </section>
      <section className="panel"><div className="panel-head"><div><h2>Master resume</h2><span>PDF, DOCX or TXT. This is your source of truth.</span></div></div>
        <div className="dropzone"><div className="upload-glyph">↑</div><strong>{resume?.name || "Choose master resume"}</strong><span>Never overwrite the source with a tailored copy.</span><input type="file" accept=".pdf,.docx,.txt" onChange={e=>setResume(e.target.files?.[0]||null)}/><button className="primary" disabled={!candidate?.id||!resume||busy} onClick={uploadResume}>Index master resume</button></div>
        <div className="divider"/>
        <label className="inline-field">GitHub username / URL<input value={github} onChange={e=>setGithub(e.target.value)} placeholder="Adi-Deshmukh"/><button className="ghost" type="button" disabled={!candidate?.id||!github||busy} onClick={syncGithub}>Sync GitHub</button></label>
      </section>
    </div>
  </div>;
}

function Applications({ applications, jobs, refresh }) {
  const update=async(id,status)=>{try{await api(`/applications/${id}?status=${encodeURIComponent(status)}`,{method:"PATCH"});await refresh()}catch(e){alert(e.message)}};
  return <div className="page"><div className="page-head"><div><div className="eyebrow">OUTCOME LOOP</div><h1>Applications</h1><p>Track where each job stands so future matching can eventually learn from outcomes.</p></div></div>
    <section className="panel">{applications.length?<div className="table-wrap"><table><thead><tr><th>ROLE</th><th>STATUS</th><th>APPLIED</th><th>UPDATED</th><th></th></tr></thead><tbody>{applications.map(a=>{const j=jobs.find(x=>x.id===a.job_id);return <tr key={a.id}><td><strong>{j?.title||`Job #${a.job_id}`}</strong></td><td><Badge tone={a.status==="applied"?"success":"neutral"}>{a.status}</Badge></td><td>{a.applied_at?new Date(a.applied_at).toLocaleDateString():"—"}</td><td>{a.updated_at?new Date(a.updated_at).toLocaleDateString():"—"}</td><td><select value={a.status} onChange={e=>update(a.id,e.target.value)}><option>interested</option><option>applied</option><option>interview</option><option>rejected</option><option>offer</option></select></td></tr>})}</tbody></table></div>:<Empty title="No applications tracked" text="Mark jobs as applications from the job workflow once you start applying."/>}</section>
  </div>;
}

function People({ jobs }) {
  const [jobId,setJobId]=useState(jobs[0]?.id||""); const [role,setRole]=useState(""); const [skills,setSkills]=useState(""); const [results,setResults]=useState([]); const [busy,setBusy]=useState(false);
  const search=async()=>{const j=jobs.find(x=>x.id===Number(jobId));if(!j)return;setBusy(true);try{const r=await api(`/people/search?company=${encodeURIComponent(j.company_name||"")}&role=${encodeURIComponent(role||j.title)}&skills=${encodeURIComponent(skills)}`);setResults(r.results||[])}catch(e){alert(e.message)}finally{setBusy(false)}};
  return <div className="page"><div className="page-head"><div><div className="eyebrow">NETWORK INTELLIGENCE</div><h1>People & outreach</h1><p>Find relevant public professional contacts. Draft messages for human review; nothing is auto-sent.</p></div></div>
    <section className="panel"><div className="form-grid compact"><label>Job<select value={jobId} onChange={e=>setJobId(e.target.value)}>{jobs.map(j=><option key={j.id} value={j.id}>{j.title}</option>)}</select></label><label>Target role<input value={role} onChange={e=>setRole(e.target.value)} placeholder="Hiring manager / engineer"/></label><label>Relevant skills<input value={skills} onChange={e=>setSkills(e.target.value)} placeholder="Python, ML, FastAPI"/></label><button className="primary" onClick={search} disabled={busy}>{busy?"Searching…":"Find people →"}</button></div></section>
    <div className="people-grid">{results.map((p,i)=><article className="person-card" key={p.profile_url||i}><div className="avatar">{p.name?.slice(0,1)||"P"}</div><strong>{p.name}</strong><span>{p.role}</span><Badge tone="success">{Math.round((p.relevance_score||0)*100)}% relevance</Badge>{p.rationale&&<p>{p.rationale}</p>}<a href={p.profile_url} target="_blank" rel="noreferrer">Public profile ↗</a></article>)}</div>
  </div>;
}

function Settings() {
  const emptyForm = {
    ai_provider: "auto",
    openai_api_key: "", openai_model: "gpt-4o",
    gemini_api_key: "", gemini_model: "gemini-2.0-flash",
    xai_api_key: "",    xai_model: "grok-3-mini",
    github_token: "",   serper_api_key: "",
  };
  const [form, setForm] = useState(emptyForm);
  const [info, setInfo] = useState(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    api("/settings").then(r => {
      setInfo(r);
      setForm(f => ({
        ...f,
        ai_provider:  r.ai_provider  || f.ai_provider,
        openai_model: r.openai_model || f.openai_model,
        gemini_model: r.gemini_model || f.gemini_model,
        xai_model:    r.xai_model    || f.xai_model,
      }));
    }).catch(() => {});
  }, []);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const save = async () => {
    try {
      const r = await api("/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      setStatus(r.message || "Settings updated.");
      setInfo(r);
      setForm(f => ({ ...f, openai_api_key: "", gemini_api_key: "", xai_api_key: "", github_token: "", serper_api_key: "" }));
    } catch (e) { setStatus(e.message); }
  };

  return (
    <div className="page">
      <div className="page-head"><div><div className="eyebrow">SYSTEM CONFIGURATION</div><h1>Settings</h1><p>Configure integrations from the dashboard. Secrets are sent only to your Carrershunt backend.</p></div></div>
      {status && <div className="notice">{status}</div>}
      {info && <div className="chips" style={{marginBottom:"1rem"}}>
        <span style={{marginRight:"0.5rem"}}>Provider: <strong>{info.ai_provider}</strong></span>
        {(info.configured_providers||[]).map(p => <Badge key={p} tone="success">{p} ✓</Badge>)}
        {info.github_configured && <Badge tone="success">GitHub ✓</Badge>}
        {info.serper_configured && <Badge tone="success">Serper ✓</Badge>}
      </div>}
      <section className="panel settings-panel">
        <div className="panel-head"><div><h2>AI routing</h2><span>Keys are runtime configuration; do not commit them to Git.</span></div></div>
        <div className="form-grid">
          <label>Provider routing
            <select value={form.ai_provider} onChange={set("ai_provider")}>
              <option value="auto">auto (primary → fallback)</option>
              <option value="openai">OpenAI only</option>
              <option value="gemini">Gemini only</option>
              <option value="grok">Grok / xAI only</option>
            </select>
          </label>
        </div>
        <div className="panel-head" style={{marginTop:"1.25rem"}}><div><h2>OpenAI</h2></div></div>
        <div className="form-grid">
          <label>API key<input type="password" value={form.openai_api_key} onChange={set("openai_api_key")} placeholder="sk-…"/></label>
          <label>Model<input value={form.openai_model} onChange={set("openai_model")}/></label>
        </div>
        <div className="panel-head" style={{marginTop:"1.25rem"}}><div><h2>Google Gemini</h2></div></div>
        <div className="form-grid">
          <label>API key<input type="password" value={form.gemini_api_key} onChange={set("gemini_api_key")} placeholder="AIza…"/></label>
          <label>Model<input value={form.gemini_model} onChange={set("gemini_model")}/></label>
        </div>
        <div className="panel-head" style={{marginTop:"1.25rem"}}><div><h2>xAI / Grok</h2></div></div>
        <div className="form-grid">
          <label>API key<input type="password" value={form.xai_api_key} onChange={set("xai_api_key")} placeholder="xai-…"/></label>
          <label>Model<input value={form.xai_model} onChange={set("xai_model")}/></label>
        </div>
        <div className="panel-head" style={{marginTop:"1.25rem"}}><div><h2>Integrations</h2></div></div>
        <div className="form-grid">
          <label>GitHub token<input type="password" value={form.github_token} onChange={set("github_token")} placeholder="ghp_…"/></label>
          <label>Serper API key<input type="password" value={form.serper_api_key} onChange={set("serper_api_key")} placeholder="For people search"/></label>
        </div>
        <div className="settings-note">Security: the backend holds these values in process memory only — they are lost on restart. For production, replace with encrypted secret storage and authentication.</div>
        <button className="primary" onClick={save}>Save integration settings</button>
      </section>
    </div>
  );
}


export default function App() {
  const [page,setPage]=useState("overview"); const [data,setData]=useState({jobs:[],companies:[],applications:[],candidate:null}); const [loading,setLoading]=useState(true);
  const refresh=async()=>{setLoading(true);try{const [jobs,companies,applications,candidate]=await Promise.all([api("/jobs"),api("/companies"),api("/applications"),api("/candidates/latest")]);setData({jobs,companies,applications,candidate})}catch(e){console.error(e)}finally{setLoading(false)}};
  useEffect(()=>{refresh()},[]);
  const stats=useMemo(()=>({jobs:data.jobs.length,companies:data.companies.length,applications:data.applications.length,matched:data.jobs.length}),[data]);
  if(loading&&!data.jobs.length&&!data.companies.length) return <div className="splash"><div className="logo">CS</div><strong>Carrershunt</strong><span>Loading control center…</span></div>;
  return <div className="app-shell">
    <aside className="sidebar"><div className="brand"><div className="brand-mark">CS</div><div><strong>Carrershunt</strong><span>Candidate Intelligence</span></div></div>
      <nav>{nav.map(([id,label,icon])=><button key={id} className={page===id?"active":""} onClick={()=>setPage(id)}><span className="nav-icon">{icon}</span>{label}</button>)}</nav>
      <div className="sidebar-bottom"><div className="api-status"><span className="pulse"/>API connected</div><div className="version">v0.2.0 · local control plane</div></div>
    </aside>
    <main><header className="topbar"><div className="crumb">CARRERSHUNT <span>/</span> {nav.find(x=>x[0]===page)?.[1].toUpperCase()}</div><button className="refresh" onClick={refresh}>↻ Refresh</button></header>
      {page==="overview"&&<Overview stats={stats} jobs={data.jobs} companies={data.companies} candidate={data.candidate} go={setPage}/>}
      {page==="jobs"&&<Jobs jobs={data.jobs} companies={data.companies} candidate={data.candidate} refresh={refresh}/>}
      {page==="companies"&&<Companies companies={data.companies} refresh={refresh} go={setPage}/>}
      {page==="candidate"&&<Candidate candidate={data.candidate} refresh={refresh}/>}
      {page==="people"&&<People jobs={data.jobs}/>}
      {page==="applications"&&<Applications applications={data.applications} jobs={data.jobs} refresh={refresh}/>}
      {page==="settings"&&<Settings/>}
    </main>
  </div>;
}
