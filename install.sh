#!/usr/bin/env bash
# Install AI-Musician-Skills into Claude Code and/or Codex CLI.
#
# Both runtimes follow the Agent Skills standard (https://agentskills.io):
# a skill is a directory containing SKILL.md. The only difference is the
# location each runtime scans:
#   Claude Code -> ~/.claude/skills/<name>/
#   Codex CLI   -> $CODEX_HOME/skills/<name>/  (default ~/.codex/skills/)
#
# Usage:
#   ./install.sh                 # install all skills into both runtimes (symlink)
#   ./install.sh --target claude # only Claude Code
#   ./install.sh --target codex  # only Codex CLI
#   ./install.sh --copy          # copy instead of symlink
#   ./install.sh --uninstall     # remove installed skills/links
#   ./install.sh --help
#
# Symlink (default) keeps installed skills in sync with this repo as you
# pull updates. Use --copy for an independent snapshot.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS=()
for d in "$REPO_DIR"/*/; do
  [ -f "${d}SKILL.md" ] && SKILLS+=("$(basename "$d")")
done

TARGET="both"
MODE="symlink"
ACTION="install"

CLAUDE_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
CODEX_DIR="${CODEX_HOME:-$HOME/.codex}/skills"

usage() {
  sed -n '2,26p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 0
}

while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    --target=*) TARGET="${1#*=}"; shift ;;
    --copy) MODE="copy"; shift ;;
    --symlink) MODE="symlink"; shift ;;
    --uninstall) ACTION="uninstall"; shift ;;
    -h|--help) usage ;;
    *) echo "Unknown option: $1" >&2; echo "Run with --help for usage." >&2; exit 2 ;;
  esac
done

case "$TARGET" in
  claude|codex|both) ;;
  *) echo "Invalid --target '$TARGET' (expected: claude | codex | both)" >&2; exit 2 ;;
esac

if [ ${#SKILLS[@]} -eq 0 ]; then
  echo "No skills found in $REPO_DIR (expected subdirectories containing SKILL.md)." >&2
  exit 1
fi

# place_one <dest-skills-dir> <runtime-label>
place_one() {
  local dest_root="$1" label="$2" name src dest
  mkdir -p "$dest_root"
  for name in "${SKILLS[@]}"; do
    src="$REPO_DIR/$name"
    dest="$dest_root/$name"
    if [ "$ACTION" = "uninstall" ]; then
      if [ -L "$dest" ] || [ -e "$dest" ]; then
        rm -rf "$dest"
        echo "  removed  $label: $dest"
      fi
      continue
    fi
    # Refuse to clobber a real (non-symlink) directory the user may have edited.
    if [ -d "$dest" ] && [ ! -L "$dest" ]; then
      echo "  SKIP     $label: $dest exists and is not a symlink (remove it manually to reinstall)" >&2
      continue
    fi
    rm -rf "$dest"
    if [ "$MODE" = "copy" ]; then
      cp -R "$src" "$dest"
      echo "  copied   $label: $dest"
    else
      ln -s "$src" "$dest"
      echo "  linked   $label: $dest -> $src"
    fi
  done
}

echo "AI-Musician-Skills installer"
echo "  repo:    $REPO_DIR"
echo "  skills:  ${SKILLS[*]}"
echo "  action:  $ACTION ($MODE)"
echo

if [ "$TARGET" = "claude" ] || [ "$TARGET" = "both" ]; then
  echo "Claude Code  ($CLAUDE_DIR)"
  place_one "$CLAUDE_DIR" "claude"
  echo
fi

if [ "$TARGET" = "codex" ] || [ "$TARGET" = "both" ]; then
  echo "Codex CLI    ($CODEX_DIR)"
  place_one "$CODEX_DIR" "codex"
  echo
fi

if [ "$ACTION" = "uninstall" ]; then
  echo "Uninstall complete."
else
  echo "Done. Restart your agent (or start a new session) so it picks up the skills."
  echo "Invoke explicitly with:  Claude Code -> /guitar-arrange-skill   Codex -> /use guitar-arrange-skill"
fi
