#!/bin/bash

echo "======================================"
echo "Docker ディスク容量チェック"
echo "======================================"

echo -e "\n1️⃣ Docker全体の使用状況:"
docker system df

echo -e "\n2️⃣ MySQLコンテナのディスク容量:"
docker-compose exec mysql df -h /var/lib/mysql 2>/dev/null || echo "MySQLが起動していません"

echo -e "\n3️⃣ MySQLボリュームの詳細:"
docker volume inspect keiba-yy_mysql_data 2>/dev/null | grep -E "Mountpoint|CreatedAt" || echo "ボリュームが見つかりません"

echo -e "\n======================================"
echo "📝 Docker Desktop設定の確認方法:"
echo "======================================"
echo "1. Docker Desktopを開く（メニューバーの🐳アイコン）"
echo "2. Settings（⚙️）をクリック"
echo "3. Resources → Advanced を選択"
echo "4. 'Disk image size'の値を確認"
echo ""
echo "現在の設定が59GBの場合："
echo "  → スライダーを右に動かして120GB以上に設定"
echo "  → 'Apply & Restart'をクリック"
echo ""
echo "⚠️ 重要: docker-compose.ymlの設定だけでは容量は増えません！"
echo "         Docker Desktop側の設定変更が必要です。"
echo "======================================"