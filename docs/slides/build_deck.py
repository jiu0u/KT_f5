# python -X utf8 docs/slides/build_deck.py → docs/slides/deck.html
# s01~s08.html(고치는 원본)을 한 파일로 합침. 장마다 디자인 방식이 달라도 서로 안 섞이게,
# 각 장을 통째로 iframe(srcdoc)에 넣음 → 장을 단독으로 열었을 때와 똑같이 보임.
# slide.css는 각 장 안에 넣어서 deck.html 하나만 열어도(깃허브 바로 열기 포함) 디자인이 보임.
# 항공사진(img/)은 링크 그대로(깃에는 없음).
import html as H
import os

D = os.path.dirname(os.path.abspath(__file__))
S = [f"s{i:02d}" for i in range(1, 9)]
CSS = open(os.path.join(D, "slide.css"), encoding="utf8").read()

pages = []
for sid in S:
    h = open(os.path.join(D, sid + ".html"), encoding="utf8").read()
    h = h.replace('<link rel="stylesheet" href="slide.css">', "<style>\n" + CSS + "\n</style>")
    pages.append(f'<section class="pg" id="{sid}"><div class="fit"><iframe title="{sid}" srcdoc="{H.escape(h, quote=True)}"></iframe></div></section>')

page = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>대전 공공건물 지붕 태양광 — 발표 슬라이드</title>
<style>
html{scroll-snap-type:y mandatory;background:#DDE3EC}
body{margin:0;background:#DDE3EC}
.pg{height:100vh;display:flex;align-items:center;justify-content:center;scroll-snap-align:center;overflow:hidden}
.fit{width:1920px;height:1080px;flex:none;transform-origin:center;box-shadow:0 18px 50px rgba(15,27,45,.16)}
.fit iframe{width:1920px;height:1080px;border:0;display:block;pointer-events:none;background:#fff}
.nav{position:fixed;right:16px;bottom:14px;font:13px "Noto Sans KR",sans-serif;color:#4B5669;background:rgba(255,255,255,.9);border:1px solid #D8DFE6;border-radius:999px;padding:6px 12px;z-index:9}
@media print{html{scroll-snap-type:none}.pg{height:auto;page-break-after:always}.fit{transform:none!important;box-shadow:none}.nav{display:none}@page{size:1920px 1080px;margin:0}}
</style></head><body>
PAGES
<div class="nav" id="nav">← → 키로 넘기기 · F 전체화면</div>
<script>
const P=[...document.querySelectorAll(".pg")], nav=document.getElementById("nav");
const fit=()=>{const k=Math.min(innerWidth/1920,innerHeight/1080);document.querySelectorAll(".fit").forEach(f=>f.style.transform=`scale(${k})`);};
addEventListener("resize",fit); fit();
const cur=()=>{let b=0,d=1e9;P.forEach((p,i)=>{const t=Math.abs(p.getBoundingClientRect().top);if(t<d){d=t;b=i;}});return b;};
const go=i=>P[Math.max(0,Math.min(P.length-1,i))].scrollIntoView({behavior:"smooth"});
addEventListener("keydown",e=>{
  if(["ArrowRight","ArrowDown","PageDown"," "].includes(e.key)){e.preventDefault();go(cur()+1);}
  else if(["ArrowLeft","ArrowUp","PageUp"].includes(e.key)){e.preventDefault();go(cur()-1);}
  else if(e.key==="f"||e.key==="F"){document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen();}
  else if(e.key==="Home")go(0); else if(e.key==="End")go(P.length-1);
});
addEventListener("scroll",()=>{nav.textContent=`${cur()+1} / ${P.length} · ← → 넘기기 · F 전체화면`;},{passive:true});
</script>
</body></html>
""".replace("PAGES", "\n".join(pages))
open(os.path.join(D, "deck.html"), "w", encoding="utf8").write(page)
print("deck.html", len(page) // 1024, "KB")
