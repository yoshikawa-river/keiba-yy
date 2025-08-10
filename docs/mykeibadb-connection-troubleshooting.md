# mykeibaDB接続トラブルシューティング

## エラー: Command Timeout expired

### 原因
1. **ネットワーク接続の問題**
   - JRA-VANサーバーへの接続がブロックされている
   - ファイアウォールでポート3306がブロックされている
   - VPNが必要だが接続していない

2. **認証情報の問題**
   - JRA-VANのユーザー名/パスワードが間違っている
   - アカウントが有効化されていない

3. **サーバー側の問題**
   - メンテナンス中
   - アクセス制限（IPアドレス制限など）

## 解決方法

### 1. JRA-VAN契約状況の確認
- JRA-VAN DataLabにログインできるか確認
- mykeibaDBサービスが契約済みか確認
- 接続情報（ホスト名、ユーザー名、パスワード）を確認

### 2. ネットワーク診断
```bash
# JRA-VANサーバーへの接続テスト（ホスト名は実際のものに変更）
ping mykeibadb.jravan.jp
nslookup mykeibadb.jravan.jp
telnet mykeibadb.jravan.jp 3306
```

### 3. ローカルMySQLへの直接接続（データ保存先）
```bash
# ローカルMySQLは正常に動作しています
mysql -h localhost -P 3306 -uroot -proot_password keiba_db
```

### 4. 代替方法

#### A. CSVダウンロード → インポート
1. JRA-VAN DataLabからCSVファイルをダウンロード
2. `volumes/csv_import/`に配置
3. インポートスクリプトを実行

#### B. APIアクセス（利用可能な場合）
1. JRA-VAN APIのアクセストークンを取得
2. REST API経由でデータ取得

#### C. 手動同期スクリプト
```python
# scripts/sync_mykeibadb.pyを使用
python scripts/sync_mykeibadb.py full
```

## 設定ファイルの場所

### Windows
- `C:\Program Files\mykeibaDB\config.ini`
- `%APPDATA%\mykeibaDB\settings.ini`

### Mac
- `/Applications/mykeibaDB.app/Contents/Resources/config.ini`
- `~/Library/Application Support/mykeibaDB/settings.ini`

## よくある質問

### Q: ローカルで動作確認したい
A: ローカルMySQLは準備完了です。サンプルデータをインポートして開発を進められます。

### Q: JRA-VANサーバーに接続できない
A: 以下を確認：
1. JRA-VAN契約が有効か
2. IPアドレス制限がないか
3. VPN接続が必要か
4. メンテナンス情報を確認

### Q: タイムアウトを延長したい
A: 設定ファイルで以下を調整：
```ini
ConnectionTimeout=120  # 120秒に延長
CommandTimeout=600     # 10分に延長
```