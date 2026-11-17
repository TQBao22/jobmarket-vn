# Anthropic — dùng output Claude để fine-tune model nhỏ (kiểm tra 2026-11-17)

Đây không phải tư vấn pháp lý. Đây là ghi chú đọc văn bản gốc, phục vụ ADR ở đầu v2.

## Kết luận
- **Không được (nếu chưa xin phép):** Usage Policy (AUP, hiệu lực 12/11/2026) áp dụng cho mọi người dùng, kể cả Claude Code và API. AUP cấm "Use outputs to train an AI model (e.g., “model scraping” or “model distillation”) without prior authorization from Anthropic". Câu này không giới hạn ở model cạnh tranh. Văn bản cũng không có ngoại lệ cho mục đích cá nhân, nghiên cứu hay phi thương mại. Kế hoạch v2 (lấy JSON của Haiku làm nhãn train cho Qwen) rơi đúng vào điều cấm này.
- **Đổi sang API không giải quyết được:** Commercial Terms chỉ cấm "train competing AI models", hẹp hơn Consumer Terms. Nhưng AUP vẫn áp dụng cho người dùng API, nên cấm chung về distillation vẫn còn.
- **Chạy `claude -p` theo script trên gói Pro/Max: chưa rõ, nhưng khả năng cao là được ở quy mô cá nhân.** Consumer Terms cấm truy cập bằng script, "except ... where we otherwise explicitly permit it". Tài liệu Claude Code hướng dẫn `-p` cho script và `claude setup-token` cho "CI pipelines and scripts" bằng OAuth của gói. Không có câu nào nói thẳng "Pro/Max được chạy `-p` hàng loạt". Rủi ro kỹ thuật: `--bare` không dùng gói và "will become the default for `-p` in a future release".
- **Phương án đề xuất:** dùng một model mở giấy phép Apache-2.0 (ví dụ Qwen3) làm teacher sinh nhãn train cho Qwen nhỏ. Claude chỉ làm baseline eval và nhánh fallback của router, tức là chỉ suy luận, không làm dữ liệu train. Cách khác là xin phép Anthropic bằng văn bản trước khi train.
- **Lưu ý gold set:** 40 JD gold hiện do claude-opus-5-5 gán. Dùng gold để **chấm điểm** thì không phải "train". Nhưng nếu đưa gold vào tập train thì cũng là train trên output Claude. Muốn dùng làm dữ liệu train thì phải gán lại bằng tay từ đầu. Chỉ duyệt và sửa nhãn Claude thì vẫn mập mờ.

## Nguồn (truy cập 2026-11-17)
| Văn bản | URL | Hiệu lực ghi trên trang |
|---|---|---|
| Consumer Terms of Service | https://www.anthropic.com/legal/consumer-terms | Oct 8, 2025 |
| Commercial Terms of Service | https://www.anthropic.com/legal/commercial-terms | Jun 17, 2025 |
| Usage Policy (AUP) | https://www.anthropic.com/legal/aup | Nov 12, 2026 |
| Claude Code — Legal and compliance | https://code.claude.com/docs/en/legal-and-compliance.md | không ghi ngày |
| Claude Code — Run programmatically (headless) | https://code.claude.com/docs/en/headless.md | không ghi ngày |
| Claude Code — Authentication | https://code.claude.com/docs/en/authentication.md | không ghi ngày |
| Qwen3-8B LICENSE (Apache-2.0) | https://huggingface.co/Qwen/Qwen3-8B/blob/main/LICENSE | — |
| Qwen2.5-3B-Instruct LICENSE (qwen-research) | https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/blob/main/LICENSE | — |
| README (thẻ `license`) Qwen2.5-1.5B-Instruct, Qwen3-1.7B, Qwen3-30B-A3B-Instruct-2507 | https://huggingface.co/Qwen/{model}/raw/main/README.md | — |

Tất cả các trang đều tải được. README của Qwen2.5-7B-Instruct trả về rỗng nên giấy phép của nó chưa được kiểm tra.

## 1. Văn bản nào áp dụng
- Claude Code docs: "Your use of Claude Code is subject to: Commercial Terms of Service - for Team, Enterprise, and Claude API users · Consumer Terms of Service - for Free, Pro, Max, and Ultra users".
- Cùng trang: "Claude Code usage is subject to the Anthropic Usage Policy."
- Consumer Terms (mở đầu): "These Terms ... govern your use of Claude.ai, Claude Pro, and other products and services that we may offer for individuals ... and they include our Acceptable Use Policy."
- AUP: "applies to anyone who submits inputs to Anthropic’s products or services ... This includes individuals using our apps (such as Claude.ai and Claude Code), developers and businesses using our API".

→ Project này đăng nhập gói cá nhân qua Claude Code, nên chịu **Consumer Terms + AUP**. Nếu chuyển sang API key thì chịu **Commercial Terms + AUP**.

## 2. Dùng output để train model
**AUP**, mục "Do Not Abuse Our Platform" thuộc Universal Usage Standards ("prohibitions that apply to all users and use cases"):
> Use outputs to train an AI model (e.g., “model scraping” or “model distillation”) without prior authorization from Anthropic

**Consumer Terms §3** ("You may not access or use ... our Services in the following ways"):
> To develop any products or services that compete with our Services, including to develop or train any artificial intelligence or machine learning algorithms or models or resell the Services.

**Commercial Terms D.4**:
> Customer may not and must not attempt to (a) access the Services to build a competing product or service, including to train competing AI models or resell the Services except as expressly approved by Anthropic

- Văn bản nói: AUP cấm việc train model trên output mà **không có điều kiện "cạnh tranh"**. Ngoại lệ duy nhất là "prior authorization from Anthropic". Không văn bản nào có ngoại lệ cho mục đích cá nhân, nghiên cứu hay phi thương mại.
- Diễn giải: câu trong Consumer Terms có thể đọc theo hai cách. Cách thứ nhất: "including ..." chỉ là ví dụ của hành vi cạnh tranh, nên một model nhỏ trích kỹ năng không cạnh tranh và không bị cấm. Cách thứ hai: cấm mọi việc train model. Commercial Terms nói rõ "competing". Dù đọc theo cách nào thì AUP vẫn cấm chung, và AUP áp dụng cho cả hai nhóm người dùng. Vì vậy câu hỏi "có cạnh tranh không" không còn quyết định kết quả.
- Mức xử lý theo AUP: "we may warn you or throttle, limit, suspend, or terminate your access". Repo công khai và bài viết sẽ mô tả rõ việc "distill Haiku sang Qwen", tức là tự công bố vi phạm.

## 3. Truy cập tự động / script (`claude -p`)
**Consumer Terms §3**:
> Except when you are accessing our Services via an Anthropic API Key or where we otherwise explicitly permit it, to access the Services through automated or non-human means, whether through a bot, script, or otherwise.

Claude Code docs:
- headless: "To run Claude Code in non-interactive mode, pass `-p` ..."; "You can wrap a non-interactive call in a script to use Claude as a project-specific linter or reviewer."
- authentication: "For CI pipelines, scripts, or other environments where interactive browser login isn't available, generate a one-year OAuth token with `claude setup-token`". Cùng trang: "Subscription OAuth credentials from `/login`. This is the default for Claude Pro, Max, Ultra, Team, and Enterprise users."
- legal-and-compliance: "Advertised usage limits for Pro, Max, and Ultra plans assume ordinary, individual usage of Claude Code and the Agent SDK." và "OAuth authentication is intended exclusively for purchasers of Claude Free, Pro, Max, Ultra, Team, and Enterprise subscription plans and is designed to support ordinary use of Claude Code and other native Anthropic applications."
- headless: "Set `ANTHROPIC_API_KEY` before running it, because bare mode doesn't use your subscription login" và "`--bare` is the recommended mode for scripted and SDK calls, and will become the default for `-p` in a future release."

- Văn bản nói: Anthropic có tài liệu chính thức về `-p` trong script và về token OAuth của gói cho script. Phần cấm rõ ràng nhắm vào bên thứ ba dùng gói để phục vụ người khác ("route requests through Free, Pro, Max, or Ultra plan credentials on behalf of their users"). AUP cũng cấm "services that route requests through consumer subscriptions".
- Diễn giải: tài liệu chính thức hướng dẫn chạy script bằng OAuth của gói. Có thể coi đây là "explicitly permit" cho việc dùng binary Claude Code chính thức trên máy cá nhân. Dù vậy, không câu nào nói thẳng điều đó, và "ordinary, individual usage" không có định nghĩa định lượng. Chạy ~130 JD theo lô 20 vẫn hợp lý ở quy mô cá nhân. Một job crawl định kỳ chạy lâu dài thì khó coi là "ordinary".
- Rủi ro kỹ thuật: khi `--bare` thành mặc định của `-p`, lệnh hiện tại sẽ cần cờ khác hoặc API key. ADR 0001 nên ghi thêm điều này.

## 4. Ai sở hữu output
- Consumer Terms §4: "Subject to your compliance with our Terms, we assign to you all of our right, title, and interest—if any—in Outputs."
- Commercial Terms B: "Customer (a) retains all rights to its Inputs, and (b) owns its Outputs ... Anthropic hereby assigns to Customer its right, title and interest (if any) in and to Outputs."
- Diễn giải: người dùng sở hữu output, nhưng sở hữu output **không** gỡ được giới hạn về cách dùng trong AUP và Terms. Bản Consumer còn kèm điều kiện "Subject to your compliance".
- Phụ: Consumer Terms §4 cho phép Anthropic dùng Materials để train "unless you opt out of training through your account settings". Nội dung JD đã lọc PII vẫn có thể được Anthropic dùng nếu chưa tắt tuỳ chọn này.

## 5. Phương án thay thế
1. **Teacher là model mở Apache-2.0** (đề xuất). Thẻ `license: apache-2.0` có trên Qwen3-8B, Qwen3-1.7B, Qwen3-30B-A3B-Instruct-2507 và Qwen2.5-1.5B-Instruct. Apache-2.0 §2 cấp quyền "to reproduce, prepare Derivative Works of, publicly display, publicly perform, sublicense, and distribute the Work". Giấy phép này không có điều khoản nào giới hạn việc dùng output. Diễn giải: được dùng output của teacher Qwen3 để train student Qwen. Cấu hình so sánh ở v2 vẫn giữ nguyên: Claude (baseline), local (student) và routing (Claude làm fallback, chỉ suy luận).
   - Bẫy: **Qwen2.5-3B-Instruct dùng giấy phép `qwen-research`**: "FOR NON-COMMERCIAL PURPOSES ONLY". Giấy phép này cũng yêu cầu ghi "Built with Qwen"/"Improved using Qwen" nếu dùng output để train model rồi phân phối. Cần kiểm tra thẻ `license` của từng kích cỡ model, không suy ra từ tên dòng model.
   - Chưa kiểm tra: máy có chạy nổi teacher 8B hay 30B-A3B không, và chất lượng tiếng Việt của teacher so với Haiku (đo bằng gold set trước khi sinh nhãn).
2. **Chỉ dùng nhãn người gán**: cần gán tay từ đầu (gold hiện là output Claude). Với ~130 JD thì tập train nhỏ. Đây là phương án tốn công nhất.
3. **Xin phép Anthropic** ("prior authorization"): văn bản không nói kênh xin phép cho người dùng cá nhân. Thời gian chờ và kết quả đều không biết trước.
4. **Dùng API theo Commercial Terms**: không giải quyết được, vì AUP vẫn áp dụng (xem mục 2).

## Chưa biết
- Lịch sử phiên bản AUP: câu về distillation có từ phiên bản nào (chưa mở trang version history).
- Anthropic có kênh xin "prior authorization" cho dự án cá nhân hay không.
