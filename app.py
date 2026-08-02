import os
from flask import Flask, render_template_string, request, send_from_directory
from flask_socketio import SocketIO, emit, join_room
from werkzeug.utils import secure_filename

app = Flask("Novachat")
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ইউজারদের ডাটাবেজ
user_accounts = {}

HTML_PAGE = '''
<!doctype html>
<html>
<head>
    <title>BlinkTalk - WhatsApp Style</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { background: #0f172a; color: #fff; font-family: Arial, sans-serif; margin: 0; padding: 20px; display: flex; justify-content: center; align-items: center; height: 100vh; box-sizing: border-box; }
        .card { width: 100%; max-width: 420px; background: #1e293b; padding: 25px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); text-align: center; box-sizing: border-box; }
        h2 { color: #38bdf8; margin-bottom: 15px; }
        input, button { width: 100%; padding: 12px; margin-top: 10px; background: #0f172a; border: 1px solid #334155; color: #fff; border-radius: 6px; box-sizing: border-box; font-size: 15px; }
        button { background: #2563eb; border: none; font-weight: bold; cursor: pointer; transition: 0.3s; }
        button:hover { background: #1d4ed8; }
        .hidden { display: none !important; }
        .error { color: #ef4444; font-size: 13px; margin-top: 8px; display: none; }
        .file-label { display: block; margin-top: 10px; background: #334155; padding: 10px; border-radius: 6px; cursor: pointer; font-size: 14px; color: #38bdf8; text-align: center; }
        .file-label input { display: none; }
        
        /* Chat Dashboard UI */
        .chat-container { display: flex; flex-direction: column; height: 450px; text-align: left; }
        .search-box { display: flex; gap: 5px; margin-bottom: 10px; }
        .search-box input { margin-top: 0; }
        .contacts-list { flex: 1; background: #0f172a; border: 1px solid #334155; border-radius: 6px; overflow-y: auto; padding: 8px; margin-bottom: 10px; }
        .contact-item { padding: 10px; background: #334155; margin-bottom: 6px; border-radius: 6px; cursor: pointer; display: flex; align-items: center; gap: 10px; }
        .contact-item:hover { background: #475569; }
        .contact-item img { width: 35px; height: 35px; border-radius: 50%; object-fit: cover; }
        
        /* Active Chat Room UI */
        .chat-box { flex: 1; background: #0f172a; border: 1px solid #334155; border-radius: 6px; overflow-y: scroll; padding: 10px; margin-bottom: 10px; display: flex; flex-direction: column; }
        .message { background: #334155; padding: 8px 12px; border-radius: 6px; margin-bottom: 8px; max-width: 85%; word-break: break-all; display: flex; align-items: center; gap: 8px; }
        .message img, .message video { width: 100px; max-height: 100px; border-radius: 6px; object-fit: cover; }
        .message .avatar { width: 25px; height: 25px; border-radius: 50%; object-fit: cover; }
        .input-group { display: flex; gap: 5px; align-items: center; }
        .input-group input[type="text"] { margin-top: 0; flex: 1; }
    </style>
</head>
<body>

    <!-- 1. LOGIN / REGISTER SCREEN -->
    <div class="card" id="loginScreen">
        <h2>BlinkTalk</h2>
        <p style="color: #94a3b8; font-size: 13px;">Login with Phone or Gmail</p>
        
        <input type="text" id="nameInput" placeholder="Your Name..." required>
        <input type="text" id="identityInput" placeholder="Phone Number or Gmail..." required>
        <input type="password" id="passwordInput" placeholder="Password..." required>
        
        <label class="file-label">
            📁 Profile Picture
            <input type="file" id="profilePicInput" accept="image/*">
        </label>
        
        <button onclick="handleLogin()">Continue</button>
        <a href="#" onclick="showForgotPassword()" style="color: #60a5fa; font-size: 13px; text-decoration: none; display: block; margin-top: 10px; text-align: center;">Forgot Password?</a>

 href="#" onclick="showForgotPassword()" style="color: #60a5fa; font-size: 13px; text-decoration: none; display: block; margin-top: 10px; text-align: center;">Forgot Password?</a>

<div id="forgotSection" style="display: none; margin-top: 15px;">
    <div id="stepOne">
        <input type="text" id="resetIdentity" placeholder="Your Phone or Gmail.." style="width: 100%; padding: 8px; margin-bottom: 8px; background: #1e293b; border: 1px solid #334155; color: white; border-radius: 4px;">
        <button onclick="requestOtp()" style="width: 100%; padding: 8px; background: #2563eb; color: white; border: none; border-radius: 4px; cursor: pointer;">Send Verification Code</button>
    </div>

    <div id="stepTwo" style="display: none; margin-top: 10px;">
        <input type="text" id="verificationCode" placeholder="Enter 4-digit Code.." style="width: 100%; padding: 8px; margin-bottom: 8px; background: #1e293b; border: 1px solid #334155; color: white; border-radius: 4px;">
        <input type="password" id="newPassword" placeholder="New Password.." style="width: 100%; padding: 8px; margin-bottom: 8px; background: #1e293b; border: 1px solid #334155; color: white; border-radius: 4px;">
        <button onclick="verifyAndReset()" style="width: 100%; padding: 8px; background: #16a34a; color: white; border: none; border-radius: 4px; cursor: pointer;">Verify & Update Password</button>
    </div>
</div>


        <p class="error" id="loginError">Please fill all fields correctly!</p>
    </div>

    <!-- 2. CONTACTS & SEARCH DASHBOARD -->
    <div class="card hidden" id="dashboardScreen" style="max-width: 480px;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <img id="myAvatarDisplay" src="" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover;">
                <h4 id="myNameDisplay" style="margin: 0; color: #38bdf8;"></h4>
            </div>
            <span style="font-size: 11px; color: #94a3b8;" id="myIdDisplay"></span>
        </div>

        <div class="chat-container">
            <p style="font-size: 13px; color: #94a3b8; margin: 0 0 5px 0; font-weight: bold;">Find & Chat with Someone:</p>
            <div class="search-box">
                <input type="text" id="searchIdentity" placeholder="Enter Phone or Gmail to Search...">
                <button onclick="searchUser()" style="width: 80px; margin-top:0;">Search</button>
            </div>

            <p style="font-size: 12px; color: #94a3b8; margin: 5px 0;">Search Results / Chats:</p>
            <div class="contacts-list" id="contactsList">
                <p style="text-align: center; color: #64748b; font-size: 13px; margin-top: 50px;">Search a phone number or email above to start chatting.</p>
            </div>
        </div>
    </div>
    
    <!-- 3. CHAT ROOM SCREEN -->
    <div class="card hidden" id="chatScreen" style="max-width: 500px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <img id="chatTargetAvatar" src="" style="width: 30px; height: 30px; border-radius: 50%; object-fit: cover;">
                <h3 id="chatTargetName" style="font-size: 14px; margin: 0; color: #38bdf8;"></h3>
            </div>
            <button onclick="goBackToDashboard()" style="width: auto; padding: 5px 10px; font-size: 11px; background: #475569;">Back</button>
        </div>
        
        <div class="chat-container">
            <div class="chat-box" id="messages"></div>
            <div class="input-group">
                <label style="background: #334155; padding: 8px; border-radius: 6px; cursor: pointer; font-size: 16px;" title="Send Photo">
                    📎<input type="file" id="mediaInput" accept="image/*,video/*" style="display:none;" onchange="sendMediaFile()">
                </label>
                <input type="text" id="myMessage" placeholder="Type a message...">
                <button onclick="sendMessage()" style="width: auto;">Send</button>
            </div>
        </div>
    </div>

    <script>
        var socket = io();
        var myName = "", myIdentity = "", myAvatar = "";
        var currentChatTargetIdentity = "", currentChatTargetName = "", currentChatTargetAvatar = "";

        function handleLogin() {
            var name = document.getElementById('nameInput').value.trim();
            var identity = document.getElementById('identityInput').value.trim();
            var password = document.getElementById('passwordInput').value.trim();
            var fileInput = document.getElementById('profilePicInput');
            var errTag = document.getElementById('loginError');

            if(name === "" || identity === "" || password === "") {
                errTag.style.display = "block";
                return;
            }

            if(fileInput.files.length > 0) {
                var formData = new FormData();
                formData.append("file", fileInput.files[0]);

                fetch('/upload', { method: 'POST', body: formData })
                .then(res => res.json())
                .then(data => {
                    myAvatar = data.filename ? ("/uploads/" + data.filename) : "https://via.placeholder.com/30";
                    registerUser(name, identity, password, myAvatar);
                });
            } else {
                myAvatar = "https://via.placeholder.com/30";
                registerUser(name, identity, password, myAvatar);
            }
        }

        function registerUser(name, identity, password, avatar) {
            socket.emit('login_user', { name: name, identity: identity, password: password, avatar: avatar });

            socket.once('login_response', function(res) {
                if(res.success) {
                    myName = name; myIdentity = identity; myAvatar = avatar;
                    document.getElementById('myNameDisplay').innerText = myName;
                    document.getElementById('myIdDisplay').innerText = myIdentity;
                    document.getElementById('myAvatarDisplay').src = myAvatar;

                    document.getElementById('loginScreen').classList.add('hidden');
                    document.getElementById('dashboardScreen').classList.remove('hidden');
                } else {
                    var errTag = document.getElementById('loginError');
                    errTag.innerText = res.message;
                    errTag.style.display = "block";
                }
            });
        }

        function searchUser() {
            var query = document.getElementById('searchIdentity').value.trim();
            if(query === "") return;

            socket.emit('search_user', { query: query, myIdentity: myIdentity });

            socket.once('search_response', function(res) {
                var list = document.getElementById('contactsList');
                list.innerHTML = "";
                if(res.found) {
                    var user = res.user;
                    var div = document.createElement('div');
                    div.className = 'contact-item';
                    div.innerHTML = '<img src="' + user.avatar + '"><div><b>' + user.name + '</b><br><span style="font-size:11px; color:#94a3b8;">' + user.identity + '</span></div>';
                    div.onclick = function() {
                        openChat(user.identity, user.name, user.avatar);
                    };
                    list.appendChild(div);
                } else {
                    list.innerHTML = '<p style="text-align: center; color: #ef4444; font-size: 13px; margin-top: 40px;">No user found with this number/email!</p>';
                }
            });
        }
        function openChat(targetIdentity, targetName, targetAvatar) {
            currentChatTargetIdentity = targetIdentity;
            currentChatTargetName = targetName;
            currentChatTargetAvatar = targetAvatar;

            document.getElementById('dashboardScreen').classList.add('hidden');
            document.getElementById('chatScreen').classList.remove('hidden');
            document.getElementById('chatTargetName').innerText = targetName;
            document.getElementById('chatTargetAvatar').src = targetAvatar;
            document.getElementById('messages').innerHTML = "";

            socket.emit('join_private_chat', { user: myIdentity, target: targetIdentity });
        }

        function goBackToDashboard() {
            document.getElementById('chatScreen').classList.add('hidden');
            document.getElementById('dashboardScreen').classList.remove('hidden');
        }

        function sendMessage() {
            var input = document.getElementById('myMessage');
            if(input.value.trim() !== "") {
                socket.emit('send_private_message', {
                    sender: myIdentity,
                    target: currentChatTargetIdentity,
                    user: myName,
                    avatar: myAvatar,
                    type: 'text',
                    content: input.value
                });
                input.value = '';
            }
        }

        function sendMediaFile() {
            var fileInput = document.getElementById('mediaInput');
            if(fileInput.files.length > 0) {
                var file = fileInput.files[0];
                var formData = new FormData();
                formData.append("file", file);

                fetch('/upload', { method: 'POST', body: formData })
                .then(res => res.json())
                .then(data => {
                    if(data.filename) {
                        var fileUrl = "/uploads/" + data.filename;
                        var fileType = file.type.startsWith('video') ? 'video' : 'image';
                        socket.emit('send_private_message', {
                            sender: myIdentity,
                            target: currentChatTargetIdentity,
                            user: myName,
                            avatar: myAvatar,
                            type: fileType,
                            content: fileUrl
                        });
                    }
                });
            }
        }

        socket.on('incoming_private_message', function(data) {
            var msgBox = document.getElementById('messages');
            var div = document.createElement('div');
            div.className = 'message';
            var contentHtml = data.type === 'image' ? '<img src="' + data.content + '">' : (data.type === 'video' ? '<video src="' + data.content + '" controls></video>' : '<span>' + data.content + '</span>');
            div.innerHTML = '<img class="avatar" src="' + (data.avatar || 'https://via.placeholder.com/30') + '"><div><span style="font-size:10px; color:#38bdf8;">' + data.user + '</span>' + contentHtml + '</div>';
            msgBox.appendChild(div);
            msgBox.scrollTop = msgBox.scrollHeight;
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return {'filename': ''}
    file = request.files['file']
    if file.filename == '':
        return {'filename': ''}
    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    return {'filename': filename}

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@socketio.on('login_user')
def handle_login_user(data):
    identity = data['identity']
    password = data['password']
    if identity in user_accounts:
        if user_accounts[identity]['password'] == password:
            emit('login_response', {'success': True})
        else:
            emit('login_response', {'success': False, 'message': 'Incorrect Password!'})
    else:
        user_accounts[identity] = {
            'name': data['name'],
            'password': password,
            'avatar': data['avatar']
        }
        emit('login_response', {'success': True})

@socketio.on('search_user')
def handle_search_user(data):
    query = data['query']
    my_id = data['myIdentity']
    if query in user_accounts and query != my_id:
        u = user_accounts[query]
        emit('search_response', {
            'found': True,
            'user': {'identity': query, 'name': u['name'], 'avatar': u['avatar']}
        })
    else:
        emit('search_response', {'found': False})
        otp_storage = {}

@socketio.on('send_otp')
def handle_send_otp(data):
    identity = data.get('identity')
    
    if identity in user_accounts:
        code = str(random.randint(1000, 9999))
        otp_storage[identity] = code
        emit('otp_sent_response', {'success': True, 'code': code, 'message': 'Verification code generated!'})
    else:
        emit('otp_sent_response', {'success': False, 'message': 'Account not found!'})

@socketio.on('verify_and_reset')
def handle_verify_and_reset(data):
    identity = data.get('identity')
    entered_code = data.get('code')
    new_password = data.get('new_password')
    
    if identity in otp_storage and otp_storage[identity] == entered_code:
        user_accounts[identity]['password'] = new_password
        del otp_storage[identity]
        emit('login_response', {'success': True, 'message': 'Password updated successfully!'})
    else:
        emit('login_response', {'success': False, 'message': 'Invalid verification code!'})

@socketio.on('join_private_chat')
def handle_join_private(data):
    room = "".join(sorted([data['user'], data['target']]))
    join_room(room)

@socketio.on('send_private_message')
def handle_send_private(data):
    room = "".join(sorted([data['sender'], data['target']]))
    payload = {
        'user': data['user'],
        'avatar': data['avatar'],
        'type': data['type'],
        'content': data['content']
    }
    emit('incoming_private_message', payload, room=room)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
