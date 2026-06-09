#!/bin/bash
# PARA Tracker 数据库备份脚本
# 用法: ./deploy/backup.sh [备份目录]
set -e

BACKUP_DIR="${1:-/opt/para-tracker/backups}"
DB_DIR="/opt/para-tracker/data"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

# 备份 SQLite 数据库
if [ -f "$DB_DIR/para_tracker.db" ]; then
    cp "$DB_DIR/para_tracker.db" "$BACKUP_DIR/para_tracker_$TIMESTAMP.db"
    echo "✅ 数据库已备份: para_tracker_$TIMESTAMP.db"
else
    echo "⚠️  未找到数据库文件，跳过"
fi

# 备份配置文件
if [ -f "/opt/para-tracker/.env" ]; then
    cp "/opt/para-tracker/.env" "$BACKUP_DIR/env_$TIMESTAMP.bak"
    echo "✅ 配置已备份: env_$TIMESTAMP.bak"
fi

# 删除 30 天前的旧备份
find "$BACKUP_DIR" -name "para_tracker_*.db" -mtime +$RETENTION_DAYS -delete 2>/dev/null
find "$BACKUP_DIR" -name "env_*.bak" -mtime +$RETENTION_DAYS -delete 2>/dev/null

echo "📦 备份目录: $BACKUP_DIR"
echo "🗑️  已清理 $RETENTION_DAYS 天前的旧备份"

# 输出备份大小
du -sh "$BACKUP_DIR" 2>/dev/null || true
