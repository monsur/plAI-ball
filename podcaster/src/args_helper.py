import argparse
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Imported after load_dotenv so config values are available for argparse defaults.
from podcaster.src import config  # noqa: E402

def get_args():
    """Get common arguments used across all scripts."""
    parser = argparse.ArgumentParser("plAI ball!")
    parser.add_argument('--date', type=str, help='Date in YYYYMMDD format (default: yesterday)',
                       default=(datetime.now() - timedelta(days=1)).strftime('%Y%m%d'))
    parser.add_argument('--delay', type=int, default=config.HTTP_DELAY_SECONDS,
                       help=f'Delay in seconds between downloads (default: {config.HTTP_DELAY_SECONDS})')
    parser.add_argument('--model', type=str, default='OpenAI',
                        help='which model to use (default: OpenAI)')
    parser.add_argument('--prettyprint', action='store_true',
                       help='whether to prettyprint the prompt file')

    args = parser.parse_args()

    # Validate date format
    try:
        datetime.strptime(args.date, '%Y%m%d')
    except ValueError:
        parser.error("Date must be in YYYYMMDD format")

    args.s3_bucket = config.S3_BUCKET

    args.output_root = Path.cwd() / "podcaster" / "output"
    args.output_dir = args.output_root / args.date
    args.output_data_dir = args.output_dir / "data"
    args.output_log_dir = args.output_dir / "logs"
    args.output_data_dir.mkdir(parents=True, exist_ok=True)
    args.output_log_dir.mkdir(parents=True, exist_ok=True)

    return args
