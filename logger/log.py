import datetime
import logging
import os
import sys

# Define the log directory and file name
log_dir = "logs"
log_file = f"validation-{datetime.datetime.now()}.log"
log_file_path =os.path.join(log_dir, log_file)

# Create the log directory if it doesn't exist
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler(stream=sys.stdout)
    ]
)

# Create a logger object
logger = logging.getLogger(__name__)