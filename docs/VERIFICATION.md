# 验证记录

2026-11-03，本机Python3.14.9、Git2.50.1、Node24.22.1。

## 已实现并本地验证

- 真实公开API采集：PingCAP、MongoDB、Elastic三个Job Board均成功读取；限定中国地区和AI文本线索。首轮保留4条真实来源记录，规则修正后4条均不匹配（销售或高经验），0条高匹配、0条当前可推荐。不为展示凑数。
- JSON本地持久化、原文来源与核验时间、源更新时间与招聘日分别保存。
- 14项Python测试：硬性学历/英语/经验/在读/销售/CRM条件；优先条件不误判为必备；缺条件不高匹配；去重、变更、连续缺失、源失败保留数据；HTML解码及不安全链接。
- JS模块测试：feed格式、域名限制、同步、新增通知去重、失败保留旧feed、个人记录与feed分开存储。这些测试使用Chrome API桩，不代表系统通知实测。
- MV3文件结构、外部脚本/无内联脚本、JSON可解析；无外部JS依赖、无模型调用。

- 开发预览页面：实际浏览器验证总览、真实来源排除表、原文详情、收藏备注、刷新后保留记录。使用明确标记的模拟Chrome API，不等同扩展安装。

## 已实现、待真实环境验证

- Chrome/Edge加载已解压扩展。浏览器工具的URL安全策略阻止访问扩展管理页；没有用其他方式绕过。
- 扩展UI的真实chrome.storage、系统通知、重启浏览器的alarm行为。
- 首次13点schedule触发仍待实际运行记录验证（不是把手动运行当定时成功）。

## 已完成的云端验收

- 公开仓库：https://github.com/qianchengguo/ai-job-monitor
- 手动云端运行：https://github.com/qianchengguo/ai-job-monitor/actions/runs/41589532674
- 测试、三来源采集、数据提交均成功；数据生成时间2026-11-03 14:23:15 +08:00。
- data/feed.json、status.json、weekly.json及extension/seed.json已逐字节核对：公开main与数据提交6b0bf7f2e0d82862ce8341b08c78bf23eb552967一致。详见cloud-verification.json。
- 定时配置为每天北京时间13:00；首次schedule尚未观察到。
- 原Codex本地每日任务经用户明确授权，在云端实跑验证后暂停，原规则和历史保留。

## 暂未实现

- BOSS/智联/51job/猎聘/牛客无人值守自动采集；没有声称已执行990项搜索。
- 自动确认岗位接受已毕业2026届、招聘状态/公司风险保证。
- 邮件/飞书通知、私人记录跨设备云同步、自动更新旧私有Sites。

## 重现

```bash
python3 -m unittest discover -s tests -v
node tests/extension.test.mjs
python3 collector/monitor.py
```

插件安装后应人工验收：选一条现有排除岗位查看详情→收藏/填写测试备注→关闭再打开确认保留→同步后记录仍在→导出记录→恢复→断网点击同步确认旧数据保留。测试备注使用“测试记录”，不要伪造已投递事实。
