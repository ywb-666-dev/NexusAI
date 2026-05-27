package org.ibo.nexusjava.common;

/**
 * 定义错误枚举
 *
 * @author: yi327
 * @date: 2026/5/27
 */
public enum ErrorCode {
    // 通用
    SUCCESS(200, "success"),
    SYSTEM_ERROR(5000, "系统繁忙，请稍后重试"),
    PARAM_ERROR(4000, "请求参数错误"),

    // 认证模块 1100-1199
    AUTH_USERNAME_EXISTS(1100, "用户名已存在"),
    AUTH_LOGIN_FAILED(1101, "用户名或密码错误"),
    AUTH_TOKEN_EXPIRED(1102, "登录已过期，请重新登录"),
    AUTH_TOKEN_INVALID(1103, "无效的登录凭证"),

    // 用户模块 1200-1299
    USER_NOT_FOUND(1200, "用户不存在"),

    // 订阅模块 1300-1399
    SUBSCRIPTION_NOT_FOUND(1300, "订阅规则不存在"),
    SUBSCRIPTION_NAME_EXISTS(1301, "订阅规则名称已存在"),

    // ... 后续按需扩展
    ;

    // 字段 + 构造 + getter
    private final Integer code;
    private final String message;
    ErrorCode(Integer code, String message) {
        this.code = code;
        this.message = message;
    }

    public Integer getCode() {
        return code;
    }
    public String getMessage() {
        return message;
    }
}
