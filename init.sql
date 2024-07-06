-- Создание таблицы vacancies
CREATE TABLE IF NOT EXISTS vacancies (
    title TEXT,
    link TEXT UNIQUE,
    company TEXT,
    area TEXT,
    salary TEXT,
    experience_required TEXT
);

-- Создание уникального индекса на поле link (для предотвращения дубликатов)
CREATE UNIQUE INDEX IF NOT EXISTS idx_vacancies_link ON vacancies (link);
