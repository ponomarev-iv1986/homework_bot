import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (CheckResponseError, GetApiAnswerError,
                        ParseStatusError, SendMessageError)

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
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


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
            'Ответ API не является словарем'
        )
    if 'homeworks' not in response:
        raise KeyError(
            'В ответе API нет ключа "homeworks"'
        )
    if 'current_date' not in response:
        raise KeyError(
            'В ответе API нет ключа "current_date"'
        )
    if not isinstance(response['homeworks'], list):
        raise TypeError(
            'В ответе API данные домашек приходят не в виде списка'
        )
    if not response['homeworks']:
        raise CheckResponseError(
            'Список домашних работ пуст'
        )


def parse_status(homework):
    """Извлечение статуса домашней работы."""
    if not isinstance(homework, dict):
        raise TypeError(
            'Домашняя работа должна быть в виде словаря'
        )
    try:
        homework_name = homework['homework_name']
    except KeyError:
        raise KeyError(
            'В ответе API нет ключа "homework_name"'
        )
    try:
        status = homework['status']
    except KeyError:
        raise KeyError(
            'В ответе API нет ключа "status"'
        )
    try:
        verdict = HOMEWORK_VERDICTS[status]
    except Exception:
        raise ParseStatusError(
            'Недокументированный статус домашки, либо домашка без статуса'
        )
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствует одна или несколько переменных окружения')
        sys.exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    previous_message = dict()
    error_message = ''
    info_message = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homework = response['homeworks'][0]
            if homework != previous_message:
                status = parse_status(homework)
                send_message(
                    bot,
                    status
                )
                previous_message = homework
            timestamp = response['current_date']
        except CheckResponseError as info:
            message = f'{info}'
            if message != info_message:
                logger.info(message)
                send_message(
                    bot,
                    'Бот успешно начал работу'
                )
                info_message = message
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != error_message:
                logger.error(message)
                send_message(
                    bot,
                    message
                )
                error_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
