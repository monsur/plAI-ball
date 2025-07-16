import time
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from podcaster.src import args_helper
from podcaster.src import http_helper
from podcaster.src import logger_helper
from podcaster.src import os_helper

logger = logger_helper.get_logger(__name__)

def run(args):

    def get_boxscore_urls(html, source_url):
        soup = BeautifulSoup(html, 'html.parser')
        boxscore_urls = []

        # Find all links that contain "box score" in their text
        for link in soup.find_all('a', string=lambda text: text and 'box score' in text.lower()):
            href = link.get('href')
            if href:
                # Convert relative URLs to absolute URLs
                absolute_url = urljoin(source_url, href)
                boxscore_urls.append(absolute_url)

        return boxscore_urls

    def save_data(url, suffix):
        html = http_helper.make_request(url)

        # Create filename from URL
        filename = f"{url.split('/')[-1]}-{suffix}.html"

        # Save HTML content
        os_helper.write_file(html, args.output_data_dir, filename)

    source_url = f"https://www.espn.com/mlb/scoreboard/_/date/{args.date}"
    logger.info(f"Fetching box scores from: {source_url}")

    source_html = http_helper.make_request(source_url)

    boxscore_urls = get_boxscore_urls(source_html, source_url)
    logger.info(f"Found {len(boxscore_urls)} games")

    for boxscore_url in boxscore_urls:
        save_data(boxscore_url, "boxscore")
        time.sleep(args.delay)
        save_data(boxscore_url.replace("boxscore", "recap"), "recap")
        time.sleep(args.delay)

    return len(boxscore_urls)

if __name__ == "__main__":
    run(args_helper.get_args())
