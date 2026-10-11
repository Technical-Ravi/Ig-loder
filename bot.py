#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import os
import sys
import random
import threading
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, request, render_template_string, jsonify
from rich.console import Console
import pyfiglet
from instagrapi import Client

console = Console()
app = Flask(__name__)
app.secret_key = 'lord-devil-v5-pro-secret'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB max

# Global storage
active_tasks = {}
task_logs = {}
task_threads = {}
task_cookies = {}
nickname_map = {} # Maps user-defined nickname to task_id

# ----------- LOGO -----------
def show_logo():
    os.system('clear' if os.name == 'posix' else 'cls')
    ascii_banner = pyfiglet.figlet_format("LORD DEVIL", font="slant")
    console.print(f"[bold red]{ascii_banner}[/bold red]")
    console.print("[bold cyan]🔥 INSTA TOOLS PRO - V5 🔥[/bold cyan]")
    console.print("[yellow]⚡ 24/7 Non-Stop | Auto-Recovery | Custom Colorful UI[/yellow]\n")

# ----------- INSTAGRAPI LOGIN -----------
def instagram_login_with_cookies(cookies_str):
    """Safely login using cookies and return Client object"""
    cl = Client()
    try:
        cookies_dict = {}
        for cookie in cookies_str.split(';'):
            cookie = cookie.strip()
            if '=' in cookie:
                key, value = cookie.split('=', 1)
                cookies_dict[key.strip()] = value.strip()
        
        sessionid = cookies_dict.get('sessionid', '')
        if sessionid:
            try:
                cl.login_by_sessionid(sessionid)
                return cl
            except Exception:
                pass
        
        try:
            cl.set_settings({
                "user_agent": "Instagram 219.0.0.12.117 Android",
                "device_settings": {
                    "cpu": "64-bit", "dpi": "480dpi", "model": "SM-G973F",
                    "device": "samsung", "resolution": "1080x1920",
                    "app_version": "219.0.0.12.117", "manufacturer": "samsung",
                    "version_code": "291685405"
                }
            })
            for key, value in cookies_dict.items():
                cl.set_cookie(key, value)
            return cl
        except Exception as e:
            return None
    except Exception as e:
        return None

# ----------- LOGGING SYSTEM -----------
def add_log(task_id, message, log_type='info'):
    if task_id not in task_logs:
        task_logs[task_id] = []
    # Keep last 500 logs to prevent memory overflow
    if len(task_logs[task_id]) >= 500:
        task_logs[task_id].pop(0)
    
    timestamp = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    
    task_logs[task_id].append({
        'time': timestamp,
        'message': message,
        'type': log_type,
        'raw': log_entry
    })

# ----------- NON-STOP WORKER THREADS -----------
def messenger_worker(cl, target_type, target_id, prefix, messages, delay, task_id):
    """Handles both Inbox and Group Messaging softly without crashing"""
    try:
        user_id = None
        index = 0
        total = len(messages)
        retry_count = 0
        consecutive_errors = 0
        
        add_log(task_id, "🚀 Task Started Successfully. Initializing...", 'info')
        
        while task_id in active_tasks and active_tasks[task_id].get('running', True):
            try:
                if target_type == 'inbox' and user_id is None:
                    user_id = cl.user_id_from_username(target_id)
                
                msg_content = messages[index]
                full_msg = f"{prefix} {msg_content}".strip()
                
                # Sending logic
                if target_type == 'inbox':
                    cl.direct_send(full_msg, [user_id])
                else:
                    cl.direct_send(full_msg, thread_ids=[target_id])
                
                # Success Logic
                retry_count = 0
                consecutive_errors = 0
                add_log(task_id, f"✅ SUCCESS -> {full_msg[:40]}...", 'success')
                
                index = (index + 1) % total
                
                # Soft Delay Loop (allows quick stopping)
                for _ in range(delay):
                    if not active_tasks.get(task_id, {}).get('running', False): break
                    time.sleep(1)
                
            except Exception as e:
                error_msg = str(e).lower()
                retry_count += 1
                consecutive_errors += 1
                
                if "feedback_required" in error_msg or "spam" in error_msg or "challenge_required" in error_msg or "item_ack" in error_msg:
                    add_log(task_id, "🚫 Action Block (CB) detected! Waiting 5 minutes to auto-recover...", 'error')
                    for _ in range(300):
                        if not active_tasks.get(task_id, {}).get('running', False): break
                        time.sleep(1)
                    continue

                elif "login" in error_msg or "session" in error_msg:
                    add_log(task_id, "🔄 Session issue. Attempting soft re-login...", 'info')
                    try:
                        cookies = task_cookies.get(task_id, '')
                        new_cl = instagram_login_with_cookies(cookies)
                        if new_cl:
                            cl = new_cl
                            user_id = None
                            add_log(task_id, "✅ Re-login successful, resuming task...", 'success')
                            continue
                        else:
                            time.sleep(60)
                            continue
                    except Exception:
                        time.sleep(60)
                        continue
                
                elif "rate" in error_msg or "limit" in error_msg:
                    add_log(task_id, "⏳ Rate Limited. Waiting 2 minutes...", 'error')
                    time.sleep(120)
                    continue
                
                add_log(task_id, f"❌ FAILED -> Error: {str(e)[:60]}", 'error')
                
                if consecutive_errors >= 5:
                    add_log(task_id, "⚠️ Too many errors in a row. Cooling down for 3 minutes...", 'info')
                    time.sleep(180)
                    consecutive_errors = 0
                else:
                    time.sleep(min(30, delay * 2))

    except Exception as e:
        add_log(task_id, f"❌ FATAL ERROR: {str(e)}. Task Stopped.", 'error')
    finally:
        active_tasks.pop(task_id, None)
        add_log(task_id, "🛑 Task has been completely STOPPED.", 'info')

def namechanger_worker(cl, thread_id, prefix, names, delay, task_id):
    """Handles Group Name Changing softly with anti-block safety"""
    try:
        index = 0
        total = len(names)
        retry_count = 0
        consecutive_errors = 0
        
        add_log(task_id, "🚀 Name Changer Started Successfully...", 'info')
        
        while task_id in active_tasks and active_tasks[task_id].get('running', True):
            try:
                base_name = names[index].strip()
                if base_name:
                    new_name = f"{prefix} {base_name}".strip()
                    cl.direct_thread_update_title(thread_id, new_name)
                    
                    retry_count = 0
                    consecutive_errors = 0
                    add_log(task_id, f"✅ SUCCESS -> Changed name to: {new_name[:40]}", 'success')
                    
                    index = (index + 1) % total
                    
                    for _ in range(delay):
                        if not active_tasks.get(task_id, {}).get('running', False): break
                        time.sleep(1)
                    
            except Exception as e:
                error_msg = str(e).lower()
                retry_count += 1
                consecutive_errors += 1
                
                # --- ANTI-BLOCK FIX: Detect Instagram's 'item_ack / something went wrong' error ---
                if "item_ack" in error_msg or "sorry" in error_msg or "something went wrong" in error_msg:
                    add_log(task_id, "🚫 Instagram Temporary Block! Delay is too low. Waiting 5 mins to cool down...", 'error')
                    add_log(task_id, "💡 TIP: Stop the task, and restart with a delay of 60s or more!", 'info')
                    for _ in range(300):
                        if not active_tasks.get(task_id, {}).get('running', False): break
                        time.sleep(1)
                    continue

                if "permission" in error_msg:
                    add_log(task_id, "❌ FAILED -> You are not admin! Cannot change name. Stopping...", 'error')
                    break 
                    
                if "feedback_required" in error_msg or "spam" in error_msg:
                    add_log(task_id, "🚫 Action Block (CB) detected! Waiting 10 minutes...", 'error')
                    for _ in range(600):
                        if not active_tasks.get(task_id, {}).get('running', False): break
                        time.sleep(1)
                    continue

                elif "login" in error_msg or "session" in error_msg:
                    add_log(task_id, "🔄 Session issue. Attempting soft re-login...", 'info')
                    try:
                        cookies = task_cookies.get(task_id, '')
                        new_cl = instagram_login_with_cookies(cookies)
                        if new_cl:
                            cl = new_cl
                            continue
                    except Exception:
                        pass
                    time.sleep(60)
                    continue
                
                add_log(task_id, f"❌ FAILED -> Error: {str(e)[:60]}", 'error')
                
                if consecutive_errors >= 5:
                    add_log(task_id, "⚠️ Facing continuous errors. Pausing for 5 minutes...", 'info')
                    time.sleep(300)
                    consecutive_errors = 0
                else:
                    time.sleep(min(30, delay * 2))

    except Exception as e:
        add_log(task_id, f"❌ FATAL ERROR: {str(e)}. Task Stopped.", 'error')
    finally:
        active_tasks.pop(task_id, None)
        add_log(task_id, "🛑 Task has been completely STOPPED.", 'info')

# ----------- FLASK ROUTES -----------

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/login', methods=['POST'])
def api_login():
    cookies = request.form.get('cookies', '').strip()
    if not cookies:
        return jsonify({'success': False, 'message': 'Cookies required'})
    
    cl = instagram_login_with_cookies(cookies)
    if cl:
        try:
            user_info = cl.account_info()
            dp_url_str = ""
            if user_info.profile_pic_url:
                dp_url_str = str(user_info.profile_pic_url)
                
            return jsonify({
                'success': True,
                'username': str(user_info.username),
                'full_name': str(user_info.full_name) if user_info.full_name else "",
                'dp_url': dp_url_str,
                'cookies': cookies
            })
        except Exception as e:
            return jsonify({'success': False, 'message': f'Login verify failed: {e}'})
    return jsonify({'success': False, 'message': 'Invalid Cookies or Checkpoint'})

@app.route('/api/start', methods=['POST'])
def api_start():
    try:
        tool_type = request.form.get('tool_type')
        cookies = request.form.get('cookies')
        task_nickname = request.form.get('task_nickname', '').strip()
        prefix = request.form.get('prefix', '').strip()
        delay = int(request.form.get('delay', 10))
        
        if not task_nickname:
            return jsonify({'success': False, 'message': 'Task Nickname is required for recovery!'})
            
        if task_nickname in nickname_map:
            old_id = nickname_map[task_nickname]
            if old_id not in active_tasks:
                pass 
            else:
                return jsonify({'success': False, 'message': 'This Nickname is already running a task. Use a different one.'})

        task_id = str(random.randint(100000000000000, 999999999999999))
        
        cl = instagram_login_with_cookies(cookies)
        if not cl:
            return jsonify({'success': False, 'message': 'Session expired. Please login again.'})
            
        messages = []
        if tool_type == 'messenger':
            msg_input_type = request.form.get('msg_input_type')
            if msg_input_type == 'text':
                raw_text = request.form.get('msg_text', '')
                messages = [m.strip() for m in raw_text.split('\n') if m.strip()]
            else:
                if 'msg_file' in request.files:
                    file = request.files['msg_file']
                    content = file.read().decode('utf-8')
                    messages = [m.strip() for m in content.split('\n') if m.strip()]
            
            if not messages:
                return jsonify({'success': False, 'message': 'No messages provided!'})
                
            target_type = request.form.get('target_type') 
            target_id = request.form.get('target_id', '').strip()
            
            task_cookies[task_id] = cookies
            active_tasks[task_id] = {'running': True, 'type': 'messenger'}
            nickname_map[task_nickname] = task_id
            task_logs[task_id] = []
            
            thread = threading.Thread(target=messenger_worker, args=(cl, target_type, target_id, prefix, messages, delay, task_id), daemon=True)
            thread.start()
            task_threads[task_id] = thread
            
        elif tool_type == 'namechanger':
            target_id = request.form.get('target_id', '').strip()
            if 'name_file' in request.files:
                file = request.files['name_file']
                content = file.read().decode('utf-8')
                messages = [m.strip() for m in content.split('\n') if m.strip()]
            
            if not messages:
                return jsonify({'success': False, 'message': 'No names provided in file!'})
                
            task_cookies[task_id] = cookies
            active_tasks[task_id] = {'running': True, 'type': 'namechanger'}
            nickname_map[task_nickname] = task_id
            task_logs[task_id] = []
            
            thread = threading.Thread(target=namechanger_worker, args=(cl, target_id, prefix, messages, delay, task_id), daemon=True)
            thread.start()
            task_threads[task_id] = thread

        return jsonify({'success': True, 'task_id': task_id})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/stop', methods=['POST'])
def api_stop():
    task_id = request.form.get('task_id', '').strip()
    if task_id in active_tasks:
        active_tasks[task_id]['running'] = False
        return jsonify({'success': True, 'message': f'Task {task_id} stopping signal sent.'})
    return jsonify({'success': False, 'message': 'Task ID not found or already stopped.'})

@app.route('/api/recover', methods=['POST'])
def api_recover():
    nickname = request.form.get('nickname', '').strip()
    if nickname in nickname_map:
        return jsonify({'success': True, 'task_id': nickname_map[nickname]})
    return jsonify({'success': False, 'message': 'Nickname not found!'})

@app.route('/api/logs', methods=['GET'])
def api_logs():
    task_id = request.args.get('task_id')
    if task_id in task_logs:
        return jsonify({'success': True, 'logs': task_logs[task_id]})
    return jsonify({'success': False})


# ----------- FRONTEND HTML & JS -----------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔥 LORD DEVIL V5 - PREMIUM 🔥</title>
    
    {% raw %}
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;500;700&display=swap');
        
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Poppins', sans-serif; }
        
        body { 
            background: linear-gradient(135deg, #ffc0cb 25%, #87cefa 75%) !important;
            background-attachment: fixed !important;
            color: #00bfff !important; 
            min-height: 100vh;
            position: relative;
            overflow-x: hidden;
        }

        #particles-js {
            position: fixed;
            width: 100%;
            height: 100%;
            top: 0;
            left: 0;
            z-index: 1;
            pointer-events: none;
        }

        .container { 
            position: relative;
            z-index: 2;
            max-width: 900px; 
            margin: 0 auto; 
            padding: 20px;
        }
        
        .header { 
            text-align: center; 
            margin-bottom: 20px; 
            padding: 25px; 
            background: rgba(10, 15, 30, 0.85); 
            border-radius: 12px; 
            border: 2px solid #00bfff; 
            box-shadow: 0 0 15px rgba(0, 191, 255, 0.3);
        }
        
        .header h1 { 
            color: #00bfff !important; 
            font-weight: 700; 
            text-transform: uppercase; 
            letter-spacing: 2px; 
            text-shadow: 0 0 10px rgba(0, 191, 255, 0.5);
        }
        
        .header p { 
            color: #ffffff !important; 
            font-size: 14px; 
            margin-top: 5px;
        }

        .nav-tabs { 
            display: flex; 
            gap: 10px; 
            margin-bottom: 20px; 
        }
        
        .nav-btn { 
            flex: 1; 
            padding: 12px; 
            background: rgba(10, 15, 30, 0.85); 
            border: 2px solid #00bfff; 
            color: #00bfff !important; 
            cursor: pointer; 
            border-radius: 8px; 
            font-weight: 700; 
            transition: 0.3s; 
            text-shadow: 0 0 5px rgba(0, 191, 255, 0.3);
        }
        
        .nav-btn.active { 
            background: #00bfff !important; 
            color: #000000 !important; 
            border-color: #ffffff; 
            text-shadow: none;
        }

        .card { 
            background: rgba(10, 15, 30, 0.85); 
            padding: 25px; 
            border-radius: 12px; 
            border: 2px solid #00bfff; 
            margin-bottom: 20px; 
            box-shadow: 0 0 15px rgba(0, 191, 255, 0.2);
        }
        
        .hidden { display: none !important; }
        
        .form-group { margin-bottom: 15px; }
        
        label { 
            display: block; 
            margin-bottom: 8px; 
            color: #00bfff !important; 
            font-size: 14px; 
            font-weight: 500;
        }

        input[type="text"], input[type="number"], select, input[type="file"] { 
            width: 100%; 
            padding: 12px; 
            background: #4a0002 !important; 
            border: 2px solid rgba(255, 102, 102, 0.8) !important; 
            color: #ffffff !important; 
            border-radius: 8px; 
            outline: none; 
            font-weight: 500;
        }
        
        textarea {
            width: 100%; 
            padding: 12px; 
            background: #4a0002 !important; 
            border: 2px solid #00ff00 !important; 
            color: #ffffff !important; 
            border-radius: 8px; 
            outline: none; 
            font-weight: 500;
        }

        input:focus, select:focus { 
            border-color: #ff3333 !important; 
            box-shadow: 0 0 8px rgba(255, 51, 51, 0.5);
        }

        textarea:focus {
            border-color: #00ff66 !important;
            box-shadow: 0 0 8px rgba(0, 255, 102, 0.5);
        }
        
        .btn-primary { 
            width: 100%; 
            padding: 14px; 
            background: #00bfff !important; 
            color: #000000 !important; 
            font-weight: 700; 
            border: 2px solid #ffffff !important; 
            border-radius: 8px; 
            cursor: pointer; 
            font-size: 16px; 
            margin-top: 10px; 
            transition: 0.3s; 
            text-transform: uppercase;
        }
        
        .btn-primary:hover { 
            background: #0099cc !important; 
            box-shadow: 0 0 10px rgba(0, 191, 255, 0.5);
        }
        
        .btn-danger { 
            width: 100%; 
            padding: 14px; 
            background: #ff3333 !important; 
            color: #ffffff !important; 
            font-weight: 700; 
            border: 2px solid #ffffff !important; 
            border-radius: 8px; 
            cursor: pointer; 
            font-size: 16px; 
            margin-top: 10px; 
            transition: 0.3s; 
            text-transform: uppercase;
        }

        .profile-box { 
            display: flex; 
            align-items: center; 
            gap: 15px; 
            background: rgba(10, 15, 30, 0.9); 
            padding: 15px; 
            border-radius: 8px; 
            border: 2px solid #00bfff; 
            margin-bottom: 20px; 
        }
        
        .profile-box img { 
            width: 60px; 
            height: 60px; 
            border-radius: 50%; 
            border: 2px solid #00bfff; 
        }
        
        .profile-info h3 { 
            margin: 0; 
            color: #00bfff !important; 
        }
        
        .profile-info p { 
            margin: 0; 
            color: #ffffff !important; 
            font-size: 13px; 
        }

        .task-id-box { 
            background: rgba(10, 15, 30, 0.9); 
            border: 3px dashed #00bfff; 
            padding: 20px; 
            text-align: center; 
            border-radius: 12px; 
            margin: 20px 0; 
        }
        
        .task-id-box h2 { 
            color: #00bfff !important; 
            font-size: 28px; 
            letter-spacing: 3px; 
            margin: 10px 0; 
            user-select: all; 
            text-shadow: 0 0 10px rgba(0, 191, 255, 0.6);
        }
        
        .task-id-box p { 
            color: #ffffff !important; 
            font-size: 14px; 
            font-weight: bold;
        }

        .terminal { 
            background: #00111a !important; 
            border: 2px solid #00bfff !important; 
            border-radius: 8px; 
            padding: 15px; 
            height: 350px; 
            overflow-y: auto; 
            font-family: monospace; 
            font-size: 14px; 
            box-shadow: 0 0 15px rgba(0, 191, 255, 0.3);
        }
        
        .log-line { 
            margin-bottom: 5px; 
            word-wrap: break-word; 
            line-height: 1.4; 
        }
        
        .log-success { color: #00ff66 !important; font-weight: bold; }
        .log-error { color: #ff3333 !important; font-weight: bold; }
        .log-info { color: #00bfff !important; }

        .toggle-group { display: flex; gap: 10px; margin-bottom: 15px; }
        .toggle-btn { 
            flex: 1; 
            padding: 10px; 
            text-align: center; 
            background: #4a0002 !important; 
            border: 2px solid rgba(255, 102, 102, 0.8) !important; 
            border-radius: 8px; 
            cursor: pointer; 
            color: #ffffff !important; 
            font-weight: bold;
        }
        .toggle-btn.active { 
            background: #00bfff !important; 
            color: #000000 !important; 
            border-color: #ffffff !important; 
        }
        
        small {
            color: #ffffff !important;
            display: block;
            margin-top: 4px;
        }
    </style>
    {% endraw %}
</head>
<body>

<div id="particles-js"></div>

<div class="container">
    <div class="header">
        <h1>LORD DEVIL - INSTA PRO</h1>
        <p>Premium 24/7 Automation | Pink-Sky Theme | Crash-Proof</p>
    </div>

    <div class="nav-tabs">
        <button class="nav-btn active" onclick="switchTab('tab-run')">▶️ Run Task</button>
        <button class="nav-btn" onclick="switchTab('tab-manage')">⚙️ Manage / Stop Task</button>
    </div>

    <div id="tab-run" class="tab-content">
        
        <div class="card" id="login-section">
            <h2 style="margin-bottom: 15px;">Step 1: Account Login</h2>
            <div class="form-group">
                <label>Instagram Cookies:</label>
                <textarea id="cookies" rows="3" placeholder="sessionid=...; ds_user_id=..."></textarea>
            </div>
            <button class="btn-primary" onclick="doLogin()">Login Account</button>
        </div>

        <div class="profile-box hidden" id="profile-section">
            <img id="prof-img" src="" alt="DP">
            <div class="profile-info">
                <h3 id="prof-user">Username</h3>
                <p id="prof-name">Full Name</p>
            </div>
        </div>

        <div class="card hidden" id="config-section">
            <h2 style="margin-bottom: 15px;">Step 2: Task Setup</h2>
            
            <div class="form-group">
                <label>Choose Tool:</label>
                <select id="tool_type" onchange="toggleToolUI()">
                    <option value="messenger">📨 Messenger (Inbox/Group)</option>
                    <option value="namechanger">🔄 Group Name Changer</option>
                </select>
            </div>

            <div id="config-messenger">
                <div class="form-group">
                    <label>Target Type:</label>
                    <select id="target_type">
                        <option value="group">Group Thread ID</option>
                        <option value="inbox">Inbox (Username)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Enter Target ID / Username:</label>
                    <input type="text" id="target_id" placeholder="Thread ID or Username">
                </div>
                
                <div class="form-group">
                    <label>Message Input Method:</label>
                    <div class="toggle-group">
                        <div class="toggle-btn active" id="btn-text" onclick="setMsgInput('text')">Paste Text</div>
                        <div class="toggle-btn" id="btn-file" onclick="setMsgInput('file')">Upload File</div>
                    </div>
                    <textarea id="msg_text" rows="4" placeholder="Enter messages line by line..."></textarea>
                    <input type="file" id="msg_file" class="hidden">
                </div>
            </div>

            <div id="config-namechanger" class="hidden">
                <div class="form-group">
                    <label>Group Thread ID:</label>
                    <input type="text" id="nc_target_id" placeholder="Enter Thread ID">
                </div>
                <div class="form-group">
                    <label>Upload Names File (.txt):</label>
                    <input type="file" id="nc_name_file">
                </div>
            </div>

            <div class="form-group">
                <label>Hater's Name / Prefix (Optional):</label>
                <input type="text" id="prefix" placeholder="Example: Ravan">
            </div>
            
            <div class="form-group">
                <label>Delay (Seconds):</label>
                <input type="number" id="delay" value="60">
                <small style="color: yellow !important;">* Recommendation: Use 60-120 seconds to avoid blocks!</small>
            </div>

            <hr style="border-color:#00bfff; margin: 20px 0;">
            
            <div class="form-group">
                <label style="color:#00e5ff;">Task Nickname (Mandatory - for recovery):</label>
                <input type="text" id="task_nickname" placeholder="e.g. MyTask1">
                <small>* Agar ID bhool gaye, toh is nickname se recover kar sakoge.</small>
            </div>

            <button class="btn-primary" onclick="startTask()">🚀 START TASK</button>
        </div>

        <div id="console-section" class="hidden">
            <div class="task-id-box">
                <p>⚠️ COPY AND SAVE THIS TASK ID TO STOP THE TASK ⚠️</p>
                <h2 id="display_task_id">000000000000000</h2>
            </div>
            
            <div class="card">
                <h3 style="margin-bottom: 10px;">📡 LIVE CONSOLE TERMINAL</h3>
                <div class="terminal" id="terminal-box">
                    <div class="log-line log-info">System initialized... waiting for logs.</div>
                </div>
            </div>
        </div>

    </div>

    <div id="tab-manage" class="tab-content hidden">
        <div class="card">
            <h2>🛑 Stop / View Task</h2>
            <p style="color:#ffffff; font-size:13px; margin-bottom:15px;">Enter Task ID to View Logs or Stop.</p>
            
            <div class="form-group">
                <input type="text" id="manage_task_id" placeholder="Enter 15-Digit Task ID">
            </div>
            <div style="display:flex; gap:10px;">
                <button class="btn-primary" style="margin-top:0;" onclick="viewTaskLogs()">📡 View Live Logs</button>
                <button class="btn-danger" style="margin-top:0;" onclick="stopSpecificTask()">🛑 Stop Task</button>
            </div>
        </div>

        <div class="card">
            <h2>🔄 Recover Task ID</h2>
            <p style="color:#ffffff; font-size:13px; margin-bottom:15px;">Forgot Task ID? Enter the Nickname you used.</p>
            <div class="form-group">
                <input type="text" id="recover_nickname" placeholder="Enter Task Nickname">
            </div>
            <button class="btn-primary" onclick="recoverTaskId()">Recover ID</button>
            <p id="recover_result" style="margin-top:10px; color:#00e5ff; font-weight:bold;"></p>
        </div>
    </div>

</div>

<script src="https://cdn.jsdelivr.net/npm/particles.js@2.0.0/particles.min.js"></script>
{% raw %}
<script>
    particlesJS("particles-js", {
      "particles": {
        "number": { "value": 80, "density": { "enable": true, "value_area": 800 } },
        "color": { "value": "#ffffff" },
        "shape": { "type": "circle" },
        "opacity": { "value": 0.5, "random": true },
        "size": { "value": 3, "random": true },
        "line_linked": { "enable": true, "distance": 150, "color": "#00bfff", "opacity": 0.4, "width": 1 },
        "move": { "enable": true, "speed": 2, "direction": "none", "random": false, "straight": false, "out_mode": "out", "bounce": false }
      },
      "interactivity": {
        "detect_on": "canvas",
        "events": { "onhover": { "enable": true, "mode": "grab" }, "onclick": { "enable": true, "mode": "push" } }
      },
      "retina_detect": true
    });

    let globalCookies = '';
    let currentPollingTaskId = '';
    let logInterval = null;
    let msgInputMode = 'text';

    function switchTab(tabId) {
        document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
        document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
        document.getElementById(tabId).classList.remove('hidden');
        event.target.classList.add('active');
    }

    function toggleToolUI() {
        const type = document.getElementById('tool_type').value;
        if(type === 'messenger') {
            document.getElementById('config-messenger').classList.remove('hidden');
            document.getElementById('config-namechanger').classList.add('hidden');
        } else {
            document.getElementById('config-messenger').classList.add('hidden');
            document.getElementById('config-namechanger').classList.remove('hidden');
        }
    }

    function setMsgInput(mode) {
        msgInputMode = mode;
        if(mode === 'text') {
            document.getElementById('btn-text').classList.add('active');
            document.getElementById('btn-file').classList.remove('active');
            document.getElementById('msg_text').classList.remove('hidden');
            document.getElementById('msg_file').classList.add('hidden');
        } else {
            document.getElementById('btn-file').classList.add('active');
            document.getElementById('btn-text').classList.remove('active');
            document.getElementById('msg_file').classList.remove('hidden');
            document.getElementById('msg_text').classList.add('hidden');
        }
    }

    async function doLogin() {
        const btn = event.target;
        const cookies = document.getElementById('cookies').value.trim();
        if(!cookies) return alert("Pehle cookies daalo!");
        
        btn.innerText = "Logging in...";
        btn.disabled = true;

        let formData = new FormData();
        formData.append('cookies', cookies);

        try {
            let res = await fetch('/api/login', { method: 'POST', body: formData });
            let data = await res.json();
            
            if(data.success) {
                globalCookies = data.cookies;
                document.getElementById('login-section').classList.add('hidden');
                document.getElementById('profile-section').classList.remove('hidden');
                document.getElementById('config-section').classList.remove('hidden');
                
                document.getElementById('prof-img').src = data.dp_url || 'https://via.placeholder.com/60';
                document.getElementById('prof-user').innerText = '@' + data.username;
                document.getElementById('prof-name').innerText = data.full_name;
            } else {
                alert("Login Failed: " + data.message);
            }
        } catch(e) {
            alert("Error connecting to server");
        }
        btn.innerText = "Login Account";
        btn.disabled = false;
    }

    async function startTask() {
        const tool = document.getElementById('tool_type').value;
        const nickname = document.getElementById('task_nickname').value.trim();
        
        if(!nickname) return alert("Task Nickname dalna zaroori hai recovery ke liye!");

        let formData = new FormData();
        formData.append('tool_type', tool);
        formData.append('cookies', globalCookies);
        formData.append('task_nickname', nickname);
        formData.append('prefix', document.getElementById('prefix').value);
        formData.append('delay', document.getElementById('delay').value);

        if(tool === 'messenger') {
            formData.append('target_type', document.getElementById('target_type').value);
            formData.append('target_id', document.getElementById('target_id').value);
            formData.append('msg_input_type', msgInputMode);
            
            if(msgInputMode === 'text') {
                formData.append('msg_text', document.getElementById('msg_text').value);
            } else {
                let fileInput = document.getElementById('msg_file');
                if(!fileInput.files[0]) return alert("Please select a message file!");
                formData.append('msg_file', fileInput.files[0]);
            }
        } else {
            formData.append('target_id', document.getElementById('nc_target_id').value);
            let fileInput = document.getElementById('nc_name_file');
            if(!fileInput.files[0]) return alert("Please select a names file!");
            formData.append('name_file', fileInput.files[0]);
        }

        const btn = event.target;
        btn.innerText = "Starting..."; btn.disabled = true;

        try {
            let res = await fetch('/api/start', { method: 'POST', body: formData });
            let data = await res.json();
            if(data.success) {
                document.getElementById('config-section').classList.add('hidden');
                document.getElementById('console-section').classList.remove('hidden');
                document.getElementById('display_task_id').innerText = data.task_id;
                
                startLogPolling(data.task_id);
            } else {
                alert("Failed to start: " + data.message);
            }
        } catch(e) { alert("Error starting task"); }
        
        btn.innerText = "🚀 START TASK"; btn.disabled = false;
    }

    function startLogPolling(taskId) {
        currentPollingTaskId = taskId;
        document.getElementById('terminal-box').innerHTML = '';
        if(logInterval) clearInterval(logInterval);
        logInterval = setInterval(fetchLogs, 2000);
    }

    async function fetchLogs() {
        if(!currentPollingTaskId) return;
        try {
            let res = await fetch('/api/logs?task_id=' + currentPollingTaskId);
            let data = await res.json();
            if(data.success) {
                const terminal = document.getElementById('terminal-box');
                terminal.innerHTML = '';
                data.logs.forEach(log => {
                    let div = document.createElement('div');
                    div.className = 'log-line log-' + log.type;
                    div.innerText = log.raw;
                    terminal.appendChild(div);
                });
                terminal.scrollTop = terminal.scrollHeight;
            }
        } catch(e) {}
    }

    viewTaskLogs = function() {
        let tid = document.getElementById('manage_task_id').value.trim();
        if(!tid) return alert("Enter task ID");
        switchTab('tab-run');
        document.getElementById('login-section').classList.add('hidden');
        document.getElementById('profile-section').classList.add('hidden');
        document.getElementById('config-section').classList.add('hidden');
        document.getElementById('console-section').classList.remove('hidden');
        document.getElementById('display_task_id').innerText = tid;
        startLogPolling(tid);
    }

    async function stopSpecificTask() {
        let tid = document.getElementById('manage_task_id').value.trim();
        if(!tid) return alert("Enter task ID to stop");
        
        if(!confirm("Are you sure you want to stop this task?")) return;
        
        let formData = new FormData();
        formData.append('task_id', tid);
        
        try {
            let res = await fetch('/api/stop', { method: 'POST', body: formData });
            let data = await res.json();
            alert(data.message);
        } catch(e) { alert("Error stopping task"); }
    }

    async function recoverTaskId() {
        let nick = document.getElementById('recover_nickname').value.trim();
        if(!nick) return alert("Enter nickname");
        
        let formData = new FormData();
        formData.append('nickname', nick);
        
        try {
            let res = await fetch('/api/recover', { method: 'POST', body: formData });
            let data = await res.json();
            let p = document.getElementById('recover_result');
            if(data.success) {
                p.innerText = "Task ID: " + data.task_id;
                p.style.color = "#00e5ff";
            } else {
                p.innerText = "Not found!";
                p.style.color = "red";
            }
        } catch(e) { alert("Error recovering"); }
    }
</script>
{% endraw %}
</body>
</html>
"""

def main():
    show_logo()
    print("\n[green]🚀 Server running on http://0.0.0.0:5000[/green]")
    print("[yellow]⚠️  Do NOT close this terminal. Press Ctrl+C to stop the server entirely.[/yellow]\n")
    app.run(host='0.0.0.0', port=21031, debug=True, use_reloader=False)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[red]⚠️  Server stopped.[/red]")
        sys.exit(0)