"""把 exports/daily/digests/*.md 渲染成单页 HTML。"""
import html
import os
import re
import glob

SRC_DIR = "exports/daily/digests"
OUT = "exports/daily/view.html"

PERSON_CLASS = [
    (("面包", "himself65"), "p-a"),
    (("solo",), "p-b"),
    (("Frank", "孔子"), "p-c"),
    (("黄哥",), "p-d"),
]


def person_class(label):
    for keys, cls in PERSON_CLASS:
        if any(k.lower() in label.lower() for k in keys):
            return cls
    return "p-n"


def inline(text):
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<q>\1</q>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    return text


FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:\.(morning|afternoon|night|day))?\.md$")


def parse(path):
    note, cats, cur_cat, cur_tic = [], [], None, None
    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip()
        if line.startswith("# ") or line.strip() == "---":
            continue
        if line.startswith("> "):
            note.append(line[2:].strip()); continue
        if line.startswith("## "):
            cur_cat = {"name": line[3:].strip(), "tickers": []}
            cats.append(cur_cat); cur_tic = None; continue
        if line.startswith("### "):
            if cur_cat is None:
                cur_cat = {"name": "", "tickers": []}; cats.append(cur_cat)
            cur_tic = {"name": line[4:].strip(), "market": "", "items": []}
            cur_cat["tickers"].append(cur_tic); continue
        if not line.strip():
            continue
        # 分类下直接挂条目（如"Frank（转述）""未能明确归属"）
        if cur_tic is None and cur_cat is not None:
            cur_tic = {"name": "", "market": "", "items": []}
            cur_cat["tickers"].append(cur_tic)
        if cur_tic is None:
            continue
        if line.lstrip().startswith("*盘面*"):
            cur_tic["market"] = re.sub(r"^\*盘面\*[：:]\s*", "", line.strip()); continue
        if line.lstrip().startswith("- "):
            body = line.lstrip()[2:]
            m = re.match(r"\*\*([^*]+)\*\*[：:]?\s*(.*)$", body)
            if m:
                cur_tic["items"].append({"who": m.group(1), "text": m.group(2)})
            else:
                cur_tic["items"].append({"who": "", "text": body})
        elif cur_tic["items"]:
            cur_tic["items"][-1]["text"] += " " + line.strip()
        else:
            cur_tic["market"] += (" " if cur_tic["market"] else "") + line.strip()
    return {"note": " ".join(note), "cats": cats}


SESSION_LABEL = {
    "morning": "上午盘（06:00–12:00）",
    "afternoon": "下午盘（12:00–18:00）",
    "night": "夜盘（18:00–次日06:00）",
    "day": "日盘（06:00–18:00，旧格式）",
}
SESSION_ORDER = {"morning": 0, "afternoon": 1, "night": 2, "day": 0}


def render_chapter(chap):
    """一个 chapter dict（note+cats）渲染成正文片段，不含外层 <section>。"""
    out = []
    if chap["note"]:
        out.append(f'<p class="daynote">{inline(chap["note"])}</p>')
    for cat in chap["cats"]:
        if cat["name"]:
            out.append(f'<h2 class="cat">{html.escape(cat["name"])}</h2>')
        for t in cat["tickers"]:
            if not t["items"] and not t["market"]:
                continue
            out.append('<article class="tsec">')
            if t["name"]:
                m = re.match(r"^([A-Za-z0-9/\.\-\+ ]+?)\s*(（.*）|\(.*\))?$", t["name"])
                sym = (m.group(1).strip() if m else t["name"])
                rest = (m.group(2) or "") if m else ""
                out.append(f'<h3 class="thead"><span class="sym">{html.escape(sym)}</span>'
                           + (f'<span class="rest">{html.escape(rest)}</span>' if rest else "")
                           + "</h3>")
            if t["market"]:
                out.append(f'<p class="mkt">{inline(t["market"])}</p>')
            for it in t["items"]:
                cls = person_class(it["who"]) if it["who"] else "p-n"
                who = f'<span class="who">{html.escape(it["who"])}</span>' if it["who"] else ""
                out.append(f'<div class="row {cls}">{who}<span class="txt">{inline(it["text"])}</span></div>')
            out.append("</article>")
    return "".join(out)


def render_day(date, chapters):
    """chapters: [(session_or_None, chapter_dict), ...]，已按 day 在前 night 在后排好序。"""
    out = [f'<section class="day" id="d-{date}">']
    for session, chap in chapters:
        if session:
            out.append(f'<h2 class="session">{SESSION_LABEL[session]}</h2>')
        out.append(render_chapter(chap))
    out.append("</section>")
    return "".join(out)


def main():
    by_date = {}
    for path in sorted(glob.glob(os.path.join(SRC_DIR, "*.md"))):
        fname = os.path.basename(path)
        m = FILENAME_RE.match(fname)
        if not m:
            print(f"跳过不认识的文件名: {fname}")
            continue
        date, session = m.group(1), m.group(2)  # session is None for 整天模式
        by_date.setdefault(date, []).append((session, parse(path)))

    if not by_date:
        raise SystemExit("没有找到 digests")

    dates = sorted(by_date)
    for date in dates:
        by_date[date].sort(key=lambda x: SESSION_ORDER.get(x[0], -1))

    tabs = "".join(f'<button class="tab" data-target="d-{d}">{d[5:]}</button>' for d in dates)
    body = "".join(render_day(d, by_date[d]) for d in dates)
    tickers = {
        t["name"]
        for d in dates
        for _, chap in by_date[d]
        for c in chap["cats"]
        for t in c["tickers"]
        if t["name"]
    }
    tpl = (TEMPLATE.replace("{{TABS}}", tabs).replace("{{DAYS}}", body)
           .replace("{{RANGE}}", f'{dates[0]} — {dates[-1]}')
           .replace("{{NDAYS}}", str(len(dates))).replace("{{NTICKERS}}", str(len(tickers))))
    open(OUT, "w", encoding="utf-8").write(tpl)
    print(f"wrote {OUT} ({os.path.getsize(OUT)/1024:.0f} KB), {len(dates)} days, {len(tickers)} tickers")


TEMPLATE = r"""<title>面包tradingroom 观点看板</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
:root{
  --bg:#f4f5f7; --surface:#ffffff; --line:#dfe2e7; --line-soft:#eaecf0;
  --ink:#14181d; --ink-2:#3d444e; --muted:#6b7280;
  --a:#9a4f2b; --a-bg:#faf2ee; --b:#1f6470; --b-bg:#eef5f6;
  --c:#5b4b8a; --c-bg:#f2f0f8; --d:#5c6b2f; --d-bg:#f3f5ea;
  --chip:#eef0f3; --code:#f2f3f5;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --bg:#14171b; --surface:#1b1f24; --line:#2c323a; --line-soft:#242a31;
    --ink:#e8eaed; --ink-2:#c2c7cf; --muted:#8b939f;
    --a:#e09a72; --a-bg:#241a15; --b:#79c2cd; --b-bg:#152225;
    --c:#b3a5dd; --c-bg:#1e1b2a; --d:#b6c47d; --d-bg:#1e2116;
    --chip:#242a31; --code:#232930;
  }
}
:root[data-theme="dark"]{
  --bg:#14171b; --surface:#1b1f24; --line:#2c323a; --line-soft:#242a31;
  --ink:#e8eaed; --ink-2:#c2c7cf; --muted:#8b939f;
  --a:#e09a72; --a-bg:#241a15; --b:#79c2cd; --b-bg:#152225;
  --c:#b3a5dd; --c-bg:#1e1b2a; --d:#b6c47d; --d-bg:#1e2116;
  --chip:#242a31; --code:#232930;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:"IBM Plex Sans",-apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB",sans-serif;
  font-size:15px;line-height:1.7;-webkit-font-smoothing:antialiased}
.wrap{max-width:900px;margin:0 auto;padding:0 20px}
header{border-bottom:1px solid var(--line);background:var(--surface)}
.hd{padding:24px 0 16px}
h1{margin:0;font-size:19px;font-weight:600}
.meta{margin:5px 0 0;color:var(--muted);font-size:13px;font-family:"IBM Plex Mono",monospace}
nav{position:sticky;top:0;z-index:10;background:var(--surface);border-bottom:1px solid var(--line)}
.tabs{display:flex;gap:4px;overflow-x:auto;padding:9px 0}
.tab{flex:0 0 auto;border:1px solid var(--line);background:transparent;color:var(--ink-2);
  font-family:"IBM Plex Mono",monospace;font-size:13px;padding:5px 11px;border-radius:3px;cursor:pointer}
.tab:hover{border-color:var(--muted)}
.tab:focus-visible{outline:2px solid var(--a);outline-offset:1px}
.tab[aria-current="true"]{background:var(--ink);color:var(--surface);border-color:var(--ink)}
main{padding:20px 0 80px}
.day{display:none}.day.on{display:block}
.daynote{margin:0 0 20px;padding:12px 15px;background:var(--surface);border:1px solid var(--line-soft);
  border-left:2px solid var(--muted);border-radius:3px;color:var(--ink-2);font-size:14px}
.cat{margin:26px 0 10px;font-size:12px;font-weight:600;letter-spacing:.12em;color:var(--muted);
  text-transform:uppercase;font-family:"IBM Plex Mono",monospace}
.session{margin:28px 0 4px;padding-top:20px;border-top:1px solid var(--line);
  font-size:15px;font-weight:600;color:var(--ink)}
.session:first-child{margin-top:0;padding-top:0;border-top:none}
.tsec{background:var(--surface);border:1px solid var(--line-soft);border-radius:4px;
  padding:15px 17px;margin:0 0 11px}
.thead{margin:0 0 9px;font-size:15px;font-weight:600;display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.sym{font-family:"IBM Plex Mono",monospace;background:var(--chip);padding:2px 8px;border-radius:3px}
.rest{color:var(--muted);font-weight:400;font-size:13.5px}
.mkt{margin:0 0 11px;color:var(--muted);font-size:13.5px;font-style:italic}
.row{display:flex;gap:9px;padding:7px 0 7px 10px;border-left:2px solid var(--line);margin-bottom:5px;
  font-size:14px;align-items:baseline}
.row:last-child{margin-bottom:0}
.who{flex:0 0 auto;font-family:"IBM Plex Mono",monospace;font-size:11.5px;font-weight:500;
  padding:1px 7px;border-radius:3px;white-space:nowrap}
.txt{min-width:0}
.p-a{border-left-color:var(--a)} .p-a .who{background:var(--a-bg);color:var(--a)}
.p-b{border-left-color:var(--b)} .p-b .who{background:var(--b-bg);color:var(--b)}
.p-c{border-left-color:var(--c)} .p-c .who{background:var(--c-bg);color:var(--c)}
.p-d{border-left-color:var(--d)} .p-d .who{background:var(--d-bg);color:var(--d)}
.p-n .who{background:var(--chip);color:var(--muted)}
q{font-family:"IBM Plex Mono",monospace;font-size:.88em;background:var(--code);padding:1px 5px;
  border-radius:3px;overflow-wrap:anywhere}
q::before,q::after{content:""}
strong{font-weight:600}
footer{border-top:1px solid var(--line);color:var(--muted);font-size:12.5px;padding:16px 0 30px;
  font-family:"IBM Plex Mono",monospace}
</style>
<header><div class="wrap hd">
  <h1>面包tradingroom 观点看板</h1>
  <p class="meta">{{RANGE}} · 美西时间 · {{NDAYS}} 天 · {{NTICKERS}} 个标的 · 面包 / solo / Frank / 黄哥</p>
</div></header>
<nav><div class="wrap"><div class="tabs" role="tablist">{{TABS}}</div></div></nav>
<main class="wrap">{{DAYS}}</main>
<footer class="wrap">数据源：Discord 面包tradingroom · 按美西自然日切分 · Frank 与黄哥的观点多为他人转述，已在条目中标注</footer>
<script>
(function(){
  var tabs=[].slice.call(document.querySelectorAll(".tab"));
  var days=[].slice.call(document.querySelectorAll(".day"));
  function show(id){
    days.forEach(function(d){d.classList.toggle("on",d.id===id)});
    tabs.forEach(function(t){t.setAttribute("aria-current",String(t.dataset.target===id))});
    try{localStorage.setItem("btr-day",id)}catch(e){}
  }
  tabs.forEach(function(t){t.addEventListener("click",function(){show(t.dataset.target);window.scrollTo(0,0)})});
  var latest=days[days.length-1].id,saved=null,seen=null;
  try{saved=localStorage.getItem("btr-day");seen=localStorage.getItem("btr-latest")}catch(e){}
  try{localStorage.setItem("btr-latest",latest)}catch(e){}
  var ok=saved&&seen===latest&&days.some(function(d){return d.id===saved});
  show(ok?saved:latest);
})();
</script>
"""

if __name__ == "__main__":
    main()
