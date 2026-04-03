import logging
import os
import shutil
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def getenv(envvar):
    return os.getenv(envvar)

def join(*args):
    return os.path.join(*args)

def read_file(*args):
    try:
        with open(join(*args), 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error("File not found: %s", e)
        return None

def write_file(content, *args):
    with open(join(*args), 'w', encoding='utf-8') as f:
        f.write(content)

def make_dir(path, clean=False):
    os.makedirs(path, exist_ok=True)
    if clean:
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            except Exception as e:
                logger.error("Error deleting %s: %s", item_path, e)
