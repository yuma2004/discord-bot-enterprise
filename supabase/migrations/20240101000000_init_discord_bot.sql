-- 企業用Discord Bot 初期データベーススキーマ
-- マイグレーション日時: 2024-01-01 00:00:00

-- ユーザーテーブル
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    discord_id VARCHAR(20) UNIQUE NOT NULL,
    username VARCHAR(100) NOT NULL,
    display_name VARCHAR(100),
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 日報テーブル
CREATE TABLE IF NOT EXISTS daily_reports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    report_date DATE NOT NULL,
    content TEXT NOT NULL,
    mood VARCHAR(10) DEFAULT 'normal',
    tasks_completed INTEGER DEFAULT 0,
    challenges TEXT,
    next_day_plan TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, report_date)
);

-- タスクテーブル
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    priority VARCHAR(10) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    due_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 出退勤テーブル
CREATE TABLE IF NOT EXISTS attendance (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    work_date DATE NOT NULL,
    clock_in_time TIMESTAMP WITH TIME ZONE,
    clock_out_time TIMESTAMP WITH TIME ZONE,
    break_start_time TIMESTAMP WITH TIME ZONE,
    break_end_time TIMESTAMP WITH TIME ZONE,
    total_break_minutes INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'absent' CHECK (status IN ('absent', 'present', 'break', 'left')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, work_date)
);

-- 設定テーブル
CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- インデックスの作成（パフォーマンス向上）
CREATE INDEX IF NOT EXISTS idx_users_discord_id ON users(discord_id);
CREATE INDEX IF NOT EXISTS idx_daily_reports_user_id ON daily_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_daily_reports_date ON daily_reports(report_date);
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_attendance_user_id ON attendance(user_id);
CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(work_date);

-- 更新日時の自動更新トリガー関数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 各テーブルにトリガーを追加
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_daily_reports_updated_at 
    BEFORE UPDATE ON daily_reports 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tasks_updated_at 
    BEFORE UPDATE ON tasks 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_attendance_updated_at 
    BEFORE UPDATE ON attendance 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_settings_updated_at 
    BEFORE UPDATE ON settings 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 初期設定データの挿入
INSERT INTO settings (key, value, description) VALUES
('app_version', '1.0.0', 'アプリケーションバージョン'),
('maintenance_mode', 'false', 'メンテナンスモード'),
('daily_report_time', '17:00', '日報リマインド時刻'),
('task_reminder_days', '1', 'タスクリマインド日数'),
('timezone', 'Asia/Tokyo', 'タイムゾーン')
ON CONFLICT (key) DO NOTHING;

-- RLS（Row Level Security）の有効化
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;

-- ポリシーの作成（基本的なセキュリティ）
-- ユーザーは自分のデータのみアクセス可能

-- ユーザーテーブルポリシー
CREATE POLICY "Users can view their own data" ON users
    FOR SELECT USING (discord_id = current_setting('app.current_user_discord_id', true));

CREATE POLICY "Users can update their own data" ON users
    FOR UPDATE USING (discord_id = current_setting('app.current_user_discord_id', true));

-- 日報テーブルポリシー
CREATE POLICY "Users can view their own reports" ON daily_reports
    FOR SELECT USING (user_id = (
        SELECT id FROM users WHERE discord_id = current_setting('app.current_user_discord_id', true)
    ));

CREATE POLICY "Users can insert their own reports" ON daily_reports
    FOR INSERT WITH CHECK (user_id = (
        SELECT id FROM users WHERE discord_id = current_setting('app.current_user_discord_id', true)
    ));

-- タスクテーブルポリシー
CREATE POLICY "Users can view their own tasks" ON tasks
    FOR SELECT USING (user_id = (
        SELECT id FROM users WHERE discord_id = current_setting('app.current_user_discord_id', true)
    ));

CREATE POLICY "Users can manage their own tasks" ON tasks
    FOR ALL USING (user_id = (
        SELECT id FROM users WHERE discord_id = current_setting('app.current_user_discord_id', true)
    ));

-- 出退勤テーブルポリシー
CREATE POLICY "Users can view their own attendance" ON attendance
    FOR SELECT USING (user_id = (
        SELECT id FROM users WHERE discord_id = current_setting('app.current_user_discord_id', true)
    ));

CREATE POLICY "Users can manage their own attendance" ON attendance
    FOR ALL USING (user_id = (
        SELECT id FROM users WHERE discord_id = current_setting('app.current_user_discord_id', true)
    ));

-- 設定テーブルポリシー（読み取り専用）
CREATE POLICY "Everyone can read settings" ON settings
    FOR SELECT TO authenticated, anon USING (true);

-- マイグレーション完了ログ
INSERT INTO settings (key, value, description) VALUES
('migration_init', NOW()::text, '初期マイグレーション実行日時')
ON CONFLICT (key) DO UPDATE SET value = NOW()::text; 