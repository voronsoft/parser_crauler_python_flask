from urllib.parse import urlparse, unquote


# функция проверки что ссылка не указывает на конкретный файл
# не css не js и т д
# создана для проверки стартовой страницы для парсинга ( поле 2 на главной странице)
def check_start_link(link):
    """Проверка корректности стартовой страницы не должна указывать на файл"""
    link = unquote(link)  # переводим ссылку в удобочитаемый вид
    if '.css' in link or '.js' in link:
        return False
    else:
        return True


def check_domain_link(link):
    """Проверка корректности домена"""
    link = unquote(link)  # переводим ссылку в удобочитаемый вид
    domain = urlparse(link)
    if domain.path == '/' and domain.scheme + '://' + domain.netloc + domain.path == link:
        return True
    else:
        return False

