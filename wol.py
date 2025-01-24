import json
import tkinter as tk
from tkinter import ttk
import threading
import time
from ping3 import ping
from wakeonlan import send_magic_packet
from datetime import datetime
import concurrent.futures  # 用于线程池

class WOLApplication:
    def __init__(self, root):
        self.root = root
        self.root.title("Wake-on-LAN Manager")
        self.root.geometry("800x600")
        self.root.configure(bg='#f0f0f0')


        self.status_colors = {
            'Online': '#e6ffe6',
            'Offline': '#f0f0f0'
        }

        self.load_config()
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(padx=20, pady=20, fill='both', expand=True)

        self.create_gui()
        self.create_log_area()

        self.ping_thread = threading.Thread(target=self.monitor_devices, daemon=True)
        self.ping_thread.start()

        self.apply_styles()

    def apply_styles(self):
        style = ttk.Style()
        style.configure('Treeview',
                        background='#ffffff',
                        fieldbackground='#ffffff',
                        rowheight=25)

        style.configure('Treeview.Heading',
                        background='#4a90e2',
                        foreground='white',
                        relief='flat',
                        font=('Arial', 10, 'bold'))

        style.configure('TFrame', background='#f0f0f0')

        style.configure('Log.TLabel',
                        background='#f0f0f0',
                        font=('Arial', 10))

        style.configure('Subtitle.TLabel',
                        background='#f0f0f0',
                        font=('Arial', 9, 'italic'),
                        foreground='#666666')

    def load_config(self):
        try:
            with open('WOL-config.json', 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            self.config = {"devices": []}
            print("The configuration file does not exist, please create it(WOL-config.json)")

    def create_gui(self):

        title_label = ttk.Label(
            self.main_frame,
            text="Device Management Console",
            font=('Arial', 16, 'bold'),
            background='#f0f0f0'
        )
        title_label.pack(pady=(0, 5))


        subtitle_label = ttk.Label(
            self.main_frame,
            text="Double-click on an offline device to transmit Wake-on-LAN magic packet",
            style='Subtitle.TLabel'
        )
        subtitle_label.pack(pady=(0, 20))


        table_frame = ttk.Frame(self.main_frame)
        table_frame.pack(fill='both', expand=True)


        columns = ('Name', 'IP Address', 'MAC Address', 'Status', 'Action')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=10)

        column_widths = {
            'Name': 150,
            'IP Address': 150,
            'MAC Address': 180,
            'Status': 100,
            'Action': 100
        }

        for col, width in column_widths.items():
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor='center')


        self.tree.tag_configure('online', background=self.status_colors['Online'])
        self.tree.tag_configure('offline', background=self.status_colors['Offline'])


        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')


        for device in self.config['devices']:
            self.tree.insert('', 'end', values=(
                device['name'],
                device['ip'],
                device['mac'],
                'Detecting...',
                'Waiting'
            ))

    def create_log_area(self):
        log_frame = ttk.Frame(self.main_frame)
        log_frame.pack(fill='x', pady=(20, 0))

        self.log_label = ttk.Label(
            log_frame,
            text="System Log: Ready for operations",
            style='Log.TLabel',
            wraplength=700
        )
        self.log_label.pack(anchor='w')

        self.time_label = ttk.Label(
            log_frame,
            text="",
            style='Log.TLabel'
        )
        self.time_label.pack(anchor='w')

    def update_log(self, message):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_label.config(text=f"System Log: {message}")
        self.time_label.config(text=f"Timestamp: {current_time}")

    def monitor_devices(self):
        while True:
            devices = self.tree.get_children()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_to_item = {
                    executor.submit(self.ping_device, self.tree.item(item)['values'], item): item for item in devices
                }
                for future in concurrent.futures.as_completed(future_to_item):
                    item = future_to_item[future]
                    try:
                        status, action, tag = future.result()
                        self.tree.set(item, 3, status)
                        self.tree.set(item, 4, action)
                        self.tree.item(item, tags=(tag,))
                    except Exception as e:
                        print(f"Error updating device {item}: {e}")

            time.sleep(5)  # 间隔时间

    def ping_device(self, values, item):
        """
        单独 ping 一个设备并返回状态信息。
        """
        ip = values[1]
        try:
            response_time = ping(ip, timeout=1)
            if response_time is None:
                return 'Offline', 'Wake', 'offline'
            else:
                return 'Online', '-', 'online'
        except Exception as e:
            print(f"Ping error for {ip}: {e}")
            return 'Error', 'Wake', 'offline'

    def wake_device(self, mac_address, device_name):
        try:
            send_magic_packet(mac_address)
            self.update_log(f"Magic packet has been transmitted to {device_name} ({mac_address})")
            return True
        except Exception as e:
            self.update_log(f"Error sending magic packet to {device_name}: {str(e)}")
            return False


def main():
    root = tk.Tk()
    app = WOLApplication(root)

    def on_click(event):
        item = app.tree.selection()[0]
        values = app.tree.item(item)['values']
        if values[3] == 'Offline':
            mac = values[2]
            name = values[0]
            app.wake_device(mac, name)

    app.tree.bind('<Double-1>', on_click)

    root.mainloop()


if __name__ == "__main__":
    main()
