# Steps to Set Up the Smart Mirror 🪜

## 🛠️ Phase 1: Preparation (The SD Card) 

### 1. Gather Required Items 🛒

 - MicroSD Card: At least 16GB (32GB or more is recommended).
 - Computer: A Windows, macOS, or Linux machine to perform the flashing.
 - MicroSD Card Reader: To connect the card to your computer.
 - Raspberry Pi Imager Software: The official tool for installing the OS.
 - 
### 2. Download and Install Raspberry Pi Imager 💾

  Go to the official Raspberry Pi website and download the Raspberry Pi Imager software for your computer's operating system (Windows, macOS, or Linux) and install it.
  
### 3. Choose the OS and Device 🔧

- Launch the Raspberry Pi Imager software.
- Click "CHOOSE DEVICE" and select "Raspberry Pi 5".
- Click "CHOOSE OS" and select "Raspberry Pi OS (64-bit)". Since your smart mirror project uses Chromium Kiosk mode, select the version with Desktop Environment (e.g., "Raspberry Pi OS (64-bit) (with Desktop)").
  
### 4. Configure OS Settings (Optional but Recommended) ⚙️

 - Click the gear icon (settings) in the bottom right. This allows you to pre-configure system settings. It's helpful to enable SSH and set a username/password now, though, for a smart mirror, the most critical step is setting the hostname and Wi-Fi.
 - Set Hostname: (e.g., smartmirror).
 - Set Username and Password: (e.g., pi and your password).
 - Configure Wi-Fi: Enter your network name (SSID) and password.
 - Set Locale settings: Select your keyboard layout and timezone.
 - Click SAVE.
   
### 5. Flash the SD Card  ⚡

- Click "CHOOSE STORAGE" and select your MicroSD card from the list. CAUTION: Double-check that you choose the correct drive, as this step will erase all data on it.
- Click "WRITE".
- The Imager will download the OS, flash it to the SD card, and verify the write process. This may take several minutes.
- Once complete, the Imager will notify you that you can remove the SD card.
***

## 🔌 Phase 2: Connecting and Initial Boot

### 1. Connect Hardware 🔗

 - Insert the MicroSD Card: Carefully insert the newly flashed MicroSD card into the MicroSD slot on your Raspberry Pi 5.
 - Connect the DSI Display: Since your project uses a DSI display, connect the ribbon cable from the display to the appropriate DSI connector on the Raspberry Pi 5 board. Ensure the cable is properly seated and the   locking mechanism is secured.
 - Connect Peripherals (Optional): If you didn't pre-configure Wi-Fi, you may need to temporarily connect a keyboard and mouse (via USB).
- Connect Power: Plug the official USB-C power supply (required for Pi 5) into the power port.
  
### 2. Initial Boot ▶️

  As soon as power is connected, the Raspberry Pi 5 will automatically power on.
  The screen should light up, and you will see the boot sequence loading.
  
  The Raspberry Pi OS Desktop environment will load after the boot process is complete.
  If you set up an account in the Imager, the screen will either go straight to the desktop or prompt you to log in with the username/password you chose.
  
  The Raspberry Pi is now successfully booted to the desktop, providing the necessary graphical environment (the GUI) to run your custom Chromium Kiosk smart mirror application.
***

## 🐍 Phase 3: Install Required Dependencies

### 1. Update System 🔄
```bash
sudo apt update && sudo apt upgrade -y
```
### 2. Install Packages
```bash
sudo apt install -y python3 python3-venv python3-pip   
```
***

## 📥 Phase 4: Clone the Smart Mirror Repository
```bash
git clone https://github.com/KaciL4/Unix_Project.git
cd smartmirror
```
***

## 🧪 Phase 5: Create Python Virtual Environment

### 1. Create a virtual environment
```bash
python3 -m venv venv
```

### 2. Activate it
```bash
source venv/bin/activate
```
### 3. Install dependencies
```bash
pip install -r requirements.txt
```
***

## ▶️ Phase 6: Test the App

### 1. Run
```bash
python app.py
```
## 2. On the Pi, on your browser
```bash
http://localhost:5000/display
```
### 3. On the same network, on your phone:
```bash
http://<PI-IP-ADDRESS>:5000/controller
```
Press Ctrl + C in the terminal to exit.
***

## ⚙️ Phase 7: Create a systemd Service (Auto-Start Backend)

### 1. Create service file
```bash
sudo nano /etc/systemd/system/smartmirror.service
```

Paste:
```bash
 [Unit]
 Description=Smart Mirror Backend
 After=network.target
 
 [Service]
 User=<YOUR-USERNAME>
 WorkingDirectory=/home/<YOUR-USERNAME>/smartmirror
 ExecStart=/home/<YOUR-USERNAME>/smartmirror/venv/bin/python /home/<YOUR-USERNAME>/smartmirror/app.py
 Restart=always
 
 [Install]
 WantedBy=multi-user.target
```
### 2. Enable service
```bash
sudo systemctl daemon-reload
sudo systemctl enable smartmirror.service
sudo systemctl start smartmirror.service
```

### 3. Check Status
```bash
sudo systemctl status smartmirror.service
```
***

## 🖥️ Phase 8: Set Up Chromium Kiosk Mode

### 1. Create the kiosk script
```bash
nano /home/<YOUR-USERNAME>/start-kiosk.sh
```

Paste:
```bash
#!/bin/bash
sleep 5
xset s off
xset -dpms
xset s noblank

chromium \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --kiosk http://localhost:5000/display
```

Make it executable:
```bash
chmod +x /home/<YOUR-USERNAME>/start-kiosk.sh
```

## 2. Create Autostart Entry
```bash
mkdir -p /home/<YOUR-USERNAME>/.config/autostart
nano /home/<YOUR-USERNAME>/.config/autostart/smartmirror-kiosk.desktop
```

Paste:
```bash
[Desktop Entry]
Type=Application
Name=SmartMirror Kiosk
Exec=/home/<YOUR-USERNAME>/start-kiosk.sh
X-LXDE-Autostart-enabled=true
```
***

## ✨ Phase 9: Reboot and Verify

```bash
sudo reboot
```

On boot, the Pi should:
 1. Start the backend (systemd)
 2. Load the desktop
 3. Run your kiosk script
 4. Show the Smart Mirror interface full screen
 
## 🧯 Phase 10: Troubleshooting

### If the display remains blank:
```bash
chmod +x ~/start-kisok.sh
```

Check autostart:
```bash
ls ~/.config/autostart/
```

### If the backend is not running
```bash
journalctl -u smartmirror.service -n 50 --no-pager
sudo systemctl restart smartmirror.service
```

### If the controller won't connect

Ensure that both devices are on the same network and check the IP address:
```bash
hostname -I
```
***

## 🎉 Installation Complete

Your Smart Mirror now:
 - auto-launches on startup
 - runs the Flask + Socket.IO backend
 - opens Chromium in kiosk mode
 - supports controller access from any device on your network

Enjoy! ✨

  
