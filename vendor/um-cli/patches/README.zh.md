# um-cli 定制补丁

## 基线版本

见同目录下的 `BASELINE.txt`（当前官方源码对齐的 tag）。  
定制差异集中在：`001-mediatools-customizations.patch`。

重新生成该补丁时，请先将 `BASELINE.txt` 更新为目标官方 tag，再运行仓库根目录：

```powershell
python scripts/regenerate_umcli_custom_patch.py
```

## 与官方的关系

- 上游：<https://git.um-react.app/um/cli>
- `source/` 目录 = **官方对应 tag 的树** + **本目录补丁**，不要手改后不更新 patch，否则下次无法追随上游。
