"""开发工具脚本集合"""
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def run_tests():
    """运行测试套件"""
    print("运行测试...")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        cwd=PROJECT_ROOT,
    )
    return result.returncode


def run_format():
    """格式化代码"""
    print("格式化代码...")
    subprocess.run([sys.executable, "-m", "black", "."], cwd=PROJECT_ROOT)
    print("完成！")


def run_lint():
    """运行代码检查"""
    print("运行 ruff 检查...")
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "."],
        cwd=PROJECT_ROOT,
    )
    return result.returncode


def run_type_check():
    """运行类型检查"""
    print("运行 mypy 类型检查...")
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "services/", "modules/", "core/"],
        cwd=PROJECT_ROOT,
    )
    return result.returncode


def main():
    import argparse

    parser = argparse.ArgumentParser(description="MediaTools 开发工具")
    parser.add_argument("command", choices=["test", "format", "lint", "typecheck", "all"])

    args = parser.parse_args()

    if args.command == "test":
        sys.exit(run_tests())
    elif args.command == "format":
        run_format()
    elif args.command == "lint":
        sys.exit(run_lint())
    elif args.command == "typecheck":
        sys.exit(run_type_check())
    elif args.command == "all":
        print("=" * 60)
        print("1. 格式化代码")
        print("=" * 60)
        run_format()
        print("\n" + "=" * 60)
        print("2. 代码检查")
        print("=" * 60)
        lint_result = run_lint()
        print("\n" + "=" * 60)
        print("3. 类型检查")
        print("=" * 60)
        type_result = run_type_check()
        print("\n" + "=" * 60)
        print("4. 运行测试")
        print("=" * 60)
        test_result = run_tests()

        if lint_result == 0 and type_result == 0 and test_result == 0:
            print("\n✓ 所有检查通过！")
            sys.exit(0)
        else:
            print("\n✗ 部分检查失败")
            sys.exit(1)


if __name__ == "__main__":
    main()
