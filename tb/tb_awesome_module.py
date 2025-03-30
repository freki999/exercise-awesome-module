from time import sleep
import cocotb
from fw_proto.awesomemodule import AwesomeTB
from fw_proto.client import Client
from fw_proto.backend import BackendService


# The Open Logic PRBS implementation seems to be broken, but okay. good enough for this test...
def calc_prbs(state):
    prbs_word = 0
    for i in range(32):
        next_bit = ((state >> 31) & 1) ^ ((state >> 28) & 1)
        prbs_word = ((prbs_word >> 1) | (next_bit << 31)) & (2**32 - 1)
        state = ((state << 1) | next_bit) & (2**32 - 1)

    return prbs_word, state


def flip32(v):
    flipped = 0
    for i in range(32):
        flipped = (flipped << 1) | ((v >> i) & 1)
    return flipped


def check_prbs(data, state):
    if state is None:
        state = flip32(int.from_bytes(data[0:4], "little"))
        assert state != 0, "State is 0!"
        data = data[4:]

    for i in range(0, len(data), 4):
        prbs_actual = int.from_bytes(data[i : i + 4], "little")
        prbs_expected, state = calc_prbs(state)

        assert prbs_actual == prbs_expected, (
            f"Data mismatch @ {i}: Got {prbs_actual:x} ({prbs_actual:b}), expected {prbs_expected:x} ({prbs_expected:b})"
        )

    return state


ADDR = 0x10000
SIZE = 0x10
N = 10


@cocotb.test()
async def test_awesome_module(dut):

    tb = AwesomeTB(dut)
    await tb.init()
    await tb.enable_interrupts()

    prbs_state = None

    for cur_addr in range(ADDR, ADDR + N * SIZE, SIZE):
        await tb.start_transfer(cur_addr, SIZE)
        await tb.wait_transfer_done()

        data = tb.mem.read(cur_addr, SIZE)
        prbs_state = check_prbs(data, prbs_state)


@cocotb.test()
async def test_awesome_client(dut):
    client = Client()
    backend = BackendService()

    client.start()  # NOTE: prototypic client (firmware) side
    backend.start()  # NOTE: prototypic backend (cloud) side

    tb = AwesomeTB(dut)
    await tb.init()
    await tb.enable_interrupts()

    sent_sequence = []
    await client.send_task(tb, ADDR, SIZE, sent_sequence, N)

    client.queue.join()
    backend.queue.join()

    sleep(2)  # some processing time due to networking

    # NOTE: Add assertions on client sending here
    assert len(sent_sequence) == N

    # NOTE: Add assertions on backend reception here
    assert backend._received_data == sent_sequence

    # NOTE: Check that signal has been received correctly at backend
    prbs_state = None
    for data in sent_sequence:
        prbs_state = check_prbs(data, prbs_state)
