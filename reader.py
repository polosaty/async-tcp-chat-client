import asyncio
import datetime
import logging

import aiofiles
import configargparse

logger = logging.getLogger('reader')

def make_timestamp():
    return datetime.datetime.now().strftime("%Y.%m.%d %H:%M")


async def connect_and_read(host, port, history_file):
    reader, writer =   await asyncio.open_connection(host, port)
    async with aiofiles.open(history_file, mode='a') as chat_log_file:
        while not reader.at_eof():
            line = await reader.readline()
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
    print(options)
    if options.loglevel:
        logging.basicConfig(level=options.loglevel)
        logger.setLevel(options.loglevel)

    asyncio.run(connect_and_read(options.host, options.port, options.history))


if __name__ == '__main__':
    main()
