import asyncio
import aiofiles
import datetime


def make_timestamp():
    return datetime.datetime.now().strftime("%Y.%m.%d %H:%M")

async def connect_and_read(host, port):
    reader, writer =   await asyncio.open_connection(host, port)
    async with aiofiles.open('chat.log', mode='a') as chat_log_file:
        while not reader.at_eof():
            line = await reader.readline()
            formated_line = f'[{make_timestamp()}] {line.decode()}'
            print(formated_line)

            await chat_log_file.write(formated_line)


if __name__ == '__main__':
    host, port = 'minechat.dvmn.org', 5000
    asyncio.run(connect_and_read(host, port))
