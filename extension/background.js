const KEY='jobFeed';
import {validFeed,feedUrl,DEFAULT_FEED} from './shared.js';
async function seed(){const s=await chrome.storage.local.get([KEY,'feedUrl']);if(!s.feedUrl)await chrome.storage.local.set({feedUrl:DEFAULT_FEED});if(!s[KEY]){const f=validFeed(await(await fetch(chrome.runtime.getURL('seed.json'))).json());await chrome.storage.local.set({[KEY]:f});}}
let running;
export function sync(){if(running)return running;running=doSync().finally(()=>{running=null;});return running;}
async function doSync(){
 try{
  await seed();const s=await chrome.storage.local.get(['feedUrl',KEY,'lastNotifiedWeek']);
  if(!s.feedUrl)return {ok:false,error:'尚未配置云端feed地址；当前显示打包时快照'};
  const u=feedUrl(s.feedUrl);const permission=u.origin+'/*';
  if(!await chrome.permissions.contains({origins:[permission]}))throw Error('尚未授权读取该feed域名');
  const r=await fetch(u.href,{cache:'no-store',signal:AbortSignal.timeout(20000),credentials:'omit',redirect:'error'});
  if(!r.ok)throw Error('feed HTTP '+r.status);const raw=await r.text();if(raw.length>12000000)throw Error('feed过大');
  const f=validFeed(JSON.parse(raw)),old=s[KEY];
  if(old&&f.generatedAt<old.generatedAt)throw Error('云端数据早于当前数据，保留当前版本');
  const oldIds=new Set((old?.jobs||[]).map(j=>j.id));
  const n=f.jobs.filter(j=>!oldIds.has(j.id)&&j.category!=='不匹配').length;
  let cloudStatus=null,cloudStatusError=null;
  try{const su=new URL(u);su.pathname=su.pathname.replace(/feed\.json$/,'status.json');if(su.href===u.href)throw Error('feed地址需以feed.json结尾');const sr=await fetch(su.href,{cache:'no-store',signal:AbortSignal.timeout(15000),credentials:'omit',redirect:'error'});if(!sr.ok)throw Error('status HTTP '+sr.status);const cs=JSON.parse(await sr.text());if(!['success','partial','failed'].includes(cs.status)||!cs.completedAt)throw Error('状态格式无效');cloudStatus=cs;}catch(e){cloudStatusError=e.message;}
  await chrome.storage.local.set({[KEY]:f,lastSyncedAt:new Date().toISOString(),syncError:null,cloudStatus,cloudStatusError});
  if(n)await chrome.notifications.create({type:'basic',iconUrl:'icon.png',title:'新增AI求职线索',message:`新增${n}条；请查看资格和待核实条件。`});
  const week=f.weekly?.weekStart;
  if(week&&s.lastNotifiedWeek!==week){await chrome.notifications.create({type:'basic',iconUrl:'icon.png',title:'本周招聘汇总',message:`本周新发现${f.weekly.new}条，变更${f.weekly.updated}条。`});await chrome.storage.local.set({lastNotifiedWeek:week});}
  return {ok:true,newCount:n};
 }catch(e){await chrome.storage.local.set({syncError:e.message,lastSyncAttemptAt:new Date().toISOString()});return {ok:false,error:e.message};}
}
async function setup(){await seed();if(!await chrome.alarms.get('sync'))await chrome.alarms.create('sync',{periodInMinutes:60});}
if(globalThis.chrome?.runtime){
 chrome.runtime.onInstalled.addListener(setup);chrome.runtime.onStartup.addListener(()=>{setup().then(sync);});
 chrome.alarms.onAlarm.addListener(a=>{if(a.name==='sync')sync();});
 chrome.runtime.onMessage.addListener((m,_sender,reply)=>{if(m.type==='sync'){sync().then(reply);return true;}});
 chrome.notifications.onClicked.addListener(()=>chrome.tabs.create({url:chrome.runtime.getURL('index.html')}));
}
