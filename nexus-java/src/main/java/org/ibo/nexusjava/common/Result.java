package org.ibo.nexusjava.common;


import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;


/**
 * 统一API响应封装类
 *
 * <p>所有 Controller 接口的返回值都应包装为此对象，确保前端接收的数据结构一致。</p>
 *
 *
 * @author: yi327
 * @date: 2026/5/26
 * @since: 1.0.0
 *
 */


@Data              // 自动生成 getter、setter、toString、equals、hashCode
@NoArgsConstructor // 无参构造
@AllArgsConstructor // 全参构造
public class Result<T> {
    /** HTTP 业务状态码，200 表示成功，非 200 表示各类业务错误 */
    private Integer code;
    /** 提示信息，成功时为 "success"，失败时为具体错误描述 */
    private String message;
    /** 实际业务数据，类型由具体接口决定 */
    private T data;
    /** 请求追踪 ID，用于分布式日志排查 */
    private String requestId;

    /**
     * 构造一个成功的响应类
     * @param data  业务数据，允许为null
     * @return  包装后的对象，code默认为200
     * @param <T>   数据泛型
     */
    public static <T> Result<T> success(T data) {
        Result<T> r = new Result<>();
        r.setCode(200);
        r.setMessage("success");
        r.setData(data);
        return r;
    }
    public static <T> Result<T> success() {
        return success(null);
    }

    /**
     * 构造一个失败的响应类
     * @param code  业务错误码，如 4001、5001 等
     * @param message   错误描述，建议直接展示给用户
     * @return  包装后的 Result 对象，data 为 null
     * @param <T>   数据泛型
     */
    public static <T> Result<T> error(Integer code, String message) {
        Result<T> r = new Result<>();
        r.setCode(code);
        r.setMessage(message);
        return r;
    }
}