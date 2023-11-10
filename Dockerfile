# Используем официальный образ Python версии 3.11
FROM python:3.11

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /flask-parser-app

# Копируем все файлы из текущей директории внутрь контейнера
COPY . .

# Устанавливаем зависимости из requirements.txt
RUN pip install -r requirements.txt

# Команда для запуска приложения
CMD ["python", "threads.py"]