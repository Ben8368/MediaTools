"""
test_apikey.py — 测试 TEC_CHI_API Key 可用性
"""
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("TEC_CHI_API_KEY", "").strip()
base_url = os.getenv("OPENAI_BASE_URL", "https://ai-gateway.tec-do.cn/claw-agents/text/v1").strip()

print("TEC_CHI_API_KEY:", api_key[:12] + "..." if len(api_key) > 12 else api_key or "(未设置)")
print("OPENAI_BASE_URL:", base_url)
print()

if not api_key:
    print("请在 .env 文件中设置 TEC_CHI_API_KEY")
    exit(1)

print("正在连接 TEC AI Gateway...")
try:
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url)
    print("连接成功\n")
except Exception as e:
    print("连接失败:", e)
    exit(1)

models_to_test = ["qwen3.6-plus", "gpt-5.4"]

print("测试各模型（发送简单 ping）：")
for model_name in models_to_test:
    try:
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Reply with one word: OK"}],
            max_tokens=10,
        )
        print("  OK %-20s -> %s" % (model_name, resp.choices[0].message.content.strip()[:30]))
    except Exception as e:
        err = str(e)[:80]
        print("  FAIL %-20s -> %s" % (model_name, err))