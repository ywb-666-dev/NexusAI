package org.ibo.nexusjava.config;
import org.ibo.nexusjava.common.RequestIdFilter;
import org.ibo.nexusjava.interceptor.JwtAuthenticationInterceptor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.Ordered;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;
/**
 * @author: yi327
 * @date: 2026/5/27
 */
@Configuration
public class WebConfig implements WebMvcConfigurer {

    @Autowired
    private JwtAuthenticationInterceptor jwtAuthenticationInterceptor;

    @Autowired
    private RequestIdFilter requestIdFilter;

    /**
     * 【第 1 件事】精确注册 RequestIdFilter
     *
     * 虽然 RequestIdFilter 加了 @Component 会自动进入 Filter 链，
     * 但默认顺序是最后，且映射路径是 /*（会拦截静态资源）。
     * 通过 FilterRegistrationBean 我们可以：
     *   1. 把它提到最高优先级（HIGHEST_PRECEDENCE），确保它比 Spring 默认 Filter 先执行
     *   2. 限定只拦截 /api/*，不拦 /favicon.ico 这类静态请求
     */
    @Bean
    public FilterRegistrationBean<RequestIdFilter> requestIdFilterRegistration() {
        FilterRegistrationBean<RequestIdFilter> registration = new FilterRegistrationBean<>();
        registration.setFilter(requestIdFilter);          // 设置 Filter 实例
        registration.addUrlPatterns("/api/*");            // 只拦 API 请求
        registration.setOrder(Ordered.HIGHEST_PRECEDENCE); // 数字越小越先执行
        return registration;
    }

    /**
     * 【第 2 件事】配置跨域（CORS）
     *
     * 前端开发服务器（如 Vite 在 localhost:5173）向 localhost:8081 发请求时，
     * 浏览器会触发预检（OPTIONS），不配置这里前端会报 CORS 错误。
     */
    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")                    // 对 /api 下所有路径生效
                .allowedOrigins(
                        "http://localhost:5173",              // Vite 默认端口
                        "http://localhost:3000"               // React 或其他前端
                )
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
                .allowedHeaders("*")                      // 允许所有请求头（含 Authorization）
                .allowCredentials(true)                   // 允许携带 Cookie / Token
                .maxAge(3600);                            // 预检结果缓存 1 小时
    }

    /**
     * 【第 3 件事】注册 JWT 拦截器
     *
     * Interceptor 工作在 DispatcherServlet 之后，比 Filter 更晚。
     * 这里排除 /api/java/auth/**，让登录、注册接口免鉴权。
     */
    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(jwtAuthenticationInterceptor)
                .addPathPatterns("/api/java/**")          // 拦截所有业务接口
                .excludePathPatterns("/api/java/auth/**"); // 放行登录、注册
    }
}
