#!/bin/sh
# ############################################################################
# @Project: python-dev-standard
# @File Path: scripts/setup-agents-link.sh
# @Description: Wire the post-checkout hook and register the AGENTS.md hard
#   link for this machine. Run once per clone, and again only if the
#   workspace moves. Safe to re-run: it is idempotent.
# @Creation Date: 2026-11-18
# @Last Update: 2026-11-18
# ############################################################################

set -eu

repo_root=$(git rev-parse --show-toplevel)
git_dir=$(git rev-parse --git-dir)
hook_src="$repo_root/scripts/hooks/post-checkout"
link_conf="$git_dir/agents-links"

# 向上的每一级找 .workbuddy，其父目录即工作区根，避免硬编码层级
find_workspace_root() {
    current=$1
    while [ "$current" != "/" ] && [ "$current" != "." ]; do
        if [ "$(basename "$current")" = ".workbuddy" ]; then
            dirname "$current"
            return 0
        fi
        current=$(dirname "$current")
    done
    return 1
}

# 允许显式指定目标，否则按工作区布局推导
src=${1:-"$repo_root/assets/project-skeleton/AGENTS.md"}
if [ $# -ge 2 ]; then
    dst=$2
else
    workspace=$(find_workspace_root "$repo_root") || {
        printf 'error: not inside a .workbuddy workspace, pass the target path\n' >&2
        exit 1
    }
    dst="$workspace/AGENTS.md"
fi

# 源必须存在，否则清单写进去也只会每次报警告
[ -f "$src" ] || { printf 'error: source not found: %s\n' "$src" >&2; exit 1; }

# 让 Git 使用仓库内的 hook 目录，这样 hook 能跟着版本走
git config core.hooksPath scripts/hooks
chmod +x "$hook_src"

# NTFS 上 filemode 不可靠，显式记录执行位，clone 到 Linux 才不会丢
git update-index --chmod=+x scripts/hooks/post-checkout 2>/dev/null || true
git update-index --chmod=+x scripts/setup-agents-link.sh 2>/dev/null || true

# 清单是机器本地信息，写进 .git 而不是工作区
printf '%s\t%s\n' "$src" "$dst" >"$link_conf"

printf 'hook path : %s\n' "$(git config core.hooksPath)"
printf 'link conf : %s\n' "$link_conf"
printf 'source    : %s\n' "$src"
printf 'target    : %s\n' "$dst"

# 立刻跑一次，把当前可能已断的链接修好
GIT_DIR="$git_dir" sh "$hook_src" 0 0 1

# 用 inode 判定修复结果，而不是相信退出码
src_id=$(stat -c '%d:%i' "$src" 2>/dev/null || echo none)
dst_id=$(stat -c '%d:%i' "$dst" 2>/dev/null || echo none)
if [ "$src_id" = "$dst_id" ] && [ "$src_id" != "none" ]; then
    printf 'status    : linked (inode %s)\n' "$src_id"
else
    printf 'status    : NOT linked (%s vs %s)\n' "$src_id" "$dst_id" >&2
    exit 1
fi
