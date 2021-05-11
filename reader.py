"""Chat reader module."""

import asyncio
from asyncio.exceptions import TimeoutError
import datetime
import logging

import aiofiles
import configargparse

from consts import CONNECT_TIMEOUT
from consts import READ_TIMEOUT
from utils import Backoff
from utils import open_connection

logger = logging.getLogger('reader')


def make_timestamp():
    """Make formatted current time string."""
    return datetime.datetime.now().strftime("%Y.%m.%d %H:%M")


@Backoff.async_retry(exception=TimeoutError, max_wait=60, jitter=1, logger=logger,
                     min_time_for_reset=max(CONNECT_TIMEOUT, READ_TIMEOUT) + 1)
async def connect_and_read(host, port, history_file):
    """Connect to chat server, read and save all messages to history_file."""
    async with open_connection(host, port) as (reader, _):

        async with aiofiles.open(history_file, mode='a') as chat_log_file:
            while not reader.at_eof():
                line = await asyncio.wait_for(
                    reader.readline(),
                    timeout=READ_TIMEOUT)
                formated_line = f'[{make_timestamp()}] {line.decode()}'
                logger.debug(repr(formated_line))

                await chat_log_file.write(formated_line)
                await chat_log_file.flush()


def main():
    args = configargparse.ArgParser(default_config_files=['.settings'])
    args.add('-c', '--config', required=False, is_config_file=True, help='config file path')
    # starts with '--' options can be set in a config file
    args.add('--host', required=False, env_var='HOST', help='host of server')
    args.add('--port', required=False, env_var='PORT', help='port of server')
    args.add('--loglevel', required=False, help='log level')
    args.add('--history', required=False, env_var='HISTORY_FILE', help='history file path')
    options, _ = args.parse_known_args()
    """Parse args and run reader."""

    if options.loglevel:
        logging.basicConfig(level=options.loglevel)
        logger.setLevel(options.loglevel)

    asyncio.run(connect_and_read(options.host, options.port, options.history))


if __name__ == '__main__':
    main()
