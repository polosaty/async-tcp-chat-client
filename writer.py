import asyncio
import configargparse

class ProtocolError(Exception):
    pass


async def connect_and_send(host, port, token, message):
    reader, writer = await asyncio.open_connection(host, port)
    
    line = await reader.readline()
    if not line.decode().startswith(
            'Hello %username%! Enter your personal hash or leave it empty to create new account.\n'):
        raise ProtocolError(f'wrong hello message {line!r}')
    
    writer.write(f'{token}\n'.encode())
    await writer.drain()
    
    line = await reader.readline()
    decoded_line = line.decode()
    if not decoded_line.startswith('{') or token not in decoded_line:
        raise ProtocolError(f'cant login {line!r}')
    
    line = await reader.readline()
    decoded_line = line.decode()
    if not decoded_line.startswith('Welcome to chat! Post your message below. End it with an empty line.\n'):
        raise ProtocolError(f'wrong welcome message {line!r}')

    writer.write(f'{message}\n\n'.encode())

    line = await reader.readline()
    if not line.decode().startswith(
            'Message send. Write more, end message with an empty line.\n'):
        raise ProtocolError(f'wrong confirm message {line!r}')

    print(f'message <{message}> sent')

def main():
    args = configargparse.ArgParser(default_config_files=['.settings'])
    args.add('-c', '--config', required=False, is_config_file=True, help='config file path')
    # starts with '--' options can be set in a config file
    args.add('--writer_host', required=False, env_var='HOST', help='host of server')
    args.add('--writer_port', required=False, env_var='PORT', help='port of server')
    args.add('--writer_token', required=False, env_var='TOKEN', help='port of server')
    args.add('--message', required=True, help='message for chat')
    options, _ = args.parse_known_args()
    print(options)
    asyncio.run(
        connect_and_send(
            options.writer_host, 
            options.writer_port, 
            options.writer_token, 
            options.message))


if __name__ == '__main__':
    main()            