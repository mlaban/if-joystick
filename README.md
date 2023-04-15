# if-joystick
A program to connect to Infinite Flight via Infinite Flight Connect API v2 and send joystick/keyboard inputs.

IFJoystick is a Python script that allows you to use your joystick or keyboard to control Infinite Flight, a popular flight simulator app for mobile devices. It does this by creating a virtual joystick and mapping the physical joystick's inputs or keyboard inputs to the virtual joystick's inputs.

## Getting Started
To use IFJoystick, you'll need to have Python installed on your device. You'll also need to enable Infinite Flight Connect in the IF settings/general.

Next, create/edit a config.json file with the following schema:

```
{
	"ssid": "",
	"password": "",
	"remote_ip_address": "192.168.0.1",
	"remote_port": 10112
}
```

Make sure to specify the IP address of your device where Infinite Flight runs on in the remote_ip_address field.

Then, just run python IFJoystick.py and the script will start listening for joystick or keyboard inputs and send them over to Infinite Flight.

## Binding Controls
Binding controls with if-joystick is simple. Just move the axis or press the button you want to bind.
Infinite Flight handles this internally by creating a virtual device when we have the API running. This virtual device has 32 axes, and 128 buttons.

The Python script gets the available devices, lists the axes and buttons, maps them to indices that work with the virtual joystick, and sets the state of those items via the API. For example, the script sets the value of api_joystick/axes/0/value to the value of the first axis found on the physical joystick.

If you want to map the POV hat, which is sometimes registered as a set of 2 axes, use the "Move Camera Left/Right" and "Up/Down" commands in the commands section.

## Stability
The app should be fairly stable, but it may need to be optimized a bit for the Raspberry Pi Zero, as there may be some lag in the axes sometimes.

## Setup on Raspberry Pi Zero

To set up IFJoystick on a Raspberry Pi Zero, you'll need to install the following packages:
```	
pip install evdev
```

To make the python run as a service, you'll need to create a service file. Create a file called ifjoystick.service in /etc/systemd/system/ with the following contents:
```
[Unit]
Description=if-joystick
After=multi-user.target

[Service]
Type=idle
ExecStart=/usr/bin/python3 /where/the/file/is/installed/if-joystick.py >> /var/log/if-joystick.log 2>&1
Restart=always
User=laura

[Install]
WantedBy=multi-user.target
```

Then, run the following commands:
```
sudo systemctl daemon-reload
sudo systemctl enable if-joystick.service
sudo systemctl start if-joystick.service
```

## Disclaimer
This was coded with help of ChatGPT by someone who has almost no idea what they're doing in Python and had to remember university projects on NetBSD from many years ago. 
It's not the most efficient code, but it works. If you have any suggestions, feel free to open an issue or a pull request.

Use at your own risk.

## Additional Information
Infinite Flight Connect API v2 documentation:
https://staging.infiniteflight.com/guide/developer-reference/connect-api/version-2

Infinite Flight Download:
https://infiniteflight.com