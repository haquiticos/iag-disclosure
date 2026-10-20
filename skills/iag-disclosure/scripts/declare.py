#!/usr/bin/env python3
"""declare.py — log e declaração de uso de IAG (Portaria CNPq 2.664/2026, Art. 9º, I, c).

Uso:
  declare.py log --tool NAME --phase FASE --purpose TEXTO [--note TEXTO]
  declare.py render [--log PATH] [--output PATH]
  declare.py selftest

O log é ai-log.jsonl no diretório atual (append-only, mesmo formato do
gateway LabAI-Comply: audit.jsonl).
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

LOG = Path("ai-log.jsonl")
PHASES = ("concepcao", "redacao", "analise de dados", "submissao", "correcao de log")


def log_entry(tool: str, phase: str, purpose: str, note: str | None) -> dict:
    return {
        "ts": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "ferramenta": tool,
        "fase_pesquisa": phase,
        "finalidade": purpose,
        "verificacao": note or "humana; revisado e aprovado pelo pesquisador",
    }


def read_entries(path: Path) -> list[dict]:
    entries, bad = [], []
    if not path.exists():
        return entries
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            if not {"ts", "ferramenta", "fase_pesquisa", "finalidade", "verificacao"} <= set(obj):
                raise ValueError("faltando campos obrigatorios")
            entries.append(obj)
        except (json.JSONDecodeError, ValueError) as exc:
            bad.append((n, str(exc)))
    if bad:
        # Append-only: linha ruim não é apagada nem "consertada"; reporta e trava.
        for n, err in bad:
            print(f"ai-log.jsonl:{n}: linha invalida ({err})", file=sys.stderr)
        sys.exit(1)
    return entries


def render(entries: list[dict]) -> str:
    if not entries:
        return (
            "DECLARAÇÃO DE USO DE INTELIGÊNCIA ARTIFICIAL GENERATIVA\n"
            "(Portaria CNPq nº 2.664/2026, Art. 9º, I, \"c\")\n\n"
            "Os autores declaram que NENHUMA ferramenta de inteligência artificial\n"
            "generativa foi empregada na elaboração deste trabalho.\n"
        )
    seen: dict[tuple, dict] = {}
    for e in entries:
        key = (e["ferramenta"], e["fase_pesquisa"], e["finalidade"])
        if key not in seen:
            seen[key] = e  # primeira ocorrência; log é append-only
    lines = [
        "DECLARAÇÃO DE USO DE INTELIGÊNCIA ARTIFICIAL GENERATIVA",
        "(Portaria CNPq nº 2.664/2026, Art. 9º, I, \"c\")",
        "",
        "Os autores declaram o uso das seguintes ferramentas de IAG:",
    ]
    for tool, phase, purpose in seen:
        lines.append(f"- {tool} — fase: {phase} — finalidade: {purpose}")
    lines += [
        "",
        "O conteúdo gerado foi revisado e validado pelos autores, que assumem",
        "integral responsabilidade pelo texto final, incluindo exatidão de citações,",
        "originalidade e integridade científica (Art. 9º, I, \"d\" e \"f\").",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("log", help="registra interação de IAG")
    pl.add_argument("--tool", required=True, help="ferramenta + versão")
    pl.add_argument("--phase", required=True, choices=PHASES)
    pl.add_argument("--purpose", required=True)
    pl.add_argument("--note", help="verificação humana realizada")

    pr = sub.add_parser("render", help="gera declaração a partir do log")
    pr.add_argument("--log", default=str(LOG))
    pr.add_argument("--output", help="default: stdout")

    sub.add_parser("selftest", help="roda verificação interna")

    args = p.parse_args()
    if args.cmd == "log":
        entry = log_entry(args.tool, args.phase, args.purpose, args.note)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(f"registrado: {LOG} ({entry['ferramenta']} / {entry['fase_pesquisa']})")
    elif args.cmd == "render":
        text = render(read_entries(Path(args.log)))
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
    else:
        selftest()


def selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        old = Path.cwd()
        import os

        os.chdir(tmp)
        try:
            # log cria JSONL com campos obrigatórios
            sys.argv = ["declare.py", "log", "--tool", "omp.sh (glm-5.3-flash)",
                        "--phase", "redacao", "--purpose", "revisao linguistica"]
            main()
            entries = read_entries(LOG)
            assert len(entries) == 1 and entries[0]["ferramenta"].startswith("omp.sh")

            # render com log: declaração positiva, sem duplicar entradas repetidas
            sys.argv = ["declare.py", "log", "--tool", "omp.sh (glm-5.3-flash)",
                        "--phase", "redacao", "--purpose", "revisao linguistica"]
            main()
            text = render(read_entries(LOG))
            assert text.count("omp.sh (glm-5.3-flash)") == 1, "dedup falhou"
            assert "fase: redacao" in text and "revisao linguistica" in text

            # render sem log: declaração negativa
            Path(LOG).unlink()
            assert "NENHUMA" in render([])

            # linha corrompida: recusa e exit != 0 (append-only preservado)
            Path(LOG).write_text("{not json\n", encoding="utf-8")
            try:
                read_entries(LOG)
                raise AssertionError("linha corrompida deveria travar")
            except SystemExit:
                pass
        finally:
            os.chdir(old)
    print("selftest ok")


if __name__ == "__main__":
    main()
