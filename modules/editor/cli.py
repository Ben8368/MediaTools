"""
editor CLI - 剪映 API 剪辑模块命令行接口

用法（通过 main.py 调用）:
    python main.py edit create-draft [--width 1080] [--height 1920]
    python main.py edit add-video --draft-id <id> --file <path>
    python main.py edit gen-video --draft-id <id>
    python main.py edit status --task-id <id>
    python main.py edit server start|stop|status

注意：本模块需要 capcut-mate 服务运行（默认 http://localhost:30000）
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import CAPCUT_MATE_BASE_URL
from modules.editor.adapter import CapcutAdapter


def main():
    parser = argparse.ArgumentParser(
        description="剪映 API 剪辑工具（基于 capcut-mate）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
前置条件:
  需要 capcut-mate 服务运行（默认 {CAPCUT_MATE_BASE_URL}）
  
启动 capcut-mate 服务:
  cd vendor/capcut-mate
  uvicorn main:app --host 0.0.0.0 --port 30000

或使用 Docker:
  cd vendor/capcut-mate
  docker-compose up -d
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 创建草稿
    create_p = subparsers.add_parser("create-draft", help="创建新草稿")
    create_p.add_argument("--width", type=int, default=1080, help="画布宽度")
    create_p.add_argument("--height", type=int, default=1920, help="画布高度")

    # 添加视频
    add_video_p = subparsers.add_parser("add-video", help="添加视频素材")
    add_video_p.add_argument("--draft-id", required=True, help="草稿 ID")
    add_video_p.add_argument("--file", required=True, help="视频文件路径")
    add_video_p.add_argument("--start", type=int, default=0, help="起始时间（微秒）")
    add_video_p.add_argument("--end", type=int, default=None, help="结束时间（微秒）")

    # 生成视频
    gen_p = subparsers.add_parser("gen-video", help="提交视频渲染任务")
    gen_p.add_argument("--draft-id", required=True, help="草稿 ID")

    # 查询状态
    status_p = subparsers.add_parser("status", help="查询渲染任务状态")
    status_p.add_argument("--task-id", required=True, help="任务 ID")

    # 服务管理
    server_p = subparsers.add_parser("server", help="capcut-mate 服务管理")
    server_p.add_argument("action", choices=["start", "stop", "status"], help="操作")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    if args.command == "server":
        _manage_server(args.action)
        return

    # 其他命令需要连接 capcut-mate 服务
    try:
        adapter = CapcutAdapter(mode="http")
    except Exception as e:
        print(f"[Error] 无法连接 capcut-mate 服务: {e}")
        print(f"请确认服务已启动: {CAPCUT_MATE_BASE_URL}")
        sys.exit(1)

    try:
        if args.command == "create-draft":
            result = adapter.create_draft(args.width, args.height)
            print("草稿创建成功:")
            print(f"  draft_id: {result.get('draft_id')}")
            print(f"  draft_url: {result.get('draft_url')}")

        elif args.command == "add-video":
            video_info = {
                "url": args.file,
                "start": args.start,
                "end": args.end if args.end is not None else 10000000,  # 默认 10 秒
            }
            draft_url = f"{CAPCUT_MATE_BASE_URL}/openapi/capcut-mate/v1/get_draft?draft_id={args.draft_id}"
            result = adapter.add_videos(draft_url, [video_info])
            print(f"视频添加成功: {json.dumps(result, ensure_ascii=False)}")

        elif args.command == "gen-video":
            result = adapter.gen_video(args.draft_id)
            print("渲染任务已提交:")
            print(f"  task_id: {result.get('task_id')}")
            print("使用以下命令查询进度:")
            print(f"  python main.py edit status --task-id {result.get('task_id')}")

        elif args.command == "status":
            result = adapter.gen_video_status(args.task_id)
            print(f"任务状态: {result.get('status')}")
            print(f"进度: {result.get('progress', 0) * 100:.1f}%")
            if result.get("output_url"):
                print(f"输出: {result['output_url']}")
    except Exception as e:
        print(f"[Error] capcut-mate 调用失败: {e}")
        print(f"请确认服务可访问: {CAPCUT_MATE_BASE_URL}")
        sys.exit(1)
    finally:
        adapter.close()


def _manage_server(action: str):
    """管理 capcut-mate 服务"""
    capcut_dir = Path(__file__).parent.parent.parent / "vendor" / "capcut-mate"

    if action == "start":
        print("启动 capcut-mate 服务...")
        print("请手动执行以下命令:")
        print(f"  cd {capcut_dir}")
        print("  uvicorn main:app --host 0.0.0.0 --port 30000")
        print("或使用 Docker:")
        print(f"  cd {capcut_dir}")
        print("  docker-compose up -d")

    elif action == "stop":
        print("停止 capcut-mate 服务...")
        print("如果使用 Docker，请执行:")
        print(f"  cd {capcut_dir}")
        print("  docker-compose down")

    elif action == "status":
        import requests
        try:
            resp = requests.get(f"{CAPCUT_MATE_BASE_URL}/docs", timeout=2)
            if resp.status_code == 200:
                print(f"capcut-mate 服务运行中: {CAPCUT_MATE_BASE_URL}")
            else:
                print("capcut-mate 服务状态异常")
        except requests.exceptions.RequestException:
            print("capcut-mate 服务未运行")
