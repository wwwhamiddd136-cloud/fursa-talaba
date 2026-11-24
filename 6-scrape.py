import re,html,json,sys,time,urllib.request,datetime
UA={"User-Agent":"Mozilla/5.0 (compatible; MaroStageBot/0.1; link aggregator, respects robots.txt)"}
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=25).read().decode('utf8','replace')
def clean(s): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()
def ep(pages=3):
    out=[]
    for p in range(1,pages+1):
        h=get(f"https://www.emploi-public.ma/fr/concours-liste?page={p}")
        for blk in h.split('<!-- Item -->')[1:]:
            m=re.search(r'href="(/fr/concours/details/[^"]+)"',blk)
            if not m: continue
            t=re.search(r'card-title">(.*?)</h2>',blk,re.S)
            o=re.search(r'card-text">(.*?)</div>',blk,re.S)
            f=clean(blk.split('card-footer')[-1])
            out.append(dict(source="emploi-public.ma",type="concours",title=clean(t.group(1)) if t else "",org=clean(o.group(1)) if o else "",info=f,url="https://www.emploi-public.ma"+m.group(1)))
        time.sleep(1.5)
    return out
def sm(pages=3):
    out=[]
    for p in range(1,pages+1):
        h=get(f"https://www.stage.ma/offres-stage?page={p}")
        for m in re.finditer(r'<li[^>]*>|<article[^>]*>',h): pass
        for blk in re.split(r'(?=<h3 class="text-\[15px\])',h)[1:]:
            m=re.search(r'href="(/offres-stage/[^"]+)">(.*?)</a>',blk,re.S)
            if not m: continue
            comp=re.search(r'href="/entreprises/[^"]+">(.*?)</a>',blk,re.S)
            sp=re.findall(r'</svg>([^<]+)</span>',blk[:3000])
            out.append(dict(source="stage.ma",type="stage",title=clean(m.group(2)),org=clean(comp.group(1)) if comp else "",info=" | ".join(clean(x) for x in sp[:3]),url="https://www.stage.ma"+m.group(1)))
        time.sleep(1.5)
    return out
MON={m:i+1 for i,m in enumerate("janvier février mars avril mai juin juillet août septembre octobre novembre décembre".split())}
def dt(s):
    m=re.search(r'(\d{1,2}) (\w+) (\d{4})',s or "")
    if m and m.group(2).lower() in MON: return "%s-%02d-%02d"%(m.group(3),MON[m.group(2).lower()],int(m.group(1)))
def enrich(items):
    for x in items:
        i=x['info']
        if x['type']=="concours":
            x['city']="";x['posts']=int(re.search(r'(\d+) poste',i).group(1)) if re.search(r'(\d+) poste',i) else None
            a=re.search(r'Limite de dépôt : (.*?)(?: - \d|Date du|$)',i);x['deadline']=dt(a.group(1)) if a else None
            b=re.search(r'Date du concours : (.*)$',i);x['exam']=dt(b.group(1)) if b else None
            x['title']=re.sub(r'^Avis de concours de recrutement (de |d\')?','',x['title']) or x['title']
        else:
            p=[t.strip() for t in i.split('|')]
            x['city']=p[0] if p else "";x['mode']=p[1] if len(p)>1 else "";x['kind']=p[2] if len(p)>2 else ""
            x['deadline']=None
    return items
if __name__=="__main__":
    n=int(sys.argv[1]) if len(sys.argv)>1 else 3
    d=enrich(ep(n)+sm(n))
    seen=set();r=[]
    for x in d:
        if x['url'] in seen: continue
        seen.add(x['url']);r.append(x)
    json.dump(dict(updated=datetime.datetime.utcnow().isoformat()+"Z",items=r),open("data.json","w"),ensure_ascii=False,indent=1)
    print(len(r))
