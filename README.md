# async-tcp-chat-client

## Чтобы читать сообщения из чата

```
docker-compose run --rm app
```

## Чтобы зарегистрировать нового пользователя
```
docker-compose run --rm app python register.py writer_nickname
```


## Чтобы отправить сообщение

```
docker-compose run --rm app  python writer.py --message Сообщение
```
