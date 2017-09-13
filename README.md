# indigo-json-broadcaster

Broadcast device and variable changes via UDP socket

This means that things like feeding influxdb or Kafka no longer require you to modify your system python install.

In exchange, you will need a separate process that reads UDP multicast broadcasts.

The port in the Indigo plugin will need to match the port in your client as well. Default is 8087.

For those of you that write your own clients, the broadcast group is: 224.1.1.1
