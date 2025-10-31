import tkinter as tk
from tkinter import colorchooser, messagebox
import socket
import threading
import json

class DanmakuClientGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("弹幕控制端（A端）")
        self.root.geometry("460x360")
        self.root.configure(bg="#f5f5f5")
        self.root.minsize(400, 320)     # 限制最小尺寸
        self.root.resizable(True, True) # ✅ 可自由调整窗口大小

        font_style = ("Microsoft YaHei", 10)

        # ======= 网格布局配置（让组件自动伸缩） =======
        self.root.columnconfigure(0, weight=1)

        # ===== 目标 IP =====
        tk.Label(self.root, text="目标 IP 地址：", bg="#f5f5f5", font=font_style).grid(row=0, column=0, sticky="w", padx=12, pady=2)
        self.ip_var = tk.StringVar(value="127.0.0.1")
        tk.Entry(self.root, textvariable=self.ip_var, font=font_style).grid(row=1, column=0, sticky="ew", padx=12)

        # ===== 端口 =====
        tk.Label(self.root, text="端口号：", bg="#f5f5f5", font=font_style).grid(row=2, column=0, sticky="w", padx=12, pady=2)
        self.port_var = tk.StringVar(value="9009")
        tk.Entry(self.root, textvariable=self.port_var, font=font_style).grid(row=3, column=0, sticky="ew", padx=12)

        # ===== 弹幕内容 =====
        tk.Label(self.root, text="弹幕内容：", bg="#f5f5f5", font=font_style).grid(row=4, column=0, sticky="w", padx=12, pady=2)
        self.msg_var = tk.StringVar()
        tk.Entry(self.root, textvariable=self.msg_var, font=("Microsoft YaHei", 11)).grid(row=5, column=0, sticky="ew", padx=12, pady=4)

        # ===== 字体大小 =====
        tk.Label(self.root, text="字体大小：", bg="#f5f5f5", font=font_style).grid(row=6, column=0, sticky="w", padx=12, pady=2)
        self.fontsize_var = tk.IntVar(value=22)
        tk.Entry(self.root, textvariable=self.fontsize_var, font=font_style).grid(row=7, column=0, sticky="ew", padx=12)

        # ===== 停留时间 =====
        tk.Label(self.root, text="停留时间（秒）：", bg="#f5f5f5", font=font_style).grid(row=8, column=0, sticky="w", padx=12, pady=2)
        self.duration_var = tk.IntVar(value=10)
        tk.Scale(self.root, from_=1, to=30, orient="horizontal", variable=self.duration_var, bg="#f5f5f5").grid(row=9, column=0, sticky="ew", padx=12)

        # ===== 字体颜色 =====
        self.color = "gray"
        color_btn = tk.Button(self.root, text="选择颜色", bg="#e0e0e0", font=font_style, relief="flat", command=self.choose_color)
        color_btn.grid(row=10, column=0, sticky="ew", padx=12, pady=4)

        # ===== 发送按钮 =====
        send_btn = tk.Button(
            self.root,
            text="发送弹幕 🚀",
            bg="#4caf50",
            fg="white",
            font=("Microsoft YaHei", 11, "bold"),
            relief="flat",
            command=self.send_message
        )
        send_btn.grid(row=11, column=0, sticky="ew", padx=12, pady=12)

        # ===== 拖动支持 =====
        self.root.bind("<ButtonPress-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)

        self.sock = None

    # 拖动窗口（可选特性）
    def start_move(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def do_move(self, event):
        x = self.root.winfo_x() + event.x - self._drag_start_x
        y = self.root.winfo_y() + event.y - self._drag_start_y
        self.root.geometry(f"+{x}+{y}")

    # 颜色选择器
    def choose_color(self):
        color = colorchooser.askcolor(title="选择字体颜色")
        if color[1]:
            self.color = color[1]

    # 建立连接
    def connect(self, ip, port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ip, port))
            return s
        except Exception as e:
            messagebox.showerror("连接失败", f"无法连接到 {ip}:{port}\n错误：{e}")
            return None

    # 发送弹幕
    def send_message(self):
        ip = self.ip_var.get().strip()
        port = int(self.port_var.get())
        msg = self.msg_var.get().strip()
        if not msg:
            messagebox.showwarning("提示", "请输入弹幕内容！")
            return

        fontsize = self.fontsize_var.get()
        duration = self.duration_var.get()
        color = self.color

        data = {
        "type": "msg",
        "text": msg,
        "fontsize": fontsize,
        "duration": duration,
        "color": color
    }

        def thread_send():
            s = self.connect(ip, port)
            if not s:
                return
            try:
                s.sendall((json.dumps(data) + "\n").encode("utf-8"))

                s.close()
                print(f"[client] sent: {data}")
            except Exception as e:
                messagebox.showerror("发送失败", str(e))

        threading.Thread(target=thread_send, daemon=True).start()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = DanmakuClientGUI()
    app.run()
