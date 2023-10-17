"""
1 получаем с базы данных список ссылок для скачивания
2 функция для создания имени для скачиваемого файла
3 функция для создания файла в папке сайта ( на основе данных с страницы)
"""
import os  # для работы с файловой системой
import requests
import threading
import mimetypes
from urllib.parse import urlparse, unquote
from models import SiteConfig  # импорт моделей представления таблиц

# объект блокировки для потоков
file_lock_thread = threading.Lock()


# Функция генерации имени для файла по названию ссылки страницы
def generate_download_filename(original_filename):
    """Функция генерации имени для файла по названию ссылки страницы - name_data.html(расширение зависит от типа заголовка Content-Type"""

    # Преобразуем оригинальное имя файла (если оно в виде URL) в читаемый формат
    parsed_url = urlparse(original_filename)

    if 'do=' in parsed_url.query:  # если в ссылке есть 'do=' или "?"
        decoded_filename = parsed_url.scheme + '/' + parsed_url.netloc + parsed_url.path + '/' + parsed_url.query
    else:
        decoded_filename = parsed_url.scheme + '/' + parsed_url.netloc + parsed_url.path + '/' + parsed_url.query

    decoded_filename = unquote(decoded_filename)
    # удаляем знаки что бы создать корректное имя для файла
    char = ['://', '//', '?', '<', '>', ',', '|', '*', '"', '/', '\\', ':', ' ']

    for ch in char:
        if ch in decoded_filename:
            decoded_filename = decoded_filename.replace(ch, '_')

    decoded_filename = decoded_filename.strip('_ ')  # удаляем лишнее в начале и конце

    # добавляем расширение в название файла по типу контента
    # Отправляем GET-запрос по указанной ссылке для получения заголовка ответа сервера
    response = requests.head(original_filename)
    # Получаем тип контента из заголовка Content-Type
    content_type = response.headers.get('Content-Type')
    # Определяем расширение файла на основе типа контента (пример: image/jpeg -> .jpg)
    if content_type and response.status_code in [200, 301, 302]:
        extension = os.path.splitext(original_filename)[-1]  # Извлекаем расширение из URL

        if not extension:  # если расширения нет
            extension = mimetypes.guess_extension(content_type.split(';')[0])  # Попытка задать расширение по типу контента
            return str(decoded_filename + extension)
        elif extension in ['.css', '.js']:  # если расширение есть и оно входит в список
            return str(decoded_filename)
        elif extension not in ['.css', '.js']:  # если расширение есть и оно НЕ входит в список
            return str(decoded_filename + '.html')  # присоединяем расширение - .html

    elif content_type and response.status_code == 404:
        return f'Code_answer_404_error-{decoded_filename}'
    else:
        return f'unknown_error-{decoded_filename}'


# Функция получения данных страницы
def get_webpage_data(url):
    """Функция получения данных страницы"""
    user_agent = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'}
    try:
        # Отправляем GET-запрос по указанной ссылке
        response = requests.get(url, user_agent)
        # Проверяем успешность запроса (код 200 означает успешный запрос)
        if response.status_code == 200:
            # Возвращаем текстовое содержимое страницы
            return response.text
        else:
            # Если запрос не успешен создаем сообщение
            return f'Код состояния страницы: {response.status_code}\nСтраница не найдена: {url}'
    except Exception as e:
        # Обработка ошибок, например, если не удается установить соединение с сервером
        print("Произошла ошибка в файле download_files.py\n"
              "при получении данных:", str(e))
        return None


# функция для создания файла в папке сайта
def create_file_in_website_folder(url=None):
    """функция для создания файла в папке сайта"""
    # Получаем путь к папке сайта
    folder_path = SiteConfig.query.first()  # запрос к бд
    # формируем путь для записи
    path_download = os.path.join(folder_path.upload_path_folder, generate_download_filename(url))

    if os.path.exists(folder_path.upload_path_folder):  # если папка сайта существует по пути из бд
        # проверка что такого файла в директории нет
        print(f'Проверка есть ли такой файл - {os.path.exists(path_download)}', end=" ")
        if not os.path.exists(path_download):  # если такого файла нет то
            data = get_webpage_data(url)  # Получаем данные страницы из адреса - создаем файл
            with file_lock_thread:  # блокируем доступ другому потоку
                with open(path_download, 'w', encoding='utf-8') as file:
                    file.write(data)  # запись данных
                    print(f'--->>> создание файла {generate_download_filename(url)}')
            return True
        else:
            print(f'-запись отменяется {path_download}')
    else:
        return False
