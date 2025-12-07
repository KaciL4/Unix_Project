# web framework for running the backend (creates web pages and API endpoints)
from flask import Flask, render_template, jsonify, request

# let the backend send real-time updates to the frontend (no page reload)
from flask_socketio import SocketIO

# to call external APIs (ex: weather API, calendar URL)
import requests

# let the program interact with the computer (files, folders, environment variables)
import os

# for working with dates and times
from datetime import datetime, timedelta, time

# to read .ics calendar files (like Google Calendar export)
from icalendar import Calendar

# to generate a QR code image
from io import BytesIO
from flask import send_file
import qrcode

# ---------------------------------------------------------------
# APP SETUP
# ---------------------------------------------------------------

app = Flask(__name__)

# Secret key is required by Flask for security (sessions, cookies, etc.)
# If none is provided in the system, it generates a random one
app.config['SECRET_KEY'] = os.environ.get("SMARTMIRROR_SECRET_KEY", os.urandom(24))

# SocketIO enables live server → screen communication (instantly update the mirror display)
socketio = SocketIO(app, cors_allowed_origins=[], async_mode="eventlet")

# URL that the QR code will open (the controller page)
QR_TARGET_URL = "http://smartmirror.local:5000/controller"


# ---------------------------------------------------------------
# QR CODE ENDPOINT
# ---------------------------------------------------------------
@app.route("/controller_qr")  #@app.route connects a URL to a function
def controller_qr():
    # Creates and returns a QR code image that links to the controller page.
    img = qrcode.make(QR_TARGET_URL)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


# ---------------------------------------------------------------
# CONFIG FILE (stores user settings like custom calendar URL)
# ---------------------------------------------------------------

CONFIG_PATH = os.path.expanduser("~/.config/smartmirror/config.json")

def load_config():
    # Loads saved settings from a config file, if it exists.
    if os.path.exists(CONFIG_PATH):
        try:
            import json
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

# Load configuration once at startup
config = load_config()

# Calendar URL, either from config file, environment variable, or default fallback
CALENDAR_URL = config.get("calendar_url") or os.environ.get(
    "SMARTMIRROR_CAL_URL",
    "https://YOUR_DEFAULT_ICS_URL.ics"
)

# Default location (Montreal) - can be changed later (controller device location)
DEFAULT_LAT = 45.5017
DEFAULT_LON = -73.5673
DEFAULT_CITY = "Current Location" # no trouble for getting different location name (too hard/can't really test)

# ---------------------------------------------------------------
# GLOBAL STATE
# Frontend asks for this state and updates automatically through SocketIO.
# ---------------------------------------------------------------

state = {
    'view': 'home',     
    'message': '',         
    'display_on': True,   
    'brightness': 100,     
    'weather': {'visible': False},   
    'calendar': {'visible': False},  
    'location': {
        'lat': DEFAULT_LAT,
        'lon': DEFAULT_LON
    }
}


# ---------------------------------------------------------------
# BASIC ROUTES (normal web pages)
# ---------------------------------------------------------------

@app.route('/')
def index():
    return "Backend Running."

@app.route('/display')
def display():
    # Shows the smart mirror screen (HTML template)
    return render_template('display.html')

@app.route('/controller')
def controller():
    # Shows the remote control interface (HTML template)
    return render_template('controller.html')


# ---------------------------------------------------------------
# API ROUTES
# used by the frontend to GET or SET data.
# return JSON instead of full HTML pages.
# ---------------------------------------------------------------

@app.route('/api/state', methods=['GET']) # /api/... means the URL is for the data
def get_state():
    # Sends the entire state to the frontend. 
    return jsonify(state)  # jsonify turns data into JSON because it's a universal data format for websites

@app.route('/api/set', methods=['POST'])
def set_state():
    # Updates multiple state values at once.
    data = request.json or {}   # whatever JSON sent the browser, if nothing, use an empty dictionnary instead of crashing
    for k, v in data.items(): # every key and value in the JSON
        if k in state:   # if the key exists, update it
            state[k] = v  

    # Broadcast update to all connected screens 
    socketio.emit('state_update', state)   # socket.emit is for the live communication from the server to the browser
    return jsonify({'ok': True, 'state': state})


@app.route('/api/toggle_display', methods=['POST'])
def api_toggle_display():
    # Turns the mirror display on or off.
    state['display_on'] = not state['display_on'] # flip boolean value
    socketio.emit('state_update', state)
    return jsonify({'ok': True, 'display_on': state['display_on']})


@app.route('/api/set_view', methods=['POST'])
def api_set_view():
    # Changes what page/view the mirror is showing.
    data = request.json or {}
    view = data.get('view', 'home')
    state['view'] = view

    # If returning to home, hide widgets
    if view == 'home':
        if state['weather']:
            state['weather']['visible'] = False
        if state['calendar']:
            state['calendar']['visible'] = False

    socketio.emit('state_update', state)
    return jsonify({'ok': True, 'view': state['view']})


@app.route('/api/set_message', methods=['POST'])
def api_set_message():
    # Updates the custom message text.
    data = request.json or {}
    state['message'] = data.get('message', '')
    socketio.emit('state_update', state)
    return jsonify({'ok': True, 'message': state['message']})


@app.route('/api/remove_message', methods=['POST'])
def api_remove_message():
    # Clears the message text.
    state['message'] = ''
    socketio.emit('state_update', state)
    return jsonify({'ok': True})


# ---------------------------------------------------------------
# WEATHER API
# ---------------------------------------------------------------

@app.route('/api/fetch_weather', methods=['POST'])
def api_fetch_weather():
    # Fetches weather data for the current location and shows it.
    lat = state['location']['lat']
    lon = state['location']['lon']
    weather_data = fetch_weather(lat=lat, lon=lon)
    weather_data['visible'] = True
    state['weather'] = weather_data

    socketio.emit('state_update', state)
    return jsonify({'ok': True, 'weather': weather_data})


@app.route('/api/toggle_weather', methods=['POST'])
def api_toggle_weather():
    # Shows/hides the weather widget. Fetches fresh data when turning on.
    visible = state['weather'].get('visible', False)

    if visible:
        state['weather']['visible'] = False
    else:
        lat = state['location']['lat']
        lon = state['location']['lon']
        weather_data = fetch_weather(lat=lat, lon=lon)
        weather_data['visible'] = True
        state['weather'] = weather_data

    socketio.emit('state_update', state)
    return jsonify({'ok': True, 'visible': state['weather']['visible']})


# ---------------------------------------------------------------
# CALENDAR API
# ---------------------------------------------------------------

@app.route('/api/toggle_calendar', methods=['POST'])
def api_toggle_calendar():
    # Shows/hides calendar widget. Refreshes data when turning on.
    visible = state['calendar'].get('visible', False)

    if visible:
        state['calendar']['visible'] = False
    else:
        calendar_data = fetch_calendar()
        calendar_data['visible'] = True
        state['calendar'] = calendar_data

    socketio.emit('state_update', state)
    return jsonify({'ok': True, 'visible': state['calendar']['visible']})


@app.route('/api/fetch_calendar', methods=['POST'])
def api_fetch_calendar():
    # Fetches and displays calendar events.
    calendar_data = fetch_calendar()
    calendar_data['visible'] = True
    state['calendar'] = calendar_data

    socketio.emit('state_update', state)
    return jsonify({'ok': True, 'calendar': calendar_data})


@app.route('/api/set_calendar_url', methods=['POST'])
def api_set_calendar_url():
    # Saves a new calendar URL and writes it into the config file.
    data = request.json or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"ok": False, "error": "No URL provided"}), 400

    if not (url.startswith("http://") or url.startswith("https://")):
        return jsonify({"ok": False, "error": "Invalid URL"}), 400

    # Update global variable + config dictionary
    global CALENDAR_URL, config
    CALENDAR_URL = url
    config["calendar_url"] = url

    # Save permanently to file
    try:
        import json
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f: # open for writing
            json.dump(config, f) #save into the file as JSON
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    return jsonify({"ok": True})


# ---------------------------------------------------------------
# SOCKET.IO EVENTS (real-time updates)
# ---------------------------------------------------------------

@socketio.on('connect')
def on_connect():
    # When a device connects, send it the current state immediately.
    socketio.emit('state_update', state)

@socketio.on('set_message')
def on_set_message(data):
    # Real-time update of the message text.
    state['message'] = data.get('message', '')
    socketio.emit('state_update', state)

@socketio.on('remove_message')
def on_remove_message():
    # Real-time clearing of message.
    state['message'] = ''
    socketio.emit('state_update', state)

@socketio.on('set_view')
def on_set_view(data):
    # Real-time switching of views/pages.
    state['view'] = data.get('view', 'home')
    socketio.emit('state_update', state)

@socketio.on('toggle_display')
def on_toggle_display():
    # Turns display on/off instantly.
    state['display_on'] = not state['display_on']
    socketio.emit('state_update', state)

@socketio.on('set_brightness')
def handle_brightness(data):
    """Updates brightness live."""
    state['brightness'] = int(data['brightness'])
    socketio.emit('state_update', state)

@socketio.on('update_location')
def on_update_location(data):
    # Updates location and fetches fresh weather.
    lat = data.get('lat')
    lon = data.get('lon')

    # Validate numbers
    try:
        lat = float(lat)
        lon = float(lon)
    except:
        return

    state['location']['lat'] = lat
    state['location']['lon'] = lon

    # Refresh weather immediately
    updated = fetch_weather(lat=lat, lon=lon)
    updated['visible'] = True
    state['weather'] = updated

    socketio.emit('state_update', state)


# ---------------------------------------------------------------
# HELPER FUNCTION: FETCH WEATHER
# ---------------------------------------------------------------

def fetch_weather(lat=DEFAULT_LAT, lon=DEFAULT_LON):
     # Calls Open-Meteo API and returns simplified weather info.
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code&temperature_unit=celsius"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            current = data['current']

            # Converts weather codes into human-friendly descriptions
            weather_codes = {
                0: 'Clear sky', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast',
                45: 'Foggy', 48: 'Foggy', 51: 'Light drizzle', 53: 'Drizzle',
                55: 'Heavy drizzle', 61: 'Light rain', 63: 'Rain', 65: 'Heavy rain',
                71: 'Light snow', 73: 'Snow', 75: 'Heavy snow', 80: 'Rain showers',
                81: 'Rain showers', 82: 'Heavy rain showers', 95: 'Thunderstorm'
            }

            desc = weather_codes.get(current.get('weather_code', 0), 'Unknown')

            return {
                'city': DEFAULT_CITY,
                'temp': round(current['temperature_2m']),
                'feels_like': round(current['apparent_temperature']),
                'description': desc,
                'humidity': current['relative_humidity_2m']
            }
        else:
            return {'error': 'Could not fetch weather data'}

    except Exception as e:
        return {'error': str(e)}


# ---------------------------------------------------------------
# HELPER FUNCTION: FETCH CALENDAR EVENTS
# ---------------------------------------------------------------

def fetch_calendar():
    # Loads .ics calendar events, filters next 7 days, return a simplified list.
    try:
        resp = requests.get(CALENDAR_URL, timeout=10)
        resp.raise_for_status()

        cal = Calendar.from_ical(resp.text)

        now = datetime.now()
        end = now + timedelta(days=7)

        events = []

        # Loop through all events in the ICS file
        for component in cal.walk('vevent'):
            summary = str(component.get('summary', ''))

            dtstart = component.get('dtstart')
            if not dtstart:
                continue

            dtstart = dtstart.dt  # Could be a full datetime or just a date

            # Convert to consistent format
            if isinstance(dtstart, datetime):
                start = dtstart.replace(tzinfo=None)
            else:
                start = datetime.combine(dtstart, time.min)

            # Only include events within the next week
            if not (now <= start <= end):
                continue

            # Format date string for display
            if isinstance(dtstart, datetime):
                date_str = start.strftime("%Y-%m-%d %H:%M")
            else:
                date_str = start.strftime("%Y-%m-%d (all day)")

            events.append({
                "summary": summary,
                "date": date_str,
                "start_dt": start
            })

        # Sort chronologically
        events.sort(key=lambda e: e["start_dt"])

        # Remove helper key
        for e in events:
            e.pop("start_dt", None)

        return {
            "events": events[:10],
            "visible": True
        }

    except Exception as e:
        return {
            "error": f"Calendar error: {e}",
            "visible": False
        }


# ---------------------------------------------------------------
# RUN THE SERVER
# ---------------------------------------------------------------
if __name__ == "__main__":
    # Runs on all network interfaces so the mirror + controller can connect
    socketio.run(app, host='0.0.0.0', port=5000)
