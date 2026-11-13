import json, re, sys, hashlib, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from docx_units import load_paragraphs, matches
BASE=Path(__file__).resolve().parent
DOCX=Path(sys.argv[1]) if len(sys.argv)>1 else BASE.parent/'starter'/'data'/'Capstone Project Document.docx'
MANIFEST=Path(sys.argv[2]) if len(sys.argv)>2 else BASE.parent/'starter'/'data'/'manifest.json'
REQ=['id','question','split','type','filter','expected_answer','gold_source_id','gold_position','evidence_quote']
raw=(BASE/'questions.jsonl').read_text(encoding='utf-8').splitlines()
Q=[json.loads(l) for l in raw]
P={p['idx']:p for p in load_paragraphs(DOCX)}
man=json.load(open(MANIFEST))['documents'][0]
err=[]; chk=lambda c,m: c or err.append(m)
chk(len(P)==man['content_units']['count'],f"số đoạn {len(P)} != manifest {man['content_units']['count']}")
chk(len(Q)>=20,'ít hơn 20 câu')
cnt=collections.Counter(q['split'] for q in Q); chk(cnt['dev']==15 and cnt['test']==5 and len(cnt)==2,f'split {dict(cnt)}')
chk(len({q['id'] for q in Q})==len(Q),'id trùng'); chk(len({q['question'] for q in Q})==len(Q),'câu hỏi trùng')
norm=lambda s:re.sub(r'(?<=\d)[.,](?=\d)','',s)
filt=[q for q in Q if q['filter']]
chk(len(filt)>=3,'<3 câu filter'); chk(any(q['split']=='test' for q in filt),'không có câu filter trong test')
secs={p['section'] for p in P.values()}; chaps={p['chapter'] for p in P.values()}
for q in Q:
    i=q['id']
    for k in REQ: chk(k in q,f'{i}: thiếu {k}')
    for k in REQ:
        if k!='filter': chk(q.get(k) not in (None,''),f'{i}: {k} rỗng')
    chk(q['gold_source_id']==man['source_id'],f'{i}: source_id sai')
    pos=q['gold_position']; chk(isinstance(pos,int) and pos in P,f'{i}: vị trí không hợp lệ')
    if pos in P:
        chk(q['evidence_quote'] in P[pos]['text'],f'{i}: evidence KHÔNG khớp đoạn {pos}')
        others=[j for j,p in P.items() if j!=pos and q['evidence_quote'] in p['text']]
        chk(not others,f'{i}: evidence cũng xuất hiện ở đoạn {others}')
        # số trong đáp án phải có trong evidence
        miss=[n for n in re.findall(r'\d+(?:[.,]\d+)*',q['expected_answer']) if norm(n) not in norm(q['evidence_quote'])]
        chk(not miss,f'{i}: số trong đáp án không có trong evidence: {miss}')
    f=q['filter']
    if f:
        chk(set(f)<= {'chapter','section'},f'{i}: trường filter lạ')
        chk(all((v in secs) if k=='section' else (v in chaps) for k,v in f.items()),f'{i}: giá trị filter không tồn tại trong tài liệu')
        if pos in P:
            chk(matches(P[pos],f),f'{i}: filter loại mất gold')
            n=sum(matches(p,f) for p in P.values()); chk(0<n<len(P),f'{i}: filter không thu hẹp')
        chk(q['gold_source_id'] not in json.dumps(f),f'{i}: filter chứa gold source')
        chk(not any(str(v).lower() in q['expected_answer'].lower() for v in f.values() if isinstance(v,str) and len(v)>3),f'{i}: filter lặp lại đáp án')
        # điều kiện filter phải được nêu trong câu hỏi
        txt=q['question']; ok=any((k=='section' and (v in txt or v.replace('Appendix ','Phụ lục ') in txt)) or (k=='chapter' and f'Chương {v}' in txt) for k,v in f.items())
        chk(ok,f'{i}: điều kiện filter không được nêu trong câu hỏi')
types=collections.Counter(q['type'] for q in Q)
for t in ('truc_tiep','dien_dat_lai','ket_hop_dieu_kien'): chk(types[t]>0,f'thiếu loại {t}')
dev_pos={q['gold_position'] for q in Q if q['split']=='dev'}; test_pos={q['gold_position'] for q in Q if q['split']=='test'}
chk(not dev_pos&test_pos,'dev/test dùng chung đoạn nguồn')
lock=json.loads((BASE/'split_lock.json').read_text(encoding='utf-8'))
for s in ('dev','test'):
    h=hashlib.sha256('\n'.join(l for l,q in zip(raw,Q) if q['split']==s).encode()).hexdigest()
    chk(h==lock[s+'_sha256'],f'{s} đã bị sửa so với split_lock')
print(f"Số câu: {len(Q)} | split: {dict(cnt)} | loại: {dict(types)}")
print(f"Filter: {len(filt)} câu (dev {sum(q['split']=='dev' for q in filt)}, test {sum(q['split']=='test' for q in filt)}) -> {[q['id'] for q in filt]}")
print(f"Evidence khớp đoạn nguồn: {sum(q['evidence_quote'] in P[q['gold_position']]['text'] for q in Q)}/{len(Q)} | số đoạn tài liệu: {len(P)}")
print('LỖI:' if err else 'PASS: tất cả kiểm tra đạt.'); [print(' -',e) for e in err]
sys.exit(1 if err else 0)
