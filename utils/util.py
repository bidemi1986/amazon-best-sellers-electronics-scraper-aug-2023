import firebase_admin
from firebase_admin import credentials, firestore, storage
from pythonjsonlogger import jsonlogger
from aiolimiter import AsyncLimiter
from urllib.parse import urlparse
import asyncio
import aiohttp
import logging
import time
import random
from swiftshadow import QuickProxy
from bs4 import BeautifulSoup
from pathlib import Path
import os 


# Firebase setup
cred = credentials.Certificate("sample-firebase-ai-app-3e813-firebase-adminsdk-l2l4r-da0a22960f.json")  # Replace with your Firebase service account key path
firebase_admin.initialize_app(cred, {
    'storageBucket': 'sample-firebase-ai-app-3e813.firebasestorage.app'  # Replace with your Firebase storage bucket name
})
db = firestore.client()
bucket = storage.bucket()

# Configures a json style logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
 
newproxy = QuickProxy()
valid_proxy = newproxy[1] + "://" + newproxy[0]
print(f"valid_proxy...", valid_proxy)


def preprocess_html(html):
    """Remove unnecessary tags like scripts and styles to minimize file size."""
    soup = BeautifulSoup(html, "html.parser")
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()
    return str(soup)


async def store_metadata_in_batch(metadata_list):
    """Store metadata in Firestore as a batch operation."""
    batch = db.batch()
    for metadata in metadata_list:
        doc_ref = db.collection("scraped_data").document()
        batch.set(doc_ref, metadata)
    await asyncio.to_thread(batch.commit)


async def HTTPClientDownloader(url, settings, session):
    """Download HTML content from a URL and store it in Firebase Storage."""
    async with settings["rate"]:
        start_time = time.perf_counter()  # Start timer

        # Make a GET request to the target website
        async with session.get(url, proxy=None, headers=settings["headers"]) as response:
            html = await response.text()
            end_time = time.perf_counter()  # Stop timer
            elapsed_time = end_time - start_time
            status = response.status

            logger.info(
                msg="Request complete.",
                extra={
                    "status": status,
                    "url": url,
                    "elapsed_time": f"{elapsed_time:4f}",
                }
            )

            # Preprocess and upload HTML to Firebase Storage
            html = preprocess_html(html)
            host = urlparse(url).hostname
            file_name = f"{urlparse(url).netloc}_{int(time.time())}.html"
            blob = bucket.blob(f"scraped_html/{host}/{file_name}")
            upload_task = asyncio.to_thread(blob.upload_from_string, html, content_type="text/html")
            await upload_task
            blob.make_public()

            # Prepare metadata for Firestore
            metadata = {
                "url": url,
                "html_file_url": blob.public_url,
                "timestamp": time.time(),
            }
            return html, metadata


async def dispatch(url, settings, session):
    """Dispatch a single URL for scraping and storage."""
    return await HTTPClientDownloader(url, settings, session)


async def main(start_urls, settings):
    """Main function to manage asynchronous tasks for scraping."""
    tasks = []
    connector = aiohttp.TCPConnector(limit=settings["max_tcp_connections"])
    async with aiohttp.ClientSession(connector=connector,max_field_size=16384) as session:
        for url in start_urls:
            task = asyncio.create_task(dispatch(url, settings, session))
            tasks.append(task)

        results = await asyncio.gather(*tasks)

    # Separate HTML content and metadata
    html_list = [result[0] for result in results]
    metadata_list = [result[1] for result in results]

    # Store metadata in Firestore as a batch
    await store_metadata_in_batch(metadata_list)

    return html_list


def webscape_ninja(
    urls,
    out="output.html",
    use_cache=False,
    max_tcp_connections=5,
    rate=10,
):
    """Main entry point for scraping URLs."""
    if isinstance(urls, str):
        urls = [urls]

    # Prepare rate limiter and settings
    user_agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    ]
    user_agent = random.choice(user_agents)
    settings = {
        "max_tcp_connections": max_tcp_connections,
        "proxies": [valid_proxy],
        "headers": {
            "user-agent": user_agent,
            "accept-language": "en",
            "accept-encoding": "gzip, deflate",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        "rate": AsyncLimiter(rate, 60),  # Allow up to 10 requests per second
    }

    # Run the asyncio loop to scrape data
    html_list = asyncio.run(main(urls, settings))

    # Return the HTML content for all URLs
    return dict(zip(urls, html_list))