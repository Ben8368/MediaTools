"""
自动扫描 PSD 中所有 ByteSans 字体的文字图层，
生成 ByteSans → NotoSans 的映射草稿 CSV
"""

import sys
import csv
import time
import os

sys.path.insert(0, os.path.dirname(__file__))

from ps_connector import PhotoshopConnector


def scan_bytesans_layers(psd_path: str) -> list[dict]:
    """扫描 PSD 中所有使用 ByteSans 字体的文字图层"""
    ps = PhotoshopConnector()
    ps.connect()

    doc = ps.open_document(psd_path)
    results = []

    def scan_container(container):
        # 递归扫描图层组
        try:
            for ls in container.LayerSets:
                scan_container(ls)
        except:
            pass

        # 扫描文字图层
        try:
            for layer in container.ArtLayers:
                if layer.Kind == 2:  # 文字图层
                    try:
                        font = layer.TextItem.Font
                        if 'ByteSans' in font:
                            text = layer.TextItem.Contents.strip()
                            # 去除换行符
                            text = text.replace('\r', ' ').replace('\n', ' ')

                            results.append({
                                'layer_name': layer.Name,
                                'text': text,
                                'font': font,
                            })
                    except Exception as e:
                        print(f"读取图层失败: {e}")
        except:
            pass

    scan_container(doc)
    
    # 关闭文档，不保存
    try:
        doc.Close(2)  # psDoNotSaveChanges
    except:
        pass
    
    ps.disconnect()

    return results


def generate_mapping_csv(psd_path: str, output_csv: str):
    """生成映射草稿 CSV"""
    print(f"扫描 PSD: {psd_path}")
    layers = scan_bytesans_layers(psd_path)

    print(f"找到 {len(layers)} 个 ByteSans 文字图层")

    # 去重（同一文字可能在多个画板中重复）
    unique_texts = {}
    for layer in layers:
        text = layer['text']
        font = layer['font']
        key = (text, font)

        if key not in unique_texts:
            unique_texts[key] = {
                'match_mode': 'exact',
                'original_text': text,
                'new_text': '',  # 留空表示保持原文字
                'font': 'NotoSans',  # 只指定字体家族，让工具自动判断字重
                'font_size': '',
                'tracking': '',
                'artboard': ''
            }

    # 写入 CSV
    with open(output_csv, 'w', newline='', encoding='utf-8-sig') as f:
        fieldnames = ['match_mode', 'original_text', 'new_text', 'font', 'font_size', 'tracking', 'artboard']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(unique_texts.values())

    print(f"生成映射草稿: {output_csv}")
    print(f"共 {len(unique_texts)} 条唯一映射规则")
    print("\n请检查 CSV 文件，确认映射规则后再执行替换")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python generate_bytesans_mapping.py <psd文件路径> [输出csv路径]")
        sys.exit(1)

    psd_path = sys.argv[1]
    output_csv = sys.argv[2] if len(sys.argv) > 2 else 'bytesans_to_notosans.csv'

    generate_mapping_csv(psd_path, output_csv)
