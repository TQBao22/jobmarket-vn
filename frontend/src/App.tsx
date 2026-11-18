import { useEffect, useState } from "react";
import { getHealth, type Health } from "./api";
import Skills from "./views/Skills";
import Jobs from "./views/Jobs";
import MatchCv from "./views/MatchCv";

const TABS = [
  { id: "skills", label: "Kỹ năng", View: Skills },
  { id: "jobs", label: "Việc làm", View: Jobs },
  { id: "match", label: "Khớp CV", View: MatchCv },
] as const;

const fromHash = () => TABS.find((t) => t.id === window.location.hash.slice(1))?.id ?? "skills";

export default function App() {
  const [tab, setTab] = useState<string>(fromHash);
  const [health, setHealth] = useState<Health | null | "err">(null);

  useEffect(() => {
    const on = () => setTab(fromHash());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  useEffect(() => { getHealth().then(setHealth, () => setHealth("err")); }, []);

  const select = (id: string) => { window.location.hash = id; setTab(id); };
  const onKey = (e: React.KeyboardEvent, i: number) => {
    const d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (!d) return;
    const next = TABS[(i + d + TABS.length) % TABS.length].id;
    select(next);
    document.getElementById(`tab-${next}`)?.focus();
  };
  const Active = TABS.find((t) => t.id === tab)!.View;

  return (
    <>
      <header className="top">
        <h1>JobMarket VN</h1>
        <p className="health" role="status">
          {health === null ? "Đang kiểm tra máy chủ…"
            : health === "err" ? "Không kết nối được API"
            : `${health.jobs} JD · Ollama ${health.ollama ? "bật" : "tắt"}`}
        </p>
      </header>
      <div role="tablist" aria-label="Chế độ xem" className="tabs">
        {TABS.map((t, i) => (
          <button key={t.id} role="tab" id={`tab-${t.id}`} aria-selected={tab === t.id}
            aria-controls="panel" tabIndex={tab === t.id ? 0 : -1}
            onClick={() => select(t.id)} onKeyDown={(e) => onKey(e, i)}>{t.label}</button>
        ))}
      </div>
      <main id="panel" role="tabpanel" aria-labelledby={`tab-${tab}`}><Active /></main>
    </>
  );
}
