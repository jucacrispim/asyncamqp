# -*- coding: utf-8 -*-

# Copyright 2018 Juca Crispim <juca@poraodojuca.net>

# This file is part of asyncamqp.

# asyncamqp is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# asyncamqp is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with asyncamqp. If not, see <http://www.gnu.org/licenses/>.

import asyncio
from asyncamqp.compat import aiter_compat
from asyncamqp.exceptions import ConsumerTimeout


class Message:
    """Simple class to encapsulate a response - and it's info from the server.
    """

    def __init__(self, channel, body, envelope, properties):
        """Constructor for Message.

        :param channel: Instance of :class:`~asyncamqp.channel.Channel`.
        :param body: Payload of the message.
        :param envelope: An aioamqp Envelope.
        :param properties: Properties of the message."""

        self.channel = channel
        self.body = body
        self.envelope = envelope
        self.properties = properties


class Consumer:
    """Class responsible for consuming messages from a queue in the
    broker."""

    MESSAGE_CLASS = Message

    def __init__(self, channel, queue, consumer_tag, nowait=False,
                 timeout=0):
        """Constructor for Consumer.
        :param channel: Instance of :class:`~asyncamqp.channel.Channel`.
        :param queue: An asyncio queue that receives messages from the broker.
        :param consumer_tag: The tag id for the consumer.
        :param nowait: Indicates if the consumer should wait for messages
          to arrive or simply consume the messages already on the broker.
        :param timeout: Timeout in milliseconds to get a message. If 0 no
          timeout is used.

        .. note::

            ``timeout`` and ``nowait`` can't be used at the sametime.
            ``nowait`` has precedend over ``timeout``

        The inteded way of using this is:

        .. code-block:: python

            async with Consumer(channel, queue, consumer_tag) as consumer:
                async for message in consumer:
                    # do your stuff with the message.
        """

        self.channel = channel
        self.queue = queue
        self.tag = consumer_tag
        self.message = None
        self.nowait = nowait
        self.timeout = timeout
        self._canceled = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc, exc_type, exc_tb):
        await self.cancel()

    @aiter_compat
    def __aiter__(self):
        return self

    async def __anext__(self):
        n = await self.fetch_message()
        if n is None or self._canceled:
            raise StopAsyncIteration
        return n

    async def cancel(self):
        if not self._canceled:  # pragma no branch
            await self.channel.basic_cancel(self.tag)
            self._canceled = True

    async def fetch_message(self):
        if self.nowait and self.queue.empty():
            await self.cancel()
            return None

        elif self.timeout and self.queue.empty():
            t = 0
            while t <= self.timeout:
                await asyncio.sleep(0.001)
                if not self.queue.empty():
                    break
                t += 1
            else:
                await self.cancel()
                raise ConsumerTimeout('Could not get a message in {} ms'.format(
                    self.timeout))

        msg = await self.queue.get()

        self.message = self.MESSAGE_CLASS(*msg)
        return self.message
