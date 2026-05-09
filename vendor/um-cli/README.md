# Unlock Music CLI

## 基本信息
- **官方仓库**: <https://git.um-react.app/um/cli>（Unlock Music CLI；历史 GitHub 镜像已不再作为主站）
- **发布页**: <https://git.um-react.app/um/cli/releases/latest>
- **用途**: 音乐解密工具
- **更新频率**: 按需更新

## 目录结构
- `source/` - 官方源码
- `bin/` - 可执行文件
- `patches/` - 我们的补丁

## 更新方式
```bash
python main.py decrypt build
```

## 补丁说明

- **基线 tag**：见 `patches/BASELINE.txt`
- **定制补丁**：`patches/001-mediatools-customizations.patch`
- **如何追随官方又保留定制**：见项目文档 [docs/VENDOR_UM_CLI.zh.md](../../docs/VENDOR_UM_CLI.zh.md)
- 维护者刷新补丁：`python scripts/regenerate_umcli_custom_patch.py`

## 更新历史
- 2026-05-09: 建立相对官方 v0.2.19 的定制补丁与再生脚本
- 2026-04-24: 初始化目录结构
