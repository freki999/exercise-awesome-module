from concurrent.futures import ThreadPoolExecutor
import paho.mqtt.client as mqtt

from fw_proto.shared import IClient


class BackendService(IClient):
    def __init__(
        self,
        broker: str = "mqtt_broker",
        port: int = 1883,
        topic: str = "test/topic",
    ):
        super().__init__(name="Backend", broker=broker, port=port, topic=topic)
        self._received_data = []

    def _on_connect(
        self,
        client,
        userdata,
        flags,
        rc,
        *args,
    ):
        super()._on_connect(client, userdata, flags, rc)
        if rc == 0:
            self.client.on_message = self._on_message
            self.client.subscribe(self._topic)

    def _on_message(self, client, userdata, msg: mqtt.MQTTMessage):
        self.logger.info(f"got message with payload size: {len(msg.payload)}")
        self._queue.put_nowait(msg.payload)

    def _do_run(self):
        consumers = []

        with ThreadPoolExecutor(max_workers=10) as pool:
            while not self._shall_stop.is_set():
                self.logger.info("Listening for data")
                data = self._queue.get()
                consumers.append(pool.submit(self._process_data, data))

    def _process_data(self, data):
        self.logger.info("Got data! ")

        # NOTE:
        # This is where data would be placed into a database or bucket or similar
        # for further processing in a decoupled component (lambda funciton, or dedicated service).

        self._received_data.append(data)
        self.queue.task_done()
