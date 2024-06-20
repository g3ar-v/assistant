from configuration.config import Configuration
from core.util.log import LOG
from pyee import EventEmitter

event = EventEmitter()

LOG.init()
LOG.info("I'm being used a lot")
