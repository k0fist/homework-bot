import logging
import os
import time
import datetime
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telebot import TeleBot

from exceptions import ConnectionError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TOKENS = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
STATUS_CHANGE = 'Изменился статус проверки работы "{name}". {status}'
ERROR_PARAMENTS = ('\n1. endpoint: {endpoint} '
                   '\n2. params с from_date: {timestamp}')


def check_tokens():
    """Проверка, что переменных окружения не пустые."""
    missing_tokens = [name for name in TOKENS if not globals()[name]]
    if missing_tokens:
        logging.critical(
            f'Нужные переменные окружения пустые: {str(missing_tokens)}'
        )
        raise KeyError(f'Нужные токены пустые: {str(missing_tokens)}')
    logging.debug('Все токены найдены')


def send_message(bot, message):
    """Отправка ботом сообщений."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(f'Сообщение: {message}, отправлено пользователю')
    except Exception as error:
        logging.exception(
            f'Сообщение: {message}, не отправлено пользователю '
            f'Произошла ошибка: {error}. '
        )


def get_api_answer(timestamp):
    """Получение ответа от сервиса Практикум Домашка по API."""
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        status_code = homework_statuses.status_code
    except requests.RequestException as error:
        raise ConnectionError(
            f'Произошла ошибка: {error} на запрос, '
            f'с параметрами: {ERROR_PARAMENTS.format(
                endpoint=ENDPOINT,
                timestamp=timestamp
            )}')
    if status_code != HTTPStatus.OK:
        raise ConnectionError(
            f'API возвращает код {status_code}, '
            f'с параметрами: {ERROR_PARAMENTS.format(
                endpoint=ENDPOINT,
                timestamp=timestamp
            )}')
    data = homework_statuses.json()
    if 'code' in data or 'error' in data:
        raise ConnectionError(
            f'В ответе есть ключи code или error на запрос, '
            f'с параметрами: {ERROR_PARAMENTS.format(
                endpoint=ENDPOINT,
                timestamp=timestamp
            )}')
    return data


def check_response(response):
    """Проверка ответа от сервиса Практикум Домашка по API."""
    if not isinstance(response, dict):
        raise TypeError(
            "Ожидается, что в ответе словарь, а получили: "
            f"{type(response)}."
        )
    homeworks = response.get('homeworks', None)
    if 'homeworks' not in response:
        raise KeyError("Отсутствует ключ 'homeworks'.")
    if not isinstance(homeworks, list):
        raise TypeError(
            "Ожидается список под ключом 'homeworks', "
            f"а получили: {type(homeworks)}.")
    return homeworks[0]


def parse_status(homework):
    """Парсинг ответа от Практикум."""
    if 'homework_name' not in homework:
        raise KeyError("Не было найдено название работы")
    if 'status' not in homework:
        raise KeyError("Не был найден статус работы")
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        raise KeyError(f"Такой статус: {status} не обрабатывается")
    return (STATUS_CHANGE.format(
        name=homework.get('homework_name'),
        status=HOMEWORK_VERDICTS[status])
    )


def main():
    """Основная логика работы бота."""
    log_file = os.path.abspath(__file__) + '.log'
    logging.basicConfig(
        format=(
            '%(asctime)s - %(levelname)s'
            ' - %(funcName)s:%(lineno)d - %(message)s'),
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(log_file, mode='w', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    check_tokens()

    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = 0
    # timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if not homework:
                logging.debug('Нет домашних работ.')
            else:
                last_change_time = homework.get('date_updated')
                status = parse_status(homework)
                timestamp = datetime.datetime.strptime(
                    last_change_time,
                    '%Y-%m-%dT%H:%M:%SZ'
                ).timestamp()
                send_message(bot, status)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
