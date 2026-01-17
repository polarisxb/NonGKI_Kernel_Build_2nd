
import os

patches_dir = r"c:\Users\32304\Desktop\dipper\NonGKI_Kernel_Build_2nd\Patches\mi8_dipper"
os.makedirs(patches_dir, exist_ok=True)

# Helper to write files with specific content
def write_patch(filename, content):
    path = os.path.join(patches_dir, filename)
    with open(path, 'w', newline='\n') as f:
        f.write(content)
    print(f"Generated {path}")

# 01_exec_hook.patch
# Note: Context lines match fs/exec.c
p01 = """diff --git a/fs/exec.c b/fs/exec.c
--- a/fs/exec.c
+++ b/fs/exec.c
@@ -57,6 +57,9 @@
 #include <linux/oom.h>
 #include <linux/compat.h>
 #include <linux/vmalloc.h>
+#ifdef CONFIG_KSU_SUSFS
+#include <linux/susfs_def.h>
+#endif
 
 #include <asm/uaccess.h>
 #include <asm/mmu_context.h>
@@ -1673,6 +1676,18 @@ static int exec_binprm(struct linux_binprm *bprm)
 	return ret;
 }
 
+#ifdef CONFIG_KSU_SUSFS
+extern bool ksu_execveat_hook __read_mostly;
+extern bool ksu_su_compat_enabled __read_mostly;
+extern bool susfs_is_boot_completed_triggered __read_mostly;
+extern bool __ksu_is_allow_uid_for_current(uid_t uid);
+extern int ksu_handle_execveat(int *fd, struct filename **filename_ptr, void *argv, void *envp, int *flags);
+extern int ksu_handle_execveat_sucompat(int *fd, struct filename **filename_ptr, void *argv, void *envp, int *flags);
+#elif defined(CONFIG_KSU)
+extern bool ksu_execveat_hook __read_mostly;
+extern int ksu_handle_execveat(int *fd, struct filename **filename_ptr, void *argv, void *envp, int *flags);
+extern int ksu_handle_execveat_sucompat(int *fd, struct filename **filename_ptr, void *argv, void *envp, int *flags);
+#endif
+
 /*
  * sys_execve() executes a new program.
  */
@@ -1697,6 +1712,23 @@ static int do_execveat_common(int fd, struct filename *filename,
 	struct files_struct *displaced;
 	int retval;
 
+#ifdef CONFIG_KSU_SUSFS
+	if (likely(susfs_is_current_proc_umounted()) || !ksu_su_compat_enabled) {
+		goto orig_flow;
+	}
+	if (unlikely(ksu_execveat_hook || !susfs_is_boot_completed_triggered)) {
+		ksu_handle_execveat(&fd, &filename, &argv, &envp, &flags);
+	} else if (unlikely(__ksu_is_allow_uid_for_current(current_uid().val))) {
+		ksu_handle_execveat_sucompat(&fd, &filename, &argv, &envp, &flags);
+	}
+orig_flow:
+#elif defined(CONFIG_KSU)
+	if (unlikely(ksu_execveat_hook))
+		ksu_handle_execveat(&fd, &filename, &argv, &envp, &flags);
+	else
+		ksu_handle_execveat_sucompat(&fd, &filename, &argv, &envp, &flags);
+#endif
+
 	if (IS_ERR(filename))
"""
write_patch("01_exec_hook.patch", p01)

# 02_open_hook.patch
p02 = """diff --git a/fs/open.c b/fs/open.c
--- a/fs/open.c
+++ b/fs/open.c
@@ -31,6 +31,9 @@
 #include <linux/ima.h>
 #include <linux/dnotify.h>
 #include <linux/compat.h>
+#ifdef CONFIG_KSU_SUSFS
+#include <linux/susfs_def.h>
+#endif
 
 #include "internal.h"
 
@@ -355,6 +358,14 @@ SYSCALL_DEFINE4(fallocate, int, fd, int, mode, loff_t, offset, loff_t, len)
 	return error;
 }
 
+#ifdef CONFIG_KSU_SUSFS
+extern bool ksu_su_compat_enabled __read_mostly;
+extern bool __ksu_is_allow_uid_for_current(uid_t uid);
+__attribute__((hot))
+extern int ksu_handle_faccessat(int *dfd, const char __user **filename_user, int *mode, int *flags);
+#elif defined(CONFIG_KSU)
+__attribute__((hot))
+extern int ksu_handle_faccessat(int *dfd, const char __user **filename_user, int *mode, int *flags);
+#endif
+
 /*
  * access() needs to use the real uid/gid, not the effective uid/gid.
  * We do this by temporarily clearing all FS-related capabilities and
@@ -375,6 +386,16 @@ SYSCALL_DEFINE3(faccessat, int, dfd, const char __user *, filename, int, mode)
 	int res;
 	unsigned int lookup_flags = LOOKUP_FOLLOW;
 
+#ifdef CONFIG_KSU_SUSFS
+	if (likely(susfs_is_current_proc_umounted()) || !ksu_su_compat_enabled) {
+		goto orig_flow;
+	}
+	if (unlikely(__ksu_is_allow_uid_for_current(current_uid().val))) {
+		ksu_handle_faccessat(&dfd, &filename, &mode, NULL);
+	}
+orig_flow:
+#elif defined(CONFIG_KSU)
+	ksu_handle_faccessat(&dfd, &filename, &mode, NULL);
+#endif
+
 	if (mode & ~S_IFMT & ~S_IRWXO & ~S_IRWXG & ~S_IRWXU)
 		return -EINVAL;
"""
write_patch("02_open_hook.patch", p02)

# 03_read_write_hook.patch
p03 = """diff --git a/fs/read_write.c b/fs/read_write.c
--- a/fs/read_write.c
+++ b/fs/read_write.c
@@ -456,6 +456,13 @@ ssize_t __vfs_read(struct file *file, char __user *buf, size_t count,
 }
 EXPORT_SYMBOL(__vfs_read);
 
+#ifdef CONFIG_KSU_SUSFS
+extern bool ksu_vfs_read_hook __read_mostly;
+__attribute__((cold))
+extern int ksu_handle_vfs_read(struct file **file_ptr, char __user **buf_ptr, size_t *count_ptr, loff_t **pos);
+#elif defined(CONFIG_KSU)
+extern bool ksu_vfs_read_hook __read_mostly;
+__attribute__((cold))
+extern int ksu_handle_vfs_read(struct file **file_ptr, char __user **buf_ptr, size_t *count_ptr, loff_t **pos);
+#endif
+
 ssize_t vfs_read(struct file *file, char __user *buf, size_t count, loff_t *pos)
 {
 	ssize_t ret;
 
+#if defined(CONFIG_KSU_SUSFS) || defined(CONFIG_KSU)
+	if (unlikely(ksu_vfs_read_hook))
+		ksu_handle_vfs_read(&file, &buf, &count, &pos);
+#endif
+
 	if (!(file->f_mode & FMODE_READ))
 		return -EBADF;
"""
write_patch("03_read_write_hook.patch", p03)

# 04_stat_hook.patch
p04 = """diff --git a/fs/stat.c b/fs/stat.c
--- a/fs/stat.c
+++ b/fs/stat.c
@@ -15,6 +15,9 @@
 #include <linux/syscalls.h>
 #include <linux/pagemap.h>
 
+#ifdef CONFIG_KSU_SUSFS
+#include <linux/susfs_def.h>
+#endif
 #include <asm/uaccess.h>
 #include <asm/unistd.h>
 
@@ -87,6 +90,15 @@ int vfs_fstat(unsigned int fd, struct kstat *stat)
 }
 EXPORT_SYMBOL(vfs_fstat);
 
+#ifdef CONFIG_KSU_SUSFS
+extern bool ksu_su_compat_enabled __read_mostly;
+extern bool __ksu_is_allow_uid_for_current(uid_t uid);
+__attribute__((hot))
+extern int ksu_handle_stat(int *dfd, const char __user **filename_user, int *flags);
+#elif defined(CONFIG_KSU)
+__attribute__((hot))
+extern int ksu_handle_stat(int *dfd, const char __user **filename_user, int *flags);
+#endif
+
 int vfs_fstatat(int dfd, const char __user *filename, struct kstat *stat,
 		int flag)
 {
@@ -98,6 +110,16 @@ int vfs_fstatat(int dfd, const char __user *filename, struct kstat *stat,
 	int error = -EINVAL;
 	unsigned int lookup_flags = 0;
 
+#ifdef CONFIG_KSU_SUSFS
+	if (likely(susfs_is_current_proc_umounted()) || !ksu_su_compat_enabled) {
+		goto orig_flow;
+	}
+	if (unlikely(__ksu_is_allow_uid_for_current(current_uid().val))) {
+		ksu_handle_stat(&dfd, &filename, &flag);
+	}
+orig_flow:
+#elif defined(CONFIG_KSU)
+	ksu_handle_stat(&dfd, &filename, &flag);
+#endif
+
 	if ((flag & ~(AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT |
 		      AT_NO_AUTOMOUNT | AT_EMPTY_PATH)) != 0)
 		return -EINVAL;
@@ -309,6 +331,10 @@ SYSCALL_DEFINE2(newlstat, const char __user *, filename,
 	return cp_new_stat(&stat, statbuf);
 }
 
+#ifdef CONFIG_KSU
+extern void ksu_handle_newfstat_ret(unsigned int *fd, struct stat __user **statbuf_ptr);
+#endif
+
 SYSCALL_DEFINE2(newfstat, unsigned int, fd, struct stat __user *, statbuf)
 {
 	struct kstat stat;
@@ -317,6 +343,9 @@ SYSCALL_DEFINE2(newfstat, unsigned int, fd, struct stat __user *, statbuf)
 	if (!error)
 		error = cp_new_stat(&stat, statbuf);
 
+#ifdef CONFIG_KSU
+	ksu_handle_newfstat_ret(&fd, &statbuf);
+#endif
 	return error;
 }
 
+#ifdef CONFIG_KSU
+extern void ksu_handle_fstat64_ret(unsigned long *fd, struct stat64 __user **statbuf_ptr);
+#endif
+
 SYSCALL_DEFINE4(readlinkat, int, dfd, const char __user *, pathname,
 		char __user *, buf, int, bufsiz)
 {
@@ -433,6 +462,9 @@ SYSCALL_DEFINE2(fstat64, unsigned long, fd, struct stat64 __user *, statbuf)
 	if (!error)
 		error = cp_new_stat64(&stat, statbuf);
 
+#ifdef CONFIG_KSU
+	ksu_handle_fstat64_ret(&fd, &statbuf);
+#endif
 	return error;
 }
"""
write_patch("04_stat_hook.patch", p04)

# 05_input_hook.patch
p05 = """diff --git a/drivers/input/input.c b/drivers/input/input.c
--- a/drivers/input/input.c
+++ b/drivers/input/input.c
@@ -377,6 +377,15 @@ static int input_get_disposition(struct input_dev *dev,
 	return disposition;
 }
 
+#ifdef CONFIG_KSU_SUSFS
+extern bool ksu_input_hook __read_mostly;
+extern int ksu_handle_input_handle_event(unsigned int *type, unsigned int *code, int *value);
+#elif defined(CONFIG_KSU)
+extern bool ksu_input_hook __read_mostly;
+extern int ksu_handle_input_handle_event(unsigned int *type, unsigned int *code, int *value);
+#endif
+
 static void input_handle_event(struct input_dev *dev,
 			       unsigned int type, unsigned int code, int value)
 {
@@ -388,6 +397,10 @@ static void input_handle_event(struct input_dev *dev,
 {
 	int disposition = input_get_disposition(dev, type, code, &value);
 
+#if defined(CONFIG_KSU_SUSFS) || defined(CONFIG_KSU)
+	if (unlikely(ksu_input_hook))
+		ksu_handle_input_handle_event(&type, &code, &value);
+#endif
+
 	if ((disposition & INPUT_PASS_TO_DEVICE) && dev->event)
 		dev->event(dev, type, code, value);
"""
write_patch("05_input_hook.patch", p05)
