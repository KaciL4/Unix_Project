from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
import requests
import os
from datetime import datetime, timedelta
from icalendar import Calendar

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-me'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

DEFAULT_LAT =  45.5017
DEFAULT_LON = -73.5673
DEFAULT_CITY = "Montreal"

state = {'view': 'home', 'message': '', 'display_on': False, 'brightness': 100, 'weather': None, 'calendar':None}

@app.route('/')
def index():
	return "Backend Running."

@app.route('/display')
def display():
	return render_template('display.html')

@app.route('/controller')
def controller():
	return render_template('controller.html')

@app.route('/api/state', methods=['GET'])
def get_state():
	return jsonify(state)

@app.route('/api/set', methods=['POST'])
def set_state():
	data = request.json or {}
	for k, v in data.items():
		if k in state:
			state[k] = v
	socketio.emit('state_update', state)
	return jsonify({'ok': True, 'state': state})

@app.route('/api/toggle_display', methods=['POST'])
def api_toggle_display():
	state['display_on'] = not state['display_on']
	socketio.emit('state_update', state)
	return jsonify({'ok': True, 'display_on': state['display_on']})

@app.route('/api/set_view', methods=['POST'])
def api_set_view():
	data = request.json or {}
	state['view'] = data.get('view', 'home')
	socketio.emit('state_update', state)
	return jsonify({'ok': True, 'view': state['view']})

@app.route('/api/set_message', methods=['POST'])
def api_set_message():
	data = request.json or {}
	state['message'] = data.get('message', '')
	socketio.emit('state_update', state)
	return jsonify({'ok': True, 'message': state['message']})

@app.route('/api/remove_message', methods=['POST'])
def api_remove_message():
	state['message'] = ''
	socketio.emit('state_update', state)
	return jsonify({'ok': True})

@app.route('/api/fetch_weather', methods=['POST'])
def api_fetch_weather():
	weather_data = fetch_weather()
	state['weather'] = weather_data
	state['view'] = 'weather'
	socketio.emit('state_update', state)
	return jsonify({'ok': True, 'weather': weather_data})

@socketio.on('connect')
def on_connect():
	socketio.emit('state_update', state)

@socketio.on('set_message')
def on_set_message(data):
    state['message'] = data.get('message', '')
    socketio.emit('state_update', state)

@socketio.on('remove_message')
def on_remove_message():
	state['message'] = ''
	socketio.emit('state_update', state)

@socketio.on('set_view')
def on_set_view(data):
	state['view'] = data.get('view', 'home')
	socketio.emit('state_update', state)

@socketio.on('toggle_display')
def on_toggle_display():
	state['display_on'] = not state['display_on']
	socketio.emit('state_update', state)
	
def fetch_weather(lat=DEFAULT_LAT, lon=DEFAULT_LON):
	"""Fetch weather data from Open-Meteo API (free, no key needed)"""
	try:
		url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code&temperature_unit=celsius"
		response = requests.get(url, timeout=5)
		if response.status_code == 200:
			data = response.json()
			current = data['current']
			
			# Weather code to description mapping
			weather_codes = {
				0: 'Clear sky', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast',
				45: 'Foggy', 48: 'Foggy', 51: 'Light drizzle', 53: 'Drizzle', 
				55: 'Heavy drizzle', 61: 'Light rain', 63: 'Rain', 65: 'Heavy rain',
				71: 'Light snow', 73: 'Snow', 75: 'Heavy snow', 80: 'Rain showers',
				81: 'Rain showers', 82: 'Heavy rain showers', 95: 'Thunderstorm'
			}
			
			weather_code = current.get('weather_code', 0)
			description = weather_codes.get(weather_code, 'Unknown')
			
			return {
				'city': DEFAULT_CITY,
				'temp': round(current['temperature_2m']),
				'feels_like': round(current['apparent_temperature']),
				'description': description,
				'humidity': current['relative_humidity_2m']
			}
		else:
			return {'error': 'Could not fetch weather data'}
	except Exception as e:
		return {'error': str(e)}
	
@socketio.on('fetch_weather')
def on_fetch_weather(data=None):
	city = data.get('city', DEFAULT_CITY) if data else DEFAULT_CITY
	weather_data = fetch_weather(city)
	state['weather'] = weather_data
	socketio.emit('state_update', state)

@app.route('/api/fetch_calendar', methods=['POST'])
def api_fetch_calendar():
	calendar_data = fetch_calendar()
	state['calendar'] = calendar_data
	state['view'] = 'calendar'
	socketio.emit('state_update', state)
	return jsonify({'ok': True, 'calendar': calendar_data})


CALENDAR_URL = "https://www.officeholidays.com/ics/canada/quebec"

def fetch_calendar(days_ahead=7):
	"""Fetch calendar events from public ICS feed"""
	try:
		response = requests.get(CALENDAR_URL, timeout=10)
		if response.status_code == 200:
			cal = Calendar.from_ical(response.content)
			events = []

			now = datetime.now()
			future = now + timedelta(days=days_ahead)

			for component in cal.walk():
				if component.name == "VEVENT":
					event_start = component.get('dtstart').dt

					# Handle all-day events (date objects)
					if isinstance(event_start, datetime):
						event_date = event_start
					else:
						event_date = datetime.combine(event_start, datetime.min.time())

					# Only include upcoming events
					if now <= event_date <= future:
						events.append({
							'title': str(component.get('summary')),
							'date': event_date.strftime('%Y-%m-%d'),
							'time': event_date.strftime('%H:%M') if isinstance(event_start, datetime) else 'All day',
							'description': str(component.get('description', ''))[:100]
						})

			# Sort by date
			events.sort(key=lambda x: x['date'])

			return {
				'events': events[:10],  # Limit to 10 events
				'count': len(events)
			}
		else:
			return {'error': 'Could not fetch calendar data'}
	except Exception as e:
		return {'error': str(e)}

@socketio.on('set_brightness')
def handle_brightness(data):
	state['brightness'] = int(data['brightness'])
	socketio.emit('state_update', state)

if __name__ == "__main__":
	socketio.run(app, host='0.0.0.0', port=5000, debug=True)
