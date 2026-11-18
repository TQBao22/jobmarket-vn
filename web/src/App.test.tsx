import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import App from "./App";

const json = (body: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));

const top = {
  months: ["2026-10", "2026-11"], jd_total: 10,
  skills: [
    { skill: "Python", jd_count: 8, share: 0.8 },
    { skill: "SQL", jd_count: 5, share: 0.5 },
    { skill: "Docker", jd_count: 2, share: 0.2 },
  ],
};
const jobs = {
  total: 7,
  jobs: [{ url: "https://example.test/j1", title: "Kỹ sư thử", company: "Công ty A",
    date_posted: "2026-11-10", valid_through: null, skills: ["Python", "Docker"] }],
};

function mockFetch(extra?: (url: string, init?: RequestInit) => Promise<Response> | undefined) {
  const fn = vi.fn((url: string, init?: RequestInit) => {
    const r = extra?.(url, init);
    if (r) return r;
    if (url.startsWith("/api/health")) return json({ status: "ok", jobs: 12, ollama: true, cv_model: "m" });
    if (url.startsWith("/api/skills/top")) return json(top);
    if (url.startsWith("/api/jobs")) return json(jobs);
    return json({ detail: "không có" }, 404);
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}
const calls = (fn: ReturnType<typeof mockFetch>) => fn.mock.calls.map((c) => c[0] as string);

describe("Kỹ năng", () => {
  it("vẽ cột theo thứ tự và chuyển sang bảng", async () => {
    mockFetch();
    render(<App />);
    expect(await screen.findByText(/12 JD · Ollama bật/)).toBeInTheDocument();
    const bars = await screen.findAllByRole("img");
    expect(bars.map((b) => b.getAttribute("aria-label"))).toEqual([
      "Python: 8 JD, 80.0%", "SQL: 5 JD, 50.0%", "Docker: 2 JD, 20.0%",
    ]);
    await userEvent.click(screen.getByLabelText("Xem bảng"));
    const rows = within(screen.getByRole("table")).getAllByRole("row");
    expect(rows).toHaveLength(4);
    expect(rows[1]).toHaveTextContent("Python8");
  });

  it("đổi tháng thì gọi lại với ?month=", async () => {
    const fn = mockFetch();
    render(<App />);
    await screen.findAllByRole("img");
    await userEvent.selectOptions(screen.getByLabelText("Tháng"), "2026-11");
    await waitFor(() => expect(calls(fn)).toContain("/api/skills/top?month=2026-11"));
  });
});

describe("Việc làm", () => {
  it("lọc theo kỹ năng gọi /api/jobs?skill=", async () => {
    const fn = mockFetch();
    window.location.hash = "jobs";
    render(<App />);
    const link = await screen.findByRole("link", { name: "Kỹ sư thử" });
    expect(link).toHaveAttribute("target", "_blank");
    expect(screen.getByText("Tổng: 7 JD")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Kỹ năng"), "Docker");
    await waitFor(() => expect(calls(fn)).toContain("/api/jobs?skill=Docker&open_only=true"));
    await userEvent.click(screen.getByLabelText("Chỉ JD đang mở"));
    await waitFor(() => expect(calls(fn)).toContain("/api/jobs?skill=Docker&open_only=false"));
  });
});

describe("Khớp CV", () => {
  const open = () => { window.location.hash = "match"; };

  it("từ chối sai loại và quá 5 MB ở client", async () => {
    const fn = mockFetch();
    open();
    render(<App />);
    const input = screen.getByLabelText(/Tệp CV/);
    await userEvent.upload(input, new File(["x"], "cv.docx"));
    expect(screen.getByRole("alert")).toHaveTextContent("Chỉ nhận tệp .pdf hoặc .txt");
    const big = new File(["x"], "cv.pdf");
    Object.defineProperty(big, "size", { value: 5 * 1024 * 1024 + 1 });
    await userEvent.upload(input, big);
    expect(screen.getByRole("alert")).toHaveTextContent("5 MB");
    await userEvent.click(screen.getByRole("button", { name: "Khớp CV" }));
    expect(calls(fn).some((u) => u === "/api/match")).toBe(false);
  });

  it("gửi multipart và hiện matched/missing", async () => {
    const fn = mockFetch((url) => url === "/api/match" ? json({
      model: "m", cv_skills: ["Python", "SQL"],
      matches: [{ url: "https://example.test/j1", title: "Kỹ sư thử", company: "Công ty A",
        score: 0.62, matched: ["Python"], missing: ["Docker"] }],
    }) : undefined);
    open();
    render(<App />);
    await userEvent.upload(screen.getByLabelText(/Tệp CV/), new File(["cv"], "cv.txt", { type: "text/plain" }));
    await userEvent.click(screen.getByRole("button", { name: "Khớp CV" }));
    expect(await screen.findByText("62%")).toBeInTheDocument();
    expect(screen.getByText("✓ Python")).toBeInTheDocument();
    expect(screen.getByText("+ Docker")).toBeInTheDocument();
    const call = fn.mock.calls.find((c) => c[0] === "/api/match")!;
    const body = call[1]!.body as FormData;
    expect(call[1]!.method).toBe("POST");
    expect((body.get("file") as File).name).toBe("cv.txt");
    expect(body.get("top_k")).toBe("10");
  });

  it("hiện detail khi 503", async () => {
    mockFetch((url) => url === "/api/match" ? json({ detail: "Ollama không chạy" }, 503) : undefined);
    open();
    render(<App />);
    await userEvent.upload(screen.getByLabelText(/Tệp CV/), new File(["cv"], "cv.txt"));
    await userEvent.click(screen.getByRole("button", { name: "Khớp CV" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Ollama không chạy");
  });
});
