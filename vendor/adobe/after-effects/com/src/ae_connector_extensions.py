"""
AE Connector 扩展方法
包含项目快照、渲染队列等高级功能
"""

def get_project_info(self) -> dict:
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


def create_checkpoint(self, label: str = "", step_index: int = 0, notes: str = "") -> dict:
    """创建项目快照（复用 Atom 的 Checkpoints.jsx 逻辑）"""
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


def revert_to_checkpoint(self, checkpoint_path: str, create_branch: bool = False) -> dict:
    """恢复到指定快照"""
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


def add_to_render_queue(self, comp_index: int, output_path: str, output_module_template: str = "Best Settings") -> dict:
    """将合成添加到渲染队列"""
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


def start_render(self) -> dict:
    """开始渲染队列中的所有项目（阻塞操作）"""
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


def get_render_queue_status(self) -> dict:
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
