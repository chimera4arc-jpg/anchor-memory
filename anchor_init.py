"""Interactive setup for Anchor.

Walks the user through picking a provider, model, and (optional) spend caps,
writes ~/.anchor/config.yaml. Re-run any time to change configuration.

Usage:
    python -m anchor_init
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".anchor"
CONFIG_PATH = CONFIG_DIR / "config.yaml"


PROVIDERS = [
    ("anthropic", "Claude (Anthropic)", "claude-haiku-4-5-20251001",
     "ANTHROPIC_API_KEY"),
    ("openai", "ChatGPT / GPT-5 (OpenAI)", "gpt-5-nano",
     "OPENAI_API_KEY"),
    ("google", "Gemini (Google)", "gemini-2.5-flash",
     "GOOGLE_API_KEY"),
    ("openai-compat-deepseek", "DeepSeek (OpenAI-compatible)", "deepseek-chat",
     "DEEPSEEK_API_KEY"),
    ("openai-compat-glm", "GLM / Zhipu (OpenAI-compatible)", "glm-4.5-flash",
     "ZHIPU_API_KEY"),
    ("openai-compat-ollama", "Local Ollama (no API key needed)", "qwen2.5:7b",
     None),
    ("skip", "Skip — configure later (LLM features disabled)", "", None),
]


COMPAT_ENDPOINTS = {
    "openai-compat-deepseek": "https://api.deepseek.com/v1",
    "openai-compat-glm": "https://open.bigmodel.cn/api/paas/v4",
    "openai-compat-ollama": "http://localhost:11434/v1",
}


def _prompt(msg: str, default: str = "") -> str:
    sfx = f" [{default}]" if default else ""
    val = input(f"{msg}{sfx}: ").strip()
    return val or default


def _yesno(msg: str, default: bool = True) -> bool:
    d = "Y/n" if default else "y/N"
    val = input(f"{msg} [{d}]: ").strip().lower()
    if not val:
        return default
    return val.startswith("y")


def main():
    print("=" * 60)
    print("Anchor Memory — Setup")
    print("=" * 60)
    print()
    print("Anchor's optional features (dream pass, concept linking,")
    print("multi-intent search) call an LLM in the background.")
    print()
    print("Core features (store, search, hebbian, emotion) work WITHOUT")
    print("an LLM — you can skip this and configure later.")
    print()

    print("What LLM provider do you use?")
    for i, (key, label, model, env_key) in enumerate(PROVIDERS, 1):
        rec = " (recommended cheapest)" if model and "nano" in model or "flash" in model and "haiku" not in model else ""
        env_note = f"  [env: {env_key}]" if env_key else ""
        print(f"  {i}) {label}{env_note}")
    print()

    choice = _prompt("Choose 1-7", "1")
    try:
        idx = int(choice) - 1
        key, label, default_model, env_key = PROVIDERS[idx]
    except (ValueError, IndexError):
        print(f"Invalid choice. Aborting.")
        sys.exit(1)

    if key == "skip":
        print("\nSkipping LLM setup. Anchor will work for core operations only.")
        print("Re-run `python -m anchor_init` any time to configure.")
        return

    # Build config dict
    cfg = {"llm": {}, "safety": {}}

    if key.startswith("openai-compat"):
        cfg["llm"]["provider"] = "openai-compat"
        cfg["llm"]["endpoint"] = COMPAT_ENDPOINTS[key]
    else:
        cfg["llm"]["provider"] = key

    model = _prompt(f"Model", default_model)
    cfg["llm"]["model"] = model

    if env_key:
        existing = os.getenv(env_key)
        if existing:
            print(f"\n{env_key} is set in your environment — Anchor will read it.")
            use_env = _yesno(f"Use env var (recommended, key stays out of config file)", True)
            if not use_env:
                api_key = _prompt(f"Paste your {env_key}")
                cfg["llm"]["api_key"] = api_key
        else:
            print(f"\n{env_key} is NOT in your environment.")
            api_key = _prompt(f"Paste your {env_key} (or leave blank to set it in env later)")
            if api_key:
                cfg["llm"]["api_key"] = api_key

    print()
    print("─" * 60)
    print("Spend caps (recommended)")
    print("─" * 60)
    print("Anchor tracks LLM spend in ~/.anchor/spend.jsonl and can refuse")
    print("to run if today's spend exceeds a cap you set. Useful safety net.")
    print()
    set_caps = _yesno("Set a daily spend cap?", True)
    if set_caps:
        cap = _prompt("Daily cap in USD", "5.00")
        try:
            cfg["safety"]["max_cost_per_day_usd"] = float(cap)
        except ValueError:
            print(f"Invalid cap '{cap}', skipping.")
        per_pass = _prompt("Warn before any single dream pass over (USD)", "0.10")
        try:
            cfg["safety"]["warn_above_per_pass_usd"] = float(per_pass)
        except ValueError:
            pass

    # Write config
    CONFIG_DIR.mkdir(exist_ok=True)
    try:
        import yaml
    except ImportError:
        print("\npyyaml not installed. Run: pip install pyyaml")
        sys.exit(1)

    CONFIG_PATH.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    try:
        CONFIG_PATH.chmod(0o600)
    except Exception:
        pass

    print()
    print("=" * 60)
    print(f"Configuration written: {CONFIG_PATH}")
    print("=" * 60)
    print()
    print(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    print("You're set. Try it:")
    print("  python -c 'from anchor_llm import get_default_llm; print(get_default_llm().call(\"\", \"hi\", max_tokens=10).text)'")


if __name__ == "__main__":
    main()
