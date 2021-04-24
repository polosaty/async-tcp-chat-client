import asyncio
import json
import logging
import os

import configargparse

from utils import closing
from utils import ProtocolError
from utils import WrongToken

logger = logging.getLogger('register')


async def connect_and_register(host, port, nickname):
    with closing(await asyncio.open_connection(host, port)) as (reader, writer):

        line = await reader.readline()
        decoded_line = line.decode()
        logger.debug('> %r', line)
        if not decoded_line.startswith(
                'Hello %username%! Enter your personal hash or leave it empty to create new account.\n'):
            raise ProtocolError(f'wrong hello message {line!r}')

        token_message = '\n'
        logger.debug('< %r', token_message)
        writer.write(token_message.encode())
        await writer.drain()

        line = await reader.readline()
        decoded_line = line.decode()
        logger.debug('> %r', line)
        if not decoded_line.startswith('Enter preferred nickname below:\n'):
            raise ProtocolError(f'wrong prompt message {line!r}')

        register_nickname_message = f'{nickname}\n'
        logger.debug('< %r', register_nickname_message)
        writer.write(register_nickname_message.encode())
        await writer.drain()

        line = await reader.readline()
        decoded_line = line.decode()
        logger.debug('> %r', line)
        if not decoded_line.startswith('{') or 'account_hash' not in decoded_line:
            raise WrongToken(f'cant register {line!r}')

        token_json = json.loads(decoded_line)
        token = token_json.get('account_hash')

        if not token:
            raise WrongToken(f'token not found in register answer {token_json!r}')

        return token


def main():
    args = configargparse.ArgParser(default_config_files=['.settings'])
    args.add('-c', '--config', required=False, is_config_file=True, help='config file path')
    # starts with '--' options can be set in a config file
    args.add('--writer_host', required=False, env_var='WRITER_HOST', help='host of server')
    args.add('--writer_port', required=False, env_var='WRITER_PORT', help='port of server')
    args.add('--loglevel', required=False, help='log level')
    args.add('writer_nickname', help='nickname to register')

    options, _ = args.parse_known_args()

    if options.loglevel:
        logging.basicConfig(level=options.loglevel)
        logger.setLevel(options.loglevel)

    logger.debug(options)

    token = asyncio.run(
        connect_and_register(
            options.writer_host,
            options.writer_port,
            options.writer_nickname,
        ))

    # сохраняем writer_token в конфиг для отправки сообщений из под зарегистриованного пользователя
    # для этого сохраняем его в переменные окружения, чтобы ArgParser его "увидел"
    # если есть другой способ, без использования "private" свойств ArgParser - сообщите мне
    os.environ['TOKEN'] = token
    # добавляем параметр writer_token в known_args
    args.add('--writer_token', required=False, env_var='TOKEN', help='token of server')
    # и перечитывем TOKEN из переменных окружения
    options, _ = args.parse_known_args()
    # сохраняем конфиг с writer_token
    args.write_config_file(options, ['.settings'], exit_after=False)
    logger.debug('exiting')


if __name__ == '__main__':
    main()
