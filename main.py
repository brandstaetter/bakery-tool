import logging
import logging.config
import yaml

from bakery_tool import event_log_reader

if __name__ == '__main__':
    try:
        with open('logging.yaml', 'r') as f:
            log_cfg = yaml.safe_load(f.read())
        logging.config.dictConfig(log_cfg)
        logging.info("Using customized logging defined in logging.yaml")
    except FileNotFoundError:
        logging.basicConfig(filename="bakery.log",
                            format="%(asctime)s - %(name)-10s - %(levelname)-5s - %(message)s",
                            level='INFO')
        logging.info("Using default logging.")

    # noinspection PyBroadException
    # pylint: disable=W0703
    try:
        runner = event_log_reader.event_log_reader()
        runner.run()
        input("Press Enter to stop reporting...")
        runner.stop()
    except Exception:
        logging.exception("Unhandled exception")
