""" Файл форм  для модуля WTF"""

from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired, URL


# Класс для создания объекта проверки что в поле введена строка в виде ссылки
class UrlLinkForm(FlaskForm):
    index_site_link = StringField('*Адрес домена (обязательно)', validators=[DataRequired(), URL(message="В поле введены некорректные данные")])
    link_url_start = StringField('*Ссылка для парсинга', validators=[DataRequired(), URL(message="В поле введены некорректные данные")])
