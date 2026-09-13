"""共享的单条消息清洗逻辑，被 etl.py（整天切分）和 etl_chapter.py（单章节）复用。"""
import re


def build_id_to_name(msgs):
    id_to_name = {}
    for m in msgs:
        a = m["author"]
        id_to_name[a["id"]] = a.get("nickname") or a["name"]
    return id_to_name


_MENTION_RE = re.compile(r"<@!?(\d+)>")


def clean_content(m, id_to_name):
    text = m["content"] or ""

    def repl(match):
        uid = match.group(1)
        return "@" + id_to_name.get(uid, uid)

    text = _MENTION_RE.sub(repl, text)
    text = re.sub(r"<#\d+>", "[频道]", text)
    text = re.sub(r"\s+\n", "\n", text).strip()

    extras = []
    for att in m.get("attachments", []):
        fname = att.get("fileName", "attachment")
        extras.append(f"[附件:{fname}]")
    for emb in m.get("embeds", []):
        title = emb.get("title") or emb.get("url") or "embed"
        extras.append(f"[embed:{title}]")
    if extras:
        text = (text + " " if text else "") + " ".join(extras)
    return text
