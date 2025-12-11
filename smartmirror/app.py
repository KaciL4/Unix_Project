from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
import requests
import os
from datetime import datetime, timedelta, time
from icalendar import Calendar

# QR code generation for controller URL
from io import BytesIO
from flask import send_file
import qrcode

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SMARTMIRROR_SECRET_KEY", os.urandom(24))
socketio = SocketIO(app, cors_allowed_origins=[], async_mode="eventlet")


QR_TARGET_URL = "http://smartmirror.local:5000/controller"  

@app.route("/controller_qr")
def controller_qr():
    """Return a QR code PNG that encodes the controller URL."""
    img = qrcode.make(QR_TARGET_URL)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

# Custom calendar ICS link
CONFIG_PATH = os.path.expanduser("~/.config/smartmirror/config.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            import json
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

config = load_config()
CALENDAR_URL = config.get("calendar_url") or os.environ.get(
    "SMARTMIRROR_CAL_URL",
    "https://YOUR_DEFAULT_ICS_URL.ics"
)

DEFAULT_LAT = 45.5017
DEFAULT_LON = -73.5673
DEFAULT_CITY = "Current Location"

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
    view = data.get('view', 'home')
    state['view'] = view

    # Hide weather and calendar when resetting to home
    if view == 'home':
        if state['weather']:
            state['weather']['visible'] = False
        if state['calendar']:
            state['calendar']['visible'] = False

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
    lat = state['location']['lat']
    lon = state['location']['lon']
    weather_data = fetch_weather(lat=lat, lon=lon)
    weather_data['visible'] = True
    state['weather'] = weather_data

    socketio.emit('state_update', state)
    return jsonify({'ok': True, 'weather': weather_data})

@app.route('/api/toggle_weather', methods=['POST'])
def api_toggle_weather():
    """Toggle weather visibility. If turning on, refresh weather."""
    visible = state['weather'].get('visible', False)

    if visible:
        # Turn OFF
        state['weather']['visible'] = False
    else:
        # Turn ON and fetch latest weather for current location
        lat = state['location']['lat']
        lon = state['location']['lon']
        weather_data = fetch_weather(lat=lat, lon=lon)
        weather_data['visible'] = True
        state['weather'] = weather_data

    socketio.emit('state_update', state)
    return jsonify({'ok': True, 'visible': state['weather']['visible']})

@app.route('/api/toggle_calendar', methods=['POST'])
def api_toggle_calendar():
    """Toggle calendar visibility. If turning on, refresh calendar."""
    visible = state['calendar'].get('visible', False)

    if visible:
        # Turn OFF
        state['calendar']['visible'] = False
    else:
        # Turn ON and fetch latest calendar
        calendar_data = fetch_calendar()
        calendar_data['visible'] = True
        state['calendar'] = calendar_data

    socketio.emit('state_update', state)
    return jsonify({'ok': True, 'visible': state['calendar']['visible']})

@app.route('/api/fetch_calendar', methods=['POST'])
def api_fetch_calendar():
    calendar_data = fetch_calendar()
    calendar_data['visible'] = True
    state['calendar'] = calendar_data

    # Don't hide weather - allow both to show

    socketio.emit('state_update', state)
    return jsonify({'ok': True, 'calendar': calendar_data})

@app.route('/api/set_calendar_url', methods=['POST'])
def api_set_calendar_url():
    data = request.json or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"ok": False, "error": "No URL provided"}), 400

    # basic validation
    if not (url.startswith("http://") or url.startswith("https://")):
        return jsonify({"ok": False, "error": "Invalid URL"}), 400

    # update global
    global CALENDAR_URL, config
    CALENDAR_URL = url
    config["calendar_url"] = url

    # persist to file
    try:
        import json, os
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    return jsonify({"ok": True})

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

@socketio.on('set_brightness')
def handle_brightness(data):
    state['brightness'] = int(data['brightness'])
    socketio.emit('state_update', state)

# Socket event to update location 
@socketio.on('update_location')
def on_update_location(data):
    lat = data.get('lat')
    lon = data.get('lon')

    try:
        lat = float(lat)
        lon = float(lon)
    except:
        return

    state['location']['lat'] = lat
    state['location']['lon'] = lon

    # Refresh weather immediately when location changes
    updated = fetch_weather(lat=lat, lon=lon)
    updated['visible'] = True
    state['weather'] = updated

    socketio.emit('state_update', state)

# Weather fetching helper function
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

# Calendar ICS URL (can be overridden)
CALENDAR_URL = os.environ.get(
    "SMARTMIRROR_CAL_URL",
    "https://calendar.google.com/calendar/ical/32c5af1c5ed39b8b04b8fc0dbc91fddd21632491bf2a70c459f3705d325d9390%40group.calendar.google.com/private-1d0b7b86956b92f5336e2000d4ffedef/basic.ics"
)

# Calendar fetching helper function
def fetch_calendar():
    try:
        resp = requests.get(CALENDAR_URL, timeout=10)
        resp.raise_for_status()
        cal = Calendar.from_ical(resp.text)

        now = datetime.now()
        end = now + timedelta(days=7)

        events = []

        for component in cal.walk('vevent'):
            summary = str(component.get('summary', ''))

            dtstart = component.get('dtstart')
            if not dtstart:
                continue
            dtstart = dtstart.dt  # can be date or datetime (maybe tz-aware)

            # Normalize start to a naive datetime
            if isinstance(dtstart, datetime):
                start = dtstart.replace(tzinfo=None)
            else:
                # it's a date (all-day event)
                start = datetime.combine(dtstart, time.min)

            # Filter to the next 7 days
            if not (now <= start <= end):
                continue

            # Pretty formatting
            if isinstance(dtstart, datetime):
                date_str = start.strftime("%Y-%m-%d %H:%M")
            else:
                date_str = start.strftime("%Y-%m-%d (all day)")

            events.append({
                "summary": summary,
                "date": date_str,
                # optional: keep a sortable key
                "start_dt": start,
            })

        # Sort by start time
        events.sort(key=lambda e: e["start_dt"])
        # Remove helper key from final payload
        for e in events:
            e.pop("start_dt", None)

        return {
            "events": events[:10],  # limit to 10
            "visible": True
        }

    except Exception as e:
        return {
            "error": f"Calendar error: {e}",
            "visible": False
        }

# Run the app
if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000)
