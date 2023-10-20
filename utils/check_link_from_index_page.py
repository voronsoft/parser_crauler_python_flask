from urllib.parse import urlparse, unquote


# Функция проверки что ссылка не указывает на конкретный файл не css не js и т д
# Создана для проверки стартовой страницы для парсинга ( поле 2 на главной странице)
def check_start_link(link):
    """Проверка корректности стартовой страницы не должна указывать на файл"""
    link = unquote(link)  # Переводим ссылку в удобочитаемый вид
    if '.css' in link or '.js' in link:
        return False
    else:
        return True


# Функция проверки корректности домена
def check_domain_link(link):
    """Проверка корректности домена"""
    link = unquote(link)  # Переводим ссылку в удобочитаемый вид
    domain = urlparse(link)
    if domain.path == '/' and domain.scheme + '://' + domain.netloc + domain.path == link:
        return True
    else:
        return False
