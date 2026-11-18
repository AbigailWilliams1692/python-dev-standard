# Changelog

本文件记录所有面向使用者的变更。格式遵循
[Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

**库的变更日志是契约的一部分**：下游按版本升级，破坏性变更必须能提前看到。
服务型项目对内演进，用 `docs/dev-log.md` 即可，不需要这份文件。

## [Unreleased]

### Added

- 待补充：下一次发布的条目写在这里，发布时移到对应版本号下。

## [0.1.0] - 2026-11-18

### Added

- `Version` 不可变值对象，支持 `parse()`、`as_tuple`、比较与哈希。
- `is_compatible_with()`，按语义化版本判断兼容性，含 `0.x` 严格匹配例外。
- `MyLibError` 与 `InvalidVersionError` 异常层次。
- `py.typed` 标记，下游可直接获得类型信息。

### Notes

- 首个版本，`0.x` 阶段不承诺向后兼容。
