class NotFoundTokenError(Exception):
    """Исключение пустоты необходимых токенов."""


class StatusHomeworkError(Exception):
    """Исключение ответа от Практикум Домашка."""


class NotFoundHomeworkNameError(Exception):
    """Исключение ответа от Практикум Домашка."""


class ConnectionError(Exception):
    """Исключение, когда код статуса не равен 200."""
