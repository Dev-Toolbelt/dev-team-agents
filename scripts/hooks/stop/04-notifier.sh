#!/usr/bin/env bash
# Stop sub-script: emits context-window warnings and a rotating tip of session
# using the DEV TEAM AGENTS notification format.
#
# Context estimation strategy (in order of preference):
#   1. Transcript-based: read token usage from transcript JSONL (more accurate)
#      then apply transcript_multiplier to compensate for system prompt + tools
#      not stored in the transcript.
#   2. Turn-count heuristic: fallback when transcript_path is not available.
set -uo pipefail

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
USER_DATA_DIR="${PROJECT_ROOT}/.claude/user-data"
PREFS_FILE="${USER_DATA_DIR}/preferences.json"
SESSION_ID_FILE="${USER_DATA_DIR}/.session-id"
NOTIFIER_STATE_FILE="${USER_DATA_DIR}/.notifier-state"

# ── Hardcoded defaults (used when prefs file is missing or malformed) ─────────
SUPPRESS="false"
USER_LANG="en"
WARN_PCT=55
CRIT_PCT=60
TRANSCRIPT_MULTIPLIER="1.8"
MODEL_MAX_TOKENS=200000

# ── Read preferences (overrides defaults when file is valid) ──────────────────
if [ -f "$PREFS_FILE" ] && command -v python3 >/dev/null 2>&1; then
    _pref() {
        python3 -c \
            "import json,sys; d=json.load(open('$PREFS_FILE')); v=d.get('$1',$2); print(str(v).lower() if isinstance(v,bool) else v)" \
            2>/dev/null || echo "$2"
    }
    SUPPRESS=$(_pref suppress_notifications false)
    USER_LANG=$(_pref language en)
    WARN_PCT=$(_pref context_window_percent_warning 55)
    CRIT_PCT=$(_pref context_window_percent_limit 60)
    TRANSCRIPT_MULTIPLIER=$(_pref transcript_multiplier 1.8)
    MODEL_MAX_TOKENS=$(_pref model_max_tokens 200000)
fi

# ── Helper: check suppression ─────────────────────────────────────────────────
_is_suppressed() {
    local type="$1"
    case "$SUPPRESS" in
        true)       return 0 ;;
        false)      return 1 ;;
        *"$type"*)  return 0 ;;
        *)          return 1 ;;
    esac
}

# ── Helper: emit notification ─────────────────────────────────────────────────
_notify() {
    local type="$1" icon="$2" msg="$3"
    _is_suppressed "$type" && return
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo " ${icon}  DEV TEAM AGENTS  ${icon}"
    echo " ${msg}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# ── Session turn counter ──────────────────────────────────────────────────────
SESSION_ID=$(cat "$SESSION_ID_FILE" 2>/dev/null || echo "0")
STATE=$(cat "$NOTIFIER_STATE_FILE" 2>/dev/null || echo "")
STATE_SESSION=$(echo "$STATE" | cut -d: -f1)
STATE_TURNS=$(echo "$STATE" | cut -d: -f2)
STATE_TIP=$(echo "$STATE" | cut -d: -f3)
STATE_DATE=$(echo "$STATE" | cut -d: -f4)
TODAY=$(date +%Y-%m-%d 2>/dev/null || echo "")

if [ "$STATE_SESSION" = "$SESSION_ID" ]; then
    TURNS=$(( ${STATE_TURNS:-0} + 1 ))
    TIP_SHOWN="${STATE_TIP:-0}"
else
    TURNS=1
    TIP_SHOWN=0
fi

printf '%s:%d:%d:%s\n' "$SESSION_ID" "$TURNS" "$TIP_SHOWN" "${STATE_DATE:-}" > "$NOTIFIER_STATE_FILE"

# ── Fast-path: skip expensive processing in purely conversational sessions ────
# If no file changes were detected (DEVTEAM_NO_CHANGES=true) AND the tip for
# today was already shown, there is nothing to emit — exit early.
if [ "${DEVTEAM_NO_CHANGES:-false}" = "true" ] && [ "${STATE_DATE:-}" = "${TODAY:-}" ]; then
    exit 0
fi

# ── Context window estimation ─────────────────────────────────────────────────
PCT_USED=0
METHOD="turns"

# Attempt 1: transcript-based estimation (more accurate than turn count).
# The hook payload (stdin, saved to DEVTEAM_HOOK_PAYLOAD by stop.sh) contains
# transcript_path — a JSONL file where each line is a conversation turn with
# usage data. We sum all input+output tokens and apply a multiplier to
# estimate the full context (system prompt + tools + messages).
TRANSCRIPT_PATH=""
if [ -n "${DEVTEAM_HOOK_PAYLOAD:-}" ] && [ -f "${DEVTEAM_HOOK_PAYLOAD:-}" ] && command -v python3 >/dev/null 2>&1; then
    TRANSCRIPT_PATH=$(python3 -c \
        "import json; d=json.load(open('$DEVTEAM_HOOK_PAYLOAD')); print(d.get('transcript_path',''))" \
        2>/dev/null || true)
fi

if [ -n "$TRANSCRIPT_PATH" ] && [ -f "$TRANSCRIPT_PATH" ] && command -v python3 >/dev/null 2>&1; then
    TRANSCRIPT_TOKENS=$(python3 -c "
import json
total = 0
try:
    with open('${TRANSCRIPT_PATH}') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                usage = (entry.get('usage') or
                         entry.get('message', {}).get('usage') or
                         entry.get('response', {}).get('usage') or {})
                total += usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
            except Exception:
                pass
except Exception:
    pass
print(total)
" 2>/dev/null || echo 0)

    if [ "${TRANSCRIPT_TOKENS:-0}" -gt 0 ] 2>/dev/null; then
        PCT_USED=$(python3 -c \
            "print(min(100, round($TRANSCRIPT_TOKENS * $TRANSCRIPT_MULTIPLIER * 100 / $MODEL_MAX_TOKENS)))" \
            2>/dev/null || echo 0)
        METHOD="transcript"
    fi
fi

# Attempt 2: turn-count heuristic (fallback when transcript is unavailable).
# Calibration: 100% ≈ 45 turns (conservative estimate). Scale linearly.
if [ "$METHOD" = "turns" ]; then
    WARN_TURNS=$(python3 -c "print(max(5, round($WARN_PCT * 45 / 100)))" 2>/dev/null || echo 15)
    CRIT_TURNS=$(python3 -c "print(max(8, round($CRIT_PCT * 45 / 100)))" 2>/dev/null || echo 25)
    if [ "$TURNS" -ge "$CRIT_TURNS" ]; then
        PCT_USED=$CRIT_PCT
    elif [ "$TURNS" -ge "$WARN_TURNS" ]; then
        PCT_USED=$WARN_PCT
    fi
fi

# ── Emit context notification ─────────────────────────────────────────────────
if [ "${PCT_USED:-0}" -ge "${CRIT_PCT:-60}" ] 2>/dev/null; then
    if [ "$USER_LANG" = "pt-BR" ] || [ "$USER_LANG" = "pt" ]; then
        _notify "critical" "🚨" "Janela de contexto estimada em ≈${PCT_USED}%! Execute /compact agora ou inicie uma nova sessão para manter a qualidade das respostas."
    elif [ "$USER_LANG" = "es" ]; then
        _notify "critical" "🚨" "Ventana de contexto estimada en ≈${PCT_USED}%. Ejecuta /compact ahora o inicia una nueva sesión para mantener la calidad."
    else
        _notify "critical" "🚨" "Context window estimated at ≈${PCT_USED}%. Run /compact now or start a new session to maintain response quality."
    fi
elif [ "${PCT_USED:-0}" -ge "${WARN_PCT:-55}" ] 2>/dev/null; then
    if [ "$USER_LANG" = "pt-BR" ] || [ "$USER_LANG" = "pt" ]; then
        _notify "warning" "⚠️" "Sua janela de contexto está se aproximando do limite (≈${PCT_USED}%). Considere executar /compact ou iniciar uma nova sessão."
    elif [ "$USER_LANG" = "es" ]; then
        _notify "warning" "⚠️" "Tu ventana de contexto se está aproximando al límite (≈${PCT_USED}%). Considera ejecutar /compact o iniciar una nueva sesión."
    else
        _notify "warning" "⚠️" "Context window approaching limit (≈${PCT_USED}%). Consider running /compact or starting a new session."
    fi
fi

# ── Tip of session (once per session) ────────────────────────────────────────
if [ "${STATE_DATE:-}" != "${TODAY:-}" ] && ! _is_suppressed "info"; then
    DAY=$(date +%-d 2>/dev/null || date +%d | sed 's/^0//')
    TIP_INDEX=$(( (DAY - 1) % 15 ))

    TIPS_EN=(
        "Use /compact regularly or start a new session to keep your context window healthy and avoid hallucinations in long sessions."
        "Run /devteam:review before opening a PR — it automatically calls code-reviewer, software-architect, and security-specialist."
        "Record hard architectural decisions as ADRs: bash .claude/dev-team-agents/scripts/new-adr.sh \"title\". This prevents agents from questioning settled choices."
        "Use /devteam:plan at the start of any new feature — it runs a multi-agent analysis (architect + product + database + backend/frontend/devops as needed)."
        "Write non-obvious domain knowledge to the project wiki at .claude/docs/wiki/ after any revealing task — agents read it on startup."
        "/devteam:commit groups your staged changes by layer and generates Conventional Commits automatically."
        "Use /devteam:refactor for structured refactoring — it runs test-first coverage, maps dependencies, and produces ordered commit blocks."
        "Run a health check occasionally: 'Run a health check on this project' — it auto-fixes stale hooks, broken symlinks, and outdated preferences."
        "Use /devteam:security before any release or after touching auth, permissions, or data-handling code."
        "The session-summary.md is read by agents on startup — keeping it updated means agents pick up context from your last session without re-asking questions."
        "Use /devteam:dba when adding migrations or modifying schema — the database-specialist catches missed indexes and locking issues before they reach production."
        "Set auto_update: true in preferences.json to get automatic updates of dev-team-agents when new versions are released."
        "Use /devteam:docs to generate changelogs, runbooks, and release notes from your git history."
        "Stack-specific skills (Next.js, Laravel, Vue, etc.) are auto-loaded by agents when detected — check .claude/skills/ for what is available in your project."
        "Use /devteam:tester when you only need to add or update tests — it avoids spinning up the full dev team when scope is just coverage."
    )

    TIPS_PTBR=(
        "Use /compact regularmente ou inicie uma nova sessão para manter sua janela de contexto saudável e evitar alucinações em sessões longas."
        "Execute /devteam:review antes de abrir um PR — ele chama automaticamente code-reviewer, software-architect e security-specialist."
        "Registre decisões arquiteturais difíceis como ADRs: bash .claude/dev-team-agents/scripts/new-adr.sh \"título\". Isso evita que agentes questionem escolhas já feitas."
        "Use /devteam:plan no início de qualquer nova funcionalidade — ele executa uma análise multi-agente (architect + product + database + backend/frontend/devops conforme necessário)."
        "Escreva conhecimento de domínio não óbvio na wiki do projeto em .claude/docs/wiki/ após qualquer tarefa reveladora — agentes leem isso na inicialização."
        "/devteam:commit agrupa suas mudanças por camada e gera Conventional Commits automaticamente."
        "Use /devteam:refactor para refatoração estruturada — ele executa cobertura test-first, mapeia dependências e produz blocos de commit ordenados."
        "Execute um health check ocasionalmente: 'Faça um health check neste projeto' — ele corrige automaticamente hooks desatualizados, symlinks quebrados e preferências desatualizadas."
        "Use /devteam:security antes de qualquer release ou após tocar em código de auth, permissões ou manipulação de dados."
        "O session-summary.md é lido por agentes na inicialização — mantê-lo atualizado significa que agentes recuperam contexto da sua última sessão sem fazer perguntas repetidas."
        "Use /devteam:dba ao adicionar migrações ou modificar schema — o database-specialist identifica índices faltantes e problemas de locking antes de chegarem à produção."
        "Defina auto_update: true no preferences.json para receber atualizações automáticas do dev-team-agents quando novas versões forem lançadas."
        "Use /devteam:docs para gerar changelogs, runbooks e release notes a partir do seu histórico git."
        "Skills específicos de stack (Next.js, Laravel, Vue, etc.) são carregados automaticamente por agentes quando detectados — verifique .claude/skills/ para o que está disponível no seu projeto."
        "Use /devteam:tester quando você só precisa adicionar ou atualizar testes — evita acionar o time completo quando o escopo é apenas cobertura."
    )

    TIPS_ES=(
        "Usa /compact regularmente o inicia una nueva sesión para mantener tu ventana de contexto saludable y evitar alucinaciones en sesiones largas."
        "Ejecuta /devteam:review antes de abrir un PR — llama automáticamente a code-reviewer, software-architect y security-specialist."
        "Registra las decisiones arquitectónicas difíciles como ADRs: bash .claude/dev-team-agents/scripts/new-adr.sh \"título\". Esto evita que los agentes cuestionen decisiones ya tomadas."
        "Usa /devteam:plan al inicio de cualquier nueva funcionalidad — ejecuta un análisis multi-agente (architect + product + database + backend/frontend/devops según sea necesario)."
        "Escribe conocimiento de dominio no obvio en la wiki del proyecto en .claude/docs/wiki/ después de cualquier tarea reveladora — los agentes la leen al inicio."
        "/devteam:commit agrupa tus cambios por capa y genera Conventional Commits automáticamente."
        "Usa /devteam:refactor para refactorización estructurada — ejecuta cobertura test-first, mapea dependencias y produce bloques de commit ordenados."
        "Ejecuta un health check ocasionalmente: 'Haz un health check en este proyecto' — corrige automáticamente hooks obsoletos, symlinks rotos y preferencias desactualizadas."
        "Usa /devteam:security antes de cualquier release o después de tocar código de auth, permisos o manejo de datos."
        "El session-summary.md es leído por agentes al inicio — mantenerlo actualizado significa que los agentes retoman el contexto de tu última sesión sin hacer preguntas repetidas."
        "Usa /devteam:dba al agregar migraciones o modificar esquemas — el database-specialist detecta índices faltantes y problemas de bloqueo antes de que lleguen a producción."
        "Establece auto_update: true en preferences.json para recibir actualizaciones automáticas de dev-team-agents cuando se publiquen nuevas versiones."
        "Usa /devteam:docs para generar changelogs, runbooks y notas de versión desde tu historial git."
        "Los skills específicos de stack (Next.js, Laravel, Vue, etc.) son cargados automáticamente por los agentes cuando se detectan — revisa .claude/skills/ para ver qué está disponible."
        "Usa /devteam:tester cuando solo necesitas agregar o actualizar pruebas — evita activar al equipo completo cuando el alcance es solo cobertura."
    )

    case "$USER_LANG" in
        pt-BR|pt) TIP="${TIPS_PTBR[$TIP_INDEX]}" ;;
        es)       TIP="${TIPS_ES[$TIP_INDEX]}" ;;
        *)        TIP="${TIPS_EN[$TIP_INDEX]}" ;;
    esac

    _notify "info" "ℹ️" "$TIP"

    printf '%s:%d:1:%s\n' "$SESSION_ID" "$TURNS" "$TODAY" > "$NOTIFIER_STATE_FILE"
fi

exit 0
