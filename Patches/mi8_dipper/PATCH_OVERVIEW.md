# NonGKI 内核补丁完整分析

本文档汇总 NonGKI_Kernel_Build_2nd 项目中所有补丁的用途和目标文件（不含 SUSFS）。

---

## 📋 补丁总览

| 类别 | 补丁/脚本 | 必要性 | 说明 |
|------|-----------|--------|------|
| **Syscall Hook** | `syscall_hook_patches.sh` | ✅ 必须 | KernelSU Manual 模式核心 |
| **SELinux Backport** | `backport_selinux_patches.sh` | ⚠️ 视情况 | 旧内核(<5.1)兼容性 |
| **Memory API** | `set_memory_to_49_and_low.patch` | ⚠️ 视情况 | kprobes 所需的内存函数 |
| **Backport** | `backport_patches.sh` | ⚠️ 视情况 | 旧内核 API 兼容 |
| **HideStuff** | `.cocci` 文件 | 🔧 可选 | 隐藏检测相关 |
| **Rekernel** | Rekernel 补丁 | 🔧 可选 | 后台进程冻结优化 |

---

## 1️⃣ Syscall Hook 补丁 (核心)

> **脚本**: `syscall_hook_patches.sh`

这是 **KernelSU Manual Hook 模式必须的补丁**，包含以下文件修改：

### 文件系统 Hook (`fs/`)

| 文件 | Hook 函数 | 功能 |
|------|-----------|------|
| `fs/exec.c` | `ksu_handle_execveat` | 检测 su 执行请求 |
| `fs/open.c` | `ksu_handle_faccessat` | 检测 su 文件访问 |
| `fs/read_write.c` | `ksu_handle_sys_read` | init.rc 注入 |
| `fs/stat.c` | `ksu_handle_stat` | 文件状态伪装 |
| `fs/namei.c` | throne_tracker 检测 | 阻止 root 检测扫描 |

### 驱动 Hook (`drivers/`)

| 文件 | Hook 函数 | 功能 |
|------|-----------|------|
| `drivers/input/input.c` | `ksu_handle_input_handle_event` | 音量键安全模式触发 |
| `drivers/tty/pty.c` | `ksu_handle_devpts` | PTY 权限处理 |

### 安全子系统 Hook (`security/`)

| 文件 | Hook 函数 | 功能 |
|------|-----------|------|
| `security/security.c` | `ksu_bprm_check`, `ksu_handle_rename`, `ksu_handle_setuid` | 权限检查和过渡 |
| `security/selinux/hooks.c` | `is_ksu_transition` | SELinux 规则绕过 |

### 内核核心 Hook (`kernel/`)

| 文件 | Hook 函数 | 功能 |
|------|-----------|------|
| `kernel/reboot.c` | `ksu_handle_sys_reboot` | **Supercall 通信入口** (Manager 与内核通信) |
| `kernel/sys.c` | `ksu_handle_setresuid` | UID 切换处理 (SUSFS 相关) |

---

## 2️⃣ SELinux Backport 补丁

> **脚本**: `backport_selinux_patches.sh`  
> **适用**: 内核版本 < 5.1

将新版内核的 SELinux API 回移植到旧内核，使 KernelSU 能正确操作 SELinux 上下文。

| 文件 | 修改内容 |
|------|----------|
| `security/selinux/hooks.c` | `inode->i_security` → `selinux_inode(inode)`, `cred->security` → `selinux_cred(cred)` |
| `security/selinux/selinuxfs.c` | 同上 |
| `security/selinux/xfrm.c` | 同上 |
| `security/selinux/include/objsec.h` | 添加 `selinux_inode()` 和 `selinux_cred()` 内联函数 |

> [!NOTE]
> 如果你的内核版本 ≥ 5.1，此补丁会自动跳过。

---

## 3️⃣ Memory API 补丁

> **文件**: `Patch/set_memory_to_49_and_low.patch`  
> **适用**: 需要 kprobes 功能的旧内核

这是一个**大型补丁** (170KB, 5260行)，回移植内核 4.9+ 的内存管理 API：

| 新增/修改 | 说明 |
|-----------|------|
| `arch/*/include/asm/set_memory.h` | 添加 `set_memory_ro()`, `set_memory_rw()`, `set_memory_x()`, `set_memory_nx()` |
| `ARCH_HAS_SET_MEMORY` | Kconfig 选项 |
| `set_direct_map_*` | 页表直接映射函数 |
| `totalram_pages()` | 函数化接口 (原为变量) |

> [!IMPORTANT]
> 此补丁主要用于 **kprobes 动态 hook**。如果你使用 Manual Hook 模式，可能不需要。

---

## 4️⃣ Kernel Read/Write Backport

> **文件**: `Patch/backport_kernel_read_and_kernel_write_*.patch`

为旧内核添加 `kernel_read()` 和 `kernel_write()` 函数，KernelSU 文件操作所需。

| 补丁文件 | 目标内核版本 |
|----------|--------------|
| `backport_kernel_read_and_kernel_write_3.18.patch` | 3.18 |
| `backport_kernel_read_and_kernel_write_4.4.patch` | 4.4 |
| `backport_kernel_read_and_kernel_write_4.9.patch` | 4.9 |

---

## 5️⃣ HideStuff (Coccinelle) 补丁

> **目录**: `HideStuff/`

使用 Coccinelle 语义补丁修改内核，用于隐藏 root 相关痕迹。

| 文件 | 目标 | 功能 |
|------|------|------|
| `function_hide_stuff.cocci` | `fs/proc/task_mmu.c` | 在 `/proc/[pid]/maps` 中隐藏 `lineage` 和 `jit-zygote-cache` 路径 |
| `added_show_vma_header_prefix_fake.cocci` | `fs/proc/task_mmu.c` | 添加伪造的 VMA header 输出函数 |
| `function_hide_stuff_partii.cocci` | `fs/proc/task_mmu.c` | 继续隐藏处理 |

> [!CAUTION]
> 这些是**检测隐藏**补丁，可能影响系统稳定性，仅在需要时使用。

---

## 6️⃣ Rekernel 补丁

> **目录**: `Rekernel/`

用于 Android 后台进程管理优化 (Re:Kernel 项目)。

| 文件 | 功能 |
|------|------|
| `rekernel_extra.patch` | 添加 `drivers/rekernel/rekernel.h`，实现 netlink 通信和冻结状态检测 |
| `rekernel_patches.sh` | 自动打补丁脚本 |

**主要功能**：
- Netlink 内核服务器 (端口 22-26)
- 进程冻结状态检测 (`frozen()`, `freezing()`)
- `/proc/rekernel/` 接口

---

## 🎯 你的 Mi8 (dipper) 需要哪些补丁？

基于你的内核版本 (4.9) 和使用 **SukiSU Manual Hook 模式**：

### ✅ 已应用的补丁 (mi8_dipper/)

| 补丁 | 状态 | 对应 syscall_hook_patches.sh 功能 |
|------|------|-----------------------------------|
| `01_exec_hook.patch` | ✅ | fs/exec.c |
| `02_open_hook.patch` | ✅ | fs/open.c |
| `03_read_write_hook.patch` | ✅ | fs/read_write.c |
| `04_stat_hook.patch` | ✅ | fs/stat.c |
| `05_input_hook.patch` | ✅ | drivers/input/input.c |
| `06_reboot_hook.patch` | ✅ | kernel/reboot.c |

### ⚠️ 可能需要的补丁

| 补丁 | 是否需要 | 原因 |
|------|----------|------|
| **SELinux hooks.c** | ⚠️ 看情况 | 如果 Zygisk/隐藏有问题，可能需要 `is_ksu_transition` |
| **security/security.c** | ⚠️ 视版本 | 4.9 内核可能需要 `ksu_bprm_check` 等 |
| **backport_selinux** | ⚠️ 可能需要 | 4.9 内核需要 `selinux_inode()` 等函数 |

### 🔧 可选补丁

| 补丁 | 建议 |
|------|------|
| HideStuff | 仅在需要深度隐藏时使用 |
| Rekernel | 仅在需要省电优化时使用 |
| SUSFS | 已排除 |

---

## 📝 测试建议

1. **先刷入当前 6 个补丁的内核**
2. **验证 SukiSU Manager 版本号正确显示**
3. **安装 Zygisk Next 测试**
4. **如果有问题**，再考虑添加：
   - `security/selinux/hooks.c` 的 `is_ksu_transition` hook
   - `security/security.c` 的相关 hook

---

*文档生成时间: 2026-01-19*
