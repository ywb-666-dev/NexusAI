package org.ibo.nexusjava.modules.auth.service;


import org.ibo.nexusjava.modules.auth.dto.LoginDTO;
import org.ibo.nexusjava.modules.auth.dto.RegisterDTO;
import org.ibo.nexusjava.modules.auth.vo.LoginVO;

/**
 * @author: yi327
 * @date: 2026/5/27
 */

public interface AuthService {
    void register(RegisterDTO dto);
    LoginVO login(LoginDTO dto);
}
