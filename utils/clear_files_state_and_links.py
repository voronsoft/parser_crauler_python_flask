# Функция очистки текстовых файлов state.txt и links.txt
import os
import threading

# Объект блокировки для потоков
file_lock_thread = threading.Lock()


# Очистка файлов state.txt и links.txt
def clear_files_state_and_links():
    """Очистка файлов state.txt и links.txt"""
    try:
        # Путь к файлу state.txt
        state_file_path = 'state.txt'
        # Путь к файлу links.txt
        links_file_path = 'links.txt'

        # Проверяем существование файла state.txt и удаляем его содержимое, если файл существует
        if os.path.exists(state_file_path):
            with file_lock_thread:
                with open(state_file_path, 'w', encoding='utf-8') as file:
                    file.truncate(0)  # Удаляем содержимое файла
                print('Файл state.txt очищен.')

        # Проверяем существование файла links.txt и удаляем его содержимое, если файл существует
        if os.path.exists(links_file_path):
            with file_lock_thread:
                with open(links_file_path, 'w', encoding='utf-8') as file:
                    file.truncate(0)  # Удаляем содержимое файла
            print('Файл links.txt очищен.')
    except Exception as e:
        print(f'Произошла ошибка при очистке данных в файлах state.txt и  links.txt:\n'
              f' {str(e)}', 'error')
