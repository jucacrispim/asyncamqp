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
from unittest import TestCase
from unittest.mock import Mock, MagicMock, patch
from asyncamqp import connect
from asyncamqp.consumer import Consumer
from asyncamqp.exceptions import ConsumerTimeout


def async_test(f):

    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        coro = asyncio.coroutine(f)
        loop.run_until_complete(coro(*args, **kwargs))

    return wrapper


class AsyncMagicMock(MagicMock):

    def __call__(self, *a, **kw):
        s = super().__call__(*a, **kw)

        async def ret():
            return s

        return ret()

    def __bool__(self):
        return True


class ConsumerTest(TestCase):

    @async_test
    async def test_consume_messages(self):
        queue = asyncio.Queue()
        channel, body, envelope, properties = Mock(), 'body', Mock(), {}
        await queue.put((channel, body, envelope, properties))
        consumer = Consumer(channel, queue, 'consumer-tag')
        message = await consumer.fetch_message()
        self.assertEqual(message.body, 'body')

    @async_test
    async def test_consume_messages_no_wait(self):
        queue = asyncio.Queue()
        channel = AsyncMagicMock()
        body, envelope, properties = 'body', Mock(), {}
        await queue.put((channel, body, envelope, properties))
        await queue.put((channel, body, envelope, properties))
        consumer = Consumer(channel, queue, 'consumer-tag', nowait=True)
        total_messages = 0

        async for _ in consumer:  # noqa f841
            total_messages += 1

        self.assertEqual(total_messages, 2)


class TestChannel(TestCase):

    @classmethod
    @async_test
    async def setUpClass(cls):
        cls.transport, cls.protocol = await connect()

    @classmethod
    @async_test
    async def tearDownClass(cls):
        await cls.protocol.close()
        cls.transport.close()

    @async_test
    async def test_basic_consume_messages(self):
        channel = await self.protocol.channel()
        await channel.queue_declare(queue_name='test-queue')
        await channel.basic_publish(payload='my-test'.encode(),
                                    exchange_name='',
                                    routing_key='test-queue')

        total = 0
        async with await channel.basic_consume(
                queue_name='test-queue', no_ack=True,
                arguments={}) as consumer:
            async for msg in consumer:
                self.assertEqual(msg.body, b'my-test')
                total += 1
                break  # noqa F999

        self.assertEqual(total, 1)
        await channel.basic_cancel(consumer.tag)

    @patch('asyncamqp.channel.logger')
    @async_test
    async def test_consumer_queue_full(self, *args, **kwargs):

        channel = await self.protocol.channel(max_queue_size=1)
        channel.basic_reject = AsyncMagicMock(spec=channel.basic_reject)
        await channel.queue_declare(queue_name='test-queue')
        await channel.basic_publish(payload='my-test'.encode(),
                                    exchange_name='',
                                    routing_key='test-queue')

        async with await channel.basic_consume(
                queue_name='test-queue', no_ack=True, no_wait=True) as cons:
            async for msg in cons:
                self.assertEqual(msg.body, b'my-test')
                await channel.basic_publish(
                    payload='my-test'.encode(), exchange_name='',
                    routing_key='test-queue')
                await channel.basic_publish(
                    payload='my-test'.encode(), exchange_name='',
                    routing_key='test-queue')

                await asyncio.sleep(0.1)
                self.assertTrue(channel.basic_reject.called)

                break  # noqa F999

    @async_test
    async def test_fetch_message_timeout(self):
        channel = await self.protocol.channel()

        async with await channel.basic_consume(
                queue_name='test-queue', no_ack=True,
                timeout=100) as consumer:
            with self.assertRaises(ConsumerTimeout):
                async for msg in consumer:  # noqa: F841
                    pass

    @async_test
    async def test_fetch_message_timeout_dont_raise(self):
        channel = await self.protocol.channel()

        await channel.queue_declare(queue_name='test-queue')
        await channel.basic_publish(payload='my-test'.encode(),
                                    exchange_name='',
                                    routing_key='test-queue')
        mchannel, body, envelope, properties = Mock(), 'body', Mock(), {}

        async with await channel.basic_consume(
                queue_name='test-queue', no_ack=True,
                timeout=100) as consumer:
            consumer.queue.empty = Mock(side_effect=[True, True, True, False])
            consumer.queue.get = AsyncMagicMock(side_effect=[(mchannel, body,
                                                              envelope,
                                                              properties)])
            total = 0
            async for msg in consumer:
                del msg
                total += 1
                break  # noqa F999

            self.assertEqual(total, 1)
