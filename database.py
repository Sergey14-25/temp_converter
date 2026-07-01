import sqlite3
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

DB_FILE = "temperature_converter.db"


class DatabaseManager:
    "Менеджер базы данных для хранения истории конвертаций"

    def __init__(self):
        "Инициализация менеджера БД"
        self.conn: Optional[sqlite3.Connection] = None

    def init_db(self):
        "Создание таблицы при первом запуске"
        try:
            self.conn = sqlite3.connect(DB_FILE)
            self.conn.row_factory = sqlite3.Row
            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    temp_c REAL NOT NULL,
                    temp_f REAL NOT NULL,
                    temp_k REAL NOT NULL,
                    formula TEXT NOT NULL,
                    notes TEXT,
                    image_path TEXT
                )
            """)
            self.conn.commit()
            logger.info("База данных инициализирована")
        except sqlite3.Error as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            raise

    def insert_record(self, data: Dict) -> int:
        "Добавление записи о конвертации с валидацией"
        try:
            temp_c = float(data["temp_c"])
            temp_f = float(data["temp_f"])
            temp_k = float(data["temp_k"])

            if temp_c < -273.15:
                raise ValueError("Температура ниже абсолютного нуля")

            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT INTO conversions 
                   (temp_c, temp_f, temp_k, formula, notes, image_path) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    temp_c,
                    temp_f,
                    temp_k,
                    data["formula"],
                    data.get("notes", ""),
                    data.get("image_path", "")
                )
            )
            self.conn.commit()
            record_id = cursor.lastrowid
            logger.info(f"Добавлена запись с id={record_id}")
            return record_id
        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка валидации данных: {e}")
            raise
        except sqlite3.Error as e:
            logger.error(f"Ошибка добавления записи: {e}")
            raise

    def get_all(self) -> List[Dict]:
        "Получение всех записей"
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, temp_c, temp_f, temp_k, formula, notes, image_path 
                FROM conversions 
                ORDER BY id DESC
            """)
            records = [dict(row) for row in cursor.fetchall()]
            logger.info(f"Получено {len(records)} записей")
            return records
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения записей: {e}")
            raise

    def update_record(self, data: Dict):
        "Обновление записи с валидацией"
        try:
            temp_c = float(data["temp_c"])
            temp_f = float(data["temp_f"])
            temp_k = float(data["temp_k"])

            cursor = self.conn.cursor()
            cursor.execute(
                """UPDATE conversions 
                   SET temp_c=?, temp_f=?, temp_k=?, formula=?, notes=?, image_path=?
                   WHERE id=?""",
                (
                    temp_c,
                    temp_f,
                    temp_k,
                    data["formula"],
                    data.get("notes", ""),
                    data.get("image_path", ""),
                    data["id"]
                )
            )
            self.conn.commit()
            logger.info(f"Обновлена запись с id={data['id']}")
        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка валидации при обновлении: {e}")
            raise
        except sqlite3.Error as e:
            logger.error(f"Ошибка обновления записи: {e}")
            raise

    def delete_record(self, record_id: int):
        "Удаление записи"
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM conversions WHERE id=?", (record_id,))
            self.conn.commit()
            logger.info(f"Удалена запись с id={record_id}")
        except sqlite3.Error as e:
            logger.error(f"Ошибка удаления записи: {e}")
            raise

    def clear_all(self):
        "Очистка всей таблицы истории."
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM conversions")
            self.conn.commit()
            logger.info("История очищена полностью")
        except sqlite3.Error as e:
            logger.error(f"Ошибка очистки истории: {e}")
            raise

    def close(self):
        "Закрытие соединения с БД"
        try:
            if self.conn:
                self.conn.close()
                logger.info("Соединение с БД закрыто")
        except sqlite3.Error as e:
            logger.error(f"Ошибка при закрытии БД: {e}")
            raise


