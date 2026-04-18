import time
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from podcaster.src import args_helper
from podcaster.src import http_helper
from podcaster.src import logger_helper

logger = logger_helper.get_logger(__name__)

def fetch_standings(args):
    """Fetch ESPN MLB standings, parse into plain text, write to standings.txt.

    Non-fatal: any failure is logged and swallowed. Standings are nice-to-have,
    not required for the pipeline to continue.
    """
    url = "https://www.espn.com/mlb/standings"
    try:
        html = http_helper.make_request(url)
        if not html:
            logger.warning("Standings fetch returned no content; skipping")
            return

        soup = BeautifulSoup(html, 'html.parser')
        tables = soup.find_all('table')
        # ESPN renders standings as paired (names, stats) tables — one pair per league.
        # Row layout is 1:1 between the two: a division header in the names table
        # lines up with the column-label row ("W", "L", ...) in the stats table.
        lines = []
        stat_headers = []
        for i in range(0, len(tables), 2):
            names_table = tables[i]
            stats_table = tables[i + 1] if i + 1 < len(tables) else None
            if not stats_table:
                continue

            name_rows = names_table.find_all('tr')
            stat_rows = stats_table.find_all('tr')

            for name_row, stat_row in zip(name_rows, stat_rows):
                name_text = name_row.get_text(' ', strip=True)
                stat_cells = [c.get_text(strip=True) for c in stat_row.find_all(['th', 'td'])]
                if not name_text or not stat_cells:
                    continue
                # Division rows pair with the stats column-header row ("W", "L", ...).
                if stat_cells[0] == 'W':
                    stat_headers = stat_cells
                    if lines:
                        lines.append("")
                    lines.append(name_text)
                    continue
                def col(label):
                    return stat_cells[stat_headers.index(label)] if label in stat_headers else ''
                lines.append(
                    f"{name_text}  W:{col('W')}  L:{col('L')}  "
                    f"GB:{col('GB')}  STRK:{col('STRK')}  L10:{col('L10')}"
                )

        (Path(args.output_dir) / "standings.txt").write_text("\n".join(lines), encoding='utf-8')
        logger.info("Standings written")
    except Exception as e:
        logger.error(f"Failed to fetch standings: {e}")


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
        (Path(args.output_data_dir) / filename).write_text(html, encoding='utf-8')

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

    fetch_standings(args)

    return len(boxscore_urls)

if __name__ == "__main__":
    run(args_helper.get_args())
