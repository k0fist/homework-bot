class ApiResponseError(Exception):
    """Исключение в случаи когда в ответе отличного от 200."""


class ApiResponseDataError(Exception):
    """Исключение в случаи когда в ответе есть ключи-ошибки."""
