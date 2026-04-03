from pathlib import Path
from bs4 import BeautifulSoup, Comment
from podcaster.src import args_helper
from podcaster.src import logger_helper

logger = logger_helper.get_logger(__name__)

def run(args):

    def process_boxscore_file(filename):
        logger.info(f"Processing {filename}")
        content = (Path(args.output_data_dir) / filename).read_text(encoding='utf-8')
        soup = BeautifulSoup(content, 'html.parser')

        # Remove unwanted tags in one go
        for tag in soup.find_all(['script', 'style', 'link', 'img', 'svg']):
            tag.decompose()

        # Remove HTML comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Remove specific containers using CSS selectors
        selectors = [
            'div.HeaderScoreboardWrapper',
            'div.PageLayout.page-container.cf.page-footer-container',
            'div#fittOverlayContainer',
            'div#fittBGContainer',
            'div#lightboxContainer',
            'header.db.Site__Header__Wrapper.sticky'
        ]
        for sel in selectors:
            for tag in soup.select(sel):
                tag.decompose()

        # Remove unwanted attributes from all tags
        attrs_to_remove = ['class', 'data-react-helmet', 'style', 'lang']
        for tag in soup.find_all(True):
            for attr in attrs_to_remove:
                tag.attrs.pop(attr, None)

        # Prune meta tags
        for meta in soup.find_all('meta'):
            if (
                'charset' in meta.attrs or
                meta.get('name') in ['viewport', 'medium', 'title'] or
                (meta.get('name') or '').startswith('twitter:') or
                meta.get('property') == 'fb:app_id' or
                (meta.get('property') or '').startswith('og:') or
                'http-equiv' in meta.attrs
            ):
                meta.decompose()

        # Remove certain sections by header text
        for section in soup.find_all("section"):
            header = section.find("header")
            if header:
                h3 = header.find("h3")
                if h3 and any(x in h3.text for x in ["MLB News", "Videos", "Game Information"]):
                    section.decompose()

        # Get the HTML content
        if args.prettyprint:
            content = soup.prettify()
        else:
            content = str(soup)
            # Remove empty lines
            lines = [line for line in content.split('\n') if line.strip()]
            content = '\n'.join(lines)

        return content

    def process_recap_file(filename):
        logger.info(f"Processing {filename}")
        content = (Path(args.output_data_dir) / filename).read_text(encoding='utf-8')
        soup = BeautifulSoup(content, 'html.parser')
        return soup.find(class_='Story__Body t__body').get_text()

    def process_file(filename):
        content = process_boxscore_file(filename)

        try:
            content += "<recap>" + process_recap_file(filename.replace("boxscore", "recap")) + "</recap>"
        except Exception as e:
            logger.warning("No recap for %s: %s", filename, e)

        (Path(args.output_data_dir) / filename.replace("boxscore", "prompt")).write_text(content, encoding='utf-8')

        return content

    data_dir = Path(args.output_data_dir)
    files = [f.name for f in data_dir.iterdir() if f.name.endswith('boxscore.html')]

    if not files:
        logger.error("No HTML files found in input directory.")
        return

    content = f"There are {len(files)} games in this prompt."
    for filename in files:
        content += "\n\n## GAME ##\n\n"
        content += process_file(filename)
    (Path(args.output_dir) / "prompt.txt").write_text(content, encoding='utf-8')

if __name__ == "__main__":
    run(args_helper.get_args())
