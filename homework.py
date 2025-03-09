import logging
import os
import requests
import time
import json
from http import HTTPStatus

from dotenv import load_dotenv
from telebot import TeleBot
from exceptions import (
    StatusHomeworkError,
    NotFoundHomeworkNameError,
    ConnectionError
)

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
    """Отправка ботом сообщения."""
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
        if status_code != HTTPStatus.OK:
            raise ConnectionError(
                f'API возвращает код {status_code}, с параметрами:'
                f'1. endpoint: {ENDPOINT} '
                f'2. headers: {HEADERS} '
                f'3. params с from_date: {timestamp}'
            )
        data = homework_statuses.json()
        check_response(data)
        homeworks = data.get('homeworks', [])
        if not homeworks:
            return {}
        return homeworks[0]
    except requests.RequestException as error:
        logging.error(f'Ошибка, Практикум Домашка недоступна: {error}')
    except json.decoder.JSONDecodeError as error:
        logging.error(f'Ошибка, ответ пришел не в json формате: {error}')
    return None


def check_response(response):
    """Проверка ответа от сервиса Практикум Домашка по API."""
    if not isinstance(response, dict):
        raise TypeError("Ожидается словарь в ответе.")
    homeworks = response.get('homeworks', None)
    if not isinstance(homeworks, list):
        raise TypeError("Ожидается список под ключом 'homeworks'.")
    if 'homeworks' not in response:
        raise KeyError("Отсутствует ключ 'homeworks'.")
    if homeworks == []:
        logging.debug('Проектов за этот период нет')
        return False
    return True


def parse_status(homework):
    """Парсинг ответа от Практикум."""
    homework_name = 'Домашка'
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise NotFoundHomeworkNameError("Не было найдено название работы")
    status = homework.get('status')
    if status is None or HOMEWORK_VERDICTS.get(status) is None:
        raise StatusHomeworkError(
            "Не был найден статус работы или не существующе название"
        )
    return (
        f'Изменился статус проверки работы "{homework_name}". '
        f'{HOMEWORK_VERDICTS.get(status)}'
    )


def main():
    """Основная логика работы бота."""
    log_file = os.path.abspath(__file__) + '.log'
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(log_file, mode='w', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    check_tokens()

    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            if not response:
                logging.debug('Нет домашних работ.')
            else:
                status = parse_status(get_api_answer(timestamp))
                if status is not None:
                    send_message(bot, status)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        except StatusHomeworkError as error:
            logging.error(f'Ошибка {error}')
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
