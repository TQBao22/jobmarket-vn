"""Trích kỹ năng bằng model mở chạy local qua Ollama (v2, ADR 0003). Cùng prompt, schema, cache, bảng DB với Claude.

Chạy (đo trên gold): python -m jobmarket.extract.local --model qwen3:1.7b --gold dev
"""
import argparse
import json
import urllib.request
from pathlib import Path
from typing import Callable

from jobmarket import db, gold
from jobmarket.extract import llm

OLLAMA = "http://localhost:11434/api/chat"
NUM_CTX = 8192  # 1 JD + prompt ≈ 2–4K token; KV cache lớn hơn không vừa 4 GB VRAM
MAX_OUTPUT = 1024  # trung vị ~130 token/JD; model nhỏ đôi khi lặp vô hạn (đo: 27K token ở 1 JD)
# think=true: phần suy nghĩ tính vào num_predict nên cần ngân sách lớn hơn, vẫn có trần để chặn lặp vô hạn
THINK_MAX_OUTPUT = 4096
THINK_NUM_CTX = 12288  # JD ≤ ~4K token + 4K output + prompt


def _post(body: dict) -> dict:
    req = urllib.request.Request(OLLAMA, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        return json.load(r)


def ollama_runner(model: str, post: Callable[[dict], dict] = _post, think: bool = False,
                  num_predict: int | None = None) -> Callable[[str, str], str]:
    """Runner cùng giao diện với `llm.claude_runner`: trả chuỗi JSON dạng output `claude -p` để dùng lại `parse_output`."""

    def run(system: str, user_input: str) -> str:
        body = {
            "model": model, "stream": False, "think": think, "format": llm.SCHEMA,
            "options": {"temperature": 0, "num_ctx": THINK_NUM_CTX if think else NUM_CTX,
                        "num_predict": num_predict or (THINK_MAX_OUTPUT if think else MAX_OUTPUT)},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user_input}],
        }
        try:
            r = post(body)
            structured = json.loads(r["message"]["content"])
        except (OSError, KeyError, json.JSONDecodeError) as e:
            return json.dumps({"is_error": True, "result": f"ollama: {e}"})
        return json.dumps({
            "structured_output": structured, "total_cost_usd": 0.0,
            "usage": {"input_tokens": r.get("prompt_eval_count"), "output_tokens": r.get("eval_count")},
        })

    return run


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True)
    ap.add_argument("--prompt", default=llm.PROMPT_VERSION)
    ap.add_argument("--gold", choices=["dev", "test", "all"], help="chỉ trích JD trong nửa gold này (gold.dev_test)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--think", action="store_true", help="bật chế độ suy nghĩ; kết quả lưu dưới model <model>-think")
    ap.add_argument("--num-predict", type=int, help="trần token output (gồm phần suy nghĩ), mặc định theo --think")
    args = ap.parse_args()
    system = (llm.PROMPTS / f"{args.prompt}.txt").read_text(encoding="utf-8")
    urls = list(gold.load())
    only = {"all": set(urls), **dict(zip(["dev", "test"], gold.dev_test(urls)))}.get(args.gold)
    store_model = f"{args.model}-think" if args.think else args.model  # tách cache/eval khỏi bản không suy nghĩ
    runner = ollama_runner(args.model, think=args.think, num_predict=args.num_predict)
    print(dict(llm.extract(db.connect(Path("data/jobs.db")), store_model, args.prompt, system, args.limit,
                           runner=runner, batch=1, only=only)))
