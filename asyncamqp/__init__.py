# -*- coding: utf-8 -*-

from aioamqp import connect  # noqa f402 for the API
from aioamqp.protocol import AmqpProtocol
from asyncamqp.channel import Channel

AmqpProtocol.CHANNEL_FACTORY = Channel

VERSION = '0.1.1'
