#!/usr/bin/env python3
"""
Generate kernel hook patches with mathematically correct hunk headers.
Key: Carefully count context (space-prefix) and added (+prefix) lines.
"""
import os

patches_dir = r"c:\Users\32304\Desktop\dipper\NonGKI_Kernel_Build_2nd\Patches\mi8_dipper"
os.makedirs(patches_dir, exist_ok=True)

def make_hunk(old_start, context_before, additions, context_after):
    """
    Generate a complete hunk with correct header.
    context_before/after: lists of strings (original file content, will get ' ' prefix)
    additions: list of strings (new content, will get '+' prefix)
    """
    old_count = len(context_before) + len(context_after)
    new_count = len(context_before) + len(additions) + len(context_after)
    new_start = old_start + (len(additions) - 0)  # Simplified, actual offset calculated later
    
    lines = []
    # Header (we'll calculate new_start based on cumulative offset in caller)
    # For now, placeholder - we'll fix this
    
    for line in context_before:
        lines.append(' ' + line)
    for line in additions:
        lines.append('+' + line)
    for line in context_after:
        lines.append(' ' + line)
    
    return old_count, new_count, lines

def write_patch(filename, content):
    path = os.path.join(patches_dir, filename)
    # Ensure LF line endings
    with open(path, 'w', newline='\n') as f:
        f.write(content)
    print(f"Generated: {path}")

# =============================================================================
# 01_exec_hook.patch
# =============================================================================
# NOTE: Using TAB (\t) for kernel code indentation

patch_01_lines = []
patch_01_lines.append("diff --git a/fs/exec.c b/fs/exec.c")
patch_01_lines.append("--- a/fs/exec.c")
patch_01_lines.append("+++ b/fs/exec.c")

# --- Hunk 1: Add include ---
# Context: 3 lines before, 3 lines after
# Added: 3 lines
# OLD: 6, NEW: 9
patch_01_lines.append("@@ -57,6 +57,9 @@")
patch_01_lines.append(" #include <linux/oom.h>")
patch_01_lines.append(" #include <linux/compat.h>")
patch_01_lines.append(" #include <linux/vmalloc.h>")
patch_01_lines.append("+#ifdef CONFIG_KSU_SUSFS")
patch_01_lines.append("+#include <linux/susfs_def.h>")
patch_01_lines.append("+#endif")
patch_01_lines.append(" ")
patch_01_lines.append(" #include <asm/uaccess.h>")
patch_01_lines.append(" #include <asm/mmu_context.h>")

# --- Hunk 2: Add extern declarations after exec_binprm ---
# Context before: 3 lines (return ret; } blank)
# Added: 13 lines (ifdef to blank)
# Context after: 3 lines (comment block)
# OLD: 6, NEW: 6 + 13 = 19
patch_01_lines.append("@@ -1673,6 +1676,19 @@ static int exec_binprm(struct linux_binprm *bprm)")
patch_01_lines.append(" \treturn ret;")
patch_01_lines.append(" }")
patch_01_lines.append(" ")
patch_01_lines.append("+#ifdef CONFIG_KSU_SUSFS")
patch_01_lines.append("+extern bool ksu_execveat_hook __read_mostly;")
patch_01_lines.append("+extern bool ksu_su_compat_enabled __read_mostly;")
patch_01_lines.append("+extern bool susfs_is_boot_completed_triggered __read_mostly;")
patch_01_lines.append("+extern bool __ksu_is_allow_uid_for_current(uid_t uid);")
patch_01_lines.append("+extern int ksu_handle_execveat(int *fd, struct filename **filename_ptr, void *argv, void *envp, int *flags);")
patch_01_lines.append("+extern int ksu_handle_execveat_sucompat(int *fd, struct filename **filename_ptr, void *argv, void *envp, int *flags);")
patch_01_lines.append("+#elif defined(CONFIG_KSU)")
patch_01_lines.append("+extern bool ksu_execveat_hook __read_mostly;")
patch_01_lines.append("+extern int ksu_handle_execveat(int *fd, struct filename **filename_ptr, void *argv, void *envp, int *flags);")
patch_01_lines.append("+extern int ksu_handle_execveat_sucompat(int *fd, struct filename **filename_ptr, void *argv, void *envp, int *flags);")
patch_01_lines.append("+#endif")
patch_01_lines.append("+")
patch_01_lines.append(" /*")
patch_01_lines.append("  * sys_execve() executes a new program.")
patch_01_lines.append("  */")

# --- Hunk 3: Add hook call in do_execveat_common ---
# Context before: 3 lines
# Added: 17 lines
# Context after: 1 line
# OLD: 4, NEW: 4 + 17 = 21
patch_01_lines.append("@@ -1697,4 +1713,21 @@ static int do_execveat_common(int fd, struct filename *filename,")
patch_01_lines.append(" \tstruct files_struct *displaced;")
patch_01_lines.append(" \tint retval;")
patch_01_lines.append(" ")
patch_01_lines.append("+#ifdef CONFIG_KSU_SUSFS")
patch_01_lines.append("+\tif (likely(susfs_is_current_proc_umounted()) || !ksu_su_compat_enabled) {")
patch_01_lines.append("+\t\tgoto orig_flow;")
patch_01_lines.append("+\t}")
patch_01_lines.append("+\tif (unlikely(ksu_execveat_hook || !susfs_is_boot_completed_triggered)) {")
patch_01_lines.append("+\t\tksu_handle_execveat(&fd, &filename, &argv, &envp, &flags);")
patch_01_lines.append("+\t} else if (unlikely(__ksu_is_allow_uid_for_current(current_uid().val))) {")
patch_01_lines.append("+\t\tksu_handle_execveat_sucompat(&fd, &filename, &argv, &envp, &flags);")
patch_01_lines.append("+\t}")
patch_01_lines.append("+orig_flow:")
patch_01_lines.append("+#elif defined(CONFIG_KSU)")
patch_01_lines.append("+\tif (unlikely(ksu_execveat_hook))")
patch_01_lines.append("+\t\tksu_handle_execveat(&fd, &filename, &argv, &envp, &flags);")
patch_01_lines.append("+\telse")
patch_01_lines.append("+\t\tksu_handle_execveat_sucompat(&fd, &filename, &argv, &envp, &flags);")
patch_01_lines.append("+#endif")
patch_01_lines.append("+")
patch_01_lines.append(" \tif (IS_ERR(filename))")

write_patch("01_exec_hook.patch", "\n".join(patch_01_lines) + "\n")

# =============================================================================
# 02_open_hook.patch
# =============================================================================
patch_02_lines = []
patch_02_lines.append("diff --git a/fs/open.c b/fs/open.c")
patch_02_lines.append("--- a/fs/open.c")
patch_02_lines.append("+++ b/fs/open.c")

# Hunk 1: include
patch_02_lines.append("@@ -31,6 +31,9 @@")
patch_02_lines.append(" #include <linux/ima.h>")
patch_02_lines.append(" #include <linux/dnotify.h>")
patch_02_lines.append(" #include <linux/compat.h>")
patch_02_lines.append("+#ifdef CONFIG_KSU_SUSFS")
patch_02_lines.append("+#include <linux/susfs_def.h>")
patch_02_lines.append("+#endif")
patch_02_lines.append(" ")
patch_02_lines.append(" #include \"internal.h\"")
patch_02_lines.append(" ")

# Hunk 2: extern declarations (3ctx + 9add + 3ctx = OLD:6, NEW:15)
patch_02_lines.append("@@ -355,6 +358,15 @@ SYSCALL_DEFINE4(fallocate, int, fd, int, mode, loff_t, offset, loff_t, len)")
patch_02_lines.append(" \treturn error;")
patch_02_lines.append(" }")
patch_02_lines.append(" ")
patch_02_lines.append("+#ifdef CONFIG_KSU_SUSFS")
patch_02_lines.append("+extern bool ksu_su_compat_enabled __read_mostly;")
patch_02_lines.append("+extern bool __ksu_is_allow_uid_for_current(uid_t uid);")
patch_02_lines.append("+__attribute__((hot))")
patch_02_lines.append("+extern int ksu_handle_faccessat(int *dfd, const char __user **filename_user, int *mode, int *flags);")
patch_02_lines.append("+#elif defined(CONFIG_KSU)")
patch_02_lines.append("+__attribute__((hot))")
patch_02_lines.append("+extern int ksu_handle_faccessat(int *dfd, const char __user **filename_user, int *mode, int *flags);")
patch_02_lines.append("+#endif")
patch_02_lines.append(" ")
patch_02_lines.append(" /*")
patch_02_lines.append("  * access() needs to use the real uid/gid, not the effective uid/gid.")

# Hunk 3: hook call (3ctx + 11add + 2ctx = OLD:5, NEW:16)
patch_02_lines.append("@@ -375,5 +387,16 @@ SYSCALL_DEFINE3(faccessat, int, dfd, const char __user *, filename, int, mode)")
patch_02_lines.append(" \tint res;")
patch_02_lines.append(" \tunsigned int lookup_flags = LOOKUP_FOLLOW;")
patch_02_lines.append(" ")
patch_02_lines.append("+#ifdef CONFIG_KSU_SUSFS")
patch_02_lines.append("+\tif (likely(susfs_is_current_proc_umounted()) || !ksu_su_compat_enabled) {")
patch_02_lines.append("+\t\tgoto orig_flow;")
patch_02_lines.append("+\t}")
patch_02_lines.append("+\tif (unlikely(__ksu_is_allow_uid_for_current(current_uid().val))) {")
patch_02_lines.append("+\t\tksu_handle_faccessat(&dfd, &filename, &mode, NULL);")
patch_02_lines.append("+\t}")
patch_02_lines.append("+orig_flow:")
patch_02_lines.append("+#elif defined(CONFIG_KSU)")
patch_02_lines.append("+\tksu_handle_faccessat(&dfd, &filename, &mode, NULL);")
patch_02_lines.append("+#endif")
patch_02_lines.append(" ")
patch_02_lines.append(" \tif (mode & ~S_IFMT & ~S_IRWXO & ~S_IRWXG & ~S_IRWXU)")

write_patch("02_open_hook.patch", "\n".join(patch_02_lines) + "\n")

# =============================================================================
# 03_read_write_hook.patch
# =============================================================================
patch_03_lines = []
patch_03_lines.append("diff --git a/fs/read_write.c b/fs/read_write.c")
patch_03_lines.append("--- a/fs/read_write.c")
patch_03_lines.append("+++ b/fs/read_write.c")

# Hunk 1: extern declaration (after EXPORT_SYMBOL(vfs_write))
# Context: EXPORT_SYMBOL(vfs_write) + blank line
# Added: 4 lines
# Context after: static inline loff_t file_pos_read
patch_03_lines.append("@@ -576,2 +576,6 @@ EXPORT_SYMBOL(vfs_write);")
patch_03_lines.append(" ")
patch_03_lines.append("+#if defined(CONFIG_KSU_MANUAL_HOOK) && !defined(CONFIG_KSU_SUSFS)")
patch_03_lines.append("+extern void ksu_handle_sys_read(unsigned int fd);")
patch_03_lines.append("+#endif")
patch_03_lines.append("+")
patch_03_lines.append(" static inline loff_t file_pos_read(struct file *file)")

# Hunk 2: sys_read hook (inside SYSCALL_DEFINE3(read))
# Context: ssize_t ret = -EBADF; + blank line
# Added: 4 lines
# Context after: if (f.file) {
patch_03_lines.append("@@ -592,2 +596,6 @@ SYSCALL_DEFINE3(read, unsigned int, fd, char __user *, buf, size_t, count)")
patch_03_lines.append(" \tssize_t ret = -EBADF;")
patch_03_lines.append(" ")
patch_03_lines.append("+#if defined(CONFIG_KSU_MANUAL_HOOK) && !defined(CONFIG_KSU_SUSFS)")
patch_03_lines.append("+\tksu_handle_sys_read(fd);")
patch_03_lines.append("+#endif")
patch_03_lines.append("+")
patch_03_lines.append(" \tif (f.file) {")

write_patch("03_read_write_hook.patch", "\n".join(patch_03_lines) + "\n")

# =============================================================================
# 04_stat_hook.patch
# =============================================================================
patch_04_lines = []
patch_04_lines.append("diff --git a/fs/stat.c b/fs/stat.c")
patch_04_lines.append("--- a/fs/stat.c")
patch_04_lines.append("+++ b/fs/stat.c")

# Hunk 1: include (3ctx + 3add + 2ctx = OLD:5, NEW:8)
patch_04_lines.append("@@ -15,5 +15,8 @@")
patch_04_lines.append(" #include <linux/syscalls.h>")
patch_04_lines.append(" #include <linux/pagemap.h>")
patch_04_lines.append(" ")
patch_04_lines.append("+#ifdef CONFIG_KSU_SUSFS")
patch_04_lines.append("+#include <linux/susfs_def.h>")
patch_04_lines.append("+#endif")
patch_04_lines.append(" #include <asm/uaccess.h>")
patch_04_lines.append(" #include <asm/unistd.h>")

# Hunk 2: extern (3ctx + 9add + 3ctx = OLD:6, NEW:15)
patch_04_lines.append("@@ -87,6 +90,15 @@ int vfs_fstat(unsigned int fd, struct kstat *stat)")
patch_04_lines.append(" }")
patch_04_lines.append(" EXPORT_SYMBOL(vfs_fstat);")
patch_04_lines.append(" ")
patch_04_lines.append("+#ifdef CONFIG_KSU_SUSFS")
patch_04_lines.append("+extern bool ksu_su_compat_enabled __read_mostly;")
patch_04_lines.append("+extern bool __ksu_is_allow_uid_for_current(uid_t uid);")
patch_04_lines.append("+__attribute__((hot))")
patch_04_lines.append("+extern int ksu_handle_stat(int *dfd, const char __user **filename_user, int *flags);")
patch_04_lines.append("+#elif defined(CONFIG_KSU)")
patch_04_lines.append("+__attribute__((hot))")
patch_04_lines.append("+extern int ksu_handle_stat(int *dfd, const char __user **filename_user, int *flags);")
patch_04_lines.append("+#endif")
patch_04_lines.append(" ")
patch_04_lines.append(" int vfs_fstatat(int dfd, const char __user *filename, struct kstat *stat,")
patch_04_lines.append(" \t\tint flag)")

# Hunk 3: hook call (3ctx + 11add + 2ctx = OLD:5, NEW:16)
patch_04_lines.append("@@ -98,5 +110,16 @@ int vfs_fstatat(int dfd, const char __user *filename, struct kstat *stat,")
patch_04_lines.append(" \tint error = -EINVAL;")
patch_04_lines.append(" \tunsigned int lookup_flags = 0;")
patch_04_lines.append(" ")
patch_04_lines.append("+#ifdef CONFIG_KSU_SUSFS")
patch_04_lines.append("+\tif (likely(susfs_is_current_proc_umounted()) || !ksu_su_compat_enabled) {")
patch_04_lines.append("+\t\tgoto orig_flow;")
patch_04_lines.append("+\t}")
patch_04_lines.append("+\tif (unlikely(__ksu_is_allow_uid_for_current(current_uid().val))) {")
patch_04_lines.append("+\t\tksu_handle_stat(&dfd, &filename, &flag);")
patch_04_lines.append("+\t}")
patch_04_lines.append("+orig_flow:")
patch_04_lines.append("+#elif defined(CONFIG_KSU)")
patch_04_lines.append("+\tksu_handle_stat(&dfd, &filename, &flag);")
patch_04_lines.append("+#endif")
patch_04_lines.append(" ")
patch_04_lines.append(" \tif ((flag & ~(AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT |")

write_patch("04_stat_hook.patch", "\n".join(patch_04_lines) + "\n")

# =============================================================================
# 05_input_hook.patch
# =============================================================================
patch_05_lines = []
patch_05_lines.append("diff --git a/drivers/input/input.c b/drivers/input/input.c")
patch_05_lines.append("--- a/drivers/input/input.c")
patch_05_lines.append("+++ b/drivers/input/input.c")

# Hunk 1: extern (3ctx + 7add + 3ctx = OLD:6, NEW:13)
patch_05_lines.append("@@ -377,6 +377,13 @@ static int input_get_disposition(struct input_dev *dev,")
patch_05_lines.append(" \treturn disposition;")
patch_05_lines.append(" }")
patch_05_lines.append(" ")
patch_05_lines.append("+#ifdef CONFIG_KSU_SUSFS")
patch_05_lines.append("+extern bool ksu_input_hook __read_mostly;")
patch_05_lines.append("+extern int ksu_handle_input_handle_event(unsigned int *type, unsigned int *code, int *value);")
patch_05_lines.append("+#elif defined(CONFIG_KSU)")
patch_05_lines.append("+extern bool ksu_input_hook __read_mostly;")
patch_05_lines.append("+extern int ksu_handle_input_handle_event(unsigned int *type, unsigned int *code, int *value);")
patch_05_lines.append("+#endif")
patch_05_lines.append(" ")
patch_05_lines.append(" static void input_handle_event(struct input_dev *dev,")
patch_05_lines.append(" \t\t\t       unsigned int type, unsigned int code, int value)")

# Hunk 2: hook call (3ctx + 5add + 2ctx = OLD:5, NEW:10)
patch_05_lines.append("@@ -388,5 +395,10 @@ static void input_handle_event(struct input_dev *dev,")
patch_05_lines.append(" {")
patch_05_lines.append(" \tint disposition = input_get_disposition(dev, type, code, &value);")
patch_05_lines.append(" ")
patch_05_lines.append("+#if defined(CONFIG_KSU_SUSFS) || defined(CONFIG_KSU)")
patch_05_lines.append("+\tif (unlikely(ksu_input_hook))")
patch_05_lines.append("+\t\tksu_handle_input_handle_event(&type, &code, &value);")
patch_05_lines.append("+#endif")
patch_05_lines.append("+")
patch_05_lines.append(" \tif ((disposition & INPUT_PASS_TO_DEVICE) && dev->event)")
patch_05_lines.append(" \t\tdev->event(dev, type, code, value);")

write_patch("05_input_hook.patch", "\n".join(patch_05_lines) + "\n")

print("\\n✅ All 5 patches generated with CORRECT hunk headers!")
