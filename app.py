from pythonjsonlogger import jsonlogger
from aiolimiter import AsyncLimiter
from urllib.parse import urlparse
import asyncio
import aiohttp
import logging
import time
from pprint import pprint as pp
import random
import aiofiles
import typer
from typing_extensions import Annotated
from pathlib import Path
import os
from bs4 import BeautifulSoup
from swiftshadow import QuickProxy
# Configures a json style logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

print(f"QuickProxy proxy",QuickProxy())
newproxy = QuickProxy()
valid_proxy = newproxy[1]+"://"+newproxy[0]
print(f"valid_proxy...",valid_proxy)

async def HTTPClientDownloader(url, settings):
    max_tcp_connections = settings['max_tcp_connections']

    # uses the rate limiter
    async with settings["rate"]:

        # open a session to make the requests
        connector = aiohttp.TCPConnector(limit=max_tcp_connections)
        async with aiohttp.ClientSession(connector=connector) as session:
            start_time = time.perf_counter()  # Start timer

            proxy = None
            html = None

            # makes a GET request to the target website
            async with session.get(url, proxy=proxy, headers=settings['headers']) as response:
                html = await response.text()
                end_time = time.perf_counter()  # Stop timer
                elapsed_time = end_time - start_time  # Calculate time taken to get response
                status = response.status

                logger.info(
                    msg="Request complete.",
                    extra={
                        "status": status,
                        "url": url,
                        "elapsed_time": f"{elapsed_time:4f}",
                    }
                )

                # save the html in a cache folder. We want this here so that if we replay
                # the code we can fetch fro mthe local cache instead of fetching from the 
                # server every time.
                loc = os.path.join(settings['cache_dir'], settings["output_path"])
                async with aiofiles.open(loc, mode="w") as fd:
                    await fd.write(html)

async def dispatch(url, settings):
    await HTTPClientDownloader(url, settings)

# the location of where our async tasks are created and invoked
async def main(start_urls, settings):
    tasks = []
    for url in start_urls:
        task = asyncio.create_task(dispatch(url, settings))
        tasks.append(task)

    results = await asyncio.gather(*tasks)
    print(f"total requests", len(results))


# a cli interface to make the program user friendly
cli_app = typer.Typer()
@cli_app.command("amazon")
def amazon(
    url: Annotated[str, typer.Option("--url", "-u", help="url")],
    out: Annotated[str, typer.Option("--out", "-o", help="output path and file name")],
    use_cache: Annotated[bool, typer.Option(help="Read from the cached version of the page")] = False,
    max_tcp_connections: Annotated[int, typer.Option("--max-tcp-conn", help="max tcp connections")] = 1,
    rate: Annotated[int, typer.Option(help="num of requests per min")] = 1,
):
    def read_from_cache(file_path):
        html_content = None
        with open(file_path, "r") as file:
            html_content = file.read()
            # print(html_content)
            print("Fetching from cache")
        return html_content    


    # cache procedures
    host = urlparse(url).hostname
    directory = "cache"
    current_directory = Path.cwd()
    cache_dir = current_directory / directory / host
    cached_file = Path(cache_dir / out)


    user_agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36' # works!
    ]
    user_agent = random.choice(user_agents)
    settings = {
        "max_tcp_connections": max_tcp_connections,
        "proxies": [
           valid_proxy # "http://localhost:8765",
        ],

        "headers": {
            'user-agent': user_agent,
            'accept-language': 'en',
            'accept-encoding': 'gzip, deflate',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        },
        "cache_dir": cache_dir,
        "output_path": out,
        "rate": AsyncLimiter(rate, 60), # 10 reqs/min
    }

    # make sure the cache directory exists
    if not cache_dir.exists():
        cache_dir.mkdir(parents=True)

    # get the resulting HTML from the cache or make a GET request
    html = None
    if use_cache:
        html = read_from_cache(cached_file)
    else:
        # use the asyncio runtime to make a request
        asyncio.run(main([url], settings))
        # read the results from the cache folder
        html = read_from_cache(cached_file)

    # once you have the HTML you can parse the document to your liking
    # from here you can parse for the data you want
    soup = BeautifulSoup(html, 'html.parser')
    # the best seller items are fixed with this ID however it could change in the future
    items = soup.find_all("div", attrs={"id":'gridItemRoot'})
    print(items)



if __name__ == '__main__':
    cli_app()
