"""Read-only public Job Board API collector. Python 3.11+, no paid/API dependency."""
import argparse
import calendar
import hashlib
import html
import json
import os
from pathlib import Path
import re
import ssl
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
TZ = timezone(timedelta(hours=8))
ROLES = [
 'AI 应用开发实习生','LLM 应用开发工程师（初级）','RAG 开发工程师','Python AI 开发助理',
 'RAG 知识库开发工程师','Python AI 开发工程师（初级）','AI Agent 应用开发工程师（初级）',
 '大模型应用工程师','AI 应用开发助理','AI 开发实习生（接受已毕业的 2026 届）',
 'AI 应用开发工程师（初级）','大模型应用开发工程师','AI 实施工程师','AI 交付工程师',
 'AI 应用运维工程师','大模型部署工程师','AI 平台运维工程师','模型服务运维工程师',
 'AI 技术支持工程师','AI 解决方案助理','企业知识库部署工程师','私有化大模型实施工程师']
CITIES = {'beijing':'北京','shanghai':'上海','shenzhen':'深圳','guangzhou':'广州','hangzhou':'杭州',
          'chengdu':'成都','nanjing':'南京','wuhan':'武汉','suzhou':'苏州','hefei':'合肥',
          'chongqing':'重庆','fuzhou':'福州','ningbo':'宁波','changsha':'长沙','xiamen':'厦门'}
AI = r'\b(?:RAG|LLM|MCP|AI|GPT|FastGPT|Dify)\b|大模型|智能体|知识库|人工智能|generative ai|language model|agentic'
TECH = r'\b(?:python|java|sql|api|docker|linux|fastapi|rag|llm|kubernetes)\b|开发|代码|部署|集成|运维|implementation|integration|software|coding'

def now():
    return datetime.now(TZ).isoformat(timespec='seconds')

def clean(s):
    s = html.unescape(html.unescape(s or ''))
    s = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', '', s or '', flags=re.I|re.S)
    s = re.sub(r'<(?:br\s*/?|/p|/li|/div|/h\d)>', '\n', s, flags=re.I)
    return re.sub(r'[ \t\r]+', ' ', html.unescape(re.sub(r'<[^>]*>', '', s))).strip()

def safe_url(s):
    u = urlsplit(s or '')
    if u.scheme != 'https' or not u.hostname or u.username or u.password:
        raise ValueError('原始来源必须是无凭据的 HTTPS URL')
    if re.search(r'(?:^|&)(?:token|password|access_token|auth|cookie)=',u.query,re.I):
        raise ValueError('来源链接不可包含凭据参数')
    return urlunsplit((u.scheme, u.netloc.lower(), u.path, u.query, ''))

def atomic(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    tmp.replace(path)

def read(path, default):
    return json.loads(Path(path).read_text(encoding='utf-8')) if Path(path).exists() else default

def fetch_json(url, timeout=25, attempts=3):
    # macOS Python.org installs may lack a CA bundle. Use the OS CA file; never disable TLS.
    ctx = ssl.create_default_context()
    if ssl.get_default_verify_paths().cafile is None and Path('/etc/ssl/cert.pem').exists():
        ctx = ssl.create_default_context(cafile='/etc/ssl/cert.pem')
    for i in range(attempts):
        try:
            req = Request(url, headers={'User-Agent':'AI-Job-Monitor/1.0 (public Job Board GET only)', 'Accept':'application/json'})
            with urlopen(req, timeout=timeout, context=ctx) as r:
                if 'json' not in r.headers.get('Content-Type', '').lower():
                    raise ValueError('非 JSON 响应；不执行验证页面')
                raw = r.read(12_000_001)
                if len(raw) > 12_000_000: raise ValueError('响应超过12MB限制')
                return json.loads(raw)
        except HTTPError as e:
            # No retries on authentication, CAPTCHA/access blocks, missing boards or rate limits.
            if e.code < 500 or i == attempts-1: raise
        except (URLError, TimeoutError):
            if i == attempts-1: raise
        time.sleep(2**i)

def greenhouse(board, cfg):
    if not re.fullmatch(r'[a-z0-9_-]+', board): raise ValueError('非法 board token')
    data = fetch_json(f'https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true',
                      cfg.get('requestTimeoutSeconds',25), cfg.get('maxAttempts',3))
    if not isinstance(data.get('jobs'), list): raise ValueError('Job Board jobs 字段结构变化')
    result = []
    for raw in data['jobs']:
        location = raw['location']['name']
        if not any(x in location.lower() for x in ['china','中国',*CITIES.keys(),*CITIES.values()]): continue
        title = raw['title']; body = clean(raw.get('content',''))
        # A title match is only a discovery hint. Classification always inspects the full JD.
        if not re.search(AI, title+'\n'+body, re.I): continue
        city = next((v for k,v in CITIES.items() if k in location.lower() or v in location), location)
        result.append({'source':f'greenhouse:{board}', 'sourceId':str(raw['id']), 'company':{'mongodb':'MongoDB','pingcap':'PingCAP','elastic':'Elastic'}.get(board,board),
            'title':title, 'city':city, 'locationRaw':location, 'salary':'未披露', 'description':body,
            'url':safe_url(raw['absolute_url']), 'sourceUpdatedAt':raw.get('updated_at'),
            # updated_at can reflect board edits; do not invent an employer publication date.
            'publishedAt':raw.get('first_published'), 'dateEvidence':'Job Board first_published' if raw.get('first_published') else '招聘日期未知；updated_at仅记录源更新时间',
            'employmentType':'实习' if re.search(r'\bintern(?:ship)?\b|实习',title,re.I) else '待核实',
            'originalJdRead':bool(body), 'sourceType':'企业官方招聘API',
            'evidenceUrl':f'https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{raw["id"]}',
            'companyReview':{'legalEntity':'待核实','employmentEntity':'待核实','fees':'待核实','outsourcingTravel':'待核实','technicalTeam':'待核实'},
            'matchedRoleKeywords':[r for r in ROLES if re.sub(r'（.*?）','',r).replace(' ','').lower() in (title+body).replace(' ','').lower()]})
    return result, len(data['jobs'])

def evidence(text, pattern):
    return next((x.strip()[:240] for x in re.split(r'[\n。;；]',text) if re.search(pattern,x,re.I)), None)

def score(job, cities):
    text = clean(job.get('description','')); title = job['title']
    conflicts=[]; unknown=[]; ev={}
    def hit(name, pattern):
        for clause in re.split(r'[\n。;；]',text):
            if not re.search(pattern,clause,re.I): continue
            if name in ['masters','experience','crmErp','school'] and re.search(r'优先|preferred|a plus',clause,re.I) and not re.search(r'必须|硬性|mandatory|must|required',clause,re.I): continue
            v=clause.strip()[:240];ev[name]=v;return v
        return None
    # Only clear mandatory wording is a hard rejection; preferences and negations are not.
    if re.search(r'销售|商务拓展|客户经理|\b(sales|account executive|business development)\b',title,re.I): conflicts.append('销售/商务岗位')
    if hit('salesKpi',r'销售额|签单指标|销售提成|以.*签约.*考核|sales quota|revenue target|owns all the sales|sales and channels|sales strategy|new business acquisition|prospect(?:ing)? (?:new )?customers'): conflicts.append('销售考核/获客职责')
    if hit('masters',r'(?:必须|要求|需具备|至少|仅限).{0,8}(?:硕士|研究生)|(?:硕士|研究生)(?:及以上)?学历|master.?s degree.{0,30}(?:required|mandatory)|(?:require|minimum).{0,25}master.?s degree'): conflicts.append('硕士及以上硬要求')
    english_text = '\n'.join(c for c in re.split(r'[\n。;；]',text) if not (re.search(r'优先|preferred|a plus',c,re.I) and not re.search(r'必须|硬性|mandatory|must|required',c,re.I)))
    english_text = re.sub(r'(?:不要求|无需|不强制|不需要).{0,12}(?:四级|六级|CET[- ]?[46])(?:证书)?', '', english_text, flags=re.I)
    if evidence(english_text,r'(?<!不)(?:要求|必须|需具备|持有).{0,12}(?:四级|六级|CET[- ]?[46])|(?:CET[- ]?[46]|英语[四六]级).{0,12}(?:必备|必须|通过)|(?:CET[- ]?[46]).{0,15}(?:required|mandatory|must)|(?:require|mandatory).{0,15}CET[- ]?[46]'): conflicts.append('英语证书硬要求'); ev['english']=evidence(english_text,r'四级|六级|CET')
    if hit('experience',r'(?:至少|要求|具备|不少于|minimum|at least)?\s*(?:[3-9]|\d{2})\s*(?:\+|至\d|[-–]\d)?\s*(?:年.{0,8}(?:经验|工作)|years? (?:of )?(?:relevant |professional |software |engineering )?experience)'): conflicts.append('多年工作经验要求')
    if hit('crmErp',r'(?:必须|要求|具备|需有).{0,12}(?:CRM|ERP).{0,25}(?:相关)?经验(?!优先)|(?:CRM|ERP).{0,15}经验.{0,8}(?:必备|必须)'): conflicts.append('CRM/ERP经验为必备')
    if hit('school',r'(?<!非)(?:仅限|必须|要求).{0,15}(?:985|211|双一流)|(?:985|211|双一流).{0,8}(?:院校毕业|院校本科|硬性要求)'): conflicts.append('院校硬限制')
    intern=job.get('employmentType')=='实习' or bool(re.search(r'实习|\bintern(?:ship)?\b',title,re.I))
    if hit('laterYear',r'(?:仅限|只招|面向).{0,20}202[7-9]|202[7-9].{0,12}(?:届|graduates).{0,12}(?:在校|only)'): conflicts.append('届次冲突')
    if intern and hit('enrolled',r'仅限在校|必须在读|须为在校|全日制在校|currently (?:enrolled|pursuing)|must be enrolled'): conflicts.append('实习明确要求在读')
    direction = 'AI实施交付' if re.search(r'FDE|交付|实施|部署|运维|技术支持|forward deployed|deployment|technical support',title,re.I) else 'AI应用开发'
    ai=bool(re.search(AI,text,re.I)); tech=bool(re.search(TECH,text,re.I))
    if not text: unknown.append('缺少原始JD正文')
    if text and not (ai and tech): conflicts.append('正文未识别到AI技术实现职责，需人工纠正规则或排除')
    grad=hit('graduate',r'接受已毕业.{0,15}2026|2026届.{0,15}(?:已毕业|毕业生|应届)|2026 graduates|graduates.{0,8}2026')
    junior=hit('junior',r'经验不限|无需经验|应届|初级|0\s*[-–]\s*1\s*年|new grad|entry.level|junior|no experience')
    degree=hit('degree',r'本科|bachelor')
    english=hit('noCertificate',r'不要求.{0,8}(?:四级|六级|CET)|无.{0,8}英语证书.{0,5}要求')
    if not grad: unknown.append('是否接受已毕业2026届待核实')
    if not degree: unknown.append('学历条件待核实')
    if not junior: unknown.append('初级经验资格待核实')
    if intern and not hit('graduateIntern',r'实习.{0,20}接受已毕业|已毕业.{0,20}(?:可以|可|接受)实习|接受已毕业.{0,15}2026'): unknown.append('已毕业者实习资格待核实')
    if not english: unknown.append('未发现英语证书硬限制，不代表企业确认免证书')
    if not job.get('publishedAt'): unknown.append('招聘方发布日期待核实')
    if job.get('sourceType')=='手动导入': unknown.append('人工导入：本系统未联网核验当前招聘状态')
    if job.get('publishedAt'):
        try:
            age=(datetime.now(TZ).date()-datetime.fromisoformat(job['publishedAt'].replace('Z','+00:00')).date()).days
            if age<0: unknown.append('招聘日期在未来，需核实')
            if age>62: unknown.append('招聘日期较旧，需重新核实')
        except ValueError: unknown.append('招聘日期格式待核实')
    pts={'direction':25 if ai and tech else 0,'graduate':20 if grad else 0,'degree':15 if degree else 0,
         'experience':15 if junior else 0,'english':10 if english else 0,
         'city':10 if job['city'] in cities else 5,'type':5 if job.get('employmentType') in ['实习','全职'] else 0}
    total=sum(pts.values())
    category='不匹配' if conflicts else '待核实' if unknown else '高匹配' if total>=80 else '中匹配' if total>=60 else '低匹配'
    return dict(score=total,scoreBreakdown=pts,category=category,direction=direction,conflicts=conflicts,
                unknowns=unknown,evidence=ev,schoolNote='未发现院校硬限制' if 'school' not in ev else ev['school'])

def identity(j):
    # Cross-source dedup is conservative: legal company/name, city and exact normalized title.
    key='|'.join(re.sub(r'\s+','',j.get(k,'')).casefold() for k in ['company','city','title'])
    return hashlib.sha256(key.encode()).hexdigest()[:24]

def fingerprint(j):
    keys=['company','title','city','salary','description','publishedAt','employmentType']
    return hashlib.sha256(json.dumps({k:j.get(k) for k in keys},sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def reconcile(previous, incoming, successful, stamp, cities):
    result={j['id']:dict(j) for j in previous};events=[];seen=set()
    for raw in incoming:
        j=dict(raw);j['url']=safe_url(j['url']); jid=identity(j);seen.add(jid);old=result.get(jid)
        current_hash=fingerprint(j);changed=bool(old and old.get('fingerprint')!=current_hash)
        j.update(sources=list(dict.fromkeys([*(old or {}).get('sources',[(old or {}).get('source',j['source'])]),j['source']])),id=jid,fingerprint=current_hash,firstSeenAt=old['firstSeenAt'] if old else stamp,
                 lastSeenAt=stamp,lastVerifiedAt=stamp if j.get('sourceType')!='手动导入' else None,
                 status='open' if j.get('sourceType')!='手动导入' else 'unverified',missingCount=0,
                 aliases=list(dict.fromkeys([*(old or {}).get('aliases',[]),j['url']])))
        j.update(score(j,cities))
        if not old or changed or old.get('status')=='suspected_expired':
            events.append({'date':stamp[:10],'at':stamp,'id':jid,'type':'new' if not old else 'updated'})
        result[jid]=j
    for jid,j in result.items():
        if jid not in seen and all(s in successful for s in j.get('sources',[j['source']])):
            j['missingCount']=j.get('missingCount',0)+1
            if j['missingCount']>=2 and j.get('status')!='suspected_expired':
                j['status']='suspected_expired';events.append({'date':stamp[:10],'at':stamp,'id':jid,'type':'suspected_expired'})
    return sorted(result.values(),key=lambda j:j['firstSeenAt'],reverse=True),events

def manual_jobs(path):
    data=read(path,[])
    if not isinstance(data,list):raise ValueError('手动导入必须是JSON数组')
    for j in data:
        for k in ['company','title','city','url','description']:
            if not isinstance(j.get(k),str) or not j[k].strip():raise ValueError('导入缺少字段 '+k)
        j.update(source='manual',sourceType='手动导入',originalJdRead=True)
        j['url']=safe_url(j['url'])
    return data

def run(root=ROOT):
    start=now();cfg=read(root/'config/sources.json',{});rows=[];logs=[];success=[]
    for board in cfg.get('greenhouseBoards',[]):
        at=now();source='greenhouse:'+board
        try:
            jobs,count=greenhouse(board,cfg);rows.extend(jobs);success.append(source)
            logs.append({'source':source,'attemptedAt':at,'state':'ok','readCount':count,'chinaAiCount':len(jobs)})
        except Exception as e:
            # Do not log arbitrary response bodies, request headers, cookies or tokens.
            logs.append({'source':source,'attemptedAt':at,'state':'failed','error':type(e).__name__,'httpStatus':getattr(e,'code',None)})
    mp=root/cfg.get('manualImport','data/manual.json')
    if mp.exists(): rows.extend(manual_jobs(mp))
    prior=read(root/'data/feed.json',{'jobs':[],'events':[]});end=now()
    status={'startedAt':start,'completedAt':end,'status':'success' if len(success)==len(cfg.get('greenhouseBoards',[])) and success else 'partial' if success else 'failed',
            'sourceCoverage':logs,'scope':'仅配置的企业公开Job Board API＋人工导入；未自动搜索BOSS/智联/51job/猎聘/牛客。未完成原990项平台检索。',
            'roleKeywords':ROLES,'schedule':'每日北京时间13:00，GitHub调度可能延迟'}
    atomic(root/'data/status.json',status)
    if not success:
        print(json.dumps({'status':'failed','message':'保留上次feed，不覆盖最近成功时间','sourceCoverage':logs},ensure_ascii=False));return 1
    jobs,events=reconcile(prior['jobs'],rows,success,end,cfg.get('preferredCities',[]))
    history=[e for e in prior.get('events',[]) if e['date']>=(datetime.now(TZ)-timedelta(days=100)).date().isoformat()]+events
    week=(datetime.now(TZ).date()-timedelta(days=datetime.now(TZ).weekday())).isoformat()
    active=[j for j in jobs if j['status']=='open' and j['category']!='不匹配']
    feed={'schemaVersion':1,'generatedAt':end,'lastSuccessAt':end if status['status']=='success' else prior.get('lastSuccessAt'),
          'lastUsableUpdateAt':end,'run':status,'jobs':jobs,'events':history,
          'summary':{'new':sum(e['type']=='new' for e in events),'valid':len(active),'high':sum(j['category']=='高匹配' for j in active),'pending':sum(j['category']=='待核实' for j in active)},
          'weekly':{'weekStart':week,'new':sum(e['date']>=week and e['type']=='new' for e in history),'updated':sum(e['date']>=week and e['type']=='updated' for e in history)}}
    atomic(root/'data/feed.json',feed)
    atomic(root/'data/weekly.json',feed['weekly'])
    # A small starter snapshot makes an unpacked extension useful before cloud setup.
    atomic(root/'extension/seed.json',feed)
    print(json.dumps({'run':status['status'],'summary':feed['summary'],'jobs':len(jobs)},ensure_ascii=False));return 0

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=ROOT);args=ap.parse_args()
    sys.exit(run(args.root))
