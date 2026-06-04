package org.ibo.nexusjava.common;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;


/**
 * 全局捕获异常，包装成Result返回
 *
 * @author: yi327
 * @date: 2026/5/27
 */
@RestControllerAdvice
public class GlobalExceptionHandler {
    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);
    @ExceptionHandler(BusinessException.class)
    public Result<Void> handleBusinessException(BusinessException e, HttpServletRequest request) {
        // 1. 从异常对象取 code 和 message
        var code=e.getCode();
        var message=e.getMessage();
        // 2. 可选：用 SLF4J 打印 warn 日志，包含 requestId 和 URL
        log.warn("[BusinessException] requestId:{},URL:{},code:{},message:{}",request.getAttribute("requestId"),request.getRequestURL(),code,message);
        // 3. 返回 Result.error(e.getCode(), e.getMessage())
        return Result.error(code,message);
    }
    @ExceptionHandler(Exception.class)
    public Result<Void> handleException(Exception e, HttpServletRequest request) {
        // 1. 打印 ERROR 级别 + 完整堆栈
        log.error("[SystemException] URI={}", request.getRequestURI(), e);
        // 2. 返回模糊提示，不要把 e.getMessage() 暴露给前端
        return Result.error(ErrorCode.SYSTEM_ERROR.getCode(), "系统繁忙，请稍后重试");
    }
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public Result<Void> handleValidException(MethodArgumentNotValidException e) {
        // 从 e.getBindingResult().getFieldErrors() 取第一个错误
        // 格式如："用户名不能为空"
        String msg = e.getBindingResult().getFieldErrors().get(0).getDefaultMessage();

        return Result.error(ErrorCode.PARAM_ERROR.getCode(), msg);
    }

}
