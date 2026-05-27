package org.ibo.nexusjava.modules.user.vo;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * @author: yi327
 * @date: 2026/5/27
 */
@Data
public class UserInfoVO {
    private Long id;           // 用户ID，前端很多地方需要（如跳转个人中心）
    private String username;   // 用户名
    private String email;      // 邮箱
    private String role;       // 角色：user / admin，前端靠它控制菜单权限
    private LocalDateTime createdAt; // 注册时间（可选，看你要不要展示）
}
