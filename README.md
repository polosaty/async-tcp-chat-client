# async-tcp-chat-client

Учебный проект по курсу [Асинхронный питон](https://dvmn.org/modules/async-python).
В проекте реализованы подключение к чату по протоколу TCP с последующим чтением переписки и запись в файл (по умолчанию chat.log).
Также реализованы регистрация пользователя и отправка сообщений в чат от имени зарегистрированного пользователя.

## Установка в virtualenv

Для установки потребуется python 3.9+ (теоретически должно работать на python 3.7, но это не тестировалось) и [virtualenv](https://virtualenv.pypa.io/en/latest/installation.html)

Скачиваем проект:

```shell
git clone git@github.com:polosaty/async-tcp-chat-client.git
# или git clone https://github.com/polosaty/async-tcp-chat-client.git
cd async-tcp-chat-client
```

Создаем виртуальное окружение, активируем его и устанавливаем в него зависимости:

```shell
virtualenv .env
source .env/bin/activate
pip install -r ./requirements.txt
```

### После установки зависимостей

Можно читать сообщения из чата:

```shell
python reader.py
```

Можно зарегистрировать нового пользователя:

```shell
python register.py writer_nickname
```

И отправлять от его имени сообщения в чат:

```shell
python writer.py --message Сообщение
```

## Установка в docker

Для установки потребуется docker + docker-compose

Скачиваем проект:
```shell
git clone git@github.com:polosaty/async-tcp-chat-client.git
# или git clone https://github.com/polosaty/async-tcp-chat-client.git
cd async-tcp-chat-client
```

Собираем образ:
```shell
docker-compose buld app
```

### После сборки образа

Можно читать сообщения из чата:

```shell
docker-compose run --rm app
```

Можно зарегистрировать нового пользователя:

```shell
docker-compose run --rm app python register.py writer_nickname
```

И отправлять от его имени сообщения в чат:

```shell
docker-compose run --rm app  python writer.py --message Сообщение
```

## Настройки

Все настройки можно задавать несколькими путями:
1. файлы конфигурации `.settings` (в нем уже заданы дефолтные настройки) и `.token` (в него сохраняется токен после регистрации)
2. переменные окружения
```shell
# адрес и порт сервера для отправки сообщений
WRITE_HOST=minechat.dvmn.org
WRITE_PORT=5050
# адрес и порт сервера для чтения сообщений
READ_HOST=minechat.dvmn.org
READ_PORT=5000
# токен тользователя
TOKEN=<guid>
# файл сохраняется история сообщений чата
HISTORY_FILE=chat.log
```
3. параметры командной строки для каждой из команд (подборнее `--help`)

## Gui

Также добавлены 2 графических приложения реализующие основные функции:
- `app.py` - для чтения и отправки сообщений
- `register_gui.py` - для регистрации нового пользователя

### Запуск в docker

Для регистрации нового пользователя:
```
docker-compose up register-gui
```

Для запуска чтения/отправки сообщений:
```
docker-compose up gui
```

### Запуск в virtualenv

Для регистрации нового пользователя:
```
python register_gui.py
```

Для запуска чтения/отправки сообщений:
```
python app.py
```
