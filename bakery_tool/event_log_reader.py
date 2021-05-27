import ast
import json
import os
import fnmatch
import logging
import threading
import time
from logging import Logger
import tailer

from bakery_tool.discord_wrapper import discord_wrapper


def translate(source: str):
    result = source.lstrip('$')
    result = result.split('_')[0]
    return result.capitalize()


class event_log_reader:
    log: Logger
    folder_location: str
    running: bool

    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.folder_location = os.environ['USERPROFILE'] + \
                               '\\Saved Games\\Frontier Developments\\Elite Dangerous'
        self.running = False
        self.log_thread = None
        self.discord_thread = None
        self.discord = discord_wrapper()

    def run(self):
        if self.discord_thread is not None:
            raise Exception("Thread already running!")
        if self.log_thread is not None:
            raise Exception("Thread already running!")
        self.running = True
        self.log_thread = threading.Thread(target=self.update_log, daemon=True)
        self.discord_thread = threading.Thread(target=self.discord.connect, daemon=True)
        if not self.discord_thread.is_alive():
            self.log.info("Starting discord process")
            self.discord_thread.start()
        if not self.log_thread.is_alive():
            self.log.info("Starting journal log reading process")
            self.log_thread.start()

    def stop(self):
        self.running = False
        if self.log_thread is not None:
            self.log.info("Stopping log reading process")
            self.log_thread.join()
            self.log_thread = None
            self.log.info("Stopped log process successfully")

    def update_log(self):
        self.log.info("Started successfully")
        while self.running:
            directory = fnmatch.filter(os.listdir(self.folder_location), "Journal.*.log")
            directory.reverse()
            target_log_file = self.folder_location + "\\" + directory[0]
            self.log.debug("Following %s", target_log_file)
            result = self.follow_log(target_log_file)

            if result is not None and result["event"] == "Shutdown":
                time.sleep(10)

    def follow_log(self, filename):
        self.log.debug("Opening %s", filename)
        with open(filename) as file_handle:
            self.log.debug("Opened successfully")
            lines = tailer.tail(file_handle, 3)
            for line in reversed(lines):
                if line != '':
                    self.log.debug("Last Line: %s", line)
                    if self.process_line(line)["event"] == "Shutdown":
                        return {"event": "Shutdown"}
            for line in tailer.follow(file_handle):
                self.log.debug("Processing line: %s", line)
                result = self.process_line(line)
                if result["event"] == "MarketUpdate":
                    self.log.info("Received a Market Update: %s", str(result))
                    items: dict = ast.literal_eval(result["Items"])
                    self.log.debug("Evaluated as %s", str(items))
                    for key, value in items.items():
                        self.discord.send_update(result["StationName"], key, value)
                if not self.running:
                    break
                return result
        return {"event": "Stopped"}

    def process_line(self, line):
        try:
            data = json.loads(line)
        except json.decoder.JSONDecodeError:
            return {"event": "DecodeError"}
        self.log.debug("Event: %s", data["event"])

        if data["event"] == "Shutdown":
            self.log.info("Elite Dangerous shutdown detected. Waiting for a newer log file.")
            return {"event": "Shutdown"}
        if data["event"] == "Market":
            self.log.info("Opened market in system %s, station %s",
                          data["StarSystem"], data["StationName"])
            with open(self.folder_location + "\\Market.json") as market_file:
                market_data = json.load(market_file)
                if market_data["MarketID"] != data["MarketID"]:
                    self.log.error("Market data mismatch!")
                    return {"event": "Error"}

                items = {}
                for item in market_data["Items"]:
                    item_name = translate(item["Name"])
                    item_stock = item["Stock"]
                    self.log.info("Found item %s with stock %d", item_name, item_stock)
                    items[item_name] = item_stock
                return {"event": "MarketUpdate", "Items": str(items),
                        "StarSystem": data["StarSystem"],
                        "StationName": data["StationName"]}

        return {"event": "Other"}
