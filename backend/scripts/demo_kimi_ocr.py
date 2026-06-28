"""Demo: Verify Kimi Code vision/OCR capability.

Usage:
    cd backend
    KIMI_CODE_API_KEY=sk-xxx .venv/bin/python scripts/demo_kimi_ocr.py [image_path]

If image_path is omitted, a synthetic lab report image is generated in /tmp.
The demo first runs a plain text chat to verify the key, then sends the image.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Make sure project root is on path so app.* imports work.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import httpx  # noqa: E402

from app.ai.kimi_ocr_provider import KimiOCRProvider  # noqa: E402

REPORT_TEXT = """健康检查报告
姓名：张三
日期：2026-06-21

收缩压：145 mmHg
舒张压：92 mmHg
空腹血糖：6.8 mmol/L
总胆固醇：5.2 mmol/L
甘油三酯：1.8 mmol/L
高密度脂蛋白：1.1 mmol/L
低密度脂蛋白：3.4 mmol/L"""


def create_synthetic_report_image(path: str) -> str:
    """Generate a simple lab report image for demo purposes."""
    width, height = 600, 500
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)

    font_paths = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    font = None
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, 22)
                break
            except Exception:
                pass
    if font is None:
        font = ImageFont.load_default()

    draw.rectangle([10, 10, width - 10, height - 10], outline="#2563EB", width=3)

    y = 30
    for line in REPORT_TEXT.splitlines():
        draw.text((30, y), line, fill="black", font=font)
        y += 36

    img.save(path, "JPEG")
    return path


async def test_text_chat(provider: KimiOCRProvider) -> bool:
    """Run a minimal text-only chat to verify the API key works."""
    url = f"{provider.base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
        "User-Agent": "KimiCLI/1.6",
    }
    payload = {
        "model": provider.model,
        "messages": [{"role": "user", "content": "请回复'测试成功'"}],
        "max_tokens": 50,
        "temperature": 1.0,
    }
    try:
        async with httpx.AsyncClient(timeout=provider.timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            print(f"Full text response:\n{json.dumps(data, ensure_ascii=False, indent=2)[:800]}\n")
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"✅ Text chat OK. Reply: {content.strip()!r}")
            return True
    except httpx.HTTPStatusError as exc:
        print(f"❌ Text chat failed: HTTP {exc.response.status_code}")
        try:
            print(exc.response.json())
        except Exception:
            print(exc.response.text)
        return False
    except Exception as exc:
        print(f"❌ Text chat failed: {exc}")
        return False


async def main() -> int:
    provider = KimiOCRProvider()
    if not provider.api_key:
        print(
            "ERROR: KIMI_CODE_API_KEY (or MOONSHOT_API_KEY) is not configured.\n"
            "Set it in backend/.env or as an environment variable."
        )
        return 1
    print(f"Endpoint: {provider.base_url}")
    print(f"Model: {provider.model}")
    print(f"API Key: {provider.api_key[:12]}...\n")

    print("--- Step 1: Verify text chat ---")
    text_ok = await test_text_chat(provider)
    if not text_ok:
        print("\nPlease check that your API key is valid and has access to the model.")
        return 1

    image_path = sys.argv[1] if len(sys.argv) > 1 else None
    if image_path is None:
        fd, image_path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)
        create_synthetic_report_image(image_path)
        print(f"\nGenerated demo image: {image_path}")
    else:
        print(f"\nUsing image: {image_path}")

    print("--- Step 2: Image OCR ---")
    try:
        indicators = await provider.extract_indicators(image_path)
    except httpx.HTTPStatusError as exc:
        print(f"❌ Image OCR failed: HTTP {exc.response.status_code}")
        try:
            body = exc.response.json()
            print(json.dumps(body, ensure_ascii=False, indent=2))
        except Exception:
            print(exc.response.text)
        print("\nIf the error says the model does not support image input, "
              "then kimi-code (kimi-for-coding) does NOT support vision.")
        return 1
    except Exception as exc:
        print(f"❌ Image OCR failed: {exc}")
        return 1

    print(f"✅ Image OCR succeeded. Extracted {len(indicators)} indicators:")
    for item in indicators:
        print(
            f"  - {item['name']} ({item['key']}): {item['value']} {item['unit']}"
            f" | raw: {item.get('raw_text', '')}"
        )

    if not indicators:
        print("No indicators extracted. The image may be too simple or the model "
              "returned an empty JSON.")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
