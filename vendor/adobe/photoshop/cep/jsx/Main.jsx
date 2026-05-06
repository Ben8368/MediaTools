$.global.MediaToolsPhotoshop = $.global.MediaToolsPhotoshop || {};

(function () {
    function safePathFromFile(file) {
        if (!file) return "";
        try {
            return file.fsName || file.fullName || String(file);
        } catch (error) {
            return "";
        }
    }

    $.global.MediaToolsPhotoshop.getActiveDocumentPath = function () {
        try {
            if (!app.documents.length) return "";
            var doc = app.activeDocument;
            return safePathFromFile(doc && doc.fullName);
        } catch (error) {
            return "";
        }
    };
})();
