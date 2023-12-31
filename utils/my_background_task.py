import requests
import threading
from time import sleep
from random import randint
from bs4 import BeautifulSoup
from datetime import datetime
from fake_useragent import UserAgent
from urllib.parse import urlparse, urljoin, unquote
from utils.clear_files_state_and_links import clear_files_state_and_links

# Объект блокировки для потоков
file_lock_thread = threading.Lock()
# Множество для хранения уникальных ссылок что бы исключать повтор при парсинге
unique_links = set()
# Множество для хранения уже обработанных URL-адресов
processed_urls = set()


def my_background_task(url_temp, data, stop_event_thread_1, pause_resume_event_thread_1, thread_name):
    """
    Функция которая по начальной странице для парсинга пройдет по всем страницам сайта
    соберёт ссылки для следующего этапа записи данных с страниц
    Ссылки будут записаны в файл links.txt
    :param url_temp - ссылка начала парсинга
    :param data: - данные сайта с БД для начала парсинга
    :param stop_event_thread_1: - флаг для остановки работы с последующим стиранием данных о сайте
    :param pause_resume_event_thread_1: - флаг для пауза/продолжить работу потоков
    :param thread_name: - идентификатор потока
    """
    global unique_links
    # Задаем начальный URL сайта, который хотим просканировать
    start_url = url_temp

    # TODO Задаем user-agent рандомно
    #   Get a random browser user-agent string
    #   print(ua.random)
    ua = UserAgent()
    headers = {'User-Agent': str(ua.random)}

    # Задаем домен сайта (получаем из объекта - data)
    domain = data.index_site_link

    # Функция для фильтрации ссылок по домену (если начинается с другого домена или '#' значит исключить)
    def filters_by_domain(link):
        # Определяем ссылки якоря
        if link[-1] == '#' or link[-2] == '#/':  # Исключаем ссылки, если в конце ссылки # или #/
            return False
        if urlparse(link).fragment:
            return False
        if not link.startswith(domain):  # Исключаем ссылки, которые не относятся к базовому домену
            return False
        return True

    # Функция для фильтрации ссылок по типу расширения (исключаем медиа)
    def filters_by_type_links(url):
        extension = ['.jpeg', '.jpg', '.gif', '.png', '.pdf', '.bmp', '.webp', '.swg', '.mp4', '.avi', '.mp3',
                     '.movie', '.mov', '.wmv', 'wma', '.wav', '.tiff', '.tif', '.mp4', '.ico']
        return not any([True for ext in extension if url.endswith(ext)])  # Если есть такое расширение вернуть False

    # Функция для получения всех ссылок на странице
    def get_links_on_page(url):
        sleep(randint(1, 4))
        response = requests.get(url, headers=headers)
        # Проверяем статус ответа сервера
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            # Находим все ссылки на странице (всех видов)
            all_urls_href = [unquote(urljoin(domain, link.get('href'))) for link in soup.find_all(lambda tag: tag.has_attr('href'))]
            all_urls_src = [unquote(urljoin(domain, link.get('src'))) for link in soup.find_all(lambda tag: tag.has_attr('src'))]
            all_urls = set(all_urls_href + all_urls_src)  # Удаляем дубликаты

            # Удаляем адреса которые не начинаются с нашего домена а так же адреса содержащие якоря - '#'
            all_urls = [link for link in all_urls if filters_by_domain(link)]
            # Удаляем ссылки которые являются медиа
            all_urls = [link for link in all_urls if filters_by_type_links(link)]

            # ----- Блок отладки -----
            if len(all_urls) >= 1:
                print(f'{thread_name} Обнаруженные страницы: {len(all_urls)} шт.')
            elif len(all_urls) <= 0:
                print(f'{thread_name} По этому адресу нет ссылок, скорее всего это файл CSS/JS')
            # ----- END Блок отладки -----

            return all_urls
        else:
            print(f"Ошибка при запросе страницы {url}. Статус код: {response.status_code}")
            return []

    # Функция для сохранения состояния выполнения
    def save_state(url):
        # Получаем заголовки страницы
        response = requests.head(url)
        # Проверяем что это не файлы
        if not any(url.endswith(_) for _ in ['.css', '.js']):
            if response.status_code == 200:
                try:
                    # Захватываем блокировку файла, чтобы избежать конфликтов доступа
                    with file_lock_thread:
                        with open('state.txt', 'r', encoding='utf-8') as file:
                            # Читаем уже существующие строки в список
                            lines = file.readlines()

                        # Добавляем новую строку
                        lines.append(unquote(url) + '\n')

                        # Если число строк в списке превышает 4, удаляем первую строку
                        if len(lines) > 4:
                            lines.pop(0)

                        # Перезаписываем файл
                        with open('state.txt', 'w', encoding='utf-8') as file:
                            file.writelines(lines)

                except Exception as e:
                    # Выбрасываем исключение с информативным сообщением
                    print(f'{thread_name} Ошибка при записи в файл state.py (вызвана в функции my_background_task.py/save_state(): {str(e)}')

    # Функция для загрузки состояния выполнения
    def load_state():
        try:
            # Захватываем блокировку файла, чтобы избежать конфликтов доступа
            with file_lock_thread:
                # Открываем файл для чтения
                with open('state.txt', 'r', encoding='utf-8') as file:
                    # Считываем все строки из файла
                    lines = file.readlines()
                if lines:
                    # Если есть хотя бы одна строка в файле
                    first_line = lines[0]  # Извлекаем первую строку
                    # Перезаписываем файл без первой строки
                    with open('state.txt', 'w', encoding='utf-8') as file:
                        file.writelines(lines[1:])
                    return first_line.strip()  # Возвращаем первую строку без начальных и конечных пробелов
                else:
                    return None  # Если файла нет или он пуст, возвращаем None
        except FileNotFoundError:
            return None  # Если файл не найден, возвращаем None

    # Функция для удаления дубликатов из файла
    def remove_duplicates_from_file(file_name='links.txt'):
        with file_lock_thread:
            with open(file_name, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                unique_url = set(lines)
            with open(file_name, 'w', encoding='utf-8') as file:
                file.writelines(unique_url)

    # Функция для проверки наличия строки (ссылки) в файле
    def is_link_in_file(link):
        try:
            with open('links.txt', 'r', encoding='utf-8') as file:
                for line in file:
                    if line.strip() == link:
                        return True
            return False
        except FileNotFoundError:
            return False

    # Функция для сохранения ссылок в файл links.txt
    def save_links_to_file(links):
        with file_lock_thread:  # Добавляем блокировку
            if links:  # Если список не пустой
                for link in links:  # Перебор списка
                    if link not in unique_links:  # Если ссылка не находится в множестве (уникальных ссылок)
                        if not is_link_in_file(unquote(link)):  # Проверяем, не существует ли такой ссылки в файле
                            with open('links.txt', 'a', encoding='utf-8') as file:  # Открываем в режиме дозаписи в конец файла
                                file.write(unquote(link) + '\n')  # Записываем ссылку в файл(links.txt) просканированых страниц
                                print(f'{thread_name} URL added to-> links.txt {link} ({datetime.now()})')
                    #     else:
                    #         print(f'{thread_name} !!!!! ИГНОР: Ссылка уже есть в файле: {link}')
                    # elif link in unique_links:
                    #     print(f'{thread_name} !!!!! ИГНОР: Ссылка уже была записана в уникальные: {link}')

        # Удаляем дубликаты из файла
        remove_duplicates_from_file()
        print('После записи удаляем дубликаты с файла')

    # Основная функция обработки ссылок при поиске ссылок на сайте
    def crawl_site(url):
        urls_to_process = [url]  # Используем список для хранения URL для обработки

        while (not stop_event_thread_1.is_set()) and (data is not None) and urls_to_process and (not pause_resume_event_thread_1.is_set()):
            with file_lock_thread:
                url = urls_to_process.pop(0)  # Берем первый URL из списка

            if url in unique_links:  # Проверяем есть ли такая ссылка в - unique_links
                print(f'{thread_name} !!!!! ИГНОР ссылка уже обработана: {url}')
                continue

            try:
                print(f'{thread_name} __________Обработка: {unquote(url)}')
                links = get_links_on_page(url)  # Получаем все ссылки со страницы
                save_links_to_file(links)  # Запись ссылок в файл / проверка есть ли такая ссылка в файле links.txt
                with file_lock_thread:  # Блокируем доступ перед проверкой
                    if url not in unique_links:  # проверяем есть ли такая ссылка в - unique_links
                        unique_links.add(url)  # Добавляем в уникальные
                        print(f'{thread_name} - URL {url} added to-> unique_links ({datetime.now()})')
                # print(f'{thread_name} __________ Ссылки на странице {url} сохранены в links.txt')
                print()
                with file_lock_thread:
                    processed_urls.add(url)  # Добавляем текущий URL в множество обработанных

                save_state(url)  # Сохраняем состояние выполнения задачи

                for link in links:
                    if link not in processed_urls and link not in urls_to_process:
                        with file_lock_thread:
                            urls_to_process.append(link)

            except Exception as e:
                # Выбрасываем исключение с информативным сообщением
                raise Exception(f'Произошла ошибка в файле my_background_task.py/функция-crawl_site()\n'
                                f'при запросе к сайту по URL: {url}: {str(e)}')

        # Если событие stop_event_thread_1 установлено в set/True
        # контрольно очистим файлы state.txt и links.txt
        if stop_event_thread_1.is_set():  #
            clear_files_state_and_links()

        # Если событие pause_resume_event_thread_1 в состоянии True цикл while не отрабатывает обход ссылок
        if pause_resume_event_thread_1.is_set():
            # сбрасываем список уникальных ссылок
            # unique_links.clear()

            print(f'{thread_name} ==========================================')
            print(f'{thread_name} ============= ПАУЗА ПАРСИНГА =============')
            print(f'{thread_name} ==========================================')

    # ################# END - основная функция модуля ##############

    # ================================================================================
    previous_url = load_state()  # Загружаем состояние выполнения, если оно существует
    if previous_url:
        print(f'{thread_name} Продолжаем обход с {previous_url}')
        crawl_site(previous_url)
    else:
        # Запускаем обход сайта с начального URL
        print('Функция crawl_site запустилась с значением: ', start_url)
        crawl_site(start_url)

    # По завершению обхода, удаляем дубликаты из файла
    remove_duplicates_from_file()

    print(f'{thread_name} ==========================================')
    print(f'{thread_name} ========= ОБХОД ССЫЛОК ЗАВЕРШЕН ==========')
    print(f'{thread_name} ==========================================')
    # сбрасываем список уникальных ссылок
    unique_links.clear()
