"""裁掉图标周围的透明边距，让颜色内容填满画布。"""
import shutil
from pathlib import Path

from PIL import Image


def trim_transparent_padding(input_path: Path, output_path: Path, scale: float = 1.08) -> None:
    """裁剪透明边距并放大，让颜色部分超出边界。

    Args:
        scale: 放大倍数，默认 1.08（放大 8%）
    """
    img = Image.open(input_path).convert("RGBA")
    bbox = img.getbbox()  # 非透明像素的边界框
    if bbox is None:
        print(f"SKIP (fully transparent): {input_path.name}")
        return
    cropped = img.crop(bbox)

    # 保持正方形：取长边，居中放置
    w, h = cropped.size
    side = max(w, h)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(cropped, ((side - w) // 2, (side - h) // 2))

    # 放大图标，让颜色部分超出边界
    new_size = int(side * scale)
    enlarged = square.resize((new_size, new_size), Image.Resampling.LANCZOS)

    # 裁剪回原始尺寸（中心裁剪）
    offset = (new_size - side) // 2
    final = enlarged.crop((offset, offset, offset + side, offset + side))

    final.save(output_path, "PNG")
    print(f"OK: {input_path.name}  {img.size} -> {final.size}  scale={scale:.0%}")


def main():
    icons_dir = Path(__file__).parent.parent / "frontend" / "public" / "static" / "app" / "icons" / "default"
    targets = ["ps.png", "ae.png"]

    for name in targets:
        src = icons_dir / name
        if not src.exists():
            print(f"NOT FOUND: {name}")
            continue
        # 恢复原始文件
        orig = icons_dir / f"{name}.orig"
        if orig.exists():
            shutil.copy2(orig, src)
            print(f"RESTORED: {name} from {orig.name}")
        trim_transparent_padding(src, src, scale=1.08)


if __name__ == "__main__":
    main()
