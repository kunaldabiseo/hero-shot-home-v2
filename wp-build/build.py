import re, json, hashlib, base64, subprocess, sys
SRC='/home/claude/hero-shot-home-v2/index.html'
W='/tmp/claude-0/-home-claude/8ceb1378-ef0e-5c6d-98f8-334fed076cdb/scratchpad/wpb/'
UP='https://heroshotphotography.com/wp-content/uploads/2026/11/'
s=open(SRC).read()
dmap=json.load(open('/home/claude/hero-shot-home-v2/wp-build/datauri-map.json'))
# data URIs (raster only)
def rep_data(m):
    uri=m.group(0); b=base64.b64decode(uri.split(',',1)[1])
    for f in dmap.values():
        if open('/home/claude/hero-shot-home-v2/wp-build/assets/'+f,'rb').read()==b: return UP+f
    raise SystemExit('nomap '+uri[:40])
s=re.sub(r'data:image/(?:png|webp|jpeg);base64,[A-Za-z0-9+/=]+',rep_data,s)
s=re.sub(r'src="ig/([^"]+)"',lambda m:'src="'+UP+'hs-ig-'+m.group(1)+'"',s)
s=re.sub(r'src="media/([^"]+)"',lambda m:'src="'+UP+'hs-'+m.group(1)+'"',s)
import collections
for old,new in (('hsv','hscv'),('hsm','hsmt')):
    print(old, len(re.findall(r'(?<![A-Za-z0-9_])'+old+r'(?![A-Za-z0-9_])',s)), 'preexisting new', len(re.findall(new,s)))
    s=re.sub(r'(?<![A-Za-z0-9_])'+old+r'(?![A-Za-z0-9_])',new,s)
head,body=s.split('<body',1); body=body.split('>',1)[1].rsplit('</body>',1)[0]
# head CSS
css=''.join(re.findall(r'<style[^>]*>(.*?)</style>',head,re.S))
css=re.sub(r'/\* =+ PREVIEW ONLY.*?(?=/\* =+ HERO)','',css,flags=re.S)
assert 'hsx-preview' not in css
fonts=re.search(r'<link href="https://fonts.googleapis.com/css2[^>]*>',head).group(0)
# split body top-level
from html.parser import HTMLParser
VOID={'img','br','input','meta','link','source','hr','wbr','area','base','col','embed','param','track'}
lines=body.split('\n'); offs=[0]
for l in lines: offs.append(offs[-1]+len(l)+1)
class P(HTMLParser):
    def __init__(s):
        super().__init__(convert_charrefs=False);s.d=0;s.items=[]
    def pos(s):
        l,c=s.getpos();return offs[l-1]+c
    def handle_starttag(s,t,a):
        if s.d==0: s.items.append([s.pos(),None,t,dict(a)])
        if t not in VOID: s.d+=1
    def handle_startendtag(s,t,a):
        if s.d==0: s.items.append([s.pos(),None,t,dict(a)])
    def handle_endtag(s,t):
        if t in VOID: return
        s.d-=1
        if s.d==0:
            e=s.pos(); s.items[-1][1]=body.index('>',e)+1
p=P();p.feed(body)
items=p.items
for it in items: assert it[1], it
def chunk(it): return body[it[0]:it[1]]
groups=[];cur=None
LABEL={'hs-top':'01 Hero','hs-paths':'03 Headshots two paths','hs-brand':'04 Brand events personal','hs-estimator':'05 Calculator and pricing','hs-reviews':'07 Reviews','hs-process':'08 Method','hs-compare':'09 Options','hs-studio':'10 Studios','hs-team':'11 Team','hs-cases':'12 Recent client work','hs-giveback':'14 Give back','hs-bts':'15 Behind the scenes','hs-faq':'16 FAQs','hs-locations':'17 Locations','hs-contact':'18 Contact'}
skip_next_script=False
for it in items:
    t,a=it[2],it[3]; c=chunk(it)
    if t=='header' or t=='footer': skip_next_script=True; continue
    if t=='script' and skip_next_script: skip_next_script=False; continue
    skip_next_script=False
    if t=='style' and a.get('id')=='hsmo-mobile-layer':
        cur={'label':'99 Mobile layer and scripts','parts':[]};groups.append(cur)
    elif t=='section' and a.get('id') in LABEL:
        cur={'label':LABEL[a['id']],'parts':[]};groups.append(cur)
    elif t=='div' and 'hsp-wrap' in a.get('class',''):
        cur={'label':'02 Proof and clients','parts':[]};groups.append(cur)
    cur['parts'].append((t,c))
# minifiers
def node(script,inp):
    r=subprocess.run(['node','-e',script],input=inp,capture_output=True,text=True,cwd=W)
    if r.returncode: raise SystemExit(r.stderr[:2000])
    if r.stderr.strip(): print(r.stderr.strip()[:200])
    return r.stdout
def minjs(js):
    return node("const t=require('terser');let d='';process.stdin.on('data',c=>d+=c).on('end',async()=>{const r=await t.minify(d,{compress:{passes:1},mangle:true,format:{comments:false}});process.stdout.write(r.code)})",js)
def stripchrome(c):
    return node(r"""const pc=require('postcss');let d='';process.stdin.on('data',c=>d+=c).on('end',()=>{const r=pc.parse(d);let n=0;r.walkRules(x=>{if(/\.hs(h|ft)(?![a-z0-9])/.test(x.selector)){const keep=x.selectors.filter(s=>!/\.hs(h|ft)(?![a-z0-9])/.test(s));if(keep.length){x.selectors=keep}else{x.remove();n++}}});r.walkAtRules(a=>{if(a.nodes&&a.nodes.length===0)a.remove()});console.error('removed',n);process.stdout.write(r.toString())})""",c)
def mincss(c):
    c=stripchrome(c)
    c=node(open(W+'scope.js').read(),c)
    return node("const C=require('clean-css');let d='';process.stdin.on('data',c=>d+=c).on('end',()=>{const r=new C({level:1}).minify(d);if(r.errors.length){console.error(r.errors);process.exit(1)}process.stdout.write(r.styles)})",c)
def minhtml(h):
    return node("const m=require('html-minifier-terser');let d='';process.stdin.on('data',c=>d+=c).on('end',async()=>{process.stdout.write(await m.minify(d,{collapseWhitespace:true,conservativeCollapse:true,removeComments:true,minifyCSS:false,minifyJS:false,keepClosingSlash:true}))})",h)
def fix_nl_js(js):
    # turn newlines inside template literals into \n escapes
    if '\n' not in js: return js
    out=[];i=0;n=len(js)
    # simple scan: track backtick state, skipping quotes/regex roughly
    st=None
    while i<n:
        ch=js[i]
        if st is None:
            if ch in '"\'`': st=ch
            out.append(ch)
        else:
            if ch=='\\': out.append(js[i:i+2]); i+=2; continue
            if ch==st: st=None
            if ch=='\n' and st=='`': out.append('\\n'); i+=1; continue
            out.append(ch)
        i+=1
    r=''.join(out); assert '\n' not in r, 'nl left'
    return r
def part_out(t,c):
    if t=='script':
        inner=re.match(r'<script[^>]*>(.*)</script>$',c,re.S).group(1)
        js=minjs(inner)
        return '<script src="data:text/javascript;base64,'+base64.b64encode(js.encode()).decode()+'"></script>'
    if t=='style':
        inner=re.match(r'<style([^>]*)>(.*)</style>$',c,re.S)
        return '<style'+inner.group(1)+'>'+mincss(inner.group(2))+'</style>'
    h=minhtml(c).replace('\n',' ')
    return h
def sec(label,cls,html):
    return '[section label="%s" padding="0px" class="%s"][row style="collapse" width="full-width"][col span="12" span__sm="12"][ux_html label="%s"]%s[/ux_html][/col][/row][/section]'%(label,cls,label,html)
RESET='body:not(#hsnz) :where(.hsn-sec .col-inner *,.hsf-lb,.hsf-lb *,.hse-dlg,.hse-dlg *,.hsx-modal,.hsx-modal *,#hse-doc,#hse-doc *,.hsy-cur,.hsy-cur *):where(:not(svg *,svg)){all:revert}body:not(#hsnz) :where(.hsn-sec .col-inner *,.hsf-lb,.hsf-lb *,.hse-dlg,.hse-dlg *,.hsx-modal,.hsx-modal *,#hse-doc,#hse-doc *):where([hidden]){display:none}body:not(#hsnz) :where(.hse-dlg,.hsf-lb,.hsx-modal,#hse-doc,.hsy-cur){font:400 16px/normal "Times New Roman",serif;color:#000;letter-spacing:normal;text-transform:none;text-align:start;word-spacing:normal}body:not(#hsnz) .hsn-sec .col-inner{font:400 16px/normal "Times New Roman",serif;color:#000;letter-spacing:normal;text-transform:none;text-align:start;word-spacing:normal}body:not(#hsnz) :where(.hsn-sec .col-inner,.hsf-lb,.hse-dlg,.hsx-modal,#hse-doc) :is(button,input,select,textarea,.button){border-radius:revert!important}'
out=[]
out.append(sec('00 Page styles','hsn-css','<!-- wp:html --><!-- /wp:html -->'+fonts+'<style id="hsn-main">'+RESET+mincss(css)+'</style>'))
for g in groups:
    html=''.join(part_out(t,c) for t,c in g['parts'])
    out.append(sec(g['label'],'hsn-sec',html))
content=''.join(out)
assert '\n' not in content and '\r' not in content
# collision check: any [word that is a registered shortcode?
open(W+'content.txt','w').write(content)
print(len(content),[g['label'] for g in groups])
print(sorted(set(re.findall(r'\[([a-z_]+)[ \]]',content))))
