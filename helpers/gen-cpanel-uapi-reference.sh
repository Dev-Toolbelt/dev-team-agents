#!/usr/bin/env bash
# gen-cpanel-uapi-reference.sh — Regenerate the cPanel UAPI function reference
# (skills/integrations/cpanel/references/function-index.md and modules/*.md)
# from the official OpenAPI spec published at api.docs.cpanel.net.
#
# Only the files carrying the `<!-- GENERATED from … -->` header are owned by
# this script. The hand-written references next to them (authentication.md,
# recipes.md, …) and SKILL.md are never touched — after a regeneration, re-check
# recipes.md against any function the new spec renamed or deprecated, and bump
# the "Source of truth" version line in SKILL.md.
#
# Usage:
#   bash helpers/gen-cpanel-uapi-reference.sh                 # download spec, regenerate
#   bash helpers/gen-cpanel-uapi-reference.sh --spec FILE     # use a local spec (JSON)
#   bash helpers/gen-cpanel-uapi-reference.sh --check         # exit 1 if the committed files drift
#
# Requires: python3, curl (unless --spec is given).
set -euo pipefail

SPEC_URL="https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="$REPO_ROOT/skills/integrations/cpanel/references"
MARKER="<!-- GENERATED from "

spec=""
check=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --spec) spec="${2:?--spec needs a file}"; shift 2 ;;
    --check) check=true; shift ;;
    -h|--help) sed -n '2,17p' "$0"; exit 0 ;;
    *) echo "gen-cpanel-uapi-reference: unknown argument: $1" >&2; exit 2 ;;
  esac
done

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

if [[ -z "$spec" ]]; then
  spec="$work/cpanel.openapi.json"
  curl -fsSL "$SPEC_URL" -o "$spec" || { echo "gen-cpanel-uapi-reference: could not download $SPEC_URL" >&2; exit 1; }
fi
[[ -f "$spec" ]] || { echo "gen-cpanel-uapi-reference: spec not found: $spec" >&2; exit 1; }

python3 - "$spec" "$work/out" <<'PY'
import json,re,os,sys
SPEC=json.load(open(sys.argv[1]))
OUT=sys.argv[2]
VER=SPEC['info']['version']
SRC='https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json'
SCH=SPEC['components']['schemas']
groups=SPEC['x-tagGroups']
t2g={}
for g in groups:
    for t in g['tags']: t2g.setdefault(t,g['name'])
def slug(s): return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')
def deref(s,seen=0):
    while isinstance(s,dict) and '$ref' in s and seen<10:
        s=SCH[s['$ref'].split('/')[-1]]; seen+=1
    if isinstance(s,dict) and 'allOf' in s:
        m={'type':'object','properties':{}}
        for p in s['allOf']:
            p=deref(p); m['properties'].update(p.get('properties',{}))
            if p.get('description') and not m.get('description'): m['description']=p['description']
        return m
    return s
def flat(txt):
    if not txt: return ''
    t=re.sub(r'\n\s*[\*\-]\s+','; ',txt)
    t=re.sub(r'\*\*(Notes?|Important|Warning):\*\*\s*;?','\\1: ',t)
    t=re.sub(r'\s*\n\s*',' ',t).strip()
    t=re.sub(r'(:)\s*;\s*',r'\1 ',t)
    return t.replace('|','\\|')
def first(txt):
    t=flat(txt); m=re.match(r'(.+?\.)(\s|$)',t)
    return (m.group(1) if m else t)[:220]
def typ(s):
    s=deref(s or {})
    if 'oneOf' in s or 'anyOf' in s:
        return ' or '.join(sorted({typ(x) for x in s.get('oneOf',s.get('anyOf'))}))
    t=s.get('type','object' if s.get('properties') else 'any')
    if t=='array': t='array of '+typ(s.get('items',{}))
    if 'enum' in s: t+=' ('+', '.join('`%s`'%e for e in s['enum'][:12])+(', …' if len(s['enum'])>12 else '')+')'
    if s.get('format'): t+=' <'+s['format']+'>'
    return t
def ex(s):
    s=deref(s or {})
    if 'example' in s and s['example'] not in (None,''):
        e=s['example']; e=json.dumps(e) if not isinstance(e,str) else e
        return e if len(e)<60 else None
    return None
def fields(s,depth,ind=''):
    s=deref(s or {}); out=[]
    if s.get('type')=='array' or 'items' in s:
        it=deref(s.get('items',{}))
        if it.get('properties') or 'oneOf' in it or 'anyOf' in it:
            out.append(ind+'- *(array of objects)*')
            return out+fields(it,depth,ind+'  ')
        return out
    for alt in ('oneOf','anyOf'):
        if alt in s:
            alts=[deref(a) for a in s[alt]]
            rich=[a for a in alts if a.get('properties') or a.get('items')]
            if len(rich)==1: return fields(rich[0],depth,ind)
            for a in rich:
                out.append(ind+'- *variant: %s*'%(a.get('title') or a.get('type','object')))
                out+=fields(a,depth,ind+'  ')
            return out
    for k,v in (s.get('properties') or {}).items():
        v=deref(v)
        out.append('%s- `%s` (%s) — %s'%(ind,k,typ(v),first(v.get('description',''))))
        if depth>1: out+=fields(v,depth-1,ind+'  ')
    return out
ops=[]
for p,pm in SPEC['paths'].items():
    for m,o in pm.items():
        g=next((t2g[t] for t in o['tags'] if t in t2g),'Other')
        sub=o['tags'][-1]
        mod,fn=p.strip('/').split('/',1)
        ops.append(dict(path=p,method=m.upper(),op=o,group=g,sub=sub,mod=mod,fn=fn))
os.makedirs(OUT+'/modules',exist_ok=True)
hdr=lambda title:'<!-- GENERATED from %s (cPanel UAPI %s). Do not hand-edit; regenerate instead. -->\n# %s\n\n'%(SRC,VER,title)
idx=[]
gdesc={}
for g in groups:
    gops=[x for x in ops if x['group']==g['name']]
    fn_=slug(g['name'])+'.md'
    lines=[hdr('UAPI — '+g['name'])]
    lines.append('Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).\n\n')
    lines.append('Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).\n\n')
    subs=[]
    for x in gops:
        if x['sub'] not in subs: subs.append(x['sub'])
    lines.append('## Contents\n\n')
    for s in subs:
        lines.append('- **%s**: %s\n'%(s,', '.join('[`%s::%s`](#%s)'%(x['mod'],x['fn'],slug(x['mod']+'-'+x['fn'])) for x in gops if x['sub']==s)))
    lines.append('\n')
    for s in subs:
        lines.append('## %s\n\n'%s)
        for x in [y for y in gops if y['sub']==s]:
            o=x['op']; name='%s::%s'%(x['mod'],x['fn'])
            lines.append('<a id="%s"></a>\n### `%s` — %s\n\n'%(slug(x['mod']+'-'+x['fn']),name,o.get('summary','')))
            meta=['`%s /execute/%s/%s`'%(x['method'],x['mod'],x['fn'])]
            ro=o.get('x-readonly')
            meta.append('RO' if ro is True else 'RW' if ro is False else 'RO/RW: unspecified')
            if o.get('x-rollback'): meta.append('rollback: '+o['x-rollback'])
            if o.get('x-cpanel-available-version'): meta.append('since %s'%o['x-cpanel-available-version'])
            if o.get('deprecated'): meta.append('**DEPRECATED**')
            if o.get('x-cpanel-internal-only'): meta.append('**internal-only**')
            if o.get('x-cpanel-plugin'): meta.append('requires plugin `%s`'%o['x-cpanel-plugin'])
            if o.get('x-cpanel-rpm'): meta.append('requires package `%s`'%o['x-cpanel-rpm'])
            if 'x-cpanel-cli-support' in o: meta.append('CLI support: %s'%o['x-cpanel-cli-support'])
            lines.append(' · '.join(meta)+'\n\n')
            lines.append(flat(o.get('description',''))+'\n\n')
            ps=o.get('parameters',[])
            if ps:
                lines.append('**Parameters**\n\n')
                for pr in sorted(ps,key=lambda q:not q.get('required')):
                    sc=deref(pr.get('schema') or next(iter(pr.get('content',{}).values()),{}).get('schema',{}))
                    isjson='content' in pr
                    bits=['**required**' if pr.get('required') else 'optional',typ(sc)]
                    if 'default' in sc: bits.append('default `%s`'%str(sc['default'])[:80])
                    e=ex(sc)
                    if e: bits.append('e.g. `%s`'%e)
                    if isjson: bits.insert(1,'JSON-encoded')
                    lines.append('- `%s` · %s — %s\n'%(pr['name'],' · '.join(bits),flat(pr.get('description',''))))
                    if isjson and sc.get('properties'): lines+= [l+'\n' for l in fields(sc,1,'  ')]
                lines.append('\n')
            rb=o.get('requestBody')
            if rb:
                for ct,c in rb.get('content',{}).items():
                    lines.append('**Request body** (`%s`)\n\n'%ct)
                    lines+= [l+'\n' for l in fields(c.get('schema',{}),2)]
                    lines.append('\n')
            try:
                res=deref(o['responses']['200']['content']['application/json']['schema'])
                data=deref(res['properties']['result'])['properties'].get('data')
            except Exception: data=None
            if data:
                f=fields(data,2)
                lines.append('**Returns** `data`: %s%s\n\n'%(typ(data), ' — '+first(deref(data).get('description','')) if deref(data).get('description') else ''))
                if f: lines+= [l+'\n' for l in f[:40]]+(['- … (truncated; see the online reference)\n'] if len(f)>40 else [])+['\n']
            cli=next((c['source'] for c in o.get('x-codeSamples',[]) if c.get('label')=='CLI'),None)
            if cli: lines.append('```bash\n'+cli.rstrip()+'\n```\n\n')
            idx.append((name,o.get('summary',''),fn_,slug(x['mod']+'-'+x['fn']),'RO' if ro is True else 'RW' if ro is False else '?',o.get('deprecated',False)))
    open(OUT+'/modules/'+fn_,'w').write(''.join(lines))
    gdesc[g['name']]=(fn_,len(gops),sorted({x['mod'] for x in gops}))
# index
L=[hdr('UAPI Function Index')]
L.append('Every UAPI function in the spec (%d operations). Grep this file by keyword (`grep -i "dns" function-index.md`) and open the linked module file.\n\n'%len(ops))
L.append('## Groups\n\n| Group | File | Functions | Modules |\n|---|---|---|---|\n')
for g,(f,n,mods) in gdesc.items(): L.append('| %s | [%s](modules/%s) | %d | %s |\n'%(g,f,f,n,', '.join('`%s`'%m for m in mods)))
L.append('\n## Functions\n\n| Function | Summary | RO/RW | File |\n|---|---|---|---|\n')
for n,s,f,a,ro,dep in sorted(idx,key=lambda r:r[0].lower()):
    L.append('| `%s` | %s%s | %s | [%s](modules/%s#%s) |\n'%(n,s.replace('|','\\|'),' **(deprecated)**' if dep else '',ro,f[:-3],f,a))
open(OUT+'/function-index.md','w').write(''.join(L))
print('generated %d operations in %d groups (UAPI %s)'%(len(ops),len(gdesc),VER))
PY

if $check; then
  drift=0
  diff -q "$work/out/function-index.md" "$TARGET/function-index.md" >/dev/null 2>&1 || { echo "drift: function-index.md"; drift=1; }
  for f in "$work/out/modules/"*.md; do
    diff -q "$f" "$TARGET/modules/$(basename "$f")" >/dev/null 2>&1 || { echo "drift: modules/$(basename "$f")"; drift=1; }
  done
  for f in "$TARGET/modules/"*.md; do
    [[ -e "$work/out/modules/$(basename "$f")" ]] || { echo "stale: modules/$(basename "$f")"; drift=1; }
  done
  [[ $drift -eq 0 ]] && echo "gen-cpanel-uapi-reference: clean ✓"
  exit $drift
fi

mkdir -p "$TARGET/modules"
# A module file the new spec no longer produces is removed only when it carries
# the generated marker — a hand-written file in modules/ is never deleted.
for f in "$TARGET/modules/"*.md; do
  [[ -e "$f" ]] || continue
  [[ -e "$work/out/modules/$(basename "$f")" ]] && continue
  if head -1 "$f" | grep -qF "$MARKER"; then
    rm "$f"; echo "removed stale modules/$(basename "$f")"
  fi
done
cp "$work/out/modules/"*.md "$TARGET/modules/"
cp "$work/out/function-index.md" "$TARGET/function-index.md"
