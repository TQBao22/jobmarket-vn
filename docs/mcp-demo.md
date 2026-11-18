# Demo MCP: 5 câu hỏi mẫu (tiêu chí v3)

Server: `python -m jobmarket.mcp` (spec 2026-07-28, `docs/research/mcp-spec.md`), cấu hình `.mcp.json`. Client: Claude Code 2.1.325, model Haiku, chỉ cho phép 3 tool của server:

```
claude -p "<câu hỏi> Chỉ dùng tool của server jobmarket. Trả lời ngắn gọn bằng tiếng Việt." \
  --mcp-config .mcp.json --strict-mcp-config --max-turns 6 --model haiku \
  --allowedTools "mcp__jobmarket__top_skills,mcp__jobmarket__search_jobs,mcp__jobmarket__match_skills"
```

Đáp án đúng tính bằng cách gọi thẳng `jobmarket.query` trên `data/jobs.db` (không qua MCP hay Claude), ngày 2026-11-18, 128 JD đã trích kỹ năng. Dữ liệu đổi sau mỗi lần crawl hằng tuần nên đáp án chỉ đúng cho ngày này.

| # | Câu hỏi | Tool | Đáp án đúng | Claude Code trả lời | Kết quả |
|---|---|---|---|---|---|
| 1 | 3 kỹ năng được tuyển nhiều nhất trong tin AI/Data trên ITviec là gì, mỗi kỹ năng có trong bao nhiêu tin? | `top_skills` | Python 86, SQL 57, LLM 44 (128 tin) | Python 86, SQL 57, LLM 44, trên 128 tin | Đúng |
| 2 | Tháng 11/2026, kỹ năng nào được yêu cầu nhiều nhất và chiếm bao nhiêu % số tin của tháng? | `top_skills` | Python, 35/51 = 68,6% | Python, 35/51 tin, 68,6% | Đúng |
| 3 | Hiện có bao nhiêu tin đang mở yêu cầu Docker? Kể 3 tin mới nhất (tên + công ty). | `search_jobs` | 39; ETP TESOL, ACB, Elcom | 39; ETP TESOL, ACB, Elcom (kèm tên vị trí, ngày đăng) | Đúng |
| 4 | Mình biết Python, SQL, Docker, LangChain, RAG. Tin đang mở nào hợp nhất, và mình còn thiếu gì cho tin đó? | `match_skills` | Mặt Trời Vàng "AI Application Prompt Engineering, RAG, Agentic AI", điểm 0,297, thiếu Prompt Engineering, Agentic AI | Như đáp án (lần 2) | Đúng ở lần 2 |
| 5 | Mình có Python và SQL. Trong 3 kỹ năng hot nhất, mình còn thiếu kỹ năng nào, và có bao nhiêu tin đang mở cần nó? | `top_skills` + `search_jobs` | LLM, 42 tin đang mở | LLM, 42 tin đang mở | Đúng |

**5/5 đúng.**

## Câu 4: lần 1 sai, sửa mô tả tool
- Lần 1, Claude bỏ qua thứ tự của tool. Nó chọn tin MTI Technology vì khớp nhiều kỹ năng nhất (4 kỹ năng, điểm 0,108), rồi tự liệt kê "còn thiếu" theo ý mình thay vì dùng trường `missing`. Mặt Trời Vàng chỉ được nhắc là phương án thay thế.
- Nguyên nhân: mô tả `match_skills` không nói `matches` đã sắp theo `score`, cũng không nói `score` tính theo tỉ lệ trọng số. Tin yêu cầu nhiều kỹ năng nên điểm thấp dù khớp nhiều.
- Sửa: mô tả nói rõ phần tử đầu là tin hợp nhất, `score` tính thế nào, `missing` lấy đúng từ tin đó. Lần 2 Claude trả đúng đáp án và tự giải thích vì sao MTI điểm thấp.
- Bài học cho v4: agent đọc mô tả tool như đọc tài liệu API. Quy tắc tính điểm không ghi trong mô tả thì agent tự đặt quy tắc riêng.
