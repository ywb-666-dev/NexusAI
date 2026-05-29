package org.ibo.nexusjava.modules.notification.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.ibo.nexusjava.modules.notification.entity.Notification;

@Mapper
public interface NotificationMapper extends BaseMapper<Notification> {
}
