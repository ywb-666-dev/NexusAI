package org.ibo.nexusjava.modules.auth.vo;

import lombok.Data;

/**
 * @author: yi327
 * @date: 2026/5/27
 */
@Data
public class LoginVO {
    private String token;
    private String tokenType = "Bearer";
    private Long expiresIn;
}