from pywebio.input import input, input_group, NUMBER, PASSWORD
from pywebio.output import put_text, put_table, put_markdown
from pywebio import start_server
import requests
from bs4 import BeautifulSoup
import re
import asyncio
import socket
import webbrowser

def get_free_port():
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def main():
    data = input_group("本软件仅供科学研究，请勿分享或另做其他用途￼", [
        input("用户名（学号）", name='username'),
        input("密码", type=PASSWORD, name='password'),
        input("课号（1 表示第一课）", type=NUMBER, name='lesson')
    ])

    session = requests.Session()

    login_page = session.get("https://lms.jp-sji.org/moodle/login/index.php")
    soup = BeautifulSoup(login_page.text, "html.parser")
    logintoken = soup.find("input", {"name": "logintoken"})["value"]

    login_data = {
        "anchor": "",
        "logintoken": logintoken,
        "username": data['username'],
        "password": data['password'],
        "rememberusername": 1
    }
    login_resp = session.post("https://lms.jp-sji.org/moodle/login/index.php", data=login_data)
    if "loginerrors" in login_resp.text:
        put_text("登录失败，请检查账号密码。")
        return

    sesskey_match = re.search(r"sesskey=([a-zA-Z0-9]+)", login_resp.text)
    sesskey = sesskey_match.group(1) if sesskey_match else ""
    if not sesskey:
        put_text("登录成功但未提取到 sesskey。")
        return

    a = 230 + data['lesson']
    scoid = 460 + data['lesson'] * 2
    scorm_url = f"https://lms.jp-sji.org/moodle/mod/scorm/player.php?a={a}&currentorg=sco1&scoid={scoid}&sesskey={sesskey}&display=popup&mode=normal"

    headers = {
        "User-Agent": "Mozilla/5.0 (iPad)",
        "Referer": "https://lms.jp-sji.org/moodle/mod/scorm/view.php?id=18606"
    }
    scorm_resp = session.get(scorm_url, headers=headers)
    html = scorm_resp.text.replace('\\n', '\n').replace('\\', '')

    student_responses = re.findall(r'cmi\.interactions_\d+\.student_response\s*=\s*"([^"]+)"', html)
    if not student_responses:
        put_text("未找到 student_response，请确认课程是否加载。")
        return

    for i, sr in enumerate(student_responses):
        answers = []
        parts = sr.split('--')[0].strip().split(',')
        for item in parts:
            match = re.match(r'(\d+):([a-zA-Z\?])(?:\[(\w)\])?', item.strip())
            if match:
                qnum, chosen, correct = match.groups()
                # 使用提供的正确答案（即使用户未作答）
                if correct:
                    answers.append([qnum, correct])
                else:
                    answers.append([qnum, chosen])
        put_markdown(f"### 第 {i+1} 组题目正确答案")
        put_table([["题号", "正确答案"]] + answers)

        
        
if __name__ == '__main__':
    asyncio.set_event_loop(asyncio.new_event_loop())
    port = get_free_port()
    host_ip = get_local_ip()
    url = f"http://{host_ip}:{port}"
    try:
        webbrowser.open(url)
    except:
        pass
    start_server(main, port=port, cdn=False, host='0.0.0.0')
