package org.ibo.nexusjava.modules.notification.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import org.ibo.nexusjava.modules.notification.vo.NotificationVO;

public interface NotificationService {
    IPage<NotificationVO> listByUser(Long userId, Long current, Long size);
    Long countUnread(Long userId);
    void markAsRead(Long id);
    void markAllAsRead(Long userId);
}
