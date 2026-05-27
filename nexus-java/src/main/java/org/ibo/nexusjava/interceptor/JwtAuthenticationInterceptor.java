package org.ibo.nexusjava.interceptor;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.security.SecurityException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.ibo.nexusjava.common.JwtUtil;
import org.ibo.nexusjava.common.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import java.io.IOException;

/**
 * @author yi327
 * @date 2026/5/27
 */
@Component
public class JwtAuthenticationInterceptor implements HandlerInterceptor {

    @Autowired
    private JwtUtil jwtUtil;

    private final ObjectMapper objectMapper=new ObjectMapper();

    // Token 请求头前缀
    private static final String TOKEN_PREFIX = "Bearer ";

    /**
     * 在 Controller 方法执行前调用。
     * 负责：提取 Token → 解析 JWT → 写入 UserContext。
     * 返回 true 放行，返回 false 拦截并写 401 响应。
     */
    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        // 1. 从请求头取 Authorization
        String authHeader = request.getHeader("Authorization");

        // 2. 如果为空或不以 Bearer 开头，返回 401
        if (authHeader == null || !authHeader.startsWith(TOKEN_PREFIX)) {
            writeUnauthorized(response, 1103, "缺少登录凭证或格式错误");
            return false;
        }

        // 3. 去掉 "Bearer " 前缀，得到纯 Token
        String token = authHeader.substring(TOKEN_PREFIX.length());

        // 4. 解析 Token
        try {
            Claims claims = jwtUtil.parseToken(token);

            // 5. 提取信息
            Long userId = Long.valueOf(claims.getSubject());
            String username = claims.get("username", String.class);
            String role = claims.get("role", String.class);

            // 6. 写入 ThreadLocal，供后续 Controller / Service 使用
            UserContext.setUserId(userId);
            UserContext.setUsername(username);
            UserContext.setRole(role);

            // 7. 同时写入 request attribute（供 Filter / 异常处理器使用）
            request.setAttribute("userId", userId);
            request.setAttribute("username", username);

            return true; // 放行

        } catch (ExpiredJwtException e) {
            writeUnauthorized(response, 1102, "登录已过期，请重新登录");
            return false;
        } catch ( JwtException | IllegalArgumentException e) {
            writeUnauthorized(response, 1103, "无效的登录凭证");
            return false;
        }
    }

    /**
     * 在整个请求处理完成后调用（包括视图渲染完毕）。
     * 负责：清理 ThreadLocal，防止内存泄漏和线程污染。
     */
    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler, Exception ex) throws Exception {
        UserContext.clear();
    }

    /**
     * 向响应体写入标准化的 401 错误（JSON 格式）。
     *
     * 因为此时请求还没进入 Controller，@RestControllerAdvice 不会生效，
     * 必须手动写响应。
     */
    private void writeUnauthorized(HttpServletResponse response, int code, String message) throws IOException {
        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED); // HTTP 401
        response.setContentType("application/json;charset=UTF-8");

        Result<Void> result = Result.error(code, message);
        String json = objectMapper.writeValueAsString(result);

        response.getWriter().write(json);
        response.getWriter().flush();
    }
}