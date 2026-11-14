#!/bin/bash
# Commit ~/sim1-usage/{reports,bin} into results/sim1/usage/ on branch claude/project-thread-15vsbi and push.
# Uses a private index + commit-tree: never touches the shared checkout's working tree, index or HEAD.
set -euo pipefail
REPO=$HOME/chemmanifold-studio; BR=claude/project-thread-15vsbi; SRC=$HOME/sim1-usage
export GIT_DIR=$REPO/.git GIT_INDEX_FILE=$SRC/data/publish.index
cd "$SRC"
for i in 1 2 3 4; do git fetch -q origin "+refs/heads/$BR:refs/remotes/origin/$BR" 2>/dev/null && break || { git ls-remote --exit-code origin "refs/heads/$BR" >/dev/null 2>&1 || break; sleep $((2**i)); }; done
if git rev-parse -q --verify "refs/remotes/origin/$BR" >/dev/null; then PARENT=$(git rev-parse "refs/remotes/origin/$BR"); else git fetch -q origin main; PARENT=$(git rev-parse FETCH_HEAD); fi
git read-tree "$PARENT"
git rm -r -q --cached --ignore-unmatch results/sim1/usage >/dev/null
for f in reports/* bin/*; do
  [ -f "$f" ] || continue
  h=$(git hash-object -w "$f"); mode=100644; [ -x "$f" ] && mode=100755
  git update-index --add --cacheinfo "$mode,$h,results/sim1/usage/$f"
done
[ -f README.md ] && git update-index --add --cacheinfo "100644,$(git hash-object -w README.md),results/sim1/usage/README.md"
TREE=$(git write-tree)
[ "$TREE" = "$(git rev-parse "$PARENT^{tree}")" ] && { echo "no changes"; exit 0; }
C=$(git -c user.name=Javier -c user.email=jaba09@gmail.com commit-tree "$TREE" -p "$PARENT" -m "sim1 usage: daily report ${1:-$(date -d yesterday +%F)}" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
for i in 1 2 3 4; do git push -q origin "$C:refs/heads/$BR" && { git update-ref "refs/remotes/origin/$BR" "$C"; echo "pushed $C"; exit 0; }; sleep $((2**i)); done
echo "push failed" >&2; exit 1
