# 1. Referências e Consistência (Comandos × Documentação × Instalador)

← [Voltar ao índice](index.md)

Esta seção foca em **inconsistências sutis** entre o que o `CLAUDE.md` documenta, o que o `install.sh` realmente faz e o que cada comando em `commands/` declara. Não são bugs — são pontos onde código e documentação **divergem silenciosamente**.

---

## 1.1 `install.sh` strippa mais arquivos do que `CLAUDE.md` documenta

O `CLAUDE.md` (linhas 178–179) declara:

> **Package exclusions:** `CLAUDE.md`, `scripts/install.sh`, `scripts/orphan-skill-scan.sh`, and `docs/` are stripped from the extracted tarball before it is placed in the project.

Já o `install.sh` (linhas 128–136) executa:

```bash
rm -rf "$EXTRACTED_ROOT/.claude"
rm -rf "$EXTRACTED_ROOT/docs"
rm -f "$EXTRACTED_ROOT/CLAUDE.md"
rm -f "$EXTRACTED_ROOT/README.md"
rm -f "$EXTRACTED_ROOT/README.pt-BR.md"
rm -f "$EXTRACTED_ROOT/.gitignore"
rm -f "$EXTRACTED_ROOT/scripts/install.sh"
rm -f "$EXTRACTED_ROOT/scripts/orphan-skill-scan.sh"
```

A documentação **não menciona**: `.claude/`, `README.md`, `README.pt-BR.md`, `.gitignore`.

> **Fingerprint:** `docs-sync-claude-md-package-exclusions`

| Impacto | Detalhe |
|---------|---------|
| **Positivo (corrigir)** | Contribuintes deixam de adivinhar o que vai ou não para o tarball |
| **Positivo (corrigir)** | Quem usa o repositório como base/fork sabe o que precisa restaurar |
| **Negativo (não corrigir)** | Surpresas em PRs que adicionam arquivos no root e não veem no projeto instalado |

**Recomendação:** atualizar a frase em `CLAUDE.md § File Structure` para listar **todos** os caminhos strippados, ou adicionar um comentário no topo do `install.sh` apontando para a seção do CLAUDE.md (e mantê-los sincronizados via PR review).

---

## 1.2 `commit.md` é o único comando que **não** restringe escopo ao worktree atual

`plan.md`, `fix.md`, `review.md`, `backend.md`, `frontend.md`, `fullstack.md`, `refactor.md` e outros começam com o bloco de detecção de contexto:

```text
Before acting, identify the current working context:
- Run `git branch --show-current`
- Run `git diff --name-only HEAD`
- Run `git diff --name-only main...HEAD`
- Check `.claude/.worktree-session` if present

Restrict all analysis and actions to files and changes within this context.
```

O `commit.md` (linhas 1–11) **pula esse bloco** e parte direto para `git status --short` em qualquer escopo. Em teoria não é um erro (commit é um ato local), mas:

- Em workflows multi-agent + worktrees (ver `skills/shared/worktree/SKILL.md`), o `commit.md` pode acabar tentando commitar arquivos **fora** do worktree em curso.
- Pelo menos a leitura inicial do `.claude/.worktree-session` não custaria nada e tornaria o comando consciente do contexto que os outros já estabeleceram.

> **Fingerprint:** `ref-commit-no-worktree-context`

**Recomendação:** prefixar o `commit.md` com a mesma detecção dos demais (4 linhas), apenas para garantir que o `git add` opere no diretório certo.

---

## 1.3 `$ARGUMENTS` documentado em apenas 1 comando de 22

O `commit.md` (linhas 95–103) traz uma tabela de argumentos:

| Argument | Effect |
|----------|--------|
| `all` / `--all` | Stage all modified files |
| `dry-run` / `--dry-run` | Preview only |
| `format: <pattern>` | Override pattern detection |
| `amend` | Amend the last commit |

Esse padrão é **excelente** e deveria estar em todos os comandos. Hoje, `plan.md`, `fix.md`, `backend.md`, `frontend.md`, `architect.md`, `qa.md`, `security.md`, `dba.md`, `devops.md`, `tester.md`, `docs.md`, `review.md`, `pr.md`, `refactor.md`, `design.md` e os 5 `workflow-*` referenciam `$ARGUMENTS` mas **não documentam** nem o que esperam, nem que opções aceitam.

> **Fingerprint:** `docs-sync-commands-arguments-table`

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Usuários descobrem flags sem ler código (ex.: `/devteam:plan scope:full`, `/devteam:review depth:strict`) |
| **Positivo** | Permite testes de regressão por argumento |
| **Negativo** | Cada comando ganha 5–15 linhas; aumento total ≈ 100 linhas distribuídas |
| **Negativo** | Risco de "documentação de argumentos que ninguém usa"; mitigar adotando apenas argumentos efetivamente referenciados nos agentes spawnados |

**Recomendação:** elevar a seção `## $ARGUMENTS options` do `commit.md` a **padrão obrigatório** em `commands/*.md`, adicionando-a aos 21 comandos que faltam. Pode entrar como uma checagem leve no `orphan-skill-scan.sh` (alerta se um comando contém `$ARGUMENTS` mas não tem a tabela).

---

## 1.4 `install.sh` engole mensagens de erro do download

Em `install.sh` linha 100:

```bash
if ! HTTP_GET_FILE "$TARBALL_URL" "$TMP_TAR" 2>/dev/null; then
```

O `2>/dev/null` joga fora a saída de erro do `curl`/`wget`. Em caso de DNS resolvendo errado, certificado expirado ou rate-limit do GitHub (HTTP 403), o usuário vê apenas:

```
ERROR: Failed to download https://github.com/.../archive/...tar.gz
```

…sem detalhe. Em ambientes corporativos com proxy ou rede instável, isto força um debug manual.

> **Fingerprint:** `auto-installer-error-output`

**Recomendação:** capturar `stderr` em variável e imprimir em caso de falha:

```bash
ERR=$(HTTP_GET_FILE "$TARBALL_URL" "$TMP_TAR" 2>&1) || {
  echo "ERROR: Download failed:" >&2
  echo "$ERR" >&2
  exit 1
}
```

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Erros de rede ficam diagnosticáveis em primeiro contato |
| **Negativo** | Mensagem do `curl`/`wget` pode incluir stack traces ruidosos; mitigável com `head -3` |

---

## 1.5 `software-architect` não está mapeado em `commands/architect.md`?

O `CLAUDE.md` lista `/devteam:architect` apontando para `software-architect`. O arquivo existe (`commands/architect.md`). Esta auditoria não detectou inconsistência **funcional**, mas detectou que **`software-architect.md` tem 180 linhas** (abaixo do limite ~200), enquanto o `setup-assistant` ultrapassa em 100% (404 linhas — já registrado em 2026-05-06). Não há fingerprint adicional aqui — é apenas confirmação positiva de que o agente de arquitetura está bem dimensionado.

---

## 1.6 Resumo de fingerprints novos

| Fingerprint | Tema |
|-------------|------|
| `docs-sync-claude-md-package-exclusions` | CLAUDE.md desatualizado em relação ao install.sh |
| `ref-commit-no-worktree-context` | `commit.md` não respeita worktree session |
| `docs-sync-commands-arguments-table` | Falta tabela de `$ARGUMENTS` em 21/22 comandos |
| `auto-installer-error-output` | `install.sh` joga fora detalhes de erro do download |
