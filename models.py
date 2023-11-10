"""Модуль представлений таблиц для БД"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()  # создаем объект SQLAlchemy


# Все собранные ссылки с сайта
class ParsedData(db.Model):
    """Класс все собранные ссылки с сайта"""
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    links_from_page = db.Column(db.Text, default='No urls from this page')  # Ссылки с страниц сайта


# Данные сайта для сбора ссылок
class SiteConfig(db.Model):
    """Класс данных сайта для сбора ссылок"""
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    index_site_link = db.Column(db.String(255), nullable=False)  # Главный домен
    link_url_start = db.Column(db.Text, nullable=False)  # Страница старта для парсинга
    upload_path_folder = db.Column(db.String(350), nullable=False, default='')  # Путь к папке сайта с файлами
