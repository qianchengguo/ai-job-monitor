# 来源可用性研究（核查于2026-11-03）

| 来源 | 当前实现 | 依据和限制 |
|---|---|---|
| 企业Greenhouse招聘板 | 已实现公开GET API | 官方Job Board文档明确GET无需鉴权；当前配置3家，每家一次列表读取，正文随content=true返回。源更新时间不自动等同招聘发布日期。不是中国全平台搜索。 |
| BOSS直聘 | 官方入口＋手动导入 | 本次robots读取失败，未验证可供个人自动采集的公开接口授权；未启用无人值守抓取。历史浏览器站内访问也不等于云端访问许可。 |
| 智联 | 官方入口＋手动导入 | 校招协议页面可读，未确认个人批量抓取的公开授权/API；不把可访问页面当自动化许可。 |
| 51job | 官方入口＋手动导入 | 官方用户协议限制自动化程序接入并收集处理内容；不部署采集器。此前详情页还出现滑动验证。 |
| 猎聘 | 官方入口＋手动导入 | 本次robots读取失败，未核实开放接口许可，不启用自动抓取。 |
| 牛客校招 | 官方入口＋手动导入 | 本次robots读取失败，未核实开放接口许可；不启用自动抓取。 |
| 其他企业官网/校招 | 后续按站配置 | 目前只支持Greenhouse适配器；新网站需单独确认访问约定及字段，不提供任意URL爬虫。 |

robots允许并不构成全部使用授权；登录账号并不授予批量自动抓取权。本项目没有声称上述来源都不允许，只说明本次未确认、因此不启用。

官方资料：
- https://docs.greenhouse.io/job-board — 公开Job Board API GET、content字段、认证说明。
- https://login.51job.com/xyservice.php?display=h5&page=1 — 用户协议自动化访问限制。页面显示版本2021-09-23，本次仍公开可读。
- https://mxiaoyuan.zhaopin.com/LoginManager/Agreement — 智联校招协议，仅作为范围参考，不推断为所有子站统一授权。
- https://www.zhipin.com/web/common/protocol/protocol-2019-09-30.html — BOSS公开协议入口；搜索结果混含隐私政策，不据此断言已获得爬虫许可。
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule — UTC定时、可能延迟、默认分支、无活动禁用。
- https://docs.github.com/en/billing/concepts/product-billing/github-actions — 标准公开仓库runner免费范围，其他计费受计划/政策影响。
- https://developer.chrome.com/docs/extensions/reference/api/alarms — 浏览器闹钟不会唤醒休眠设备、可延迟触发；云端负责真正离线于本机的采集。

通知选择：仅Chrome通知，不配置邮箱/企业微信/飞书，不申请任何额外服务；浏览器离线时没有即时提醒。每周统计每次采集重算、以北京时间周一为界，每周第一次同步显示一次汇总。无需另一条付费定时服务。
