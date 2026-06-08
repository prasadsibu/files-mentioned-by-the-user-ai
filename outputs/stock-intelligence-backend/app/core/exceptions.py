class AppError(Exception):
    status_code = 500
    error_code = "APP_ERROR"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class StockNotFoundError(AppError):
    status_code = 404
    error_code = "STOCK_NOT_FOUND"


class AnalysisError(AppError):
    status_code = 422
    error_code = "ANALYSIS_ERROR"
