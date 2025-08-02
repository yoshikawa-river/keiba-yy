#!/usr/bin/env python3
"""
通知テスト用のPythonスクリプト
フィボナッチ数列を計算して結果を表示する
"""


def fibonacci(n):
    """n番目のフィボナッチ数を計算"""
    if n <= 0:
        return 0
    if n == 1:
        return 1
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def main():
    # 最初の10個のフィボナッチ数を表示
    for i in range(10):
        pass


if __name__ == "__main__":
    main()
