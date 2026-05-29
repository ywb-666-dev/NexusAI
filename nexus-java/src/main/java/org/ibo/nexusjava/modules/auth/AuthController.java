package org.ibo.nexusjava.modules.auth;


import jakarta.validation.Valid;
import org.ibo.nexusjava.common.Result;
import org.ibo.nexusjava.modules.auth.dto.LoginDTO;
import org.ibo.nexusjava.modules.auth.dto.RegisterDTO;
import org.ibo.nexusjava.modules.auth.service.AuthService;
import org.ibo.nexusjava.modules.auth.vo.LoginVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * @author: yi327
 * @date: 2026/5/27
 */
@RestController
@RequestMapping("/api/java/auth")
public class AuthController {
    @Autowired
    AuthService authService;

    @PostMapping("/register")
    public Result<Void> register(@Valid @RequestBody RegisterDTO dto){
        authService.register(dto);
        return Result.success();

    }

    @PostMapping("/login")
    public Result<LoginVO>  login(@Valid @RequestBody LoginDTO dto){
        LoginVO loginVO = authService.login(dto);
        return Result.success(loginVO);
    }
}
