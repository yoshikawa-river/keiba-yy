# MySQL Connection Information

## Quick Connection Reference

### Local Connection (同じMac上から)
```
Host: localhost
Port: 3306
User: keiba_user
Pass: keiba_password
DB:   keiba_db
```

### Remote Connection (別のマシンから)
```
Host: 192.168.11.14  # Your Mac's IP
Port: 3306
User: keiba_user
Pass: keiba_password
DB:   keiba_db
```

## MySQL Workbench Settings

1. Click "+" to add new connection
2. Enter these settings:
   - Connection Name: `Keiba AI Docker`
   - Hostname: `localhost`
   - Port: `3306`
   - Username: `keiba_user`
   - Password: `keiba_password` (click "Store in Keychain...")
   - Default Schema: `keiba_db`
3. Click "Test Connection"
4. Click "OK" to save

## Command Line Connection

```bash
# Local connection
mysql -h localhost -P 3306 -u keiba_user -pkeiba_password keiba_db

# Remote connection
mysql -h 192.168.11.14 -P 3306 -u keiba_user -pkeiba_password keiba_db
```

## Docker Status Check

```bash
# Check if MySQL container is running
docker ps | grep keiba-mysql

# Start MySQL container if not running
docker compose up -d mysql

# View MySQL logs
docker logs keiba-mysql
```

## Root Access (Admin only)

```bash
# Root user credentials
Username: root
Password: root_password

# Connect as root
mysql -h localhost -P 3306 -u root -proot_password
```