import asyncio
import logging

import configargparse

from utils import closing
from utils import ProtocolError
from utils import WrongToken

logger = logging.getLogger('sender')


async def connect_and_send(host, port, token, message):
    with closing(await asyncio.open_connection(host, port)) as (reader, writer):

        line = await reader.readline()
        decoded_line = line.decode()
        logger.debug('> %r', line)
        if not decoded_line.startswith(
                'Hello %username%! Enter your personal hash or leave it empty to create new account.\n'):
            raise ProtocolError(f'wrong hello message {line!r}')

        token_message = f'{token}\n'
        logger.debug('< %r', token_message)
        writer.write(token_message.encode())
        await writer.drain()

        line = await reader.readline()
        decoded_line = line.decode()
        logger.debug('> %r', line)
        if not decoded_line.startswith('{') or token not in decoded_line:
            raise WrongToken(f'cant login {line!r}')

        line = await reader.readline()
        decoded_line = line.decode()
        logger.debug('> %r', decoded_line)
        if not decoded_line.startswith('Welcome to chat! Post your message below. End it with an empty line.\n'):
            raise ProtocolError(f'wrong welcome message {line!r}')

        logger.debug('< %r', message)
        writer.write(f'{message}\n\n'.encode())

        line = await reader.readline()
        logger.debug('> %r', line)
        if not line.decode().startswith(
                'Message send. Write more, end message with an empty line.\n'):
            raise ProtocolError(f'wrong confirm message {line!r}')

        logger.debug(f'message <{message}> sent')


def main():
    args = configargparse.ArgParser(default_config_files=['.settings'])
    args.add('-c', '--config', required=False, is_config_file=True, help='config file path')
    args.add('--writer_host', required=False, env_var='WRITER_HOST', help='host of server')
    args.add('--writer_port', required=False, env_var='WRITER_PORT', help='port of server')
    args.add('--writer_token', required=False, env_var='TOKEN', help='port of server')
    args.add('--message', required=True, help='message for chat')
    args.add('--loglevel', required=False, help='log level')

    options, _ = args.parse_known_args()
    if options.loglevel:
        logging.basicConfig(level=options.loglevel)
        logger.setLevel(options.loglevel)

    logger.debug(options)

    asyncio.run(
        connect_and_send(
            options.writer_host,
            options.writer_port,
            options.writer_token,
            options.message))


if __name__ == '__main__':
    main()
