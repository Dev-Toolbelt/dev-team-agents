# Eixo E — Economia de Tokens — 2026-08-12

**Baseline:** `HEAD` = `07e0725`

## Panorama

O delta cresceu arquivos que já são dívidas de token registradas, mas **não** criou uma dívida nova e
original com evidência que passe pelo Protocolo Anti-Duplicação. Os maiores crescimentos incidem em
fingerprints já abertos:

| Arquivo | Antes | HEAD | Fingerprint (já registrado) |
|---|---|---|---|
| `CLAUDE.md` | 549 | **586** | `token-claude-md-426-lines…` (🔴 reaberto) |
| `scripts/install.sh` | 947 | **1085** | `token-install-sh-503-lines…` (🔴 aberto) |
| `CHANGELOG.md` | 441 | **959** | `token-changelog-already-growing…` (🔴 aberto) |
| `scripts/hooks/session-start.sh` | 174 | **306** | `flow-session-start-118-lines-monolithic` (🔴 aberto) |
| `skills/shared/interaction-patterns/SKILL.md` | 209 | 209 | `token-interaction-patterns-209-lines…` (🔴 aberto) |

Reapresentar qualquer um destes seria violar a **Porta de estado** do Protocolo Anti-Duplicação
(item já registrado e não implementado = ruído, não descoberta). Cada um foi revalidado como
reproduzindo nas Fases 1/1b.

## Ganho de token detectado no delta (positivo)

Registrado por completude: o delta **melhorou** a economia de tokens em dois pontos, fechando
fingerprints:

- `flow-telemetry-pre-tool-use-02` (🟢): early-exit por substring antes do fork `python3` em toda
  chamada de tool que não seja Task/Bash — corta 2 forks `python3` por chamada na maioria das tools.
- `token-dedup-step-reads-full-…-index-md` já estava ✅; o banco segue com o campo `alvo:` para
  pré-filtro mecânico.

## Achado

**Nenhum achado original neste eixo.** As dívidas de token materiais já estão no banco e foram
revalidadas abertas; o delta não introduziu carregamento eager novo, skill sempre-carregada
convertível, nem leitura de arquivo inteiro onde `grep`/`head` bastaria que não estivesse já coberto.
