package org.ibo.nexusjava.modules.user.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.ibo.nexusjava.modules.user.entity.User;
import org.ibo.nexusjava.modules.user.mapper.UserMapper;
import org.ibo.nexusjava.modules.user.service.UserService;
import org.springframework.stereotype.Service;

/**
 * @author: yi327
 * @date: 2026/5/27
 */
@Service
public class UserServiceImpl extends ServiceImpl<UserMapper, User> implements UserService {
}
