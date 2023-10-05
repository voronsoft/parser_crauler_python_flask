import os  # для работы с файловой системой
import subprocess
import platform

import requests
import threading
from time import sleep
from shutil import rmtree  # импортировано для возможности удаления папок из системы если они не пустые
from urllib.parse import unquote
from forms_wtf import UrlLinkForm  # классы представления для работы с БД
from models import db, ParsedData, SiteConfig  # импорт моделей представления таблиц
from utils.my_background_task import my_background_task
from utils.save_links_to_database import save_links_to_database
from utils.save_links_files import create_file_in_website_folder
from utils.clear_files_state_and_links import clear_files_state_and_links
from utils.check_link_from_index_page import check_domain_link, check_start_link
from utils.create_site_folder_and_update_db import create_site_folder_and_update_db
from flask import Flask, render_template, redirect, url_for, request, flash, Response

# создаем приложение
app = Flask(__name__)

# загружаем настройки для приложения из файла настроек
# from_object(obj) обновляет атрибуты конфигурации вашего приложения
# obj - может быть модулем(в нашем случае), классом или словарем
app.config.from_object('instance.app_config')

#  выполняет инициализацию объекта SQLAlchemy для вашего Flask-приложения
db.init_app(app)

# Создаем события для управления потоком1, изначально находится в состоянии "не установлено" (unset/False)
stop_event_thread_1 = threading.Event()  # служит для полного стирания данных о сайте
pause_resume_event_thread_1 = threading.Event()  # служит для опций пауза/продолжить

# Флаг работает/не работает поток thread_1_run (True/ONN or False/OFF)
thread_1_run = False  # OFF


# Маршрут главная страница
@app.route('/', methods=['GET', 'POST'])
def index():
    url_parser = UrlLinkForm()
    # --------- Блок корректности введённых ссылок на главной странице
    # проверка ссылок из формы если прошли то проверяем свободна ли таблица SiteConfig
    if url_parser.validate_on_submit() and SiteConfig.query.first() is None:
        index_site_link = request.form['index_site_link']  # корень сайта из поля формы
        link_url_start = request.form['link_url_start']  # страница старта парсинга из поля формы

        # проверка ссылок на предмет правильного условия для ввода
        if not check_domain_link(index_site_link):
            flash(f'<b>Адрес домена</b> - указан неверный формат url домена: {index_site_link}<br>'
                  f'Пример:<br> http(s)://domain.com<b>/</b> - <b>ОК</b><br>'
                  f'http(s)://domain.com - <b>в конце после .COM должен стоять слеш /</b><br>')
            return redirect(url_for('index'))

        elif not check_start_link(link_url_start):
            flash(f'<b>Ссылка для парсинга</b> - должна вести на страницу сайта, а не на файл<br>'
                  f'Как правило в файлах нет ссылок для парсинга<br>'
                  f'Ссылка должна вести на любую страницу типа - <b>html</b><br>')
            return redirect(url_for('index'))

        # проверяем ответ сервера, существуют ли ссылки:
        try:
            requests.get(index_site_link)  # отправляем запрос серверу
            requests.get(link_url_start)  # отправляем запрос серверу
        except Exception as err:
            # Обработка всех видов ошибок
            return render_template('error.html', error_message=str(err))
        # --------- END блок корректности введённых ссылок на главной странице

        # --------- Блок логика записи в базу данных полученных из формы на главной странице после этапа проверки
        data_url = SiteConfig(index_site_link=unquote(index_site_link), link_url_start=unquote(link_url_start))
        try:
            db.session.add(data_url)  # добавляет объект data_url в текущую сессию базы данных
            db.session.commit()  # записываем в базу данных данные из объекта
        except Exception as e:
            # В случае ошибки откатываем транзакцию
            db.session.rollback()
            # Обрабатываем ошибку или выводим сообщение
            print(f"Произошла ошибка при записи в базу данных: {e}")
            return render_template('error.html', error_message=str(e))
        # --------- END блок логика записи в бд

        # блок создания и записи в бд папки сайта в uploads
        answ = create_site_folder_and_update_db(app, db, index_site_link, link_url_start)
        if answ is True:
            return redirect(url_for('start'))
        else:
            return render_template('error.html', error_message=answ)

    # если таблица содержит данные выводим оповещение
    elif SiteConfig.query.first() is not None:
        temp = SiteConfig.query.first()
        flash(f'Вы не можете ввести данные другого сайта если до этого вы вводили  данные:<br>'
              f'<b>Главная страница сайта: {unquote(temp.index_site_link)}</b><br>'
              f'<b>Страница для парсинга: {unquote(temp.link_url_start)}</b><br>'
              f'Необходимо сначала очистить данные прошлого сайта<br>'
              f'Нажмите кнопку - ОЧИСТИТЬ в меню<br>'
              )
        return render_template('index.html', title="Главная страница", url_parser=url_parser, data=temp)

    return render_template('index.html', title="Главная страница", url_parser=url_parser)


# маршрут начала парсинга
@app.route('/start')
def start():
    global thread_1_run
    print('========')
    print(f'сост потока1 {stop_event_thread_1}')
    print(f'stop_event_thread_1 = {stop_event_thread_1.is_set()}')
    print('========')
    data = SiteConfig.query.first()  # получаем объект записи о сайте из бд

    # если data пустая (отправит на главную для ввода данных)
    if data is None:  # если объект пустой (то есть записи в бд нет)
        return render_template('start.html', title='Старт процесса парсинга111', data=data)

    # если поток выполняется пробуем вывести спарсенные ссылки из бд
    elif thread_1_run:
        print('================ ВХОД =================')
        print('=======================================')
        # записываем в бд ссылки из файла links.txt
        save_links_to_database()
        all_urls = [f'<b>{ind + 1} -</b> {link.links_from_page}' for ind, link in enumerate(ParsedData.query.all())]
        return render_template('start.html', title='Старт процесса парсинга222', data=data, all_urls=all_urls)

    # если поток unset/False и данные сайта есть в таблице бд
    elif not stop_event_thread_1.is_set() and data is not None:
        thread_1 = threading.Thread(target=my_background_task, args=(data, stop_event_thread_1, pause_resume_event_thread_1))
        print(f'333333 состояние потока до старта======={thread_1.is_alive()}')
        thread_1.start()  # запускаем поток
        thread_1_run = True  # Переключаем флаг работы потока thread_1_run (True/ONN)
        all_urls = False
        print(f'333333 состояние потока после старта======={thread_1.is_alive()}')
        return render_template('start.html', title='Старт процесса парсинга333', data=data, all_urls=all_urls)

    return 'Сработала заглушка'


@app.route('/save-links-files', methods=['GET', 'POST'])
def links_save_files():
    data_site = SiteConfig.query.first()  # получаем объект записи о сайте из бд
    # перед получением ссылок воспользуемся функцией записи ссылок с файла в бд
    if save_links_to_database():  # если все записано в БД
        # получаем количество записей из таблицы ParsedData
        urls_count = ParsedData.query.count()
    else:
        urls_count = False  # 'В БД нет записей (ссылок).'
        data_site = False  # 'Нет данных'

    # если пришел запрос POST начинаем основной цикл создания файлов в папке сайта
    if request.method == 'POST':
        print('со страницы пришёл запрос POST')  # если была нажата кнопка Начать запись-->
        links = [link.links_from_page for link in ParsedData.query.all()]

        for ind, link in enumerate(links):
            create_file_in_website_folder(link)
            print(f'{ind + 1} обработана: {link}')
            print('___________________________________________________________')
            print()
            sleep(2)

    return render_template('save_links_files.html', title='Запись ссылок в файлы', data_site=data_site, urls_count=urls_count)


# маршрут документация
@app.route('/documentation')
def documentation():
    ...
    return render_template('documentation.html', title='Документация')


# маршрут сброса данных
@app.route('/clear_site_and_data', methods=['POST'])
def clear_site_and_data():
    """Очистка базы данных и удаление папки с данными из папки uploads"""
    # задаем событию для потока1 значение  "не установлено" (unset/False)
    stop_event_thread_1.set()  # Переходит в состояние "установлено" (unset/.is_set()==False).
    print('=================== Очистка данных =====================')
    print('Поток в начальном состоянии - "не установлено" (unset/False)')

    # Удаление папки сайта с данными
    folder_path = SiteConfig.query.first()

    # удаление папки из системы по пути folder_path
    if folder_path:
        try:
            print(f'Папка {folder_path.upload_path_folder} сайта успешно удалена')
            rmtree(folder_path.upload_path_folder)  # Удаляем папку и ее содержимое

        except OSError as e:
            print(f'Ошибка при удалении папки сайта: {e}')
            flash(f'Ошибка при удалении папки сайта: {str(e)}', 'error')
    else:
        print(f'Папка сайта успешно удалена')

    # Очистка файлов state.txt и links.txt
    clear_files_state_and_links()

    # удаление данных в таблицах
    try:
        db.session.query(SiteConfig).delete()  # Операция удаления данных из таблицы SiteConfig
        db.session.query(ParsedData).delete()  # Операция удаления данных из таблицы ParsedData
        db.session.commit()
        print('БД так же очищена')
        flash('Данные успешно очищены')
    except Exception as e:
        db.session.rollback()
        flash(f'Произошла ошибка при очистке данных в БД: {str(e)}', 'error')

    # после очистки данных возвращаем событию состояние unset/False
    stop_event_thread_1.clear()  # состояние unset/False
    # изменяем флаг работы потока thread_1_run
    global thread_1_run
    thread_1_run = False

    print(f'stop_event_thread_1: {stop_event_thread_1}')
    print(f'stop_event_thread_1 = {stop_event_thread_1.is_set()}')
    print('=================== Очистка данных =====================')
    return redirect(url_for('index'))  # Перенаправление на домашнюю страницу


# TODO продумать вопрос об остановке процесса по необходимости
# маршрут для "ПАУЗА" задачи в потоке1
@app.route('/pause-thread-1', methods=['POST'])
def pause_thread_1():
    global thread_1_run  # доступ на изменение переменной из функции

    pause_resume_event_thread_1.set()  # останавливаем поток
    thread_1_run = False  # работа потока OFF
    return redirect(url_for('start'))


# маршрут для "ПРОДОЛЖИТЬ" задачу в потоке1
@app.route('/resume-thread-1', methods=['POST'])
def resume_thread_1():
    global thread_1_run  # доступ на изменение переменной из функции

    pause_resume_event_thread_1.clear()  # запускаем поток
    thread_1_run = True  # работа потока ONN
    return redirect(url_for('start'))


# Маршрут счетчик найденных ссылок
@app.route('/sse')
def sse():
    # Функция для получения количества ссылок
    def get_link_count():
        try:
            with open('links.txt', 'r') as file:
                lines = file.readlines()
                return len(lines)
        except FileNotFoundError:
            # return 0
            return 'Файл links.txt(с ссылками для подсчета количества) в корне сайта не найден !!!'

    def generate():
        while True:
            link_count = get_link_count()  # Получаем текущее количество ссылок
            yield f"data: {link_count}\n\n"
            sleep(1)  # Ждем 2 секунду перед отправкой следующего обновления
            print('SSE-1 работает >>>>>')

    return Response(generate(), content_type='text/event-stream')


# Маршрут счетчик количества файлов сохраненных в папке сайта
@app.route('/sse-files-count-folder-site')
def sse_files_count():
    # получаем путь папки сайта из БД
    path_folder_site = SiteConfig.query.first().upload_path_folder
    website_folder = os.path.join(path_folder_site)
    print(f'path_folder_site: {path_folder_site}')
    print(f'website_folder = {os.path.join(path_folder_site)}')
    print()

    def generate():
        while True:
            # получаем количество файлов в папке сайта
            file_count = len([f for f in os.listdir(website_folder) if os.path.isfile(os.path.join(website_folder, f))])
            sleep(1)  # Ждем 1 секунду перед следующей проверкой
            # Отправляем количество файлов клиенту
            yield f"data: {file_count}\n\n"
            print(f'SSE-2 работает >>>>> отправляет data {file_count}')

    return Response(generate(), content_type='text/event-stream')


# Маршрут открытия файлового менеджера в зависимости от ОС (Linux or Windows)
@app.route('/open_file_manager', methods=['POST'])
def open_file_manager():
    if request.method == 'POST':
        os_type = platform.system()
        if os_type == 'Linux':
            # Определите путь к папке сайта
            path_folder_site = SiteConfig.query.first().upload_path_folder
            path_folder_site = os.path.join(path_folder_site)
            # Команда для открытия файлового менеджера в Linux
            subprocess.Popen(['xdg-open', path_folder_site])
        elif os_type == 'Windows':
            # Определите путь к папке сайта
            path_folder_site = SiteConfig.query.first().upload_path_folder
            path_folder_site = os.path.join(path_folder_site)
            # Команда для открытия файлового менеджера в Windows
            subprocess.Popen(['explorer', path_folder_site])
        else:
            return "Неподдерживаемая операционная система."

    return redirect(url_for('documentation'))


# # -------------------------------------------------
# # запуск приложения с сервером - Werkzeug (тестовый местный)
# if __name__ == '__main__':
#     # app.run()
#     app.run(host='0.0.0.0')

# запуск приложения с сервером - Waitress (для использования SSE)
if __name__ == '__main__':
    from waitress import serve

    serve(app, host='0.0.0.0', port=5000, _quiet=True)
