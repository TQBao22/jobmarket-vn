# MCP spec — handshake, tools, lỗi cho server stdio tự viết (kiểm tra 2026-11-18)

Ghi chú đọc spec gốc, phục vụ v3 (MCP server stdio, stdlib, 3 tool chỉ đọc). Chữ in hoa (MUST/SHOULD/MAY) giữ nguyên theo spec.

## Kết luận
- **Phiên bản hiện hành là `2026-07-28`** ("The **current** protocol version is 2026-07-28", trang Versioning). Spec gọi bản này là **modern**: stateless, không còn `initialize`. Bản `2025-11-25` trở về trước là **legacy**: có handshake `initialize`.
- **Claude Code 2.1.325 là client dual-era.** Nó gửi probe `server/discover` với `2026-07-28` trước. Server không trả lời thì nó lùi về `initialize` `2025-11-25` (log bên dưới). Cách làm này khớp mục "stdio: Backward Compatibility" của spec.
- **Đề xuất: chỉ hỗ trợ `2026-07-28`.** Lý do:
  1. Claude Code thử bản này trước, nên server trả lời được `server/discover` thì client ở lại modern.
  2. Không có trạng thái kết nối, mỗi request tự đủ. Test chỉ cần gửi một dòng JSON và so response, không phải dựng handshake.
  3. Ít method hơn: `server/discover`, `tools/list`, `tools/call`. Bản này đã bỏ `ping` và `notifications/initialized`.
  4. Quy tắc trong `.claude/rules/mcp-server.md` yêu cầu viết theo đúng phiên bản Claude Code gửi lên, tức `2026-07-28`.
- **Cái giá:** client chỉ biết legacy (đời cũ, chỉ gửi `initialize`) sẽ không dùng được server. Spec cho phép điều này (ma trận "Legacy / Modern: Fails"). Nếu sau này cần phục vụ client legacy thì thêm `initialize`, `notifications/initialized` và `ping` (xem mục 2). Server lúc đó thành dual-era.
- **Rủi ro chính:** mới thấy Claude Code gửi probe, **chưa thấy** nó chạy tiếp `tools/list` modern sau khi nhận `DiscoverResult`. Cần chạy thử và ghi log trước khi chốt (xem "Chưa xác minh").

## Log thật từ Claude Code 2.1.325
Ghi ngày 2026-11-18, server chưa trả lời `server/discover`. Claude Code gửi:
```
{"jsonrpc":"2.0","id":"server-discover-probe-1","method":"server/discover","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientInfo":{"name":"claude-code","version":"2.1.325",...},"io.modelcontextprotocol/clientCapabilities":{"roots":{"listChanged":true},"elicitation":{"form":{},"url":{}}}}}}
```
Server không trả lời, Claude Code chuyển sang:
```
{"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{...},"clientInfo":{...}},"jsonrpc":"2.0","id":0}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"method":"tools/list","jsonrpc":"2.0","id":1}
```

## Nguồn (truy cập 2026-11-18)
Repo gốc là `github.com/modelcontextprotocol/modelcontextprotocol`, nhánh `main`. Trang web `modelcontextprotocol.io/specification/<ver>/...` được build từ cùng file `.mdx`.
| Văn bản | Đường dẫn trong repo |
|---|---|
| Versioning (trang chung) | https://modelcontextprotocol.io/specification/versioning |
| Schema 2026-07-28 (nguồn sự thật) | `schema/2026-07-28/schema.ts` |
| Schema 2025-11-25 | `schema/2025-11-25/schema.ts` |
| Discovery | `docs/specification/2026-07-28/server/discover.mdx` |
| Versioning and Compatibility | `docs/specification/2026-07-28/basic/versioning.mdx` |
| Overview (`_meta`, mã lỗi, stateless) | `docs/specification/2026-07-28/basic/index.mdx` |
| stdio | `docs/specification/2026-07-28/basic/transports/stdio.mdx` |
| Tools 2026 / 2025 | `docs/specification/{2026-07-28,2025-11-25}/server/tools.mdx` |
| Key Changes 2026 / 2025 | `docs/specification/{2026-07-28,2025-11-25}/changelog.mdx` |
| Lifecycle, Ping, Transports 2025 | `docs/specification/2025-11-25/basic/{lifecycle,utilities/ping,transports}.mdx` |

## 1. `server/discover` và request stateless (2026-07-28)
- discover.mdx: "Servers **MUST** implement it". Response gồm `supportedVersions`, `capabilities`, `_meta['io.modelcontextprotocol/serverInfo']` (SHOULD) và `instructions` (tuỳ chọn).
- schema.ts: `DiscoverResult extends CacheableResult`, và `CacheableResult extends Result`. Vì vậy **`resultType`, `ttlMs`, `cacheScope` đều bắt buộc**:
  - `Result.resultType`: "Servers implementing this protocol version MUST include this field".
  - `CacheableResult` có `ttlMs: number` (≥0) và `cacheScope: "public" | "private"`, cả hai không có dấu `?`.
- Server khai báo tool thì phải có capability `tools` (tools.mdx: "Servers that support tools **MUST** declare the `tools` capability"). `listChanged` là tuỳ chọn.

Response tối thiểu cho request `id:"server-discover-probe-1"` (`serverInfo` là `Implementation`, bắt buộc có `name` và `version`):
```json
{"jsonrpc":"2.0","id":"server-discover-probe-1","result":{"resultType":"complete","supportedVersions":["2026-07-28"],"capabilities":{"tools":{}},"ttlMs":3600000,"cacheScope":"public","_meta":{"io.modelcontextprotocol/serverInfo":{"name":"jobmarket-vn","version":"0.1.0"}}}}
```

**Không có `initialize`.** Changelog 2026 mục 2: "Make MCP stateless: remove the `initialize`/`notifications/initialized` handshake". `ClientRequest` của schema 2026 chỉ còn: `server/discover`, `completion/complete`, `prompts/*`, `resources/*`, `subscriptions/listen`, `tools/call`, `tools/list`.

**`_meta` trên mỗi request.** schema: `RequestParams { _meta: RequestMetaObject }` là bắt buộc. `ListToolsRequest` và `CallToolRequest` đều kế thừa nó. Bảng "Per-request protocol fields" trong index.mdx:
| Key | Bắt buộc |
|---|---|
| `io.modelcontextprotocol/protocolVersion` | Có |
| `io.modelcontextprotocol/clientCapabilities` | Có |
| `io.modelcontextprotocol/clientInfo` | Không (client SHOULD gửi) |
| `io.modelcontextprotocol/logLevel` | Không |

Server phải kiểm từng request, không dựa vào request trước. index.mdx: "Servers **MUST NOT** rely on prior requests over the same connection to establish context".
- **Thiếu field bắt buộc:** "the server **MUST** reject it with JSON-RPC error code `-32602` (Invalid params)".
- **Sai phiên bản:** server **MUST** trả `UnsupportedProtocolVersionError`, `code: -32022`, `data: {supported, requested}` (versioning.mdx):
  ```json
  {"jsonrpc":"2.0","id":1,"error":{"code":-32022,"message":"Unsupported protocol version","data":{"supported":["2026-07-28"],"requested":"2025-11-25"}}}
  ```
- **Mỗi result:** SHOULD có `_meta["io.modelcontextprotocol/serverInfo"]` ("Per-response protocol fields").
- **Client thiếu capability:** nếu cần capability mà client không khai thì trả `-32021`. 3 tool chỉ đọc không cần capability nào của client, nên không gặp trường hợp này.

## 2. Server chỉ legacy, hoặc server modern gặp client legacy
**Server chỉ hỗ trợ `2025-11-25`.** Theo stdio.mdx, client nhận "any other error, or does not respond within a reasonable timeout" thì coi server là legacy và lùi về `initialize`. Spec nói: "The fallback **MUST NOT** be keyed to one specific error code: legacy servers respond ... (commonly `-32601` or `-32602`) or not at all."
- Trả ngay `-32601` (JSON-RPC "Method not found", `METHOD_NOT_FOUND` trong schema) là đúng chuẩn. Client lùi về legacy luôn, không phải chờ hết timeout.
- **Không** trả `-32022`, `-32020`, `-32021` cho `server/discover`. Đây là "recognized modern error", client sẽ ở lại modern: "Do **not** fall back to `initialize`".

**Server hỗ trợ `2026-07-28` có phải giữ `initialize` không?** Không bắt buộc. versioning.mdx: dual-era "**MAY** implement both behaviors". Server chỉ modern thì "**SHOULD** name the protocol versions it supports in any error it returns to an `initialize` request". Ví dụ (mã lỗi tuỳ cài đặt, theo ma trận tương thích):
```json
{"jsonrpc":"2.0","id":0,"error":{"code":-32601,"message":"initialize is not supported; supported versions: 2026-07-28"}}
```
Nếu muốn dual-era, thêm 3 việc (lifecycle.mdx và ping.mdx bản 2025):
- `initialize`: trả `{protocolVersion, capabilities, serverInfo}`. Server hỗ trợ bản client xin thì "**MUST** respond with the same version".
- `notifications/initialized`: không trả lời.
- `ping`: trả `{"result":{}}`.

## 3. Schema `tools/list` và `tools/call`
| Trường | 2025-11-25 | 2026-07-28 |
|---|---|---|
| `Tool.name` (bắt buộc), `title`, `description`, `icons`, `annotations`, `_meta` | có | có |
| `Tool.inputSchema` (bắt buộc) | `{type:"object", properties?, required?}` | `{type:"object", ...}`, mọi keyword JSON Schema 2020-12 |
| `Tool.outputSchema` | tuỳ chọn, `type:"object"` | tuỳ chọn, schema bất kỳ |
| `Tool.execution` (task) | có | không còn (tasks thành extension) |
| `ListToolsResult` | `tools`, `nextCursor?` | thêm bắt buộc `resultType`, `ttlMs`, `cacheScope` |
| `CallToolRequestParams` | `name`, `arguments?` | `name`, `arguments?`, `_meta` bắt buộc |
| `CallToolResult` | `content` (bắt buộc), `structuredContent?` (object), `isError?` | như bên trái, thêm `resultType`; `structuredContent` là JSON bất kỳ |

`ToolAnnotations` gồm `title`, `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`. Server này nên khai `readOnlyHint: true`.

Hai quy tắc chung cho cả hai bản (tools.mdx):
- Tool trả `structuredContent` thì "SHOULD also return the serialized JSON in a TextContent block".
- Có `outputSchema` thì "Servers **MUST** provide structured results that conform to this schema".

Tên tool SHOULD dài 1–128 ký tự, chỉ gồm `A-Z a-z 0-9 _ - .`. Bản 2026 thêm: server SHOULD trả danh sách tool theo thứ tự cố định.

Ví dụ 2026-07-28 (bản 2025 thì bỏ `resultType`, `ttlMs`, `cacheScope`):
```json
{"jsonrpc":"2.0","id":2,"result":{"resultType":"complete","tools":[{"name":"top_skills","description":"Top kỹ năng theo số JD","inputSchema":{"type":"object","properties":{"limit":{"type":"integer","minimum":1,"maximum":50}}},"annotations":{"readOnlyHint":true}}],"ttlMs":300000,"cacheScope":"public"}}
{"jsonrpc":"2.0","id":3,"result":{"resultType":"complete","content":[{"type":"text","text":"[{\"skill\":\"python\",\"jobs\":97}]"}],"structuredContent":[{"skill":"python","jobs":97}],"isError":false}}
```

## 4. Lỗi giao thức và lỗi thực thi tool
Mã chuẩn JSON-RPC có trong cả hai schema: `-32700` parse, `-32600` invalid request, `-32601` method not found, `-32602` invalid params, `-32603` internal. Không bản nào có batch.

Response lỗi có `id?: RequestId`, trong đó `RequestId = string | number`. Khi không đọc được id (parse error) thì **bỏ trường `id`**, không gửi `null`. Đây là theo schema MCP; JSON-RPC 2.0 gốc dùng `null`.

tools.mdx (cả hai bản) chia lỗi làm hai loại:
| Trường hợp | Loại | Trả về |
|---|---|---|
| Tool không tồn tại | Protocol error | `{"code":-32602,"message":"Unknown tool: xyz"}` (ví dụ có sẵn trong spec, cả 2 bản) |
| Request sai schema `CallToolRequest` (thiếu `name`, `arguments` không phải object) | Protocol error | `-32602` |
| Server lỗi (DB hỏng...) | Protocol error | `-32603` |
| Tham số sai giá trị/kiểu theo `inputSchema` ("date in wrong format, value out of range") | Tool execution error | `result` với `isError: true` và `content` text giải thích |
| Lỗi nghiệp vụ, lỗi API ngoài | Tool execution error | như trên |

Changelog 2025-11-25 mục 5 (SEP-1303): "input validation errors should be returned as Tool Execution Errors rather than Protocol Errors to enable model self-correction". Bản 2026 giữ nguyên phân loại này.

## 5. Notification, `ping`, framing stdio
- **Notification:** "The receiver **MUST NOT** send a response" (index.mdx, cả hai bản). Server bỏ qua mọi `notifications/*` không biết, kể cả `notifications/initialized` và `notifications/cancelled`.
- **Notification ở bản 2026:** `ClientNotification` chỉ còn `CancelledNotification`. Với `notifications/cancelled`, server "**MUST NOT** send any further messages" cho request đó. Tool chạy đồng bộ và nhanh thì bỏ qua được.
- **`ping`:** bản 2025 "receiver **MUST** respond promptly with an empty response" (`"result":{}`). Bản 2026 đã bỏ (changelog mục 5). Server modern nhận `ping` thì trả `-32601`.
- **Framing** (stdio.mdx, cả hai bản):
  - Mỗi message là một dòng, "**MUST NOT** contain embedded newlines". Ghi bằng `json.dumps(obj, ensure_ascii=False)`: escape `\n` trong chuỗi, không có newline thật.
  - stdout chỉ chứa message MCP hợp lệ.
  - stderr "**MAY**" dùng cho mọi loại log.
  - Bản 2026 thêm: server "**MUST NOT** write JSON-RPC _requests_ to `stdout`", và "**SHOULD** exit promptly" khi stdin EOF.
- **Request ID:** chuỗi hoặc số, không `null`. Response phải trả lại đúng id đó. Log thật cho thấy Claude Code dùng cả id chuỗi (`"server-discover-probe-1"`) lẫn id số (`0`).

## 6. Method server phải xử lý (đề xuất: chỉ 2026-07-28)
| Message vào | Xử lý |
|---|---|
| `server/discover` | `DiscoverResult` (mục 1) |
| `tools/list` | kiểm `_meta` → `ListToolsResult` |
| `tools/call` | kiểm `_meta` → tool lạ: `-32602`; tham số sai: `isError:true`; OK: `content` + `structuredContent` |
| `initialize`, `ping`, method khác có `id` | `-32601`; với `initialize` thì nêu phiên bản hỗ trợ trong `message` |
| Bất kỳ message không có `id` (notification) | không trả lời |
| Dòng không parse được JSON | `-32700`, không có `id` |

Kiểm `_meta` trên mọi request, kể cả `server/discover`:
- thiếu `_meta`, `protocolVersion` hoặc `clientCapabilities` → `-32602`;
- `protocolVersion` khác `2026-07-28` → `-32022`.

## Chưa xác minh
- Sau khi nhận `DiscoverResult`, Claude Code 2.1.325 có gửi `tools/list`/`tools/call` kèm `_meta` đúng như spec không? Mới chỉ thấy probe. Cần ghi log stdin của server khi chạy thật.
- Ví dụ `tools/list` và `tools/call` trong tools.mdx 2026 **không có** `_meta`, trong khi schema bắt buộc có. Có thể ví dụ chỉ rút gọn. Server nên kiểm theo schema, nhưng nếu Claude Code thật không gửi `_meta` trên `tools/list` thì phải nới quy tắc này.
- Claude Code chờ probe bao lâu trước khi lùi về `initialize`: spec chỉ ghi "reasonable timeout", không có số.
- Claude Code có dùng `structuredContent` hay chỉ đọc `content` text: không có tài liệu sơ cấp. Cứ gửi cả hai theo SHOULD của spec.
- Claude Code có xử lý `ttlMs`/`cacheScope` (cache danh sách tool) không: không có tài liệu.
