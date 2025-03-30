import paho.mqtt.client as mqtt

from fw_proto.shared import IClient
from fw_proto.awesomemodule import AwesomeTB


class Client(IClient):
    def __init__(
        self,
        broker: str = "mqtt_broker",
        port: int = 1883,
        topic: str = "test/topic",
    ):
        super().__init__(
            name="Client",
            broker=broker,
            port=port,
            topic=topic,
        )

    def _do_run(self):
        """Continuously publishes messages to the topic."""

        while not self._shall_stop.is_set():
            self.logger.info("Waiting for data")
            data = self._queue.get()
            result = self.client.publish(self._topic, data)
            self.queue.task_done()
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.info(f"Published: -> {self._topic}")
            else:
                self.logger.info("Failed to publish message")

    async def send_task(
        self,
        tb: AwesomeTB,
        addr: int,
        size: int,
        sent_sequence: list,
        max_chunks=25,
    ):
        # NOTE:
        # This task reads from the DMA mapped buffer and placed the data in the send Q of the client

        if tb.memory_size % size != 0:
            raise RuntimeError("size is not aligned with memory size")

        current_addr = addr
        at = 0

        while True and at < max_chunks:
            await tb.start_transfer(current_addr, size)
            await tb.wait_transfer_done()

            data = tb.mem.read(current_addr, size)
            self.queue.put_nowait(data)

            current_addr += size

            at += 1
            sent_sequence.append(data)
