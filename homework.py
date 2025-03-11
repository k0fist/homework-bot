from http import HTTPStatus
import logging
import os
import time

import requests
from dotenv import load_dotenv
from telebot import TeleBot

from requests.exceptions import RequestException, HTTPError

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
MISSING_TOKENS_PHRASE = 'Нужные переменные окружения пустые: {missing_tokens}.'
TOKENS_FOUND_PHRASE = 'Все токены найдены.'
PHRASE_SEND_MESSAGE = 'Сообщение: {message}, отправлено пользователю'
PHRASE_NO_SEND_MESSAGE = (
    'Сообщение: {message}, не отправлено пользователю. '
    'Произошла ошибка: {error}.'
)
ERROR_CONNECT_PHRASE = (
    'Произошла ошибка: {error} на запрос, с параметрами: '
    '\n1. url: {url} '
    '\n2. headers: {headers} '
    "\n3. params: {params}"
)
NOT_CORRECT_CODE_PHRASE = (
    'API возвращает код {status_code}, с параметрами: '
    '\n1. url: {url} '
    '\n2. headers: {headers} '
    "\n3. params: {params}"
)
ERROR_KEY_PHRASE = (
    'В ответе есть ключ {key} со значением {value} '
    'на запрос, с параметрами: '
    '\n1. url: {url} '
    '\n2. headers: {headers} '
    "\n3. params: {params}"
)
NEED_KEY_HM_PHRASE = (
    "Ожидается список под ключом 'homeworks', "
    'а получили: {type}.'
)
ERROR_PHRASE = 'Произошла ошибка: {error}.'
NEED_DICT_PHRASE = 'Ожидается, что в ответе словарь, а получили: {response}.'
NEED_KEY_PHRASE = 'Отсутствует ключ {key}.'
NOT_FOUND_NAME_PHRASE = 'Не было найдено название работы'
NOT_FOUND_STATUS_PHRASE = 'Не был найден статус работы'
STATUS_ERROR_PHRASE = 'Такой статус: {status} не обрабатывается'
NO_HOMEWORKS_PHRASE = 'Нет домашних работ.'


def check_tokens():
    """Проверка, что переменных окружения не пустые."""
    missing_tokens = [name for name in TOKENS if not globals()[name]]
    if missing_tokens:
        logging.critical(
            MISSING_TOKENS_PHRASE.format(missing_tokens=missing_tokens)
        )
        raise KeyError(
            MISSING_TOKENS_PHRASE.format(missing_tokens=missing_tokens)
        )
    logging.debug(TOKENS_FOUND_PHRASE)


def send_message(bot, message):
    """Отправка ботом сообщений."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(PHRASE_SEND_MESSAGE.format(message=message))
        return True
    except Exception as error:
        logging.exception(
            PHRASE_NO_SEND_MESSAGE.format(message=message, error=error)
        )
        return False


def get_api_answer(timestamp):
    """Получение ответа от сервиса Практикум Домашка по API."""
    requests_pars = dict(
        url=ENDPOINT,
        headers=HEADERS,
        params={'from_date': {timestamp}}
    )
    try:
        homework_statuses = requests.get(**requests_pars)
    except RequestException as error:  # Обрабатываем все исключения от requests
        logging.error(ERROR_CONNECT_PHRASE.format(
            error=error,
            **requests_pars
        ))
    status_code = homework_statuses.status_code
    if status_code != HTTPStatus.OK:
        raise HTTPError(
            NOT_CORRECT_CODE_PHRASE.format(
                status_code=status_code,
                **requests_pars
            ))
    data = homework_statuses.json()
    for key in ['error', 'code']:
        if key in data:
            raise ValueError(
                ERROR_KEY_PHRASE.format(
                    key=key,
                    value=data[key],
                    **requests_pars
                ))
    return data



def check_response(response):
    """Проверка ответа от сервиса Практикум Домашка по API."""
    if not isinstance(response, dict):
        raise TypeError(NEED_DICT_PHRASE.format(response=type(response)))
    if 'homeworks' not in response:
        raise KeyError(NEED_KEY_PHRASE.format(key='homeworks'))
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError(NEED_KEY_HM_PHRASE.format(
            type=type(homeworks)
        ))
    return homeworks


def parse_status(homework):
    """Парсинг ответа от Практикум."""
    if 'homework_name' not in homework:
        raise KeyError(NOT_FOUND_NAME_PHRASE)
    if 'status' not in homework:
        raise KeyError(NOT_FOUND_STATUS_PHRASE)
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(STATUS_ERROR_PHRASE.format(status=status))
    return (STATUS_CHANGE.format(
        name=homework['homework_name'],
        status=HOMEWORK_VERDICTS[status])
    )


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = 0
    sent_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if not homeworks:
                logging.debug(NO_HOMEWORKS_PHRASE)
                continue
            homework = homeworks[0]
            verdict = parse_status(homework)
            if verdict != sent_message and send_message(bot, verdict):
                sent_message = verdict
                timestamp = response.get('current_date')
        except Exception as error:
            message = ERROR_PHRASE.format(error=error)
            logging.error(message)
            if message != sent_message and send_message(bot, message):
                sent_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    import sys

    logging.basicConfig(
        format=(
            '%(asctime)s - %(levelname)s'
            ' - %(funcName)s:%(lineno)d - %(message)s'),
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(
                os.path.abspath(__file__) + '.log',
                mode='w',
                encoding='utf-8'
            ),
            logging.StreamHandler(sys.stdout)
        ]
    )
    main()
