#!/usr/bin/env python3
"""declare.py — log e declaração de uso de IAG (Portaria CNPq 2.664/2026, Art. 9º, I, c).

Uso:
  declare.py log --tool NAME --phase FASE --purpose TEXTO [--note TEXTO]
  declare.py render [--log PATH] [--output PATH]
  declare.py import [--sessions-dir DIR] [--project DIR] [--log PATH] [--dry-run]
  declare.py selftest

O log é ai-log.jsonl no diretório atual (append-only, mesmo formato do
gateway LabAI-Comply: audit.jsonl).
"""
import argparse
import datetime
import json
import sys
import unicodedata
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


def _norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower())
                   if unicodedata.category(c) != "Mn")


def infer_phase(prompt: str) -> str:
    """Heurística por keywords sobre o enum PHASES; revisão humana (Gate 3)."""
    t = _norm(prompt)
    if any(w in t for w in ("commit", "github", "ci.yml", "workflow", "repositorio",
                            "skill list", "instal", "demo", "readme")):
        return "submissao"
    if any(w in t for w in ("analise", "dados", "resultados", "estatistic",
                            "grafic", "tabela", "correlac")):
        return "analise de dados"
    if any(w in t for w in ("reda", "escrev", "rascunho", "paragraf", "secao",
                            "revis", "text", "carta", "resum")):
        return "redacao"
    return "concepcao"


def parse_session(path: Path) -> list[dict]:
    """1 entrada por prompt do usuário; ferramenta = modelos que responderam."""
    prompts: list[dict] = []
    pending: list[str] = []  # modelos acumulados desde o prompt anterior
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines:
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("type") != "message":
            continue
        m = o.get("message") or {}
        role = m.get("role")
        if role == "user":
            text = "".join(b.get("text", "") for b in (m.get("content") or [])
                           if isinstance(b, dict) and b.get("type") == "text").strip()
            # system-reminder, conteúdo vazio e prompts do harness (ex. geração
            # de commit message) não são interação de pesquisa
            if text and not text.startswith(("<system-reminder>", "<chat>",
                                             "You are generating a single git commit message")):
                if prompts:
                    prompts[-1]["models"] = pending[:] or prompts[-1]["models"]
                pending.clear()
                prompts.append({"ts": o.get("timestamp"),
                                "text": text, "models": []})
        elif role == "assistant":
            model = m.get("model")
            if model and model not in pending:
                pending.append(model)
    if prompts:
        prompts[-1]["models"] = pending[:] or prompts[-1]["models"]
    sid = path.stem.split("_")[-1][:13]
    return [{"ts": p["ts"], "ferramenta": "omp.sh (" + ", ".join(p["models"]) + ")"
             if p["models"] else "omp.sh (modelo nao registrado)",
             "fase_pesquisa": infer_phase(p["text"]),
             "finalidade": p["text"].replace("\n", " ")[:200],
             "verificacao": "humana; importado do historico de sessao omp — "
                            "a revisar pelo pesquisador",
             "fonte": sid}
            for p in prompts]


def import_sessions(sessions_dir: Path, project: Path | None,
                    log_path: Path, dry_run: bool) -> int:
    if not sessions_dir.is_dir():
        print(f"diretorio de sessoes nao encontrado: {sessions_dir}", file=sys.stderr)
        return 1
    existing = {e.get("fonte") for e in read_entries(log_path)}
    existing.discard(None)
    existing.discard("")
    imported = skipped = 0
    for f in sorted(sessions_dir.glob("*/*.jsonl")):
        sid = f.stem.split("_")[-1][:13]
        if sid in existing:
            skipped += 1
            continue
        if project and not _session_in_project(f, project):
            skipped += 1
            continue
        entries = parse_session(f)
        if not entries:
            skipped += 1
            continue
        if dry_run:
            for e in entries:
                print(f"[dry-run] {e['ts']} | {e['ferramenta']} | "
                      f"{e['fase_pesquisa']} | {e['finalidade'][:80]}")
            imported += len(entries)
            continue
        with log_path.open("a", encoding="utf-8") as out:
            for e in entries:
                out.write(json.dumps(e, ensure_ascii=False) + "\n")
        imported += len(entries)
        print(f"{f.name}: {len(entries)} entrada(s)")
    print(f"import: {imported} entrada(s), {skipped} sessao(oes) pulada(s)"
          + (" (dry-run)" if dry_run else ""))
    return 0


def _session_in_project(f: Path, project: Path) -> bool:
    """Compara o cwd do evento `session` do transcript com o diretório alvo."""
    try:
        target = str(project.resolve())
    except OSError:
        return False
    try:
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    o = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if o.get("type") == "session":
                    return o.get("cwd") == target
    except OSError:
        return False
    return False


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

    pi = sub.add_parser("import", help="importa prompts de sessões do omp para o log")
    default_dir = Path.home() / ".omp/agent/sessions"
    pi.add_argument("--sessions-dir", default=str(default_dir))
    pi.add_argument("--project", default=".", help="filtra sessões deste cwd (default: atual)")
    pi.add_argument("--log", default=str(LOG))
    pi.add_argument("--dry-run", action="store_true")

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
    elif args.cmd == "import":
        rc = import_sessions(Path(args.sessions_dir), Path(args.project),
                             Path(args.log), args.dry_run)
        if rc:
            sys.exit(rc)
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
            Path(LOG).unlink()

            # import: sessão sintética 1 prompt + 2 respostas (modelos distintos)
            cwd = Path.cwd().resolve()
            slug = "-" + str(cwd).replace("/", "-")
            sid_full = "01a1aaaa-1111-2222-3333-444455556666"
            sfile = Path("sdir") / slug / f"2026-01-01T00-00-00Z_{sid_full}.jsonl"
            sfile.parent.mkdir(parents=True, exist_ok=True)
            events = [
                {"type": "session", "id": sid_full, "cwd": str(cwd)},
                {"type": "message", "timestamp": "2026-01-01T00:00:01Z",
                 "message": {"role": "user", "content": [{"type": "text",
                            "text": "Analisar dados do experimento"}]}},
                {"type": "message", "timestamp": "2026-01-01T00:00:02Z",
                 "message": {"role": "assistant", "model": "m1", "content": []}},
                {"type": "message", "timestamp": "2026-01-01T00:00:03Z",
                 "message": {"role": "assistant", "model": "m2", "content": []}},
                {"type": "message", "timestamp": "2026-01-01T00:00:04Z",
                 "message": {"role": "user", "content": [{"type": "text",
                            "text": "<system-reminder>"}]}},
                {"type": "message", "timestamp": "2026-01-01T00:00:05Z",
                 "message": {"role": "assistant", "model": "m1", "content": []}},
            ]
            sfile.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
            entries = parse_session(sfile)
            assert len(entries) == 1, "system-reminder nao deve virar entrada"
            assert entries[0]["ferramenta"] == "omp.sh (m1, m2)"
            assert entries[0]["fase_pesquisa"] == "analise de dados"
            assert entries[0]["finalidade"] == "Analisar dados do experimento"

            # prompt do harness (commit) é ignorado; finalidade truncada em 1 linha
            long_prompt = "x" * 300 + "\n" + "y" * 100
            ev2 = [
                {"type": "message", "timestamp": "t",
                 "message": {"role": "user", "content": [{"type": "text",
                            "text": "You are generating a single git commit message.\n..." }]}},
                {"type": "message", "timestamp": "t",
                 "message": {"role": "user", "content": [{"type": "text",
                            "text": long_prompt}]}},
                {"type": "message", "timestamp": "t",
                 "message": {"role": "assistant", "model": "m1", "content": []}},
            ]
            f2 = sfile.parent / "b.jsonl"
            f2.write_text("\n".join(json.dumps(e) for e in ev2), encoding="utf-8")
            e2 = parse_session(f2)
            assert len(e2) == 1, "prompt de commit nao deve virar entrada"
            assert "\n" not in e2[0]["finalidade"] and len(e2[0]["finalidade"]) == 200

            # import dedup: segunda execução pula a sessão
            sys.argv = ["declare.py", "import", "--sessions-dir", "sdir",
                        "--project", str(cwd)]
            main()
            n1 = len(read_entries(LOG))
            assert n1 == 1, f"esperava 1 entrada, veio {n1}"
            main()
            n2 = len(read_entries(LOG))
            assert n2 == n1, f"re-import deveria pular; {n1} -> {n2}"

            # dry-run não grava
            Path(LOG).write_text("", encoding="utf-8")
            sys.argv = ["declare.py", "import", "--sessions-dir", "sdir",
                        "--project", str(cwd), "--dry-run"]
            main()
            assert read_entries(LOG) == [], "dry-run nao deveria gravar"
        finally:
            os.chdir(old)
    print("selftest ok")


if __name__ == "__main__":
    main()
