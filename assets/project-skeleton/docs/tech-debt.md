> 状态：可用｜最后核对：2026-11-18｜对应提交：未提交

# 技术债登记

规则：发现即登记，不允许只存在于对话或某人的记忆里。偿还后移入「已偿还」并注明日期。

## 未偿还

| 编号 | 位置 | 影响 | 触发条件 | 偿还计划 |
| --- | --- | --- | --- | --- |
| #1 | `infrastructure/persistence/in_memory_chat_repository.py` | 进程退出即丢数据；多 worker 各自一份，会话会「串丢」 | 部署多副本或重启 | 换 PostgreSQL 实现，复用 `ChatSessionRepository` 端口，`container` 改一行 |
| #2 | `modules/chat/router.py::send_message` | 客户端超时重试会产生两轮对话并重复计费 | 网络抖动、前端自动重试 | `core/idempotency.py` 已提供 `IdempotencyStore` 端口与内存实现（有测试），**尚未接到 HTTP 层**；接入只需在 router 读 `Idempotency-Key` 头、命中则回放缓存响应，多副本时把内存实现换成 Redis |
| #3 | `dependencies.py::get_current_user_id` | `X-User-Id` 可被伪造，无签名无过期 | 任何非本地环境 | 接 JWT 校验：验签 + 过期 + 受众，失败抛 `AuthenticationError` |
| #4 | `in_memory_chat_repository.py::_parse_cursor` | 偏移量游标在翻页期间有写入时会重复或漏项 | 并发写入 + 翻页 | 换库后改复合游标 `(updated_at, session_id)` 的 base64 编码 |
| #5 | `scripts/check_style.py::PINYIN_WORDS` | 拼音检测为词表启发式：只扫函数名/类名/模块级常量（参数与局部变量不扫），词表 75 条仍可能漏判新词 | 新增业务词汇 | 收窄误报靠"只收多音节词"约束；漏判属已知边界，靠 review 兜底，不追求完备 |
| #6 | `docs/ux.md` | 交互契约无前端实现，文案未经真实用户验证 | 前端开发启动 | 前端落地后补组件路径与实测截图，并把文案外置为资源文件 |

## 已偿还

| 编号 | 偿还日期 | 说明 |
| --- | --- | --- |
| — | — | 暂无 |
