#!/bin/env python3

from enum import IntEnum

class modbus_exception(IntEnum):
    ILLEGAL_FUNCTION = 0x1
    ILLEGAL_DATA_ADDRESS = 0x2
    ILLEGAL_DATA_VALUE = 0x3
