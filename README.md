# MODBUS Server

This is a MODBUS TCP server simulator.

## Execute

Make sure the Python is version 3.7 or newer.

```sh
./server.py
```

The default listening port is **5020**.

## Impelemented Functions

1. Read Coils
2. Read Discrete Inputs
3. Read Holding Registers
4. Read Input Registers
5. Write Single Coil
6. Write Single Register
7. Write Multiple Coils
8. Write Multiple registers

* Server will response **ILLEGAL FUNCTION** exception if the request function code is not listed above.
* Server will response **ILLEGAL DATA ADDRESS** exception if the request address is invalid.
* Server will response **ILLEGAL DATA VALUE** exception if the request data value is invalid.
* Server will response random values if the reading request format is correct.
* Server will accept all of the written values if the writing request format is correct.

## Reference:

* [MODBUS Application Protocol Specification V1.1b3](http://www.modbus.org/docs/Modbus_Application_Protocol_V1_1b3.pdf)
* [MODBUS Messaging on TCP/IP Implementation Guide V1.0b](http://www.modbus.org/docs/Modbus_Messaging_Implementation_Guide_V1_0b.pdf)
* [MODBUS/TCP Security Protocol Specification](http://modbus.org/docs/MB-TCP-Security-v21_2018-07-24.pdf)
