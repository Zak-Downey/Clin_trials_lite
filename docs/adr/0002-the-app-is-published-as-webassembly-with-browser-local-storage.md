# 2. The app is published as WebAssembly with browser-local storage

**Status:** accepted (2026-09-20)

## The question

The monitor had to be usable by an analyst with no Python installed, and the
requirement it was specified under was *no login*. Nobody was to be asked to
create an account, be issued a password, or have their competitor watchlist
sitting in somebody else's database.

That rules out the ordinary shape for a web app -- a server holding everyone's
data, handing each person their own back once they have proved who they are --
because the proving is the login. What is left is to put the whole app in the
visitor's browser, which raises the question this record answers: where does an
analyst's watchlist then live, and what does that cost them?

## The decision

Publish the app as a static page whose Python is compiled to WebAssembly by
[stlite](https://stlite.net) and executed in the visitor's own browser. Keep the
watchlist in the browser: `web/index.html` mounts `/watchlist` on IndexedDB
through stlite's `idbfsMountpoints`, and points `MONITOR_DB` at the SQLite file
inside it.

There is no server, no account, and no database anybody else can read. The page
is served by GitHub Pages, which holds no data of ours, and the registry is
called from the analyst's own browser rather than through us.

## Why

No login is not a feature that was dropped; it is the constraint everything else
follows from. Once nobody proves who they are, there is nobody for a server to
hand a watchlist back *to*, so a server holding watchlists would be holding them
for anyone who asked. Keeping the data on the machine that made it is the honest
version of that constraint rather than a shortcut around it.

What it buys is worth naming, because it is most of the reason to accept the
cost below. A competitor watchlist is a statement about what a company is paying
attention to, and here it never leaves the analyst's machine -- there is no
breach that exposes it, and no subpoena that reaches it, because there is no
copy to take. Nothing has to be administered: no accounts to provision when an
analyst joins or revoke when they leave, no hosting bill, no database to keep
upgraded, and no credential anywhere in the publishing pipeline.

The choice was also cheap to make, which is not a reason on its own but removes
the usual argument against. `storage.py` already read its location from the
environment, so keeping the watchlist in the browser cost no change to the
storage layer at all: the page sets `MONITOR_DB` and mounts a directory. The
same modules run locally against an ordinary `monitor.db` and in the browser
against an IndexedDB-backed one. Running in a browser did cost application code
elsewhere -- `browser.py` carries the transport and the pause between registry
calls -- but none of it for where the data lives.

**The trade-off accepted: no login, and therefore no sync, no backup, no
sharing.** These are one consequence wearing three faces, and all three are
real:

- **No sync.** A watchlist built on a desktop is not there on a laptop. The
  analyst who covers two machines keeps two unrelated sets of lists.
- **No backup.** Nobody is holding a copy. Clearing site data, using a private
  window, or a browser profile being reset takes the monitoring with it, and
  there is nothing to restore from.
- **No sharing.** Two analysts cannot read one list. There is no way to hand
  a watchlist to a colleague, or for a team to keep one between them.

A fourth consequence falls out of how the write-out works rather than from the
login: stlite syncs the mounted directory to IndexedDB as a whole file after
each script run, so two tabs of the app open at once are two copies of the
database drifting apart, and whichever acts last overwrites the other. One tab,
on one machine, with nothing leaving it.

None of that is hidden from the analyst. The README states it where somebody
deciding whether to trust the tool will read it, because a tool that forgets and
a tool that lied differ only in whether it said so first.

## What would reopen this

A requirement that two people see the same list. That is the one this decision
cannot be stretched to cover: sharing needs a server holding the list, and a
server holding lists needs to know whose is whose, which is the login. Anyone
arriving at that is revisiting this record, not fixing a bug, and the cost they
are taking on is the whole of the "why" above -- somewhere to store other
people's competitive intelligence, and the duty of care that comes with it.

Backup and hand-to-hand sharing, though, do *not* need the login, and that is
the cheaper move to reach for first: export a list to a file and import it back.
It gives an analyst something to keep, something to carry to their laptop, and
something to send a colleague, while the data stays theirs to move. It is not
sync -- two imported copies diverge from the moment they are opened -- but it
answers most of what people actually ask for when they ask for sync, and it
leaves this decision standing.

## See also

- `web/index.html`, the `idbfsMountpoints` comment on what the browser keeps and
  when it is written out
- `storage.py`, which reads `MONITOR_DB` and is otherwise unaware of any of this
- `README.md`, "Where your watchlists live", the same facts for the analyst
- `.scratch/github-pages-deployment/spec.md`, the feature this was decided for
- `.scratch/github-pages-deployment/issues/05-publish-the-site-to-github-pages.md`
- `.scratch/github-pages-deployment/issues/06-say-where-the-data-lives.md`
