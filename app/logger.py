import logging
import os
import sys

LOG_DIR = 'logs'

MAIN_LOGGER_NAME = 'main'

def get_logger(logger_name: str = MAIN_LOGGER_NAME, level = logging.INFO):
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    if not logger.handlers:
        file_handler = logging.FileHandler(os.path.join(LOG_DIR, f'{logger_name}.log'))
        
        formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
        )
        file_handler.setFormatter(formatter)

        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
        
    return logger