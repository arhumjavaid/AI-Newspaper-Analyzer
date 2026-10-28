"""Download news pages and extract headline + lead paragraphs (verbatim) to JSONL."""
import hashlib, html, json, re, subprocess, sys
from html.parser import HTMLParser
from pathlib import Path

urls_file, raw_dir, out_file = map(Path, sys.argv[1:4])
raw_dir.mkdir(parents=True, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
SKIP = re.compile(r"follow us|subscribe|copyright|all rights reserved|whatsapp|download the app|read more|also read|comments are moderated|published in dawn|for the latest news", re.I)

class P(HTMLParser):
    def __init__(self):
        super().__init__(); self.title=None; self.paras=[]; self._in=0; self._buf=[]; self._skip=0
    def handle_starttag(self, tag, a):
        a=dict(a)
        if tag=="meta" and a.get("property")=="og:title" and not self.title: self.title=a.get("content")
        if tag in ("script","style","aside","figure","nav","footer"): self._skip+=1
        if tag=="p" and not self._skip: self._in+=1; self._buf=[]
    def handle_endtag(self, tag):
        if tag in ("script","style","aside","figure","nav","footer") and self._skip: self._skip-=1
        if tag=="p" and self._in:
            self._in-=1; t=re.sub(r"\s+"," ","".join(self._buf)).strip()
            if len(t)>=60 and not SKIP.search(t): self.paras.append(t)
    def handle_data(self, d):
        if self._in and not self._skip: self._buf.append(d)

with out_file.open("w", encoding="utf-8") as out:
    for url in [u.strip() for u in urls_file.read_text().splitlines() if u.strip()]:
        f = raw_dir / (hashlib.md5(url.encode()).hexdigest()[:10] + ".html")
        if not f.exists():
            subprocess.run(["curl","-sL","-m","30","-A",UA,"-o",str(f),url])
        data = f.read_text(encoding="utf-8", errors="ignore") if f.exists() else ""
        p = P(); p.feed(data)
        words, body = 0, []
        for para in p.paras:
            body.append(para); words += len(para.split())
            if words >= 180: break
        title = html.unescape(p.title or "").split(" - ")[0].strip()
        rec = {"url": url, "headline": title, "body": " ".join(body)}
        print(f"{len(rec['body'].split()):4d}w | {title[:70]} | {url}")
        out.write(json.dumps(rec, ensure_ascii=False) + "\n")
