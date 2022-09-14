# pulse_api
Есть метод API возвращающий информацию о посте https://jsonplaceholder.typicode.com/posts/<id> где <id> это идентификатор поста.

API имеет ограничение по частоте запросов до 30 раз в минуту, а надо иметь возможность обращаться к нему в несколько раз чаще.

При превышении ограничения происходит временная блокировка доступа.

Для этого API уже сделаны зеркала, api_addr = [‘https://jsonplaceholder.typicode.com’, ‘http://188.127.251.4:8240’,]

Надо написать функцию на Python, которая по заданному идентификатору поста будет возвращать ответ метода API.

Требования к функции:
1. Вызов функции не должен приводить к блокировке со стороны API.
2. Функция может вызываться одновременно из разных потоков и из разных процессов.
3. Функция должна эффективно использовать все доступные адреса для доступа к API.
4. Любой разработчик команды должен иметь возможность вызывать функцию и просто получить результат.

----

### Используемый стек

1) rabbitmq.
2) redis.
3) pyrabbit.
4) requests

----

#### Запуск контейнеров

```shell
docker-compose up

```

Зайти в контейнер app_selery и запустить worker  
```shell
celery -A poster worker -Q original
celery -A poster worker -Q mirror

```
После того как workers запущены, через импорт доступна функция poster.get_post(post_id), которая формирует запрос к ограниченному API, добавляет его в меньшую очередь ('https://jsonplaceholder.typicode.com',
 'http://188.127.251.4:8240'), по результатам выполнения возращает JSON-ответ.