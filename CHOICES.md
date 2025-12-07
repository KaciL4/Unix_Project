# Platform Choosen 🌐

We chose to use a **Raspberry Pi 5** instead of a Virtual Machine because it's more efficient, uses less power, and it makes the project feel like a real embedded system. 
Although a Virtual Machine is easier to test and fast to reset it something breaks, a Raspberry Pi is more realistic for a physical smart mirror.
***
## Distribution Options 📋

We chose Raspberry Pi OS (64-bit) with Desktop for installation via the Raspberry Pi Imager. 
The Desktop environment provides a necessary Graphical User Interface (GUI) for initial setup, troubleshooting the display, and configuring 
the Chromium Kiosk mode, offering better debugging capabilities compared to the lightweight, but more labor-intensive, Pi OS Lite version.
***
## Autostart Method ⚙️

We chose to use a systemd service since .bashrc only works after login, so it's not reliable, amd cron doesn't restart on crash. 
A systemd is cleaner, it handles auto-restart, and logs errors. so it's the most professional and stable way.
***
## Display Software 💻
The mirror interface use a Python script to generate a local HTML page displayed in Chromium Kiosk mode. 
This gives us full control, and Kiosk mode is easy to autostart. This approach provides maximum flexibility 
using web technologies (HTML/CSS/JavaScript) while Kiosk mode ensures a clean, distraction-free display without 
browser controls. The JavaScript client communicates dynamically with the backend via Socket.IO for real-time updates.

***
## Task Automating ⚡

Tasks are segregated based on function:

- **System Tasks** (e.g., updates, maintenance, cleanup) are handled using Bash scripts for efficient, low-level system interaction.

- **Application Logic** (e.g., handling API calls, data processing, state management) is managed exclusively within the Python backend.
***
## Scheduling 🗓️

To manage recurring application tasks, such as fetching weather data or refreshing quotes, Flask-APScheduler is used. This Python 
library integrates directly into the running Flask application process, providing a robust, centralized, and language-native solution 
for time-based tasks that benefits directly from the stability and auto-restart capabilities offered by the encompassing systemd service.
