import { useEffect, useMemo, useRef, useState } from "react";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");
const SUPABASE_URL = (import.meta.env.VITE_SUPABASE_URL || "").replace(/\/$/, "");
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || "";
const SUPABASE_CONFIGURED = Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);
const SESSION_KEY = "carrershunt.supabase.session";

function readStoredSession() {
  try { return JSON.parse(sessionStorage.getItem(SESSION_KEY) || "null"); }
  catch { return null; }
}

function saveSession(session) {
  const normalized = {
    ...session,
    expires_at: session.expires_at || Math.floor(Date.now() / 1000) + (session.expires_in || 3600),
  };
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(normalized));
  return normalized;
}

function clearSession() {
  sessionStorage.removeItem(SESSION_KEY);
}

async function getValidSession() {
  const session = readStoredSession();
  if (!session?.access_token) return null;
  if ((session.expires_at || 0) > Math.floor(Date.now() / 1000) + 60) return session;
  if (!session.refresh_token || !SUPABASE_CONFIGURED) {
    clearSession();
    return null;
  }
  try {
    const response = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=refresh_token`, {
      method: "POST",
      headers: { apikey: SUPABASE_ANON_KEY, "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: session.refresh_token }),
    });
    if (!response.ok) throw new Error("Session refresh failed");
    return saveSession(await response.json());
  } catch {
    clearSession();
    return null;
  }
}

async function supabaseAuth(endpoint, payload) {
  const response = await fetch(`${SUPABASE_URL}/auth/v1/${endpoint}`, {
    method: "POST",
    headers: { apikey: SUPABASE_ANON_KEY, "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.msg || data.message || data.error_description || "Supabase authentication failed.");
  return data;
}

async function ensureSupabaseProfile(session, name = "") {
  if (!SUPABASE_CONFIGURED || !session?.access_token || !session.user?.id) return;
  const response = await fetch(`${SUPABASE_URL}/rest/v1/profiles?id=eq.${encodeURIComponent(session.user.id)}&select=id`, {
    headers: { apikey: SUPABASE_ANON_KEY, Authorization: `Bearer ${session.access_token}` },
  });
  if (!response.ok) throw new Error("Could not load your Supabase profile.");
  const rows = await response.json();
  if (!rows.length) {
    await syncSupabaseProfile(session, { name, email: session.user.email });
  }
}

async function syncSupabaseProfile(session, values = {}) {
  if (!SUPABASE_CONFIGURED || !session?.access_token || !session.user?.id) return;
  const row = {
    id: session.user.id,
    full_name: values.name ?? values.full_name ?? session.user.user_metadata?.full_name ?? "",
    email: values.email ?? session.user.email ?? "",
    education: values.education ?? null,
    graduation_year: values.graduation_year ? Number(values.graduation_year) : null,
    experience_years: Number(values.experience_years) || 0,
    location: values.location ?? null,
    work_authorization: values.work_authorization ?? null,
    resume_text: values.resume_text ?? "",
    evidence: values.evidence ?? {},
  };
  const response = await fetch(`${SUPABASE_URL}/rest/v1/profiles?on_conflict=id`, {
    method: "POST",
    headers: {
      apikey: SUPABASE_ANON_KEY,
      Authorization: `Bearer ${session.access_token}`,
      "Content-Type": "application/json",
      Prefer: "resolution=merge-duplicates,return=minimal",
    },
    body: JSON.stringify(row),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Supabase profile save failed: ${detail.slice(0, 240)}`);
  }
}

function AuthScreen({ onAuthenticated }) {
  const [mode, setMode] = useState("signin");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true); setMessage(""); setError("");
    try {
      if (mode === "signup") {
        const result = await supabaseAuth("signup", {
          email: email.trim(),
          password,
          data: { full_name: name.trim() },
        });
        if (!result.access_token || !result.user) {
          setMessage("Account created. Check your email to confirm the address, then sign in.");
          setMode("signin");
          return;
        }
        const session = saveSession(result);
        await ensureSupabaseProfile(session, name.trim());
        onAuthenticated(session);
        return;
      }
      const result = await supabaseAuth("token?grant_type=password", { email: email.trim(), password });
      const session = saveSession(result);
      await ensureSupabaseProfile(session, session.user?.user_metadata?.full_name || email.split("@")[0]);
      onAuthenticated(session);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return <div className="auth-shell">
    <div className="auth-card">
      <div className="brand-mark auth-mark">CS</div>
      <div className="eyebrow">CANDIDATE INTELLIGENCE</div>
      <h1>{mode === "signup" ? "Create your account" : "Sign in to Carrershunt"}</h1>
      <p>Keep your candidate profile and resume private to your account.</p>
      <form onSubmit={submit} className="auth-form">
        {mode === "signup" && <label>Full name<input autoComplete="name" value={name} onChange={e=>setName(e.target.value)} required maxLength={200} placeholder="Your name"/></label>}
        <label>Email<input type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} required placeholder="you@example.com"/></label>
        <label>Password<input type="password" autoComplete={mode === "signup" ? "new-password" : "current-password"} value={password} onChange={e=>setPassword(e.target.value)} required minLength={6} placeholder="At least 6 characters"/></label>
        {error && <div className="notice notice-error" role="alert">{error}</div>}
        {message && <div className="notice" role="status">{message}</div>}
        <button className="primary full" disabled={busy}>{busy ? <><span className="spinner" aria-hidden="true"/> {mode === "signup" ? "Creating account…" : "Signing in…"}</> : mode === "signup" ? "Create account" : "Sign in"}</button>
      </form>
      <button className="auth-switch" disabled={busy} onClick={()=>{setMode(mode==="signup"?"signin":"signup");setError("");setMessage("");}}>
        {mode === "signup" ? "Already have an account? Sign in" : "New to Carrershunt? Create an account"}
      </button>
    </div>
  </div>;
}

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
  const headers = new Headers(options.headers || {});
  const session = await getValidSession();
  if (session?.access_token) headers.set("Authorization", `Bearer ${session.access_token}`);
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const type = res.headers.get("content-type") || "";
  const data = type.includes("application/json") ? await res.json() : await res.text();
  if (!res.ok) {
    const detail = data?.detail;
    const message = typeof detail === "string"
      ? detail
      : [detail?.message, ...(detail?.validation_errors || [])].filter(Boolean).join(" ")
        || data?.message
        || "Request failed";
    throw new Error(message);
  }
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
  const [creatingResume, setCreatingResume] = useState(false);
  const isAnalyzing = Object.values(running).some(Boolean);
  const isBusy = isAnalyzing || creatingResume;
  const canAnalyze = Boolean(candidate?.resume_text && candidate.resume_text !== "Master resume pending" && candidate.resume_text.trim().length >= 100);

  const createResume = async () => {
    if (!selected || !result?.resume) return;
    setCreatingResume(true); setMessage("");
    try {
      const r = await api(`/resumes/tailor/${selected.id}`, { method: "POST" });
      setResult(current => ({ ...current, resume_generated: true, resume_id: r.resume_id, resume_download_url: r.download_url }));
      setMessage("Tailored DOCX created and passed quality checks.");
    } catch (e) { setMessage(e.message); }
    finally { setCreatingResume(false); }
  };

  const openResult = async (job) => {
    setSelected(job); setResult(null); setMessage("");
    try {
      const r = await api(`/pipeline/jobs/${job.id}/latest`);
      setResult(r.result);
      if (r.status === "failed") setMessage(r.error || "The last analysis failed. Run analysis again.");
    } catch { setResult(null); }
  };

  useEffect(() => {
    if (!selected && jobs.length) {
      openResult(jobs[0]);
    }
  }, [jobs]);
  
  const run = async (job, useLlm = false) => {
    if (isAnalyzing || !candidate) return;
    setSelected(job);
    setResult(null);
    setRunning({[job.id]: true});
    setMessage("Analyzing the actual job description against your candidate profile…");
    try {
      const r = await api(`/pipeline/${job.id}?use_llm=${useLlm}`, {method:"POST"});
      if (!r?.match || !r?.resume) throw new Error("Analysis returned an incomplete result. Check the backend logs and retry.");
      setResult(r);
      setMessage(`Analysis complete for ${job.title}.`);
      await refresh();
    } catch(e) {
      setMessage(`Analysis failed: ${e.message}. Check that the job description and candidate resume are available, then retry.`);
    } finally {
      setRunning({});
    }
  };

  return <div className="page">
    <div className="page-head"><div><div className="eyebrow">JOB INTELLIGENCE</div><h1>Jobs</h1><p>Review eligibility, evidence, gaps, score breakdown, and the tailored resume before applying.</p></div></div>
    {message && <div className={message.startsWith("Analysis failed:") ? "notice notice-error" : "notice"} role="status" aria-live="polite">{message}</div>}
    {isAnalyzing && <div className="processing-panel"><span className="spinner" aria-hidden="true" /><div><strong>Analyzing role against your profile</strong><span>Reading requirements, comparing evidence, and preparing the resume plan. Keep this page open.</span></div></div>}
    {!canAnalyze && <div className="warning-box">Create your candidate profile and upload a real master resume before running analysis. The placeholder profile text is not sufficient for matching.</div>}
    <section className="panel">
      <div className="panel-head"><div><h2>{jobs.length} roles in pipeline</h2><span>Click a role to inspect its latest analysis.</span></div></div>
      {jobs.length ? <div className="job-grid">{jobs.map(j => {
        const company = companies.find(c => c.id === j.company_id);
        return <article className={selected?.id === j.id ? "job-card selected" : "job-card"} key={j.id} onClick={() => {if(!isBusy) openResult(j)}}>
          <div className="job-top"><Badge>{j.source || "source"}</Badge><span className="job-id">#{j.id}</span></div>
          <h3>{j.title}</h3><p>{company?.name || "Unknown company"} · {j.location || "Location not specified"}</p>
          <div className="job-meta"><span>{j.employment_type || "Role"}</span>{j.job_url ? <a href={j.job_url} target="_blank" rel="noreferrer" onClick={e=>e.stopPropagation()}>View role ↗</a> : <span>Posting URL unavailable</span>}{j.apply_url && j.apply_url !== j.job_url && <a href={j.apply_url} target="_blank" rel="noreferrer" onClick={e=>e.stopPropagation()}>Apply ↗</a>}</div>
          <button className="primary full analyze-button" disabled={!canAnalyze || isBusy || !j.description || j.description.trim().length < 100 || !j.job_url} title={!canAnalyze ? "Upload a real master resume first" : (!j.description || j.description.trim().length < 100) ? "This posting has no usable description; re-ingest the company" : ""} onClick={e => {e.stopPropagation();run(j, false)}}>{running[j.id] ? <><span className="spinner" aria-hidden="true" /> Analyzing role…</> : isBusy ? "Processing…" : (!j.description || j.description.trim().length < 100) ? "Job details unavailable" : !canAnalyze ? "Upload master resume first" : "Analyze role"}</button>
        </article>
      })}</div> : <Empty title="No jobs imported" text="Go to Companies, upload your Excel, then ingest the sources." />}
    </section>

    {selected && <section className="panel result-panel">
      <div className="panel-head"><div><div className="eyebrow">MATCH RESULT</div><h2>{selected.title}</h2><span>{companies.find(c=>c.id===selected.company_id)?.name || "Company"} · {selected.location || "Location unspecified"}</span></div>
        {result?.resume_download_url ? <a className="primary download-link" href={`${API_BASE}${result.resume_download_url}`}>Download tailored DOCX ↓</a> : result?.resume && <button className="primary" disabled={creatingResume} onClick={createResume}>{creatingResume ? "Creating DOCX…" : "Create tailored resume"}</button>}
      </div>
      <details className="job-description"><summary>Review full job description</summary><div className="job-description-content">{selected.description || "No job description was captured for this posting."}</div></details>
      {result ? <div className="result-grid">
        <div className="score-card"><span>FIT SCORE</span><strong>{Math.round(result.match?.fit_score ?? 0)}</strong><small>{result.match?.eligible ? "Eligible" : "Hard eligibility failure"}</small></div>
        <div className="score-card"><span>INTERVIEW ESTIMATE</span><strong className="small-score">{result.match?.interview_estimate || "—"}</strong><small>Confidence: {result.match?.confidence || "—"}</small></div>
        <div className="score-card"><span>RESUME</span><strong className="small-score">{result.resume_generated ? "Ready" : result.resume ? "Not created" : "Unavailable"}</strong><small>{result.resume_generated ? "DOCX generated" : result.resume ? "Create after reviewing the JD" : "Run job analysis first"}</small></div>
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
  const [runId, setRunId] = useState(null); const [runStatus, setRunStatus] = useState(null);
  useEffect(() => {
    let active = true;
    api("/companies/import-runs/latest").then(status => {
      if (!active) return;
      setRunStatus(status);
      if (!["completed", "completed_with_errors"].includes(status.status)) setRunId(status.run_id);
    }).catch(() => {});
    return () => { active = false; };
  }, []);
  useEffect(() => {
    if (!runId) return;
    let active = true; let timer;
    const poll = async () => {
      try {
        const status = await api(`/companies/import-runs/${runId}`);
        if (!active) return;
        setRunStatus(status);
        if (["completed", "completed_with_errors"].includes(status.status)) {
          setMessage(`Ingestion ${status.status}: ${status.jobs_ingested} jobs discovered. Open Jobs to review results.`);
          await refresh();
          return;
        }
      } catch (e) {
        if (active) setMessage(`Could not refresh ingestion status: ${e.message}`);
      }
      if (active) timer = setTimeout(poll, 1500);
    };
    poll();
    return () => { active = false; if (timer) clearTimeout(timer); };
  }, [runId]);
  const upload = async () => {
    const file=input.current?.files?.[0]; if(!file) return;
    setBusy(true); setMessage("");
    try {
      const body=new FormData(); body.append("file",file);
      const r=await api("/companies/import",{method:"POST",body});
      setRunId(r.ingestion_run_id || null);
      setRunStatus(null);
      setMessage(`Imported ${r.imported} companies. Queued ${r.queued_companies || 0} companies for background scraping.`);
      await refresh();
    } catch(e){setMessage(e.message)} finally{setBusy(false)}
  };
  const ingest = async (id) => {
    setBusy(true); setMessage("");
    try { const r=await api(`/jobs/ingest/company/${id}`,{method:"POST"}); setRunId(r.ingestion_run_id || null); setRunStatus(null); setMessage(`Queued ${r.queued_companies || 1} company for background crawling.`); }
    catch(e){setMessage(e.message)} finally{setBusy(false)}
  };
  return <div className="page">
    <div className="page-head"><div><div className="eyebrow">SOURCE MANAGEMENT</div><h1>Companies</h1><p>Your Excel is the input layer. Carrershunt turns those sources into normalized jobs.</p></div>
      <label className="primary upload-btn">Upload Excel<input ref={input} type="file" accept=".xlsx,.xls" onChange={upload} hidden />{busy && <span>…</span>}</label>
    </div>
    <div className="import-strip"><div className="file-icon">XLS</div><div><strong>Expected columns</strong><span>Company · Careers URL · ATS (optional) · Active (optional)</span></div><div className="import-arrow">Excel → Companies → Jobs</div></div>
    {message && <div className="notice">{message}</div>}
    {runStatus && <section className="panel"><div className="panel-head"><div><h2>Ingestion run #{runStatus.run_id}</h2><span>Status: {runStatus.status} · {runStatus.jobs_ingested} jobs discovered</span></div><button className="ghost" onClick={()=>go("jobs")}>Open Jobs</button></div><div className="chips"><Badge>Queued {runStatus.task_counts?.queued ?? 0}</Badge><Badge>Running {runStatus.task_counts?.running ?? 0}</Badge><Badge tone="success">Completed {runStatus.task_counts?.completed ?? 0}</Badge><Badge tone="warning">Warnings {runStatus.task_counts?.completed_with_warnings ?? 0}</Badge><Badge tone="warning">Failed {runStatus.task_counts?.failed ?? 0}</Badge></div>{(runStatus.tasks||[]).filter(t=>t.error).map(t=><p key={t.id} className={t.status==="failed"?"notice-error":"muted"}>{t.company || `Job #${t.job_id}`} · {t.error}</p>)}</section>}
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
        await refresh();
        const latest = await api("/candidates/latest");
        const session = await getValidSession();
        if (session) await syncSupabaseProfile(session, latest || form);
        setMessage("Profile updated and synced to your account.");
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
      await refresh();
      const latest = await api("/candidates/latest");
      const session = await getValidSession();
      if (session) await syncSupabaseProfile(session, latest || form);
      setMessage(`Candidate created (#${r.id}). Upload the master resume below.`);
    } catch (e) {
      setMessage(e.message);
    } finally {
      setBusy(false);
    }
  };
  const uploadResume=async()=>{
    if(!candidate?.id||!resume)return;
    setBusy(true);setMessage("");
    try{const b=new FormData();b.append("file",resume);const r=await api(`/candidates/${candidate.id}/resume`,{method:"POST",body:b});await refresh();const latest=await api("/candidates/latest");const session=await getValidSession();if(session)await syncSupabaseProfile(session,latest||form);setMessage(`Master resume indexed: ${r.characters_extracted.toLocaleString()} characters and synced to your account.`);}
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
  const [jobId,setJobId]=useState(jobs[0]?.id||""); const [role,setRole]=useState(""); const [skills,setSkills]=useState(""); const [results,setResults]=useState([]); const [busy,setBusy]=useState(false); const [message,setMessage]=useState("");
  useEffect(()=>{if(!jobId && jobs.length)setJobId(jobs[0].id)},[jobs,jobId]);
  const search=async()=>{const j=jobs.find(x=>x.id===Number(jobId));if(!j)return;setBusy(true);setMessage("");try{const r=await api(`/people/search?company=${encodeURIComponent(j.company_name||"")}&role=${encodeURIComponent(role||j.title)}&skills=${encodeURIComponent(skills)}`);setResults(r.results||[]);setMessage((r.results||[]).length ? "" : "No public contacts found. Check your Serper configuration and search terms.")}catch(e){setMessage(e.message)}finally{setBusy(false)}};
  return <div className="page"><div className="page-head"><div><div className="eyebrow">NETWORK INTELLIGENCE</div><h1>People & outreach</h1><p>Find relevant public professional contacts. Draft messages for human review; nothing is auto-sent.</p></div></div>
    <section className="panel">{message&&<div className="notice">{message}</div>}<div className="form-grid compact"><label>Job<select value={jobId} onChange={e=>setJobId(e.target.value)}>{jobs.map(j=><option key={j.id} value={j.id}>{j.title}</option>)}</select></label><label>Target role<input value={role} onChange={e=>setRole(e.target.value)} placeholder="Hiring manager / engineer"/></label><label>Relevant skills<input value={skills} onChange={e=>setSkills(e.target.value)} placeholder="Python, ML, FastAPI"/></label><button className="primary" onClick={search} disabled={busy}>{busy?"Searching…":"Find people →"}</button></div></section>
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
      {SUPABASE_CONFIGURED && <div className="warning-box">Account mode is enabled. Integration keys are shared server configuration, so configure them in the backend environment rather than saving them here. Per-account encrypted key storage is not implemented yet.</div>}
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
        <button className="primary" disabled={SUPABASE_CONFIGURED} onClick={save}>Save integration settings</button>
      </section>
    </div>
  );
}


export default function App() {
  const [page,setPage]=useState("overview"); const [data,setData]=useState({jobs:[],companies:[],applications:[],candidate:null}); const [loading,setLoading]=useState(true);
  const [authSession,setAuthSession]=useState(()=>SUPABASE_CONFIGURED ? null : readStoredSession());
  const [apiHealth,setApiHealth]=useState("checking");
  useEffect(()=>{
    let active=true; let timer;
    const check=async()=>{
      try{
        const response=await fetch(`${API_BASE}/health`);
        const result=response.ok?await response.json():null;
        if(active)setApiHealth(result?.status==="ok"?"online":"offline");
      }catch{if(active)setApiHealth("offline")}
      if(active)timer=setTimeout(check,30000);
    };
    check();
    return ()=>{active=false;if(timer)clearTimeout(timer)};
  },[]);
  useEffect(()=>{
    if(!SUPABASE_CONFIGURED) return;
    let active=true;
    getValidSession().then(session=>{if(active)setAuthSession(session)}).catch(()=>{if(active)setAuthSession(null)});
    return ()=>{active=false};
  },[]);
  const refresh=async()=>{setLoading(true);try{const [jobs,companies,applications,candidate]=await Promise.all([api("/jobs"),api("/companies"),api("/applications"),api("/candidates/latest")]);setData({jobs,companies,applications,candidate})}catch(e){console.error(e)}finally{setLoading(false)}};
  useEffect(()=>{if(!SUPABASE_CONFIGURED || authSession)refresh()},[authSession?.user?.id]);
  const stats=useMemo(()=>({jobs:data.jobs.length,companies:data.companies.length,applications:data.applications.length,matched:data.jobs.filter(j=>j.job_url && j.description && j.description.length>=100).length}),[data]);
  if(SUPABASE_CONFIGURED && !authSession) return <AuthScreen onAuthenticated={setAuthSession}/>;
  if(loading&&!data.jobs.length&&!data.companies.length) return <div className="splash"><div className="logo">CS</div><strong>Carrershunt</strong><span>Loading control center…</span></div>;
  return <div className="app-shell">
    <aside className="sidebar"><div className="brand"><div className="brand-mark">CS</div><div><strong>Carrershunt</strong><span>Candidate Intelligence</span></div></div>
      <nav>{nav.map(([id,label,icon])=><button key={id} className={page===id?"active":""} onClick={()=>setPage(id)}><span className="nav-icon">{icon}</span>{label}</button>)}</nav>
      <div className="sidebar-bottom"><div className="api-status"><span className={`pulse ${apiHealth==="offline"?"offline":""}`}/>{apiHealth==="online"?"API connected":apiHealth==="checking"?"Checking API…":"API unavailable"}</div><div className="version">v0.2.0 · local control plane</div></div>
    </aside>
    <main><header className="topbar"><div className="crumb">CARRERSHUNT <span>/</span> {nav.find(x=>x[0]===page)?.[1].toUpperCase()}</div><div className="topbar-actions"><button className="refresh" onClick={refresh}>↻ Refresh</button>{SUPABASE_CONFIGURED && <button className="signout" onClick={()=>{clearSession();setAuthSession(null);setData({jobs:[],companies:[],applications:[],candidate:null});setPage("overview")}}>Sign out</button>}</div></header>
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
