# 5. Robustez de Scripts (Hooks, Instalador, Atualizador)

← [Voltar ao índice](index.md)

Esta seção é **inédita** — a passada anterior não tocou em conteúdo de scripts shell. Aqui são levantados defeitos concretos com **linha exata** que afetam estabilidade em condições adversas: rede ruim, falha de extração, instalações concorrentes.

---

## 5.1 Dispatchers de hooks com `set -uo pipefail` faltando o `-e`

`scripts/hooks/pre-tool-use.sh` linha 5:
```bash
set -uo pipefail
```

`scripts/hooks/stop.sh` linha 4:
```bash
set -uo pipefail
```

Ambos os dispatchers **omitem o `-e`** (errexit). Isso significa que erros em comandos individuais (não pipefails) são **silenciosamente ignorados**. O sub-script `01-check-updates.sh` correto usa `set -euo pipefail` (linha 5), o que torna a inconsistência ainda mais visível.

> **Fingerprint:** `auto-hook-dispatchers-missing-errexit`

A justificativa aparente (não documentada) é "o dispatcher deve continuar mesmo se um sub-script falhar", e o código de fato captura `SCRIPT_EXIT` manualmente. Mas o `-e` afeta apenas comandos **fora** do `||`/`if`/`while` — e há comandos assim no dispatcher (`HOOKS_DIR=` em linha 7, `INPUT=$(cat)` em linha 8 do `pre-tool-use.sh`). Se um desses falhar, o dispatcher segue silenciosamente para o `for`.

**Recomendação:** trocar para `set -euo pipefail` e usar `|| true` apenas onde a tolerância a erro é **intencional** (na linha 14 já está, com `|| SCRIPT_EXIT=$?`). Isto torna a tolerância explícita e o resto do script robusto.

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Falhas latentes (env corrompido, `dirname` falhando) viram visíveis em vez de silenciosas |
| **Positivo** | Coerência com o sub-script (que já usa `-euo`) |
| **Negativo** | Risco baixíssimo de regressão — dispatcher é simples, ~20 linhas |

---

## 5.2 `01-check-updates.sh` faz chamadas HTTP **sem timeout**

`scripts/hooks/pre-tool-use/01-check-updates.sh` linha 31:

```bash
HTTP_GET() { curl -fsSL "$1"; }
```

E linha 32 (DL):

```bash
HTTP_DL() { curl -fsSL -o "$1" "$2"; }
```

**Sem `--connect-timeout`. Sem `--max-time`.** Em rede ruim ou DNS travando (caso recorrente em VPN corporativa), o `curl` pode pendurar **indefinidamente**, e como esse hook roda no **PreToolUse** do Claude Code, **toda invocação de tool** fica bloqueada esperando resposta de `api.github.com`.

A defesa atual (`TWENTY_FOUR_HOURS=86400`, linha 12) só protege depois da primeira chamada bem-sucedida. **Na primeira execução**, o usuário pode ficar 60+ segundos esperando.

> **Fingerprint:** `auto-curl-no-timeout-update-check`

**Recomendação:**

```bash
HTTP_GET() { curl -fsSL --connect-timeout 5 --max-time 10 "$1"; }
HTTP_DL()  { curl -fsSL --connect-timeout 5 --max-time 30 -o "$1" "$2"; }
```

Para `wget` (fallback nas linhas 34–35), adicionar `--timeout=10`.

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | UX **drasticamente** melhor em redes ruins ou offline |
| **Positivo** | Reduz risco de Claude Code parecer "travado" para o usuário |
| **Negativo** | Em conexões realmente lentas (3G, GitHub rate-limit retornando 200 em 8s), pode falhar prematuramente — mitigável com `--max-time 30` |

---

## 5.3 `install.sh` não tem rollback se o segundo `mv` falhar

`install.sh` linhas 138–143:

```bash
if [ -d "$INSTALL_DIR" ]; then
    OLD_INSTALL="${INSTALL_DIR}.old.$$"
    mv "$INSTALL_DIR" "$OLD_INSTALL"      # ← passo 1
    mv "$EXTRACTED_ROOT" "$INSTALL_DIR"   # ← passo 2 — se falhar aqui, sem rollback
    rm -rf "$OLD_INSTALL" "$TMP_DIR" || true
fi
```

A intenção (comentário linha 125) é "atomic rename so the running script is never deleted mid-execution". Mas se o **segundo `mv`** falhar (ex.: filesystem cheio, permissão), o usuário fica:
- `$INSTALL_DIR` apagado/movido
- `$EXTRACTED_ROOT` ainda em `$TMP_DIR` (que não foi removido)
- **Instalação corrompida**, sem rollback automático

> **Fingerprint:** `auto-install-no-rollback-on-second-mv-failure`

**Recomendação:** adicionar trap que reverte o primeiro `mv` se o segundo falhar:

```bash
mv "$INSTALL_DIR" "$OLD_INSTALL"
if ! mv "$EXTRACTED_ROOT" "$INSTALL_DIR"; then
    echo "ERROR: failed to install new version. Rolling back..." >&2
    mv "$OLD_INSTALL" "$INSTALL_DIR"
    rm -rf "$TMP_DIR"
    exit 1
fi
rm -rf "$OLD_INSTALL" "$TMP_DIR" || true
```

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Falha de instalação preserva versão anterior funcional |
| **Positivo** | Reduz surface de "instalação parcial" (debug pesadelo) |
| **Negativo** | +6 linhas no script — mas o ROI é alto |

---

## 5.4 `update.sh` baixa e executa instalador sem verificar integridade

(Não consegui ler o `update.sh` na inspeção rápida, mas o `01-check-updates.sh` linhas 67–70 mostra o padrão usado pela rotina de auto-update:)

```bash
TMP_INSTALLER=$(mktemp)
trap 'rm -f "$TMP_INSTALLER"' EXIT
HTTP_DL "$TMP_INSTALLER" "$INSTALL_URL"
bash "$TMP_INSTALLER" latest
```

**Sem checksum, sem assinatura GPG, sem validação prévia.** Um MITM em rede comprometida ou um repositório espelhado modificado pode fazer o usuário rodar **arbitrary code** em `bash`. O `curl -fsSL` valida HTTPS (TLS), mas isso só protege contra MITM passivo, não contra GitHub comprometido ou typo-squatting de URL.

> **Fingerprint:** `auto-update-no-integrity-check`

**Recomendação (em ordem de esforço crescente):**

1. Publicar SHA256 dos releases em `releases/<tag>/checksums.txt` e validar antes de executar.
2. Assinar releases com GPG e validar assinatura no instalador.
3. Cobrar PIN de versão por padrão; auto-update apenas com flag explícita (já existe — `.auto-update`).

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Cadeia de suprimento defendida; auditoria possível |
| **Negativo** | Adicionar checksum: ~10 linhas + workflow de release |
| **Negativo** | GPG: complexidade alta (gerenciamento de chaves), provavelmente desnecessário em escala atual |

---

## 5.5 `01-session-summary.sh` confia em `git log --since` sem fallback se git não existir

`01-session-summary.sh` linha 10:

```bash
TODAY_COMMITS=$(git log --since="${TODAY} 00:00:00" --oneline 2>/dev/null || true)
```

O `2>/dev/null || true` torna o erro silencioso. Se o usuário rodar Claude Code **fora de um repo git** (ex.: pasta de scripts ad-hoc, projeto de exploração), `TODAY_COMMITS` fica vazio e o hook **nunca** dispara o aviso de session-summary, ainda que o usuário tenha feito mudanças.

> **Fingerprint:** `auto-session-summary-no-git-detection`

**Recomendação:** detectar antecipadamente com `git rev-parse --is-inside-work-tree`. Se não estiver em repo, sair com `exit 0` (sem aviso, comportamento aceitável). Se estiver em repo mas sem commits hoje, manter a lógica atual.

```bash
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    exit 0
fi
```

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Hook fica robusto fora de repos git (não vaza erros silenciosos) |
| **Positivo** | Possibilita detectar diferentes condições e ajustar mensagens |
| **Negativo** | Em pastas que **deveriam** estar versionadas mas não estão, perde-se o "lembrete educativo"; mitigável com mensagem explícita ("não é repo git — ignorando session-summary") |

---

## 5.6 `01-check-updates.sh` define `LAST_CHECK_FILE` mesmo quando `mkdir` pode falhar

Linhas 41–42:

```bash
mkdir -p "$USER_DATA_DIR"
date +%s > "$LAST_CHECK_FILE"
```

O `mkdir -p` é tolerante mas **não 100% à prova de erro** (ex.: `USER_DATA_DIR` é arquivo, não diretório; ou parent path read-only). Se `mkdir` falhar, o `date +%s >` quebra e — graças ao `set -euo pipefail` — o script aborta. O hook escapa silenciosamente, mas o **`LAST_CHECK_FILE` nunca é atualizado**, então a próxima execução refaz a checagem (e o ciclo continua).

> **Fingerprint:** `auto-check-updates-mkdir-resilience`

**Recomendação:** capturar falha do `mkdir` e abortar o hook **silenciosamente** (sem `exit 2` que o usuário veria):

```bash
if ! mkdir -p "$USER_DATA_DIR" 2>/dev/null; then
    exit 0  # silently skip update check on bad filesystem
fi
date +%s > "$LAST_CHECK_FILE" 2>/dev/null || exit 0
```

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Hook não derruba o pipeline em filesystems estranhos (containers, ambientes restritos) |
| **Negativo** | Falhas reais de FS ficam invisíveis — risco baixo, é hook auxiliar |

---

## 5.7 Resumo de fingerprints novos

| Fingerprint | Tema |
|-------------|------|
| `auto-hook-dispatchers-missing-errexit` | `pre-tool-use.sh` e `stop.sh` sem `-e` em `set` |
| `auto-curl-no-timeout-update-check` | `curl` sem `--connect-timeout` no hook de checagem de update |
| `auto-install-no-rollback-on-second-mv-failure` | `install.sh` não reverte se segundo `mv` falhar |
| `auto-update-no-integrity-check` | Auto-update baixa e executa instalador sem SHA256/GPG |
| `auto-session-summary-no-git-detection` | Hook de session-summary não detecta ausência de git |
| `auto-check-updates-mkdir-resilience` | `01-check-updates.sh` aborta em filesystem com `mkdir` falhando |
