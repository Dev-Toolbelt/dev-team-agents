# Token Efficiency — Detailed Strategies

Detailed bash patterns and file operation recipes. See [SKILL.md](SKILL.md) for core rules.

---

## Quiet Output Modes

```bash
grep -q "term" file          # exit status only, no output
git --quiet commit -m "msg"
curl -s https://example.com
wget -q https://example.com
make -s
```

Use verbose flags only when the user explicitly asks for detailed output.

---

## Filter Log Files Before Reading

```bash
# Recent lines only
tail -100 app.log

# Filter for errors with context
grep -A 10 -i "error\|fail\|warning" app.log | head -100

# Specific time range
grep "2025-01-15" app.log | tail -50

# Count first, then read
grep -c "ERROR" app.log
grep "ERROR" app.log | tail -20
```

Only read the full log if the user explicitly says to, filtered output lacks context, or the file is small (<1000 lines).

---

## Lightweight Sources Before Large Files

```bash
# Git state
git status --short
git log --oneline -10

# Project dependencies (small files)
cat package.json | jq '.dependencies'
head -20 requirements.txt

# Process state
ps aux | grep node
```

---

## Grep Instead of Reading Files

```bash
# Find with context
grep -A 5 -B 5 "pattern" file.ts

# Case-insensitive
grep -i "error" file.log

# Recursive with limit
grep -r "TODO" src/ | head -20

# Count matches
grep -c "import" *.ts
```

---

## Read Files with Limits

```bash
# Check size first
wc -l large_file.ts

# Then read strategically
Read: large_file.ts (limit: 100)         # structure only
Read: large_file.ts (offset: 500, limit: 50)  # specific section
```

---

## Bash Commands Instead of Reading Files

### Copy

```bash
# Not: Read + Write
cp source.txt destination.txt
```

### Replace text in files

```bash
# macOS (BSD sed)
sed -i '' 's/old_value/new_value/g' config.yaml

# Linux (GNU sed)
sed -i 's/old_value/new_value/g' config.yaml

# Cross-platform (works on both)
sed -i.bak 's/old_value/new_value/g' config.yaml && rm config.yaml.bak

# Path separators — use | as delimiter
sed -i '' 's|old/path|new/path|g' config.yaml
```

> **macOS note:** `sed -i` without the empty string `''` fails on macOS with cryptic errors. Always use `sed -i ''` for macOS or `sed -i.bak` for cross-platform safety.

### Append

```bash
echo "New entry" >> log.txt
cat >> log.txt << 'EOF'
Multiple lines
of content
EOF
```

### Delete lines

```bash
sed -i '' '/DELETE/d' data.txt
grep -v "DELETE" data.txt > data_tmp.txt && mv data_tmp.txt data.txt
```

### Extract specific lines

```bash
sed -n '100,110p' large_file.ts
awk 'NR>=100 && NR<=110' large_file.ts
head -110 large_file.ts | tail -11
```

### Merge files

```bash
cat file1.ts file2.ts > combined.ts
cat file2.ts >> file1.ts
```

### Count lines/words/characters

```bash
wc -l file.ts
wc -w file.ts
wc -c file.ts
```

### Check if file contains text

```bash
grep -q "search_term" config.yaml && echo "Found" || echo "Not found"
```

### Sort and deduplicate

```bash
sort -u file.txt > sorted_unique.txt
awk '!seen[$0]++' file.txt > no_dupes.txt  # preserves order
```

### Find and replace across multiple files

```bash
find . -name "*.ts" -exec sed -i '' 's/OldClass/NewClass/g' {} +
for f in *.ts; do sed -i '' 's/OldClass/NewClass/g' "$f"; done
```

### Rename files in bulk

```bash
for f in *.txt; do mv "$f" "${f%.txt}.md"; done
```

### Directory size analysis

```bash
du -sh */          # all subdirectories, human-readable
du -sh */ | sort -h  # sorted by size
```

---

## When to Break These Rules

Still use Read/Edit/Write when:
1. **Complex logic required** — conditional edits based on file structure
2. **Code-aware changes** — editing within functions, preserving indentation
3. **Validation needed** — need to verify content before changing
4. **Interactive review** — user needs to see content before approving
5. **Creating new content** — use Write tool directly for new files
6. **Low-cost operations** — small files (< 100 lines) are fine to Read + Edit

---

## Filter Large Command Output

```bash
# Not: find / -name "*.ts"
find ./src -name "*.ts" | head -50
find . -name "*.ts" -type f | wc -l    # count first
find . -name "*.ts" | grep "test" | head -20

# Not: ls -laR /
ls -la
find . -maxdepth 2 -type f
tree -L 2
```

---

## Summarize, Don't Dump

**Bad:**
```
[Paste entire 5K token ls -la output with 500 files]
```

**Good:**
```
This directory has 487 files:
- 235 TypeScript files (src/)
- 142 test files (tests/)
- 89 config files (*.yaml, *.json)
- Entry point: src/index.ts

Want to see a specific area?
```

---

## Optimize Code Reading

```bash
# 1. Get overview
find ./src -name "*.ts" | head -20
grep -r "^export class " --include="*.ts" | head -20
grep -r "^export function " --include="*.ts" | wc -l

# 2. Read structure only
Read: src/index.ts (limit: 80)

# 3. Search for specific code
Grep: "class UserService" src/

# 4. Read only relevant section
Read: src/services/user.service.ts (offset: 150, limit: 50)
```

---

## JSON/Data Tools

```bash
# Not: Read entire JSON
cat config.json | jq '.database'
cat config.json | jq 'keys'

# CSV — sample and analyze
head -20 data.csv
wc -l data.csv
```

---

## Safe Glob Patterns

```bash
# Fails when no *.md files exist
for file in *.md 2>/dev/null; do ...  # WRONG

# Correct — nullglob handles empty matches
shopt -s nullglob
for file in *.md; do
    cp "$file" backup/
done
shopt -u nullglob

# Alternative — explicit check
if ls *.md 1>/dev/null 2>&1; then
    for file in *.md; do cp "$file" backup/; done
fi
```

---

## Moving Files Safely

```bash
# Fails on missing files
mv file1.ts file2.ts file3.ts destination/

# Safe — handles missing files gracefully
for f in file1.ts file2.ts file3.ts; do
    [ -f "$f" ] && mv "$f" destination/ && echo "Moved $f"
done

# Pattern-based
for f in fix_*.ts; do
    [ -f "$f" ] && mv "$f" deprecated/
done
```

---

## Validate Against Large Reference Files

```bash
# Inefficient — read large file repeatedly
grep -c "pattern" large_reference.json

# Efficient — extract once, reuse
grep -o '"id":"[^"]*"' large_reference.json | sed 's/"id":"//;s/"//' > ids.txt
# Future validations use the small extracted file
grep -qF "$id" ids.txt && echo "valid" || echo "invalid"
```

---

## Background Process Management

```bash
# Start process in background
Bash(command="npm run build", run_in_background=true)
# Returns shell_id

# Tell user once with the ID, then don't poll
"Build running in background (ID: abc123). Let me know when to check."

# Check when user asks
TaskOutput(task_id="abc123")
```

Avoid repeated polling — each check consumes context. Let the user decide when to check results.
