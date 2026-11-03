export const DEFAULT_FEED='https://raw.githubusercontent.com/qianchengguo/ai-job-monitor/main/data/feed.json';
export function validFeed(f){
 if(f?.schemaVersion!==1||!Array.isArray(f.jobs)||!f.run||!Array.isArray(f.events)||!f.generatedAt)throw Error('数据格式不支持');
 const ids=new Set();
 for(const j of f.jobs){
  if(typeof j.id!=='string'||ids.has(j.id))throw Error('重复或缺少岗位ID');ids.add(j.id);
  if(typeof j.title!=='string'||typeof j.company!=='string'||!['高匹配','中匹配','低匹配','待核实','不匹配'].includes(j.category))throw Error('岗位字段无效');
  const u=new URL(j.url);if(u.protocol!=='https:'||u.username||u.password)throw Error('不安全的来源链接');
 }
 return f;
}
export function feedUrl(s){
 const u=new URL(s);if(!((u.protocol==='https:'&&u.hostname==='raw.githubusercontent.com')||(u.protocol==='http:'&&['localhost','127.0.0.1'].includes(u.hostname))))throw Error('仅支持GitHub Raw或本机测试地址');
 if(u.username||u.password||u.search||u.hash)throw Error('地址不可包含凭据、参数或片段');return u;
}
