class GetApiAnswerError(Exception):
    """Ошибка запроса к API-сервису."""

    pass


class CheckResponseError(Exception):
    """Ответ API не соответствует документации."""

    pass


class SendMessageError(Exception):
    """Ошибка отправки сообщения в чат."""

    pass


class ParseStatusError(Exception):
    """Ошибка извлечения статуса ДР."""

    pass
