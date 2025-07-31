-- MySQL初期化スクリプト
-- 競馬予想AIシステム用データベーススキーマ

-- データベース作成（docker-composeで作成済みの場合はスキップ）
-- CREATE DATABASE IF NOT EXISTS keiba_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE keiba_db;

-- ========================================
-- 基本テーブル
-- ========================================

-- 競馬場マスタ
CREATE TABLE IF NOT EXISTS racecourses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    jra_code VARCHAR(2) UNIQUE NOT NULL,
    name VARCHAR(50) NOT NULL,
    name_kana VARCHAR(100),
    location VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- レース情報
CREATE TABLE IF NOT EXISTS races (
    id INT AUTO_INCREMENT PRIMARY KEY,
    race_key VARCHAR(20) UNIQUE NOT NULL, -- YYYYMMDDRRNN形式
    race_date DATE NOT NULL,
    racecourse_id INT,
    race_number INT NOT NULL,
    race_name VARCHAR(100) NOT NULL,
    race_name_sub VARCHAR(100),
    grade VARCHAR(10), -- G1, G2, G3, OP, etc
    race_type VARCHAR(10) NOT NULL, -- 芝, ダート
    distance INT NOT NULL, -- メートル単位
    direction VARCHAR(10), -- 右, 左, 直線
    weather VARCHAR(10), -- 晴, 曇, 雨, 雪
    track_condition VARCHAR(10), -- 良, 稍重, 重, 不良
    prize_money JSON, -- 賞金情報をJSON形式で保存
    entry_count INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (racecourse_id) REFERENCES racecourses(id),
    INDEX idx_race_date (race_date),
    INDEX idx_racecourse_id (racecourse_id),
    INDEX idx_grade (grade)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 馬情報
CREATE TABLE IF NOT EXISTS horses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    horse_id VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(50) NOT NULL,
    name_kana VARCHAR(100),
    sex VARCHAR(10) NOT NULL, -- 牡, 牝, セ
    birth_date DATE,
    color VARCHAR(20), -- 毛色
    father_name VARCHAR(50),
    mother_name VARCHAR(50),
    mother_father_name VARCHAR(50),
    owner_name VARCHAR(100),
    trainer_name VARCHAR(50),
    breeding_farm VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    FULLTEXT INDEX idx_name_fulltext (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 騎手マスタ
CREATE TABLE IF NOT EXISTS jockeys (
    id INT AUTO_INCREMENT PRIMARY KEY,
    jockey_id VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(50) NOT NULL,
    name_kana VARCHAR(100),
    birth_date DATE,
    license_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 調教師マスタ
CREATE TABLE IF NOT EXISTS trainers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trainer_id VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(50) NOT NULL,
    name_kana VARCHAR(100),
    belonging VARCHAR(20), -- 美浦, 栗東
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- レース関連テーブル
-- ========================================

-- 出走情報
CREATE TABLE IF NOT EXISTS race_entries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    race_id INT,
    horse_id INT,
    post_position INT NOT NULL, -- 枠番
    horse_number INT NOT NULL, -- 馬番
    jockey_id INT,
    trainer_id INT,
    weight_carried DECIMAL(4,1) NOT NULL, -- 斤量
    horse_weight INT, -- 馬体重
    horse_weight_diff INT, -- 馬体重増減
    age INT NOT NULL,
    odds_win DECIMAL(6,1), -- 単勝オッズ
    odds_place_min DECIMAL(6,1), -- 複勝オッズ（最小）
    odds_place_max DECIMAL(6,1), -- 複勝オッズ（最大）
    popularity INT, -- 人気順位
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_race_horse (race_id, horse_number),
    FOREIGN KEY (race_id) REFERENCES races(id),
    FOREIGN KEY (horse_id) REFERENCES horses(id),
    FOREIGN KEY (jockey_id) REFERENCES jockeys(id),
    FOREIGN KEY (trainer_id) REFERENCES trainers(id),
    INDEX idx_horse_id (horse_id),
    INDEX idx_jockey_id (jockey_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- レース結果
CREATE TABLE IF NOT EXISTS race_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    race_entry_id INT UNIQUE,
    finish_position INT, -- 着順
    finish_time TIME, -- タイム
    last_3f_time DECIMAL(4,1), -- 上がり3ハロン
    corner_positions VARCHAR(20), -- 通過順位
    remarks TEXT, -- 備考
    prize_money INT, -- 獲得賞金
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (race_entry_id) REFERENCES race_entries(id),
    INDEX idx_finish_position (finish_position)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- オッズ履歴（時系列データ）
CREATE TABLE IF NOT EXISTS odds_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    race_id INT,
    horse_number INT NOT NULL,
    odds_type VARCHAR(20) NOT NULL, -- win, place, quinella, etc
    odds_value DECIMAL(8,1) NOT NULL,
    recorded_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (race_id) REFERENCES races(id),
    INDEX idx_race_time (race_id, recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 予測・分析関連テーブル
-- ========================================

-- 予測結果
CREATE TABLE IF NOT EXISTS predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    race_id INT,
    model_name VARCHAR(50) NOT NULL,
    model_version VARCHAR(20),
    prediction_data JSON NOT NULL, -- 予測結果の詳細
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (race_id) REFERENCES races(id),
    INDEX idx_race_model (race_id, model_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 特徴量キャッシュ
CREATE TABLE IF NOT EXISTS feature_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    race_id INT,
    horse_id INT,
    feature_type VARCHAR(50) NOT NULL,
    feature_data JSON NOT NULL,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    UNIQUE KEY unique_feature (race_id, horse_id, feature_type),
    FOREIGN KEY (race_id) REFERENCES races(id),
    FOREIGN KEY (horse_id) REFERENCES horses(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- MLflow実験結果保存用（オプション）
CREATE TABLE IF NOT EXISTS mlflow_experiments (
    experiment_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(256) UNIQUE NOT NULL,
    artifact_location VARCHAR(256),
    lifecycle_stage VARCHAR(32),
    creation_time BIGINT,
    last_update_time BIGINT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- ビュー
-- ========================================

-- レース出走表ビュー
CREATE OR REPLACE VIEW v_race_cards AS
SELECT 
    r.id as race_id,
    r.race_date,
    r.race_number,
    r.race_name,
    r.grade,
    r.distance,
    r.race_type,
    rc.name as racecourse_name,
    re.horse_number,
    re.post_position,
    h.name as horse_name,
    h.sex,
    re.age,
    j.name as jockey_name,
    re.weight_carried,
    re.odds_win,
    re.popularity
FROM races r
JOIN racecourses rc ON r.racecourse_id = rc.id
JOIN race_entries re ON r.id = re.race_id
JOIN horses h ON re.horse_id = h.id
JOIN jockeys j ON re.jockey_id = j.id
ORDER BY r.race_date DESC, r.race_number, re.horse_number;

-- ========================================
-- 初期データ投入
-- ========================================

-- 競馬場マスタデータ
INSERT INTO racecourses (jra_code, name, name_kana, location) VALUES
    ('01', '札幌', 'サッポロ', '北海道札幌市'),
    ('02', '函館', 'ハコダテ', '北海道函館市'),
    ('03', '福島', 'フクシマ', '福島県福島市'),
    ('04', '新潟', 'ニイガタ', '新潟県新潟市'),
    ('05', '東京', 'トウキョウ', '東京都府中市'),
    ('06', '中山', 'ナカヤマ', '千葉県船橋市'),
    ('07', '中京', 'チュウキョウ', '愛知県豊明市'),
    ('08', '京都', 'キョウト', '京都府京都市'),
    ('09', '阪神', 'ハンシン', '兵庫県宝塚市'),
    ('10', '小倉', 'コクラ', '福岡県北九州市')
ON DUPLICATE KEY UPDATE name=VALUES(name);

-- ========================================
-- 権限設定（MySQLでは異なる方法で設定）
-- ========================================

-- アプリケーション用ユーザーに必要な権限を付与
-- GRANT ALL PRIVILEGES ON keiba_db.* TO 'keiba_user'@'%';
-- FLUSH PRIVILEGES;