def test():
    import threading

    # threading.Thread

    thread_condition = threading.Condition()
    thread_condition.wait()  # ?
    thread_condition.notify_all()  # ?


# coding: utf-8

import logging, threading

from queue import Queue

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(message)s')

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
logger.addHandler(ch)

fibo_dict = {}
shared_queue = Queue()
input_list = [3, 10, 5, 7]

queue_condition = threading.Condition()


def fibonacci_task(condition):
    with condition:
        while shared_queue.empty():
            logger.info("[%s] - waiting for elements in queue.." % threading.current_thread().name)
            condition.wait()
        else:
            value = shared_queue.get()
            a, b = 0, 1
            for item in range(value):
                a, b = b, a + b
                fibo_dict[value] = a
            shared_queue.task_done()
            logger.debug("[%s] fibonacci of key [%d] with result [%d]" % (
                threading.current_thread().name, value, fibo_dict[value]))


def queue_task(condition):
    logging.debug('Starting queue_task...')
    with condition:
        for item in input_list:
            shared_queue.put(item)
            logging.debug("Notifying fibonacci_task threadsthat the queue is ready to consume..")
            condition.notify_all()


if __name__ == "__main__":
    threads = [
        threading.Thread(daemon=True, target=fibonacci_task, args=(queue_condition,))
        for i in range(4)
    ]

    [thread.start() for thread in threads]

    prod = threading.Thread(name='queue_task_thread', daemon=True, target=queue_task, args=(queue_condition,))
    prod.start()

    print([thread.join() for thread in threads])
