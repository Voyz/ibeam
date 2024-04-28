import datetime
import logging
import os
import sys
from pathlib import Path

initialized = False


def initialize(log_format: str,
               log_level: str,
               log_to_file: bool,
               outputs_dir: str
               ):
    global initialized
    if initialized: return
    initialized = True

    logger = logging.getLogger('ibeam')
    formatter = logging.Formatter(log_format)

    # stdout handler, for INFO and below:
    h1 = logging.StreamHandler(stream=sys.stdout)
    h1.setLevel(getattr(logging, log_level))
    h1.addFilter(lambda record: record.levelno <= logging.INFO)
    h1.setFormatter(formatter)
    logger.addHandler(h1)

    # stderr handler, for WARNING and above:
    h2 = logging.StreamHandler(stream=sys.stderr)
    h2.setLevel(logging.WARNING)
    h2.setFormatter(formatter)
    logger.addHandler(h2)


    logger.setLevel(logging.DEBUG)

    if log_to_file:
        file_handler = DailyRotatingFileHandler(os.path.join(outputs_dir, 'ibeam_log'))
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)


def set_level_for_all(logger, level):
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)


class DailyRotatingFileHandler(logging.FileHandler):

    def __init__(self, *args, date_format='%Y-%m-%d', **kwargs):
        self.timestamp = None
        self.date_format = date_format
        super().__init__(*args, **kwargs)

    def get_timestamp(self):
        return datetime.datetime.now().strftime(self.date_format)

    def get_filename(self, timestamp):
        return f'{self.baseFilename}__{timestamp}.txt'

    def _open(self):
        self.timestamp = self.get_timestamp()
        try:
            return open(self.get_filename(self.timestamp), self.mode, encoding=self.encoding)
        except FileNotFoundError:
            Path(self.baseFilename).parent.mkdir(parents=True, exist_ok=True)
            return open(self.get_filename(self.timestamp), self.mode, encoding=self.encoding)

    def emit(self, record):
        if self.get_timestamp() != self.timestamp:
            self.stream = self._open()

        super().emit(record)
