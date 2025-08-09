# homework_bot
Телеграм‑бот, который раз в заданный интервал обращается к API «Практикум Домашка» и присылает в чат статус последней домашней работы: взята на проверку, принята или отправлена на доработку.

Бот построен на pyTelegramBotAPI (TeleBot) и работает как длительно живущий процесс с повторными запросами к API каждые RETRY_PERIOD секунд (по умолчанию — 600).

### Возможности

- Периодически опрашивает API Яндекс.Практикума.
- Отправляет в Telegram понятные сообщения о смене статуса.
- Ведёт подробные логи (в файл и в stdout).
- Строгая проверка ответа API и обработка нестандартных ситуаций (кастомные исключения).


Автор проекта [Муллагалиев Вадим](https://github.com/k0fist)

## Техно-стек

- Python 3.11
- requests — HTTP‑клиент
- python‑dotenv — загрузка переменных окружения из .env
- pyTelegramBotAPI (telebot) — отправка сообщений в Telegram
- logging — логирование

### Переменные окружения

Создайте файл .env в корне проекта и укажите параметры:
PRACTICUM_TOKEN=ya_practicum_oauth_token
TELEGRAM_TOKEN=telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_or_user_id

### Как запустить проект Yacut:

1. Клонировать репозиторий и перейти в него в командной строке:

    ```bash
    git@github.com:k0fist/homework-bot.git
    cd homework-bot
    ```

2. Создать и активировать виртуальное окружение:
   ```bash
   python -m venv venv
   source venv/Scripts/activate   # или venv/bin/activate на Linux
   ```
3. Установить зависимости:
   ```bash
   pip install -r requirements.txt
   ```

4. Создать в директории проекта файл .env с пятью переменными окружения:

    ```
    PRACTICUM_TOKEN=ya_practicum_oauth_token
    TELEGRAM_TOKEN=telegram_bot_token
    TELEGRAM_CHAT_ID=your_chat_or_user_id
    ```

5. Запустить проект:

    ```
    python main.py
    ```

### Как это работает

check_tokens() — валидирует наличие всех нужных токенов.

get_api_answer(timestamp) — обращается к https://practicum.yandex.ru/api/user_api/homework_statuses/ с заголовком авторизации OAuth и параметром from_date. Возвращает разобранный JSON или бросает исключения при проблемах сети/кода ответа/ошибках в теле.

check_response(response) — убеждается, что пришёл словарь с ключом homeworks, где значение — список.

parse_status(homework) — извлекает homework_name и status, сопоставляет статус с человекочитаемым вердиктом.

send_message(bot, message) — отправляет сообщение в Telegram, логирует успех/ошибку.

main() — основной цикл: опрос API → проверка/парсинг → отправка в чат только изменившихся сообщений → ожидание RETRY_PERIOD и повтор.
