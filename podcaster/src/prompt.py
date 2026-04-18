from pathlib import Path
from bs4 import BeautifulSoup
from podcaster.src import args_helper
from podcaster.src import logger_helper

logger = logger_helper.get_logger(__name__)

def run(args):

    def process_boxscore_file(filename):
        """Extract structured plain text from an ESPN boxscore HTML page."""
        logger.info(f"Processing {filename}")
        content = (Path(args.output_data_dir) / filename).read_text(encoding='utf-8')
        soup = BeautifulSoup(content, 'html.parser')
        lines = []

        # Game title from h1 (e.g. "Athletics @ Atlanta Braves")
        h1 = soup.find('h1')
        if h1:
            lines.append(h1.get_text(strip=True))

        # Team abbreviations from the first table (label column)
        team_abbrevs = []
        first_table = soup.find('table')
        if first_table:
            for row in first_table.find_all('tr'):
                cell_text = row.get_text(strip=True)
                if cell_text:
                    team_abbrevs.append(cell_text)

        # Line score from the table with inning headers (1,2,3...R,H,E)
        for table in soup.find_all('table'):
            headers = [th.get_text(strip=True) for th in table.find_all('th')]
            if '1' in headers and 'R' in headers:
                lines.append("")
                lines.append("Line Score:")
                header_str = "     " + "  ".join(f"{h:>3}" for h in headers)
                lines.append(header_str)
                data_rows = [tr for tr in table.find_all('tr') if tr.find('td')]
                for i, row in enumerate(data_rows):
                    cells = [td.get_text(strip=True) for td in row.find_all('td')]
                    team = team_abbrevs[i] if i < len(team_abbrevs) else "???"
                    row_str = f"{team:>4} " + "  ".join(f"{c:>3}" for c in cells)
                    lines.append(row_str)
                break

        # Win/Loss/Save pitchers
        decisions = []
        for span in soup.find_all('span'):
            label = span.get_text(strip=True)
            if label in ('win', 'loss', 'save'):
                parent = span.parent
                while parent and parent.name != 'a':
                    parent = parent.parent
                if parent:
                    text = parent.get_text(' ', strip=True)
                    # Remove the label word from the text
                    text = text.replace(f'{label} ', '', 1).strip()
                    prefix = {'win': 'W', 'loss': 'L', 'save': 'S'}[label]
                    decisions.append(f"  {prefix}: {text}")
        if decisions:
            lines.append("")
            lines.append("Pitching Decisions:")
            lines.extend(decisions)

        # Batting and pitching tables from sections
        sections = soup.find_all('section')
        for section in sections:
            label_div = section.find('div', string=lambda t: t and ('Hitting' in t or 'Pitching' in t))
            if not label_div:
                continue

            label = label_div.get_text(strip=True)
            lines.append("")
            lines.append(f"{label}:")

            tables = section.find_all('table')
            # Tables come in pairs: names table + stats table
            for j in range(0, len(tables), 2):
                names_table = tables[j]
                stats_table = tables[j + 1] if j + 1 < len(tables) else None
                if not stats_table:
                    continue

                headers = [th.get_text(strip=True) for th in stats_table.find_all('th')]
                name_rows = names_table.find_all('tr')[1:]  # skip header
                stat_rows = stats_table.find_all('tr')[1:]  # skip header

                for name_row, stat_row in zip(name_rows, stat_rows):
                    name = name_row.get_text(' ', strip=True)
                    cells = [td.get_text(strip=True) for td in stat_row.find_all('td')]
                    if name.lower() == 'team' or name.lower() == 'totals':
                        stats_str = ", ".join(f"{h}:{c}" for h, c in zip(headers, cells))
                        lines.append(f"  TEAM: {stats_str}")
                    else:
                        stats_str = ", ".join(f"{h}:{c}" for h, c in zip(headers, cells))
                        lines.append(f"  {name}: {stats_str}")

        # Scoring summary — parse the table with columns: [empty, empty, inning, play, away_score, home_score]
        for section in sections:
            heading = section.find('div', string=lambda t: t and 'Scoring Summary' in t)
            if not heading:
                header_el = section.find('header')
                if header_el:
                    h3 = header_el.find('h3')
                    if h3 and 'Scoring Summary' in h3.get_text():
                        heading = h3
            if heading:
                lines.append("")
                lines.append("Scoring Summary:")
                table = section.find('table')
                if table:
                    for row in table.find_all('tr'):
                        cells = [td.get_text(strip=True) for td in row.find_all('td')]
                        if not cells:
                            continue
                        # Filter out empty cells; typically: ['', '', '2nd', 'play description', '0', '2']
                        non_empty = [c for c in cells if c]
                        if len(non_empty) >= 3:
                            inning = non_empty[0]
                            play = non_empty[1]
                            score = f"{non_empty[2]}-{non_empty[3]}" if len(non_empty) >= 4 else ""
                            lines.append(f"  {inning}: {play} ({score})")
                break

        return "\n".join(lines)

    def process_recap_file(filename):
        logger.info(f"Processing {filename}")
        content = (Path(args.output_data_dir) / filename).read_text(encoding='utf-8')
        soup = BeautifulSoup(content, 'html.parser')
        return soup.find(class_='Story__Body t__body').get_text()

    def process_file(filename):
        content = process_boxscore_file(filename)

        try:
            content += "\n\n<recap>\n" + process_recap_file(filename.replace("boxscore", "recap")) + "\n</recap>"
        except Exception as e:
            logger.warning("No recap for %s: %s", filename, e)

        (Path(args.output_data_dir) / filename.replace("boxscore.html", "prompt.txt")).write_text(content, encoding='utf-8')

        return content

    data_dir = Path(args.output_data_dir)
    files = sorted(f.name for f in data_dir.iterdir() if f.name.endswith('boxscore.html'))

    if not files:
        logger.error("No HTML files found in input directory.")
        return

    content = f"There are {len(files)} games in this prompt."

    standings_path = Path(args.output_dir) / "standings.txt"
    if standings_path.exists():
        content += "\n\n## STANDINGS ##\n\n" + standings_path.read_text(encoding='utf-8')

    for filename in files:
        content += "\n\n## GAME ##\n\n"
        content += process_file(filename)
    (Path(args.output_dir) / "prompt.txt").write_text(content, encoding='utf-8')

if __name__ == "__main__":
    run(args_helper.get_args())
