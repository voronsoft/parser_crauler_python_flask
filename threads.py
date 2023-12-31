import os
import platform
import requests
import threading
import subprocess
import numpy as np
from time import sleep
from shutil import rmtree
from urllib.parse import unquote
from forms_wtf import UrlLinkForm
from models import db, ParsedData, SiteConfig
from utils.first_url_threads import get_links_on_page
from utils.my_background_task import my_background_task
from utils.save_links_to_database import save_links_to_database
from utils.save_links_files import create_file_in_website_folder
from utils.clear_files_state_and_links import clear_files_state_and_links
from utils.check_link_from_index_page import check_domain_link, check_start_link
from utils.create_site_folder_and_update_db import create_site_folder_and_update_db
from flask import Flask, render_template, redirect, url_for, request, flash, Response

# создаем приложение
app = Flask(__name__)

# Загружаем настройки для приложения из файла настроек
# from_object(obj) обновляет атрибуты конфигурации вашего приложения
# obj - может быть модулем(в нашем случае), классом или словарем
app.config.from_object('instance.app_config')

# Выполняет инициализацию объекта SQLAlchemy для вашего Flask-приложения
db.init_app(app)

# Создаем события для управления потоком, изначально находится в состоянии "не установлено" (unset/False)
stop_event_thread_1 = threading.Event()  # Служит для полного стирания данных о сайте
pause_resume_event_thread_1 = threading.Event()  # Служит для опций пауза/продолжить

# Флаг работает/не работает поток thread_run (True/ONN or False/OFF)
thread_run = False  # OFF


# Маршрут главная страница
@app.route('/', methods=['GET', 'POST'])
def index():
    url_parser = UrlLinkForm()
    # --------- Блок корректности введённых ссылок на главной странице
    # Проверка ссылок из формы если прошли то проверяем свободна ли таблица SiteConfig
    if url_parser.validate_on_submit() and SiteConfig.query.first() is None:
        index_site_link = request.form['index_site_link']  # корень сайта из поля формы
        link_url_start = request.form['link_url_start']  # страница старта парсинга из поля формы

        # Проверка ссылок на предмет правильного условия для ввода
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

        # Проверяем ответ сервера, существуют ли ссылки:
        try:
            response1 = requests.get(index_site_link)  # отправляем запрос серверу для корня сайта
            response2 = requests.get(link_url_start)  # отправляем запрос серверу для стартовой страницы
            if response1.status_code != 200 or response2.status_code != 200:
                flash('Страницы домена сайта или стартовой страницы не существуют или вернули ошибку')
        except Exception as e:
            # Обработка ошибок
            flash(f'Ошибка при запросе к страницам домен сайта или стартовой странице.')
            return render_template('error.html', error_message=str(e))
        # --------- END блок корректности введённых ссылок на главной странице

        # Получаем ссылки для старта потоков записав из в бд
        links_start = get_links_on_page(link_url_start, index_site_link)
        links_start = ' '.join(map(unquote, links_start))

        # --------- Блок логика записи в базу данных полученных из формы на главной странице после этапа проверки
        data_url = SiteConfig(index_site_link=unquote(index_site_link), link_url_start=links_start)
        try:
            db.session.add(data_url)  # Добавляет объект data_url в текущую сессию базы данных
            db.session.commit()  # Записываем в базу данных данные из объекта
        except Exception as e:
            # В случае ошибки откатываем транзакцию
            db.session.rollback()
            # Обрабатываем ошибку или выводим сообщение
            print(f"Произошла ошибка при записи в базу данных: {e}")
            return render_template('error.html', error_message=str(e))
        # --------- END блок логика записи в бд

        answ = create_site_folder_and_update_db(app, db, index_site_link, link_url_start)

        if answ is True:
            return redirect(url_for('start'))
        else:
            return render_template('error.html', error_message=answ)

    # Если таблица содержит данные выводим оповещение
    elif SiteConfig.query.first() is not None:
        temp = SiteConfig.query.first()
        flash(f'Вы не можете ввести данные другого сайта если до этого вы вводили  данные:<br>'
              f'<b>Домен: {unquote(temp.index_site_link)}</b><br>'
              f'Необходимо сначала очистить данные прошлого сайта<br>'
              f'Нажмите кнопку - ОЧИСТИТЬ в меню<br>'
              )
        return render_template('index.html', title="Главная страница", url_parser=url_parser, data=temp)

    return render_template('index.html', title="Главная страница", url_parser=url_parser)


# Маршрут начала парсинга
@app.route('/start')
def start():
    global thread_run
    print('========')
    print(f'сост потока stop_event_thread_1 {stop_event_thread_1} - {stop_event_thread_1.is_set()}')
    print('========')
    data = SiteConfig.query.first()  # Получаем объект записи о сайте из бд
    if data:
        url = iter(data.link_url_start.split())
    else:
        url = None

    # Если data пустая (отправит на главную для ввода данных)
    if data is None:  # Если объект пустой (то есть записи в бд нет)
        return render_template('start.html', title='Старт процесса парсинга111', data=data)

    # TODO - Основное условие запуска потоков !!!!!
    elif not stop_event_thread_1.is_set() and data is not None and thread_run is not True and url is not None:
        print("Сработал запуск потоков")

        # Функция для обработки ссылок в каждом потоке
        def process_links_2():
            thread_name = threading.current_thread().name  # Получаем название текущего потока и передаем его в основную функцию
            # В функции my_background_task предусмотрена блокировка доступа для параллельных потоков
            my_background_task(next(url), data, stop_event_thread_1, pause_resume_event_thread_1, thread_name)

        # TODO установка количества потоков для сбора ссылок
        # Создаем 4 потока
        for i in range(0, 4):
            thread = threading.Thread(target=process_links_2)
            thread.start()
            thread_run = True  # Переключаем флаг работы потока в состояние (True/ONN)

        return render_template('start.html', title='Старт процесса парсинга111', data=data, thread_run=thread_run)

    return render_template('start.html', title='Старт процесса парсинга', data=data, thread_run=thread_run)


# Маршрут создания файла скаченной страницы в папке сайта из списка найденных ссылок
# Используется метод создания 4 потоков с разделением списка ссылок на 4 части
# (исходя из количества созданных потоков делим список)
@app.route('/save-links-files', methods=['GET', 'POST'])
def links_save_files():
    data_site = SiteConfig.query.first()  # Получаем объект записи о сайте из бд
    # Перед получением ссылок воспользуемся функцией записи ссылок с файла в бд
    if save_links_to_database():  # Если все записано в БД
        # Получаем количество записей из таблицы ParsedData
        urls_count = ParsedData.query.count()
    else:
        urls_count = False  # 'В БД нет записей (ссылок).'
        data_site = False  # 'Нет данных'

    # если запись в бд в таблице SiteConfig существует и поле upload_path_folder имеет запись пути папки сайта
    if data_site and data_site.upload_path_folder:
        # проверяем есть ли такая папка в директории если нет то создаем что бы начать запись файлов в папку сайта
        if not os.path.exists(data_site.upload_path_folder):
            os.makedirs(data_site.upload_path_folder)

    # Функция для обработки ссылок в каждом потоке
    def process_links(lst):
        for link in lst:
            with app.app_context():  # Создаем контекст приложения для доступа к данным из функции - create_file_in_website_folder
                create_file_in_website_folder(link)  # Функция записи файлов в папку сайта

    # Если пришел запрос POST начинаем основной цикл создания файлов в папке сайта
    if request.method == 'POST':
        print('Пришёл POST')  # Если была нажата кнопка: Начать запись-->

        #  Получаем из БД все ссылки по которым будем создавать файлы в папке
        links = [link.links_from_page for link in ParsedData.query.all()]

        # TODO количество потоков для записи файлов, установлено 4
        # Разбиваем список ссылок на 4 части (по числу потоков) используем библиотеку numpy
        split_links_from_thread = [arr.tolist() for arr in np.array_split(links, 4)]

        # Создаем потоки согласно количеству частей списка
        for i in range(len(split_links_from_thread)):
            thread = threading.Thread(target=process_links, args=(split_links_from_thread[i],))
            thread.start()

    return render_template('save_links_files.html', title='Запись ссылок в файлы', data_site=data_site, urls_count=urls_count)


# Маршрут документация
@app.route('/documentation')
def documentation():
    ...
    return render_template('documentation.html', title='Документация')


# Маршрут сброса данных
@app.route('/clear_site_and_data', methods=['POST'])
def clear_site_and_data():
    """Очистка базы данных и удаление папки с данными из папки uploads"""
    # Задаем событию для потока значение  "не установлено" (unset/False)
    stop_event_thread_1.set()  # Переходит в состояние "установлено" (unset/.is_set()==False).
    print('=================== Очистка данных =====================')
    print('Поток в начальном состоянии - "не установлено" (unset/False)')

    # Получаем путь к папке для удаления
    folder_path = SiteConfig.query.first()

    # Удаление папки из системы по пути folder_path
    if folder_path and os.path.exists(folder_path.upload_path_folder):
        try:
            print(f'Папка {folder_path.upload_path_folder} сайта успешно удалена')
            rmtree(folder_path.upload_path_folder)  # Удаляем папку и ее содержимое

        except OSError as e:
            print(f'Ошибка при удалении папки сайта: {e}')
            return render_template('error.html', error_message='Ошибка при удалении папки сайта: ' + str(e))
    else:
        print(f'Папка сайта успешно удалена')

    # Очистка файлов state.txt и links.txt
    clear_files_state_and_links()

    # Удаление данных в таблицах
    try:
        db.session.query(SiteConfig).delete()  # Операция удаления данных из таблицы SiteConfig
        db.session.query(ParsedData).delete()  # Операция удаления данных из таблицы ParsedData
        db.session.commit()
        print('БД так же очищена')
        flash('Данные успешно очищены')
    except Exception as e:
        db.session.rollback()
        flash(f'Произошла ошибка при очистке данных в БД: {str(e)}')
        return render_template('error.html', error_message='Произошла ошибка при очистке данных в БД: ' + str(e))

    # После очистки данных возвращаем событиям состояние unset/False
    stop_event_thread_1.clear()  # Сброс, состояние unset/False
    pause_resume_event_thread_1.clear()  # Сброс, состояние unset/False
    # Изменяем флаг работы потока thread_run
    global thread_run
    thread_run = False

    print(f'Состояние потока stop_event_thread_1: {stop_event_thread_1} - {stop_event_thread_1.is_set()}')
    print('=================== END Очистка данных =====================')
    return redirect(url_for('index'))


# Маршрут для "ПАУЗА" задачи в потоке по сбору ссылок
@app.route('/pause-thread-1', methods=['POST'])
def pause_thread_1():
    global thread_run  # доступ на изменение переменной из функции

    pause_resume_event_thread_1.set()  # Останавливаем поток устанавливая событие в set
    thread_run = True  # Работа потока - если True сработает условие в строке 122
    return redirect(url_for('start'))


# Маршрут для "ПРОДОЛЖИТЬ" задачу в потоке
@app.route('/resume-thread-1', methods=['POST'])
def resume_thread_1():
    global thread_run  # Доступ на изменение переменной из функции

    pause_resume_event_thread_1.clear()  # Запускаем поток
    print('НАЖАЛ КНОПКУ ПРОДОЛЖИТЬ', pause_resume_event_thread_1.is_set())
    thread_run = False  # Работа потока - если False сработает условие в строке 132
    return redirect(url_for('start'))


# Маршрут счетчик найденных ссылок SSE оповещение
@app.route('/sse')
def sse():
    # Функция для получения количества обработанных ссылок
    def get_link_count():
        try:
            with open('links.txt', 'r', encoding='utf-8') as file:
                lines = file.readlines()
                return len(lines)
        except Exception as e:
            raise Exception(f'Ошибка в маршруте /sse - функция: get_link_count\n ERROR - {e}')

    def generate():
        while True:
            link_count = get_link_count()  # Получаем текущее количество ссылок
            print(f'SSE-1 RUN {link_count}')
            yield f"data: {link_count}\n\n"
            sleep(2)  # Ждем 2 секунды

    return Response(generate(), content_type='text/event-stream')


# Маршрут счетчик количества файлов сохраненных в папке сайта для SSE оповещение
@app.route('/sse-files-count-folder-site')
def sse_files_count():
    # Получаем путь папки сайта из БД
    path_folder_site = SiteConfig.query.first().upload_path_folder
    website_folder = os.path.join(path_folder_site)

    def generate():
        if os.path.exists(website_folder):
            while True:
                if os.path.exists(website_folder):
                    # Получаем количество файлов в папке сайта
                    file_count = len([f for f in os.listdir(website_folder) if os.path.isfile(os.path.join(website_folder, f))])
                    print(f'SSE-2 RUN {file_count}')
                    yield f"data: {file_count}\n\n"  # Отправляем количество файлов клиенту
                    sleep(2)  # Ждем 2 секунды
                else:
                    break

    return Response(generate(), content_type='text/event-stream')


# Маршрут открытия файлового менеджера в зависимости от ОС (Linux or Windows)
# Реакция на нажатие кнопки - Просмотр файлов
@app.route('/open_file_manager', methods=['POST', 'GET'])
def open_file_manager():
    if request.method == 'POST':
        os_type = platform.system()
        # os LINUX
        if os_type == 'Linux':
            if SiteConfig.query.first():
                path_folder_site = SiteConfig.query.first().upload_path_folder
                path_folder_site = os.path.join(path_folder_site)
                # Получение списка файлов в каталоге
                file_list = os.listdir(path_folder_site)
                return render_template('show-file.html', path_folder_site=path_folder_site, file_list=file_list)

        # os WINDOWS
        elif os_type == 'Windows':
            # Путь к папке сайта
            path_folder_site = SiteConfig.query.first().upload_path_folder
            path_folder_site = os.path.join(path_folder_site)
            # Команда для открытия файлового менеджера в Windows
            subprocess.Popen(['explorer', path_folder_site])
            file_list = os.listdir(path_folder_site)
            return render_template('show-file.html', path_folder_site=path_folder_site, file_list=file_list)
        else:
            flash(f'Возникла ошибка при открытии файлового менеджера вашей системы')
            return render_template('error.html', error_message=str('Неподдерживаемая операционная система.'))

    return redirect(url_for('documentation'))


# --------------- РАЗДЕЛ ВЫБОРА СЕРВЕРА ---------------------------
# запуск приложения с сервером - Werkzeug (тестовый)
if __name__ == '__main__':
    app.run(host='0.0.0.0')

# # запуск приложения с сервером - Waitress (для использования SSE оповещений)
# if __name__ == '__main__':
#     from waitress import serve
#
#     serve(app, host='0.0.0.0', port=5000, _quiet=True)
