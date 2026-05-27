package org.ibo.nexusjava.common;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.jboss.logging.MDC;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.UUID;

/**
 * @author: yi327
 * @date: 2026/5/27
 */
@Component
public class RequestIdFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain)
            throws ServletException, IOException {
        //1、生成UUID(去掉横线是为了缩短长度)
        String  requestId= UUID.randomUUID().toString().replace("-","");
        //2、放入MDC
        MDC.put("requestId",requestId);
        //3、放入响应头，让前端拿到这个ID(报错时可以把ID贴给后端排查)
        response.setHeader("X-Request-Id",requestId);
        //4、也放入request attribute,供后面的GlobalExceptionHandler取用
        request.setAttribute("requestId",requestId);
        try{
            //5、放行请求
            filterChain.doFilter(request,response);
        }finally {
            //6、请求结束后清理MDC，防止线程池复用导致下一个请求带上旧的requestId
            MDC.remove("requestId");
        }
    }
}
