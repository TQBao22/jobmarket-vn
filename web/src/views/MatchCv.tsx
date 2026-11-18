import { useState } from "react";
import { postMatch, type MatchResult } from "../api";
import Chips from "./Chips";

const MAX = 5 * 1024 * 1024;

export default function MatchCv() {
  const [file, setFile] = useState<File | null>(null);
  const [topK, setTopK] = useState(10);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [res, setRes] = useState<MatchResult | null>(null);

  const pick = (f: File | null) => {
    setFile(null); setErr("");
    if (!f) return;
    if (!/\.(pdf|txt)$/i.test(f.name)) return setErr("Chỉ nhận tệp .pdf hoặc .txt.");
    if (f.size > MAX) return setErr("Tệp lớn hơn 5 MB.");
    setFile(f);
  };
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return setErr("Hãy chọn một tệp CV hợp lệ.");
    setBusy(true); setErr(""); setRes(null);
    try { setRes(await postMatch(file, topK)); }
    catch (x) { setErr((x as Error).message); }
    finally { setBusy(false); }
  };

  return (
    <section aria-labelledby="h-match">
      <h2 id="h-match">Khớp CV với JD đang mở</h2>
      <form onSubmit={submit} className="controls">
        <label>Tệp CV (.pdf, .txt, tối đa 5 MB){" "}
          {/* không đặt accept: để kiểm tra loại tệp phía client luôn chạy */}
          <input type="file" onChange={(e) => pick(e.target.files?.[0] ?? null)} />
        </label>
        <label>Số kết quả{" "}
          <input type="number" min={1} max={50} value={topK}
            onChange={(e) => setTopK(Math.min(50, Math.max(1, Number(e.target.value) || 1)))} />
        </label>
        <button type="submit" disabled={busy}>Khớp CV</button>
      </form>
      <p className="muted">CV chỉ xử lý trên máy này, không lưu.</p>
      {busy && <p role="status">Đang xử lý bằng model local, có thể mất khoảng 1 phút…</p>}
      {err && <p role="alert" className="alert">{err}</p>}
      {res && (
        <>
          <h3>Kỹ năng trong CV</h3>
          <Chips items={res.cv_skills} label="Kỹ năng trong CV" />
          <h3>Việc làm phù hợp</h3>
          <ol className="list">
            {res.matches.map((m) => (
              <li key={m.url}>
                <a href={m.url} target="_blank" rel="noopener">{m.title}</a>
                {" "}<strong>{Math.round(m.score * 100)}%</strong>
                <div className="muted">{m.company}</div>
                <Chips items={m.matched} prefix="✓ " label="Kỹ năng đã có" />
                <Chips items={m.missing} prefix="+ " label="Kỹ năng còn thiếu" />
              </li>
            ))}
          </ol>
        </>
      )}
    </section>
  );
}
