"""Модуль представлений таблиц для БД"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()  # создаем объект SQLAlchemy


class ParsedData(db.Model):
    """Класс все собранные ссылки с сайта"""
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    links_from_page = db.Column(db.Text, default='No urls from this page')  # ссылки с страниц сайта


class SiteConfig(db.Model):
    """Класс данных сайта для сбора ссылок"""
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    index_site_link = db.Column(db.String(255), nullable=False)  # главный домен
    link_url_start = db.Column(db.String(255), nullable=False)  # страница старта для парсинга
    upload_path_folder = db.Column(db.String(255), nullable=False, default='')  # путь к папке сайта с файлами
