package org.ibo.nexusjava.common;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

class BusinessExceptionTest {
    @Test
    void exposesDefaultAndCustomMessagesToTheApiHandler() {
        assertEquals(ErrorCode.PARAM_ERROR.getMessage(), new BusinessException(ErrorCode.PARAM_ERROR).getMessage());
        assertEquals("未找到相关来源", new BusinessException(ErrorCode.PARAM_ERROR, "未找到相关来源").getMessage());
        assertEquals(ErrorCode.SYSTEM_ERROR.getMessage(), new BusinessException(ErrorCode.SYSTEM_ERROR, new RuntimeException("cause")).getMessage());
    }
}
