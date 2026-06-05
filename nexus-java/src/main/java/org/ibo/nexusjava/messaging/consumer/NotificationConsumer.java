package org.ibo.nexusjava.messaging.consumer;

import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
import org.apache.rocketmq.spring.core.RocketMQListener;
import org.ibo.nexusjava.messaging.dto.NotificationMessage;
import org.ibo.nexusjava.modules.notification.entity.Notification;
import org.ibo.nexusjava.modules.notification.mapper.NotificationMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;

@Slf4j
@Component
@ConditionalOnProperty(name = "rocketmq.enabled", havingValue = "true")
@RocketMQMessageListener(
        topic = "nexus-notification",
        consumerGroup = "nexus-java-notification-consumers"
)
public class NotificationConsumer implements RocketMQListener<NotificationMessage> {

    @Autowired
    private NotificationMapper notificationMapper;

    @Override
    public void onMessage(NotificationMessage message) {
        log.info("[Notification] 收到通知消息: userId={}, type={}",
                message.getUserId(), message.getType());

        Notification notification = new Notification();
        notification.setUserId(message.getUserId());
        notification.setType(message.getType());
        notification.setTitle(message.getTitle());
        notification.setContent(message.getContent());
        notification.setIsRead(0);
        notification.setRelatedId(message.getRelatedId());
        notification.setCreatedAt(LocalDateTime.now());

        notificationMapper.insert(notification);

        log.info("[Notification] 通知已持久化: notificationId={}, userId={}",
                notification.getId(), message.getUserId());
    }
}
