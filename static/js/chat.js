
  const username = "{{ username }}";

  // render messages array
  function renderMessages(messages) {
  const messagesDiv = document.getElementById("messages");
  
  // Check scroll position BEFORE clearing messages
  const wasNearBottom =
      messagesDiv.scrollHeight -
      messagesDiv.scrollTop -
      messagesDiv.clientHeight < 80;

  messagesDiv.innerHTML = "";

  messages.forEach(msg => {
    // wrapper row
    const row = document.createElement("div");
    row.className = msg.sender === username ? "message-row me" : "message-row other";

    // avatar circle (only for received messages)
    if (msg.sender !== username) {
      const avatar = document.createElement("div");
      avatar.className = "avatar-circle-public"; 
      avatar.textContent = (msg.sender || "?").charAt(0).toUpperCase(); // initial character of sender
      avatar.setAttribute("data-username", msg.sender);

      const statusDot = document.createElement("span");
      statusDot.className = `status-dot-public ${isUserOnline(msg.sender) ? 'status-online' : 'status-hidden'}`;
      avatar.appendChild(statusDot);

      row.appendChild(avatar);
    }

    // bubble
    const bubble = document.createElement("div");
    bubble.className = msg.sender === username ? "message me" : "message other";

    // sender
    const sender = document.createElement("strong");
    sender.textContent = msg.sender === username ? "You" : msg.sender;
    bubble.appendChild(sender);

    // message text
    const msgText = document.createElement("div");
    msgText.textContent = msg.message;
    bubble.appendChild(msgText);

    // horizontal line
    const footer = document.createElement("div");
    footer.className = "msg-footer";

    const divider = document.createElement("div");
    divider.className = "msg-divider";
    footer.appendChild(divider);
    
    // timestamp
    const time = document.createElement("small");
    time.className = "timestamp text-muted d-block";
    
    time.textContent = formatTime(msg.sent_at);
    
    //bubble.appendChild(time);
    footer.appendChild(time);
    bubble.appendChild(footer);
    row.appendChild(bubble);
    messagesDiv.appendChild(row);
  });

  //messagesDiv.scrollTop = messagesDiv.scrollHeight;
    if (wasNearBottom || messagesDiv.scrollHeight === 0) {
      messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }
}

// helper to append a single message row (used for incoming WebSocket messages)
function appendMessageRow(msg) {
  const messagesDiv = document.getElementById("messages");

  // Check BEFORE adding the new message if the user is near the bottom
  const wasNearBottom =
      messagesDiv.scrollHeight -
      messagesDiv.scrollTop -
      messagesDiv.clientHeight < 80;
  
  const row = document.createElement("div");
  row.className = msg.sender === username ? "message-row me" : "message-row other";

  if (msg.sender !== username) {
    const avatar = document.createElement("div");
    avatar.className = "avatar-circle-public";
    avatar.textContent = (msg.sender || "?").charAt(0).toUpperCase();

    // Store full username for reliable matching
    avatar.setAttribute("data-username", msg.sender);

    // Add status dot on public chat messages
    const statusDot = document.createElement("span");
    statusDot.className = `status-dot-public ${isUserOnline(msg.sender) ? 'status-online' : 'status-hidden'}`;
    avatar.appendChild(statusDot);

    row.appendChild(avatar);
  }

    const bubble = document.createElement("div");
    bubble.className = msg.sender === username ? "message me" : "message other";

    // sender
    const sender = document.createElement("strong");
    sender.textContent = msg.sender === username ? "You" : msg.sender;
    bubble.appendChild(sender);

    // message text
    const msgText = document.createElement("div");
    msgText.textContent = msg.message;
    bubble.appendChild(msgText);

    // horizontal line
    const footer = document.createElement("div");
    footer.className = "msg-footer";

    const divider = document.createElement("div");
    divider.className = "msg-divider";
    footer.appendChild(divider);

    // timestamp
    const time = document.createElement("small");
    time.className = "timestamp text-muted d-block";

    time.textContent = formatTime(msg.sent_at);
    //bubble.appendChild(time);
    footer.appendChild(time);
    bubble.appendChild(footer);
    row.appendChild(bubble);
    messagesDiv.appendChild(row);

    //messagesDiv.scrollTop = messagesDiv.scrollHeight;
    
    // only scroll to bottom if the user was already near the bottom before the new message arrived
    if (wasNearBottom) {
        messagesDiv.scrollTo({
            top: messagesDiv.scrollHeight,
            behavior: "smooth"
        });
    }
}

function formatTime(sent_at) {
    if (!sent_at) return "Just now";

    return new Intl.DateTimeFormat("en-US", {
        year: "numeric",
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
        timeZone: "Asia/Yangon"
    }).format(new Date(sent_at));
}


// Handle incoming WebSocket messages
function handleIncomingMessage(event) {
  const data = JSON.parse(event.data);

  if (data.type === "message") {
    appendMessageRow(data);

    // Play sounds
    if (data.sender !== username) {
      document.getElementById("receiveSound").play();
    } else {
      document.getElementById("sendSound").play();
    }
    return;
  }

  if (data.type === "presence") {
    onlineUsers[data.username] = data.online;   // ✅ keep map updated
    updateUserStatus(data.username, data.online);
    return; // stop here, don’t render as a chat bubble
  }

  if (data.type === "presence_init") {
    data.users.forEach(u => {
      onlineUsers[u.username] = u.online;       // ✅ keep map updated
      updateUserStatus(u.username, u.online);
    });
    return;
  }
}


const onlineUsers = {};       // *Map to track online status of users (important for public chat and user list updates)*
function updateUserStatus(username, online) {
  onlineUsers[username] = online;

  // Update user buttons (sidebar)
  const userButtons = document.querySelectorAll("#users button");

  userButtons.forEach(btn => {
    if (btn.dataset.username === username) {
      const dot = btn.querySelector(".status-dot");

        if(dot){
          
            //check recently online status
            btn.innerHTML = `<span class="status-dot ${online ? 'status-online' : 'status-offline'}"></span>
                             <strong>👤 ${username}</strong>`;
        }
    }
  });

  // Update top bar if currently chatting with this user
  const headerUser = document.querySelector("#chatHeader .username");
  if (headerUser && headerUser.textContent.trim() === username) {
    const userInfo = headerUser.parentElement; // .user-info container

    // Dot
    //let statusDot = userInfo.querySelector(".status-dot");
    //if (statusDot) {
    //  statusDot.className = `status-dot ${online ? 'status-online' : 'status-offline'}`;
    //}

    // Text
    let statusText = userInfo.querySelector(".status");
    if (statusText) {
      statusText.textContent = online ? "online" : "offline";
      statusText.className = `status ${online ? 'online-text' : 'text-muted'}`;
    }
  }
  
  // Update public chat avatars
  const chatAvatars = document.querySelectorAll(".avatar-circle-public");
  chatAvatars.forEach(avatar => {
    if (avatar.getAttribute("data-username") === username) {
      const statusDot = avatar.querySelector(".status-dot-public");
      if (statusDot) {
        // can be placed last seen recently (status-offline)
        statusDot.className = `status-dot-public ${online ? 'status-online' : 'status-hidden'}`;
      }
    }
  });
}

function isUserOnline(username) {
  return !!onlineUsers[username];
}

  // Fetch PUBLIC messages
  async function loadPublicMessages() {
    const response = await fetch("/messages");
    const data = await response.json();
    renderMessages(data);

    // After rebuilding messages, re‑apply presence state
    Object.keys(onlineUsers).forEach(u => {
      updateUserStatus(u, onlineUsers[u]);
    });
  }

  // Fetch PRIVATE messages
  async function loadMessagesForRoom(receiver) {
    const response = await fetch("/messages?receiver=" 
                                + encodeURIComponent(receiver) 
                                + "&username=" + encodeURIComponent(username));
    const data = await response.json();
    renderMessages(data);

    // After rebuilding messages, re‑apply presence state
    Object.keys(onlineUsers).forEach(u => {
      updateUserStatus(u, onlineUsers[u]);
    });
  }


// Helper to connect WebSocket
let ws = null;
let reconnectTimer = null;
let manualClose = false;


function connectWebSocket(url) {

  // Cancel previous reconnect timer
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }

  // Close old connection intentionally
  if (ws) {
    manualClose = true;
    ws.close();
  }

  ws = new WebSocket(url);


  document.getElementById("sendBtn").disabled = true;


  ws.onopen = () => {
    console.log("Connected to " + url);

    manualClose = false;

    document.getElementById("sendBtn").disabled = false;
  };


  ws.onmessage = handleIncomingMessage;


  ws.onclose = (e) => {

    console.log("Closed:", e.code, e.reason);

    document.getElementById("sendBtn").disabled = true;


    // Ignore intentional close
    if (manualClose) {
      console.log("Manual close, no reconnect");
      return;
    }


    reconnectTimer = setTimeout(() => {

      console.log("Attempting reconnect...");

      connectWebSocket(url);

    },3000);
  };


  ws.onerror = (err) => {
    console.error("WebSocket error:", err);
  };
}


// Send message function
function sendMessage() {
  let input = document.getElementById("messageText");
  if (input.value.trim() !== "") {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      console.log("ws.readyState =", ws.readyState);
      alert("Connection not ready yet. Please wait a moment.");
      return;
    }

    ws.send(JSON.stringify({
      sender: username,
      message: input.value
    }));

    //document.getElementById("sendSound").play();
    input.value = "";
  }
}

// Public Chat button
const publicBtn = document.getElementById("publicChat");
publicBtn.className = "btn BtnPS w-100 mb-2";
publicBtn.onclick = function () {
  connectWebSocket(
    getWebSocketUrl(
        "/ws?username=" + encodeURIComponent(username)
    )
);

  //document.getElementById("messages").innerHTML = "";
  loadPublicMessages();

  document.getElementById("chatHeader").innerHTML = `

    <div class="left">
      <span class="username" style="display:flex; align-items:center; gap:5px;">
        <img src="/static/internet.png" alt="globe" style="width: 22px;height:22px;vertical-align:middle;">
        Public Chat
      </span>
    </div>

  `;
  if(window.innerWidth < 768){
    sidebar.classList.remove("active");
}
};

// Load users list
async function loadUsers() {
  const response = await fetch("/users");
  const users = await response.json();
  const userDiv = document.getElementById("users");
  userDiv.innerHTML = "";

  users.forEach(user => {
    if (user.username === username) return;

    let privateBtn = document.createElement("button");
    privateBtn.className = "btn btn-outline-secondary w-100 mb-2";
    privateBtn.dataset.username = user.username;
    // ✅ Always include the dot span from the start
    privateBtn.innerHTML = ` 
                    <span class="status-dot ${user.online ? 'status-online' : 'offline'}"></span>
                    <strong>👤 ${user.username} </strong>`; 

    privateBtn.onclick = function () {
      connectWebSocket(
        getWebSocketUrl(
          "/ws?username=" 
          + encodeURIComponent(username) 
          + "&receiver=" 
          + encodeURIComponent(user.username)
        )
      );

      //document.getElementById("messages").innerHTML = ""; manual clear is not needed anymore
      loadMessagesForRoom(user.username);

      const header = document.getElementById("chatHeader");
      header.innerHTML = `

          <div class="left d-flex align-items-center">

              <div class="header-avatar">
                  ${user.username.charAt(0).toUpperCase()}
              </div>

              <div class="user-info ms-2">
                  <span class="username">
                      ${user.username}
                  </span>
                  <br>

                  <span class="status ${isUserOnline(user.username) ? 'online-text' : 'text-muted'}">
                      ${isUserOnline(user.username) ? 'online' : 'offline'}
                  </span>
              </div>

          </div>


          <div class="actions">

              <i class="fas fa-search"></i>

              <i class="fas fa-ellipsis-v"></i>

          </div>

          `;
      if(window.innerWidth < 768){
          sidebar.classList.remove("active");
      }
    };

    userDiv.appendChild(privateBtn);
  });
  Object.keys(onlineUsers).forEach(u=>{
    updateUserStatus(u, onlineUsers[u]);
});
}

function getWebSocketUrl(path) {
    const protocol = location.protocol === "https:" 
        ? "wss://" 
        : "ws://";

    return protocol + location.host + path;
}

// Run on page load
window.onload = function () {
  // Bind Send button
  document.getElementById("sendBtn").onclick = sendMessage;
  document.getElementById("messageText").addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      sendMessage();
    }
  });

  
  // Initial WebSocket + data load
  //connectWebSocket("ws://127.0.0.1:8000/ws?username=" + encodeURIComponent(username));
  const protocol = location.protocol === "https:" ? "wss://" : "ws://";

  connectWebSocket(
      getWebSocketUrl("/ws?username=" + encodeURIComponent(username))
  );
  loadUsers();
  loadPublicMessages();

  document.getElementById("chatHeader").innerHTML = `
    <div class="left">
      <span class="username" style="display:flex; align-items:center; gap:5px;">
        <img src="/static/internet.png" alt="globe" style="width: 22px;height:22px;vertical-align:middle;">
        Public Chat
      </span>
    </div>
  `;

  // Scroll button
  const messagesDiv = document.getElementById("messages");
  const scrollBtn = document.getElementById("scrollBottomBtn");

  messagesDiv.addEventListener("scroll", () => {

      const nearBottom =
          messagesDiv.scrollHeight -
          messagesDiv.scrollTop -
          messagesDiv.clientHeight < 80;

      if (nearBottom) {
          scrollBtn.style.display = "none";
      } else {
          scrollBtn.style.display = "block";
      }
  });

    scrollBtn.onclick = () => {
      messagesDiv.scrollTo({
          top: messagesDiv.scrollHeight,
          behavior: "smooth"
      });
  };



  document.getElementById("logoutBtn").onclick = function () {

    // Close websocket first
    manualClose = true;

    if (ws) {
        ws.close();
    }

    window.location.href = "/logout";
};
};


 /* Humburger */
  const menuBtn = document.getElementById("menuBtn");
  const closeSidebar = document.getElementById("closeSidebar");
  const sidebar = document.getElementById("sidebar");


  menuBtn.onclick = function(){
      sidebar.classList.toggle("active");
  };
  closeSidebar.onclick = function(){
      sidebar.classList.remove("active");
};
