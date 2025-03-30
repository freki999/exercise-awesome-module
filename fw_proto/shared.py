from abc import ABC, abstractmethod
import logging
from queue import Queue
import threading
import paho.mqtt.client as mqtt


class IClient(ABC):
    def __init__(
        self,
        name: str = "",
        broker: str = "localhost",
        port: int = 1883,
        topic: str = "test/topic",
    ):
        self._broker = broker
        self._port = port
        self._topic = topic

        self._thread: threading.Thread = None
        self._queue = Queue()
        self._logger = logging.getLogger(name or type(self).__name__)
        self._logger.setLevel(logging.DEBUG)

        # Set up callbacks
        self._client: mqtt.Client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, name)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

        # NOTE: Here we would have to add the TLS and CA chain checking.

        self._shall_stop = threading.Event()

    @property
    def client(self):
        return self._client

    @property
    def logger(self):
        return self._logger

    @property
    def queue(self):
        return self._queue

    def _on_connect(self, client, userdata, flags, rc, *args):
        if rc == 0:
            self.logger.info(f"Connected to MQTT broker at {self._broker}:{self._port}")
        else:
            self.logger.info(f"Failed to connect, return code {rc}")

    def _on_disconnect(
        self,
        client,
        userdata,
        rc,
        *args,
    ):
        self.logger.info("Disconnected from MQTT broker")

    def start(
        self,
    ):
        if not self._thread:
            pass

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        if self._thread and self._thread.is_alive():
            self._shall_stop.set()
            self._thread.join()
            self._thread = None

    def _run(self):
        """Continuously publishes messages to the topic."""
        self.logger.info(f"Connecting to {self._broker}:{self._port}!")
        self.client.connect(self._broker, self._port, 60)
        self.client.loop_start()

        try:
            self._do_run()
        except Exception as ex:
            self.logger.info(ex)
        finally:
            self.client.loop_stop()
            self.client.disconnect()

    @abstractmethod
    def _do_run(self):
        pass
