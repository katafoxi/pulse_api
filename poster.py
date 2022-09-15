from functools import wraps
from queue import Empty

import requests
from celery import Celery
from kombu import Queue
from pyrabbit.api import Client
from pyrabbit.http import HTTPError

# Прототип решения: https://habr.com/ru/post/494090/
# Алгоритм ограничения пропускной способности: https://en.wikipedia.org/wiki/Token_bucket

base_url = [
    'https://jsonplaceholder.typicode.com',
    'http://188.127.251.4:8240'
]
BACKEND_URL = 'redis://app_redis:6379/1'
BROKER_URL = 'pyamqp://guest@rabbitmq:5672//'
app = Celery(
    'getter_post',
    broker=BROKER_URL,
    backend=BACKEND_URL
)

task_queues = [
    Queue('original'),
    Queue('mirror')
]

# Предел пропускной способности API в минуту
rate_limits = {
    'original': 29,
    'mirror': 29
}

# автоматически сгенерируем очереди с токенами под все группы, на которые нужен лимит
task_queues += [Queue(name + '_tokens', max_length=2) for name, limit in rate_limits.items()]

app.conf.task_queues = task_queues


# это таска будет играть роль токена
# она никогда не будет запущена, мы просто будем забирать ее как сообщение из очереди
@app.task
def token():
    return 1


# автоматически настроим выпуск токенов с нужной скоростью
# @app.on_after_configure.connect
@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    for name, limit in rate_limits.items():
        app.add_periodic_task(60 / limit, token.signature(queue=name + '_tokens'), name=name + '_tokens')


# функция для взятия токена из очереди
def rate_limit(task_group):
    def decorator_func(func):
        @wraps(func)
        def function(self, *args, **kwargs):
            with self.app.connection_for_read() as conn:
                with conn.SimpleQueue(task_group + '_tokens', no_ack=True, queue_opts={'max_length': 2}) as queue:
                    try:
                        queue.get(block=True, timeout=5)
                        return func(self, *args, **kwargs)
                    except Empty:
                        self.retry(countdown=1)

        return function

    return decorator_func


@app.task(bind=True, max_retries=None)
@rate_limit('original')
def get_post_original_api(self, post_id):
    response = requests.get(f"{base_url[0]}/posts/{post_id}", timeout=2)
    return response.json()


@app.task(bind=True, max_retries=None)
@rate_limit('mirror')
def get_post_mirror_api(self, post_id):
    response = requests.get(f"{base_url[1]}/posts/{post_id}", timeout=2)
    return response.json()


def get_rabbitmq_queue_length(queue: str) -> int:
    """
    Счетчик длины очереди в RabbitMQ
    https://stackoverflow.com/questions/17863626/retrieve-queue-length-with-celery-rabbitmq-django
    :param queue:
    :return:
    """
    count = 0
    try:
        cl = Client('rabbitmq:15672', 'guest', 'guest')
        count = cl.get_queue_depth('/', queue)
    except HTTPError as e:
        print("Exception: Could not establish to rabbitmq http api: " + str(
            e) + " Check for port, proxy, username/pass configuration errors")
        raise

    return count


def get_post(post_id: int):
    if type(post_id) == int:
        if get_rabbitmq_queue_length('original') >= get_rabbitmq_queue_length('mirror'):
            return get_post_mirror_api.apply_async(queue='mirror', kwargs={'post_id': post_id}).get()
        else:
            return get_post_original_api.apply_async(queue='original', kwargs={'post_id': post_id}).get()
    else:
        return 'Uncorrect post_id number'
