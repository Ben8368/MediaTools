# vendor/um-cli：追随上游并保留 MediaTools 定制

## 原则

- **上游事实来源**：[Unlock Music CLI](https://git.um-react.app/um/cli)；**不要**在不做记录的情况下直接改 `vendor/um-cli/source/`。
- **定制必须通过补丁**：差异集中在 `vendor/um-cli/patches/001-mediatools-customizations.patch`；官方对应版本写在 `vendor/um-cli/patches/BASELINE.txt`（tag，如 `v0.2.19`）。
- **与项目治理一致**：第三方逻辑仍在 `vendor/`，自有封装在 `modules/decryptor`、`adapters` 等（参见 Law-006）。

## 日常更新官方（保留定制）

1. 查看上游 [Releases](https://git.um-react.app/um/cli/releases/latest)，确认新 tag（示例 `v0.2.20`）。
2. **更新基线**：编辑 `vendor/um-cli/patches/BASELINE.txt`，写入新 tag（**仅在已验证补丁能套上或准备解决冲突时**再改）。
3. **干净对齐官方树**（任选其一）  
   - A. 删除 `vendor/um-cli/source` 下除补丁外的内容，将官方该 tag 解压/克隆到 `source/`；  
   - B. 在临时目录 `git clone --branch <tag> ...`，再把**无 `.git`** 的文件树拷入 `source/`。
4. **应用定制补丁**（在 `vendor/um-cli/source` 目录下执行）：

   ```powershell
   git apply --check ..\patches\001-mediatools-customizations.patch
   git apply ..\patches\001-mediatools-customizations.patch
   ```

   - 若 **`git apply` 失败**：按冲突文件手工合并，直至 `go build ./cmd/um` 通过；然后执行下面「刷新补丁」。

5. **编译并提交**：`go build -o ../../../../bin/um-cli.exe ./cmd/um`（路径按本机调整），再跑项目侧 `build_umcli` / 手工拷贝二进制；在 MediaTools 仓库中提交 `source/` 与（如有变更）`patches/`。

## 你改了定制代码之后（刷新补丁）

在 **`BASELINE.txt` 已与当前官方基线一致** 的前提下，从仓库根目录执行：

```powershell
python scripts/regenerate_umcli_custom_patch.py
```

会用 `BASELINE.txt` 的 tag 克隆官方、叠上当前 `source/`，重写 `001-mediatools-customizations.patch`。**不要用 PowerShell `Out-File` 重定向存补丁**，避免编码损坏；脚本已使用 `git diff --output` 生成二进制安全补丁。

## 与 `apply_patches.py` 的关系

`python scripts/apply_patches.py apply um-cli` 会在 `vendor/um-cli/source` 下执行 `git apply`。**无需**在 `source/` 内初始化 Git 仓库即可打补丁。

## 基线与补丁不匹配时

现象：`git apply` 大量冲突或行号错位。处理顺序建议：

1. 确认 `BASELINE.txt` 与生成 `001` 时所用官方 tag 一致。  
2. 将 `BASELINE.txt` 改回**上一次能应用成功**的 tag，拉干净官方树，打上旧补丁，确认可编译。  
3. 再 bump 官方到新 tag：用 Git 在临时 clone 里 `merge`/`rebase` 或手工搬运差异，最后 **`regenerate_umcli_custom_patch.py`** 生成新 `001`，并更新 `BASELINE.txt`。
