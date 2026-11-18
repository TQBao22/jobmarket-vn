import { useEffect, useState } from "react";
import { getJobs, type Jobs as JobsData } from "../api";
import Chips from "./Chips";

export default function Jobs() {
  const [input, setInput] = useState("");
  const [skill, setSkill] = useState("");
  const [openOnly, setOpenOnly] = useState(true);
  const [data, setData] = useState<JobsData | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    const t = setTimeout(() => setSkill(input.trim()), 300);
    return () => clearTimeout(t);
  }, [input]);
  useEffect(() => {
    setErr("");
    getJobs(skill, openOnly).then(setData, (e: Error) => setErr(e.message));
  }, [skill, openOnly]);

  return (
    <section aria-labelledby="h-jobs">
      <h2 id="h-jobs">Việc làm</h2>
      <div className="controls">
        <label>Kỹ năng{" "}
          <input type="search" value={input} placeholder="vd. Docker" onChange={(e) => setInput(e.target.value)} />
        </label>
        <label><input type="checkbox" checked={openOnly} onChange={(e) => setOpenOnly(e.target.checked)} /> Chỉ JD đang mở</label>
      </div>
      {err && <p role="alert" className="alert">{err}</p>}
      {data && <p className="muted" aria-live="polite">Tổng: {data.total} JD</p>}
      <ul className="list">
        {data?.jobs.map((j) => (
          <li key={j.url}>
            <a href={j.url} target="_blank" rel="noopener">{j.title}</a>
            <div className="muted">{j.company} · {j.date_posted ?? "không rõ ngày"}</div>
            <Chips items={j.skills} label="Kỹ năng của JD" />
          </li>
        ))}
      </ul>
    </section>
  );
}
