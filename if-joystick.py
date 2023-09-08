import asyncio
import os
import json
import subprocess

from infinite_flight_api_client import InfiniteFlightAPIClient

# Laura: I coded this while being a complete noob at python, so it's probably not the best code ever written. It was written with the help of Github Copilot and ChatGPT.
#		 So go easy on me if the code is not perfect. I'm still learning. I'm sure there are better ways to do this. I'm just trying to get something working.

async def main():
	print("Loading Infinite Flight API Client")
	
	try:
		import evdev
	except ImportError:
		print("Please install evdev")
		return

	config_file_path = os.path.expanduser("./config.json")

	# check if config file is present
	if not os.path.isfile(config_file_path):
		print("Config file not found. Please create a config.json file in the same directory as this script.")
		return

	# load config
	with open(config_file_path, 'r') as f:
		config = json.load(f)

	ssid = config['ssid']
	password = config['password']
	remote_ip_address = config['remote_ip_address']
	remote_port = config['remote_port']

	print ("config loaded with ssid: " + ssid + " password: " + password + " remote_ip_address: " + remote_ip_address + " remote_port: " + str(remote_port))

	# apply the ssid and password to the wifi interface if we are not currently on this wifi network
	#if not ssid in str(subprocess.check_output("iwgetid -r", shell=True)):
	#	print("Connecting to wifi network: " + ssid)
	#	subprocess.call("nmcli dev wifi connect " + ssid + " password " + password, shell=True)
	#	print("Connected to wifi network: " + ssid) 
	#else:
	#	print("Already connected to wifi network: " + ssid)
	
	# show current IP
	print("Current IP: " + str(subprocess.check_output("hostname -I", shell=True)))

	while True:
		try:
			client = InfiniteFlightAPIClient()
			print("Connecting to client: " + remote_ip_address + ":" + str(remote_port))
			await client.connect(host=remote_ip_address, port=remote_port)
			print("Connected to client!")
		except Exception as e:
			print("Error: " + str(e))
			print("Retrying in 5 seconds...")
			await asyncio.sleep(5)
			continue

	print("DONE");

if __name__ == "__main__":
	asyncio.run(main())