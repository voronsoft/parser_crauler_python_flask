import os
import requests
from time import sleep
from pprint import pprint
from random import randint
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, unquote
from utils.clear_files_state_and_links import clear_files_state_and_links


def my_background_task(data, stop_event_thread_1, pause_resume_event_thread_1):
    """
    Функция которая по начальной странице для парсинга пройдет по всем страницам сайта
    соберёт ссылки для следующего этапа записи данных с страниц
    Ссылки будут записаны в файл links.txt
    :param data: - данные сайта для начала парсинга
    :param stop_event_thread_1: - флаг для остановки работы с последующим стиранием данных о сайте
    :param pause_resume_event_thread_1: - флаг для пауза/продолжить работы
    """

    # Задаем начальный URL сайта, который вы хотите просканировать
    start_url = data.link_url_start
    # Задаем user-agent
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'}

    # Множество для хранения уже обработанных URL-адресов
    processed_urls = set()

    # Множество для хранения уникальных ссылок что бы исключать повтор при парсинге
    unique_links = set()

    # Задаем домен сайта (извлекаем его из начального URL)
    parsed_start_url = urlparse(start_url)
    domain = parsed_start_url.scheme + '://' + parsed_start_url.netloc + '/'

    # Функция для фильтрации ссылок по домену (если начинается с другого домена или '#' значит исключить)
    def filters_by_domain(link):
        # определяем ссылки якоря
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
        # если есть такое расширение вернуть False
        return not any([True for ext in extension if url.endswith(ext)])

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
            all_urls = set(all_urls_href + all_urls_src)  # удаляем дубликаты

            # удаляем адреса которые не начинаются с нашего домена а так же адреса содержащие якоря - '#'
            all_urls = [link for link in all_urls if filters_by_domain(link)]
            # удаляем ссылки которые являются медиа
            all_urls = [link for link in all_urls if filters_by_type_links(link)]
            print('Обнаруженные страницы:')
            if len(all_urls) >= 1:
                pprint(all_urls)
            elif len(all_urls) <= 0:
                print('По этому адресу нет ссылок, скорее всего это файл CSS или JS')
            return all_urls
        else:
            print(f"Ошибка при запросе страницы {url}. Статус код: {response.status_code}")
            return []

    # Функция для сохранения состояния выполнения
    def save_state(url):
        with open('state.txt', 'w', encoding='utf-8') as file:
            file.write(unquote(url))

    # Функция для загрузки состояния выполнения
    def load_state():
        try:
            with open('state.txt', 'r', encoding='utf-8') as file:
                return file.read().strip()
        except FileNotFoundError:
            return None

    # Функция для удаления дубликатов из файла
    def remove_duplicates_from_file():
        with open('links.txt', 'r', encoding='utf-8') as file:
            lines = file.readlines()

            unique_url = set(lines)

        with open('links.txt', 'w', encoding='utf-8') as file:
            file.writelines(unique_url)

    # Функция проверки что ссылка уже записана в файл links.txt
    def verify_links_file(link):
        try:
            # Открываем файл на чтение
            with open('links.txt', 'r', encoding='utf-8') as file:
                # Читаем содержимое файла и декодируем
                file_contents = unquote(file.read())

            # Декодируем также строку link
            decoded_link = unquote(link)

            # Добавляем символ новой строки в конец декодированной строки link
            decoded_link_with_newline = decoded_link + '\n'

            # Проверяем наличие декодированной строки link в содержимом файла
            if decoded_link_with_newline in file_contents:
                return True  # Строка найдена в файле
            else:
                return False  # Строка не найдена в файле

        except FileNotFoundError:
            # Вызываем исключение и завершаем выполнение кода
            raise FileNotFoundError('Файл "links.txt" не существует.')

    # Функция для проверки наличия строки в файле
    def is_link_in_file(link):
        try:
            with open('links.txt', 'r', encoding='utf-8') as file:
                for line in file:
                    if line.strip() == link:
                        return True
            return False
        except FileNotFoundError:
            return False

    # Функция для сохранения ссылок в файл
    def save_links_to_file(links):
        with open('links.txt', 'a', encoding='utf-8') as file:  # открываем в режиме дозаписи в конец файла
            if links:  # если список не пустой
                for link in links:
                    if link not in unique_links:  # если ссылка не находится в множестве (уникальных ссылок)
                        if not is_link_in_file(unquote(link)):  # Проверяем, не существует ли такой ссылки в файле
                            file.write(unquote(link) + '\n')  # записываем ссылку в файл(links.txt) просканированных страниц
                            print(f'URL saved in links.txt: {link}')
                        else:
                            print(f'!!!!! ИГНОР: Ссылка уже есть в файле: {link}')
                    elif link in unique_links:
                        print(f'!!!!! ИГНОР: Ссылка уже была записана в уникальные: {link}')

        remove_duplicates_from_file()

    # Функция для обхода всех страниц сайта (используем метод цикла while)
    def crawl_site(url):
        urls_to_process = [url]  # Используем список для хранения URL для обработки

        # while работает пока:
        # stop_event_thread_1 = False/unset
        # data содержит данные (не None)
        # urls_to_process - не None
        # pause_resume_event_thread_1 = False/unset
        while not stop_event_thread_1.is_set() and data is not None and urls_to_process and not pause_resume_event_thread_1.is_set():
            url = urls_to_process.pop(0)  # Берем первый URL из списка

            if url in unique_links:
                print(f'!!!!! ИГНОР ссылка была ранее обработана: {url}')
                continue

            try:
                print(f'__________Обработка: {unquote(url)}')
                links = get_links_on_page(url)  # Получаем все ссылки со страницы
                save_links_to_file(links)  # Запись ссылок в файл
                unique_links.add(url)  # Добавляем в уникальные
                print(f'__________ Cсылка {url} добавлена в - unique_links_________')
                print(f'__________ Ссылки на странице {url} сохранены в links.txt')
                print()
                processed_urls.add(url)  # Добавляем текущий URL в множество обработанных
                save_state(url)  # Сохраняем состояние выполнения

                for link in links:
                    if link not in processed_urls and link not in urls_to_process:
                        urls_to_process.append(link)

            except requests.exceptions.RequestException as e:
                print(f'Произошла ошибка в файле my_background_task.py\n'
                      f'при запросе к сайту {url}: {e}')

        # если произошла остановка потока до записи данных в текстовые файлы
        # контрольно очистим файлы state.txt и links.txt
        if stop_event_thread_1.is_set():
            clear_files_state_and_links()
        if pause_resume_event_thread_1.is_set():
            print('==========================================')
            print('============= ПАУЗА ПАРСИНГА =============')
            print('==========================================')

    # ================================================================================
    previous_url = load_state()  # Загружаем состояние выполнения, если оно существует
    if previous_url:
        print(f'Продолжаем обход с {previous_url}')
        crawl_site(previous_url)
    else:
        # Запускаем обход сайта с начального URL
        crawl_site(start_url)

    # По завершению обхода, удаляем дубликаты из файла
    remove_duplicates_from_file()

    print('==========================================')
    print('========= ОБХОД ССЫЛОК ЗАВЕРШЕН ==========')
    print('==========================================')
