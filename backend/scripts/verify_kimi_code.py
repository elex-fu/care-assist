"""Verify Kimi Code provider connectivity.

Run from backend directory:
    source .venv/bin/activate && python scripts/verify_kimi_code.py
"""

import asyncio
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ai.kimi_code_provider import KimiCodeProvider
from app.config import settings


async def main():
    print("=" * 60)
    print("Kimi Code Provider Verification")
    print("=" * 60)
    print(f"Base URL: {settings.KIMI_CODE_BASE_URL}")
    print(f"Model: {settings.KIMI_CODE_MODEL}")
    print(f"API Key configured: {'Yes' if settings.KIMI_CODE_API_KEY else 'No'}")
    print()

    if not settings.KIMI_CODE_API_KEY:
        print("ERROR: KIMI_CODE_API_KEY is not set in backend/.env")
        sys.exit(1)

    provider = KimiCodeProvider()
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "你好，请用一句话介绍自己。"},
    ]

    try:
        print("Sending non-streaming request...")
        reply = await provider.chat(messages, stream=False, max_tokens=128)
        print("\nNon-streaming reply:")
        print(reply)
        print()

        print("Sending streaming request...")
        chunks = []
        async for chunk in await provider.chat(messages, stream=True, max_tokens=128):
            chunks.append(chunk)
            print(chunk, end="", flush=True)
        print("\n")

        full_reply = "".join(chunks)
        print("Streaming reply assembled:")
        print(full_reply)
        print()

        print("Testing family summary generation...")
        summary = await provider.generate_summary({
            "member_cards": [
                {"name": "张三", "type": "adult", "latest_status": "normal", "abnormal_count": 0},
                {"name": "李四", "type": "elderly", "latest_status": "high", "abnormal_count": 1},
            ]
        })
        print("Summary:")
        print(summary)
        print()

        print("=" * 60)
        print("SUCCESS: Kimi Code provider is working correctly.")
        print("=" * 60)
    except Exception as exc:
        print(f"ERROR: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
