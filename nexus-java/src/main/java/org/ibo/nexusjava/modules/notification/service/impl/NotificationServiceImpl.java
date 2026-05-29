package org.ibo.nexusjava.modules.notification.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.ibo.nexusjava.common.BusinessException;
import org.ibo.nexusjava.common.ErrorCode;
import org.ibo.nexusjava.modules.notification.entity.Notification;
import org.ibo.nexusjava.modules.notification.mapper.NotificationMapper;
import org.ibo.nexusjava.modules.notification.service.NotificationService;
import org.ibo.nexusjava.modules.notification.vo.NotificationVO;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Service
public class NotificationServiceImpl extends ServiceImpl<NotificationMapper, Notification> implements NotificationService {

    private NotificationVO convertToVO(Notification notification) {
        NotificationVO vo = new NotificationVO();
        vo.setId(notification.getId());
        vo.setUserId(notification.getUserId());
        vo.setType(notification.getType());
        vo.setTitle(notification.getTitle());
        vo.setContent(notification.getContent());
        vo.setIsRead(notification.getIsRead());
        vo.setRelatedId(notification.getRelatedId());
        vo.setCreatedAt(notification.getCreatedAt());
        return vo;
    }

    @Override
    public IPage<NotificationVO> listByUser(Long userId, Long current, Long size) {
        LambdaQueryWrapper<Notification> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Notification::getUserId, userId);
        wrapper.orderByDesc(Notification::getCreatedAt);

        Page<Notification> page = new Page<>(current != null ? current : 1, size != null ? size : 10);
        page(page, wrapper);

        List<NotificationVO> records = page.getRecords().stream()
                .map(this::convertToVO)
                .collect(Collectors.toList());

        Page<NotificationVO> resultPage = new Page<>(page.getCurrent(), page.getSize(), page.getTotal());
        resultPage.setRecords(records);
        return resultPage;
    }

    @Override
    public Long countUnread(Long userId) {
        LambdaQueryWrapper<Notification> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Notification::getUserId, userId);
        wrapper.eq(Notification::getIsRead, 0);
        return count(wrapper);
    }

    @Override
    public void markAsRead(Long id) {
        Notification notification = getById(id);
        if (notification == null) {
            throw new BusinessException(ErrorCode.NOTIFICATION_NOT_FOUND);
        }
        notification.setIsRead(1);
        updateById(notification);
    }

    @Override
    public void markAllAsRead(Long userId) {
        LambdaQueryWrapper<Notification> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Notification::getUserId, userId);
        wrapper.eq(Notification::getIsRead, 0);

        Notification update = new Notification();
        update.setIsRead(1);
        update(update, wrapper);
    }
}
