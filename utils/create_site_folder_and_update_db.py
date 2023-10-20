# Функция создания папки в директории uploads по названию домена сайта
# формируем имя папки (директории)
# создание папки сайта в uploads
# сохранение в бд путь к папке
import os

from flask import render_template, flash

from models import SiteConfig
from urllib.parse import unquote


def create_site_folder_and_update_db(app, db, index_site_link, link_url_start):
    """
    :param app: - объект приложение
    :param db: - объект базы данных
    :param index_site_link: - URL основного домена
    :param link_url_start: - URL стартовой страницы
    :return:
    """
    # --------- Блок - если запись ссылок прошла успешно создаем имя и корневую папку для сайта в uploads
    # название папки такое же как домен (с заменой знаков)

    # формируем допустимое имя папки (удаляем лишние знаки)
    file_name = unquote(index_site_link)
    for ch in ['http://', 'https://', ':', '/', '.']:
        if ch == 'http://' or ch == 'https://':
            file_name = file_name.replace(ch, '')
        elif ch in file_name:
            file_name = file_name.replace(ch, '_')

    file_name = file_name.strip('_')  # удаляем лишнее в конце и начале
    print(f'Название папки для сайта: {file_name}')
    # END - формируем допустимое имя папки (удаляем лишние знаки)

    # Путь к файлу в папке "uploads" (используя значение из файла конфигурации приложения)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)  # file_path содержит относительный путь к файлу в папке "uploads"
    print(f'Путь к папке: {file_path}')
    # END путь к файлу в папке "uploads" (используя значение из файла конфигурации приложения)

    # --------- Блок создание папки по названию запрошеного сайта с проверкой и записью в бд
    try:
        # Проверяем, существует ли папка в uploads, если нет, создаем ее
        if not os.path.exists(file_path):
            os.makedirs(file_path)  # создаем папку
            print(f'Папка создана проверьте директорию uploads\\{file_name}')
            # в таблицу SiteConfig записываем путь к папке в поле upload_path_folder
            data_file_path = SiteConfig.query.first()  # Получаем первую запись из таблицы
            if data_file_path:  # Если запись не пустая
                data_file_path.upload_path_folder = file_path  # Устанавливаем значение поля upload_path_folder
                db.session.commit()  # Сохраняем изменения в базе данных
                print(f'Путь к папке с сайтом записан в БД: {data_file_path.upload_path_folder}')

        else:
            print("папка уже существует в uploads")
            print('_____________________________________')

        print(f'\nГлавная страница сайта: {unquote(index_site_link)}')
        print(f'Страница для парсинга: {unquote(link_url_start)}')
        print('_____________________________________')
        # --------- END Блок создание папки по названию запрошеного сайта с проверкой и записью в бд
        # Если все ок перенаправляем на страницу начала процесса парсинга

        return True

    except Exception as err:
        # Если произошла ошибка, откатываем изменения в базе данных
        db.session.rollback()
        print(f'При создании главной папки возникли проблемы.: {err}')
        flash('При создании главной папки возникли проблемы.')
        return render_template('error.html', error_message=str(err))
