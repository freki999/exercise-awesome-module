from python:3.12-slim-bookworm as AwesomeModule_CIRunner

RUN apt update \
    && apt install g++ ghdl gtkwave git --no-install-recommends -y \
    && pip3 install cocotb cocotbext-axi pytest --no-cache \
    && python3 -m venv venv \
    && . venv/bin/activate

COPY ./open-logic/ /home/open-logic


WORKDIR /home