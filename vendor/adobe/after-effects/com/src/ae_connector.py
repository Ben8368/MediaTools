"""
After Effects COM 连接管理模块
通过 win32com 控制 After Effects 打开/修改/渲染工程
"""

import os
import time
import win32com.client
from typing import Optional, Any


class AfterEffectsConnector:
    """After Effects COM 连接管理器"""

    def __init__(self):
        self.app = None

    def connect(self) -> None:
        """连接到 After Effects（如果未运行则自动启动）"""
        try:
            self.app = win32com.client.Dispatch("AfterFX.Application")
        except Exception:
            raise ConnectionError(
                "无法连接到 After Effects。请确保已安装 Adobe After Effects 并尝试手动启动后重试。"
            )

    def disconnect(self) -> None:
        """断开连接"""
        self.app = None

    def open_project(self, filepath: str):
        """打开 AEP 工程文件，返回 Project 对象"""
        filepath = os.path.abspath(filepath)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"文件不存在: {filepath}")

        script = f"""
        var file = new File("{filepath.replace(chr(92), '/')}");
        if (!file.exists) {{
            throw new Error("File not found: {filepath}");
        }}
        app.open(file);
        "opened";
        """
        result = self.app.DoScript(script)
        time.sleep(1.0)  # 等待工程加载
        return self.app.project

    def save_project(self, output_path: str) -> None:
        """保存工程到指定路径"""
        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        script = f"""
        var file = new File("{output_path.replace(chr(92), '/')}");
        app.project.save(file);
        "saved";
        """
        self.app.DoScript(script)

    def close_project(self) -> None:
        """关闭当前工程（不保存）"""
        script = """
        app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
        "closed";
        """
        try:
            self.app.DoScript(script)
        except Exception:
            pass

    def scan_project_for_text_layers(self, project_path: str) -> list[dict[str, Any]]:
        """
        扫描工程中的所有文本图层
        返回 [{"comp_name": str, "layer_name": str, "layer_index": int, "text": str, ...}, ...]
        """
        # JSX 脚本：遍历所有合成，提取文本图层信息，序列化为 JSON 字符串返回
        script = r"""
        var results = [];
        var proj = app.project;
        for (var i = 1; i <= proj.numItems; i++) {
            var item = proj.item(i);
            if (!(item instanceof CompItem)) continue;
            var compName = item.name;
            for (var j = 1; j <= item.numLayers; j++) {
                var layer = item.layer(j);
                if (!(layer instanceof TextLayer)) continue;
                var textProp = layer.property("Source Text");
                var td = textProp.value;
                var text = td.text || "";
                var font = "";
                var fontSize = 0;
                var tracking = 0;
                try { font = td.font; } catch(e) {}
                try { fontSize = td.fontSize; } catch(e) {}
                try { tracking = td.tracking; } catch(e) {}
                results.push({
                    comp_name: compName,
                    comp_index: i,
                    layer_name: layer.name,
                    layer_index: j,
                    original_text: text,
                    source_font: font,
                    font_size: fontSize,
                    tracking: tracking
                });
            }
        }
        JSON.stringify(results);
        """
        raw = self.app.DoScript(script)
        import json
        layers = json.loads(raw) if raw else []
        return layers

    def apply_text_changes(
        self,
        changes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        批量应用文本修改。
        changes 每项：{comp_index, layer_index, target_text, target_font, font_size, tracking}
        返回每项的执行结果。
        """
        import json

        changes_json = json.dumps(changes, ensure_ascii=False)
        # 转义反斜杠，防止 JSX 字符串解析错误
        changes_json_escaped = changes_json.replace("\\", "\\\\").replace('"', '\\"')

        script = f"""
        var changes = eval('(' + "{changes_json_escaped}" + ')');
        var results = [];
        var proj = app.project;

        for (var ci = 0; ci < changes.length; ci++) {{
            var ch = changes[ci];
            var ok = false;
            var msg = "";
            try {{
                var comp = proj.item(ch.comp_index);
                if (!comp || !(comp instanceof CompItem)) {{
                    throw new Error("Comp not found: index " + ch.comp_index);
                }}
                var layer = comp.layer(ch.layer_index);
                if (!layer || !(layer instanceof TextLayer)) {{
                    throw new Error("Text layer not found: index " + ch.layer_index);
                }}
                var textProp = layer.property("Source Text");
                var td = textProp.value;
                if (ch.target_text !== null && ch.target_text !== undefined && ch.target_text !== "") {{
                    td.text = ch.target_text;
                }}
                if (ch.target_font !== null && ch.target_font !== undefined && ch.target_font !== "") {{
                    td.font = ch.target_font;
                }}
                if (ch.font_size !== null && ch.font_size !== undefined && ch.font_size > 0) {{
                    td.fontSize = ch.font_size;
                }}
                if (ch.tracking !== null && ch.tracking !== undefined) {{
                    td.tracking = ch.tracking;
                }}
                textProp.setValue(td);
                ok = true;
                msg = "ok";
            }} catch(e) {{
                msg = e.toString();
            }}
            results.push({{ comp_index: ch.comp_index, layer_index: ch.layer_index, ok: ok, msg: msg }});
        }}
        JSON.stringify(results);
        """
        raw = self.app.DoScript(script)
        return json.loads(raw) if raw else []

    def get_available_fonts(self, query: str = "", limit: int = 200) -> list[dict[str, str]]:
        """
        枚举 AE 中可用的字体
        返回 [{"family": str, "style": str, "postScript": str}, ...]

        实现原理：调用 app.fonts.allFonts API (AE 24+)
        与 Atom 插件的 Fonts.jsx 使用相同的 ExtendScript API
        """
        import json

        # 转义查询字符串，防止 JSX 注入
        query_escaped = query.replace("\\", "\\\\").replace('"', '\\"')

        script = f"""
        var query = "{query_escaped}";
        var limit = {limit};
        var out = [];

        // 检查 app.fonts API 是否可用（AE 24+）
        if (typeof app.fonts === 'undefined' || !app.fonts) {{
            throw new Error("app.fonts API not available (requires AE 24+)");
        }}

        // 轮询非系统字体文件夹变化（AE 24.6+）
        try {{
            if (typeof app.fonts.pollForAndPushNonSystemFontFoldersChanges === 'function') {{
                app.fonts.pollForAndPushNonSystemFontFoldersChanges();
            }}
        }} catch(e) {{}}

        var families = app.fonts.allFonts;
        var queryLower = query ? query.toLowerCase() : null;

        for (var i = 0; i < families.length; i++) {{
            var fam = families[i];
            for (var j = 0; j < fam.length; j++) {{
                var f = fam[j];

                // 跳过替代字体
                try {{
                    if (f.isSubstitute) continue;
                }} catch(e) {{}}

                var familyName = '';
                var styleName = '';
                var postScript = '';

                try {{ familyName = f.familyName || ''; }} catch(e) {{}}
                try {{ styleName = f.styleName || ''; }} catch(e) {{}}
                try {{ postScript = f.postScriptName || ''; }} catch(e) {{}}

                // 查询过滤
                if (queryLower) {{
                    var matchFamily = familyName.toLowerCase().indexOf(queryLower) !== -1;
                    var matchStyle = styleName.toLowerCase().indexOf(queryLower) !== -1;
                    var matchPS = postScript.toLowerCase().indexOf(queryLower) !== -1;
                    if (!matchFamily && !matchStyle && !matchPS) continue;
                }}

                out.push({{
                    family: familyName,
                    style: styleName,
                    postScript: postScript
                }});

                if (out.length >= limit) break;
            }}
            if (out.length >= limit) break;
        }}

        JSON.stringify(out);
        """

        raw = self.app.DoScript(script)
        return json.loads(raw) if raw else []

    def get_project_info(self) -> dict[str, Any]:
        """获取当前工程信息"""
        script = """
        var info = {
            file: null,
            dirty: false,
            revision: 0
        };
        if (app.project && app.project.file) {
            info.file = app.project.file.fsName;
            info.dirty = app.project.dirty;
            info.revision = app.project.revision;
        }
        JSON.stringify(info);
        """
        raw = self.app.DoScript(script)
        import json
        return json.loads(raw) if raw else {}

    def create_checkpoint(
        self,
        label: str = "",
        step_index: int = 0,
        notes: str = "",
    ) -> dict[str, Any]:
        """
        创建项目快照（复用 Atom 的 Checkpoints.jsx 逻辑）
        返回快照信息：{id, label, checkpointPath, ...}
        """
        import json

        label_escaped = label.replace("\\", "\\\\").replace('"', '\\"')
        notes_escaped = notes.replace("\\", "\\\\").replace('"', '\\"')

        script = f"""
        if (!app.project || !app.project.file) {{
            throw new Error("Project must be saved before creating checkpoint");
        }}

        var mainFile = app.project.file;
        if (app.project.dirty) {{
            app.project.save(mainFile);
        }}

        var checkpointsFolder = new Folder(mainFile.path + '/_atom_checkpoints');
        if (!checkpointsFolder.exists) {{
            checkpointsFolder.create();
        }}

        var baseName = mainFile.name.replace(/\\.aepx?$/i, '');
        var ts = new Date().getTime();
        var stepStr = String({step_index});
        while (stepStr.length < 3) stepStr = '0' + stepStr;
        var checkpointName = baseName + '_atom_step-' + stepStr + '_' + ts + '.aep';
        var checkpointFile = new File(checkpointsFolder.fsName + '/' + checkpointName);

        var ok = mainFile.copy(checkpointFile);
        if (!ok) {{
            throw new Error("Failed to copy project file: " + mainFile.error);
        }}

        function shortId(index) {{
            var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
            var base = chars.length;
            var n = index + 1;
            var result = '';
            while (n > 0) {{
                n--;
                result = chars.charAt(n % base) + result;
                n = Math.floor(n / base);
            }}
            return result;
        }}

        var checkpoint = {{
            id: shortId({step_index}),
            label: "{label_escaped}" || ("Step " + {step_index}),
            stepIndex: {step_index},
            createdAt: new Date().toUTCString(),
            aeRevision: app.project.revision,
            checkpointPath: checkpointFile.fsName,
            notes: "{notes_escaped}"
        }};

        JSON.stringify(checkpoint);
        """

        raw = self.app.DoScript(script)
        return json.loads(raw) if raw else {}

    def revert_to_checkpoint(
        self,
        checkpoint_path: str,
        create_branch: bool = False,
    ) -> dict[str, Any]:
        """
        恢复到指定快照
        如果 create_branch=True，会在恢复前创建当前状态的分支副本
        """
        import json

        checkpoint_path_escaped = checkpoint_path.replace("\\", "\\\\").replace('"', '\\"')

        script = f"""
        var checkpointFile = new File("{checkpoint_path_escaped}");
        if (!checkpointFile.exists) {{
            throw new Error("Checkpoint file not found");
        }}

        if (!app.project || !app.project.file) {{
            throw new Error("No project open");
        }}

        var mainFile = app.project.file;
        var branchPath = null;

        if ({str(create_branch).lower()}) {{
            if (app.project.dirty) {{
                app.project.save(mainFile);
            }}
            var checkpointsFolder = new Folder(mainFile.path + '/_atom_checkpoints');
            if (!checkpointsFolder.exists) checkpointsFolder.create();
            var baseName = mainFile.name.replace(/\\.aepx?$/i, '');
            var branchName = baseName + '_branch_' + new Date().getTime() + '.aep';
            var branchFile = new File(checkpointsFolder.fsName + '/' + branchName);
            var branchOk = mainFile.copy(branchFile);
            if (!branchOk) {{
                throw new Error("Failed to create branch copy");
            }}
            branchPath = branchFile.fsName;
        }}

        app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
        var overwriteOk = checkpointFile.copy(mainFile.fsName);
        if (!overwriteOk) {{
            throw new Error("Failed to overwrite project with checkpoint");
        }}

        app.open(mainFile);

        JSON.stringify({{
            ok: true,
            revertedTo: "{checkpoint_path_escaped}",
            branchPath: branchPath
        }});
        """

        raw = self.app.DoScript(script)
        return json.loads(raw) if raw else {}

    def add_to_render_queue(
        self,
        comp_index: int,
        output_path: str,
        output_module_template: str = "Best Settings",
    ) -> dict[str, Any]:
        """
        将合成添加到渲染队列
        返回渲染项信息
        """
        import json

        output_path_escaped = output_path.replace("\\", "\\\\").replace('"', '\\"')
        template_escaped = output_module_template.replace("\\", "\\\\").replace('"', '\\"')

        script = f"""
        var comp = app.project.item({comp_index});
        if (!comp || !(comp instanceof CompItem)) {{
            throw new Error("Composition not found at index {comp_index}");
        }}

        var rqItem = app.project.renderQueue.items.add(comp);
        var outputModule = rqItem.outputModules[1];
        outputModule.file = new File("{output_path_escaped}");

        try {{
            outputModule.applyTemplate("{template_escaped}");
        }} catch(e) {{}}

        JSON.stringify({{
            renderQueueItemIndex: rqItem.index,
            compName: comp.name,
            outputPath: "{output_path_escaped}",
            status: "queued"
        }});
        """

        raw = self.app.DoScript(script)
        return json.loads(raw) if raw else {}

    def start_render(self) -> dict[str, Any]:
        """
        开始渲染队列中的所有项目
        注意：这是阻塞操作，会等待渲染完成
        """
        script = """
        var numQueued = 0;
        for (var i = 1; i <= app.project.renderQueue.numItems; i++) {
            var item = app.project.renderQueue.item(i);
            if (item.status === RQItemStatus.QUEUED) {
                numQueued++;
            }
        }

        if (numQueued === 0) {
            throw new Error("No items queued for rendering");
        }

        app.project.renderQueue.render();

        JSON.stringify({
            ok: true,
            itemsRendered: numQueued
        });
        """

        raw = self.app.DoScript(script)
        import json
        return json.loads(raw) if raw else {}

    def get_render_queue_status(self) -> dict[str, Any]:
        """获取渲染队列状态"""
        script = """
        var items = [];
        for (var i = 1; i <= app.project.renderQueue.numItems; i++) {
            var item = app.project.renderQueue.item(i);
            var statusStr = "unknown";
            try {
                if (item.status === RQItemStatus.QUEUED) statusStr = "queued";
                else if (item.status === RQItemStatus.RENDERING) statusStr = "rendering";
                else if (item.status === RQItemStatus.DONE) statusStr = "done";
                else if (item.status === RQItemStatus.WILL_CONTINUE) statusStr = "will_continue";
                else if (item.status === RQItemStatus.NEEDS_OUTPUT) statusStr = "needs_output";
                else if (item.status === RQItemStatus.UNQUEUED) statusStr = "unqueued";
                else if (item.status === RQItemStatus.USER_STOPPED) statusStr = "user_stopped";
                else if (item.status === RQItemStatus.ERR_STOPPED) statusStr = "error_stopped";
            } catch(e) {}

            items.push({
                index: i,
                compName: item.comp ? item.comp.name : "",
                status: statusStr
            });
        }

        JSON.stringify({
            numItems: app.project.renderQueue.numItems,
            items: items
        });
        """

        raw = self.app.DoScript(script)
        import json
        return json.loads(raw) if raw else {}
