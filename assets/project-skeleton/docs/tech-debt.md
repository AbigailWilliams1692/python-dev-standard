> 状态：可用｜最后核对：2026-11-18｜对应提交：未提交

# 技术债登记

规则：发现即登记，不允许只存在于对话或某人的记忆里。偿还后移入「已偿还」并注明日期。

## 未偿还

| 编号 | 位置 | 影响 | 触发条件 | 偿还计划 |
| --- | --- | --- | --- | --- |
| #1 | `infrastructure/persistence/in_memory_chat_repository.py` | 进程退出即丢数据；多 worker 各自一份，会话会「串丢」 | 部署多副本或重启 | 换 PostgreSQL 实现，复用 `ChatSessionRepository` 端口，`container` 改一行 |
| #2 | `modules/chat/router.py::send_message` | 客户端超时重试会产生两轮对话并重复计费 | 网络抖动、前端自动重试 | 接受 `Idempotency-Key` 头，Redis 记录 24h，键为 `(owner_id, key)` |
| #3 | `dependencies.py::get_current_user_id` | `X-User-Id` 可被伪造，无签名无过期 | 任何非本地环境 | 接 JWT 校验：验签 + 过期 + 受众，失败抛 `AuthenticationError` |
| #4 | `in_memory_chat_repository.py::_parse_cursor` | 偏移量游标在翻页期间有写入时会重复或漏项 | 并发写入 + 翻页 | 换库后改复合游标 `(updated_at, session_id)` 的 base64 编码 |
| #5 | `scripts/check_style.py::PINYIN_WORDS` | 拼音检测为词表启发式，漏判（新词）与误报（英文同形词）都可能 | 新增业务词汇 | 用真实代码跑一轮，收集误报/漏报后迭代词表；接受其为 WARN 而非 ERROR |
| #6 | `docs/ux.md` | 交互契约无前端实现，文案未经真实用户验证 | 前端开发启动 | 前端落地后补组件路径与实测截图，并把文案外置为资源文件 |

## 已偿还

| 编号 | 偿还日期 | 说明 |
| --- | --- | --- |
| — | — | 暂无 |
