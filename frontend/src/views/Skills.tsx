import { useEffect, useState } from "react";
import { getTopSkills, type TopSkills } from "../api";

const pct = (x: number) => `${(x * 100).toFixed(1)}%`;

export default function Skills() {
  const [month, setMonth] = useState("");
  const [data, setData] = useState<TopSkills | null>(null);
  const [months, setMonths] = useState<string[]>([]);
  const [err, setErr] = useState("");
  const [table, setTable] = useState(false);
  const [tip, setTip] = useState<number | null>(null);

  useEffect(() => {
    setErr("");
    getTopSkills(month || undefined).then((d) => {
      setData(d);
      setMonths((old) => (old.length ? old : d.months));
    }, (e: Error) => setErr(e.message));
  }, [month]);

  const skills = data?.skills ?? [];
  const max = Math.max(1, ...skills.map((s) => s.jd_count));
  const row = 28, labelW = 120, valW = 56, W = 600;
  const barW = W - labelW - valW;

  return (
    <section aria-labelledby="h-skills">
      <h2 id="h-skills">Kỹ năng được yêu cầu nhiều nhất</h2>
      <div className="controls">
        <label>Tháng{" "}
          <select value={month} onChange={(e) => setMonth(e.target.value)}>
            <option value="">Tất cả</option>
            {months.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </label>
        <label><input type="checkbox" checked={table} onChange={(e) => setTable(e.target.checked)} /> Xem bảng</label>
      </div>
      {err && <p role="alert" className="alert">{err}</p>}
      {data && <p className="muted">Tính trên {data.jd_total} JD đã trích kỹ năng</p>}
      {data && !table && (
        <div className="chart">
          <svg viewBox={`0 0 ${W} ${skills.length * row + 4}`} role="group"
            aria-label="Biểu đồ cột ngang kỹ năng theo số JD">
            {[0, 0.25, 0.5, 0.75, 1].map((f) => (
              <line key={f} className="grid" x1={labelW + f * barW} x2={labelW + f * barW} y1={0} y2={skills.length * row} />
            ))}
            {skills.map((s, i) => {
              const w = Math.max(4, (s.jd_count / max) * barW), y = i * row + 4, h = row - 8, r = 4;
              return (
                <g key={s.skill} tabIndex={0} className="bar" role="img"
                  aria-label={`${s.skill}: ${s.jd_count} JD, ${pct(s.share)}`}
                  onMouseEnter={() => setTip(i)} onMouseLeave={() => setTip(null)}
                  onFocus={() => setTip(i)} onBlur={() => setTip(null)}>
                  <rect x={0} y={i * row} width={W} height={row} fill="transparent" />
                  <text className="lbl" x={labelW - 8} y={y + h / 2 + 4} textAnchor="end">{s.skill}</text>
                  {/* góc bo 4px ở đầu giá trị, đầu gốc vuông */}
                  <path className="fill" d={`M${labelW},${y} h${w - r} a${r},${r} 0 0 1 ${r},${r} v${h - 2 * r} a${r},${r} 0 0 1 ${-r},${r} h${r - w} z`} />
                  <text className="lbl" x={labelW + w + 6} y={y + h / 2 + 4}>{pct(s.share)}</text>
                </g>
              );
            })}
          </svg>
          {tip !== null && skills[tip] && (
            <div className="tooltip" role="tooltip">
              <strong>{skills[tip].skill}</strong>: {skills[tip].jd_count} JD · {pct(skills[tip].share)}
            </div>
          )}
        </div>
      )}
      {data && table && (
        <div className="scroll">
          <table>
            <thead><tr><th scope="col">Kỹ năng</th><th scope="col">Số JD</th><th scope="col">Tỉ lệ</th></tr></thead>
            <tbody>
              {skills.map((s) => (
                <tr key={s.skill}><th scope="row">{s.skill}</th><td>{s.jd_count}</td><td>{pct(s.share)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
