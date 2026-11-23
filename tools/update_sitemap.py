#!/usr/bin/env python3
"""サイトマップ(asuka-sitemap.xml)とllms.txtの自動更新。標準ライブラリのみ。

- 新しいページ  : asuka-sitemap.xml に追加（lastmod=今日・日本時間）
- 変更したページ: --changed で渡されたファイルだけ lastmod を今日に更新
- 削除したページ: サイトマップからは消さず、ログで報告するだけ
- llms.txt      : 「詳細ページは○件」の件数だけ更新
- 書き込み前にXML構文を検証し、失敗したら何も書かない
"""
import argparse, datetime, os, re, sys
import xml.etree.ElementTree as ET

BASE = "https://asuka-travel-guide.github.io/"
SITEMAP = "asuka-sitemap.xml"
LLMS = "llms.txt"
EXCLUDE_ROOT = {"404.html"}


def is_excluded(rel):
    name = os.path.basename(rel)
    return rel in EXCLUDE_ROOT or name.startswith("google")


def list_pages(root):
    pages = []
    for n in os.listdir(root):
        if n.endswith(".html") and os.path.isfile(os.path.join(root, n)):
            if not is_excluded(n):
                pages.append(n)
    sp = os.path.join(root, "spots")
    if os.path.isdir(sp):
        for n in os.listdir(sp):
            if n.endswith(".html"):
                pages.append("spots/" + n)
    return pages


def rel_to_url(rel):
    return BASE if rel == "index.html" else BASE + rel


def url_to_rel(url):
    if url == BASE:
        return "index.html"
    return url[len(BASE):] if url.startswith(BASE) else None


def read(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-8")


def write(path, text):
    with open(path, "wb") as f:
        f.write(text.encode("utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--changed", default="", help="変更ファイルの一覧（改行区切りのファイル）")
    ap.add_argument("--today", default="")
    a = ap.parse_args()
    root = a.root

    jst = datetime.timezone(datetime.timedelta(hours=9))
    today = a.today or datetime.datetime.now(jst).strftime("%Y-%m-%d")

    changed = set()
    if a.changed and os.path.isfile(a.changed):
        changed = {l.strip() for l in read(a.changed).splitlines() if l.strip()}

    sm_path = os.path.join(root, SITEMAP)
    sm = read(sm_path)
    nl = "\r\n" if "\r\n" in sm else "\n"
    sm = sm.replace("\r\n", "\n")

    block_re = re.compile(r"  <url>\n.*?</url>\n", re.S)
    blocks = block_re.findall(sm)
    head = sm[: sm.index(blocks[0])]
    tail = sm[sm.rindex(blocks[-1]) + len(blocks[-1]):]

    entries = []  # [rel, text]
    for b in blocks:
        m = re.search(r"<loc>(.*?)</loc>", b)
        entries.append([url_to_rel(m.group(1).strip()) if m else None, b])
    known = {e[0] for e in entries}

    pages = list_pages(root)
    log = []

    # 1) lastmod 更新（変更されたページのみ）
    for e in entries:
        if e[0] in changed and e[0] in pages:
            new = re.sub(r"<lastmod>.*?</lastmod>", "<lastmod>%s</lastmod>" % today, e[1])
            if new != e[1]:
                e[1] = new
                log.append("lastmod更新: " + e[0])

    # 2) 新しいページの追加
    def block(rel):
        return "  <url>\n    <loc>%s</loc>\n    <lastmod>%s</lastmod>\n  </url>\n" % (rel_to_url(rel), today)

    for rel in sorted(p for p in pages if p not in known):
        new = [rel, block(rel)]
        if rel.startswith("spots/"):
            # spots/ の中で名前順の位置に入れる
            idx = len(entries)
            for i, e in enumerate(entries):
                if e[0] and e[0].startswith("spots/") and e[0] > rel:
                    idx = i
                    break
            entries.insert(idx, new)
        else:
            # ルートのページは最初の spots/ の手前
            idx = next((i for i, e in enumerate(entries) if e[0] and e[0].startswith("spots/")), len(entries))
            entries.insert(idx, new)
        log.append("追加: " + rel)

    # 3) 削除されたページは報告のみ
    for e in entries:
        if e[0] and e[0] not in pages and not is_excluded(e[0]):
            log.append("【要確認】ファイルが無いのにサイトマップに残っています（自動では消しません）: " + e[0])

    new_sm = head + "".join(e[1] for e in entries) + tail

    # 4) 検証（失敗したら何も書かない）
    try:
        tree = ET.fromstring(new_sm.encode("utf-8"))
    except ET.ParseError as ex:
        print("ERROR: サイトマップのXML検証に失敗しました。何も書き込みません: %s" % ex)
        return 1
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    locs = [u.find(ns + "loc").text for u in tree.findall(ns + "url")]
    if len(locs) != len(set(locs)):
        print("ERROR: サイトマップにURLの重複があります。何も書き込みません。")
        return 1

    # 5) llms.txt の件数
    llms_path = os.path.join(root, LLMS)
    llms_new = None
    if os.path.isfile(llms_path):
        llms = read(llms_path)
        count = len([p for p in pages if p.startswith("spots/")])
        new_llms = re.sub(r"(詳細ページは)\d+(件)", r"\g<1>%d\g<2>" % count, llms)
        if new_llms != llms:
            llms_new = new_llms
            log.append("llms.txt: 詳細ページ件数を %d件 に更新" % count)

    # ルートに新ページがあれば、llms.txt・sitemap.html・トップは手動と知らせる
    for l in log:
        if l.startswith("追加: ") and "/" not in l[4:]:
            log.append("【手動】%s は llms.txt・sitemap.html・ヘッダー等への掲載を確認してください" % l[4:])

    if new_sm.replace("\n", nl) != read(sm_path):
        write(sm_path, new_sm.replace("\n", nl))
    if llms_new is not None:
        write(llms_path, llms_new)

    print("\n".join(log) if log else "更新なし")
    return 0


if __name__ == "__main__":
    sys.exit(main())
