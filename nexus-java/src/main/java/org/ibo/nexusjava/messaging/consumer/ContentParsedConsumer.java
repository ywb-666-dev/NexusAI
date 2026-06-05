package org.ibo.nexusjava.messaging.consumer;

import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
import org.apache.rocketmq.spring.core.RocketMQListener;
import org.ibo.nexusjava.messaging.dto.ContentParsedMessage;
import org.ibo.nexusjava.modules.content.entity.Content;
import org.ibo.nexusjava.modules.content.mapper.ContentMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.UUID;

@Slf4j
@Component
@ConditionalOnProperty(name = "rocketmq.enabled", havingValue = "true")
@RocketMQMessageListener(
        topic = "nexus-content-parsed",
        consumerGroup = "nexus-java-content-parsed-consumers"
)
public class ContentParsedConsumer implements RocketMQListener<ContentParsedMessage> {

    @Autowired
    private ContentMapper contentMapper;

    @Override
    public void onMessage(ContentParsedMessage message) {
        log.info("[ContentParsed] 收到内容解析消息: taskId={}, subscriptionId={}",
                message.getTaskId(), message.getSubscriptionId());

        Content content = new Content();
        content.setId(UUID.randomUUID().toString());
        content.setSubscriptionId(message.getSubscriptionId());
        content.setSourcePlatform(message.getSourcePlatform());
        content.setSourceUrl(message.getSourceUrl());
        content.setTitle(message.getTitle());
        content.setSummary(message.getSummary());
        content.setContentBody(message.getContentBody());
        content.setAuthor(message.getAuthor());
        content.setPublishedAt(message.getPublishedAt());
        content.setFetchedAt(LocalDateTime.now());
        content.setContentHash(message.getContentHash());
        content.setVectorId(message.getVectorId());
        content.setStatus(1);
        content.setIsDuplicate(0);
        content.setCreatedAt(LocalDateTime.now());

        contentMapper.insert(content);

        log.info("[ContentParsed] 内容已保存: contentId={}, subscriptionId={}",
                content.getId(), message.getSubscriptionId());
    }
}
