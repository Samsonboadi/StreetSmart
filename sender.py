import sys
import logging
import logging.handlers
import random
import time

PANGRAMS = [
    'Quick zephyrs blow, vexing daft Jim.',
    'How quickly daft jumping zebras vex.',
    'Jail zesty vixen who grabbed pay from quack.',
    'The five boxing wizards jump quickly.',
    'The quick brown fox jumps over the lazy dog.',
    'Sphinx of black quartz, judge my vow.',
    'Pack my box with five dozen liquor jugs.',
    'The quick onyx goblin jumps over the lazy dwarf.',
    'Cwm fjord bank glyps vext quiz.',
    'How razorback-jumping frogs can level six piqued gymnasts!',
    'Cozy lummox gives smart squid who asks for job pen.',
    'Amazingly few discotheques provide jukeboxes.',
    "'Now fax quiz Jack!' my brave ghost pled",
    "Watch Jeopardy!, Alex Trebek's fun TV quiz game.",
    'Jackdaws love my big sphinx of quartz.',
]


def main(port=logging.handlers.DEFAULT_TCP_LOGGING_PORT):
    rootLogger = logging.getLogger('')
    rootLogger.setLevel(logging.DEBUG)
    socketHandler = logging.handlers.SocketHandler('localhost', port)
    rootLogger.addHandler(socketHandler)

    logging.info('Jackdaws love my big sphinx of quartz.')

    logger1 = logging.getLogger('myapp.area1')
    logger2 = logging.getLogger('myapp.area2')

    loggers = [logger1.debug, logger1.info, logger1.warning, logger1.error,
               logger2.debug, logger2.info, logger2.warning, logger2.error]

    for i in range(10):
        message = random.choice(PANGRAMS)
        logger = random.choice(loggers)
        logger(message)
        time.sleep(random.randrange(10))


# logger1.debug('Quick zephyrs blow, vexing daft Jim.')
# logger1.info('How quickly daft jumping zebras vex.')
# logger2.warning('Jail zesty vixen who grabbed pay from quack.')
# logger2.error('The five boxing wizards jump quickly.')
# logger2.error('The quick brown fox jumps over the lazy dog.')
# logger2.error('Sphinx of black quartz, judge my vow.')
# logger2.error('Pack my box with five dozen liquor jugs.')
# logger2.error('The quick onyx goblin jumps over the lazy dwarf.')
# logger2.error('Cwm fjord bank glyps vext quiz.')
# logger2.error('How razorback-jumping frogs can level six piqued gymnasts!')
# logger2.error('Cozy lummox gives smart squid who asks for job pen.')
# logger2.error('Amazingly few discotheques provide jukeboxes.')
# logger2.error("'Now fax quiz Jack!' my brave ghost pled")
# logger2.error("Watch Jeopardy!, Alex Trebek's fun TV quiz game.")
# logging.info('Jackdaws love my big sphinx of quartz.')

if __name__ == "__main__":
    main(sys.argv[1])
