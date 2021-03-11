import datetime
import logging
import os

from ibeam.src import var

initialized = False


def initialize():
    global initialized
    if initialized: return
    initialized = True

    logger = logging.getLogger('ibeam')
    formatter = logging.Formatter('%(asctime)s|%(levelname)-.1s| %(message)s')

    stream_handler = logging.StreamHandler()

    stream_handler.setFormatter(formatter)
    logging.getLogger('ibeam').setLevel(getattr(logging, var.LOG_LEVEL))
    logger.addHandler(stream_handler)

    if var.LOG_TO_FILE:
        file_handler = DailyRotatingFileHandler(os.path.join(var.OUTPUTS_DIR, 'ibeam_log'))
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)


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
        return open(self.get_filename(self.timestamp), self.mode, encoding=self.encoding)

    def emit(self, record):
        if self.get_timestamp() != self.timestamp:
            self.stream = self._open()

        super().emit(record)
