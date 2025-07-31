-- PostgreSQL初期化スクリプト
-- 競馬予想AIシステム用データベーススキーマ

-- 拡張機能の有効化
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 日本語検索用

-- スキーマ作成
CREATE SCHEMA IF NOT EXISTS keiba;

-- デフォルトスキーマ設定
SET search_path TO keiba, public;

-- ========================================
-- 基本テーブル
-- ========================================

-- 競馬場マスタ
CREATE TABLE IF NOT EXISTS racecourses (
    id SERIAL PRIMARY KEY,
    jra_code VARCHAR(2) UNIQUE NOT NULL,
    name VARCHAR(50) NOT NULL,
    name_kana VARCHAR(100),
    location VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- レース情報
CREATE TABLE IF NOT EXISTS races (
    id SERIAL PRIMARY KEY,
    race_key VARCHAR(20) UNIQUE NOT NULL, -- YYYYMMDDRRNN形式
    race_date DATE NOT NULL,
    racecourse_id INTEGER REFERENCES racecourses(id),
    race_number INTEGER NOT NULL,
    race_name VARCHAR(100) NOT NULL,
    race_name_sub VARCHAR(100),
    grade VARCHAR(10), -- G1, G2, G3, OP, etc
    race_type VARCHAR(10) NOT NULL, -- 芝, ダート
    distance INTEGER NOT NULL, -- メートル単位
    direction VARCHAR(10), -- 右, 左, 直線
    weather VARCHAR(10), -- 晴, 曇, 雨, 雪
    track_condition VARCHAR(10), -- 良, 稍重, 重, 不良
    prize_money JSONB, -- 賞金情報をJSON形式で保存
    entry_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 馬情報
CREATE TABLE IF NOT EXISTS horses (
    id SERIAL PRIMARY KEY,
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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 騎手マスタ
CREATE TABLE IF NOT EXISTS jockeys (
    id SERIAL PRIMARY KEY,
    jockey_id VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(50) NOT NULL,
    name_kana VARCHAR(100),
    birth_date DATE,
    license_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 調教師マスタ
CREATE TABLE IF NOT EXISTS trainers (
    id SERIAL PRIMARY KEY,
    trainer_id VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(50) NOT NULL,
    name_kana VARCHAR(100),
    belonging VARCHAR(20), -- 美浦, 栗東
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- レース関連テーブル
-- ========================================

-- 出走情報
CREATE TABLE IF NOT EXISTS race_entries (
    id SERIAL PRIMARY KEY,
    race_id INTEGER REFERENCES races(id),
    horse_id INTEGER REFERENCES horses(id),
    post_position INTEGER NOT NULL, -- 枠番
    horse_number INTEGER NOT NULL, -- 馬番
    jockey_id INTEGER REFERENCES jockeys(id),
    trainer_id INTEGER REFERENCES trainers(id),
    weight_carried DECIMAL(4,1) NOT NULL, -- 斤量
    horse_weight INTEGER, -- 馬体重
    horse_weight_diff INTEGER, -- 馬体重増減
    age INTEGER NOT NULL,
    odds_win DECIMAL(6,1), -- 単勝オッズ
    odds_place_min DECIMAL(6,1), -- 複勝オッズ（最小）
    odds_place_max DECIMAL(6,1), -- 複勝オッズ（最大）
    popularity INTEGER, -- 人気順位
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(race_id, horse_number)
);

-- レース結果
CREATE TABLE IF NOT EXISTS race_results (
    id SERIAL PRIMARY KEY,
    race_entry_id INTEGER REFERENCES race_entries(id) UNIQUE,
    finish_position INTEGER, -- 着順
    finish_time INTERVAL, -- タイム
    last_3f_time DECIMAL(4,1), -- 上がり3ハロン
    corner_positions VARCHAR(20), -- 通過順位
    remarks TEXT, -- 備考
    prize_money INTEGER, -- 獲得賞金
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- オッズ履歴（時系列データ）
CREATE TABLE IF NOT EXISTS odds_history (
    id SERIAL PRIMARY KEY,
    race_id INTEGER REFERENCES races(id),
    horse_number INTEGER NOT NULL,
    odds_type VARCHAR(20) NOT NULL, -- win, place, quinella, etc
    odds_value DECIMAL(8,1) NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_odds_history_race_time (race_id, recorded_at)
);

-- ========================================
-- 予測・分析関連テーブル
-- ========================================

-- 予測結果
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    race_id INTEGER REFERENCES races(id),
    model_name VARCHAR(50) NOT NULL,
    model_version VARCHAR(20),
    prediction_data JSONB NOT NULL, -- 予測結果の詳細
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_predictions_race_model (race_id, model_name)
);

-- 特徴量キャッシュ
CREATE TABLE IF NOT EXISTS feature_cache (
    id SERIAL PRIMARY KEY,
    race_id INTEGER REFERENCES races(id),
    horse_id INTEGER REFERENCES horses(id),
    feature_type VARCHAR(50) NOT NULL,
    feature_data JSONB NOT NULL,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(race_id, horse_id, feature_type)
);

-- MLflow実験結果保存用（オプション）
CREATE TABLE IF NOT EXISTS mlflow_experiments (
    experiment_id SERIAL PRIMARY KEY,
    name VARCHAR(256) UNIQUE NOT NULL,
    artifact_location VARCHAR(256),
    lifecycle_stage VARCHAR(32),
    creation_time BIGINT,
    last_update_time BIGINT
);

-- ========================================
-- インデックス
-- ========================================

-- レース検索用
CREATE INDEX idx_races_date ON races(race_date);
CREATE INDEX idx_races_racecourse ON races(racecourse_id);
CREATE INDEX idx_races_grade ON races(grade) WHERE grade IS NOT NULL;

-- 馬検索用
CREATE INDEX idx_horses_name ON horses(name);
CREATE INDEX idx_horses_name_trgm ON horses USING gin (name gin_trgm_ops);

-- 出走情報検索用
CREATE INDEX idx_race_entries_horse ON race_entries(horse_id);
CREATE INDEX idx_race_entries_jockey ON race_entries(jockey_id);

-- 結果検索用
CREATE INDEX idx_race_results_position ON race_results(finish_position);

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
-- 関数・トリガー
-- ========================================

-- 更新日時自動更新トリガー
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 各テーブルにトリガーを設定
CREATE TRIGGER update_racecourses_updated_at BEFORE UPDATE ON racecourses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_races_updated_at BEFORE UPDATE ON races
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_horses_updated_at BEFORE UPDATE ON horses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_jockeys_updated_at BEFORE UPDATE ON jockeys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_trainers_updated_at BEFORE UPDATE ON trainers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_race_entries_updated_at BEFORE UPDATE ON race_entries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_race_results_updated_at BEFORE UPDATE ON race_results
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

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
ON CONFLICT (jra_code) DO NOTHING;

-- ========================================
-- 権限設定
-- ========================================

-- アプリケーション用ユーザーに必要な権限を付与
GRANT ALL PRIVILEGES ON SCHEMA keiba TO keiba_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA keiba TO keiba_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA keiba TO keiba_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA keiba TO keiba_user;