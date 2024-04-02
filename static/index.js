// Function to show logs in a modal
function showLogs(userId) {
    fetch(`/client/${userId}`)
    .then(response => response.json())
    .then(data => {
        const logs = data.data.logs;
        const logText = logs.map(log => `[${log[0]}] -- ${log[1]}`).join('<br>');
        document.getElementById('logText').innerHTML = logText;
        document.getElementById('logsModal').style.display = 'block';
    })
    .catch(error => console.error('Error:', error));
}

// 更新连接数量的统计
function updateOnlineCount(onlineCount, allCount) {
    // 获取显示连接数量的<span>元素
    var onlineCountElement = document.getElementById("onlineCount");
    var allCountElement = document.getElementById("allCount");
    onlineCountElement.textContent = onlineCount;
    allCountElement.textContent = allCount;
}

// 弹出对话框输入 user_id 和 proxy
function addUser() {
    var userId = prompt("请输入UserID:");
    if (!userId) {
        return
    }
    var proxy = prompt("设置代理 (不使用代理点击取消)");
    if (userId) {
        // 构建带参数的 URL
        var baseUrl = '/client/';
        var url = new URL(baseUrl, window.location.href);
        url.searchParams.append('user_id', userId);
        if (proxy) {
            url.searchParams.append('proxy_url', proxy);
        }
        fetch(url.href, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
        })
        .then(response => {
            if (response.ok) {
                alert('账号添加成功');
                fetchData();
            } else {
                alert('账号添加失败');
            }
        })
        .catch(error => {
            alert('请求错误:', error);
        });
    }
}



function deleteUser(userId) {
    fetch(`/client/${userId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.message === 'success') {
            alert('删除成功');
            // If deletion is successful, reload all data
            fetchData();
        }
    })
    .catch(error => console.error('Error:', error));
}

function deleteAllUser() {
    showLoading();
    fetch(`/client/`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.message === 'success') {
            alert('删除成功');
            // If deletion is successful, reload all data
            fetchData();
        }
        hideLoading();
    })
    .catch(error => {
        console.error('Error:', error);
        hideLoading();
    });
}

function uploadFile() {
    const input = document.createElement('input');
    input.type = 'file';
    input.onchange = function() {
        const file = input.files[0];
        const formData = new FormData();
        formData.append('file', file);
        showLoading();
        fetch('/upload/', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (response.ok) {
                alert('文件上传成功');
                fetchData()
            } else {
                alert('文件上传失败！');
            }
            hideLoading();
        })
        .catch(error => {
            console.error('Error:', error);
            hideLoading();
        });
    };
    input.click();
}

// Function to close the modal
function closeModal() {
    document.getElementById('logsModal').style.display = 'none';
}


// 模拟数据请求的函数 fetchData，您需要根据实际情况替换为您的数据请求逻辑
function fetchData() {
    return new Promise((resolve, reject) => {
        // Make a GET request to the API endpoint
    fetch('/client/')
    .then(response => response.json())
    .then(data => {
        const statusMap = {
            0: '未连接',
            1: '连接中',
            2: '已连接',
            3: '已停止'
        };
        let counter = 0; // 初始编号为1
        let onlineCounter = 0;
        const tableBody = document.querySelector('#data-table tbody');
        // Clear existing data in the table
        tableBody.innerHTML = '';

        data.data.forEach(item => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${counter+1}</td>
                <td>${item.user_id}</td>
                <td class="proxy">${item.proxy_url || ''}</td>
                <td class="status-${item.status}">${statusMap[item.status]}</td>
                <td>
                    <button onclick="showLogs('${item.id}')">日志</button>
                    <button onclick="deleteUser('${item.id}')">删除</button>
                </td>
            `;
            tableBody.appendChild(row);
            counter++;
            if (item.status == 2){
                onlineCounter++
            }
        });
        updateOnlineCount(onlineCounter, counter);
        resolve();
    })
    .catch(error => console.error('Error:', error))
    });
}

function fetchDataInterval(){
    fetchData().then(() => {
        // 数据请求完成后等待5秒再发起下一次请求
        setTimeout(fetchDataInterval, 5000);
    });
}

function showLoading() {
    document.getElementById('loading').style.display = 'block';
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}


fetchDataInterval()
