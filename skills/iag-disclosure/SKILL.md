---
name: iag-disclosure
description: >
  Conformidade com a Portaria CNPq 2.664/2026 (Política de Integridade na
  Atividade Científica) em tarefas de pesquisa com agentes de IA. Use SEMPRE
  que a sessão tocar pesquisa científica apoiada pelo CNPq: revisão de
  literatura, análise de dados, redação de artigos/projetos/relatórios,
  código de pesquisa, ou quando o usuário mencionar CNPq, Portaria 2664,
  integridade científica, IAG, declaração de uso de IA, Lattes ou parecer.
  Ativa os 4 gates (confidencialidade, log, verificação, declaração) e
  mantém ai-log.jsonl auditável.
metadata:
  author: LabAI-Comply
  portaria: "CNPq nº 2.664, de 6 de março de 2026"
  version: "1.1.0"
license: MIT
compatibility: >-
  Requer python3 (stdlib only) para scripts/declare.py (log e declaração).
  Sem dependências externas.
---

# Portaria CNPq 2.664/2026 em agentes de IA

Pesquisa apoiada pelo CNPq + IAG: usar IA é permitido; o que a norma regula é
**declaração, responsabilidade humana e confidencialidade** (Art. 9º). Sua
atuação como agente não é neutra: cada interação é uso de IAG e cai no
Art. 9º, I, c. Este fluxo torna a conformidade subproduto do trabalho, não
etapa extra.

Norma completa: `references/portaria.md` (leia só os trechos citados abaixo).

## Os 4 gates (sempre, nesta ordem)

### Gate 1 — Confidencialidade (Art. 9º, I, e; Art. 7º, III)

Antes de processar QUALQUER texto de projeto, proposta ou parecer:

- Recuse processar projeto/proposta de TERCEIROS (não publicado, não seu) para
  elaboração de parecer científico. Isso é vedado pela norma. Ofereça
  alternativa: o próprio autor submeter o texto ao fluxo desta skill.
- **Você é consultor ad hoc / membro de Comitê?** O parecer é redigido POR VOCÊ
  — use a IA apenas para: verificar citações do manuscrito, checar a clareza do
  SEU próprio rascunho, estruturar tópicos que VOCÊ já escreveu. Nunca cole o
  manuscrito avaliado em IAG nem envie a subagentes; registre no log com
  `fase_pesquisa: submissao` e `finalidade: apoio a parecer — sem conteúdo do
  manuscrito`. Declare impedimentos do Art. 7º, V (parentesco até 3º grau,
  vínculo institucional/profissional/colaborativo, orientação anterior) ANTES
  de qualquer análise — se existirem, a rota é recusar a avaliação, não
  "avaliar com cuidado".
- Texto do PRÓPRIO usuário ainda não publicado: processe, mas anime-o a
  anonimizar antes de enviar a serviços cloud. Nunca inclua em prompts:
  dados de participantes, dados brutos não publicados, trechos de proposta de
  colega. Se o usuário colar algo assim, avise e prossiga só com versão
  anonimizada.

### Gate 2 — Log (Art. 9º, I, c)

Toda interação de IAG entra em `ai-log.jsonl` no diretório de trabalho do
projeto, via script abaixo. Formato alinhado ao gateway LabAI-Comply
(`audit.jsonl`) e ao vocabulário de `defaults/main.yml`
(`fase_pesquisa`, `finalidade`):

```json
{"ts":"2026-10-19T11:00:00Z","ferramenta":"omp.sh (glm-5.3-flash)","fase_pesquisa":"concepcao","finalidade":"estruturar roteiro de entrevista","verificacao":"humana; revisado e aprovado pelo pesquisador"}
```

Campos: `ts` ISO-8601, `ferramenta` + versão, `fase_pesquisa` (concepção,
redação, análise de dados, submissão), `finalidade`, `verificacao` (o que o
humano conferiu). **Append-only** — nunca edite linha antiga; erro novo = linha
nova. Rodar `declare.py log` em cada tarefa parece burocracia; é o que
transforma a declaração final em relatório gerado em vez de reconstrução de
memória meses depois.

**Backfill de sessões antigas (omp):** sem log contemporâneo, `import`
reconstrói entradas dos transcripts do omp (`~/.omp/agent/sessions/`), 1
entrada por prompt do usuário, com `ferramenta` e `ts` extraídos do
transcript, `fase_pesquisa` inferida por keywords e `verificacao` marcada
"a revisar". É reconstrução com evidência de máquina — revise as fases
classificadas antes do `render`:

```sh
python3 declare.py import --dry-run          # prévia, sem gravar
python3 declare.py import                    # importa sessões do projeto atual
python3 declare.py import --project ~/outro-projeto
```

Idempotente: sessões já importadas (campo `fonte`) são puladas.

### Gate 3 — Verificação (Art. 9º, II, h/i; Art. 33, I)

Referência, dado numérico ou fato que VOCÊ produzir nasce `unverified`.
Emita assim: `Fonte: [UNVERIFIED] Autor et al. 2021, DOI a conferir`. Só o
pesquisador remove a marca após conferir a fonte primária (DOI no
CrossRef/PubMed, dataset original). Nunca remova a marca você mesmo — fabricar
citação é infração gravíssima (Art. 33, I), e a marca é o que permite ao
pesquisador separar o que ele validou do que você propôs.

### Gate 4 — Declaração (Art. 9º, I, c)

Na submissão (artigo, relatório, projeto):

1. `python3 declare.py render` — gera a declaração a partir do log.
2. Insira a saída na seção metodológica / expõe eletrônica.
3. Sem log (nenhum uso de IAG): `render` emite a declaração negativa.
4. Rode o checklist de submissão ao final desta skill e entregue-o junto.

## Workflow omp

1. **Triagem/estrutura** — subagentes (scout) para mapear literatura e
   estrutura. Output entra no Gate 3 (tudo `unverified` até humano conferir).
2. **Rascunho** — agente redige APENAS a partir de texto/fonte fornecida pelo
   pesquisador; não invente trechos sem fonte. Marque `[UNVERIFIED]` onde a
   fonte não cobre.
3. **Código de análise** — agente escreve/depura; o pesquisador executa e
   valida resultados (ele responde por eles: Art. 9º, I, f).
4. **Fechamento** — `declare.py render` + checklist; pesquisador assina.

Nunca envie texto de projeto alheio a subagentes (Gate 1 aplica-se a eles
também).

## Checklist de submissão (Art. 9º, II)

- [ ] Declaração de uso de IAG presente (ou negativa), com ferramenta + finalidade
- [ ] `ai-log.jsonl` completo; nenhuma interação fora dele
- [ ] Nenhuma citação `unverified` restante
- [ ] Autofiliação citada (Art. 9º, II, g); sem publicação duplicada/fragmentada (II, f, u)
- [ ] Versões anteriores (preprint, anais, apresentação) declaradas na submissão (Art. 9º, II, e/u)
- [ ] Periódico/evento não predatório verificado (Art. 9º, II, v; DOAJ, Critério Qualis)
- [ ] Referências só com relevância real (Art. 9º, II, k)
- [ ] Dados/código depositados em repositório confiável, se possível (Art. 9º, I, g)
- [ ] Autoria restrita a contribuição efetiva; IAG não é autoria (Art. 9º, II, p/q)

## Composição com outras skills (Art. 9º, II)

Esta skill cobre o ciclo CNPq mínimo. Para as lacunas que ela NÃO cobre,
compose (não duplique):

- Verificação de citações em escala (CrossRef/OpenAlex, triagem de retração):
  `rseng-citation-hygiene` — nossa marca `[UNVERIFIED]` é o handshake: itens
  marcados entram, itens conferidos saem.
- Declaração para periódico estrangeiro (política do venue, CRediT, COI,
  data availability): `submission-disclosures` ou `reproducibility-statement`
  — gere primeiro a declaração CNPq com `declare.py render`.
- Triagem de periódicos predatórios como ferramenta dedicada: lacuna de
  mercado (seção 5 da nota de pesquisa); hoje o checklist cobre com
  verificação manual.

## Declaração de saída (template)

ALWAYS use this exact template (render gera a partir do log):

```
DECLARAÇÃO DE USO DE INTELIGÊNCIA ARTIFICIAL GENERATIVA
(Portaria CNPq nº 2.664/2026, Art. 9º, I, "c")

Os autores declaram o uso das seguintes ferramentas de IAG:
- <ferramenta> — fase: <fase_pesquisa> — finalidade: <finalidade>

O conteúdo gerado foi revisado e validado pelos autores, que assumem
integral responsabilidade pelo texto final, incluindo exatidão de citações,
originalidade e integridade científica (Art. 9º, I, "d" e "f").
```

Sem uso de IAG:

```
DECLARAÇÃO DE USO DE INTELIGÊNCIA ARTIFICIAL GENERATIVA
(Portaria CNPq nº 2.664/2026, Art. 9º, I, "c")

Os autores declaram que NENHUMA ferramenta de inteligência artificial
generativa foi empregada na elaboração deste trabalho.
```

## Manutenção

Log corrompido ou linha inválida: `log` recusa a linha e reporta; não
"conserte" apagando — registre correção como nova linha com
`finalidade: correcao de log`.

## Auto-avaliação da skill

Validar após editar: `skills-ref validate <caminho-da-skill>`
(https://github.com/agentskills/agentskills). CI roda esse gate (job
`skill-spec-validate` em `.github/workflows/ci.yml`).
