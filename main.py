"""
PinPrompt - Prompt 分类管理工具
功能：分类存储 prompt、窗口置顶、一键复制
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import pyperclip
from datetime import datetime

# 数据文件路径
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts.json")

class PinPromptApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PinPrompt - Prompt管理工具")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # 置顶状态
        self.always_on_top = tk.BooleanVar(value=False)
        
        # 数据
        self.data = self.load_data()
        self.current_category = None
        
        # 创建UI
        self.create_ui()
        
        # 加载分类
        self.refresh_categories()
        
    def load_data(self):
        """加载数据"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {"categories": {}}
        return {"categories": {}}
    
    def save_data(self):
        """保存数据"""
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def create_ui(self):
        """创建UI"""
        # 顶部工具栏
        toolbar = ttk.Frame(self.root, padding=5)
        toolbar.pack(fill=tk.X)
        
        ttk.Button(toolbar, text="➕ 新建分类", command=self.add_category).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📝 新建Prompt", command=self.add_prompt).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🗑️ 删除分类", command=self.delete_category).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # 置顶按钮
        self.top_btn = ttk.Checkbutton(
            toolbar, 
            text="📌 窗口置顶", 
            variable=self.always_on_top,
            command=self.toggle_on_top
        )
        self.top_btn.pack(side=tk.LEFT, padx=2)
        
        # 主内容区
        main_frame = ttk.Frame(self.root, padding=5)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：分类列表
        left_frame = ttk.LabelFrame(main_frame, text="分类", padding=5)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        
        self.category_listbox = tk.Listbox(left_frame, width=20, font=("Microsoft YaHei", 10))
        self.category_listbox.pack(fill=tk.BOTH, expand=True)
        self.category_listbox.bind('<<ListboxSelect>>', self.on_category_select)
        
        # 右侧：Prompt列表
        right_frame = ttk.LabelFrame(main_frame, text="Prompts", padding=5)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 创建Canvas和Scrollbar实现滚动
        self.canvas = tk.Canvas(right_frame, bg="#f5f5f5")
        scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 鼠标滚轮绑定
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # 底部状态栏
        self.status_bar = ttk.Label(self.root, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
    def _on_mousewheel(self, event):
        """鼠标滚轮事件"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def toggle_on_top(self):
        """切换置顶状态"""
        self.root.attributes('-topmost', self.always_on_top.get())
        status = "已置顶" if self.always_on_top.get() else "取消置顶"
        self.status_bar.config(text=status)
    
    def refresh_categories(self):
        """刷新分类列表"""
        self.category_listbox.delete(0, tk.END)
        for cat in sorted(self.data["categories"].keys()):
            self.category_listbox.insert(tk.END, f"📁 {cat}")
    
    def on_category_select(self, event):
        """选择分类"""
        selection = self.category_listbox.curselection()
        if selection:
            idx = selection[0]
            cat_name = list(sorted(self.data["categories"].keys()))[idx]
            self.current_category = cat_name
            self.refresh_prompts()
            self.status_bar.config(text=f"当前分类: {cat_name}")
    
    def refresh_prompts(self):
        """刷新Prompt列表"""
        # 清空现有内容
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        if not self.current_category or self.current_category not in self.data["categories"]:
            return
        
        prompts = self.data["categories"][self.current_category].get("prompts", [])
        
        if not prompts:
            ttk.Label(self.scrollable_frame, text="暂无Prompt，点击「新建Prompt」添加", 
                     font=("Microsoft YaHei", 10)).pack(pady=20)
            return
        
        for i, prompt in enumerate(prompts):
            self.create_prompt_card(prompt, i)
    
    def create_prompt_card(self, prompt, index):
        """创建Prompt卡片"""
        frame = ttk.Frame(self.scrollable_frame, padding=10)
        frame.pack(fill=tk.X, pady=5, padx=5)
        
        # 标题行
        title_frame = ttk.Frame(frame)
        title_frame.pack(fill=tk.X)
        
        ttk.Label(title_frame, text=prompt.get("title", "无标题"), 
                 font=("Microsoft YaHei", 11, "bold")).pack(side=tk.LEFT)
        
        # 按钮组
        btn_frame = ttk.Frame(title_frame)
        btn_frame.pack(side=tk.RIGHT)
        
        # 复制按钮
        copy_btn = ttk.Button(btn_frame, text="📋 复制", width=8,
                             command=lambda: self.copy_prompt(prompt.get("content", "")))
        copy_btn.pack(side=tk.LEFT, padx=2)
        
        # 编辑按钮
        edit_btn = ttk.Button(btn_frame, text="✏️ 编辑", width=8,
                             command=lambda: self.edit_prompt(index))
        edit_btn.pack(side=tk.LEFT, padx=2)
        
        # 删除按钮
        del_btn = ttk.Button(btn_frame, text="🗑️", width=4,
                            command=lambda: self.delete_prompt(index))
        del_btn.pack(side=tk.LEFT, padx=2)
        
        # 内容预览
        content = prompt.get("content", "")
        preview = content[:200] + "..." if len(content) > 200 else content
        
        content_label = ttk.Label(frame, text=preview, font=("Microsoft YaHei", 9),
                                 wraplength=500, justify=tk.LEFT)
        content_label.pack(fill=tk.X, pady=(5, 0))
        
        # 分隔线
        ttk.Separator(self.scrollable_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=2)
    
    def copy_prompt(self, content):
        """复制Prompt到剪贴板"""
        try:
            pyperclip.copy(content)
            self.status_bar.config(text="✅ 已复制到剪贴板")
            messagebox.showinfo("成功", "Prompt已复制到剪贴板！")
        except Exception as e:
            # 备用方案
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.status_bar.config(text="✅ 已复制到剪贴板")
            messagebox.showinfo("成功", "Prompt已复制到剪贴板！")
    
    def add_category(self):
        """添加分类"""
        name = simpledialog.askstring("新建分类", "请输入分类名称:", parent=self.root)
        if name:
            if name in self.data["categories"]:
                messagebox.showwarning("警告", "分类已存在！")
                return
            self.data["categories"][name] = {"prompts": []}
            self.save_data()
            self.refresh_categories()
            self.status_bar.config(text=f"已创建分类: {name}")
    
    def delete_category(self):
        """删除分类"""
        if not self.current_category:
            messagebox.showwarning("警告", "请先选择一个分类！")
            return
        
        if messagebox.askyesno("确认", f"确定删除分类「{self.current_category}」？\n该分类下所有Prompt将被删除！"):
            del self.data["categories"][self.current_category]
            self.save_data()
            self.current_category = None
            self.refresh_categories()
            self.refresh_prompts()
            self.status_bar.config(text="分类已删除")
    
    def center_window(self, window, width, height):
        """将窗口居中显示"""
        window.update_idletasks()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f'{width}x{height}+{x}+{y}')
    
    def add_prompt(self):
        """添加Prompt"""
        if not self.current_category:
            messagebox.showwarning("警告", "请先选择一个分类！")
            return
        
        # 创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("新建Prompt")
        self.center_window(dialog, 500, 400)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 主内容区
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 标题
        ttk.Label(main_frame, text="标题:").pack(anchor=tk.W)
        title_entry = ttk.Entry(main_frame, font=("Microsoft YaHei", 10))
        title_entry.pack(fill=tk.X, pady=(0, 10))
        
        # 内容
        ttk.Label(main_frame, text="内容:").pack(anchor=tk.W)
        content_text = tk.Text(main_frame, font=("Microsoft YaHei", 10))
        content_text.pack(fill=tk.BOTH, expand=True)
        
        def save():
            title = title_entry.get().strip()
            content = content_text.get("1.0", tk.END).strip()
            
            if not title or not content:
                messagebox.showwarning("警告", "标题和内容不能为空！")
                return
            
            self.data["categories"][self.current_category]["prompts"].append({
                "title": title,
                "content": content,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            self.save_data()
            self.refresh_prompts()
            dialog.destroy()
            self.status_bar.config(text=f"已添加Prompt: {title}")
        
        # 底部按钮区（固定在底部）
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text="保存 (Ctrl+S)", command=save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        # 绑定 Ctrl+S 快捷键
        dialog.bind('<Control-s>', lambda e: save())
        dialog.bind('<Control-S>', lambda e: save())
        
        # 焦点设置到标题输入框
        title_entry.focus_set()
    
    def edit_prompt(self, index):
        """编辑Prompt"""
        prompts = self.data["categories"][self.current_category]["prompts"]
        prompt = prompts[index]
        
        # 创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("编辑Prompt")
        self.center_window(dialog, 500, 400)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 主内容区
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 标题
        ttk.Label(main_frame, text="标题:").pack(anchor=tk.W)
        title_entry = ttk.Entry(main_frame, font=("Microsoft YaHei", 10))
        title_entry.insert(0, prompt.get("title", ""))
        title_entry.pack(fill=tk.X, pady=(0, 10))
        
        # 内容
        ttk.Label(main_frame, text="内容:").pack(anchor=tk.W)
        content_text = tk.Text(main_frame, font=("Microsoft YaHei", 10))
        content_text.insert("1.0", prompt.get("content", ""))
        content_text.pack(fill=tk.BOTH, expand=True)
        
        def save():
            title = title_entry.get().strip()
            content = content_text.get("1.0", tk.END).strip()
            
            if not title or not content:
                messagebox.showwarning("警告", "标题和内容不能为空！")
                return
            
            prompts[index] = {
                "title": title,
                "content": content,
                "created": prompt.get("created", ""),
                "modified": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            self.save_data()
            self.refresh_prompts()
            dialog.destroy()
            self.status_bar.config(text=f"已更新Prompt: {title}")
        
        # 底部按钮区（固定在底部）
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text="保存 (Ctrl+S)", command=save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        # 绑定 Ctrl+S 快捷键
        dialog.bind('<Control-s>', lambda e: save())
        dialog.bind('<Control-S>', lambda e: save())
        
        # 焦点设置到标题输入框
        title_entry.focus_set()
    
    def delete_prompt(self, index):
        """删除Prompt"""
        if messagebox.askyesno("确认", "确定删除此Prompt？"):
            del self.data["categories"][self.current_category]["prompts"][index]
            self.save_data()
            self.refresh_prompts()
            self.status_bar.config(text="Prompt已删除")

def main():
    root = tk.Tk()
    
    # 设置窗口图标（可选）
    try:
        root.iconbitmap("icon.ico")
    except:
        pass
    
    app = PinPromptApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
