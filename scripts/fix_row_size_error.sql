-- MySQL Row Size Too Large エラー修正スクリプト
-- エラー: Row size too large (> 8126)
-- 解決策: VARCHAR型をTEXT型に変更、行フォーマットをDYNAMICまたはCOMPRESSEDに設定

-- 1. InnoDBのデフォルト設定を最適化
SET GLOBAL innodb_strict_mode = OFF;
SET GLOBAL innodb_default_row_format = 'DYNAMIC';

-- 2. データベースを選択
USE keiba_db;

-- 3. 既存テーブルの行フォーマットを変更（例）
-- ALTER TABLE your_table_name ROW_FORMAT=DYNAMIC;

-- 4. 大きなVARCHAR列をTEXT型に変更するサンプル
-- 以下は一般的な競馬データテーブルの修正例

-- レーステーブルの修正（存在する場合）
DROP TABLE IF EXISTS races_new;
CREATE TABLE IF NOT EXISTS races_new (
    race_id VARCHAR(20) PRIMARY KEY,
    race_date DATE NOT NULL,
    place_code VARCHAR(10),
    race_number INT,
    race_name TEXT,  -- VARCHAR(255) → TEXT
    race_condition TEXT,  -- VARCHAR(500) → TEXT
    distance INT,
    track_type VARCHAR(10),
    track_condition VARCHAR(10),
    weather VARCHAR(10),
    race_comment TEXT,  -- 長いコメントはTEXT型
    INDEX idx_race_date (race_date),
    INDEX idx_place (place_code)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 馬テーブルの修正（存在する場合）
DROP TABLE IF EXISTS horses_new;
CREATE TABLE IF NOT EXISTS horses_new (
    horse_id VARCHAR(20) PRIMARY KEY,
    horse_name VARCHAR(100),
    horse_name_eng VARCHAR(100),
    birth_date DATE,
    sex VARCHAR(10),
    color VARCHAR(20),
    father_name VARCHAR(100),
    mother_name VARCHAR(100),
    trainer_name VARCHAR(50),
    owner_name VARCHAR(100),
    breeder_name VARCHAR(100),
    breeding_farm TEXT,  -- 長い場合はTEXT
    comment TEXT,  -- コメントはTEXT型
    INDEX idx_horse_name (horse_name),
    INDEX idx_birth (birth_date)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- レース結果テーブルの修正（存在する場合）
DROP TABLE IF EXISTS race_results_new;
CREATE TABLE IF NOT EXISTS race_results_new (
    result_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    race_id VARCHAR(20),
    horse_id VARCHAR(20),
    finish_order INT,
    gate_number INT,
    horse_number INT,
    jockey_name VARCHAR(50),
    trainer_name VARCHAR(50),
    horse_weight INT,
    weight_change INT,
    time_seconds DECIMAL(5,2),
    margin VARCHAR(20),
    corner_positions VARCHAR(50),
    last_3f DECIMAL(4,1),
    odds DECIMAL(6,1),
    popularity INT,
    comment TEXT,  -- 長いコメントはTEXT型
    INDEX idx_race (race_id),
    INDEX idx_horse (horse_id),
    INDEX idx_result (race_id, finish_order)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- オッズテーブルの修正（存在する場合）
DROP TABLE IF EXISTS odds_new;
CREATE TABLE IF NOT EXISTS odds_new (
    odds_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    race_id VARCHAR(20),
    bet_type VARCHAR(20),
    horse_numbers VARCHAR(50),
    odds_value DECIMAL(10,1),
    popularity INT,
    INDEX idx_race_bet (race_id, bet_type)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. パフォーマンス設定テーブル（大きなデータ用）
DROP TABLE IF EXISTS large_data_table;
CREATE TABLE IF NOT EXISTS large_data_table (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    data_type VARCHAR(50),
    data_content LONGTEXT,  -- 非常に大きなデータ用
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_type (data_type)
) ENGINE=InnoDB ROW_FORMAT=COMPRESSED DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. 汎用的な修正関数
-- 既存テーブルのVARCHAR列をTEXTに変換する例
DELIMITER $$
CREATE PROCEDURE ConvertVarcharToText(IN table_name VARCHAR(100))
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE column_name VARCHAR(100);
    DECLARE column_type VARCHAR(100);
    DECLARE cur CURSOR FOR 
        SELECT COLUMN_NAME, COLUMN_TYPE 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = 'keiba_db' 
        AND TABLE_NAME = table_name
        AND DATA_TYPE = 'varchar'
        AND CHARACTER_MAXIMUM_LENGTH > 255;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
    
    OPEN cur;
    
    read_loop: LOOP
        FETCH cur INTO column_name, column_type;
        IF done THEN
            LEAVE read_loop;
        END IF;
        
        SET @sql = CONCAT('ALTER TABLE ', table_name, ' MODIFY COLUMN ', column_name, ' TEXT');
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END LOOP;
    
    CLOSE cur;
    
    -- 行フォーマットをDYNAMICに変更
    SET @sql = CONCAT('ALTER TABLE ', table_name, ' ROW_FORMAT=DYNAMIC');
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
END$$
DELIMITER ;

-- 7. 設定確認クエリ
SELECT 
    TABLE_NAME,
    ROW_FORMAT,
    TABLE_ROWS,
    AVG_ROW_LENGTH,
    DATA_LENGTH,
    INDEX_LENGTH
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'keiba_db'
ORDER BY DATA_LENGTH DESC;