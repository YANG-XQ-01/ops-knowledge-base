/* 页面的大脑：负责发消息、收回答、渲染气泡 */

// 拿到页面上的关键元素
const messagesEl = document.getElementById("messages");
const inputEl = document.getElementById("question-input");
const sendBtn = document.getElementById("send-button");

// 发送按钮被点击 或 在输入框按回车 → 发送消息
sendBtn.addEventListener("click", sendQuestion);
inputEl.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
        sendQuestion();
    }
});

async function sendQuestion() {
    const question = inputEl.value.trim(); // 去掉首尾空格
    if (!question) return; // 空问题不发

    // 1. 把用户的问题显示成气泡
    appendMessage("user", escapeHtml(question));

    // 2. 清空输入框，禁用按钮，显示「正在输入」
    inputEl.value = "";
    setSending(true);
    const typingEl = appendMessage("assistant", "");
    typingEl.querySelector(".bubble").classList.add("typing");
    typingEl.querySelector(".bubble").innerHTML =
        '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';

    try {
        // 3. 调用后端接口（fetch = 浏览器里发 HTTP 请求）
        const response = await fetch("/api/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question }),
        });

        if (!response.ok) {
            throw new Error(`请求失败：HTTP ${response.status}`);
        }

        const data = await response.json();

        // 4. 用真正的回答替换掉「正在输入」
        //    formatAnswer 内部先转义再渲染，防 XSS
        typingEl.querySelector(".bubble").classList.remove("typing");
        typingEl.querySelector(".bubble").innerHTML =
            formatAnswer(data.answer) +
            cacheTag(data.from_cache) +
            sourcesHtml(data.sources);
    } catch (error) {
        // 5. 出错也要让用户看到提示，而不是干等
        typingEl.querySelector(".bubble").classList.remove("typing");
        typingEl.querySelector(".bubble").innerHTML =
            `⚠️ ${escapeHtml(error.message)}`;
    } finally {
        setSending(false);
        messagesEl.scrollTop = messagesEl.scrollHeight; // 滚到底部
    }
}

/* 在消息区追加一条消息，返回外层容器 */
function appendMessage(role, content) {
    const wrapper = document.createElement("div");
    wrapper.className = `message ${role}`;
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = content; // textContent = 纯文本插入（天然安全）
    wrapper.appendChild(bubble);
    messagesEl.appendChild(wrapper);
    return wrapper;
}

/* 转义 HTML：把 < > & 等危险字符变成安全字符 */
function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

/* 格式化回答：转义后把 **加粗** 和换行变成好看的格式 */
function formatAnswer(text) {
    let safe = escapeHtml(text);
    // 把 **xxx** 转成 <strong>xxx</strong>（先转义再做标记转换，防止注入）
    safe = safe.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    safe = safe.replace(/\n/g, "<br>"); // 换行转 <br>
    return safe;
}

/* 如果回答来自缓存，加一个小闪电标签 */
function cacheTag(fromCache) {
    return fromCache
        ? '<span class="cache-tag">⚡ 缓存命中</span>'
        : "";
}

/* 参考来源展示 */
function sourcesHtml(sources) {
    if (!sources || sources.length === 0) return "";
    const list = sources
        .map((s) => escapeHtml(s))
        .join("、");
    return `<div class="sources">📚 参考：${list}</div>`;
}

/* 发送期间锁定输入 */
function setSending(isSending) {
    sendBtn.disabled = isSending;
    inputEl.disabled = isSending;
    if (!isSending) inputEl.focus();
}
