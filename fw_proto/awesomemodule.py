import logging
import cocotb
from cocotb.triggers import Timer
from cocotb.clock import Clock
from cocotbext.axi import (
    AxiWriteBus,
    AxiLiteBus,
    AxiLiteMaster,
    AxiRamWrite,
)
from cocotbext.axi.sparse_memory import SparseMemory
from cocotb.triggers import Event, RisingEdge


class AwesomeTB:
    CLOCK_PERIOD_NS = 10

    REG_IS = 0x00
    REG_IE = 0x04
    REG_GIE = 0x08
    REG_CTRL = 0x0C
    REG_ADDR_L = 0x10
    REG_ADDR_H = 0x14
    REG_SIZE = 0x18

    IRQ_DONE = 1
    IRQ_ERROR = 2

    CTRL_START = 1

    def __init__(self, dut):
        self.logger = logging.getLogger(__name__)

        self.dut = dut
        self.axi_ctrl = AxiLiteMaster(
            AxiLiteBus.from_prefix(dut, "s_axi_ctrl"),
            dut.clk,
            dut.rst,
        )
        self.memory_size = 2**24
        self.mem = AxiRamWrite(
            AxiWriteBus.from_prefix(dut, "m_axi_data"),
            dut.clk,
            dut.rst,
            mem=SparseMemory(self.memory_size),
        )
        self.transfer_done = Event()

    async def init(self):
        self.dut.rst.value = 1
        cocotb.start_soon(Clock(self.dut.clk, self.CLOCK_PERIOD_NS, units="ns").start())
        cocotb.start_soon(self.irq_handler())
        await Timer(100, units="ns")
        self.dut.rst.value = 0

    async def enable_interrupts(self):
        self.logger.info("Enabling interrupts")
        await self.axi_ctrl.write_dword(self.REG_IE, self.IRQ_DONE | self.IRQ_ERROR)
        await self.axi_ctrl.write_dword(self.REG_GIE, 1)

    async def start_transfer(self, address, size):
        self.logger.info(f"Starting transfer of {size:x} bytes to {address:x}")
        await self.axi_ctrl.write_qword(self.REG_ADDR_L, address)
        await self.axi_ctrl.write_dword(self.REG_SIZE, size)
        await self.axi_ctrl.write_dword(self.REG_CTRL, self.CTRL_START)

    async def wait_transfer_done(self):
        while not self.transfer_done.is_set():
            await self.transfer_done.wait()
        self.transfer_done.clear()

    async def irq_handler(self):
        while True:
            await RisingEdge(self.dut.irq)
            irq_status = await self.axi_ctrl.read_dword(self.REG_IS)

            if irq_status & self.IRQ_DONE:
                self.logger.info("Got DONE interrupt")
                self.transfer_done.set()

            if irq_status & self.IRQ_ERROR:
                self.logger.error("Got ERROR interrupt")

            await self.axi_ctrl.write_dword(self.REG_IS, irq_status)
