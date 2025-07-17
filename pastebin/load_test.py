import asyncio
import functools
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import aiohttp
import requests


BASE_URL = "http://localhost:8000"
MY_TEXTS_URL = f"{BASE_URL}/mytexts"

N_REQUESTS = 10000
TEST_URL = BASE_URL


def make_request(url, cookies=None):
    return requests.get(url, cookies=cookies).status_code


async def thread_pool_async():
    with ThreadPoolExecutor(max_workers=100) as executor:
        urls = [TEST_URL for _ in range(N_REQUESTS)]

        start = time.time()
        tasks = [
            asyncio.get_running_loop().run_in_executor(
                executor,
                functools.partial(make_request, TEST_URL)
            )
            for url in urls
        ]
        results = asyncio.gather(*tasks)
        elapsed = time.time() - start

        print(f"Made {N_REQUESTS} requests to {TEST_URL} in {elapsed:.2f} seconds")



def thread_pool():
    with ThreadPoolExecutor(max_workers=100) as executor:
        urls = [TEST_URL for _ in range(N_REQUESTS)]

        start = time.time()
        results = executor.map(make_request, urls)
        elapsed = time.time() - start

        print([res for res in results])
        print(f"Made {N_REQUESTS} requests to {TEST_URL} in {elapsed:.2f} seconds")


async def main():
    #await thread_pool_async()
    thread_pool()


asyncio.run(main())
