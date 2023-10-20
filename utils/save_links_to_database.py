# Функция для сохранения данных из файла 'links.txt' в базу данных ParsedData
from models import db, ParsedData


def save_links_to_database():
    """Функция для сохранения данных из файла 'links.txt' в базу данных ParsedData"""
    try:
        with open('links.txt', 'r', encoding='utf-8') as file:
            links = file.readlines()

        # Очищаем таблицу ParsedData перед добавлением новых данных
        db.session.query(ParsedData).delete()
        db.session.commit()

        # Добавляем ссылки в базу данных
        for link in links:
            parsed_data = ParsedData(links_from_page=link.strip())
            db.session.add(parsed_data)

        db.session.commit()

        return True
    except Exception as err:
        # В случае ошибки откатываем транзакцию
        db.session.rollback()
        print(f"Произошла ошибка при записи в базу данных (ссылки из links.txt в БД: {err}"
              f"Ошибка вызвана в файле - utils/save_links_to_database.py")
        return str(err)
