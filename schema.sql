CREATE TABLE IF NOT EXISTS user_locks (
    user_id INTEGER PRIMARY KEY,
    status TEXT DEFAULT 'free',
    updated_at INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS staging (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT,
    file_name TEXT,
    media_type TEXT,
    title TEXT,
    year TEXT,
    season INTEGER,
    episode INTEGER,
    episode_end INTEGER,
    part INTEGER,
    quality TEXT,
    category TEXT DEFAULT 'movie',
    status TEXT DEFAULT 'pending',
    created_at INTEGER
);

CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    year TEXT,
    order_index INTEGER DEFAULT 0,
    category TEXT DEFAULT 'movie'
);

CREATE TABLE IF NOT EXISTS movie_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_id INTEGER,
    quality TEXT,
    file_id TEXT,
    FOREIGN KEY (movie_id) REFERENCES movies(id)
);

CREATE TABLE IF NOT EXISTS shows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    order_index INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS seasons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    show_id INTEGER,
    season_number INTEGER,
    FOREIGN KEY (show_id) REFERENCES shows(id)
);

CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id INTEGER,
    episode_number INTEGER,
    FOREIGN KEY (season_id) REFERENCES seasons(id)
);

CREATE TABLE IF NOT EXISTS episode_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id INTEGER,
    quality TEXT,
    part INTEGER,
    file_id TEXT,
    FOREIGN KEY (episode_id) REFERENCES episodes(id)
);

CREATE TABLE IF NOT EXISTS approved_users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    approved_at INTEGER
);

CREATE INDEX IF NOT EXISTS idx_movie_files_movie_id ON movie_files(movie_id);
CREATE INDEX IF NOT EXISTS idx_seasons_show_id ON seasons(show_id);
CREATE INDEX IF NOT EXISTS idx_episodes_season_id ON episodes(season_id);
CREATE INDEX IF NOT EXISTS idx_episode_files_episode_id ON episode_files(episode_id);

CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT,
    detail TEXT,
    created_at INTEGER
);

CREATE INDEX IF NOT EXISTS idx_activity_log_created_at ON activity_log(created_at);
CREATE INDEX IF NOT EXISTS idx_activity_log_user_id ON activity_log(user_id);
