import asyncio
import struct
import re
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
import pygame

import evdev
from evdev import InputDevice, categorize, ecodes

from typing import Any, Dict, List, Union

class APICall:
	def __init__(self) -> None:
		self.stateID: int = 0
		self.BoolValue: bool = False
		self.IntValue: int = 0
		self.FloatValue: float = 0.0
		self.DoubleValue: float = 0.0
		self.StringValue: str = ""
		self.LongValue: int = 0

class StateInfo:
	def __init__(self, ID, Type, Path):
		self.ID = ID
		self.Type = Type
		self.Path = Path

class State:
	def __init__(self, ID, Path, Value):
		self.ID = ID
		self.Path = Path
		self.Value = Value

class CommandInfo:
	def __init__(self, ID, Path):
		self.ID = ID
		self.Path = Path


class InfiniteFlightAPIClient:
	def __init__(self) -> None:
		self.command_base: int = 0x100000
		self.state_info: List[StateInfo] = []
		self.state_info_by_id: Dict[int, StateInfo] = {}
		self.apiCallQueue: List[APICall] = []
		self.states: List[State] = []
		self.state_by_id: Dict[int, State] = {}
		self.commands: List[CommandInfo] = []
		self.lock: asyncio.Lock = asyncio.Lock()
		self.stateInfoOK = False
		self.joystickInitOK = False
		self.joystick_axis_info = {}
		self.keys_info = {}
		self.alljoystick_axis_info = {}
		self.joystick_devices = []
		self.keyboard_devices = []

	async def refresh_all_values(self) -> None:
		if self.stateInfo:
			for item in self.stateInfo:
				await self.get_state(item.ID)

	async def run_command(self, command_id):
		async with self.lock:
			await self.send_int(self.writer, command_id)
			await self.send_boolean(self.writer, True)

		
	async def read_command(self):
		print("Reading command 2")
		command_id = await self.read_int()
		print ("Command ID: {0}".format(command_id))
		data_length = await self.read_int()
		print("Read commandID: {0} - Length: {1}".format(command_id, data_length))
	
		if command_id == -1:
			await self.read_manifest()
		else:
			state_info = self.state_info_by_id[command_id]
			state = self.state_by_id[command_id]

			if state_info["type"] == bool:
				value = await self.read_boolean()
				state["value"] = value
			elif state_info["type"] == int:
				value = await self.read_int()
				state["value"] = value
			elif state_info["type"] == float:
				value = await self.read_float()
				state["value"] = value
			elif state_info["type"] == str:
				value = await self.read_string()
				state["value"] = value
			elif state_info["type"] == 'long':  # Use a string 'long' to represent the Python int type for large integers
				value = await self.read_long()
				state["value"] = value
				 
		#self.state_received(command_id)

	async def connect(self, host: str = "localhost", port: int = 10112) -> None:
		while True:
			try:
				self.reader, self.writer = await asyncio.open_connection(host, port)
				print("Connection established")

				async def read() -> None:
					try:
						while True:
							print("Reading command 1")
							await self.read_command()
					except Exception as ex:
						print("Exception in read: {0}".format(ex))
						raise ConnectionError("Error in process_queue()")

				async def process_queue() -> None:
					try:
						while True:
							if self.stateInfoOK == False:
								print("Requesting state list...")
								await self.send_command(-1)
								await asyncio.sleep(0.5)
							else:
								await self.send_joystick_state_evdev()
								await asyncio.sleep(0.016)
					except Exception as ex:
						print("Exception in process_queue: {0}".format(ex))
						raise ConnectionError("Error in process_queue")

				await asyncio.gather(read(), process_queue())

			except ConnectionError as e:
				print(f"Connection error: {e}. Attempting to reconnect...")
				await asyncio.sleep(5)  # Wait 5 seconds before attempting to reconnect
				continue
			
			except Exception as e:
				print(f"Unexpected error: {e}")
				break

	async def send_joystick_state_evdev(self):
		if self.joystickInitOK == False:
			devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
			#self.joystick_devices = [device for device in devices if device.capabilities().get(ecodes.EV_ABS) or device.capabilities().get(ecodes.EV_KEY)]
			self.joystickInitOK = True
			
			print ("Joystick devices: {0}".format(self.joystick_devices))

			axisIndex = 0
			buttonIndex = 0

			for device in devices:
				# show device name
				print ("Device: {0}".format(device.name))

				if not self.is_joystick(device) and not self.is_keyboard(device):
					print("Not a joystick or keyboard")
					continue

				if self.is_joystick(device):					
					if evdev.ecodes.EV_ABS in device.capabilities():
						absinfo = device.capabilities()[evdev.ecodes.EV_ABS]
					
						print ("Valid device found: {0}".format(device.name))

						device_axis_info = {}
					
						for axis, info in absinfo:
							device_axis_info['axis_' + str(axis)] = {
								'type': 'axis',
								'code': axis,
								'min': info.min,
								'max': info.max,
								'axisIndex': axisIndex
							}
							axisIndex += 1
						
						keyinfo = device.capabilities()[evdev.ecodes.EV_KEY]
						print ("Keyinfo: {0}".format(keyinfo))
						for button_code in keyinfo:
							# show button index and	code
							# print ("Adding Button: {0} - {1}".format(buttonIndex, button_code))
							device_axis_info['button_' + str(button_code)] = {
								'type': 'button',
								'code': button_code,
								'buttonIndex': buttonIndex
							}
							buttonIndex += 1

						print ("Device path {0}".format(device.path))
						self.alljoystick_axis_info[device.path] = device_axis_info
						self.joystick_devices.append(device)

						# store this data in a dictionary for later
						self.joystick_axis_info[device.path] = absinfo
						pass

				elif self.is_keyboard(device):
					keyinfo = device.capabilities()[evdev.ecodes.EV_KEY]
					#print("Keyinfo: {0}".format(keyinfo))

					device_key_info = {}
					keyIndex = 0
					for key_code in keyinfo:
						device_key_info['button_' + str(key_code)] = {
							'type': 'button',
							'code': key_code,
							'buttonIndex': keyIndex
						}
						keyIndex += 1

					print("Device path {0}".format(device.path))

					#print("Device key info: {0}".format(device_key_info))

					self.alljoystick_axis_info[device.path] = device_key_info
					self.joystick_devices.append(device)

			return

		axesPath = "api_joystick/axes/"
		buttonsPath = "api_joystick/buttons/"

		deviceButtonIndex = 0
		deviceAxisIndex = 0

		deviceIndex = 0

		for device in self.joystick_devices:
			event = device.read_one()  # Poll the device state using read_one()

			while event:
				if event.type == ecodes.EV_ABS:					
					# Get the axis info for this device
					axis_info_list = self.joystick_axis_info[device.path]
					# Find the correct axis information in the list					
					device_info = self.alljoystick_axis_info[device.path]
					axis_info = device_info.get('axis_' + str(event.code), None)

					if axis_info is not None:
						min_value = axis_info['min']
						max_value = axis_info['max']
						axisIndex = axis_info['axisIndex']
						value = self.normalize_value(float(event.value), min_value, max_value)  # Normalize the value to be in the range of -1 to 1

					axisPath = axesPath + str(axisIndex) + "/value"
					command_id = await self.get_command_id(axisPath)

					if command_id is not None:  # Add this check
						joystick_state = self.state_by_id[command_id]
						await self.set_state(command_id, int(value * 1000))
					else :
						print("Command ID not found for {0}".format(axisPath))

				elif event.type == ecodes.EV_KEY:
					value = event.value
												
					device_info = self.alljoystick_axis_info[device.path]
					button_info = device_info.get('button_' + str(event.code), None)

					if button_info is not None:
						#print ("Button found: {0}".format(event.code))
						buttonIndex = button_info['buttonIndex']
					else:
						print ("Button not found: {0}".format(event.code))
									
					buttonPath = buttonsPath + str(buttonIndex) + "/value"

					command_id = await self.get_command_id(buttonPath)

					joystick_state = self.state_by_id[command_id]
					await self.set_state(command_id, int(value))
				
				event = device.read_one()  # Poll the device state using read_one()

			deviceButtonIndex += 63
			deviceAxisIndex + 16
			deviceIndex += 1

	# pygame version is not used right now because it doesn't work on the py. It works on windows though. It seems like 
	# it may need to have a display attached, not clear...
	async def send_joystick_state_pygame(self):

		if self.joystickInitOK == False:
			pygame.init()
			pygame.joystick.init()
			self.joystick_count = pygame.joystick.get_count()
			print ("Joystick Count: {0}".format(self.joystick_count))
			self.joystickInitOK = True
			return

		axesPath = "api_joystick/axes/"
		buttonsPath = "api_joystick/buttons/"

		buttonIndex = 0
		axisIndex = 0

		# get joystick state
		pygame.event.pump()
		for i in range(self.joystick_count):
			joystick = pygame.joystick.Joystick(i)
			num_axes = joystick.get_numaxes()
			num_buttons = joystick.get_numbuttons()

			for axis in range(num_axes):
				value = joystick.get_axis(axis)
				#print("Joystick: {}, Axis: {}, Value: {}".format(i, axis, value))
				# format path of axis 
				axisPath = axesPath + str(axisIndex) + "/value"
				# get the command_id for the joystick state
				command_id = await self.get_command_id(axisPath)
				# get the joystick state
				joystick_state = self.state_by_id[command_id]
				# send the joystick state
				# print the type of Value
				print ("Type of Value: {0} - {1} - Casted: {2}".format(type(value), value, int(value)))
				# call self.set_state but as an int
				await self.set_state(command_id, int(value * 1000))
				axisIndex = axisIndex + 1

			for button in range(num_buttons):
				value = joystick.get_button(button)
				#print("Joystick: {}, Button: {}, Value: {}".format(i, button, value))
				# format path of button 
				buttonPath = buttonsPath + str(buttonIndex) + "/value"
				# get the command_id for the joystick state
				command_id = await self.get_command_id(buttonPath)
				# get the joystick state
				joystick_state = self.state_by_id[command_id]
				# send the joystick state
				await self.set_state(command_id, int(value))
				buttonIndex = buttonIndex + 1
				
	async def send_command(self, command_id):
		async with self.lock:
			await self.send_int(-1)  # index of command list
			await self.send_boolean(False)

	async def set_state(self, command_id, value):
		#print ("Setting state {0} to {1}".format(command_id, value))
		async with self.lock:
			await self.send_int(command_id)
			await self.send_boolean(True)  # set

			if isinstance(value, bool):
				await self.send_boolean(value)
			elif isinstance(value, int):
				await self.send_int(value)
			elif isinstance(value, float):
				await self.send_float(value)
			elif isinstance(value, str):
				await self.send_string(value)
			elif isinstance(value, (long, int)):  # Python 2.x: long; Python 3.x: int
				await self.send_long(value)
			elif isinstance(value, double):
				await self.send_double(value)
			else:
				raise ValueError("Unsupported value type")

	async def get_state(command_id):
		async with self.lock:
			await self.send_int(command_id)
			await self.send_boolean(False)
		
	# create method to retrieve the command_id based on a state name
	async def get_command_id(self, state_name):
		# show state count
		#print ("State Count: {0}".format(len(self.state_info)))
		for listedState in self.state_info:
			#print ("Checking State: {0} - {1}".format(listedState.Path, state_name))
			if listedState.Path == state_name:
				return listedState.ID

	def normalize_value(self, value, min_value, max_value):
		neutral_position = (max_value + min_value) / 2
		normalized_value = (value - neutral_position) / (max_value - neutral_position)
		return normalized_value

	def is_joystick(self, device):
		if not (device.capabilities().get(ecodes.EV_ABS) and device.capabilities().get(ecodes.EV_KEY)):
			print ("Device {0} is not a joystick because it does not have EV_ABS and EV_KEY capabilities".format(device.name))
			return False

			# Exclude devices with REL_X and REL_Y events, which are common for mice
		if ecodes.EV_REL in device.capabilities() and ecodes.REL_X in device.capabilities()[ecodes.EV_REL] and ecodes.REL_Y in device.capabilities()[ecodes.EV_REL]:
			print ("Device {0} is not a joystick because it has REL_X and REL_Y capabilities".format(device.name))
			return False

		return True

		
	def is_keyboard(self, device):
		isJoystick = evdev.ecodes.EV_KEY in device.capabilities()
		if isJoystick:
			print ("Device {0} is a keyboard".format(device.name))
		else:
			print ("Device {0} is not a keyboard".format(device.name))
		return isJoystick
	
# Read Methods        
		
	async def read_int(self) -> int:
		data = await self.reader.readexactly(4)
		return struct.unpack("i", data)[0]

	async def read_double(self) -> float:
		data = await self.reader.readexactly(8)
		return struct.unpack("d", data)[0]

	async def read_float(self) -> float:
		data = await self.reader.readexactly(4)
		return struct.unpack("f", data)[0]

	async def read_long(self) -> int:
		data = await self.reader.readexactly(8)
		return struct.unpack("q", data)[0]

	async def read_boolean(self) -> bool:
		data = await self.reader.readexactly(1)
		return struct.unpack("?", data)[0]

	async def read_string(self) -> str:
		size = await self.read_int()
		data = await self.reader.readexactly(size)
		return data.decode("utf-8")

# Send methods

	async def send_int(self, value: int) -> None:
		data = struct.pack("i", value)
		self.writer.write(data)
		await self.writer.drain()

	async def send_boolean(self, value: bool) -> None:
		data = struct.pack("?", value)
		self.writer.write(data)
		await self.writer.drain()

	async def send_string(self, value: str) -> None:
		data = value.encode("utf-8")
		await self.send_int(len(data))
		self.writer.write(data)
		await self.writer.drain()

	async def send_float(self, value: float) -> None:
		data = struct.pack("f", value)
		self.writer.write(data)
		await self.writer.drain()

	async def send_double(self, value: float) -> None:
		data = struct.pack("d", value)
		self.writer.write(data)
		await self.writer.drain()

	async def send_long(self, value: int) -> None:
		data = struct.pack("q", value)
		self.writer.write(data)
		await self.writer.drain()

	def queue_call(self, call):
		with self.api_call_queue_lock:
			self.api_call_queue.append(call)

	@staticmethod
	def get_type_index(py_type):
		type_dict = {
			bool: 0,
			int: 1,
			float: 2,
			str: 4,
			"long": 5,  # Use a string 'long' to represent the Python int type for large integers
		}
		return type_dict.get(py_type, -1)

	@staticmethod
	def get_type_from_index(index):
		index_dict = {
			0: bool,
			1: int,
			2: float,
			3: float,
			4: str,
			5: "long",  # Use a string 'long' to represent the Python int type for large integers
		}
		return index_dict.get(index, None)

# Read Manifest		
	async def read_manifest(self):
		print("Reading Manifest...")
		manifest_str = await self.read_string()

		lines = manifest_str.split('\n')

		print("States:", len(lines))

		if (len(lines) <= 1):
			print("Invalid states - Infinite Flight may not be ready")
			return

		for i, line in enumerate(lines):
			items = line.split(',')

			if len(items) == 3:
				state_id = int(items[0])
			else:
				continue

			if (state_id & self.command_base) == self.command_base:
				# store commands
				# self.commands.append(CommandInfo(ID=state_id, Path=items[2]))
				pass
			else:
				state_type = self.get_type_from_index(int(items[1]))
				new_state_info = StateInfo(ID=state_id, Type=state_type, Path=items[2])
				self.state_info.append(new_state_info)
				self.state_info_by_id[state_id] = new_state_info
				state_data = State(ID=state_id, Path=items[2], Value="")
				self.states.append(state_data)
				self.state_by_id[state_id] = state_data

		print ("State Count: {0}".format(len(self.state_info)))
		# print all states
		"""
		for state in self.state_info:
			if state is not None:
				# if state.Path contains "api_joystick" then store the state ID
				if "api_joystick" in state.Path:
					print ("Joystick State ID: {0}".format(state.ID))				
				#print(state)
		"""
		self.stateInfoOK = True

		print ("Read manifest complete")

		#self.manifest_received()

		# Once we get the manifest, refresh all values once.
		#await self.refresh_all_values()
		
async def main() -> None:
	print("Starting...")
	api_client = InfiniteFlight
