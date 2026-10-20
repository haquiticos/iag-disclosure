# iag-disclosure

Skill ([Agent Skills](https://agentskills.io)) de conformidade com a **Portaria CNPq nº 2.664/2026** (Política de Integridade na Atividade Científica) em tarefas de pesquisa com agentes de IA: log auditável de uso de IAG (`ai-log.jsonl`), marcação de conteúdo não verificado e geração da declaração de uso de IAG exigida pelo Art. 9º, I, "c".

## Instalação

```sh
npx skills add haquiticos/iag-disclosure --skill iag-disclosure
```

Ou copie o diretório `skills/iag-disclosure/` para o diretório de skills do seu agente (ex.: `~/.agents/skills/`).

## Estrutura

```
skills/iag-disclosure/
├── SKILL.md            # fluxo: 4 gates (confidencialidade, log, verificação, declaração)
├── references/
│   └── portaria.md     # texto integral da Portaria (fonte: DOU)
└── scripts/
    └── declare.py      # log e declaração (python3, stdlib only)
```

`docs/` guarda a nota de pesquisa e conversas de referência que originaram a skill — não faz parte do pacote da skill.

## Uso

A skill ativa automaticamente quando a sessão envolve pesquisa científica apoiada pelo CNPq com IAG. Manualmente:

```sh
# registrar interação de IAG
python3 skills/iag-disclosure/scripts/declare.py log \
  --tool "omp.sh (glm-5.3-flash)" --phase redacao \
  --purpose "revisao linguistica"

# gerar declaração a partir do log
python3 skills/iag-disclosure/scripts/declare.py render
```

## Verificação

```sh
python3 skills/iag-disclosure/scripts/declare.py selftest
agentskills validate skills/iag-disclosure   # pip install skills-ref
```

CI roda ambos a cada push/PR (`.github/workflows/ci.yml`).

## Licença

MIT
