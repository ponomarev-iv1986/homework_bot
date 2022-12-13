import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (CheckResponseError, GetApiAnswerError,
                        NoEnvVariableError, ParseStatusError, SendMessageError)

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s'
)
handler.setFormatter(formatter)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка доступности переменных окружения."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    raise NoEnvVariableError(
        'Отсутствует одна или несколько переменных окружения'
    )


def send_message(bot, message):
    """Отправка сообщения в Telegram чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logger.debug('Сообщение отправлено в чат')
    except Exception:
        logger.error('Ошибка отправки сообщения в чат')
        raise SendMessageError(
            'Ошибка отправки сообщения в чат'
        )


def get_api_answer(timestamp):
    """Запрос к API-сервису."""
    try:
        params = {'from_date': timestamp}
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except Exception:
        raise GetApiAnswerError(
            f'Ошибка запроса к API-сервису {ENDPOINT}'
        )
    if response.status_code != HTTPStatus.OK:
        raise GetApiAnswerError(
            'Передано что-то неожиданное при запросе к API'
        )
    return response.json()


def check_response(response):
    """Проверка ответа API."""
    if not isinstance(response, dict):
        raise TypeError(
            'Струтура данных в ответе API не соответствует ожиданиям'
        )
    if 'homeworks' not in response.keys():
        raise CheckResponseError(
            'В ответе API нет ключа "homeworks"'
        )
    if not isinstance(response['homeworks'], list):
        raise TypeError(
            'В ответе API данные домашек приходят не в виде списка'
        )


def parse_status(homework):
    """Извлечение статуса домашней работы."""
    try:
        homework_name = homework['homework_name']
    except Exception:
        raise ParseStatusError(
            'В ответе API нет ключа "homework_name"'
        )
    try:
        verdict = HOMEWORK_VERDICTS[homework['status']]
    except Exception:
        raise ParseStatusError(
            'Недокументированный статус домашки, либо домашка без статуса'
        )
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    try:
        check_tokens()
    except NoEnvVariableError as critical:
        logger.critical(critical)
        raise NoEnvVariableError(
            'Отсутствует одна или несколько переменных окружения'
        )

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response['homeworks']
            if not homeworks:
                send_message(
                    bot,
                    'Статус домашних работ не изменен'
                )
                logger.debug('Сообщение успешно отправлено в чат')
            else:
                status = parse_status(homeworks[0])
                send_message(
                    bot,
                    status
                )
                logger.debug('Сообщение успешно отправлено в чат')
            timestamp = response['current_date']
            time.sleep(RETRY_PERIOD)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            raise error


if __name__ == '__main__':
    main()
