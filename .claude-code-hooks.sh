#!/bin/bash
# Claude Code起動時にSerena MCPを起動（既に起動している場合はそのまま使用）

# Serena MCPが起動しているか確認
check_serena_running() {
    pgrep -f "serena-mcp-server" > /dev/null 2>&1
    return $?
}

# Serena MCPを起動
start_serena_mcp() {
    # 既に起動している場合はスキップ
    if check_serena_running; then
        echo "✅ Serena MCPは既に起動しています"
        return 0
    fi
    
    echo "🚀 Serena MCPを起動しています..."
    
    # 環境変数を設定してブラウザを開かないようにする
    export SERENA_NO_BROWSER=true
    export SERENA_DISABLE_DASHBOARD_AUTO_OPEN=true
    
    # Serena MCPをバックグラウンドで起動（存在する場合）
    if command -v serena-mcp-server &> /dev/null; then
        nohup serena-mcp-server --context ide-assistant > /tmp/serena-mcp.log 2>&1 &
        echo "✅ Serena MCPを起動しました（PID: $!）"
    else
        echo "⚠️  Serena MCPサーバーが見つかりません"
    fi
}

# Serena MCPのステータスを表示
show_serena_status() {
    if check_serena_running; then
        local pids=$(pgrep -f "serena-mcp-server")
        echo "📊 Serena MCP状態:"
        echo "   - ステータス: 実行中"
        echo "   - プロセスID: $pids"
        echo "   - ダッシュボード: http://127.0.0.1:24284/dashboard/index.html"
        echo "   - ブラウザ自動起動: 無効"
    else
        echo "📊 Serena MCP状態: 停止中"
    fi
}

# メイン処理
start_serena_mcp
show_serena_status