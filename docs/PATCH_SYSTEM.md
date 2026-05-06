# 补丁系统

MediaTools 使用补丁配置来管理外部工具和本机环境差异。补丁系统的目标是让项目能跟随上游工具更新，同时保留必要的本地规则。

## 配置加载顺序

补丁规则通常按以下顺序加载：

1. `patches/tool_patches.json`
2. `runtime/tool_patches.json`
3. `projects/<current-workspace>/manifests/tool_patches.json`

后加载的规则可以覆盖先加载的规则。

## 使用场景

- 指定外部工具可执行文件位置
- 覆盖某个工具的默认参数
- 适配本机安装路径
- 临时规避上游工具行为变化
- 为特定工作区使用不同工具版本或参数

## 全局规则

放在：

```text
patches/tool_patches.json
```

适合保存项目级默认规则。示例文件可放在：

```text
patches/tool_patches.example.json
```

## 运行时规则

放在：

```text
runtime/tool_patches.json
```

适合保存本机临时规则。该目录通常不提交。

## 工作区规则

放在：

```text
projects/<current-workspace>/manifests/tool_patches.json
```

适合保存某个项目特有的工具偏好，例如固定某次制作使用的 FFmpeg 参数。

## 维护建议

- 能写入 `.env` 的本机私密配置，不要写入补丁文件。
- 全局补丁应尽量少，只放跨开发者稳定适用的规则。
- 工作区补丁应随工作区含义命名和说明，避免半年后看不懂。
- 改补丁加载逻辑时，必须更新测试和本文档。

## 相关代码

- `patches/tool_patches.py`
- `tests/test_tool_patches.py`
- `docs/EXTERNAL_TOOLS.md`

## 排查

如果工具行为异常：

1. 先检查当前工作区。
2. 查看工作区 `manifests/tool_patches.json`。
3. 查看 `runtime/tool_patches.json`。
4. 查看 `patches/tool_patches.json`。
5. 用 CLI 或 API 状态接口确认最终解析到的工具路径和参数。
