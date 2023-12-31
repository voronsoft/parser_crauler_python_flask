""" Файл настроек для приложения app.py"""
import os
import secrets

# Путь к корню проекта Flask относительно местоположения файла config.py
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# указываем путь к базе данных (если запускаем напрямую)
# SQLALCHEMY_DATABASE_URI = 'mysql://root:root@localhost:3306/db_parser'

# указываем путь к базе данных ( для подключения посредством docker)
# mysql это название имени сервиса из docker-compose.yml
SQLALCHEMY_DATABASE_URI = 'mysql://root:root@mysql:3306/db_parser'

# Секретный ключ
SECRET_KEY = secrets.token_hex(16)

# Режим отладки
DEBUG = True

# Путь к папке для загрузок
UPLOAD_FOLDER = 'uploads'
