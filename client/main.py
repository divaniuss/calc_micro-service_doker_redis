import customtkinter as ctk
import requests


#local test
AUTH_URL = "http://127.0.0.1:8000"
CALC_URL = "http://127.0.0.1:8001"


#docker + nginx
# AUTH_URL = "http://127.0.0.1"
# CALC_URL = "http://127.0.0.1"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class CalcApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Calc")
        self.geometry("400x400")
        self.token = None
        self.show_auth_frame()

    def show_auth_frame(self):
        for widget in self.winfo_children():
            widget.destroy()

        self.user_entry = ctk.CTkEntry(self, placeholder_text="username", width=200)
        self.user_entry.pack(pady=(50, 10))

        self.pass_entry = ctk.CTkEntry(self, placeholder_text="password", show="*", width=200)
        self.pass_entry.pack(pady=10)

        ctk.CTkButton(self, text="Login", command=self.login).pack(pady=5)
        ctk.CTkButton(self, text="Register", command=self.register).pack(pady=5)

    def login(self):
        username = self.user_entry.get()
        password = self.pass_entry.get()

        if not username or not password:
            print("validation failed")
            return

        try:
            res = requests.post(
                f"{AUTH_URL}/login",
                json={"username": username, "password": password},
                timeout=5
            )
            if res.status_code == 200:
                print("login success")
                self.token = res.json().get("access_token")
                self.show_calc_frame()
            else:
                print("auth failed")
        except Exception:
            print("server error")

    def register(self):
        username = self.user_entry.get()
        password = self.pass_entry.get()

        if not username or not password:
            print("validation failed")
            return

        try:
            res = requests.post(
                f"{AUTH_URL}/register",
                json={"username": username, "password": password},
                timeout=5
            )
            if res.status_code == 200:
                print("register success")
            else:
                print("register failed")
        except Exception:
            print("server error")

    def show_calc_frame(self):
        for widget in self.winfo_children():
            widget.destroy()

        self.calc_entry = ctk.CTkEntry(self, placeholder_text="expression", width=250)
        self.calc_entry.pack(pady=(50, 20))

        ctk.CTkButton(self, text="Calculate", command=self.calculate).pack(pady=10)

        self.result_label = ctk.CTkLabel(self, text="Result: ", font=("Arial", 18))
        self.result_label.pack(pady=20)

    def calculate(self):
        expr = self.calc_entry.get()

        if not expr:
            print("validation failed")
            return

        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            res = requests.post(
                f"{CALC_URL}/calc",
                json={"expression": expr},
                headers=headers,
                timeout=5
            )
            if res.status_code == 200:
                print("calc success")
                ans = res.json().get("result")
                self.result_label.configure(text=f"Result: {ans}")
            else:
                print("calc error")
        except Exception:
            print("server error")



app = CalcApp()
app.mainloop()