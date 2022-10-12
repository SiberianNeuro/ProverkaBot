import logging

from loguru import logger


class InterceptHandler(logging.Handler):
    LEVELS_MAP = {
        logging.CRITICAL: "CRITICAL",
        logging.ERROR: "ERROR",
        logging.WARNING: "WARNING",
        logging.INFO: "INFO",
        logging.DEBUG: "DEBUG",
    }

    def _get_level(self, record):
        return self.LEVELS_MAP.get(record.levelno, record.levelno)

    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup():
    logger.level("DOCUMENTS", no=33, color="<blue>")
    logger.level("REGISTRATION", no=33, color="<green>")
    logger.level("GOOGLE", no=33, color="<cyan>")
    logger.level("DATABASE", no=33, color="<yellow>")
    logger.add('logs/logfile_{time:DD_MM_YYYY}.log', rotation='8:30', compression='zip',
               format="{time:DD-MM-YYYY at HH:mm:ss}: {level}: [{module}({line})]: {message}")
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO)
