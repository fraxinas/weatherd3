weatherd3

(CC) 2018 by Andreas Frisch <fraxinas@dreambox.guru>

This python3 asyncio script opens a local HTTP server to which LAN-enabled 
weather stations like WH2601 can push their data instead of wunderground.
Weatherd3 then takes the data, converts units where needed and relays
it to a linknx server under the configured group addresses.
In the weather logger's web interface, please configure:
Remote Server: Customized
Server IP: IP of the machine running `weatherd3`
Server Port: 8084 by default
Server Type: PHP
Station ID / Password: anything (ignored)

`weatherd3.py` requires `python3` with `asyncio` and `aiohttp`

please `cp config_sample.json config.json` and set the correct
`linknx host` and `knx_group` addresses.

run `weatherd3.py` in the background or by systemd unit file (to be added)
