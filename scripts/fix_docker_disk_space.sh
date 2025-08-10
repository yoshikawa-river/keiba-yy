#!/bin/bash

echo "========================================="
echo "Docker容量問題解決スクリプト"
echo "========================================="

# 現在の状況を表示
echo -e "\n📊 現在のDocker使用状況:"
docker system df

echo -e "\n📦 MySQLボリューム使用量:"
docker exec keiba-mysql df -h /var/lib/mysql 2>/dev/null || echo "MySQLコンテナが起動していません"

# 不要なリソースのクリーンアップ
echo -e "\n🧹 クリーンアップオプション:"
echo "1. 停止中のコンテナを削除"
echo "2. 未使用のイメージを削除"
echo "3. 未使用のボリュームを削除（注意：データが消える）"
echo "4. ビルドキャッシュをクリア"
echo "5. すべてクリーンアップ（Docker prune）"
echo "6. MySQLのログファイルをクリア"
echo "7. スキップ"

read -p "選択してください [1-7]: " choice

case $choice in
    1)
        echo "停止中のコンテナを削除中..."
        docker container prune -f
        ;;
    2)
        echo "未使用のイメージを削除中..."
        docker image prune -a -f
        ;;
    3)
        echo "⚠️ 警告: これにより未使用のボリュームが削除されます"
        read -p "本当に実行しますか？ (y/N): " confirm
        if [[ $confirm == "y" ]]; then
            docker volume prune -f
        fi
        ;;
    4)
        echo "ビルドキャッシュをクリア中..."
        docker builder prune -a -f
        ;;
    5)
        echo "⚠️ 警告: すべての未使用リソースを削除します"
        read -p "本当に実行しますか？ (y/N): " confirm
        if [[ $confirm == "y" ]]; then
            docker system prune -a --volumes -f
        fi
        ;;
    6)
        echo "MySQLのログファイルをクリア中..."
        docker-compose exec mysql sh -c "rm -f /var/lib/mysql/*.log /var/lib/mysql/mysql-bin.* /var/lib/mysql/ib_logfile*"
        echo "MySQLを再起動します..."
        docker-compose restart mysql
        ;;
    7)
        echo "スキップしました"
        ;;
    *)
        echo "無効な選択です"
        ;;
esac

echo -e "\n📊 クリーンアップ後の状況:"
docker system df

echo -e "\n========================================="
echo "💡 追加の対策:"
echo "========================================="
echo "1. Docker Desktop設定で仮想ディスクサイズを増やす："
echo "   - Docker Desktop → Settings → Resources → Disk image size"
echo "   - 現在の59GBから120GB以上に増やすことを推奨"
echo ""
echo "2. docker-compose.ymlでボリュームを外部ストレージにマウント："
echo "   volumes:"
echo "     - /path/to/external/storage:/var/lib/mysql"
echo ""
echo "3. 不要なテーブルやデータを削除："
echo "   docker-compose exec mysql mysql -uroot -proot_password"
echo "   SHOW DATABASES;"
echo "   DROP DATABASE unnecessary_db;"
echo "========================================="