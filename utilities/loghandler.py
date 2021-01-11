import logging
import time
import sys

logfilename = 'log-' + time.strftime('%Y-%m-%d') + '.log'
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S', handlers=[logging.FileHandler(logfilename)])