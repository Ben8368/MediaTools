"""
Photoshop COM 连接管理模块
通过 win32com 控制 Photoshop 打开/保存/导出文件
支持多画板(Artboard)操作
"""

import os
import time
import win32com.client
from typing import Optional


# Photoshop 常量（COM 枚举值）
# DialogModes
psDisplayNoDialogs = 3

# SaveOptions
psSaveChanges = 1
psDoNotSaveChanges = 2

# LayerKind
psTextLayer = 2
psSmartObjectLayer = 17

# Units
psPixels = 1
psPoints = 5

# SaveFormat / Export
psPNGFile = 13
psJPEG = 6
psPhotoshop = 1

# TypeUnits (Photoshop 实际枚举值)
psTypePixels = 5
psTypePoints = 1


class PhotoshopConnector:
    """Photoshop COM 连接管理器"""

    def __init__(self):
        self.app = None
        self._original_ruler_units = None
        self._original_type_units = None

    def connect(self) -> None:
        """连接到 Photoshop（如果未运行则自动启动）"""
        try:
            self.app = win32com.client.Dispatch("Photoshop.Application")
        except Exception:
            raise ConnectionError(
                "无法连接到 Photoshop。请确保已安装 Adobe Photoshop 并尝试手动启动后重试。"
            )

        # 保存并设置标尺单位为像素，方便 Bounds 计算
        # 强制锁定 TypeUnits 为 px，避免换字体后 PS 重新解释单位导致字号变化
        self._original_ruler_units = self.app.Preferences.RulerUnits
        self._original_type_units = self.app.Preferences.TypeUnits
        self.app.Preferences.RulerUnits = psPixels
        self.app.Preferences.TypeUnits = psTypePixels  # 锁定为 px，避免换字体后字号单位错乱

        # 不显示对话框
        self.app.DisplayDialogs = psDisplayNoDialogs

    def disconnect(self) -> None:
        """恢复设置"""
        if self.app and self._original_ruler_units is not None:
            try:
                self.app.Preferences.RulerUnits = self._original_ruler_units
                self.app.Preferences.TypeUnits = self._original_type_units
            except Exception:
                pass

    def open_document(self, filepath: str):
        """打开 PSD 文件，返回 Document 对象"""
        filepath = os.path.abspath(filepath)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"文件不存在: {filepath}")
        doc = self.app.Open(filepath)
        # 等待文档完全加载
        time.sleep(0.5)
        return doc

    def save_psd(self, doc, output_path: str) -> None:
        """保存为 PSD 文件"""
        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        desc = win32com.client.Dispatch("Photoshop.PhotoshopSaveOptions")
        desc.AlphaChannels = True
        desc.Layers = True
        doc.SaveAs(output_path, desc, True)

    def export_png(self, doc, output_path: str) -> None:
        """导出为 PNG 文件"""
        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        opts = win32com.client.Dispatch("Photoshop.PNGSaveOptions")
        opts.Interlaced = False
        opts.Compression = 6
        doc.SaveAs(output_path, opts, True)

    def export_jpg(self, doc, output_path: str, quality: int = 10) -> None:
        """导出为 JPG 文件"""
        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        opts = win32com.client.Dispatch("Photoshop.JPEGSaveOptions")
        opts.Quality = quality  # 0-12
        doc.SaveAs(output_path, opts, True)

    def close_document(self, doc, save: bool = False) -> None:
        """关闭文档"""
        if save:
            doc.Close(psSaveChanges)
        else:
            doc.Close(psDoNotSaveChanges)

    def get_layer_bounds_area(self, layer) -> float:
        """获取图层边界框面积（像素^2）"""
        bounds = layer.Bounds  # [left, top, right, bottom]
        width = float(bounds[2]) - float(bounds[0])
        height = float(bounds[3]) - float(bounds[1])
        return width * height

    def get_layer_bounds(self, layer) -> tuple:
        """获取图层边界框 (left, top, right, bottom)"""
        bounds = layer.Bounds
        return (float(bounds[0]), float(bounds[1]),
                float(bounds[2]), float(bounds[3]))

    def get_layer_id(self, layer) -> int:
        """Return Photoshop's stable layer id for an ArtLayer/LayerSet."""
        if layer is None:
            return 0
        for attr in ("id", "ID"):
            try:
                value = getattr(layer, attr)
                return int(value)
            except Exception:
                pass
        return 0

    def select_layer_by_id(self, layer_id: int) -> None:
        """Select a layer by id using Action Manager, required for smart object commands."""
        ref = win32com.client.Dispatch("Photoshop.ActionReference")
        ref.PutIdentifier(self.app.CharIDToTypeID("Lyr "), int(layer_id))
        desc = win32com.client.Dispatch("Photoshop.ActionDescriptor")
        desc.PutReference(self.app.CharIDToTypeID("null"), ref)
        self.app.ExecuteAction(self.app.CharIDToTypeID("slct"), desc, psDisplayNoDialogs)

    def get_layer_descriptor(self, layer):
        """Read a layer ActionDescriptor; returns None when Photoshop refuses the query."""
        layer_id = self.get_layer_id(layer)
        if not layer_id:
            return None
        try:
            ref = win32com.client.Dispatch("Photoshop.ActionReference")
            ref.PutIdentifier(self.app.StringIDToTypeID("layer"), layer_id)
            return self.app.ExecuteActionGet(ref)
        except Exception:
            return None

    def _descriptor_value_as_string(self, desc, key_id) -> str:
        """Best-effort ActionDescriptor value reader for stable smart object keys."""
        for getter in ("GetString", "GetInteger", "GetLargeInteger", "GetDouble", "GetBoolean", "GetPath"):
            try:
                value = getattr(desc, getter)(key_id)
                text = str(value).strip()
                if text:
                    return text
            except Exception:
                pass
        return ""

    def get_smart_object_identity(self, layer) -> str:
        """Return a shared-content identity for a smart object, or layer fallback when unavailable."""
        layer_id = self.get_layer_id(layer)
        desc = self.get_layer_descriptor(layer)
        if desc is None:
            return f"layer:{layer_id}" if layer_id else ""

        for object_key in ("smartObjectMore", "smartObject"):
            try:
                object_key_id = self.app.StringIDToTypeID(object_key)
                if not desc.HasKey(object_key_id):
                    continue
                smart_desc = desc.GetObjectValue(object_key_id)
            except Exception:
                continue
            for value_key in ("placedID", "documentID", "ID", "link", "fileReference", "linked"):
                try:
                    value_key_id = self.app.StringIDToTypeID(value_key)
                    if not smart_desc.HasKey(value_key_id):
                        continue
                    value = self._descriptor_value_as_string(smart_desc, value_key_id)
                    if value:
                        return f"{object_key}.{value_key}:{value}"
                except Exception:
                    pass
        return f"layer:{layer_id}" if layer_id else ""

    def is_smart_object_layer(self, layer) -> bool:
        """Detect smart objects using both COM LayerKind and ActionDescriptor metadata."""
        try:
            if int(layer.Kind) == psSmartObjectLayer:
                return True
        except Exception:
            pass

        desc = self.get_layer_descriptor(layer)
        if desc is None:
            return False
        for key_name in ("smartObject", "smartObjectMore"):
            try:
                if desc.HasKey(self.app.StringIDToTypeID(key_name)):
                    return True
            except Exception:
                pass
        return False

    def find_layer_by_id(self, container, layer_id: int):
        """Recursively find an ArtLayer or LayerSet by Photoshop layer id."""
        target = int(layer_id or 0)
        if not target:
            return None
        try:
            for layer in container.ArtLayers:
                if self.get_layer_id(layer) == target:
                    return layer
        except Exception:
            pass
        try:
            for layer_set in container.LayerSets:
                if self.get_layer_id(layer_set) == target:
                    return layer_set
                found = self.find_layer_by_id(layer_set, target)
                if found is not None:
                    return found
        except Exception:
            pass
        return None

    def collect_text_layers(self, container) -> list:
        """递归收集所有文字图层"""
        text_layers = []
        try:
            for layer in container.ArtLayers:
                try:
                    if layer.Kind == psTextLayer:
                        text_layers.append(layer)
                except Exception:
                    pass
        except Exception:
            pass

        try:
            for layer_set in container.LayerSets:
                text_layers.extend(self.collect_text_layers(layer_set))
        except Exception:
            pass

        return text_layers

    def collect_smart_object_layers(self, container) -> list:
        """Recursively collect smart object art layers."""
        smart_layers = []
        try:
            for layer in container.ArtLayers:
                try:
                    if self.is_smart_object_layer(layer):
                        smart_layers.append(layer)
                except Exception:
                    pass
        except Exception:
            pass

        try:
            for layer_set in container.LayerSets:
                smart_layers.extend(self.collect_smart_object_layers(layer_set))
        except Exception:
            pass

        return smart_layers

    def open_smart_object_contents(self, layer):
        """Open the selected smart object's embedded document and return the active document."""
        layer_id = self.get_layer_id(layer)
        if not layer_id:
            raise RuntimeError("Smart object layer has no id")
        return self.open_smart_object_contents_by_id(layer_id)

    def open_smart_object_contents_by_id(self, layer_id: int):
        """Open smart object contents by stable Photoshop layer id."""
        if not layer_id:
            raise RuntimeError("Smart object layer has no id")
        self.select_layer_by_id(layer_id)
        desc = win32com.client.Dispatch("Photoshop.ActionDescriptor")
        self.app.ExecuteAction(self.app.StringIDToTypeID("placedLayerEditContents"), desc, psDisplayNoDialogs)
        time.sleep(0.6)
        # 强制设置 TypeUnits 为 px，避免智能对象内部单位错乱
        # 重试机制确保设置成功
        for _ in range(3):
            try:
                self.app.Preferences.TypeUnits = psTypePixels
                if self.app.Preferences.TypeUnits == psTypePixels:
                    break
                time.sleep(0.1)
            except Exception:
                time.sleep(0.1)
        return self.app.ActiveDocument

    # ========== 多画板(Artboard)支持 ==========

    def _is_artboard(self, layer_set) -> bool:
        """
        判断一个 LayerSet 是否是画板(Artboard)
        通过 ActionDescriptor 读取 artboardEnabled 属性
        """
        try:
            ref = win32com.client.Dispatch("Photoshop.ActionReference")
            ref.PutIdentifier(self.app.StringIDToTypeID("layer"), layer_set.id)

            desc = self.app.ExecuteActionGet(ref)
            ab_key = self.app.StringIDToTypeID("artboardEnabled")
            if desc.HasKey(ab_key):
                return desc.GetBoolean(ab_key)
        except Exception:
            pass

        # 回退方案：检查图层名称是否包含 "Artboard" 或 "画板"
        try:
            name = layer_set.Name.lower()
            if "artboard" in name:
                return True
        except Exception:
            pass

        return False

    def collect_artboards(self, doc) -> list:
        """
        收集文档中所有画板
        返回 [(artboard_layer_set, artboard_name), ...]
        """
        artboards = []
        try:
            for layer_set in doc.LayerSets:
                if self._is_artboard(layer_set):
                    artboards.append(layer_set)
        except Exception:
            pass
        return artboards

    def collect_text_layers_in_artboard(self, artboard) -> list:
        """收集单个画板内的所有文字图层"""
        return self.collect_text_layers(artboard)

    def collect_text_layers_outside_artboards(self, doc, artboard_ids: set) -> list:
        """收集不属于任何画板的文字图层（文档顶层 + 非画板图层组内）"""
        text_layers = []

        # 顶层 ArtLayers
        try:
            for layer in doc.ArtLayers:
                try:
                    if layer.Kind == psTextLayer:
                        text_layers.append(layer)
                except Exception:
                    pass
        except Exception:
            pass

        # 非画板的 LayerSets 中递归查找
        try:
            for layer_set in doc.LayerSets:
                try:
                    if layer_set.id not in artboard_ids:
                        text_layers.extend(self.collect_text_layers(layer_set))
                except Exception:
                    pass
        except Exception:
            pass

        return text_layers

    def collect_smart_object_layers_outside_artboards(self, doc, artboard_ids: set) -> list:
        """Collect smart objects outside artboards (top-level and non-artboard groups)."""
        smart_layers = []
        try:
            for layer in doc.ArtLayers:
                try:
                    if self.is_smart_object_layer(layer):
                        smart_layers.append(layer)
                except Exception:
                    pass
        except Exception:
            pass

        try:
            for layer_set in doc.LayerSets:
                try:
                    if self.get_layer_id(layer_set) not in artboard_ids:
                        smart_layers.extend(self.collect_smart_object_layers(layer_set))
                except Exception:
                    pass
        except Exception:
            pass

        return smart_layers

    def export_artboard_png(self, doc, artboard, output_path: str) -> None:
        """
        导出单个画板为 PNG
        策略：隐藏其他画板 -> 裁剪到画板区域 -> 导出 -> 撤销恢复
        """
        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 记录所有画板的可见性
        all_artboards = self.collect_artboards(doc)
        visibility_backup = []
        for ab in all_artboards:
            try:
                visibility_backup.append((ab, ab.Visible))
                if ab.id != artboard.id:
                    ab.Visible = False
            except Exception:
                pass

        try:
            # 获取画板边界
            bounds = self.get_layer_bounds(artboard)
            left, top, right, bottom = bounds

            # 记录原始画布大小
            orig_width = doc.Width
            orig_height = doc.Height

            # 裁剪到画板区域
            doc.Crop([left, top, right, bottom])
            time.sleep(0.3)

            # 导出 PNG
            opts = win32com.client.Dispatch("Photoshop.PNGSaveOptions")
            opts.Interlaced = False
            opts.Compression = 6
            doc.SaveAs(output_path, opts, True)

        finally:
            # 撤销裁剪（多次撤销确保恢复）
            try:
                doc.ActiveHistoryState = doc.HistoryStates.Item(doc.HistoryStates.Count - 1)
            except Exception:
                pass

            # 恢复所有画板可见性
            for ab, was_visible in visibility_backup:
                try:
                    ab.Visible = was_visible
                except Exception:
                    pass

    def export_artboard_jpg(self, doc, artboard, output_path: str, quality: int = 10) -> None:
        """
        导出单个画板为 JPG
        策略同 export_artboard_png
        """
        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        all_artboards = self.collect_artboards(doc)
        visibility_backup = []
        for ab in all_artboards:
            try:
                visibility_backup.append((ab, ab.Visible))
                if ab.id != artboard.id:
                    ab.Visible = False
            except Exception:
                pass

        try:
            bounds = self.get_layer_bounds(artboard)
            left, top, right, bottom = bounds

            doc.Crop([left, top, right, bottom])
            time.sleep(0.3)

            opts = win32com.client.Dispatch("Photoshop.JPEGSaveOptions")
            opts.Quality = quality
            doc.SaveAs(output_path, opts, True)

        finally:
            try:
                doc.ActiveHistoryState = doc.HistoryStates.Item(doc.HistoryStates.Count - 1)
            except Exception:
                pass

            for ab, was_visible in visibility_backup:
                try:
                    ab.Visible = was_visible
                except Exception:
                    pass



    # ========== Font Detection ==========

    _font_weights_cache = {}  # class-level cache: family -> [weights]

    def get_available_weights(self, target_family: str) -> list:
        """
        检测目标字体家族在 PS 中已安装的字重。
        返回 list of (weight_name, postscript_name) tuples。
        weight_name 是标准字重词（Bold/Medium/Regular 等），
        postscript_name 是 PS 实际接受的名称（如 NotoSansJP-Bold）。
        结果按 weight_name 排序，并缓存。
        
        匹配规则：
        1. 显示名精确匹配（可变字体，如 "Noto Sans SC"）
        2. 显示名空格前缀（如 "Noto Sans JP Bold"）
        3. PostScript 名连字符前缀（如 "ByteSans-Bold"）
        """
        instance_cache = getattr(self, "_fw_cache", None)
        if instance_cache is None:
            self._fw_cache = {}
            instance_cache = self._fw_cache
        if target_family in instance_cache:
            return instance_cache[target_family]

        found_dict = {}  # {postscript_name: weight_name} 用于去重

        try:
            all_fonts = self.app.Fonts
            for ft in all_fonts:
                display_name = ft.Name
                ps_name = ft.PostScriptName

                # 规则1: 精确匹配显示名（可变字体，如 Noto Sans SC）
                if display_name == target_family:
                    if "-" in ps_name:
                        weight_part = ps_name.split("-", 1)[1]
                        found_dict[ps_name] = weight_part
                    continue

                # 规则2: 显示名空格前缀（如 "Noto Sans JP Bold"）
                space_prefix = target_family + " "
                if display_name.startswith(space_prefix):
                    weight_part = display_name[len(space_prefix):]
                    found_dict[ps_name] = weight_part
                    continue

                # 规则3: PostScript 名连字符前缀（如 "ByteSans-Bold"）
                dash_prefix = target_family + "-"
                if ps_name.startswith(dash_prefix):
                    weight_part = ps_name[len(dash_prefix):]
                    found_dict[ps_name] = weight_part
        except Exception:
            pass

        # 转换为 list of tuples 并排序
        result = sorted([(w, ps) for ps, w in found_dict.items()], key=lambda x: x[0])
        instance_cache[target_family] = result
        return result

    def get_font_separator(self, target_family: str) -> str:
        """兼容旧接口，已废弃，返回空字符串"""
        return ""
