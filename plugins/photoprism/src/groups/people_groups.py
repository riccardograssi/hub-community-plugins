"""People groups (e.g. university) on top of PhotoPrism subjects.

PhotoPrism has no native group-of-people entity. Groups live in a JSON file
and open the library with person:"A|B|C" (any member).
"""

from __future__ import annotations

import json
import os
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs

GROUPS_PATH = Path(
    os.environ.get("PHOTOPRISM_GROUPS_FILE", "/photoprism/storage/people-groups.json")
)
INJECT_PATH = Path(__file__).with_name("inject.html")

INJECT_MARK = "homelab-people-groups-btn"

PAGE_HTML = """<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Gruppi di persone — PhotoPrism</title>
  <style>
    :root { color-scheme: dark; --bg:#12151c; --card:#1c2230; --text:#e8eef8; --muted:#8b97ab; --accent:#c9a227; --line:rgba(255,255,255,.08); }
    * { box-sizing: border-box; }
    body { margin:0; font-family: system-ui, sans-serif; background:var(--bg); color:var(--text); }
    header { padding:1.25rem 1.5rem; border-bottom:1px solid var(--line); display:flex; gap:1rem; flex-wrap:wrap; align-items:center; justify-content:space-between; }
    h1 { margin:0; font-size:1.25rem; }
    a { color: var(--accent); }
    main { max-width: 920px; margin: 0 auto; padding: 1.25rem 1.5rem 3rem; }
    .row { display:flex; gap:.5rem; flex-wrap:wrap; margin-bottom:1rem; }
    input, button, select { font: inherit; padding:.5rem .7rem; border-radius:8px; border:1px solid var(--line); background:#0f131a; color:var(--text); }
    button { background:#5e2750; color:#fff; border:0; cursor:pointer; font-weight:600; }
    button.ghost { background:transparent; color:var(--accent); border:1px solid var(--line); }
    button.danger { background:#7f1d1d; }
    .grid { display:grid; grid-template-columns: 1fr 1fr; gap:1rem; }
    @media (max-width: 800px) { .grid { grid-template-columns: 1fr; } }
    .card { background: var(--card); border:1px solid var(--line); border-radius:12px; padding:1rem; }
    .card h2 { margin:0 0 .75rem; font-size:1rem; }
    ul { list-style:none; margin:0; padding:0; }
    li { padding:.45rem 0; border-bottom:1px solid var(--line); display:flex; justify-content:space-between; gap:.5rem; align-items:center; }
    li:last-child { border-bottom:0; }
    .muted { color: var(--muted); font-size:.9rem; }
    .people { max-height: 55vh; overflow: auto; }
    .people li { cursor:pointer; }
    .people li.on { outline:1px solid var(--accent); border-radius:8px; padding:.45rem .5rem; }
    #peopleSearch { width: 100%; margin: .5rem 0; }
    .err { color:#fca5a5; }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Gruppi di persone</h1>
      <p class="muted" style="margin:.35rem 0 0">Università, squadra, famiglia: un gruppo raggruppa volti già riconosciuti. Le foto del gruppo sono solo quelle in cui compaiono <strong>almeno due</strong> persone del gruppo insieme (uno da solo non basta).</p>
    </div>
    <a href="/ui/library/people">Torna a Persone</a>
  </header>
  <main>
    <div class="row">
      <input id="newName" placeholder="Nome gruppo, es. Università Tor Vergata" size="40" />
      <button id="create">Crea gruppo</button>
    </div>
    <p id="msg" class="err"></p>
    <div class="grid">
      <section class="card">
        <h2>Gruppi</h2>
        <ul id="groups"></ul>
      </section>
      <section class="card">
        <h2 id="detailTitle">Dettaglio</h2>
        <p class="muted" id="hint">Seleziona un gruppo, poi spunta le persone riconosciute.</p>
        <div class="row" id="actions" hidden>
          <button id="openPhotos">Apri foto di gruppo</button>
          <button class="ghost" id="rename">Rinomina</button>
          <button class="danger" id="del">Elimina</button>
        </div>
        <input id="peopleSearch" placeholder="Cerca persona…" autocomplete="off" hidden />
        <ul class="people" id="people"></ul>
      </section>
    </div>
  </main>
  <script>
    const api = (path, opts) => fetch(path, Object.assign({ credentials: "same-origin" }, opts || {}));
    let groups = [];
    let people = [];
    let selected = null;

    function qTogether(names) {
      const clean = [];
      const seen = {};
      names.forEach((n) => {
        const s = (n || "").trim();
        if (!s || seen[s]) return;
        seen[s] = true;
        clean.push(s);
      });
      if (clean.length < 2) return "";
      const pairs = [];
      for (let i = 0; i < clean.length; i++) {
        for (let j = i + 1; j < clean.length; j++) {
          pairs.push(clean[i] + "&" + clean[j]);
        }
      }
      return 'person:"' + pairs.join("|") + '"';
    }

    async function load() {
      const msg = document.getElementById("msg");
      msg.textContent = "";
      const [gR, pR] = await Promise.all([
        api("/__hub/people-groups/api/groups"),
        api("/__hub/people-groups/api/people"),
      ]);
      if (!gR.ok || !pR.ok) {
        msg.textContent = "Impossibile leggere gruppi o persone PhotoPrism (SSO o API).";
        return;
      }
      groups = (await gR.json()).groups || [];
      people = (await pR.json()).people || [];
      people.sort((a, b) => (a.name || "").localeCompare(b.name || "", "it", { sensitivity: "base" }));
      groups.sort((a, b) => (a.name || "").localeCompare(b.name || "", "it", { sensitivity: "base" }));
      render();
    }

    function render() {
      const ul = document.getElementById("groups");
      ul.innerHTML = "";
      const sortedGroups = groups.slice().sort((a, b) => (a.name || "").localeCompare(b.name || "", "it", { sensitivity: "base" }));
      sortedGroups.forEach((g) => {
        const li = document.createElement("li");
        const n = (g.personNames || []).length;
        li.innerHTML = "<strong>" + escapeHtml(g.name) + "</strong><span class='muted'>" + n + " persone</span>";
        li.style.cursor = "pointer";
        if (selected && selected.id === g.id) li.style.outline = "1px solid var(--accent)";
        li.onclick = () => { selected = g; render(); };
        ul.appendChild(li);
      });
      const title = document.getElementById("detailTitle");
      const actions = document.getElementById("actions");
      const hint = document.getElementById("hint");
      const pul = document.getElementById("people");
      const search = document.getElementById("peopleSearch");
      pul.innerHTML = "";
      if (!selected) {
        title.textContent = "Dettaglio";
        actions.hidden = true;
        hint.hidden = false;
        search.hidden = true;
        return;
      }
      title.textContent = selected.name;
      actions.hidden = false;
      hint.hidden = true;
      search.hidden = false;
      const q = (search.value || "").trim().toLocaleLowerCase("it");
      const set = new Set(selected.personUids || []);
      const sorted = people.slice().sort((a, b) => (a.name || "").localeCompare(b.name || "", "it", { sensitivity: "base" }));
      const shown = sorted.filter((p) => !q || (p.name || "").toLocaleLowerCase("it").includes(q));
      shown.forEach((p) => {
        const li = document.createElement("li");
        const on = set.has(p.uid);
        if (on) li.classList.add("on");
        li.innerHTML = "<span>" + escapeHtml(p.name || p.uid) + "</span><span class='muted'>" + (on ? "nel gruppo" : "aggiungi") + "</span>";
        li.onclick = () => togglePerson(p);
        pul.appendChild(li);
      });
      if (!people.length) {
        pul.innerHTML = "<li class='muted'>Nessuna persona riconosciuta. Abilita i volti in PhotoPrism e dai un nome ai cluster.</li>";
      } else if (!shown.length) {
        pul.innerHTML = "<li class='muted'>Nessun nome coincide con la ricerca.</li>";
      }
    }

    function escapeHtml(s) {
      return String(s).replace(/[&<>"']/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c]));
    }

    async function saveGroups() {
      const r = await api("/__hub/people-groups/api/groups", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ groups }),
      });
      if (!r.ok) {
        document.getElementById("msg").textContent = "Salvataggio gruppi fallito.";
        return;
      }
      groups = (await r.json()).groups || groups;
      if (selected) selected = groups.find((g) => g.id === selected.id) || null;
      render();
    }

    function togglePerson(p) {
      if (!selected) return;
      const uids = new Set(selected.personUids || []);
      const names = new Map();
      (selected.personUids || []).forEach((id, i) => names.set(id, (selected.personNames || [])[i] || id));
      if (uids.has(p.uid)) uids.delete(p.uid);
      else {
        uids.add(p.uid);
        names.set(p.uid, p.name || p.uid);
      }
      selected.personUids = Array.from(uids);
      selected.personNames = selected.personUids.map((id) => names.get(id) || (people.find((x) => x.uid === id) || {}).name || id);
      const idx = groups.findIndex((g) => g.id === selected.id);
      if (idx >= 0) groups[idx] = selected;
      saveGroups();
    }

    document.getElementById("create").onclick = async () => {
      const name = document.getElementById("newName").value.trim();
      if (!name) return;
      groups.push({ id: crypto.randomUUID(), name, personUids: [], personNames: [] });
      document.getElementById("newName").value = "";
      selected = groups[groups.length - 1];
      await saveGroups();
    };

    document.getElementById("openPhotos").onclick = () => {
      if (!selected) return;
      const n = (selected.personNames || []).filter(Boolean).length;
      if (n < 2) {
        document.getElementById("msg").textContent = "Servono almeno due persone nel gruppo.";
        return;
      }
      location.href = "/__hub/people-groups/photos?id=" + encodeURIComponent(selected.id);
    };

    document.getElementById("rename").onclick = async () => {
      const name = prompt("Nuovo nome", selected && selected.name || "");
      if (!name || !selected) return;
      selected.name = name.trim();
      await saveGroups();
    };

    document.getElementById("peopleSearch").addEventListener("input", () => render());

    document.getElementById("del").onclick = async () => {
      if (!selected || !confirm("Eliminare il gruppo?")) return;
      groups = groups.filter((g) => g.id !== selected.id);
      selected = null;
      await saveGroups();
    };

    load();
  </script>
</body>
</html>
"""


PHOTOS_HTML = """<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Foto di gruppo</title>
  <style>
    :root { color-scheme: dark; --bg:#12151c; --card:#1c2230; --text:#e8eef8; --muted:#8b97ab; --accent:#c9a227; }
    body { margin:0; font-family:system-ui,sans-serif; background:var(--bg); color:var(--text); }
    header { padding:1rem 1.25rem; display:flex; gap:1rem; flex-wrap:wrap; align-items:center; justify-content:space-between; }
    a { color: inherit; text-decoration: none; }
    img { width:100%; aspect-ratio:1; object-fit:cover; display:block; background:#0b0e14; }
    .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(180px,1fr)); gap:.75rem; padding:0 1.25rem 2rem; }
    figure { margin:0; background:var(--card); border-radius:10px; overflow:hidden; }
    img { width:100%; aspect-ratio:1; object-fit:cover; display:block; }
    figcaption { padding:.5rem .6rem; font-size:.8rem; color:var(--muted); }
    .err { color:#fca5a5; padding:0 1.25rem; }
  </style>
</head>
<body>
  <header>
    <div>
      <h1 id="title" style="margin:0;font-size:1.15rem">Foto di gruppo</h1>
      <p class="muted" id="sub" style="margin:.3rem 0 0;color:var(--muted)">Solo foto con almeno due persone del gruppo (non serve che ci siano tutti).</p>
    </div>
    <a href="/__hub/people-groups">Torna ai gruppi</a>
  </header>
  <p id="msg">Carico…</p>
  <div class="grid" id="grid"></div>
  <script>
    const id = new URLSearchParams(location.search).get("id") || "";
    (async function () {
      const msg = document.getElementById("msg");
      if (!id) { msg.textContent = "Gruppo mancante."; return; }
      const r = await fetch("/__hub/people-groups/api/together?id=" + encodeURIComponent(id), { credentials: "same-origin" });
      if (!r.ok) { msg.textContent = "Ricerca fallita."; return; }
      const data = await r.json();
      document.getElementById("title").textContent = data.name || "Foto di gruppo";
      const photos = data.photos || [];
      msg.textContent = photos.length ? (photos.length + " foto con almeno due persone del gruppo") : "Nessuna foto con due o più persone del gruppo insieme.";
      const grid = document.getElementById("grid");
      photos.forEach((p) => {
        const a = document.createElement("a");
        a.href = "/ui/library/browse?q=" + encodeURIComponent("uid:" + p.uid);
        const fig = document.createElement("figure");
        const img = document.createElement("img");
        img.src = "/__hub/people-groups/api/thumb?hash=" + encodeURIComponent(p.hash);
        img.alt = "";
        const cap = document.createElement("figcaption");
        cap.textContent = (p.members || []).join(", ");
        fig.appendChild(img);
        fig.appendChild(cap);
        a.appendChild(fig);
        grid.appendChild(a);
      });
    })();
  </script>
</body>
</html>
"""


def unique_names(names: list[str]) -> list[str]:
    clean: list[str] = []
    seen: set[str] = set()
    for n in names:
        s = str(n).strip() if n else ""
        if not s or s in seen:
            continue
        seen.add(s)
        clean.append(s)
    return clean


def person_search_query(names: list[str]) -> str:
    """Any group member (candidates). Together-filter is applied in Python."""
    clean = unique_names(names)
    if not clean:
        return ""
    return 'person:"' + "|".join(clean) + '"'


def group_member_hits(markers: list, uids: set[str], names: set[str]) -> list[str]:
    hits: list[str] = []
    seen: set[str] = set()
    for m in markers or []:
        if not isinstance(m, dict) or m.get("Invalid"):
            continue
        sid = str(m.get("SubjUID") or "")
        nm = str(m.get("Name") or "").strip()
        key = sid or nm
        if not key or key in seen:
            continue
        if (sid and sid in uids) or (nm and nm in names):
            seen.add(key)
            hits.append(nm or sid)
    return hits


def load_groups() -> list[dict[str, Any]]:
    if not GROUPS_PATH.is_file():
        return []
    try:
        data = json.loads(GROUPS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    groups = data.get("groups") if isinstance(data, dict) else data
    if not isinstance(groups, list):
        return []
    out: list[dict[str, Any]] = []
    for g in groups:
        if not isinstance(g, dict):
            continue
        name = str(g.get("name") or "").strip()
        if not name:
            continue
        uids = [str(x) for x in (g.get("personUids") or []) if x]
        names = [str(x) for x in (g.get("personNames") or [])]
        while len(names) < len(uids):
            names.append(uids[len(names)])
        out.append(
            {
                "id": str(g.get("id") or uuid.uuid4()),
                "name": name,
                "personUids": uids,
                "personNames": names[: len(uids)],
            }
        )
    return out


def save_groups(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    GROUPS_PATH.parent.mkdir(parents=True, exist_ok=True)
    cleaned = []
    for g in groups:
        name = str(g.get("name") or "").strip()
        if not name:
            continue
        uids = [str(x) for x in (g.get("personUids") or []) if x]
        names = [str(x) for x in (g.get("personNames") or [])]
        while len(names) < len(uids):
            names.append("")
        cleaned.append(
            {
                "id": str(g.get("id") or uuid.uuid4()),
                "name": name,
                "personUids": uids,
                "personNames": names[: len(uids)],
            }
        )
    GROUPS_PATH.write_text(
        json.dumps({"groups": cleaned}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return cleaned


def set_person_groups(
    uid: str,
    name: str,
    group_ids: list[str],
    create_name: str = "",
) -> list[dict[str, Any]]:
    uid = str(uid or "").strip()
    name = str(name or "").strip() or uid
    if not uid:
        raise ValueError("uid")
    wanted = {str(x) for x in group_ids if str(x).strip()}
    groups = load_groups()
    extra = str(create_name or "").strip()
    if extra:
        existing = next((g for g in groups if g["name"].casefold() == extra.casefold()), None)
        if existing is None:
            existing = {
                "id": str(uuid.uuid4()),
                "name": extra,
                "personUids": [],
                "personNames": [],
            }
            groups.append(existing)
        wanted.add(existing["id"])
    for g in groups:
        uids = list(g.get("personUids") or [])
        names = list(g.get("personNames") or [])
        while len(names) < len(uids):
            names.append("")
        in_g = uid in uids
        should = g["id"] in wanted
        if should and not in_g:
            uids.append(uid)
            names.append(name)
        elif not should and in_g:
            i = uids.index(uid)
            uids.pop(i)
            if i < len(names):
                names.pop(i)
        elif should and in_g and name:
            i = uids.index(uid)
            if i < len(names):
                names[i] = name
        g["personUids"] = uids
        g["personNames"] = names[: len(uids)]
    return save_groups(groups)


def inject_nav(html: bytes, content_type: str) -> bytes:
    ct = (content_type or "").lower()
    if "text/html" not in ct:
        return html
    if INJECT_MARK.encode("utf-8") in html:
        return html
    try:
        text = html.decode("utf-8")
    except UnicodeDecodeError:
        return html
    if re.search(r"</body>", text, re.I):
        text = re.sub(r"</body>", lambda _m: inject_fragment() + "</body>", text, count=1, flags=re.I)
        return text.encode("utf-8")
    return (text + inject_fragment()).encode("utf-8")


def _people_from_subjects(payload: Any) -> list[dict[str, str]]:
    rows = payload if isinstance(payload, list) else []
    if isinstance(payload, dict):
        rows = payload.get("subjects") or payload.get("data") or []
    out: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        uid = str(row.get("UID") or row.get("uid") or "")
        name = str(row.get("Name") or row.get("name") or "").strip()
        subj_type = str(row.get("Type") or row.get("type") or "person")
        if not uid or subj_type not in ("", "person"):
            continue
        if not name:
            continue
        out.append({"uid": uid, "name": name})
    out.sort(key=lambda p: p["name"].lower())
    return out


def inject_fragment() -> str:
    return INJECT_PATH.read_text(encoding="utf-8")


def photos_with_two_members(
    get_json: Callable[..., tuple[int, Any]], group: dict[str, Any]
) -> list[dict[str, Any]]:
    names = unique_names(group.get("personNames") or [])
    uids = {str(x) for x in (group.get("personUids") or []) if x}
    nameset = set(names)
    query = person_search_query(names)
    if len(names) < 2 or not query:
        return []
    found: list[dict[str, Any]] = []
    offset = 0
    while offset < 1500:
        status, batch = get_json(
            "/api/v1/photos",
            {"q": query, "count": "100", "offset": str(offset), "merged": "true"},
        )
        if status != 200 or not isinstance(batch, list) or not batch:
            break
        found.extend(batch)
        if len(batch) < 100:
            break
        offset += 100

    def one(photo: dict[str, Any]) -> dict[str, Any] | None:
        uid = str(photo.get("UID") or "")
        if not uid:
            return None
        status, detail = get_json(f"/api/v1/photos/{uid}", None)
        if status != 200 or not isinstance(detail, dict):
            return None
        markers: list = []
        for item in detail.get("Files") or []:
            if isinstance(item, dict):
                markers.extend(item.get("Markers") or [])
        members = group_member_hits(markers, uids, nameset)
        if len(members) < 2:
            return None
        return {
            "uid": uid,
            "hash": str(photo.get("Hash") or ""),
            "title": str(photo.get("Title") or ""),
            "members": members,
        }

    with ThreadPoolExecutor(max_workers=2) as pool:
        scored = list(pool.map(lambda item: one(item) if isinstance(item, dict) else None, found))
    return [x for x in scored if x]


def _json_bytes(payload: dict[str, Any], status: int = 200) -> tuple[int, str, bytes]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return status, "application/json; charset=utf-8", body


def _html(page: str) -> tuple[int, str, bytes]:
    return 200, "text/html; charset=utf-8", page.encode("utf-8")


def _read_json(body: bytes) -> Any:
    if not body:
        raise ValueError("json")
    return json.loads(body.decode("utf-8"))


def dispatch(
    method: str,
    path: str,
    query: str,
    body: bytes,
    get_json: Callable[..., tuple[int, Any]],
) -> tuple[int, str, bytes]:
    path = path.rstrip("/") or "/"
    params = {key: values[-1] for key, values in parse_qs(query).items()}
    if path == "/__hub/people-groups" and method == "GET":
        return _html(PAGE_HTML)
    if path == "/__hub/people-groups/photos" and method == "GET":
        return _html(PHOTOS_HTML)
    if path == "/__hub/people-groups/api/groups":
        if method == "GET":
            return _json_bytes({"groups": load_groups()})
        if method == "PUT":
            try:
                payload = _read_json(body)
            except (UnicodeError, ValueError, json.JSONDecodeError):
                return _json_bytes({"error": "invalid_json"}, 400)
            groups = payload.get("groups") if isinstance(payload, dict) else None
            if not isinstance(groups, list):
                return _json_bytes({"error": "groups_required"}, 400)
            return _json_bytes({"groups": save_groups(groups)})
        return _json_bytes({"error": "method"}, 405)
    if path == "/__hub/people-groups/api/membership" and method == "POST":
        try:
            payload = _read_json(body)
        except (UnicodeError, ValueError, json.JSONDecodeError):
            return _json_bytes({"error": "invalid_json"}, 400)
        if not isinstance(payload, dict):
            return _json_bytes({"error": "invalid_json"}, 400)
        uid = str(payload.get("uid") or "").strip()
        name = str(payload.get("name") or "").strip()
        create_name = str(payload.get("createName") or "").strip()
        raw_ids = payload.get("groupIds") or []
        if not isinstance(raw_ids, list):
            return _json_bytes({"error": "group_ids"}, 400)
        group_ids = [str(item) for item in raw_ids if item]
        try:
            groups = set_person_groups(uid, name, group_ids, create_name)
        except ValueError:
            return _json_bytes({"error": "uid_required"}, 400)
        return _json_bytes({"groups": groups})
    if path == "/__hub/people-groups/api/people" and method == "GET":
        status, payload = get_json("/api/v1/subjects", {"count": "10000", "type": "person"})
        if status != 200:
            return _json_bytes({"people": []})
        return _json_bytes({"people": _people_from_subjects(payload)})
    if path == "/__hub/people-groups/api/together" and method == "GET":
        gid = (params.get("id") or "").strip()
        group = next((item for item in load_groups() if item["id"] == gid), None)
        if group is None:
            return _json_bytes({"error": "group_not_found"}, 404)
        photos = photos_with_two_members(get_json, group)
        return _json_bytes({"name": group["name"], "photos": photos})
    return _json_bytes({"error": "not_found"}, 404)
