import string
import random
import argparse
import json
from os import path, mkdir
from bs4 import BeautifulSoup as bs
import asyncio
import aiohttp
import logging
import aiofiles
from contextlib import suppress

TARGET_URL = "https://news.ycombinator.com"
API_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
DEFAULT_CONCUR_REQ = 3

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y.%m.%d %H:%M:%S",
)


def randname(n=10):
    """_summary_

    Args:
        n (int, optional): Generated name length. Defaults to 10.

    Returns:
        str: Random string
    """
    return "".join(
        random.choice(string.ascii_lowercase + string.digits) for _ in range(n)
    )


def get_links(comment_content):
    """Searches for links in comments

    Args:
        comment_content (BeautifulSoup): Comment tag

    Returns:
        list: URL links extracted from comments
    """
    links = comment_content.find_all("a")
    if links:
        return [l.get("href") for l in links]
    else:
        return []


class Crawler:
    """
    A class designed to automatically collect top-30 news on news.ycombinator.com
    and links in comments.
    """

    def __init__(self, directory):
        self.download_dir = directory
        self.semaphore = asyncio.Semaphore(DEFAULT_CONCUR_REQ)

    async def crawl(self, period, amount):
        """Polls the site for new news

        Args:
            period (int): Polling interval in seconds
            amount (int): Number of processed top news
        """

        if not path.exists(self.download_dir):
            try:
                mkdir(self.download)
            except OSError as e:
                logging.ERROR(
                    f"Cannot create directory {self.download_dir} for downloads:{e}"
                )
                return
        self.session = aiohttp.ClientSession(
            loop=self.loop,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/112.0"
            },
        )

        while True:
            logging.info("Starting new iteration...")
            future = asyncio.ensure_future(self.get_posts(amount))

            await asyncio.sleep(period)

    async def close_connection(self):
        await self.session.close()

    async def finish_tasks(self):
        pending = asyncio.Task.all_tasks()
        for task in pending:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    def run_crawler(self, period: int, amount: int = 30) -> None:
        """Starts a poll Loop

        Args:
            period (int): Polling interval in seconds
            amount (int, optional): Number of processed top news. Defaults to 30.
        """
        self.loop = asyncio.get_event_loop()
        try:
            self.loop.run_until_complete(self.crawl(period, amount))

        except KeyboardInterrupt:
            logging.info("Shutting down - received keyboard interrupt")
            self.loop.run_until_complete(self.finish_tasks())
            self.loop.run_until_complete(self.close_connection())

        finally:
            self.loop.close()

    async def fetch(self, url):
        """Downloads page content
        Args:
            url (str): URL to request

        Raises:
            Exception: Downloading timeout expired
            Exception: Other errors

        Returns:
            bytes: Downloaded content
        """
        try:
            async with self.session.get(url) as response:
                return await response.read()
        except asyncio.TimeoutError:
            raise Exception(f"Timeout expired while downloading {url}")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            raise Exception(f"Exception while downloading {url}") from e

    async def get_comments(self, id):
        """Parses comments under a post looking for links

        Args:
            id (str): News post id
        """
        logging.info(f"Collecting comments for post {id}")
        comments_url = f"{TARGET_URL}/item?id={id}"
        try:
            response = await self.fetch(comments_url)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.error(e)
            return

        if not response:
            return
        root = bs(response, "html.parser")
        comments = root.find_all("span", {"class": "commtext c00"})
        comment_links = list()
        folder = path.join(self.download_dir, id)
        for comm in comments:
            links = get_links(comm)
            if links:
                comment_links.extend(links)

        print(comment_links)
        tasks = [self.download(l, folder) for l in comment_links]
        results = await asyncio.gather(*tasks)

    async def get_posts(self, amount: int):
        """Parses main page with top news

        Args:
            amount (int): Number of processed top news
        """
        try:
            response = await self.fetch(API_URL)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.error(e)
            return

        if not response:
            return

        news = json.loads(response.decode("utf-8"))
        tasks = [self.process_post(n) for n in news[:amount]]

        results = await asyncio.gather(*tasks)

    async def process_post(self, post_id: int):
        """Parses news post and starts downloading

        Args:
            post_info (int): Post Id
        """
        folder = path.join(self.download_dir, str(post_id))
        if path.exists(folder):
            logging.info(f"Post {post_id} had already previously saved. Skipping...")
            return

        logging.info(f"Collecting links for post {post_id}")
        comments_url = f"{TARGET_URL}/item?id={post_id}"
        try:
            async with self.semaphore:
                response = await self.fetch(comments_url)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.error(e)
            return

        if not response:
            return
        post_comment_page = bs(response, "html.parser")
        comments = post_comment_page.find_all("span", {"class": "commtext c00"})
        links = list()
        for comm in comments:
            links = get_links(comm)
            if links:
                links.extend(links)

        title_elem = post_comment_page.find("span", {"class": "titleline"}).find("a")
        link = title_elem.get("href")
        links.append(link)

        mkdir(folder)
        tasks = [self.download(l, folder) for l in links]
        results = await asyncio.gather(*tasks)

    async def download(self, url: str, folder: str):
        """Download web page provided by URL

        Args:
            url (str): Target URL
            folder (str): Folder to save
        """
        fpath = path.join(folder, randname())
        logging.info(f"Saving {url} to {fpath}")
        try:
            response = await self.fetch(url)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.error(e)
            return
        if response:
            async with aiofiles.open(fpath, "w+b") as fout:
                await fout.write(response)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyses Nginx log for most requested URLs and generate report"
    )
    parser.add_argument(
        "--period",
        metavar="period",
        type=int,
        default=120,
        help="Poll period in seconds. Defaults to 2 minutes",
        required=False,
    )
    parser.add_argument(
        "--amount",
        metavar="amount",
        type=int,
        default=30,
        help="Number of posts to parse, Defaults to 30",
        required=False,
    )
    parser.add_argument(
        "--directory",
        metavar="directory",
        type=str,
        default=path.dirname(path.abspath(__file__)) + "/downloads",
        help="Download directory",
        required=False,
    )

    args = parser.parse_args()

    crawler = Crawler(args.directory)
    crawler.run_crawler(args.period, args.amount)
