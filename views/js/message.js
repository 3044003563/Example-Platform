class MessageManager {
    constructor() {
        // 单例模式
        if (MessageManager.instance) {
            return MessageManager.instance;
        }
        MessageManager.instance = this;
        
        // 检查是否已经存在消息容器
        const existingHost = document.getElementById('message-host');
        if (existingHost) {
            // 如果已存在，直接使用
            this.container = existingHost.shadowRoot.querySelector('.message-container');
        } else {
            // 初始化消息容器
            this.initContainer();
        }
    }

    // 消息类型定义
    static types = {
        SUCCESS: 'success',
        ERROR: 'error',
        WARNING: 'warning',
        INFO: 'info',
        PROGRESS: 'progress'  // 添加进度条类型
    };

    // 初始化全局消息容器
    initContainer() {
        // 创建一个 shadow DOM 来封装消息样式和容器
        const shadowHost = document.createElement('div');
        shadowHost.id = 'message-host';
        document.body.appendChild(shadowHost);

        const shadow = shadowHost.attachShadow({ mode: 'open' });

        // 添加样式
        const style = document.createElement('style');
        style.textContent = `
            .message-container {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                transform: none;
                z-index: 9999;
                pointer-events: none;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                display: flex;
                flex-direction: column;
                align-items: center;
                font-size: 12px !important;  /* 设置基础字体大小 */
            }

            .message {
                display: flex;
                align-items: center;
                padding: 8px 16px;  /* 减小内边距 */
                margin-bottom: 8px;  /* 减小外边距 */
                border-radius: 4px;
                box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
                background: white;
                opacity: 0;
                transform: translateY(-20px);
                transition: all 0.3s ease;
                min-width: 60px;
                max-width: 300px;
                width: fit-content;
                font-size: 12px !important;  /* 消息文本大小 */
            }

            .message span {
                white-space: normal;
                word-break: break-word;
                font-size: 12px !important;  /* 确保文本大小 */
            }

            .message.show {
                opacity: 1;
                transform: translateY(0);
            }

            .message-icon {
                margin-right: 8px;
                font-size: 14px !important;  /* 调整图标大小 */
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .message-success {
                background: #f0f9eb;
                color: #67c23a;
                border-left: 4px solid #67c23a;  /* 添加左边框 */
            }

            /* 成功图标特殊样式 */
            .message-success .message-icon {
                color: #67c23a;
            }

             /* 添加图标动画效果 */
            @keyframes checkmark {
                0% {
                    transform: scale(0);
                }
                50% {
                    transform: scale(1.2);
                }
                100% {
                    transform: scale(1);
                }
            }

            
            @keyframes shake {
                0%, 100% { transform: translateX(0); }
                25% { transform: translateX(-3px); }
                75% { transform: translateX(3px); }
            }

            @keyframes bounce {
                0%, 100% { transform: translateY(0); }
                50% { transform: translateY(-3px); }
            }

            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }


            .message-success .message-icon {
                animation: checkmark 0.3s ease-in-out;
            }

            .message-error {
                background: #fef0f0;
                color: #f56c6c;
                border-left: 4px solid #f56c6c;
            }
            .message-error .message-icon {
                color: #f56c6c;
                animation: shake 0.3s ease-in-out;
            }


            .message-warning {
                background: #fdf6ec;
                color: #e6a23c;
                border-left: 4px solid #e6a23c;
            }
            
            .message-warning .message-icon {
                color: #e6a23c;
                animation: bounce 0.3s ease-in-out;
            }


            .message-info {
                background: #f4f4f5;
                color: #909399;
                border-left: 4px solid #909399;
            }

            .message-info .message-icon {
                color: #909399;
                animation: fadeIn 0.3s ease-in-out;
            }


            .dialog {
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: white;
                padding: 20px;  /* 减小内边距 */
                border-radius: 4px;
                box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
                min-width: 380px;
                max-width: 90vw;
                pointer-events: auto;
                z-index: 10001;
                font-size: 12px !important;  /* 对话框基础字体大小 */
            }

            .dialog-header {
                margin-bottom: 20px;
            }

            .dialog-title {
                display: flex;
                align-items: center;
                font-size: 14px !important;  /* 标题字体稍大 */
                font-weight: 500;
                color: #303133;
                margin: 0;
                padding-bottom: 12px;
                border-bottom: 1px solid #ebeef5;
            }

            .dialog-title .message-icon {
                margin-right: 8px;
                font-size: 14px !important;  /* 标题图标大小 */
            }

            .dialog-mask {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.3);
                z-index: 10000;
                opacity: 0;
                transition: opacity 0.3s ease;
                pointer-events: auto;
            }

            .dialog-mask.show {
                opacity: 1;
            }

            .dialog.show {
                opacity: 1;
                transform: translate(-50%, -50%) scale(1);
            }

            .dialog-content {
                font-size: 12px !important;  /* 内容字体大小 */
                line-height: 1.5;
                color: #606266;
                margin: 16px 0;
                word-break: break-word;
            }

            .dialog-buttons {
                display: flex;
                justify-content: flex-end;
                gap: 12px;
                margin-top: 30px;
            }

            .dialog-button {
                padding: 6px 16px;  /* 减小按钮内边距 */
                border-radius: 4px;
                border: none;
                cursor: pointer;
                font-size: 12px !important;  /* 按钮字体大小 */
                transition: all 0.3s;
                height: 24px;  /* 固定按钮高度 */
                line-height: 1;
            }

            .dialog-confirm {
                background: #409eff;
                color: white;
                font-weight: 500;
            }

            .dialog-confirm:hover {
                background: #66b1ff;
            }

            .dialog-cancel {
                background: #f4f4f5;
                color: #606266;
                border: 1px solid #dcdfe6;
            }

            .dialog-cancel:hover {
                color: #409eff;
                border-color: #c6e2ff;
                background-color: #ecf5ff;
            }


            .message-progress {
                background: #e1f3ff;
                color: #409eff;
                padding-right: 40px;
                min-width: 120px; /* 最小宽度 */
                max-width: 300px; /* 最大宽度限制 */
                width: fit-content; /* 根据内容自适应宽度 */
            }

            .progress-spinner {
                display: inline-block;
                width: 16px;
                height: 16px;
                border: 2px solid #409eff;
                border-top-color: transparent;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }

            @keyframes spin {
                to { transform: rotate(360deg); }
            }

            .link-btn {
                color: #1890ff;
                text-decoration: none;
                font-size: 12px;
                cursor: pointer;
                margin: 0 6px;  /* 添加左右间距 */
            }

            .link-btn:hover {
                color: #40a9ff;
            }

            .link-btn.delete {
                color: #ff4d4f;
            }

            .link-btn.delete:hover {
                color: #ff7875;
            }

            /* 移除之前的 separator 相关样式 */
            .separator {
                display: none;
            }

            /* 确保表头的操作列也居中 */
            .item-table th:last-child {
                text-align: center;
            }
        `;

        // 创建容器
        const container = document.createElement('div');
        container.className = 'message-container';

        // 添加到 shadow DOM
        shadow.appendChild(style);
        shadow.appendChild(container);

        this.container = container;
    }



    
    // 添加显示进度条消息的方法
    showProgress(content) {
        const messageElement = document.createElement('div');
        messageElement.className = `message message-progress`;
        
        // 添加加载图标
        const spinner = document.createElement('div');
        spinner.className = 'progress-spinner message-icon';
        messageElement.appendChild(spinner);

        // 添加文本
        const textSpan = document.createElement('span');
        textSpan.textContent = content;
        messageElement.appendChild(textSpan);

        // 添加到容器
        this.container.appendChild(messageElement);

        // 添加动画类
        setTimeout(() => messageElement.classList.add('show'), 10);

        // 返回关闭函数
        return () => {
            messageElement.classList.remove('show');
            setTimeout(() => messageElement.remove(), 300);
        };
    }

    // 获取单例实例
    static getInstance() {
        if (!MessageManager.instance) {
            return new MessageManager();
        }
        return MessageManager.instance;
    }

    // 添加静态方法
    static showProgress(content) {
        return MessageManager.getInstance().showProgress(content);
    }

   

    // 修改 confirm 方法的实现
    confirm(options) {
        const {
            title = '提示',
            content = '',
            confirmText = '确定',
            cancelText = '取消',
            type = MessageManager.types.INFO
        } = options;

        return new Promise((resolve) => {
            const mask = document.createElement('div');
            mask.className = 'dialog-mask';
            
            const dialog = document.createElement('div');
            dialog.className = 'dialog';
            
            // 修改 dialog 的 HTML 结构，添加图标
            dialog.innerHTML = `
                <div class="dialog-header">
                    <div class="dialog-title">
                        <i class="fas ${this.getIconClass(type)} message-icon"></i>
                        <span>${title}</span>
                    </div>
                </div>
                <div class="dialog-content">${content}</div>
                <div class="dialog-buttons">
                    <button class="dialog-button dialog-cancel">${cancelText}</button>
                    <button class="dialog-button dialog-confirm">${confirmText}</button>
                </div>
            `;

            // 添加到容器
            this.container.appendChild(mask);
            this.container.appendChild(dialog);

            // 显示动画
            requestAnimationFrame(() => {
                mask.classList.add('show');
                dialog.classList.add('show');
            });

            // 关闭对话框
            const close = (result) => {
                mask.classList.remove('show');
                dialog.classList.remove('show');
                setTimeout(() => {
                    mask.remove();
                    dialog.remove();
                    resolve(result);
                }, 300);
            };

            // 绑定按钮事件
            dialog.querySelector('.dialog-confirm').onclick = () => close(true);
            dialog.querySelector('.dialog-cancel').onclick = () => close(false);
            mask.onclick = () => close(false);
        });
    }


     
 

    // 修改 show 方法，添加图标动画
    show(content, type = MessageManager.types.INFO, duration = 3000) {
        const messageElement = document.createElement('div');
        messageElement.className = `message message-${type}`;
        
        // 添加图标
        const icon = document.createElement('i');
        icon.className = `fas ${this.getIconClass(type)} message-icon`;
        messageElement.appendChild(icon);

        // 添加文本
        const textSpan = document.createElement('span');
        textSpan.textContent = content;
        messageElement.appendChild(textSpan);

        // 添加到容器
        this.container.appendChild(messageElement);

        // 添加动画类
        requestAnimationFrame(() => {
            messageElement.classList.add('show');
            // 重置图标动画
            icon.style.animation = 'none';
            icon.offsetHeight; // 触发重排
            icon.style.animation = null;
        });

        // 自动移除
        setTimeout(() => {
            messageElement.classList.remove('show');
            setTimeout(() => messageElement.remove(), 300);
        }, duration);
    }

    getIconClass(type) {
        switch (type) {
            case MessageManager.types.SUCCESS:
                return 'fa-check-circle';
            case MessageManager.types.ERROR:
                return 'fa-times-circle';
            case MessageManager.types.WARNING:
                return 'fa-exclamation-circle';
            default:
                return 'fa-info-circle';
        }
    }

    // 静态方法：成功消息
    static success(content, duration) {
        MessageManager.getInstance().show(content, MessageManager.types.SUCCESS, duration);
    }

    // 静态方法：错误消息
    static error(content, duration) {
        MessageManager.getInstance().show(content, MessageManager.types.ERROR, duration);
    }

    // 静态方法：警告消息
    static warning(content, duration) {
        MessageManager.getInstance().show(content, MessageManager.types.WARNING, duration);
    }

    // 静态方法：信息消息
    static info(content, duration) {
        MessageManager.getInstance().show(content, MessageManager.types.INFO, duration);
    }

    

    // 修改静态方法
    static confirm(options) {
        return MessageManager.getInstance().confirm(options);
    }

}

// 导出为全局变量
window.Message = MessageManager;