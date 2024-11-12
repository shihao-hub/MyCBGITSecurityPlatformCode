import sys
import re
import logging, threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor

# import requests

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(message)s')

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
logger.addHandler(ch)

html_link_regex = re.compile(r'<a\s(?:.*?\s)*?href=[\'"](.*?)[\'"].*?>')

urls = queue.Queue()
urls.put('http://www.google.com')
urls.put('http://br.bing.com/')
urls.put('https://duckduckgo.com/')
urls.put('https://github.com/')
urls.put('http://br.search.yahoo.com/')

result_dict = {}


def group_urls_task(urls):
    try:
        url = urls.get(True, 0.05)  # true表示阻塞其他线程访问这个队列，0.05表示阻塞的超时时间
        result_dict[url] = None
        logger.info("[%s] putting url [%s] in dictionary..." % (threading.current_thread().name, url))
    except queue.Empty:
        logging.error('Nothing to be done, queue is empty')


def crawl_task(url):
    # import requests
    links = ["tmp holder"]
    try:
        # request_data = requests.get(url)
        logger.info("[%s] crawling url [%s] ..." % (threading.current_thread().name, url))
        # links = html_link_regex.findall(request_data.text)
        import time
        time.sleep(1)
    except:
        logger.error(sys.exc_info()[0])
        raise
    finally:
        return (url, links)


if __name__ == "__main__":
    time_start = time.time()
    with ThreadPoolExecutor(max_workers=3) as group_link_threads:
        for i in range(urls.qsize()):
            future = group_link_threads.submit(group_urls_task, urls)

    with ThreadPoolExecutor(max_workers=3) as crawler_link_threads:
        future_tasks = {
            crawler_link_threads.submit(crawl_task, url): url
            for url in result_dict.keys()
        }
        for k, v in future_tasks.items():
            result_dict[v] = k.result()
    print("cost: {} s".format(time.time() - time_start))
    print(result_dict)
