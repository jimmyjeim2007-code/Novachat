import os
from flask import Flask, render_template_string, request, send_from_directory, jsonify
from flask_socketio import SocketIO, emit, join_room
from werkzeug.utils import secure_filename

app = Flask("Novachat")
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

user_accounts = {}
blocked_users = {}
nicknames = {}
chats_history = {}

HTML_PAGE = '''
<!doctype html>
<html>
<head>
    <title>BlinkTalk - Messenger Style</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body, html { width: 100%; height: 100%; background: #0f172a; color: #fff; font-family: Arial, sans-serif; overflow: hidden; }
        
        .app-container { width: 100vw; height: 100vh; display: flex; justify-content: center; align-items: center; }
        .card { width: 100%; height: 100%; max-width: none; max-height: none; background: #1e293b; display: flex; flex-direction: column; padding: 15px; border-radius: 0; box-shadow: none; }
        
        @media (min-width: 768px) {
            .card { width: 480px; height: 85vh; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
        }

        h2 { color: #38bdf8; margin-bottom: 15px; text-align: center; }
        input, button { width: 100%; padding: 12px; margin-top: 10px; background: #0f172a; border: 1px solid #334155; color: #fff; border-radius: 6px; font-size: 15px; outline: none; }
        button { background: #2563eb; border: none; font-weight: bold; cursor: pointer; transition: 0.3s; }
        button:hover { background: #1d4ed8; }
        .hidden { display: none !important; }
        .error { color: #ef4444; font-size: 13px; margin-top: 8px; display: none; text-align: center; }
        .success { color: #10b981; font-size: 13px; margin-top: 8px; display: none; text-align: center; }
        .file-label { display: block; margin-top: 10px; background: #334155; padding: 10px; border-radius: 6px; cursor: pointer; font-size: 14px; color: #38bdf8; text-align: center; }
        .file-label input { display: none; }
        
        .chat-container { display: flex; flex-direction: column; flex: 1; overflow: hidden; text-align: left; }
        .search-box { display: flex; gap: 5px; margin-bottom: 10px; }
        .search-box input { margin-top: 0; }
        .contacts-list { flex: 1; background: #0f172a; border: 1px solid #334155; border-radius: 6px; overflow-y: auto; padding: 8px; margin-bottom: 10px; }
        .contact-item { padding: 10px; background: #334155; margin-bottom: 6px; border-radius: 6px; cursor: pointer; display: flex; align-items: center; gap: 10px; }
        .contact-item:hover { background: #475569; }
        .contact-item img { width: 40px; height: 40px; border-radius: 50%; object-fit: cover; }
        
        .chat-box { flex: 1; background: #0f172a; border: 1px solid #334155; border-radius: 6px; overflow-y: scroll; padding: 10px; margin-bottom: 10px; display: flex; flex-direction: column; }
        .message { background: #334155; padding: 8px 12px; border-radius: 6px; margin-bottom: 8px; max-width: 85%; word-break: break-all; display: flex; flex-direction: column; gap: 4px; }
        .message img, .message video { width: 150px; max-height: 150px; border-radius: 6px; object-fit: cover; }
        .input-group { display: flex; gap: 5px; align-items: center; }
        .input-group input[type="text"] { margin-top: 0; flex: 1; }
        
        .notification-banner { position: fixed; top: 20px; right: 20px; background: #2563eb; color: white; padding: 10px 20px; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); display: none; z-index: 1000; font-size: 14px; }
    </style>
</head>
<body>

    <div id="notificationBanner" class="notification-banner"></div>

    <div class="app-container">
        <!-- 1. LOGIN SCREEN -->
        <div class="card" id="loginScreen" style="justify-content: center; overflow-y: auto;">
            <h2>BlinkTalk</h2>
            <p style="color: #94a3b8; font-size: 13px; text-align: center; margin-bottom: 15px;">Login with Phone or Gmail</p>
            
            <input type="text" id="nameInput" placeholder="Your Name..." required>
            <input type="text" id="identityInput" placeholder="Phone Number or Gmail..." required>
            <input type="password" id="passwordInput" placeholder="Password..." required>
            
            <div style="margin-top: 10px; text-align: center;">
                <img id="previewAvatar" src="" style="width: 60px; height: 60px; border-radius: 50%; object-fit: cover; display: none; margin: 0 auto 5px auto; border: 2px solid #38bdf8;">
                <label class="file-label">
                    Select Profile Picture
                    <input type="file" id="profilePicInput" accept="image/*" onchange="previewProfilePic(event)">
                </label>
            </div>
            
            <button onclick="handleLogin()">Continue</button>
            <p style="text-align: center; margin-top: 10px;"><a href="#" onclick="showForgotPassword()" style="color: #38bdf8; font-size: 13px; text-decoration: none;">Forgot Password?</a></p>
            <p class="error" id="loginError">Please fill all fields correctly!</p>
        </div>

         <!-- FORGOT PASSWORD SCREEN -->
        <div class="card hidden" id="forgotScreen" style="justify-content: center; overflow-y: auto;">
            <h2>Reset Password</h2>
            <p style="color: #94a3b8; font-size: 13px; text-align: center; margin-bottom: 15px;">Enter your registered Phone or Gmail</p>
            
            <input type="text" id="forgotIdentityInput" placeholder="Phone Number or Gmail..." required>
            <input type="password" id="newPasswordInput" placeholder="New Password..." required>
            
            <button onclick="handleResetPassword()">Update Password</button>
            <p style="text-align: center; margin-top: 10px;"><a href="#" onclick="showLogin()" style="color: #38bdf8; font-size: 13px; text-decoration: none;">Back to Login</a></p>
            <p class="error" id="forgotError">User not found!</p>
            <p class="success" id="forgotSuccess">Password updated successfully!</p>
        </div>

        <!-- 2. DASHBOARD SCREEN -->
        <div class="card hidden" id="dashboardScreen">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <img id="myAvatarDisplay" src="" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover;">
                    <h4 id="myNameDisplay" style="margin: 0; color: #38bdf8;"></h4>
                </div>
                <span style="font-size: 11px; color: #94a3b8;" id="myIdDisplay"></span>
            </div>

            <div class="chat-container">
                <p style="font-size: 13px; color: #94a3b8; margin: 0 0 5px 0; font-weight: bold;">Messages / Inbox:</p>
                <div class="search-box">
                    <input type="text" id="searchIdentity" placeholder="Search by Phone or Gmail...">
                    <button onclick="searchUser()" style="width: 80px; margin-top:0;">Search</button>
                </div>

                <div class="contacts-list" id="contactsList">
                    <p style="text-align: center; color: #64748b; font-size: 13px; margin-top: 50px;">No messages yet. Search user to chat.</p>
                </div>
            </div>
        </div>
        
        <!-- 3. CHAT SCREEN -->
        
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <img id="chatTargetAvatar" src="" style="width: 35px; height: 35px; border-radius: 50%; object-fit: cover;">
                    <div>
                        <h3 id="chatTargetName" style="font-size: 14px; margin: 0; color: #38bdf8;"></h3>
                        <input type="text" id="nicknameInput" placeholder="Set Nickname" style="padding: 2px 5px; font-size: 10px; margin-top: 2px; width: 110px; background: #0f172a; border: 1px solid #334155; color: #fff;" onchange="updateNickname()">
                    </div>
                </div>
                <div>
                    <button onclick="toggleBlockUser()" id="blockBtn" style="width: auto; padding: 6px 10px; font-size: 11px; background: #ef4444; margin-right: 5px;">Block</button>
                    <button onclick="goBackToDashboard()" style="width: auto; padding: 6px 10px; font-size: 11px; background: #475569;">Back</button>
                </div>
            </div>
            
            <div id="callContainer" style="display: none; background: #111; padding: 10px; text-align: center; border-radius: 6px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: center; gap: 10px; margin-bottom: 10px;">
                    <video id="localVideo" autoplay muted playsinline style="width: 100px; height: 80px; border-radius: 4px; background: #000; object-fit: cover;"></video>
                    <video id="remoteVideo" autoplay playsinline style="width: 100px; height: 80px; border-radius: 4px; background: #000; object-fit: cover;"></video>
                </div>
                <audio id="remoteAudio" autoplay></audio>
                <button onclick="endCall()" style="background: #ef4444; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; width: auto;">End Call</button>
            </div>

            <div style="display: flex; gap: 5px; margin-bottom: 8px;">
                <button onclick="startCall('audio')" style="background: #10b981; color: white; border: none; padding: 6px 10px; border-radius: 4px; cursor: pointer; margin-top:0; font-size: 12px;">Audio Call</button>
                <button onclick="startCall('video')" style="background: #3b82f6; color: white; border: none; padding: 6px 10px; border-radius: 4px; cursor: pointer; margin-top:0; font-size: 12px;">Video Call</button>
            </div>  
            <div id="callContainer" style="display: none; background: #111; padding: 10px; text-align: center; border-radius: 6px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: center; gap: 10px; margin-bottom: 10px;">
                    <video id="localVideo" autoplay muted playsinline style="width: 100px; height: 80px; border-radius: 4px; background: #000; object-fit: cover;"></video>
                    <video id="remoteVideo" autoplay playsinline style="width: 100px; height: 80px; border-radius: 4px; background: #000; object-fit: cover;"></video>
                </div>
                <audio id="remoteAudio" autoplay></audio>
                <button onclick="endCall()" style="background: #ef4444; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; width: auto;">End Call</button>
            </div>

            <div style="display: flex; gap: 5px; margin-bottom: 8px;">
                <button onclick="startCall('audio')" style="background: #10b981; color: white; border: none; padding: 6px 10px; border-radius: 4px; cursor: pointer; margin-top:0; font-size: 12px;">Audio Call</button>
                <button onclick="startCall('video')" style="background: #3b82f6; color: white; border: none; padding: 6px 10px; border-radius: 4px; cursor: pointer; margin-top:0; font-size: 12px;">Video Call</button>
            </div>

            <div class="chat-container">
                <div class="chat-box" id="messages"></div>
                <div class="input-group" id="inputGroupArea">
                    <label style="background: #334155; padding: 10px; border-radius: 6px; cursor: pointer; font-size: 16px;" title="Send Media">
                        📎<input type="file" id="mediaInput" accept="image/*,video/*" style="display:none;" onchange="sendMediaFile()">
                    </label>
                    <button onclick="startVoiceRecording()" id="micBtn" style="width: auto; background: #334155; padding: 10px 12px; margin-top:0;" title="Voice Note">🎤</button>
                    <input type="text" id="myMessage" placeholder="Type a message...">
                    <button onclick="sendMessage()" style="width: auto; padding: 10px 15px;">Send</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        let currentUser = null;
        let currentTarget = null;
        let currentTargetRealName = '';
        let currentTargetAvatar = '';
        let localStream = null;
        let mediaRecorder = null;
        let audioChunks = [];

        function previewProfilePic(event) {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const preview = document.getElementById('previewAvatar');
                    preview.src = e.target.result;
                    preview.style.display = 'block';
                }
                reader.readAsDataURL(file);
            }
        }

        function showForgotPassword() {
            document.getElementById('loginScreen').classList.add('hidden');
            document.getElementById('forgotScreen').classList.remove('hidden');
            document.getElementById('forgotError').style.display = 'none';
            document.getElementById('forgotSuccess').style.display = 'none';
        }

        function showLogin() {
            document.getElementById('forgotScreen').classList.add('hidden');
            document.getElementById('loginScreen').classList.remove('hidden');
        }

        function handleResetPassword() {
            const identity = document.getElementById('forgotIdentityInput').value.trim();
            const newPassword = document.getElementById('newPasswordInput').value.trim();
            const errEl = document.getElementById('forgotError');
            const succEl = document.getElementById('forgotSuccess');

            errEl.style.display = 'none';
            succEl.style.display = 'none';

            if(!identity || !newPassword) {
                errEl.innerText = "Please fill all fields!";
                errEl.style.display = 'block';
                return;
            }

            fetch('/reset_password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ identity, newPassword })
            })
            .then(res => res.json())
            .then(data => {
                if(data.success) {
                    succEl.style.display = 'block';
                    setTimeout(() => { showLogin(); }, 1500);
                } else {
                    errEl.innerText = "User not found with this Phone/Gmail!";
                    errEl.style.display = 'block';
                }
            });
        }
        function handleLogin() {
            const name = document.getElementById('nameInput').value.trim();
            const identity = document.getElementById('identityInput').value.trim();
            const password = document.getElementById('passwordInput').value.trim();
            const fileInput = document.getElementById('profilePicInput');

            if(!name || !identity || !password) {
                document.getElementById('loginError').style.display = 'block';
                return;
            }

            const formData = new FormData();
            formData.append('name', name);
            formData.append('identity', identity);
            formData.append('password', password);
            if(fileInput.files[0]) {
                formData.append('file', fileInput.files[0]);
            }

            fetch('/register', { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                currentUser = { name, identity, avatar: data.avatar };
                document.getElementById('loginScreen').classList.add('hidden');
                document.getElementById('dashboardScreen').classList.remove('hidden');
                document.getElementById('myNameDisplay').innerText = name;
                document.getElementById('myIdDisplay').innerText = identity;
                document.getElementById('myAvatarDisplay').src = data.avatar;
                socket.emit('join', { identity });
                refreshInbox();
            });
        }

        function searchUser() {
            const query = document.getElementById('searchIdentity').value.trim();
            if(!query) return;

            fetch('/search?q=' + query + '&user=' + currentUser.identity)
            .then(res => res.json())
            .then(data => {
                if(data.found) {
                    openChat(data.identity, data.name, data.avatar, data.isBlocked, data.nickname);
                } else {
                    alert('User not found!');
                }
            });
        }

        function openChat(identity, name, avatar, isBlocked, nickname) {
            currentTarget = identity;
            currentTargetRealName = name;
            currentTargetAvatar = avatar;
            
            let displayName = nickname || name;
            document.getElementById('dashboardScreen').classList.add('hidden');
            document.getElementById('chatScreen').classList.remove('hidden');
            document.getElementById('chatTargetName').innerText = displayName;
            document.getElementById('chatTargetAvatar').src = avatar;
            document.getElementById('nicknameInput').value = nickname || '';
            document.getElementById('messages').innerHTML = '';
            
            loadChatHistory(identity);
            updateBlockButton(isBlocked);
        }

        function loadChatHistory(targetIdentity) {
            fetch('/get_history?user=' + currentUser.identity + '&target=' + targetIdentity)
            .then(res => res.json())
            .then(data => {
                const box = document.getElementById('messages');
                box.innerHTML = '';
                data.messages.forEach(msg => {
                    appendMessage(msg.senderName, msg.content, msg.type, msg.sender === currentUser.identity);
                });
            });
        }

        function updateNickname() {
            const newNickname = document.getElementById('nicknameInput').value.trim();
            fetch('/set_nickname', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user: currentUser.identity, target: currentTarget, nickname: newNickname })
            })
            .then(res => res.json())
            .then(data => {
                document.getElementById('chatTargetName').innerText = newNickname || currentTargetRealName;
                refreshInbox();
            });
        }

        function updateBlockButton(isBlocked) {
            const btn = document.getElementById('blockBtn');
            const inputArea = document.getElementById('inputGroupArea');
            if(isBlocked) {
                btn.innerText = "Unblock";
                btn.style.background = "#10b981";
                inputArea.style.display = "none";
            } else {
                btn.innerText = "Block";
                btn.style.background = "#ef4444";
                inputArea.style.display = "flex";
            }
        }

        function toggleBlockUser() {
            fetch('/toggle_block', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ blocker: currentUser.identity, target: currentTarget })
            })
            .then(res => res.json())
            .then(data => {
                updateBlockButton(data.isBlocked);
            });
        }

        function goBackToDashboard() {
            document.getElementById('chatScreen').classList.add('hidden');
            document.getElementById('dashboardScreen').classList.remove('hidden');
            currentTarget = null;
            refreshInbox();
        }

        function refreshInbox() {
            if(!currentUser) return;
            fetch('/get_inbox?user=' + currentUser.identity)
            .then(res => res.json())
            .then(data => {
                const list = document.getElementById('contactsList');
                list.innerHTML = '';
                if(data.chats.length === 0) {
                    list.innerHTML = `<p style="text-align: center; color: #64748b; font-size: 13px; margin-top: 50px;">No messages yet.</p>`;
                    return;
                }
                data.chats.forEach(chat => {
                    list.innerHTML += `<div class="contact-item" onclick="openChat('${chat.identity}', '${chat.name}', '${chat.avatar}', ${chat.isBlocked}, '${chat.nickname}')">
                        <img src="${chat.avatar}">
                        <div style="flex:1;">
                            <h4 style="margin:0; color:#38bdf8;">${chat.nickname || chat.name}</h4>
                            <span style="font-size:11px; color:#94a3b8;">${chat.lastMessage}</span>
                        </div>
                    </div>`;
                });
            });
        }

        function sendMessage() {
            const input = document.getElementById('myMessage');
            const text = input.value.trim();
            if(!text || !currentTarget) return;

            socket.emit('private_message', {
                target: currentTarget,
                sender: currentUser.identity,
                senderName: currentUser.name,
                message: text,
                type: 'text'
            });
       appendMessage(currentUser.name, text, 'text', true);
            input.value = '';
        }

        function sendMediaFile() {
            const fileInput = document.getElementById('mediaInput');
            const file = fileInput.files[0];
            if(!file || !currentTarget) return;

            const formData = new FormData();
            formData.append('file', file);

            fetch('/upload', { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                if(data.url) {
                    socket.emit('private_message', {
                        target: currentTarget,
                        sender: currentUser.identity,
                        senderName: currentUser.name,
                        message: data.url,
                        type: data.type
                    });
                    appendMessage(currentUser.name, data.url, data.type, true);
                }
            });
        }

        function startVoiceRecording() {
            if (!navigator.mediaDevices.getUserMedia) return alert('Audio recording not supported.');
            navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
                mediaRecorder.onstop = () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                    const formData = new FormData();
                    formData.append('file', audioBlob, 'voice_note.webm');
                    
                    fetch('/upload', { method: 'POST', body: formData })
                    .then(res => res.json())
                    .then(data => {
                        socket.emit('private_message', {
                            target: currentTarget,
                            sender: currentUser.identity,
                            senderName: currentUser.name,
                            message: data.url,
                            type: 'audio'
                        });
                        appendMessage(currentUser.name, data.url, 'audio', true);
                    });
                };
                mediaRecorder.start();
                alert('Recording started... Tap OK to stop.');
                mediaRecorder.stop();
            });
        }

        function appendMessage(senderName, content, type, isMe) {
            const box = document.getElementById('messages');
            const div = document.createElement('div');
            div.className = 'message';
            div.style.marginLeft = isMe ? 'auto' : '0';
            div.style.background = isMe ? '#2563eb' : '#334155';

            let innerHtml = `<b>${senderName}</b>`;
            if(type === 'image') {
                innerHtml += `<img src="${content}">`;
            } else if(type === 'video') {
                innerHtml += `<video src="${content}" controls></video>`;
            } else if(type === 'audio') {
                innerHtml += `<audio src="${content}" controls style="width: 150px; height: 30px;"></audio>`;
            } else {
                innerHtml += `<span>${content}</span>`;
            }

            div.innerHTML = innerHtml;
            box.appendChild(div);
            box.scrollTop = box.scrollHeight;
        }

        socket.on('receive_message', function(data) {
            if(currentTarget === data.sender) {
                appendMessage(data.senderName, data.message, data.type, false);
            } else {
                showNotification(data.senderName, data.message);
                refreshInbox();
            }
        });

        function showNotification(senderName, message) {
            const banner = document.getElementById('notificationBanner');
            banner.innerText = `New message from ${senderName}: ${message}`;
            banner.style.display = 'block';
            setTimeout(() => { banner.style.display = 'none'; }, 4000);
        }

        async function startCall(type) {
            document.getElementById('callContainer').style.display = 'block';
            try {
                localStream = await navigator.mediaDevices.getUserMedia({ video: type === 'video', audio: true });
                document.getElementById('localVideo').srcObject = localStream;
            } catch (err) {
                alert('Camera/Microphone permission denied.');
            }
        }

        function endCall() {
            if(localStream) {
                localStream.getTracks().forEach(track => track.stop());
            }
            document.getElementById('callContainer').style.display = 'none';
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/register', methods=['POST'])
def register():
    name = request.form.get('name')
    identity = request.form.get('identity')
    password = request.form.get('password')
    
    avatar_url = '/uploads/default_avatar.png'
    if 'file' in request.files:
        file = request.files['file']
        if file.filename != '':
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            avatar_url = f'/uploads/{filename}'
            
    if identity in user_accounts:
        # If user exists, update password/name if needed or keep existing avatar if not re-uploaded
        if avatar_url == '/uploads/default_avatar.png':
            avatar_url = user_accounts[identity]['avatar']
            
    user_accounts[identity] = {
        'name': name,
        'password': password,
        'avatar': avatar_url
    }
    return jsonify({'avatar': avatar_url})

@app.route('/reset_password', methods=['POST'])
def reset_password():
    data = request.get_json()
    identity = data.get('identity')
    new_password = data.get('newPassword')
    
    if identity in user_accounts:
        user_accounts[identity]['password'] = new_password
        return jsonify({'success': True})
    return jsonify({'success': False})

    @app.route('/reset_password', methods=['POST'])
def reset_password():
    data = request.get_json()
    identity = data.get('identity')
    new_password = data.get('newPassword')
    
    if identity in user_accounts:
        user_accounts[identity]['password'] = new_password
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/search')
def search_user():
    query = request.args.get('q', '')
    user_id = request.args.get('user', '')
    if query in user_accounts:
        is_blocked = query in blocked_users.get(user_id, [])
        nickname = nicknames.get(user_id, {}).get(query, '')
        return jsonify({
            'found': True,
            'identity': query,
            'name': user_accounts[query]['name'],
            'avatar': user_accounts[query]['avatar'],
            'isBlocked': is_blocked,
            'nickname': nickname
        })
    return jsonify({'found': False})

@app.route('/set_nickname', methods=['POST'])
def set_nickname():
    data = request.get_json()
    user = data.get('user')
    target = data.get('target')
    nickname = data.get('nickname')
    
    if user not in nicknames:
        nicknames[user] = {}
    nicknames[user][target] = nickname
    return jsonify({'success': True})

@app.route('/toggle_block', methods=['POST'])
def toggle_block():
    data = request.get_json()
    blocker = data.get('blocker')
    target = data.get('target')
    
    if blocker not in blocked_users:
        blocked_users[blocker] = []
        
    if target in blocked_users[blocker]:
        blocked_users[blocker].remove(target)
        is_blocked = False
    else:
        blocked_users[blocker].append(target)
        is_blocked = True
        
    return jsonify({'isBlocked': is_blocked})

@app.route('/get_history')
def get_history():
    user = request.args.get('user')
    target = request.args.get('target')
    room_key = "_".join(sorted([user, target]))
    messages = chats_history.get(room_key, [])
    return jsonify({'messages': messages})

@app.route('/get_inbox')
def get_inbox():
    user = request.args.get('user')
    user_chats = []
    for identity, acc in user_accounts.items():
        if identity == user:
            continue
        room_key = "_".join(sorted([user, identity]))
        history = chats_history.get(room_key, [])
        if history:
            last_msg = history[-1]['message']
            if history[-1]['type'] != 'text':
                last_msg = f"[{history[-1]['type']}]"
            is_blocked = identity in blocked_users.get(user, [])
            nickname = nicknames.get(user, {}).get(identity, '')
            user_chats.append({
                'identity': identity,
                'name': acc['name'],
                'avatar': acc['avatar'],
                'lastMessage': last_msg,
                'isBlocked': is_blocked,
                'nickname': nickname
            })
    return jsonify({'chats': user_chats})

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file'})
    file = request.files['file']
    filename = secure_filename(file.filename or 'media.webm')
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    if filename.lower().endswith(('mp4', 'webm', 'ogg', 'mov')):
        file_type = 'video'
    elif filename.lower().endswith(('mp3', 'wav', 'ogg', 'webm')) and 'voice' in filename:
        file_type = 'audio'
    else:
        file_type = 'image'
        
    return jsonify({'url': f'/uploads/{filename}', 'type': file_type})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@socketio.on('join')
def handle_join(data):
    join_room(data['identity'])

@socketio.on('private_message')
def handle_private_message(data):
    target = data['target']
    sender = data['sender']
    
    if sender in blocked_users.get(target, []):
        return
        
    room_key = "_their_room" if False else "_".join(sorted([sender, target]))
    if room_key not in chats_history:
        chats_history[room_key] = []
        
    chats_history[room_key].append({
        'sender': sender,
        'senderName': data['senderName'],
        'message': data['message'],
        'type': data['type']
    })
    
    emit('receive_message', data, room=target)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
