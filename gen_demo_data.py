#!/usr/bin/env python3
"""Generate a fully synthetic demo graph + curated queries for the standalone
cortex-demo. No vector DB, no embeddings, no real data; invented showcase notes.
Output shape matches the old /api/graph and /api/search contracts exactly."""
import json, math, random, time, hashlib

random.seed(1312)  # deterministic builds
NOW = time.time()

PALETTE = {
    "demo_research": "#00e5ff",
    "demo_infra":    "#a259ff",
    "demo_ideas":    "#39ff14",
    "demo_journal":  "#ffd700",
}

# --- themed content pools (homelab / AI / SRE flavoured, 100% invented) ---
THEMES = {
  "demo_research": {
    "center": (-60, 35), "n": 74,
    "subjects": [
      ("embedding drift", ["embeddings","drift","eval","vectors"],
       "Tracked how the {model} embedding space rotates after a re-index; cosine to the old centroid drops ~{p}% over a month."),
      ("retrieval latency", ["retrieval","latency","rag","perf"],
       "p95 retrieval latency sat at {ms}ms; most of it was the rerank pass, not the ANN search itself."),
      ("semantic cache", ["cache","retrieval","rag","cost"],
       "A query-embedding cache with a {p}% hit rate cut redundant vector searches and shaved the LLM bill."),
      ("reranking", ["rerank","retrieval","quality"],
       "Cross-encoder rerank lifted top-3 relevance noticeably but added {ms}ms; worth it only above k={k}."),
      ("vector quantization", ["quantization","vectors","memory","perf"],
       "Scalar quantization shrank the index {p}% with almost no recall loss; product quantization was a step too far."),
      ("UMAP projection", ["umap","projection","viz","clustering"],
       "n_neighbors={k}, min_dist={md} gave the cleanest 3-region separation for the memory map."),
      ("LLM distillation", ["distillation","llm","small-model"],
       "Distilling the judge into a {b}B model kept ~{p}% of agreement at a fraction of the latency."),
      ("context window", ["context","llm","rag"],
       "Past ~{k}k tokens, stuffing more retrieved chunks hurt answer quality; lost-in-the-middle is real."),
      ("hybrid search", ["hybrid","bm25","retrieval"],
       "BM25 + dense fusion beat either alone; the win was almost entirely on rare-term queries."),
      ("eval harness", ["eval","rag","quality","ci"],
       "Built a small golden-set harness so retrieval changes get a relevance delta before they ship."),
    ],
  },
  "demo_infra": {
    "center": (55, 40), "n": 76,
    "subjects": [
      ("Podman quadlet", ["podman","quadlet","systemd","containers"],
       "Migrated the service to a Quadlet; systemctl restart now recreates from the new image, podman restart didn't."),
      ("Caddy ingress", ["caddy","tls","ingress","reverse-proxy"],
       "Single Caddy front terminates TLS for every subdomain; the auth bypass paths needed an explicit matcher."),
      ("Prometheus scrape", ["prometheus","metrics","observability"],
       "Added a scrape job for the exporter; the gotcha was the target port, not the path."),
      ("WireGuard tunnel", ["wireguard","vpn","network","tunnel"],
       "Kill-switch holds when the tunnel drops; no traffic leaks while it re-dials a new endpoint."),
      ("GPU fan curve", ["gpu","nvidia","fans","thermal"],
       "NVML daemon drives the fan curve with a {s}s cooldown; capped power at {w}W to dodge the firmware override."),
      ("PXE boot", ["pxe","provisioning","dr","netboot"],
       "Compute-served PXE over the crossover link rebuilds the kiosk from preseed in one pass."),
      ("backup retention", ["backup","retention","nas","cron"],
       "Keep-8 sliding window; a mid-run abort once skipped the prune and the count drifted to {k}."),
      ("fail2ban jail", ["fail2ban","security","ssh","hardening"],
       "Custom filter on the gateway; the default sshd jail was a placebo with password auth off."),
      ("NVMe LVM", ["lvm","storage","disk","nvme"],
       "Carved /var onto its own LV after a runaway log filled root; now it's {p}% and isolated."),
      ("ntfy alert", ["ntfy","alerting","push","ops"],
       "Routed vmalert through an ntfy relay so a flapping target pings the phone, not an inbox."),
    ],
  },
  "demo_ideas": {
    "center": (-15, -55), "n": 58,
    "subjects": [
      ("gesture UI", ["gesture","ui","webcam","interaction"],
       "Hand-tracking as the only input for a graph explorer; pinch to target, two fists to zoom."),
      ("memory graph viz", ["viz","graph","memory","3d"],
       "Project the note embeddings to 3D and let people walk the clusters instead of reading a list."),
      ("self-hosted analytics", ["analytics","privacy","selfhost"],
       "A cookieless page-view beacon that's just a counter; no third party, no fingerprint."),
      ("edge cache demo", ["cdn","edge","resilience"],
       "Ship a showcase fully static so a traffic spike can't dent it; origin barely involved."),
      ("voice journal", ["voice","journal","whisper","capture"],
       "Dictate a daily note, transcribe on-device, auto-tag it into the right region of the map."),
      ("automation bot", ["automation","bot","ops","glue"],
       "A small agent that watches alerts and proposes the fix as a one-click runbook step."),
      ("portfolio site", ["portfolio","showcase","web"],
       "One page that *is* the demo; open it from a post and you're already inside the thing."),
      ("offline-first notes", ["offline","local-first","sync"],
       "Notes that live in a flat file first and sync when they can, never the other way round."),
    ],
  },
  "demo_journal": {
    "center": (25, -40), "n": 52,
    "subjects": [
      ("shipped", ["shipped","log","win"],
       "Shipped the {thing} today; smaller than planned but it's live and it works."),
      ("debugged", ["debug","fix","log","ops"],
       "Spent the morning chasing a {thing} that turned out to be a stale clone, not real drift."),
      ("learned", ["learned","note-to-self","insight"],
       "Learned the hard way that host-side rate-limits do nothing against a volumetric flood."),
      ("decision", ["decision","tradeoff","log"],
       "Decided to keep the personal plane direct and only push the public demo behind an edge."),
      ("retro", ["retro","reflection","log"],
       "Looking back at the week: the {thing} migration was the right call, the timing wasn't."),
      ("idea-seed", ["idea","seed","journal"],
       "Random thought before sleep: the graph could double as the nav for the whole site."),
      ("tired-but-good", ["log","mood","win"],
       "Long day on the {thing}. Tired, but the lab is quieter than it's been in weeks."),
    ],
  },
}

MODELS = ["MiniLM","bge-small","e5-base","gte","embeddinggemma"]
THINGS = ["backup script","VPN failover","fan curve","ingress rewrite","screener","graph build","NAS sync"]

def jitter_pt(cx, cy, spread):
    # gaussian blob + occasional sub-cluster offset
    ox, oy = random.choice([(0,0),(0,0),(18,-12),(-14,16),(10,20)])
    return (cx+ox+random.gauss(0,spread), cy+oy+random.gauss(0,spread))

def mk_id(coll, i):
    return hashlib.md5(f"{coll}-{i}-cortexdemo".encode()).hexdigest()[:12]

points, links = [], []
by_tag = {}

for coll, spec in THEMES.items():
    cx, cy = spec["center"]
    for i in range(spec["n"]):
        subj, tags, tmpl = random.choice(spec["subjects"])
        x, y = jitter_pt(cx, cy, 13)
        z = random.gauss(0, 12)
        preview = tmpl.format(
            model=random.choice(MODELS), thing=random.choice(THINGS),
            p=random.randint(8,46), ms=random.randint(40,420), k=random.randint(3,16),
            md=round(random.uniform(0.05,0.4),2), b=random.choice([1,3,7,8]),
            s=random.randint(5,20), w=random.choice([150,165,175]),
        )
        imp = round(min(1.0, max(0.25, random.betavariate(2,3)+0.15)), 2)
        age = round(random.uniform(0.2, 120), 1)
        ntags = [subj.split()[0].lower()] + random.sample(tags, k=min(len(tags), random.randint(2,3)))
        ntags = list(dict.fromkeys(ntags))[:4]
        pid = mk_id(coll, i)
        # only the fields the front-end actually reads (trimmed: no z/color/recent/age_days)
        pt = {
            "id": pid, "collection": coll, "x": round(x,1), "y": round(y,1),
            "importance": imp, "tags": ntags, "preview": preview, "type": subj,
        }
        points.append(pt)
        for t in ntags:
            by_tag.setdefault(t, []).append(pid)

# --- links: connect points that share a tag (cap per tag), + a few cross bridges ---
idset = {p["id"] for p in points}
seen = set()
for t, ids in by_tag.items():
    random.shuffle(ids)
    for a, b in zip(ids, ids[1:]):
        if a == b: continue
        key = tuple(sorted((a,b)))
        if key in seen: continue
        seen.add(key)
        links.append({"source": a, "target": b, "weight": round(random.uniform(0.4,1.0),2)})
        if len([1 for l in links]) > 0 and random.random() < 0.6:
            continue  # thin it out a bit
# trim to a reasonable mesh
random.shuffle(links)
links = links[:420]

counts = {}
for p in points:
    counts[p["collection"]] = counts.get(p["collection"], 0) + 1

# trimmed graph: only counts + points + links (front-end reads nothing else)
graph = {"counts": counts, "points": points, "links": links}

# --- curated queries: pick nodes by keyword match, freeze with plausible scores ---
CURATED = [
  ("make retrieval faster",        ["latency","cache","rerank","quantization","retrieval","perf"]),
  ("self-hosted observability",    ["prometheus","metrics","observability","ntfy","alerting"]),
  ("ideas for a portfolio demo",   ["gesture","viz","portfolio","showcase","edge","3d"]),
  ("what broke and how I fixed it",["debug","fix","backup","drift","ops"]),
  ("embeddings and vector search", ["embeddings","vectors","retrieval","hybrid","umap"]),
  ("keep the home lab resilient",  ["backup","wireguard","vpn","retention","security","thermal"]),
  ("running LLMs locally on a GPU", ["gpu","nvidia","distillation","quantization","thermal"]),
  ("things I learned this week",   ["learned","retro","insight","decision","log"]),
]

def score_node(p, kws):
    hay = (p["preview"] + " " + " ".join(p["tags"]) + " " + p["type"] + " " + p["collection"]).lower()
    s = sum(1.0 for k in kws if k in hay)
    s += 0.3 * p["importance"]
    return s

queries = []
for q, kws in CURATED:
    scored = sorted(((score_node(p,kws), p) for p in points), key=lambda t: t[0], reverse=True)
    top = [p for s,p in scored if s > 0][:9]
    hits = []
    for rank, p in enumerate(top):
        sc = round(max(0.52, 0.93 - rank*0.045 - random.uniform(0,0.02)), 3)
        hits.append({"id": p["id"], "collection": p["collection"], "score": sc, "preview": p["preview"]})
    queries.append({"query": q, "hits": hits})

with open("graph.json","w") as f: json.dump(graph, f, separators=(",",":"))
with open("queries.json","w") as f: json.dump(queries, f, separators=(",",":"))

print(f"points={len(points)} links={len(links)} counts={counts}")
print(f"queries={len(queries)} avg_hits={sum(len(q['hits']) for q in queries)/len(queries):.1f}")
for q in queries: print(f"  - {q['query']:32s} -> {len(q['hits'])} hits, top={q['hits'][0]['score'] if q['hits'] else '-'}")
