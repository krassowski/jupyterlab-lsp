""" Language Server stdio-mode readers

Parts of this code are derived from:

> https://github.com/palantir/python-jsonrpc-server/blob/0.2.0/pyls_jsonrpc/streams.py#L83   # noqa
> https://github.com/palantir/python-jsonrpc-server/blob/45ed1931e4b2e5100cc61b3992c16d6f68af2e80/pyls_jsonrpc/streams.py  # noqa
> > MIT License   https://github.com/palantir/python-jsonrpc-server/blob/0.2.0/LICENSE
> > Copyright 2018 Palantir Technologies, Inc.
"""
# pylint: disable=broad-except

import asyncio
import io
from typing import Optional

from tornado.httputil import HTTPHeaders
from tornado.queues import Queue
from traitlets import Float, Instance
from traitlets.config import LoggingConfigurable

from .non_blocking import make_non_blocking


class StdIOBase(LoggingConfigurable):
    """ Non-blocking, queued base for communicating with stdio Language Servers
    """

    stream = Instance(io.BufferedIOBase, help="the stream to read/write")
    queue = Instance(Queue, help="queue to get/put")


class Reader(StdIOBase):
    """ Language Server stdio Reader

        Because non-blocking (but still synchronous) IO is used, rudimentary
        exponential backoff is used.
    """

    max_wait = Float(2.0, help="maximum time to wait on idle stream").tag(config=True)
    min_wait = Float(0.05, help="minimum time to wait on idle stream").tag(config=True)
    next_wait = Float(0.05, help="next time to wait on idle stream").tag(config=True)

    async def sleep(self):
        """ Simple exponential backoff for sleeping
        """
        self.next_wait = min(self.next_wait * 2, self.max_wait)
        await asyncio.sleep(self.next_wait)

    def wake(self):
        """ Reset the wait time
        """
        self.wait = self.min_wait

    async def read(self) -> None:
        """ Read from a Language Server until it is closed
        """
        make_non_blocking(self.stream)

        while not self.stream.closed:
            message = None
            try:
                message = self.read_one()

                if message is None:
                    await self.sleep()
                    continue
                else:
                    self.wake()

                await self.queue.put(message)
            except Exception:
                self.log.exception("[R] failed to read %s", message)
                await self.sleep()

    def read_one(self) -> Optional[bytes]:
        """ Read a single message
        """
        headers = HTTPHeaders()

        line = self._readline().decode("utf-8").strip()

        if not line:
            return

        headers.parse_line(line)

        while line and line.strip():
            line = self._readline().decode("utf-8").strip()
            if line:
                headers.parse_line(line)

        content_length = int(headers.get("content-length", "0"))

        if content_length:
            message = self.stream.read(content_length).decode("utf-8")
            return message

    def _readline(self) -> bytes:
        """ Read a line (or immediately return None)
        """
        try:
            return self.stream.readline()
        except OSError:  # pragma: no cover
            return b""


class Writer(StdIOBase):
    """ Language Server stdio Writer
    """

    async def write(self):
        """ Write to a Language Server until it closes
        """
        while not self.stream.closed:
            message = await self.queue.get()
            try:
                body = message.encode("utf-8")
                response = "Content-Length: {}\r\n\r\n{}".format(len(body), message)
                self.stream.write(response.encode("utf-8"))
                self.stream.flush()
            except Exception:
                self.log.exception("[W] Couldn't write message: %s", response)
            finally:
                self.queue.task_done()
