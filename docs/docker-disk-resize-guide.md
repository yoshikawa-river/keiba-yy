# Docker Desktop ディスクサイズ増設ガイド

## 📱 macOS版 Docker Desktopの設定手順

### 1. Docker Desktopを開く
- メニューバーのDockerアイコンをクリック
- または、アプリケーションから「Docker Desktop」を起動

### 2. 設定画面を開く
- Docker Desktop画面右上の ⚙️ (Settings) をクリック
- または、メニューバー → Docker Desktop → Settings

### 3. Resourcesタブを選択
- 左サイドバーから「Resources」をクリック
- 「Advanced」を選択

### 4. Disk image sizeを変更
現在の設定: **59GB** → 推奨: **120GB以上**

スライダーまたは数値入力で変更：
- 最小推奨: 120 GB
- 余裕を持たせる場合: 200 GB
- 最大: お使いのMacのディスク容量に依存

### 5. 設定を適用
1. 「Apply & restart」ボタンをクリック
2. Dockerが自動的に再起動します（数分かかります）
3. 再起動完了後、新しいディスクサイズが適用されます

## ⚠️ 重要な注意事項

### データの保持について
- **ボリュームデータは保持されます**
- MySQLのデータも失われません
- ただし、念のためバックアップを推奨

### 設定が見つからない場合
新しいバージョンのDocker Desktopでは：
1. Docker Desktop → Settings
2. 「Resources」→「Disk image size」
3. スライダーで調整

古いバージョンでは：
1. Docker Desktop → Preferences
2. 「Disk」タブ
3. 「Disk image size」を調整

## 🔍 設定確認コマンド

```bash
# Docker全体の情報
docker system df

# 現在の使用状況
docker ps -s

# ボリュームのサイズ
docker volume ls -q | xargs docker volume inspect | grep -E "Name|Mountpoint|Size"
```

## 🚀 設定後の確認

```bash
# MySQLコンテナの容量確認
docker-compose exec mysql df -h /var/lib/mysql

# 期待される結果
# Filesystem      Size  Used Avail Use% Mounted on
# /dev/vda1       120G   50G   66G  43% /var/lib/mysql
```

## 💡 その他の容量管理方法

### 1. 定期的なクリーンアップ
```bash
# 未使用のイメージ、コンテナ、ネットワークを削除
docker system prune -a

# ビルドキャッシュをクリア
docker builder prune -a

# ボリュームの削除（注意：データが消える）
docker volume prune
```

### 2. 外部ストレージの利用
docker-compose.ymlで外部ディレクトリをマウント：
```yaml
volumes:
  - /Volumes/ExternalDrive/mysql:/var/lib/mysql
```

### 3. 不要なデータの削除
```sql
-- MySQLで不要なデータを削除
DROP DATABASE unnecessary_db;
OPTIMIZE TABLE large_table;
```

## トラブルシューティング

### Q: 設定を変更してもサイズが増えない
A: 以下を確認：
1. Docker Desktopを完全に再起動
2. `docker system df`で確認
3. コンテナを再作成: `docker-compose down && docker-compose up -d`

### Q: "No space left on device"エラーが続く
A: 以下の手順：
1. `docker system prune -a --volumes` (注意：全データ削除)
2. Docker Desktopをリセット（Settings → Troubleshoot → Reset to factory defaults）
3. ディスクサイズを設定してから再構築

### Q: Macのディスク容量が足りない
A: 以下の対策：
1. 不要なファイルを削除してMacの空き容量を増やす
2. 外部ドライブを使用
3. Docker Desktop for Macの`.raw`ファイルを外部ドライブに移動（上級者向け）