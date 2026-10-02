#!/usr/bin/env python3
"""Chama o Jev (TypeSafe, System One) pelo OpenRouter.

Uso:
  python3 jev.py pedido.json          # arquivo com {"state": ..., "questions": {...}}
  cat pedido.json | python3 jev.py -  # ou pela entrada padrão

Imprime um JSON com as respostas, o tempo (ms), o custo (US$) e os tokens.
A chave vem SÓ da variável de ambiente OPENROUTER_API_KEY ou do arquivo
~/.config/openrouter/key (permissão 600). Ela nunca é impressa nem salva.
"""
import json
import os
import stat
import sys
import time
import urllib.error
import urllib.request

ENDPOINT = "https://openrouter.ai/api/alpha/decisions"
DEFAULT_MODEL = "typesafe/jev-1.13"
KEY_FILE = os.path.expanduser("~/.config/openrouter/key")


def load_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if key:
        return key
    if os.path.isfile(KEY_FILE):
        mode = stat.S_IMODE(os.stat(KEY_FILE).st_mode)
        if mode & 0o077:
            sys.exit(f"erro: {KEY_FILE} precisa de permissão 600 (chmod 600 {KEY_FILE})")
        with open(KEY_FILE, encoding="utf-8") as fh:
            key = fh.read().strip()
        if key:
            return key
    sys.exit("erro: chave do OpenRouter não encontrada (defina OPENROUTER_API_KEY no ambiente)")


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    raw = sys.stdin.read() if sys.argv[1] == "-" else open(sys.argv[1], encoding="utf-8").read()
    body = json.loads(raw)
    body.setdefault("model", DEFAULT_MODEL)
    for field in ("state", "questions"):
        if field not in body:
            sys.exit(f"erro: o pedido precisa de '{field}'")

    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {load_key()}", "Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            status = resp.status
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        detail = err.read().decode("utf-8", "replace")
        print(json.dumps({"ok": False, "status": err.code, "elapsed_ms": elapsed_ms, "error": detail}, ensure_ascii=False, indent=2))
        sys.exit(1)
    except urllib.error.URLError as err:
        print(json.dumps({"ok": False, "error": str(err.reason)}, ensure_ascii=False, indent=2))
        sys.exit(1)
    elapsed_ms = round((time.perf_counter() - started) * 1000)

    usage = payload.get("usage") or {}
    print(
        json.dumps(
            {
                "ok": True,
                "status": status,
                "model": payload.get("model"),
                "elapsed_ms": elapsed_ms,
                "cost_usd": usage.get("cost"),
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
                "answers": payload.get("answers"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
