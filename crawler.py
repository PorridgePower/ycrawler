import string
import random
import argparse
from os import path, mkdir
from bs4 import BeautifulSoup as bs
import asyncio
import aiohttp
import logging
import aiofiles
from contextlib import suppress

TARGET_URL = "https://news.ycombinator.com"

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

    def __init__(self, target_url, directory):
        self.target_url = target_url
        self.download_dir = directory

    async def crawl(self, period):
        """Polls the site for new news

        Args:
            period (int): Polling interval in seconds
        """
        self.session = aiohttp.ClientSession(loop=self.loop)

        while True:
            logging.info("Starting new iteration...")
            future = asyncio.ensure_future(self.get_posts())

            await asyncio.sleep(period)

    async def close_connection(self):
        await self.session.close()

    async def finish_tasks(self):
        pending = asyncio.Task.all_tasks()
        for task in pending:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    def run_crawler(self, period: int) -> None:
        """Starts a poll Loop

        Args:
            period (int): Polling interval in seconds
        """
        self.loop = asyncio.get_event_loop()
        try:
            self.loop.run_until_complete(self.crawl(period))

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

    async def get_posts(self):
        """Parses main page with top news"""
        try:
            response = await self.fetch(TARGET_URL)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.error(e)
            return

        if not response:
            return

        root = bs(response, "html.parser")
        news = root.find_all("tr", {"class": "athing"})
        tasks = [self.process_post(n) for n in news]

        results = await asyncio.gather(*tasks)

    async def process_post(self, post_info: bs):
        """Parses news post and starts downloading

        Args:
            post_info (BeautifulSoup): Tag element
        """
        id = post_info.get("id")
        if path.exists(path.join(self.download_dir, id)):
            logging.info(f"Post {id} had already previously saved. Skipping...")
            return
        logging.info(f"Process post {id}")
        title_elem = post_info.find("span", {"class": "titleline"}).find("a")
        link = title_elem.get("href")
        folder = path.join(self.download_dir, id)
        mkdir(folder)
        await self.download(link, folder)
        await self.get_comments(id)

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
        help="Poll period in seconds. Default 2 minutes",
        required=False,
    )
    parser.add_argument(
        "--direcroty",
        metavar="direcroty",
        type=str,
        default=path.dirname(path.abspath(__file__)) + "/downloads",
        help="Download direcroty",
        required=False,
    )

    args = parser.parse_args()

    crawler = Crawler(TARGET_URL, args.direcroty)
    crawler.run_crawler(args.period)
