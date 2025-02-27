from parrot.bot import Parrot
from parrot.config import logger


def main() -> None:
	logger.info("Initializing bot...")
	bot = Parrot()
	bot.go()


if __name__ == "__main__":
	main()
