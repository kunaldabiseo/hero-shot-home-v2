const pc=require('postcss');let d='';process.stdin.on('data',c=>d+=c).on('end',()=>{const r=pc.parse(d);
const B=':not(#hsnz)';
r.walkRules(x=>{let p=x.parent;while(p){if(p.type==='atrule'&&/keyframes/i.test(p.name))return;p=p.parent}
x.selectors=x.selectors.map(s=>{const t=s.trim();
const m=t.match(/^(html(?:[.#:\[][^\s>~+]*)?\s*(?:>\s*)?\s+)?body([.#:\[][^\s>~+]*)?/);
if(m&&(/^html/.test(t)||/^body/.test(t)))return t.slice(0,m[0].length)+B+t.slice(m[0].length);
if(/^(html|:root)\b/.test(t))return t;return 'body'+B+' '+t})});
r.walkDecls('border-radius',dcl=>{dcl.important=true});
process.stdout.write(r.toString())})
