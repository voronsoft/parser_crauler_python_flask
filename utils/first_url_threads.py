# Функция для фильтрации ссылок по типу расширения (исключаем медиа)
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from urllib.parse import unquote, urljoin, urlparse

ua = UserAgent()
headers = {'User-Agent': str(ua.random)}


# Функция для фильтрации ссылок по домену (если начинается с другого домена или '#' значит исключить)
def filters_by_domain(link, domain):
    # Определяем ссылки якоря
    if link[-1] == '#' or link[-2] == '#/':  # Исключаем ссылки, если в конце ссылки # или #/
        return False
    if urlparse(link).fragment:
        return False
    if not link.startswith(domain):  # Исключаем ссылки, которые не относятся к базовому домену
        return False
    return True


def filters_by_type_links(url):
    extension = ['.jpeg', '.jpg', '.gif', '.png', '.pdf', '.bmp', '.webp', '.swg', '.mp4', '.avi', '.mp3',
                 '.movie', '.mov', '.wmv', 'wma', '.wav', '.tiff', '.tif', '.mp4', '.ico']
    return not any([True for ext in extension if url.endswith(ext)])  # Если есть такое расширение вернуть False


# Функция для получения всех ссылок на странице
def get_links_on_page(url, domain):
    response = requests.get(url, headers=headers)
    # Проверяем статус ответа сервера
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'lxml')
        # Находим все ссылки на странице (всех видов)
        all_urls_href = [unquote(urljoin(domain, link.get('href'))) for link in soup.find_all(lambda tag: tag.has_attr('href'))]
        all_urls_src = [unquote(urljoin(domain, link.get('src'))) for link in soup.find_all(lambda tag: tag.has_attr('src'))]
        all_urls = set(all_urls_href + all_urls_src)  # Удаляем дубликаты

        # Удаляем адреса которые не начинаются с нашего домена а так же адреса содержащие якоря - '#'
        all_urls = [link for link in all_urls if filters_by_domain(link, domain)]
        # Удаляем ссылки которые являются медиа
        all_urls = [link for link in all_urls if filters_by_type_links(link)]
        # Удаляем ссылки .css и .js

        all_urls = [link for link in all_urls if not link.endswith('css')]
        all_urls = [link for link in all_urls if not link.endswith('js')]

        return all_urls
    else:
        print(f"Ошибка при запросе страницы {url}. Статус код: {response.status_code}")
        return []
