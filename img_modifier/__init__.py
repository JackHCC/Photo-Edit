from logging.config import fileConfig

# init logger from config file
fileConfig('logging_config.ini')

__all__ = ["color_filter", "img_modifier"]

