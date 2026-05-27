package org.ibo.nexusjava.common;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import org.ibo.nexusjava.common.ErrorCode;
/**
 * 运行时异常，带错误码和消息
 *
 * @author: yi327
 * @date: 2026/5/26
 * @since 1.0.0
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
//为什么不继承 Exception？ 因为这是一个非受检异常，Controller / Service 层不需要在方法签名上写 throws，减少代码污染。
public class BusinessException extends RuntimeException {
    /** 业务运行时异常错误码*/
    private Integer code;
    /**提示信息*/
    private String message;

    // 1. 只有错误码枚举
    public BusinessException(ErrorCode errorCode) {
        super(errorCode.getMessage());
        this.code = errorCode.getCode();
    }

    // 2. 错误码枚举 + 自定义消息（覆盖枚举里的默认消息）
    public BusinessException(ErrorCode errorCode, String customMessage) {
        super(customMessage);
        this.code = errorCode.getCode();
    }

    // 3. 错误码枚举 + 原始异常 cause（用于包装底层异常，保留堆栈）
    public BusinessException(ErrorCode errorCode, Throwable cause) {
        super(errorCode.getMessage(), cause);
        this.code = errorCode.getCode();
    }


}
