import logging
import discord
import yaml

from discord import TextChannel
from discord.ext import tasks


class BakerClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.log = logging.getLogger(__name__)

        self.message_pile = {}
        #pylint: disable=E1101
        self.messaging_task.start()

    async def on_ready(self):
        for channel in self.get_all_channels():
            self.log.debug("Found channel %s - %s of type %s", channel.guild.name,
                           channel.name, channel.type)

    @tasks.loop(seconds=60)  # task runs every 60 seconds
    async def messaging_task(self):
        self.log.debug("Running message task")
        self.log.debug("Message Pile height = %d", len(self.message_pile.keys()))
        for key, value in self.message_pile.items():
            self.log.debug("Looking for channel '%s'", key)
            for channel in self.get_all_channels():
                if isinstance(channel, TextChannel) and key == channel.name:
                    async for message in channel.history():
                        if message.author == self.user:
                            await message.delete()
                    self.log.debug("Found channel, sending %s", value)
                    for entry in value:
                        await channel.send(entry)
        self.log.debug("Cleaning message pile")
        self.message_pile.clear()

    @messaging_task.before_loop
    async def before_messaging_task(self):
        await self.wait_until_ready()  # wait until the bot logs in


class discord_wrapper:

    def __init__(self):
        self.log = logging.getLogger(__name__)
        try:
            with open('config.yaml', 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f.read())
        except FileNotFoundError as e:
            self.log.exception("Please configure the discord connection in config.yaml")
            raise e

        self.client = BakerClient()

    def connect(self):
        try:
            self.client.run(self.config["discord"]["client_token"])
        except KeyError as e:
            self.log.exception("Please configure the discord connection token in config.yaml")
            raise e

    def send_update(self, station_name: str, commodity: str, stock: int):
        try:
            cmdr_name = self.config["elite"]["cmdr_name"]
        except KeyError as e:
            self.log.exception("Please configure the CMDR name in config.yaml")
            raise e
        try:
            channel_mapping = self.config["discord"]["channel_mapping"]
        except KeyError as e:
            self.log.exception("Please configure the discord channel mapping in config.yaml")
            raise e
        if station_name in channel_mapping.keys():
            if channel_mapping[station_name] not in self.client.message_pile.keys():
                self.client.message_pile[channel_mapping[station_name]] = []
            message = commodity + ": " + str(stock) + " (reported by CMDR " + cmdr_name + ")"
            self.client.message_pile[channel_mapping[station_name]].append(message)
            self.log.debug("Enqueued message %s for target channel %s",
                           message, channel_mapping[station_name])
        else:
            self.log.info("Ignoring %s - no channel mapping found!", station_name)
