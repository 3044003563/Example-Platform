# danmaku_server_with_consent.py
# B端：带授权确认的弹幕显示服务
# 运行示例: python danmaku_server_with_consent.py --port 9009

import socket, threading, argparse, json, queue
import tkinter as tk
from tkinter import messagebox, colorchooser

# 全局授权缓存：存放已允许的客户端 IP
ALLOWED_IPS = set()

# ---------- 弹幕显示窗口 ----------
class DanmakuWindow:
    def __init__(self, width=800, height=300, default_duration=8, default_fontsize=22, default_color="#AAAAAA"):
        self.width = width
        self.height = height
        self.default_duration = default_duration
        self.fontsize = default_fontsize
        self.color = default_color

        self.root = tk.Tk()
        self.root.title("弹幕显示端（B）")
        self.root.overrideredirect(True)
        self.root.geometry(f"{width}x{height}+100+100")
        self.root.attributes("-topmost", True)

        try:
            self.root.attributes("-transparentcolor", "black")
            self.root.configure(bg="black")
            self.canvas_bg = "black"
        except Exception:
            self.root.configure(bg="")
            self.canvas_bg = "white"

        self.canvas = tk.Canvas(self.root, bg=self.canvas_bg, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # 允许拖动窗口
        self._drag_data = {"x": 0, "y": 0}
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)

        self.items = {}
        self.ctrl_win = None

    def show_message(self, text, duration=None, fontsize=None, color=None):
        duration = duration or self.default_duration
        fontsize = fontsize or self.fontsize
        color = color or self.color
        w = self.canvas.winfo_width() or self.width
        h = self.canvas.winfo_height() or self.height
        x = w // 2
        y = h // 2
        item = self.canvas.create_text(x, y, text=text, anchor="center",
                                       fill=color, font=("Microsoft YaHei", int(fontsize)))
        after_id = self.root.after(int(duration * 1000), lambda i=item: self._remove_item(i))
        self.items[item] = after_id
        print(text)

    def _remove_item(self, item):
        aid = self.items.pop(item, None)
        if aid:
            try:
                self.root.after_cancel(aid)
            except Exception:
                pass
        try:
            self.canvas.delete(item)
        except Exception:
            pass

    def _on_press(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _on_drag(self, event):
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")

    def start_mainloop(self):
        self.root.mainloop()

    def open_control_panel(self):
        if hasattr(self, "ctrl_win") and self.ctrl_win and tk.Toplevel.winfo_exists(self.ctrl_win):
            return

        self.ctrl_win = tk.Toplevel()
        self.ctrl_win.title("控制面板")
        self.ctrl_win.geometry("320x240")
        self.ctrl_win.attributes("-topmost", True)
        self.ctrl_win.configure(bg="#f5f5f5")

        font_style = ("Microsoft YaHei", 10)

        tk.Label(self.ctrl_win, text="默认停留时间（秒）:", bg="#f5f5f5", font=font_style).pack(anchor="w", padx=8, pady=2)
        dur_var = tk.StringVar(value=str(self.default_duration))
        e1 = tk.Entry(self.ctrl_win, textvariable=dur_var, font=font_style)
        e1.pack(fill="x", padx=8)

        tk.Label(self.ctrl_win, text="字体大小:", bg="#f5f5f5", font=font_style).pack(anchor="w", padx=8, pady=2)
        fs_var = tk.StringVar(value=str(self.fontsize))
        e2 = tk.Entry(self.ctrl_win, textvariable=fs_var, font=font_style)
        e2.pack(fill="x", padx=8)

        tk.Label(self.ctrl_win, text="字体颜色:", bg="#f5f5f5", font=font_style).pack(anchor="w", padx=8, pady=2)
        color_btn = tk.Button(
            self.ctrl_win, text="选择颜色",
            command=lambda: self._choose_color(),
            bg="#e0e0e0", font=font_style, relief="flat"
        )
        color_btn.pack(padx=8, pady=6, fill="x")

        def preview_now():
            try:
                dur = float(dur_var.get())
                fs = int(fs_var.get())
                color = self.color
                self.show_message("示例文字", duration=dur, fontsize=fs, color=color)
            except Exception as e:
                print("[preview] error:", e)

        preview_btn = tk.Button(
            self.ctrl_win, text="预览效果",
            command=preview_now,
            bg="#dcdcdc", font=font_style, relief="flat"
        )
        preview_btn.pack(pady=4, padx=8, fill="x")

        def apply_and_close():
            try:
                self.default_duration = float(dur_var.get())
            except:
                pass
            try:
                self.fontsize = int(fs_var.get())
            except:
                pass
            self.ctrl_win.destroy()

        apply_btn = tk.Button(
            self.ctrl_win, text="应用并关闭",
            command=apply_and_close,
            bg="#bdbdbd", font=font_style, relief="flat"
        )
        apply_btn.pack(pady=6, padx=8, fill="x")

    def _choose_color(self):
        c = colorchooser.askcolor(initialcolor=self.color)
        if c and c[1]:
            self.color = c[1]


# ---------- Server 网络与授权逻辑 ----------
def server_listen_thread(listen_ip, port, on_incoming_connection, stop_event):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((listen_ip, port))
    srv.listen(1)
    print(f"[server] listening on {listen_ip}:{port}")
    while not stop_event.is_set():
        try:
            srv.settimeout(1.0)
            conn, addr = srv.accept()
        except Exception:
            continue
        print(f"[server] new connection from {addr}")
        on_incoming_connection.put((conn, addr))
    srv.close()
    print("[server] listener stopped")


def handle_connections(incoming_queue, danmaku_win, stop_event, consent_timeout=30):
    """
    只在第一次连接时弹出授权确认；同一 IP 之后自动允许。
    """
    root = danmaku_win.root

    def poll():
        try:
            while True:
                conn, addr = incoming_queue.get_nowait()
                client_ip = addr[0]
                ip_str = f"{client_ip}:{addr[1]}"

                # ✅ 如果该 IP 已授权，不再询问
                if client_ip in ALLOWED_IPS:
                    print(f"[server] {client_ip} 已授权，直接接收弹幕。")
                    t = threading.Thread(
                        target=connection_receive_loop,
                        args=(conn, addr, danmaku_win, stop_event),
                        daemon=True
                    )
                    t.start()
                    continue

                # 🚪 首次连接弹出确认
                allow = messagebox.askyesno(
                    "连接请求",
                    f"检测到来自 {ip_str} 的连接请求。\n是否允许接收弹幕？"
                )

                if allow:
                    ALLOWED_IPS.add(client_ip)
                    danmaku_win.root.after(
                        0,
                        lambda: danmaku_win.show_message(
                            f"✅ 已授权 {client_ip}",
                            duration=2,
                            color="lime"
                        )
                    )
                    print(f"[server] {client_ip} 已加入授权列表。")
                    t = threading.Thread(
                        target=connection_receive_loop,
                        args=(conn, addr, danmaku_win, stop_event),
                        daemon=True
                    )
                    t.start()
                else:
                    conn.close()
                    danmaku_win.root.after(
                        0,
                        lambda: danmaku_win.show_message(
                            f"❌ 拒绝连接 {client_ip}",
                            duration=2,
                            color="red"
                        )
                    )
        except queue.Empty:
            pass

        if not stop_event.is_set():
            root.after(200, poll)

    root.after(200, poll)


def connection_receive_loop(conn, addr, danmaku_win, stop_event):
    with conn:
        try:
            buf = b""
            while not stop_event.is_set():
                data = conn.recv(4096)
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    try:
                        payload = json.loads(line.decode("utf-8", errors="ignore"))
                        text = payload.get("text", "").strip()
                        fontsize = payload.get("fontsize", danmaku_win.fontsize)
                        duration = payload.get("duration", danmaku_win.default_duration)
                        color = payload.get("color", danmaku_win.color)
                        if text:
                            danmaku_win.root.after(
                                0, lambda t=text, d=duration, f=fontsize, c=color:
                                danmaku_win.show_message(t, d, f, c)
                            )
                    except Exception as e:
                        print("[server] JSON解析错误:", e)
        except Exception as e:
            print("[server] connection error:", e)
    print(f"[server] connection {addr} closed")



# ---------- 主入口 ----------
def start_server_gui(listen_ip, port):
    dan = DanmakuWindow()
    incoming_q = queue.Queue()
    stop_ev = threading.Event()

    t = threading.Thread(target=server_listen_thread, args=(listen_ip, port, incoming_q, stop_ev), daemon=True)
    t.start()
    handle_connections(incoming_q, dan, stop_ev, consent_timeout=30)

    dan.canvas.bind("<Double-Button-1>", lambda e: dan.open_control_panel())

    messagebox.showinfo("提示", f"弹幕显示端已启动（端口 {port}）。当有远端连接请求时会询问确认。")
    try:
        dan.start_mainloop()
    finally:
        stop_ev.set()
        print("[server] 程序已退出。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0", help="绑定地址")
    parser.add_argument("--port", type=int, default=9009, help="监听端口")
    args = parser.parse_args()
    start_server_gui(args.host, args.port)
