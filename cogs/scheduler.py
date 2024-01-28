import asyncio
import logging
import time
import typing
from asyncio import Task

import aiohttp
import discord

from bs4 import BeautifulSoup
from tortoise.expressions import F

from persistence import EventStates
from persistence.models import Event, MessageDeleteQueue, EventRegister
from utils.overwrites import ExtCog

from bot import Neria
from utils.utils import TimingContext

logger = logging.getLogger("Neria")


class ScheduleManager(ExtCog):

    def __init__(self, bot: "Neria"):
        self.bot = bot
        self.scheduler = Scheduler()
        self.server_status_url = ""
        self.server_status_dict: dict[str, list] = None
        self.scheduler.register("notification_dispatcher", self.notification_dispatcher, dispatch_every=60, max_time=3)
        self.scheduler.register("server_status_scraper", self.scrape_for_server_status, dispatch_every=600, max_time=30)
        self.scheduler.register("mapping_cleanup", self.mapping_cleanup, dispatch_every=10)
        self.scheduler.register("msg_delete_dispatcher", self.msg_delete_dispatcher, dispatch_every=60)
        self.scheduler.register("event_dispatcher", self.event_dispatcher, dispatch_every=60, max_time=5)
        self.scheduler.start()

    def get_lang(self, lang: str):
        pass

    async def mapping_cleanup(self):
        copy = self.bot.interaction_income_mapping.copy()
        for k, v in copy.items():
            if time.time() - v > 11:
                self.bot.interaction_income_mapping.pop(k)

    async def msg_delete_dispatcher(self):
        await self.bot.wait_until_ready()
        msg_entries = await MessageDeleteQueue.filter(delete_at__lte=time.time())
        logger.debug(f"Queried {len(msg_entries)} items to delete.")
        for saved_msg in msg_entries:
            async def delete_msg(passed_msg):
                msg_id = passed_msg.id
                channel = self.bot.get_channel(passed_msg.channel_id)
                try:
                    m = await channel.fetch_message(msg_id)
                    await m.delete()
                except discord.HTTPException:
                    pass
                finally:
                    await passed_msg.delete()

            self.bot.loop.create_task(delete_msg(saved_msg))

    async def notification_dispatcher(self):
        await self.bot.wait_until_ready()
        with TimingContext("notification_db_access"):
            lfgs: list[EventRegister] = await EventRegister.filter(
                event__event_start__lte=time.time() + F("notify_before"),
                event__state=EventStates.PLANING,
                notified=False
            )
        logger.debug(f"Notify dispatcher queried {len(lfgs)} items")
        if len(lfgs) > 0:
            logger.info(f"Notify dispatcher queried {len(lfgs)} items")
        for to_dispatch in lfgs:
            async def dispatch(e: EventRegister):
                try:
                    await self.bot.event_manager.notify_start_user(e)
                finally:
                    e.notified = True
                    await e.save()
                    pass

            # to_dispatch.last_dispatch = int(time.time())
            # await to_dispatch.save()
            asyncio.create_task(dispatch(to_dispatch))

    async def event_dispatcher(self):
        await self.bot.wait_until_ready()
        lfgs: list[Event] = await Event.filter(event_start__lte=time.time(),
                                               state=EventStates.PLANING)
        logger.debug(f"Event dispatcher queried {len(lfgs)} items")
        if len(lfgs) > 0:
            logger.info(f"Event dispatcher queried {len(lfgs)} items")
        for to_dispatch in lfgs:
            async def dispatch(e: Event):
                with TimingContext("dispatch_event", max_time=2):
                    try:
                        await self.bot.event_manager.on_event_start(e)
                    finally:
                        pass

            to_dispatch.state = EventStates.ENDED
            await to_dispatch.save()
            asyncio.create_task(dispatch(to_dispatch))

    async def scrape_for_server_status(self):
        try:
            async with aiohttp.ClientSession() as session:
                server_response = await session.get(url="https://www.playlostark.com/de-de/support/server-status")
                raw_html = await server_response.content.read()
        except Exception:
            #  Swallow in case of error
            return

        soup = BeautifulSoup(raw_html, "lxml")
        buttons = soup.find("div", {"class": "ags-ServerStatus-content-tabs"})
        button_names = []
        for i in buttons.find_all("a"):
            button_names.append(i.findNext().getText().strip())

        server_response_container = soup.find("div", {"class": "ags-ServerStatus-content-responses"})
        responses = server_response_container.find_all("div", {"class": "ags-ServerStatus-content-responses-response"})
        counter = 0
        ret = {}
        for i in responses:
            for server in i.find_all("div", {"class": "ags-ServerStatus-content-responses-response-server"}):
                d = {}
                x = server.findNext()
                status_element = x.findNext()
                status_element_classes = status_element["class"]
                if "good" in status_element_classes[1]:
                    d["status"] = "good"
                elif "busy" in status_element_classes[1]:
                    d["status"] = "busy"
                elif "full" in status_element_classes[1]:
                    d["status"] = "full"
                else:
                    d["status"] = "maintenance"
                d["name"] = server.find_all_next("div")[2].getText().replace("\n", "").strip()

                server_list = ret.get(button_names[counter], None)
                if server_list is None:
                    server_list = []
                    ret[button_names[counter]] = server_list
                server_list.append(d)
            counter += 1
        self.server_status_dict = ret


class Scheduler:
    class ScheduledTask:
        def __init__(self, name, coro, dispatch_every, init_delay=0, ensure_completed=True, max_time=1):
            self.name = name
            self.is_canceled = False
            self.dispatch_every = dispatch_every
            self.coro = coro
            self.last_task: typing.Union[asyncio.Task, None] = None
            self.util_dispatch = init_delay
            self.ensure_completed = ensure_completed
            self.max_time = max_time

        @property
        def can_run(self):
            return self.util_dispatch <= 0

        @property
        def is_finished(self):
            if self.last_task is None:
                return True
            return self.last_task.done()

        def subtract(self, amount):
            self.util_dispatch -= amount

        def dispatch(self):
            logger.debug(f"Dispatching task '{self.name}'")
            self.util_dispatch = self.dispatch_every
            start = time.perf_counter()
            self.last_task = asyncio.create_task(self.coro())

            def callback(t: Task):
                if t.exception():
                    logger.error(f"Exception in {self.name}", exc_info=t.exception())
                total_time = round(time.perf_counter() - start, 3)
                logger.debug(f"Execution of '{self.name}' took {total_time} seconds")
                if total_time > self.max_time:
                    logger.warning(f"Execution of task '{self.name}' took to long. ({total_time})")

            self.last_task.add_done_callback(callback)

    def __init__(self):
        self.schedules: list[Scheduler.ScheduledTask] = []
        self.task: asyncio.Task = None
        self.delay = 5

    def register(self, name, coro, dispatch_every, init_delay=0, ensure_completed=True, max_time=1):
        logger.info(f"Registered scheduled task '{name}' queued every {dispatch_every}")
        scheduled = Scheduler.ScheduledTask(name, coro, dispatch_every, init_delay, ensure_completed, max_time)
        self.schedules.append(scheduled)

    def get(self, name):
        for i in self.schedules:
            if i.name == name:
                return i
        else:
            raise KeyError

    async def __start_scheduling(self):
        logger.info("Started main scheduler task")
        while True:
            await asyncio.sleep(self.delay)
            for i in self.schedules:
                i.subtract(self.delay)
                if i.can_run:
                    if i.ensure_completed and not i.is_finished:
                        continue
                    i.dispatch()

    def start(self):
        loop = asyncio.get_event_loop_policy().get_event_loop()
        self.task = loop.create_task(self.__start_scheduling())

    def shutdown(self):
        self.task.cancel()
        currently_running = []
        for i in self.schedules:
            if not i.is_finished:
                currently_running.append(i.last_task)
        for to_kill in currently_running:
            to_kill.cancel()


async def setup(bot: Neria):
    await bot.add_cog(ScheduleManager(bot))
