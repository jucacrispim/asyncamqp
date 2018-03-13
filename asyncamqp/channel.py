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
import io
import logging
import uuid
from aioamqp.channel import Channel as BaseChannel
from aioamqp.channel import amqp_frame, amqp_constants
from aioamqp.envelope import Envelope
from asyncamqp.consumer import Consumer


logger = logging.getLogger(__name__)


class Channel(BaseChannel):

    def __init__(self, *args, max_queue_size=0, **kwargs):
        """Constructor for Channel.

        :param args: Arguments passed to aioamqp.channel.Channel.
        :param max_queue_size: Max size for consumer queue. If 0 the queue
          is infinite.
        :param kwargs: Kwargs passed to aioamqp.channel.Channel."""

        super().__init__(*args, **kwargs)
        self.max_queue_size = max_queue_size

    async def basic_consume(self, queue_name='', consumer_tag='',
                            no_local=False, no_ack=False, exclusive=False,
                            no_wait=False, arguments=None, wait_message=True,
                            timeout=0):
        """Starts the consumption of message into a queue.
        the callback will be called each time we're receiving a message.

            Args:
                queue_name:     str, the queue to receive message from
                consumer_tag:   str, optional consumer tag
                no_local:       bool, if set the server will not send messages
                                to the connection that published them.
                no_ack:         bool, if set the server does not expect
                                acknowledgements for messages
                exclusive:      bool, request exclusive consumer access,
                                meaning only this consumer can access the queue
                no_wait:        bool, if set, the server will not respond to
                                the method
                arguments:      dict, AMQP arguments to be passed to the server
                wait_message:   Indicates if the consumer should wait for new
                                messages in the queue or simply return None if
                                the queue is empty.
                timeout:        A timeout for waiting messages.
                                ``wait_message`` has precendence over timeout.
        """
        # If a consumer tag was not passed, create one
        consumer_tag = consumer_tag or 'ctag%i.%s' % (
            self.channel_id, uuid.uuid4().hex)

        if arguments is None:
            arguments = {}

        frame = amqp_frame.AmqpRequest(
            self.protocol._stream_writer, amqp_constants.TYPE_METHOD,
            self.channel_id)
        frame.declare_method(
            amqp_constants.CLASS_BASIC, amqp_constants.BASIC_CONSUME)
        request = amqp_frame.AmqpEncoder()
        request.write_short(0)
        request.write_shortstr(queue_name)
        request.write_shortstr(consumer_tag)
        request.write_bits(no_local, no_ack, exclusive, no_wait)
        request.write_table(arguments)

        self.consumer_queues[consumer_tag] = asyncio.Queue(self.max_queue_size)
        self.last_consumer_tag = consumer_tag

        consumer = Consumer(self, self.consumer_queues[consumer_tag],
                            consumer_tag, nowait=not wait_message,
                            timeout=timeout)

        await self._write_frame_awaiting_response(
            'basic_consume', frame, request, no_wait)

        if not no_wait:
            self._ctag_events[consumer_tag].set()

        return consumer

    async def basic_deliver(self, frame):
        response = amqp_frame.AmqpDecoder(frame.payload)
        consumer_tag = response.read_shortstr()
        delivery_tag = response.read_long_long()
        is_redeliver = response.read_bit()
        exchange_name = response.read_shortstr()
        routing_key = response.read_shortstr()
        content_header_frame = await self.protocol.get_frame()

        buffer = io.BytesIO()
        while(buffer.tell() < content_header_frame.body_size):
            content_body_frame = await self.protocol.get_frame()
            buffer.write(content_body_frame.payload)

        body = buffer.getvalue()
        envelope = Envelope(consumer_tag, delivery_tag,
                            exchange_name, routing_key, is_redeliver)
        properties = content_header_frame.properties

        consumer_queue = self.consumer_queues[consumer_tag]

        event = self._ctag_events.get(consumer_tag)
        if event:
            await event.wait()
            del self._ctag_events[consumer_tag]

        if consumer_queue.full():
            # if the queue is full we reject and requeue the message.
            await self.basic_reject(delivery_tag, requeue=True)
            logger.warning('Rejecting message for {}'.format(consumer_tag))
        else:
            await consumer_queue.put((self, body, envelope, properties))
