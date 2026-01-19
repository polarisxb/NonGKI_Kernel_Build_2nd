# 如何正确生成 Git Patch 文件

本文档记录了成功生成可通过 `git apply --check` 验证的 patch 文件的方法。

## 常见问题

1. **Windows 换行符 (CRLF)** - PowerShell 重定向会产生 UTF-16LE 编码
2. **行号不匹配** - 手写补丁时上下文行号与实际源码不符
3. **缺少上下文行** - patch 格式要求每个 hunk 有上下文

---

## ✅ 正确方法：使用 git diff 生成

### 步骤 1: 修改源码文件

直接在内核源码中进行修改，例如：

```c
// kernel/reboot.c - 在 SYSCALL_DEFINE4(reboot) 前添加
#ifdef CONFIG_KSU
extern int ksu_handle_sys_reboot(int magic1, int magic2, unsigned int cmd, void __user **arg);
#endif
```

### 步骤 2: 用 git diff 生成补丁

```bash
cd /path/to/kernel_source
git diff --no-color path/to/file.c > my_hook.patch
```

### 步骤 3: 恢复源码

```bash
git checkout path/to/file.c
```

### 步骤 4: 验证补丁

```bash
git apply --check my_hook.patch
```

无输出 = 通过 ✅

---

## ⚠️ 手写 Patch 的格式要求

如必须手写，请遵循以下格式：

```diff
diff --git a/kernel/reboot.c b/kernel/reboot.c
index 2946ed1..ae3d618 100644
--- a/kernel/reboot.c
+++ b/kernel/reboot.c
@@ -277,6 +277,11 @@ static DEFINE_MUTEX(reboot_mutex);
  *
  * reboot doesn't sync: do that yourself before calling this.
  */
+
+#ifdef CONFIG_KSU
+extern int ksu_handle_sys_reboot(...);
+#endif
+
 SYSCALL_DEFINE4(reboot, int, magic1, int, magic2, unsigned int, cmd,
```

### 关键点

| 元素 | 说明 |
|------|------|
| `@@` 行 | 格式: `@@ -旧行号,行数 +新行号,行数 @@` |
| 空格开头 | 未修改的上下文行（必须以空格开头，不是无字符） |
| `+` 开头 | 新增的行 |
| `-` 开头 | 删除的行 |
| 换行符 | **必须用 Unix LF (`\n`)，不能用 Windows CRLF** |

---

## 编码问题解决

PowerShell 重定向可能产生错误编码，使用以下方法：

```powershell
# 方法1: 使用 cmd 包装
cmd /c "git diff file.c" | Out-File -FilePath patch.patch -Encoding utf8

# 方法2: 直接修改后手动创建文件（推荐）
# 使用 VS Code 或其他编辑器创建，确保 UTF-8 + LF 换行
```

---

## 06_reboot_hook.patch 示例

这是一个成功通过验证的完整示例：

```diff
diff --git a/kernel/reboot.c b/kernel/reboot.c
index 2946ed1..ae3d618 100644
--- a/kernel/reboot.c
+++ b/kernel/reboot.c
@@ -277,6 +277,11 @@ static DEFINE_MUTEX(reboot_mutex);
  *
  * reboot doesn't sync: do that yourself before calling this.
  */
+
+#ifdef CONFIG_KSU
+extern int ksu_handle_sys_reboot(int magic1, int magic2, unsigned int cmd, void __user **arg);
+#endif
+
 SYSCALL_DEFINE4(reboot, int, magic1, int, magic2, unsigned int, cmd,
 		void __user *, arg)
 {
@@ -284,6 +289,10 @@ SYSCALL_DEFINE4(reboot, int, magic1, int, magic2, unsigned int, cmd,
 	char buffer[256];
 	int ret = 0;
 
+#ifdef CONFIG_KSU
+	ksu_handle_sys_reboot(magic1, magic2, cmd, &arg);
+#endif
+
 	/* We only trust the superuser with rebooting the system. */
 	if (!ns_capable(pid_ns->user_ns, CAP_SYS_BOOT))
 		return -EPERM;
```

---

## 调试技巧

```bash
# 查看补丁应用预览
git apply --stat my.patch

# 详细检查
git apply --check -v my.patch

# 查看文件编码 (PowerShell)
Get-Content my.patch | Format-Hex | Select-Object -First 10
# 应该看到 0A (LF)，不是 0D 0A (CRLF)
```
