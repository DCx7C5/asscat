import logging

from textual import logging as tlogging


def setup_logger(name) -> logging.Logger:

    logger = logging.getLogger(name)
    fileformatter = logging.Formatter(
        fmt='%(asctime)s %(levelname)s %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    handler = logging.FileHandler(
        filename='asscat.log',
        mode='a',
        encoding='utf-8',
    )
    handler.setFormatter(fileformatter)
    handler.setLevel(logging.DEBUG)
    tuihandler = tlogging.TextualHandler()
    tuihandler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.addHandler(tuihandler)
    logger.setLevel(logging.DEBUG)
    logging.basicConfig(
        handlers=[handler, tuihandler]
    )
    return logger



