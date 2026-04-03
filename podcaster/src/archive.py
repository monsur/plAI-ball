import os
from pathlib import Path
import boto3
from podcaster.src import args_helper
from podcaster.src import logger_helper

logger = logger_helper.get_logger(__name__)

def run(args):
    s3 = boto3.client('s3',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"))

    output_dir = Path(args.output_dir)
    for filepath in output_dir.rglob("*"):
        if filepath.is_file():
            relative_path = filepath.relative_to(output_dir)
            s3_path = f"archive/{args.date}/{relative_path}"

            logger.info(f"Uploading from {filepath} to {s3_path}...")
            s3.upload_file(str(filepath), args.s3_bucket, s3_path)

if __name__ == "__main__":
    run(args_helper.get_args())
