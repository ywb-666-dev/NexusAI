package org.ibo.nexusjava.interceptor;

/**
 * 基于 ThreadLocal 的用户上下文工具类。
 *
 * Spring Boot 默认使用 Tomcat 线程池，一个请求对应一个线程。
 * ThreadLocal 保证每个线程有自己独立的变量副本，线程之间互不干扰。
 *
 * 使用场景：Controller / Service 层里随时获取"当前登录用户是谁"，
 * 不用把 userId 从 Controller 一路往下传参。
 *
 * @author yi327
 * @date 2026/5/27
 */
public class UserContext {

    // ThreadLocal 里存一个 Map，方便后续扩展（如加入 username、role 等）
    private static final ThreadLocal<java.util.Map<String, Object>> CONTEXT = ThreadLocal.withInitial(java.util.HashMap::new);

    private static final String KEY_USER_ID = "userId";
    private static final String KEY_USERNAME = "username";
    private static final String KEY_ROLE = "role";

    public static void setUserId(Long userId) {
        CONTEXT.get().put(KEY_USER_ID, userId);
    }

    public static Long getUserId() {
        Object val = CONTEXT.get().get(KEY_USER_ID);
        return val == null ? null : (Long) val;
    }

    public static void setUsername(String username) {
        CONTEXT.get().put(KEY_USERNAME, username);
    }

    public static String getUsername() {
        Object val = CONTEXT.get().get(KEY_USERNAME);
        return val == null ? null : (String) val;
    }

    public static void setRole(String role) {
        CONTEXT.get().put(KEY_ROLE, role);
    }

    public static String getRole() {
        Object val = CONTEXT.get().get(KEY_ROLE);
        return val == null ? null : (String) val;
    }

    /**
     * 请求结束后必须调用，防止线程池复用导致下一个请求带上旧数据。
     */
    public static void clear() {
        CONTEXT.remove();
    }
}