package org.ibo.nexusjava.modules.auth.service.impl;

import org.ibo.nexusjava.modules.auth.service.AuthService;

/**
 * @author: yi327
 * @date: 2026/5/27
 */

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import org.ibo.nexusjava.common.BusinessException;
import org.ibo.nexusjava.common.ErrorCode;
import org.ibo.nexusjava.common.JwtUtil;
import org.ibo.nexusjava.modules.auth.dto.LoginDTO;
import org.ibo.nexusjava.modules.auth.dto.RegisterDTO;
import org.ibo.nexusjava.modules.auth.service.AuthService;
import org.ibo.nexusjava.modules.auth.vo.LoginVO;
import org.ibo.nexusjava.modules.user.entity.User;
import org.ibo.nexusjava.modules.user.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

@Service
public class AuthServiceImpl implements AuthService {

    @Autowired
    private UserService userService;

    @Autowired
    private JwtUtil jwtUtil;

    private final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    @Override
    public void register(RegisterDTO dto) {
        // 1. 检查用户名是否已存在
        LambdaQueryWrapper<User> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(User::getUsername, dto.getUsername());
        if (userService.count(wrapper) > 0) {
            throw new BusinessException(ErrorCode.AUTH_USERNAME_EXISTS);
        }

        // 2. 加密密码
        String hash = passwordEncoder.encode(dto.getPassword());

        // 3. 构造用户实体
        User user = new User();
        user.setUsername(dto.getUsername());
        user.setPasswordHash(hash);
        user.setEmail(dto.getEmail());
        user.setRole("user"); // 默认角色

        // 4. 保存
        userService.save(user);
    }

    @Override
    public LoginVO login(LoginDTO dto) {
        // 1. 根据用户名查用户
        LambdaQueryWrapper<User> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(User::getUsername, dto.getUsername());
        User user = userService.getOne(wrapper);

        if (user == null) {
            throw new BusinessException(ErrorCode.AUTH_LOGIN_FAILED);
        }

        // 2. 校验密码
        if (!passwordEncoder.matches(dto.getPassword(), user.getPasswordHash())) {
            throw new BusinessException(ErrorCode.AUTH_LOGIN_FAILED);
        }

        // 3. 生成 JWT
        String token = jwtUtil.generateToken(user.getId(), user.getUsername(), user.getRole());

        // 4. 构造返回对象
        LoginVO vo = new LoginVO();
        vo.setToken(token);
        vo.setTokenType("Bearer");
        vo.setExpiresIn(86400L); // 24小时，单位秒

        return vo;
    }
}