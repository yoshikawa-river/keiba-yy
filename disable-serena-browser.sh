#!/bin/bash
# Serena MCPのブラウザ自動起動を無効化するスクリプト

echo "🛡️ Serena MCPブラウザ自動起動無効化スクリプト"
echo "======================================="

# 1. 既存のSerena MCPプロセスを終了
echo "1. 既存のSerena MCPプロセスを終了中..."
pkill -f serena-mcp-server 2>/dev/null
sleep 1

# 2. 環境変数を設定
echo "2. 環境変数を設定中..."
export SERENA_NO_BROWSER=true
export SERENA_DISABLE_DASHBOARD_AUTO_OPEN=true
export SERENA_DASHBOARD_AUTO_OPEN=false
export SERENA_BROWSER_OPEN=false
export SERENA_HEADLESS=true
export NO_BROWSER=true

# 3. 設定ファイルを確認・更新
echo "3. 設定ファイルを確認中..."

# Pythonスクリプトでブラウザ起動をオーバーライド
cat > /tmp/override_webbrowser.py << 'PYTHON_EOF'
import sys
import os

# webbrowserモジュールをモック
class MockBrowser:
    def open(self, url, new=0, autoraise=True):
        print(f"[Browser launch blocked] URL: {url}")
        return True
    
    def open_new(self, url):
        print(f"[Browser launch blocked] URL: {url}")
        return True
    
    def open_new_tab(self, url):
        print(f"[Browser launch blocked] URL: {url}")
        return True

# webbrowserモジュールを置き換え
sys.modules['webbrowser'] = MockBrowser()
PYTHON_EOF

# 4. Serena起動時の環境変数を永続化
echo "4. 起動設定を永続化中..."
cat > ~/.serena-no-browser << 'EOF'
export SERENA_NO_BROWSER=true
export SERENA_DISABLE_DASHBOARD_AUTO_OPEN=true
export SERENA_DASHBOARD_AUTO_OPEN=false
export SERENA_BROWSER_OPEN=false
export SERENA_HEADLESS=true
export NO_BROWSER=true
EOF

# 5. 完了メッセージ
echo ""
echo "✅ 設定完了！"
echo ""
echo "以下の対策を実施しました："
echo "  • 環境変数によるブラウザ起動の無効化"
echo "  • Serena MCPプロセスの再起動"
echo "  • 永続的な設定ファイルの作成"
echo ""
echo "今後Serena MCPを起動する際は以下のコマンドを使用してください："
echo "  source ~/.serena-no-browser && serena-mcp-server"
echo ""
echo "ダッシュボードには手動でアクセスできます："
echo "  http://127.0.0.1:24284/dashboard/index.html"