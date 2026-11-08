# Every agent: tools, processes, worktrees and the shell

Facts for any agent working in this repo, the orchestrating session included. They are written once here so the role files do not each carry a copy that drifts. This repo's own commands, folders and stand-ins are in `local/repo.md`.

An agent sees no memory and no earlier session, so everything it needs is in its role file, in the files that names, or in its prompt.

## Tools and processes

- **Write a long run's output to a file and read the file**, not the terminal: `<command> > <file> 2>&1`. Tests, walks and builds all print more than the context can afford.
- **A subagent runs long jobs in the foreground** with the Bash tool's `timeout` parameter, up to 600000 ms (ten minutes), and never uses `run_in_background`: each exit wakes the orchestrating session. The orchestrating session alone runs a job it is not waiting on in the background, and waits for the notification rather than polling with `sleep`. The guard refuses `run_in_background` from a subagent.
- **Stop only the processes you started, by process id.** Never by name (`pkill`, `killall`, `kill` fed by `pgrep`): the other agents' browsers and servers, and the user's own, match the same name (a walker ran `pkill -f chrom` during the first parallel walk, 2026-11-06). The guard refuses these.
- **Read a file with the Read tool before editing it** (a range is enough); Edit refuses a file seen only through `cat` or `sed`.
- **Outline a module before reading it, then read the range you need.** A large file read whole costs more context than the ticket. `local/repo.md` gives the outline command for this repo's language.
- **A removal's target is never a shell variable**: the harness refuses `git worktree remove $w` in a loop and `git branch -d $names`. List the targets literally, one command per target.
- **When the guard refuses a command, do what its message says.** Do not look for another spelling of the same command. If the rule is wrong for the case in hand, say so in your report: that is how the rule gets fixed.

## When the gate refuses

- **A refusal is one line**: `gate: refused by <rule>: <what happened>. Needs: <the input that satisfies it>`. Read it for its rule and its need, and supply the need. A rule name is a fixed vocabulary: one name per condition, each listed with its meaning in `RULES` in the gate's `refuse.py`.
- **The gate's source is not opened.** Reading it to learn what a refusal wanted is the cost this section removes; the line holds what you need.
- **A refusal that lacks either part is a kit defect.** Report it, for the ledger, and say which command printed it; do not work out the need from the code.

## Git

- **Work in progress is a commit on your branch**, squashed or amended later; never a stash. It is made at green: a red test stays uncommitted until it passes. The guard refuses `git stash`.
- **Never bypass a hook** (`--no-verify`, `commit -n`, or a changed `core.hooksPath`). A hook that fails is a red check. The guard refuses all three.
- **Pushing, opening the pull request and marking it ready are the orchestrating session's.** Merging into `main` is the user's. The guard refuses a push from a subagent, any forced push, and any push or merge into a protected branch.
- **A commit still lands if the shell gives up** on a long pre-commit, so check `git status -sb` before going on.
- **Back out of a merge that went wrong with `git merge --abort`** and report it. Whoever ran the merge does not try again until the orchestrating session has read why.

## In a worktree

- **One ticket, one worktree, one branch**: `.claude/worktrees/<NN-slug>/` on branch `ticket/<NN-slug>`, where `<NN-slug>` is the ticket's file name without `.md` (or its leading words), branched from the integration branch's tip. The gate matches worktrees to tickets by that name. A part of one ticket's work done by a separate agent, such as one exploratory walker's area, is `<NN-slug>--<part>`.
- **Shared tooling lives in the main checkout.** A virtual environment, an installed-dependencies folder, or a build cache is not duplicated per worktree; call it by absolute path from the main checkout unless `local/repo.md` says otherwise.
- **Leave any shared-workspace or shared-port environment variable unset.** Each test run starts its own server on a free port with its own temporary state. A shared one makes parallel runs read each other's data.
- **Under parallel load, browser or network tests time out.** Re-run a failing one alone before calling it a failure.

## This machine: zsh on macOS

Replace this section if the agents run somewhere else.

- **Quote globs and expand them in place**: `ls 'docs/'*.md` or `ls docs | grep md`; an unmatched glob is an error ("no matches found"), and a glob held in a variable is never expanded.
- **An unquoted `$var` is one word**: `for b in $list` loops once over every line. Pipe into `while read b` instead.
- **A word starting with `=` is a command lookup**: separate output with `---`, not `=====`.
- **There is no `timeout` command.** Use the Bash tool's `timeout` parameter.
- **`sed -i` takes a backup suffix**, so `sed -i 's/a/b/' f` reads `'s/a/b/'` as the suffix and `f` as the script; write `sed -i '' 's/a/b/' f`, or edit with the Edit tool. The guard refuses the wrong form.
- **`grep` may be ugrep**, and refuses a bounded repeat like `.\{0,80\}` as too complex; use `cut -c1-80` to bound a line, or `grep -o` with a plain pattern.
- **A `sed` delimiter that appears in the text breaks the command**: Markdown is full of `/` and `|`. Use the Edit tool for Markdown.
- **A path with a space breaks an unquoted loop.** Quote every path, and read lists with `while IFS= read -r`.
