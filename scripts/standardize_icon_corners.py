#!/usr/bin/env python3
"""
统一图标圆角 - 将所有 app 图标处理为统一的大圆角
"""
from pathlib import Path

from PIL import Image, ImageDraw


def create_rounded_mask(size, radius):
    """创建圆角遮罩"""
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), size], radius=radius, fill=255)
    return mask

def apply_rounded_corners(input_path, output_path, corner_radius_percent=22):
    """
    给图标应用统一的圆角

    Args:
        input_path: 输入图标路径
        output_path: 输出图标路径
        corner_radius_percent: 圆角半径占图标尺寸的百分比（默认 22%，接近 iOS 风格）
    """
    img = Image.open(input_path).convert('RGBA')
    size = img.size

    # 计算圆角半径
    radius = int(min(size) * corner_radius_percent / 100)

    # 创建圆角遮罩
    mask = create_rounded_mask(size, radius)

    # 应用遮罩
    output = Image.new('RGBA', size, (0, 0, 0, 0))
    output.paste(img, (0, 0))
    output.putalpha(mask)

    # 保存
    output.save(output_path, 'PNG')
    print(f"OK: {output_path.name} (radius={radius}px, {corner_radius_percent}%)")

def main():
    icons_dir = Path(__file__).parent.parent / 'frontend' / 'public' / 'static' / 'app' / 'icons' / 'default'

    # 需要处理的图标
    icons = ['download-center.png', 'ps.png', 'ae.png']

    for icon_name in icons:
        input_path = icons_dir / icon_name
        if not input_path.exists():
            print(f"SKIP: {icon_name} not found")
            continue

        # 备份原图标
        backup_path = icons_dir / f"{icon_name}.backup"
        if not backup_path.exists():
            import shutil
            shutil.copy2(input_path, backup_path)
            print(f"BACKUP: {backup_path.name}")

        # 应用统一圆角
        apply_rounded_corners(input_path, input_path, corner_radius_percent=22)

if __name__ == '__main__':
    main()
