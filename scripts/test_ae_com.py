"""测试 AE COM 连接器的基本功能"""

import sys
from pathlib import Path

# 添加项目根目录到 path
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from adapters.after_effects_runtime import AfterEffectsAutomationAdapter


def test_adapter_status():
    """测试适配器状态"""
    print("=== 测试 AE 适配器状态 ===")
    adapter = AfterEffectsAutomationAdapter()
    status = adapter.get_status()

    print(f"Available: {status['available']}")
    print(f"Platform: {status['platform']}")
    print(f"Source exists: {status['source_exists']}")
    print(f"Windows only: {status['windows_only']}")
    print(f"pywin32: {status['pywin32']}")
    print(f"Src dir: {status['src_dir']}")

    if not status['available']:
        print(f"Reason: {status['reason']}")
        return False
    return True


def test_connector_import():
    """测试连接器导入"""
    print("\n=== 测试连接器导入 ===")
    try:
        adapter = AfterEffectsAutomationAdapter()
        runtime = adapter.load_runtime()
        AfterEffectsConnector = runtime['AfterEffectsConnector']
        print(f"✓ AfterEffectsConnector 导入成功: {AfterEffectsConnector}")
        return True
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        return False


def test_ae_connection():
    """测试 AE 连接（需要 AE 已安装）"""
    print("\n=== 测试 AE 连接 ===")
    try:
        adapter = AfterEffectsAutomationAdapter()
        runtime = adapter.load_runtime()
        AfterEffectsConnector = runtime['AfterEffectsConnector']
        pythoncom = runtime['pythoncom']

        pythoncom.CoInitialize()
        try:
            connector = AfterEffectsConnector()
            connector.connect()
            print("✓ AE 连接成功")

            # 测试简单脚本执行
            result = connector.app.DoScript('app.version;')
            print(f"✓ AE 版本: {result}")

            connector.disconnect()
            return True
        finally:
            pythoncom.CoUninitialize()
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        print("  提示：请确保 After Effects 已安装且可以启动")
        return False


if __name__ == "__main__":
    print("After Effects COM 连接器测试\n")

    # 测试 1: 适配器状态
    if not test_adapter_status():
        print("\n适配器状态检查失败，无法继续测试")
        sys.exit(1)

    # 测试 2: 连接器导入
    if not test_connector_import():
        print("\n连接器导入失败，无法继续测试")
        sys.exit(1)

    # 测试 3: AE 连接（可选，需要 AE 安装）
    print("\n提示：接下来将尝试连接 After Effects")
    print("如果 AE 未安装或未启动，此测试会失败（这是正常的）")
    input("按 Enter 继续...")
    test_ae_connection()

    print("\n=== 测试完成 ===")
