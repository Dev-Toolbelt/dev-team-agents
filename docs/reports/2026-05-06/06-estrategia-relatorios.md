# 6. Estratégia de Originalidade dos Próximos Relatórios

← [Voltar ao índice](index.md)

Para garantir que **não haverá repetição** de sugestões nos próximos dias:

---

## Mecanismo

1. **Banco de fingerprints**: arquivo `docs/reports/_index.md` mantém todos os
   fingerprints já publicados. Cada sugestão deste relatório foi registrada lá.
2. **Convenção `<categoria>-<tópico-específico>`**: facilita filtrar por categoria e
   evitar repetição "ampla" do mesmo tema.
3. **Reaproveitamento permitido**: se um tema voltar com **escopo diferente**
   (ex.: `token-context-loading-dedup` já publicado, mas `token-tool-output-summarize`
   é tema novo), pode ser reproposto.
4. **Rotação trimestral**: fingerprints com mais de 90 dias podem migrar para
   `_index-archive-YYYY-Q.md` para o índice ativo não inflar.

## Fluxo do agendamento

```text
Antes de gerar o próximo relatório:
  1. Ler docs/reports/_index.md
  2. Construir lista de fingerprints "queimados"
  3. Gerar candidatos a sugestão
  4. Filtrar fora os fingerprints já queimados
  5. Se < 5 sugestões originais sobrarem:
       a. Aprofundar em sub-temas (ex.: rever uma skill específica em detalhes)
       b. Investigar áreas ainda não cobertas (testes, design, devops específico)
  6. Publicar relatório + acrescentar novos fingerprints ao índice
```

## Bandas temáticas a explorar nos próximos dias

Para alimentar o pipeline futuro com originalidade, eis macro-temas ainda **não
explorados** em profundidade neste relatório:

- Conteúdo concreto de skills individuais (ex.: revisão de `skills/devops/aws/SKILL.md`)
- Cobertura de testes — `test-pyramid` vs `test-strategy` (overlap?)
- Conteúdo dos hooks (`scripts/hooks/`) — robustez, error handling
- Templates (somente `plan-template.md` existe; faltam ADR, backlog, sprint?)
- Análise de `commands/*.md` individualmente
- Auditoria do `install.sh` e `update.sh` (resiliência, idempotência)
- Estratégia de versionamento e tags do git
- Internacionalização — só PT-BR e EN cobertos

Isso garante **um pipeline de pelo menos 30 dias de relatórios originais** com escopo
distinto a cada execução.
