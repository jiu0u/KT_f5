# python -X utf8 docs/slides/build_deck.py → docs/slides/deck.html
# s01~s08.html(고치는 원본)을 한 파일로 합침. 장마다 <style>은 #sNN 안으로 범위를 좁혀 서로 안 섞이게 함.
# slide.css는 안에 넣어서 deck.html 하나만 열어도 디자인이 보임. 항공사진(img/)은 링크 그대로(깃에는 없음).
import os, re

D = os.path.dirname(os.path.abspath(__file__))
S = [f"s{i:02d}" for i in range(1, 9)]


def scope(css, sid):
    out = []
    for rule in css.split("}"):
        if "{" not in rule:
            continue
        sel, body = rule.split("{", 1)
        sel = ",".join(f"#{sid} {x.strip()}" for x in sel.split(",") if x.strip())
        out.append(f"{sel}{{{body}}}")
    return "\n".join(out)


base = open(os.path.join(D, "slide.css"), encoding="utf8").read()
base = base.replace("body{width:1920px;height:1080px;overflow:hidden;", "body{")
styles, pages = [], []
for sid in S:
    h = open(os.path.join(D, sid + ".html"), encoding="utf8").read()
    st = re.search(r"<style>(.*?)</style>", h, re.S)
    if st:
        styles.append(scope(st.group(1), sid))
    body = re.search(r"<body>(.*)</body>", h, re.S).group(1).strip()
    pages.append(f'<section class="pg" id="{sid}"><div class="fit">{body}</div></section>')

html = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>대전 공공건물 지붕 태양광 — 발표 슬라이드</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&family=IBM+Plex+Mono:wght@500;600&display=swap">
<style>
{base}
html{{scroll-snap-type:y mandatory;background:#05090E}}
body{{margin:0;background:#05090E}}
.pg{{height:100vh;display:flex;align-items:center;justify-content:center;scroll-snap-align:center;overflow:hidden}}
.fit{{width:1920px;height:1080px;flex:none;transform-origin:center;background:var(--bg)}}
.nav{{position:fixed;right:16px;bottom:14px;font:13px "Noto Sans KR",sans-serif;color:#A7B5C4;background:rgba(14,22,32,.85);border:1px solid #24313F;border-radius:999px;padding:6px 12px;z-index:9}}
@media print{{html{{scroll-snap-type:none}}.pg{{height:auto;page-break-after:always}}.fit{{transform:none!important}}.nav{{display:none}}@page{{size:1920px 1080px;margin:0}}}}
{chr(10).join(styles)}
</style></head><body>
{chr(10).join(pages)}
<div class="nav" id="nav">← → 키로 넘기기 · F 전체화면</div>
<script>
const P=[...document.querySelectorAll(".pg")], nav=document.getElementById("nav");
const fit=()=>{{const k=Math.min(innerWidth/1920,innerHeight/1080);document.querySelectorAll(".fit").forEach(f=>f.style.transform=`scale(${{k}})`);}};
addEventListener("resize",fit); fit();
const cur=()=>{{let b=0,d=1e9;P.forEach((p,i)=>{{const t=Math.abs(p.getBoundingClientRect().top);if(t<d){{d=t;b=i;}}}});return b;}};
const go=i=>P[Math.max(0,Math.min(P.length-1,i))].scrollIntoView({{behavior:"smooth"}});
addEventListener("keydown",e=>{{
  if(["ArrowRight","ArrowDown","PageDown"," "].includes(e.key)){{e.preventDefault();go(cur()+1);}}
  else if(["ArrowLeft","ArrowUp","PageUp"].includes(e.key)){{e.preventDefault();go(cur()-1);}}
  else if(e.key==="f"||e.key==="F"){{document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen();}}
  else if(e.key==="Home")go(0); else if(e.key==="End")go(P.length-1);
}});
addEventListener("scroll",()=>{{nav.textContent=`${{cur()+1}} / ${{P.length}} · ← → 넘기기 · F 전체화면`;}},{{passive:true}});
</script>
<!-- 깃허브 바로 열기(htmlpreview)가 가끔 스크립트를 실행하지 않음 → 0.3초 뒤에도 그대로면 여기서 실행 -->
<img hidden alt="" src="data:," onerror="setTimeout(function(){{[].slice.call(document.scripts).filter(function(s){{return s.type==='text/htmlpreview'}}).forEach(function(s){{var n=document.createElement('script');n.text=s.text;s.parentNode.replaceChild(n,s)}})}},300)">
</body></html>
"""
open(os.path.join(D, "deck.html"), "w", encoding="utf8").write(html)
print("deck.html", len(html) // 1024, "KB")
