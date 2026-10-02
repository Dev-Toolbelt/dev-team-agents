#!/usr/bin/env bash
# scripts/hooks/lib/file-stat.sh — portable file mtime/size. Not a hook; sourced.
#
# GNU `stat -f` means "filesystem status" and prints a multi-line block to stdout
# before failing, so the BSD form cannot be tried first. GNU `-c` is probed first
# (it fails silently on BSD), then BSD `-f`, and every result is validated as an
# integer so a garbage capture can never reach shell arithmetic.

_dt_stat_num() {
    local gnu_fmt="$1" bsd_fmt="$2" file="$3" v
    v=$(stat -c "$gnu_fmt" "$file" 2>/dev/null) || v=""
    case "$v" in ''|*[!0-9]*) v=$(stat -f "$bsd_fmt" "$file" 2>/dev/null) || v="" ;; esac
    case "$v" in ''|*[!0-9]*) v=0 ;; esac
    echo "$v"
}

dt_file_mtime() { _dt_stat_num %Y %m "$1"; }
dt_file_size()  { _dt_stat_num %s %z "$1"; }

# dt_date_to_epoch YYYY-MM-DD — prints epoch seconds; prints nothing and returns 1
# when no tool can parse it (callers decide; never a silent 0).
dt_date_to_epoch() {
    local d="$1" v
    v=$(date -d "$d" +%s 2>/dev/null) || v=""
    case "$v" in ''|*[!0-9]*) v=$(date -j -f "%Y-%m-%d" "$d" +%s 2>/dev/null) || v="" ;; esac
    case "$v" in ''|*[!0-9]*)
        v=$(python3 -c 'import sys,calendar,time;print(calendar.timegm(time.strptime(sys.argv[1],"%Y-%m-%d")))' "$d" 2>/dev/null) || v="" ;;
    esac
    case "$v" in ''|*[!0-9]*) return 1 ;; esac
    echo "$v"
}
